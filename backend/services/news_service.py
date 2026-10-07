import uuid
import hashlib
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from backend.models.news import (
    NewsSource, Article, ArticleVersion, PoliticalEntity, Topic,
    ArticleEntity, ArticleTopic, ArticleFeature, CoverageMetric, BiasIndicator,
    SourceType, ActiveStatus
)
from backend.models.common import Document, Evidence, Source
from backend.nlp.news_analyzer import TamilNewsAnalyzer
from backend.acquisition.news_scraper import NewsScraper
from backend.core.logger import setup_logger

logger = setup_logger("civiclens.services.news_service")

class NewsService:
    """Business logic for Phase 4 Tamil News Ingestion, Provenance, and Neutral Coverage Analysis."""

    def __init__(self, db: Session):
        self.db = db
        self.analyzer = TamilNewsAnalyzer()
        self.scraper = NewsScraper()

    def register_source(self, source_id: str, source_name: str, domain: str, language: str = "ta",
                        source_type: SourceType = SourceType.PRINT_DIGITAL, official_url: str = None,
                        selector_config: dict = None) -> NewsSource:
        """Registers a new media outlet or government portal in the source registry."""
        existing = self.db.query(NewsSource).filter(NewsSource.source_id == source_id).first()
        if existing:
            return existing

        source = NewsSource(
            source_id=source_id,
            source_name=source_name,
            domain=domain,
            language=language,
            source_type=source_type,
            official_url=official_url or f"https://{domain}",
            robots_policy_checked=True,
            active_status=ActiveStatus.ACTIVE,
            selector_config=selector_config
        )
        self.db.add(source)

        # Sync with core common.Source model for unified provenance
        common_source = self.db.query(Source).filter(Source.name == source_name).first()
        if not common_source:
            common_source = Source(
                name=source_name,
                url=official_url or f"https://{domain}",
                type="News" if source_type != SourceType.OFFICIAL_GOV else "Government"
            )
            self.db.add(common_source)

        self.db.commit()
        self.db.refresh(source)
        return source

    def ingest_article(self, source_id: str, url: str, title: str, article_text: str,
                       author: str = "Staff Reporter", publication_date: datetime = None,
                       section: str = None, is_test_fixture: bool = False) -> Article:
        """
        Ingests a news article, creates unified Document/Evidence provenance records,
        runs NLP normalization, entity extraction, topic classification, and feature indexing.
        """
        source = self.db.query(NewsSource).filter(NewsSource.source_id == source_id).first()
        if not source:
            raise ValueError(f"News source '{source_id}' not found in registry.")

        # Check exact duplicate URL or text hash
        text_hash = self.scraper.compute_text_hash(article_text)
        existing_art = self.db.query(Article).filter(
            (Article.url == url) | (Article.text_hash == text_hash)
        ).first()
        if existing_art:
            logger.info(f"Duplicate article detected for URL: {url}. Skipping ingestion.")
            return existing_art

        # Detect language and normalize Tamil script
        lang = self.analyzer.detect_language(article_text)
        normalized_text = self.analyzer.normalize_tamil_text(article_text) if lang == "ta" else article_text
        normalized_title = self.analyzer.normalize_tamil_text(title) if lang == "ta" else title
        word_count = len(normalized_text.split())

        article_id = f"art_{uuid.uuid4().hex[:10]}"
        pub_date = publication_date or datetime.now(timezone.utc)

        article = Article(
            article_id=article_id,
            source_id=source_id,
            url=url,
            canonical_url=url,
            title=normalized_title,
            author=author,
            publication_date=pub_date,
            section=section,
            language=lang,
            article_text=normalized_text,
            word_count=word_count,
            text_hash=text_hash,
            is_test_fixture=is_test_fixture
        )
        self.db.add(article)

        # Track Initial Version
        version = ArticleVersion(
            article_id=article_id,
            version_number=1,
            text_hash=text_hash,
            article_text=normalized_text
        )
        self.db.add(version)

        # Core Unified Provenance Link: Create Document & Evidence records
        common_source = self.db.query(Source).filter(Source.name == source.source_name).first()
        common_doc = Document(
            source_id=common_source.id if common_source else None,
            title=normalized_title,
            content=normalized_text,
            url=url,
            published_date=pub_date.date() if isinstance(pub_date, datetime) else pub_date
        )
        self.db.add(common_doc)
        self.db.flush()

        evidence = Evidence(
            document_id=common_doc.id,
            content=normalized_text[:500], # Lead paragraph snippet
            explanation="Ingested news article for Phase 4 political coverage analysis.",
            result_type="NewsArticle",
            result_id=article_id
        )
        self.db.add(evidence)

        # Run NLP Extraction
        entities = self.analyzer.extract_entities(normalized_text)
        for ent_data in entities:
            # Ensure entity exists in PoliticalEntity DB
            db_ent = self.db.query(PoliticalEntity).filter(PoliticalEntity.entity_id == ent_data["entity_id"]).first()
            if not db_ent:
                db_ent = PoliticalEntity(
                    entity_id=ent_data["entity_id"],
                    entity_type=ent_data["type"],
                    name=ent_data["name"],
                    normalized_name=ent_data["name"]
                )
                self.db.add(db_ent)

            art_ent = ArticleEntity(
                article_id=article_id,
                entity_id=ent_data["entity_id"],
                mention_count=ent_data["mention_count"],
                prominence_score=ent_data["prominence_score"],
                sentiment_score=ent_data["sentiment_score"]
            )
            self.db.add(art_ent)

        # Run Topic Classification
        topics = self.analyzer.classify_topics(normalized_text)
        for idx, top_data in enumerate(topics):
            db_top = self.db.query(Topic).filter(Topic.topic_id == top_data["topic_id"]).first()
            if not db_top:
                db_top = Topic(
                    topic_id=top_data["topic_id"],
                    topic_code=top_data["topic_id"],
                    topic_name=top_data["topic_name"]
                )
                self.db.add(db_top)

            art_top = ArticleTopic(
                article_id=article_id,
                topic_id=top_data["topic_id"],
                relevance_score=top_data["relevance_score"],
                is_primary=(idx == 0)
            )
            self.db.add(art_top)

        # Extract NLP Features & Signals
        feat_data = self.analyzer.extract_features(normalized_title, normalized_text)
        features = ArticleFeature(
            article_id=article_id,
            headline_sentiment=feat_data["headline_sentiment"],
            body_sentiment=feat_data["body_sentiment"],
            quote_count=feat_data["quote_count"],
            official_source_citation_count=feat_data["official_source_citation_count"],
            word_count=feat_data["word_count"],
            vocabulary_richness=feat_data["vocabulary_richness"],
            framing_indicators=feat_data["framing_indicators"]
        )
        self.db.add(features)

        self.db.commit()
        self.db.refresh(article)
        return article

    def calculate_bias_indicators(self, source_id: str, compare_source_id: str = None) -> list:
        """
        Calculates multi-dimensional comparative statistical indicators.
        Enforces neutral terminology and avoids single-score claims.
        """
        source = self.db.query(NewsSource).filter(NewsSource.source_id == source_id).first()
        if not source:
            return []

        articles = self.db.query(Article).filter(Article.source_id == source_id).all()
        total_articles = len(articles)
        if total_articles == 0:
            return []

        # 1. Topic Emphasis Indicator
        indicators = []
        topic_counts = {}
        for art in articles:
            for top in art.topics:
                topic_counts[top.topic_id] = topic_counts.get(top.topic_id, 0) + 1

        for topic_id, count in topic_counts.items():
            ratio = round(count / total_articles, 3)
            ind_id = f"ind_top_{source_id}_{topic_id}"
            ind = BiasIndicator(
                indicator_id=ind_id,
                source_id=source_id,
                compare_source_id=compare_source_id,
                metric_type="topic_emphasis",
                window_start=datetime.now(timezone.utc),
                window_end=datetime.now(timezone.utc),
                indicator_value=ratio,
                statistical_confidence=1.0,
                interpretation_label=f"Topic emphasis metric: {ratio * 100}% of published coverage allocated to topic '{topic_id}'.",
                metadata_json={"article_count": count, "total_corpus": total_articles}
            )
            indicators.append(ind)

        # 2. Entity Prominence Indicator
        entity_prominence = {}
        for art in articles:
            for ent in art.entities:
                if ent.entity_id not in entity_prominence:
                    entity_prominence[ent.entity_id] = []
                entity_prominence[ent.entity_id].append(ent.prominence_score)

        for ent_id, scores in entity_prominence.items():
            avg_prom = round(sum(scores) / len(scores), 3)
            ind_id = f"ind_ent_{source_id}_{ent_id}"
            ind = BiasIndicator(
                indicator_id=ind_id,
                source_id=source_id,
                compare_source_id=compare_source_id,
                metric_type="entity_prominence",
                window_start=datetime.now(timezone.utc),
                window_end=datetime.now(timezone.utc),
                indicator_value=avg_prom,
                statistical_confidence=1.0,
                interpretation_label=f"Entity prominence metric: Mean visibility score of {avg_prom} for entity '{ent_id}'.",
                metadata_json={"mentions_corpus": len(scores)}
            )
            indicators.append(ind)

        return indicators
