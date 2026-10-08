import re
import uuid
import hashlib
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Set, Tuple
from sqlalchemy.orm import Session

from backend.core.logger import setup_logger
from backend.models.news import (
    Article, NewsSource, PoliticalEvent, ArticleEvent, ArticleEntity,
    ArticleTopic, ArticleFeature, BiasIndicator
)
from backend.nlp.intelligence_layer import IntelligenceLayerService

logger = setup_logger("civiclens.services.event_comparison_service")


class EventCandidateDetector:
    """Detects candidate political event clusters from ingested news articles."""

    @staticmethod
    def extract_keywords(text: str) -> Set[str]:
        words = re.findall(r'[\u0B80-\u0BFF\w]{4,}', text.lower())
        return set(words)

    def find_candidates(self, db: Session, days_window: int = 3) -> List[Dict[str, Any]]:
        """Scans recent articles to identify candidate event clusters based on text/entity overlap."""
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_window)
        articles = db.query(Article).filter(Article.publication_date >= cutoff_date).all()

        if not articles:
            return []

        clusters = []
        visited = set()

        for i, art1 in enumerate(articles):
            if art1.article_id in visited:
                continue

            kw1 = self.extract_keywords(art1.title + " " + art1.article_text[:300])
            cluster_arts = [art1]
            visited.add(art1.article_id)

            for j, art2 in enumerate(articles[i+1:], start=i+1):
                if art2.article_id in visited:
                    continue

                kw2 = self.extract_keywords(art2.title + " " + art2.article_text[:300])
                overlap = len(kw1.intersection(kw2))
                union = len(kw1.union(kw2))
                sim = overlap / union if union > 0 else 0.0

                if sim >= 0.25:
                    cluster_arts.append(art2)
                    visited.add(art2.article_id)

            if len(cluster_arts) >= 2:
                clusters.append({
                    "cluster_id": f"cluster_{uuid.uuid4().hex[:8]}",
                    "title_sample": art1.title,
                    "article_count": len(cluster_arts),
                    "article_ids": [a.article_id for a in cluster_arts],
                    "articles": cluster_arts
                })

        return clusters


class EventClusteringEngine:
    """Maps candidate article clusters to ground-truth PoliticalEvent DB records."""

    @staticmethod
    def link_cluster_to_event(db: Session, cluster: Dict[str, Any], event_name: str) -> PoliticalEvent:
        event_id = f"evt_{uuid.uuid4().hex[:10]}"
        pub_date = cluster["articles"][0].publication_date.date() if cluster["articles"][0].publication_date else datetime.now(timezone.utc).date()

        event = db.query(PoliticalEvent).filter(PoliticalEvent.event_name == event_name).first()
        if not event:
            event = PoliticalEvent(
                event_id=event_id,
                event_name=event_name,
                event_date=pub_date,
                description=f"Clustered event: {cluster['title_sample']}"
            )
            db.add(event)
            db.flush()

        for art in cluster["articles"]:
            existing_link = db.query(ArticleEvent).filter(
                ArticleEvent.article_id == art.article_id,
                ArticleEvent.event_id == event.event_id
            ).first()
            if not existing_link:
                link = ArticleEvent(
                    article_id=art.article_id,
                    event_id=event.event_id,
                    relevance_score=1.0,
                    role_in_event="coverage_report"
                )
                db.add(link)

        db.commit()
        db.refresh(event)
        return event


class SourceGroupingEngine:
    """Groups clustered articles covering an event by their parent news source."""

    @staticmethod
    def group_by_source(db: Session, articles: List[Article]) -> Dict[str, List[Article]]:
        grouped = {}
        for art in articles:
            sid = art.source_id
            if sid not in grouped:
                grouped[sid] = []
            grouped[sid].append(art)
        return grouped


