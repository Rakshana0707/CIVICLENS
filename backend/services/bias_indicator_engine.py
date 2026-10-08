"""
Phase 4.7 — Multi-Dimensional News Bias & Coverage Indicator Engine.

IMPORTANT:
This engine does NOT generate a scalar "bias score" or infer political bias intent.
Instead, it calculates 12 independent, reproducible, multi-dimensional indicators,
normalized distributions, and statistical confidence bounds using neutral terminology.
"""

import math
import uuid
import re
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Set, Tuple
from sqlalchemy.orm import Session

from backend.core.logger import setup_logger
from backend.models.news import (
    Article, NewsSource, PoliticalEvent, ArticleEvent, ArticleEntity,
    ArticleTopic, ArticleFeature, BiasIndicator, CoverageMetric, SourceComparison
)

logger = setup_logger("civiclens.services.bias_indicator_engine")

METHODOLOGY_VERSION = "v1.0"
CALCULATION_VERSION = "v1.0"
MINIMUM_SAMPLE_SIZE = 5


class MultiDimensionalBiasCalculator:
    """Calculates 12 multi-dimensional, reproducible statistical indicators for a news source."""

    @staticmethod
    def calculate_confidence(sample_size: int) -> float:
        """Calculates statistical confidence based on sample size bounds."""
        if sample_size <= 0:
            return 0.0
        if sample_size < MINIMUM_SAMPLE_SIZE:
            return round(sample_size / float(MINIMUM_SAMPLE_SIZE), 2)
        return 1.0

    def compute_all_indicators(self, db: Session, source_id: str, days_window: int = 30) -> Dict[str, Any]:
        """Computes all 12 indicators for a news source over a specified time window."""
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_window)
        articles = db.query(Article).filter(
            Article.source_id == source_id,
            Article.created_at >= cutoff_date
        ).all()

        n = len(articles)
        conf = self.calculate_confidence(n)

        if n == 0:
            return {
                "source_id": source_id,
                "sample_size": 0,
                "confidence": 0.0,
                "indicators": {},
                "message": "Insufficient articles in time window to compute indicators."
            }

        # Collect linguistic features
        features = [a.features for a in articles if a.features]
        headline_sents = [f.headline_sentiment for f in features if f.headline_sentiment is not None]
        body_sents = [f.body_sentiment for f in features if f.body_sentiment is not None]
        quote_counts = [f.quote_count for f in features if f.quote_count is not None]
        official_citations = [f.official_source_citation_count for f in features if f.official_source_citation_count is not None]

        # 1. Sentiment Distribution
        all_sents = body_sents if body_sents else [0.0]
        pos_cnt = sum(1 for s in all_sents if s > 0.1)
        neu_cnt = sum(1 for s in all_sents if -0.1 <= s <= 0.1)
        neg_cnt = sum(1 for s in all_sents if s < -0.1)
        sent_dist = {
            "positive_ratio": round(pos_cnt / float(len(all_sents)), 3),
            "neutral_ratio": round(neu_cnt / float(len(all_sents)), 3),
            "negative_ratio": round(neg_cnt / float(len(all_sents)), 3),
            "mean": round(sum(all_sents) / len(all_sents), 3)
        }

        # 2. Headline Sentiment
        hl_sents = headline_sents if headline_sents else [0.0]
        hl_dist = {
            "positive_ratio": round(sum(1 for s in hl_sents if s > 0.1) / float(len(hl_sents)), 3),
            "neutral_ratio": round(sum(1 for s in hl_sents if -0.1 <= s <= 0.1) / float(len(hl_sents)), 3),
            "negative_ratio": round(sum(1 for s in hl_sents if s < -0.1) / float(len(hl_sents)), 3),
            "mean": round(sum(hl_sents) / len(hl_sents), 3)
        }

        # 3. Article Sentiment
        art_dist = sent_dist  # reuse body sentiment distribution

        # 4 & 5. Entity Prominence & Mention Frequency
        entity_stats = {}
        total_entity_mentions = 0
        for a in articles:
            for e in a.entities:
                eid = e.entity_id
                if eid not in entity_stats:
                    entity_stats[eid] = {"mentions": 0, "prominence_sum": 0.0}
                entity_stats[eid]["mentions"] += e.mention_count
                entity_stats[eid]["prominence_sum"] += e.prominence_score
                total_entity_mentions += e.mention_count

        ent_prominence = {}
        ent_frequency = {}
        for eid, stats in entity_stats.items():
            ent_prominence[eid] = round(stats["prominence_sum"] / float(n), 3)
            ent_frequency[eid] = {
                "raw_mentions": stats["mentions"],
                "normalized_ratio": round(stats["mentions"] / float(max(1, total_entity_mentions)), 3)
            }

        # 6. Topic Emphasis Distribution
        topic_counts = {}
        for a in articles:
            for t in a.topics:
                tcode = t.topic_id
                topic_counts[tcode] = topic_counts.get(tcode, 0) + 1

        total_topics = sum(topic_counts.values())
        topic_emphasis = {}
        for tcode, cnt in topic_counts.items():
            topic_emphasis[tcode] = round(cnt / float(max(1, total_topics)), 3)

        # 7. Event Coverage Frequency
        total_events = db.query(PoliticalEvent).count()
        covered_events_count = db.query(ArticleEvent.event_id).join(Article).filter(Article.source_id == source_id).distinct().count()
        event_coverage_freq = {
            "total_tracked_events": total_events,
            "events_covered": covered_events_count,
            "coverage_ratio": round(covered_events_count / float(max(1, total_events)), 3)
        }

        # 8. Positive / Negative Framing Distribution
        pos_framing = sum(1 for f in features if f.headline_sentiment > 0.1 or f.body_sentiment > 0.1)
        neg_framing = sum(1 for f in features if f.headline_sentiment < -0.1 or f.body_sentiment < -0.1)
        neu_framing = len(features) - pos_framing - neg_framing
        n_feat = max(1, len(features))
        framing_dist = {
            "positive_framing_pct": round((pos_framing / float(n_feat)) * 100.0, 1),
            "negative_framing_pct": round((neg_framing / float(n_feat)) * 100.0, 1),
            "balanced_framing_pct": round((neu_framing / float(n_feat)) * 100.0, 1)
        }

        # 9. Quote Distribution
        tot_quotes = sum(quote_counts)
        quote_dist = {
            "mean_quotes_per_article": round(tot_quotes / float(n), 2),
            "total_quotes": tot_quotes
        }

        # 10. Source-Reference Distribution
        tot_citations = sum(official_citations)
        denom = max(1, tot_quotes + tot_citations)
        sourcing_dist = {
            "total_official_citations": tot_citations,
            "official_citation_ratio": round(tot_citations / float(denom), 3),
            "quote_to_citation_ratio": round(tot_quotes / float(max(1, tot_citations)), 2)
        }

        # 11 & 12. Placeholder defaults for single source (populated in pairwise comparison)
        wording_sim = {"note": "Requires pairwise outlet comparison"}
        coverage_diff = {"note": "Requires pairwise outlet comparison"}

        return {
            "source_id": source_id,
            "sample_size": n,
            "statistical_confidence": conf,
            "methodology_version": METHODOLOGY_VERSION,
            "calculation_version": CALCULATION_VERSION,
            "indicators": {
                "sentiment_distribution": sent_dist,
                "headline_sentiment": hl_dist,
                "article_sentiment": art_dist,
                "entity_prominence": ent_prominence,
                "entity_mention_frequency": ent_frequency,
                "topic_emphasis": topic_emphasis,
                "event_coverage_frequency": event_coverage_freq,
                "framing_distribution": framing_dist,
                "quote_distribution": quote_dist,
                "sourcing_reference_distribution": sourcing_dist,
                "wording_similarity": wording_sim,
                "coverage_difference": coverage_diff
            }
        }


