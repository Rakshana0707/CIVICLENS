"""
Unit Tests for Phase 4.7 — Multi-Dimensional News Bias Indicator Engine.

IMPORTANT:
All test cases use strictly synthetic test fixtures tagged with `is_test_fixture=True`.
No real political conclusions or real-world bias claims are asserted.
"""

import pytest
import hashlib
from datetime import datetime, timezone, timedelta
from backend.models.news import (
    NewsSource, Article, PoliticalEvent, ArticleEvent, ArticleEntity,
    ArticleTopic, ArticleFeature, ActiveStatus, SourceType,
    BiasIndicator, CoverageMetric, SourceComparison
)
from backend.services.bias_indicator_engine import (
    MultiDimensionalBiasCalculator, PairwiseSourceComparer, BiasIndicatorEngine,
    METHODOLOGY_VERSION, CALCULATION_VERSION
)


@pytest.fixture
def setup_bias_engine_fixtures(db_session):
    """Sets up synthetic sources, articles, features, and topics for multi-dimensional analysis testing."""
    now = datetime.now(timezone.utc)

    # 1. Sources
    src_a = NewsSource(
        source_id="src_bias_alpha",
        source_name="Synthetic Alpha Post",
        domain="alpha-bias.example.com",
        language="ta",
        source_type=SourceType.PRINT_DIGITAL,
        active_status=ActiveStatus.ACTIVE
    )
    src_b = NewsSource(
        source_id="src_bias_beta",
        source_name="Synthetic Beta Chronicle",
        domain="beta-bias.example.com",
        language="en",
        source_type=SourceType.DIGITAL_NATIVE,
        active_status=ActiveStatus.ACTIVE
    )
    db_session.add_all([src_a, src_b])
    db_session.commit()

    # 2. Articles for Source A (5 articles for full confidence)
    arts_a = []
    for i in range(5):
        t = f"TEST FIXTURE — Alpha Metro Scheme Article {i+1}"
        text = f"TEST FIXTURE — NOT REAL NEWS DATA. சென்னை மெட்ரோ திட்டப் பணிகள் தொடர்கின்றன. மு.க.ஸ்டாலின் அறிக்கை வெளியிட்டார் {i+1}."
        art = Article(
            article_id=f"art_alpha_{i+1}",
            source_id="src_bias_alpha",
            url=f"https://alpha-bias.example.com/news/{i+1}",
            title=t,
            article_text=text,
            text_hash=hashlib.sha256(text.encode('utf-8')).hexdigest(),
            publication_date=now - timedelta(days=i),
            language="ta",
            word_count=180,
            is_test_fixture=True
        )
        arts_a.append(art)

    # 3. Articles for Source B (3 articles for low sample confidence)
    arts_b = []
    for i in range(3):
        t = f"TEST FIXTURE — Beta Urban Transit News {i+1}"
        text = f"TEST FIXTURE — NOT REAL NEWS DATA. Urban transit infrastructure updates for Chennai budget plans {i+1}."
        art = Article(
            article_id=f"art_beta_{i+1}",
            source_id="src_bias_beta",
            url=f"https://beta-bias.example.com/news/{i+1}",
            title=t,
            article_text=text,
            text_hash=hashlib.sha256(text.encode('utf-8')).hexdigest(),
            publication_date=now - timedelta(days=i),
            language="en",
            word_count=220,
            is_test_fixture=True
        )
        arts_b.append(art)

    db_session.add_all(arts_a + arts_b)
    db_session.commit()

    # 4. Attach Features & Entities
    for i, a in enumerate(arts_a):
        feat = ArticleFeature(
            article_id=a.article_id,
            headline_sentiment=0.3 if i % 2 == 0 else -0.2,
            body_sentiment=0.2 if i % 2 == 0 else -0.1,
            quote_count=2 + i,
            official_source_citation_count=1 + i,
            vocabulary_richness=0.60
        )
        ent = ArticleEntity(
            article_id=a.article_id,
            entity_id="ent_person_cm_mkstalin",
            mention_count=3,
            prominence_score=0.75
        )
        top = ArticleTopic(
            article_id=a.article_id,
            topic_id="TOPIC_INFRASTRUCTURE",
            relevance_score=0.9
        )
        db_session.add_all([feat, ent, top])

    for i, b in enumerate(arts_b):
        feat = ArticleFeature(
            article_id=b.article_id,
            headline_sentiment=-0.3,
            body_sentiment=-0.2,
            quote_count=1,
            official_source_citation_count=4,
            vocabulary_richness=0.72
        )
        top = ArticleTopic(
            article_id=b.article_id,
            topic_id="TOPIC_BUDGET_ECONOMY",
            relevance_score=0.85
        )
        db_session.add_all([feat, top])

    db_session.commit()

    return {
        "src_a": src_a.source_id,
        "src_b": src_b.source_id
    }