class CrossSourceEventComparer:
    """
    Computes multi-dimensional cross-source comparative signals for an event:
    1. Publication timing & reporting speed
    2. Headline differences & word count
    3. Entity mention frequency & prominence breakdown
    4. Topic emphasis distribution
    5. Sentiment & sourcing signals
    6. Omission / presence coverage disparity
    """

    def compare_event_coverage(self, db: Session, event_id: str) -> Dict[str, Any]:
        event = db.query(PoliticalEvent).filter(PoliticalEvent.event_id == event_id).first()
        if not event:
            return {"error": f"Event '{event_id}' not found."}

        links = db.query(ArticleEvent).filter(ArticleEvent.event_id == event_id).all()
        articles = [link.article for link in links if link.article]

        if not articles:
            return {"event_id": event_id, "event_name": event.event_name, "message": "No articles linked to this event."}

        # 1. Group articles by source
        grouped = SourceGroupingEngine.group_by_source(db, articles)
        all_registered_sources = db.query(NewsSource).filter(NewsSource.active_status == "active").all()
        active_source_ids = [s.source_id for s in all_registered_sources]

        source_analyses = {}
        overall_earliest = min((a.publication_date for a in articles if a.publication_date), default=datetime.now(timezone.utc))

        for sid, src_arts in grouped.items():
            src_obj = db.query(NewsSource).filter(NewsSource.source_id == sid).first()
            sname = src_obj.source_name if src_obj else sid

            # Timing
            dates = [a.publication_date for a in src_arts if a.publication_date]
            earliest_src = min(dates) if dates else overall_earliest
            reporting_delay_min = round((earliest_src - overall_earliest).total_seconds() / 60.0, 1)

            # Headlines & Depth
            headlines = [a.title for a in src_arts]
            mean_word_count = round(sum(a.word_count for a in src_arts) / len(src_arts), 1)

            # Entity Prominence Breakdown
            entity_prominence = {}
            for a in src_arts:
                for e in a.entities:
                    eid = e.entity_id
                    if eid not in entity_prominence:
                        entity_prominence[eid] = {"mentions": 0, "prominence_sum": 0.0}
                    entity_prominence[eid]["mentions"] += e.mention_count
                    entity_prominence[eid]["prominence_sum"] += e.prominence_score

            ent_breakdown = {}
            for eid, data in entity_prominence.items():
                ent_breakdown[eid] = {
                    "total_mentions": data["mentions"],
                    "avg_prominence": round(data["prominence_sum"] / len(src_arts), 3)
                }

            # Sentiment & Sourcing Signals
            headline_sentiments = []
            body_sentiments = []
            quote_counts = []
            official_citations = []

            for a in src_arts:
                if a.features:
                    headline_sentiments.append(a.features.headline_sentiment)
                    body_sentiments.append(a.features.body_sentiment)
                    quote_counts.append(a.features.quote_count)
                    official_citations.append(a.features.official_source_citation_count)

            avg_headline_sentiment = round(sum(headline_sentiments) / len(headline_sentiments), 3) if headline_sentiments else 0.0
            avg_body_sentiment = round(sum(body_sentiments) / len(body_sentiments), 3) if body_sentiments else 0.0
            total_quotes = sum(quote_counts)
            total_official_citations = sum(official_citations)

            source_analyses[sid] = {
                "source_id": sid,
                "source_name": sname,
                "article_count": len(src_arts),
                "reporting_delay_minutes": reporting_delay_min,
                "first_published_at": earliest_src.isoformat(),
                "mean_word_count": mean_word_count,
                "headlines": headlines,
                "entity_prominence_breakdown": ent_breakdown,
                "signals": {
                    "avg_headline_sentiment": avg_headline_sentiment,
                    "avg_body_sentiment": avg_body_sentiment,
                    "total_quotes": total_quotes,
                    "total_official_citations": total_official_citations,
                    "official_citation_ratio": round(total_official_citations / max(1, total_quotes + total_official_citations), 2)
                }
            }

        # 2. Compute Disparities & Omissions (Neutral Terminology)
        coverage_disparities = []
        covered_source_ids = set(grouped.keys())

        # Omission / Presence Differential
        for sid in active_source_ids:
            if sid not in covered_source_ids:
                src_obj = db.query(NewsSource).filter(NewsSource.source_id == sid).first()
                sname = src_obj.source_name if src_obj else sid
                coverage_disparities.append({
                    "disparity_type": "coverage_disparity",
                    "source_id": sid,
                    "source_name": sname,
                    "description": f"Coverage disparity: Source '{sname}' did not publish reports on event '{event.event_name}' while rival outlets covered it."
                })

        # Pairwise Entity & Framing Divergence
        source_pairs = list(source_analyses.keys())
        for i in range(len(source_pairs)):
            for j in range(i+1, len(source_pairs)):
                s1 = source_analyses[source_pairs[i]]
                s2 = source_analyses[source_pairs[j]]

                # Entity Emphasis Difference
                ent1 = set(s1["entity_prominence_breakdown"].keys())
                ent2 = set(s2["entity_prominence_breakdown"].keys())

                for eid in ent1.union(ent2):
                    p1 = s1["entity_prominence_breakdown"].get(eid, {}).get("avg_prominence", 0.0)
                    p2 = s2["entity_prominence_breakdown"].get(eid, {}).get("avg_prominence", 0.0)
                    diff = abs(p1 - p2)

                    if diff >= 0.4:
                        coverage_disparities.append({
                            "disparity_type": "entity_emphasis_difference",
                            "source_a": s1["source_name"],
                            "source_b": s2["source_name"],
                            "entity_id": eid,
                            "prominence_a": p1,
                            "prominence_b": p2,
                            "description": f"Entity emphasis difference for '{eid}': {s1['source_name']} (prominence {p1}) vs {s2['source_name']} (prominence {p2})."
                        })

        return {
            "event_id": event.event_id,
            "event_name": event.event_name,
            "event_date": event.event_date.isoformat() if event.event_date else None,
            "total_articles": len(articles),
            "sources_count": len(grouped),
            "source_coverage": source_analyses,
            "coverage_disparities": coverage_disparities
        }


class EventComparisonService:
    """Unified service for candidate detection, clustering, cross-source comparison, and indicator persistence."""

    def __init__(self, db: Session):
        self.db = db
        self.detector = EventCandidateDetector()
        self.clustering = EventClusteringEngine()
        self.comparer = CrossSourceEventComparer()

    def run_event_analysis_pipeline(self) -> List[Dict[str, Any]]:
        """Runs candidate detection, clusters articles into events, and computes comparative signals."""
        clusters = self.detector.find_candidates(self.db)
        results = []

        for cl in clusters:
            event = self.clustering.link_cluster_to_event(self.db, cl, f"Event: {cl['title_sample'][:40]}")
            comp = self.comparer.compare_event_coverage(self.db, event.event_id)

            # Persist neutral bias indicators into DB
            for disp in comp.get("coverage_disparities", []):
                ind_id = f"ind_disp_{uuid.uuid4().hex[:8]}"
                ind = BiasIndicator(
                    indicator_id=ind_id,
                    source_id=disp.get("source_id", "src_multi"),
                    metric_type=disp["disparity_type"],
                    window_start=datetime.now(timezone.utc) - timedelta(days=3),
                    window_end=datetime.now(timezone.utc),
                    indicator_value=1.0,
                    interpretation_label=disp["description"],
                    metadata_json=disp
                )
                self.db.add(ind)

            self.db.commit()
            results.append(comp)

        return results