class PairwiseSourceComparer:
    """Computes reproducible pairwise comparisons between two news sources."""

    @staticmethod
    def extract_words(text: str) -> Set[str]:
        return set(re.findall(r'[\u0B80-\u0BFF\w]{4,}', text.lower()))

    def compare_sources(self, db: Session, source_a_id: str, source_b_id: str, days_window: int = 30) -> Dict[str, Any]:
        calculator = MultiDimensionalBiasCalculator()
        res_a = calculator.compute_all_indicators(db, source_a_id, days_window)
        res_b = calculator.compute_all_indicators(db, source_b_id, days_window)

        cutoff = datetime.now(timezone.utc) - timedelta(days=days_window)
        arts_a = db.query(Article).filter(Article.source_id == source_a_id, Article.created_at >= cutoff).all()
        arts_b = db.query(Article).filter(Article.source_id == source_b_id, Article.created_at >= cutoff).all()

        # 11. Cross-Source Wording Similarity (Jaccard Overlap across headlines & texts)
        words_a = set()
        for a in arts_a:
            words_a.update(self.extract_words(a.title + " " + a.article_text[:300]))

        words_b = set()
        for b in arts_b:
            words_b.update(self.extract_words(b.title + " " + b.article_text[:300]))

        overlap = len(words_a.intersection(words_b))
        union = len(words_a.union(words_b))
        jaccard_sim = round(overlap / float(union), 3) if union > 0 else 0.0

        # Topic emphasis divergence
        top_a = res_a.get("indicators", {}).get("topic_emphasis", {})
        top_b = res_b.get("indicators", {}).get("topic_emphasis", {})
        all_topics = set(top_a.keys()).union(set(top_b.keys()))
        topic_div = round(sum(abs(top_a.get(t, 0.0) - top_b.get(t, 0.0)) for t in all_topics) / 2.0, 3) if all_topics else 0.0

        # Entity prominence divergence
        ent_a = res_a.get("indicators", {}).get("entity_prominence", {})
        ent_b = res_b.get("indicators", {}).get("entity_prominence", {})
        all_ents = set(ent_a.keys()).union(set(ent_b.keys()))
        ent_div = round(sum(abs(ent_a.get(e, 0.0) - ent_b.get(e, 0.0)) for e in all_ents) / float(max(1, len(all_ents))), 3) if all_ents else 0.0

        # Framing divergence
        frame_a = res_a.get("indicators", {}).get("framing_distribution", {})
        frame_b = res_b.get("indicators", {}).get("framing_distribution", {})
        pos_diff = abs(frame_a.get("positive_framing_pct", 0.0) - frame_b.get("positive_framing_pct", 0.0))
        neg_diff = abs(frame_a.get("negative_framing_pct", 0.0) - frame_b.get("negative_framing_pct", 0.0))
        framing_div = round((pos_diff + neg_diff) / 200.0, 3)

        # 12. Coverage Differences (Event presence / omission disparity)
        cov_a = set(link.event_id for link in db.query(ArticleEvent.event_id).join(Article).filter(Article.source_id == source_a_id).all())
        cov_b = set(link.event_id for link in db.query(ArticleEvent.event_id).join(Article).filter(Article.source_id == source_b_id).all())
        
        shared_events = len(cov_a.intersection(cov_b))
        total_unique_events = len(cov_a.union(cov_b))
        coverage_diff_score = round(1.0 - (shared_events / float(max(1, total_unique_events))), 3)

        return {
            "source_a_id": source_a_id,
            "source_b_id": source_b_id,
            "window_days": days_window,
            "methodology_version": METHODOLOGY_VERSION,
            "calculation_version": CALCULATION_VERSION,
            "wording_similarity_score": jaccard_sim,
            "topic_emphasis_divergence": topic_div,
            "entity_prominence_divergence": ent_div,
            "framing_divergence": framing_div,
            "coverage_difference_score": coverage_diff_score,
            "normalized_comparisons": {
                "source_a": {
                    "positive_framing_pct": frame_a.get("positive_framing_pct", 0.0),
                    "negative_framing_pct": frame_a.get("negative_framing_pct", 0.0),
                    "balanced_framing_pct": frame_a.get("balanced_framing_pct", 0.0)
                },
                "source_b": {
                    "positive_framing_pct": frame_b.get("positive_framing_pct", 0.0),
                    "negative_framing_pct": frame_b.get("negative_framing_pct", 0.0),
                    "balanced_framing_pct": frame_b.get("balanced_framing_pct", 0.0)
                }
            }
        }


