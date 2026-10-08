import os
import re
import uuid
import hashlib
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Tuple, Any
from sqlalchemy.orm import Session

from backend.core.logger import setup_logger
from backend.database.session import SessionLocal
from backend.models.news import (
    Article, NewsSource, NewsIngestionFailure, NewsProcessingQueue
)
from backend.models.common import Document, Evidence, Source
from backend.acquisition.news_scraper_framework import SourceScraper, NewsSourceRegistry
from backend.nlp.news_analyzer import TamilNewsAnalyzer
from backend.services.news_service import NewsService

logger = setup_logger("civiclens.ingestion.news_pipeline")

RAW_ARTICLES_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "scratch", "raw_articles")


class RawStoreManager:
    """Manages raw source page HTML storage and raw reference generation."""

    def __init__(self, base_dir: str = RAW_ARTICLES_DIR):
        self.base_dir = base_dir
        os.makedirs(self.base_dir, exist_ok=True)

    def save_raw_html(self, source_id: str, url: str, html_content: str) -> str:
        """Saves raw HTML payload to disk under source and date hierarchy."""
        url_hash = hashlib.sha256(url.encode('utf-8')).hexdigest()[:12]
        date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        source_dir = os.path.join(self.base_dir, source_id, date_str)
        os.makedirs(source_dir, exist_ok=True)

        file_name = f"{url_hash}.html"
        file_path = os.path.join(source_dir, file_name)

        try:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(html_content)
            logger.info(f"Saved raw page to {file_path}")
            return file_path
        except Exception as e:
            logger.error(f"Failed to save raw HTML payload for {url}: {e}")
            return ""


class DuplicateDetector:
    """
    Multi-tier duplicate detection engine enforcing:
    1. Canonical URL check
    2. Content SHA-256 hash check
    3. Fuzzy Title + Date window similarity check
    """

    @staticmethod
    def compute_title_jaccard_similarity(title1: str, title2: str) -> float:
        """Computes word-level Jaccard similarity between two title strings."""
        t1_words = set(re.sub(r'[^\w\s]', '', title1.lower()).split())
        t2_words = set(re.sub(r'[^\w\s]', '', title2.lower()).split())
        if not t1_words or not t2_words:
            return 0.0
        intersection = t1_words.intersection(t2_words)
        union = t1_words.union(t2_words)
        return len(intersection) / len(union)

    def check_duplicate(self, db: Session, url: str, canonical_url: str,
                        text_hash: str, title: str, pub_date: datetime) -> Tuple[bool, Optional[str]]:
        """
        Executes multi-tier duplicate checks against existing DB records.
        Returns (is_duplicate: bool, reason: str).
        """
        # Tier 1: Canonical URL or Exact URL match
        canon_target = canonical_url or url
        existing_url = db.query(Article).filter(
            (Article.url == url) | (Article.canonical_url == canon_target) | (Article.url == canon_target)
        ).first()
        if existing_url:
            return True, f"Tier 1 Duplicate: Matching URL/Canonical URL ({existing_url.article_id})"

        # Tier 2: Content Hash Match
        existing_hash = db.query(Article).filter(Article.text_hash == text_hash).first()
        if existing_hash:
            return True, f"Tier 2 Duplicate: Matching SHA-256 content hash ({existing_hash.article_id})"

        # Tier 3: Fuzzy Title + Date Window Similarity Check (within 48h)
        if pub_date:
            window_start = pub_date - timedelta(days=2)
            window_end = pub_date + timedelta(days=2)
            candidates = db.query(Article).filter(
                Article.publication_date >= window_start,
                Article.publication_date <= window_end
            ).all()

            for cand in candidates:
                sim = self.compute_title_jaccard_similarity(title, cand.title)
                if sim >= 0.80:
                    return True, f"Tier 3 Duplicate: High title similarity ({sim:.2f}) with article {cand.article_id}"

        return False, ""


class FailureTracker:
    """Records and logs ingestion failures (prevents silent drops)."""

    @staticmethod
    def record_failure(db: Session, source_id: Optional[str], url: str,
                       failure_type: str, error_details: str, raw_html_path: str = "") -> NewsIngestionFailure:
        logger.warning(f"Ingestion failure [{failure_type}] for {url}: {error_details}")
        failure = NewsIngestionFailure(
            source_id=source_id,
            url=url,
            failure_type=failure_type,
            error_details=error_details,
            raw_html_path=raw_html_path
        )
        db.add(failure)
        db.commit()
        db.refresh(failure)
        return failure


class ProcessingQueueManager:
    """Manages downstream NLP processing task queue for ingested articles."""

    @staticmethod
    def enqueue_article(db: Session, article_id: str) -> NewsProcessingQueue:
        queue_item = NewsProcessingQueue(
            article_id=article_id,
            status="PENDING",
            attempts=0
        )
        db.add(queue_item)
        db.commit()
        db.refresh(queue_item)
        logger.info(f"Enqueued article {article_id} for downstream NLP processing.")
        return queue_item

    @staticmethod
    def fetch_pending(db: Session, limit: int = 10) -> List[NewsProcessingQueue]:
        return db.query(NewsProcessingQueue).filter(NewsProcessingQueue.status == "PENDING").limit(limit).all()

    @staticmethod
    def mark_completed(db: Session, queue_id: int) -> None:
        item = db.query(NewsProcessingQueue).filter(NewsProcessingQueue.id == queue_id).first()
        if item:
            item.status = "COMPLETED"
            item.processed_at = datetime.now(timezone.utc)
            db.commit()

    @staticmethod
    def mark_failed(db: Session, queue_id: int, error_msg: str) -> None:
        item = db.query(NewsProcessingQueue).filter(NewsProcessingQueue.id == queue_id).first()
        if item:
            item.status = "FAILED"
            item.attempts += 1
            item.error_message = error_msg
            db.commit()