class TestPhase4BiasIndicatorEngine:
    """Test suite for Phase 4.7 Multi-Dimensional News Bias Indicator Engine."""

    def test_12_indicators_calculation(self, db_session, setup_bias_engine_fixtures):
        """Test calculation of all 12 independent multi-dimensional statistical indicators."""
        calc = MultiDimensionalBiasCalculator()
        src_a = setup_bias_engine_fixtures["src_a"]
        res = calc.compute_all_indicators(db_session, src_a, days_window=30)

        assert res["source_id"] == src_a
        assert res["sample_size"] == 5
        assert res["statistical_confidence"] == 1.0
        assert res["methodology_version"] == METHODOLOGY_VERSION
        assert res["calculation_version"] == CALCULATION_VERSION

        inds = res["indicators"]

        # 1. Sentiment distribution
        assert "sentiment_distribution" in inds
        assert "positive_ratio" in inds["sentiment_distribution"]

        # 2. Headline sentiment
        assert "headline_sentiment" in inds

        # 3. Article sentiment
        assert "article_sentiment" in inds

        # 4 & 5. Entity prominence and frequency
        assert "entity_prominence" in inds
        assert "entity_mention_frequency" in inds

        # 6. Topic emphasis
        assert "topic_emphasis" in inds

        # 7. Event coverage frequency
        assert "event_coverage_frequency" in inds

        # 8. Framing distribution
        assert "framing_distribution" in inds
        assert "positive_framing_pct" in inds["framing_distribution"]

        # 9. Quote distribution
        assert "quote_distribution" in inds

        # 10. Sourcing reference distribution
        assert "sourcing_reference_distribution" in inds
        assert "official_citation_ratio" in inds["sourcing_reference_distribution"]

        # 11 & 12. Cross-source wording & coverage diff placeholders
        assert "wording_similarity" in inds
        assert "coverage_difference" in inds

    def test_confidence_bounds_on_small_samples(self, db_session, setup_bias_engine_fixtures):
        """Test statistical confidence scaling when article sample size N < 5."""
        calc = MultiDimensionalBiasCalculator()
        src_b = setup_bias_engine_fixtures["src_b"]
        res = calc.compute_all_indicators(db_session, src_b, days_window=30)

        assert res["sample_size"] == 3
        assert res["statistical_confidence"] == 0.6  # 3/5

    def test_pairwise_source_comparison(self, db_session, setup_bias_engine_fixtures):
        """Test pairwise source comparison including normalized framing % and wording similarity."""
        comparer = PairwiseSourceComparer()
        src_a = setup_bias_engine_fixtures["src_a"]
        src_b = setup_bias_engine_fixtures["src_b"]

        comp = comparer.compare_sources(db_session, src_a, src_b, days_window=30)

        assert comp["source_a_id"] == src_a
        assert comp["source_b_id"] == src_b
        assert "wording_similarity_score" in comp
        assert "framing_divergence" in comp
        assert "normalized_comparisons" in comp
        assert "positive_framing_pct" in comp["normalized_comparisons"]["source_a"]

    def test_persistence_engine(self, db_session, setup_bias_engine_fixtures):
        """Test persisting BiasIndicator, CoverageMetric, and SourceComparison records with version tracking."""
        engine = BiasIndicatorEngine(db_session)
        src_a = setup_bias_engine_fixtures["src_a"]
        src_b = setup_bias_engine_fixtures["src_b"]

        # Persist indicators
        indicators = engine.generate_and_persist_source_indicators(src_a, days_window=30)
        assert len(indicators) > 0
        for ind in indicators:
            assert ind.methodology_version == METHODOLOGY_VERSION
            assert ind.calculation_version == CALCULATION_VERSION
            assert "Biased" not in ind.interpretation_label

        # Persist comparison
        comp_rec = engine.generate_and_persist_comparison(src_a, src_b, days_window=30)
        assert comp_rec is not None
        assert comp_rec.methodology_version == METHODOLOGY_VERSION
        assert comp_rec.calculation_version == CALCULATION_VERSION

    def test_bias_indicator_api_endpoints(self, api_client):
        """Test Flask REST API routes for calculating indicators, fetching coverage metrics, and comparisons."""
        from backend.database.session import SessionLocal
        db = SessionLocal()
        try:
            # Register a source for API calculation test
            src = NewsSource(
                source_id="src_api_calc_test",
                source_name="API Calc Test Source",
                domain="api-calc.example.com",
                language="en",
                source_type=SourceType.DIGITAL_NATIVE,
                active_status=ActiveStatus.ACTIVE
            )
            db.add(src)
            db.commit()

            now = datetime.now(timezone.utc)
            for i in range(2):
                art_t = f"TEST FIXTURE API Article {i}"
                art = Article(
                    article_id=f"art_api_calc_{i}",
                    source_id="src_api_calc_test",
                    url=f"https://api-calc.example.com/news-{i}",
                    title=art_t,
                    article_text=art_t,
                    text_hash=hashlib.sha256(art_t.encode('utf-8')).hexdigest(),
                    publication_date=now,
                    is_test_fixture=True
                )
                db.add(art)
            db.commit()

            # 1. POST /api/news/indicators/calculate
            res_calc = api_client.post('/api/news/indicators/calculate', json={"source_id": "src_api_calc_test", "days_window": 30})
            assert res_calc.status_code == 200
            assert len(res_calc.json["data"]) > 0

            # 2. GET /api/news/metrics/coverage
            res_cov = api_client.get('/api/news/metrics/coverage')
            assert res_cov.status_code == 200

            # 3. GET /api/news/comparisons
            res_comp = api_client.get('/api/news/comparisons')
            assert res_comp.status_code == 200

        finally:
            db.close()