class BiasIndicatorEngine:
    """Unified service for computing, persisting, and querying multi-dimensional bias indicators and comparisons."""

    def __init__(self, db: Session):
        self.db = db
        self.calculator = MultiDimensionalBiasCalculator()
        self.comparer = PairwiseSourceComparer()

    def generate_and_persist_source_indicators(self, source_id: str, days_window: int = 30) -> List[BiasIndicator]:
        """Calculates 12 multi-dimensional indicators for a source and persists them to the DB."""
        results = self.calculator.compute_all_indicators(self.db, source_id, days_window)
        if "error" in results or results.get("sample_size", 0) == 0:
            return []

        now = datetime.now(timezone.utc)
        win_start = now - timedelta(days=days_window)
        indicators = []

        # Store indicators into DB
        for metric_key, val in results.get("indicators", {}).items():
            ind_id = f"ind_{source_id}_{metric_key}_{uuid.uuid4().hex[:6]}"
            label = f"Multi-dimensional indicator: {metric_key} distribution for source {source_id}"
            
            # Represent numeric value for main field
            numeric_val = val.get("positive_ratio", val.get("coverage_ratio", val.get("mean_quotes_per_article", 1.0))) if isinstance(val, dict) else float(val)

            ind = BiasIndicator(
                indicator_id=ind_id,
                source_id=source_id,
                metric_type=metric_key,
                window_start=win_start,
                window_end=now,
                indicator_value=numeric_val,
                statistical_confidence=results["statistical_confidence"],
                interpretation_label=label,
                methodology_version=METHODOLOGY_VERSION,
                calculation_version=CALCULATION_VERSION,
                metadata_json=val
            )
            self.db.add(ind)
            indicators.append(ind)

        # Also store CoverageMetric for topic emphasis summary
        cov_id = f"cov_{source_id}_{datetime.now(timezone.utc).strftime('%Y-%W')}"
        existing_cov = self.db.query(CoverageMetric).filter(CoverageMetric.metric_id == cov_id).first()
        if not existing_cov:
            cov = CoverageMetric(
                metric_id=cov_id,
                source_id=source_id,
                time_period=datetime.now(timezone.utc).strftime("%Y-W%W"),
                total_articles=results["sample_size"],
                article_frequency=round(results["sample_size"] / float(max(1, days_window)), 2),
                avg_prominence=0.5,
                avg_sentiment=results["indicators"]["sentiment_distribution"].get("mean", 0.0),
                methodology_version=METHODOLOGY_VERSION,
                calculation_version=CALCULATION_VERSION,
                metric_data=results["indicators"]
            )
            self.db.add(cov)

        self.db.commit()
        return indicators

    def generate_and_persist_comparison(self, source_a_id: str, source_b_id: str, days_window: int = 30) -> SourceComparison:
        """Calculates pairwise comparison metrics between two sources and persists a SourceComparison record."""
        comp_data = self.comparer.compare_sources(self.db, source_a_id, source_b_id, days_window)
        now = datetime.now(timezone.utc)
        win_start = now - timedelta(days=days_window)

        comp_id = f"sc_{source_a_id}_{source_b_id}_{uuid.uuid4().hex[:6]}"
        record = SourceComparison(
            comparison_id=comp_id,
            source_a_id=source_a_id,
            source_b_id=source_b_id,
            window_start=win_start,
            window_end=now,
            wording_similarity_score=comp_data["wording_similarity_score"],
            topic_emphasis_divergence=comp_data["topic_emphasis_divergence"],
            entity_prominence_divergence=comp_data["entity_prominence_divergence"],
            framing_divergence=comp_data["framing_divergence"],
            coverage_difference_score=comp_data["coverage_difference_score"],
            methodology_version=METHODOLOGY_VERSION,
            calculation_version=CALCULATION_VERSION,
            comparison_data=comp_data
        )
        self.db.add(record)
        self.db.commit()
        self.db.refresh(record)
        return record