class MultilingualLanguageDetector:
    """Enhanced language detection supporting Tamil (ta), English (en), and Mixed (mixed)."""

    @staticmethod
    def detect_language(text: str) -> str:
        if not text:
            return "en"
        
        tamil_chars = sum(1 for c in text if '\u0B80' <= c <= '\u0BFF')
        english_chars = sum(1 for c in text if 'a' <= c.lower() <= 'z')
        total_alpha = sum(1 for c in text if c.isalpha())

        if total_alpha == 0:
            return "en"

        tam_ratio = tamil_chars / total_alpha
        eng_ratio = english_chars / total_alpha

        if tam_ratio > 0.40 and eng_ratio > 0.20:
            return "mixed"
        elif tam_ratio > 0.15:
            return "ta"
        else:
            return "en"


class NewsIngestionPipeline:
    """
    End-to-end Raw Article Ingestion Pipeline implementing:
    SOURCE -> SCRAPER -> RAW PAGE -> ARTICLE EXTRACTION -> METADATA -> RAW ARTICLE STORE -> PROCESSING QUEUE
    """

    def __init__(self, db: Session, scraper: Optional[SourceScraper] = None):
        self.db = db
        self.scraper = scraper or SourceScraper()
        self.raw_store = RawStoreManager()
        self.dup_detector = DuplicateDetector()
        self.failure_tracker = FailureTracker()
        self.queue_manager = ProcessingQueueManager()
        self.lang_detector = MultilingualLanguageDetector()
        self.analyzer = TamilNewsAnalyzer()

    def process_url(self, source_id: str, url: str, is_test_fixture: bool = False) -> Optional[Article]:
        """Processes a single article URL through the full pipeline."""
        # 1. Fetch Raw Page Content
        source_config = self.scraper.registry.get_source(source_id)
        if not source_config:
            self.failure_tracker.record_failure(self.db, source_id, url, "VALIDATION_ERROR", f"Source '{source_id}' not found.")
            return None

        if not source_config.enabled:
            logger.warning(f"Source '{source_id}' is disabled. Skipping {url}.")
            return None

        raw_html = self.scraper.fetcher.fetch(url, source_config=source_config)
        if not raw_html:
            self.failure_tracker.record_failure(self.db, source_id, url, "HTTP_ERROR", "Failed to fetch HTTP raw page payload.")
            return None

        # 2. Save Raw Article Page to Store
        raw_ref_path = self.raw_store.save_raw_html(source_id, url, raw_html)

        # 3. Article Extraction & Metadata Parsing
        parsed = self.scraper.parser.parse(raw_html, url, source_config=source_config)
        if not parsed or not parsed.get("article_text") or len(parsed["article_text"].split()) < 15:
            self.failure_tracker.record_failure(
                self.db, source_id, url, "PARSER_ERROR",
                "Article parser produced empty or insufficient body text.", raw_ref_path
            )
            return None

        title = parsed["title"]
        body_text = parsed["article_text"]
        canonical_url = parsed.get("canonical_url", url)
        pub_date = parsed.get("publication_date", datetime.now(timezone.utc))
        text_hash = parsed.get("text_hash") or hashlib.sha256(body_text.encode('utf-8')).hexdigest()

        # 4. Multi-Tier Duplicate Detection
        is_dupe, dupe_reason = self.dup_detector.check_duplicate(
            self.db, url, canonical_url, text_hash, title, pub_date
        )
        if is_dupe:
            logger.info(f"Skipping duplicate article ({url}): {dupe_reason}")
            return None

        # 5. Language Detection & Text Normalization
        lang = self.lang_detector.detect_language(body_text)
        normalized_text = self.analyzer.normalize_tamil_text(body_text) if lang in ["ta", "mixed"] else body_text
        normalized_title = self.analyzer.normalize_tamil_text(title) if lang in ["ta", "mixed"] else title

        # 6. Database Persistence & Provenance Record
        article_id = f"art_{uuid.uuid4().hex[:10]}"
        article = Article(
            article_id=article_id,
            source_id=source_id,
            url=url,
            canonical_url=canonical_url,
            title=normalized_title,
            author=parsed.get("author", "Staff Reporter"),
            publication_date=pub_date,
            retrieval_date=datetime.now(timezone.utc),
            section=parsed.get("section", "General"),
            language=lang,
            raw_html_path=raw_ref_path,
            article_text=normalized_text,
            word_count=len(normalized_text.split()),
            text_hash=text_hash,
            is_test_fixture=is_test_fixture
        )
        self.db.add(article)

        # Core Provenance: Unified Document and Evidence Records
        common_source = self.db.query(Source).filter(Source.name == source_config.source_name).first()
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
            content=normalized_text[:500],
            explanation="Ingested article record in Phase 4 raw article store.",
            result_type="NewsArticle",
            result_id=article_id
        )
        self.db.add(evidence)

        # 7. Push to Processing Queue
        self.queue_manager.enqueue_article(self.db, article_id)

        self.db.commit()
        self.db.refresh(article)
        logger.info(f"Successfully ingested article {article_id} from {source_id}")
        return article
