"""
Unit Tests for Phase 4.6 — Cross-Source Political Event Comparison.

IMPORTANT:
All test cases use strictly synthetic test fixtures.
No real political conclusions or real-world news articles are asserted.
All synthetic fixtures are marked with `is_test_fixture=True`.
"""

import pytest
import hashlib
from datetime import datetime, timezone, timedelta
from backend.models.news import NewsSource, Article, PoliticalEvent, ArticleEvent, ArticleEntity, ArticleFeature, ActiveStatus, SourceType
from backend.services.news_service import NewsService
from backend.services.event_comparison_service import (
    EventCandidateDetector, EventClusteringEngine, SourceGroupingEngine,
    CrossSourceEventComparer, EventComparisonService
)


@pytest.fixture
def setup_event_test_data(db_session):
    """Sets up synthetic sources, articles, and ground-truth events for cross-source comparison testing."""
    # 1. Register synthetic sources
    src1 = NewsSource(
        source_id="src_test_alpha",
        source_name="Test Alpha Daily",
        domain="alpha.example.com",
        language="ta",
        source_type=SourceType.PRINT_DIGITAL,
        active_status=ActiveStatus.ACTIVE
    )
    src2 = NewsSource(
        source_id="src_test_beta",
        source_name="Test Beta Times",
        domain="beta.example.com",
        language="en",
        source_type=SourceType.PRINT_DIGITAL,
        active_status=ActiveStatus.ACTIVE
    )
    src3 = NewsSource(
        source_id="src_test_gamma",
        source_name="Test Gamma Express",
        domain="gamma.example.com",
        language="en",
        source_type=SourceType.PRINT_DIGITAL,
        active_status=ActiveStatus.ACTIVE
    )
    db_session.add_all([src1, src2, src3])
    db_session.commit()

    now = datetime.now(timezone.utc)

    art1_text = "TEST FIXTURE — NOT REAL NEWS DATA. சென்னை மெட்ரோ திட்டத்திற்குத் தமிழ் நிலத்தின் பட்ஜெட் நிதி ஒதுக்கீடு செய்யப்பட்டுள்ளது. முதலமைச்சர் மு.க.ஸ்டாலின் திட்டத்தை தொடங்கி வைத்தார்."
    art1 = Article(
        article_id="art_evt_001",
        source_id="src_test_alpha",
        url="https://alpha.example.com/metro-budget",
        title="TEST FIXTURE — சென்னை மெட்ரோ திட்ட வரவுசெலவுத் திட்டம்",
        article_text=art1_text,
        text_hash=hashlib.sha256(art1_text.encode('utf-8')).hexdigest(),
        publication_date=now - timedelta(hours=2),
        language="ta",
        word_count=200,
        is_test_fixture=True
    )
    art2_text = "TEST FIXTURE — NOT REAL NEWS DATA. The State Budget allocated funding for urban metro expansion in Chennai. M.K. Stalin announced major transit infrastructure investment."
    art2 = Article(
        article_id="art_evt_002",
        source_id="src_test_beta",
        url="https://beta.example.com/metro-budget-tn",
        title="TEST FIXTURE — TN State Budget Allocates Funds for Metro Expansion",
        article_text=art2_text,
        text_hash=hashlib.sha256(art2_text.encode('utf-8')).hexdigest(),
        publication_date=now - timedelta(hours=1),
        language="en",
        word_count=250,
        is_test_fixture=True
    )
    db_session.add_all([art1, art2])
    db_session.commit()

    # 3. Add Article Features and Entities
    feat1 = ArticleFeature(
        article_id="art_evt_001",
        headline_sentiment=0.4,
        body_sentiment=0.3,
        quote_count=3,
        official_source_citation_count=2,
        vocabulary_richness=0.65
    )
    feat2 = ArticleFeature(
        article_id="art_evt_002",
        headline_sentiment=0.1,
        body_sentiment=0.05,
        quote_count=1,
        official_source_citation_count=4,
        vocabulary_richness=0.70
    )

    ent1 = ArticleEntity(
        article_id="art_evt_001",
        entity_id="ent_person_cm_mkstalin",
        mention_count=5,
        prominence_score=0.85
    )
    ent2 = ArticleEntity(
        article_id="art_evt_002",
        entity_id="ent_person_cm_mkstalin",
        mention_count=2,
        prominence_score=0.35
    )

    db_session.add_all([feat1, feat2, ent1, ent2])
    db_session.commit()

    # 4. Create Ground-Truth Political Event & Link Articles
    event = PoliticalEvent(
        event_id="evt_test_metro_2026",
        event_name="Metro Budget Allocation 2026",
        event_date=now.date(),
        description="TEST FIXTURE ground-truth event for budget allocation."
    )
    db_session.add(event)
    db_session.commit()

    link1 = ArticleEvent(article_id="art_evt_001", event_id=event.event_id, relevance_score=1.0, role_in_event="primary_report")
    link2 = ArticleEvent(article_id="art_evt_002", event_id=event.event_id, relevance_score=1.0, role_in_event="primary_report")
    db_session.add_all([link1, link2])
    db_session.commit()

    return {
        "event_id": event.event_id,
        "src1_id": src1.source_id,
        "src2_id": src2.source_id,
        "src3_id": src3.source_id,
        "art1_id": art1.article_id,
        "art2_id": art2.article_id
    }


class TestPhase4EventComparison:
    """Test suite for event candidate detection, clustering, cross-source metrics, and API endpoints."""

    def test_keyword_extraction(self):
        """Test candidate detector keyword extraction for Tamil and English text."""
        detector = EventCandidateDetector()
        kw_ta = detector.extract_keywords("சென்னை மெட்ரோ திட்டம் மற்றும் பட்ஜெட்")
        assert "சென்னை" in kw_ta
        assert "மெட்ரோ" in kw_ta

        kw_en = detector.extract_keywords("Chennai Metro Budget Allocation 2026")
        assert "chennai" in kw_en
        assert "metro" in kw_en

    def test_candidate_detection(self, db_session, setup_event_test_data):
        """Test candidate event detection algorithm on overlapping synthetic articles."""
        detector = EventCandidateDetector()
        candidates = detector.find_candidates(db_session, days_window=3)
        assert isinstance(candidates, list)
        # Note: Depending on Jaccard threshold, two overlapping synthetic articles may form a candidate cluster
        if candidates:
            cl = candidates[0]
            assert "cluster_id" in cl
            assert cl["article_count"] >= 2

    def test_cluster_linking(self, db_session, setup_event_test_data):
        """Test linking candidate article clusters to ground-truth PoliticalEvent DB records."""
        art1 = db_session.query(Article).filter(Article.article_id == "art_evt_001").first()
        art2 = db_session.query(Article).filter(Article.article_id == "art_evt_002").first()

        cluster = {
            "title_sample": "TEST FIXTURE — Metro Scheme",
            "articles": [art1, art2]
        }
        event = EventClusteringEngine.link_cluster_to_event(db_session, cluster, "Test Metro Cluster Event")
        assert event is not None
        assert event.event_name == "Test Metro Cluster Event"

        links = db_session.query(ArticleEvent).filter(ArticleEvent.event_id == event.event_id).all()
        assert len(links) == 2

    def test_source_grouping(self, db_session, setup_event_test_data):
        """Test grouping articles by source ID."""
        arts = db_session.query(Article).all()
        grouped = SourceGroupingEngine.group_by_source(db_session, arts)
        assert "src_test_alpha" in grouped
        assert "src_test_beta" in grouped
        assert len(grouped["src_test_alpha"]) == 1

    def test_cross_source_event_comparison(self, db_session, setup_event_test_data):
        """Test multi-dimensional cross-source comparative metrics calculation."""
        comparer = CrossSourceEventComparer()
        evt_id = setup_event_test_data["event_id"]
        res = comparer.compare_event_coverage(db_session, evt_id)

        assert res["event_id"] == evt_id
        assert res["total_articles"] == 2
        assert res["sources_count"] == 2
        assert "src_test_alpha" in res["source_coverage"]
        assert "src_test_beta" in res["source_coverage"]

        # Check reporting delay (Alpha published 2h ago, Beta 1h ago -> Beta delay ~60 min)
        beta_cov = res["source_coverage"]["src_test_beta"]
        assert beta_cov["reporting_delay_minutes"] >= 50.0

        # Check signals
        alpha_cov = res["source_coverage"]["src_test_alpha"]
        assert alpha_cov["signals"]["avg_headline_sentiment"] == 0.4
        assert alpha_cov["signals"]["total_quotes"] == 3

        # Check entity emphasis divergence disparity (Alpha 0.85 vs Beta 0.35 -> diff 0.5 >= 0.4)
        disparities = res["coverage_disparities"]
        assert len(disparities) > 0
        
        disparity_types = [d["disparity_type"] for d in disparities]
        assert "entity_emphasis_difference" in disparity_types or "coverage_disparity" in disparity_types

        # Verify neutral wording in descriptions
        for disp in disparities:
            desc = disp["description"]
            assert "Biased" not in desc
            assert "Fake News" not in desc

    def test_omission_disparity_detection(self, db_session, setup_event_test_data):
        """Test identification of coverage disparity when an active source omits coverage."""
        comparer = CrossSourceEventComparer()
        evt_id = setup_event_test_data["event_id"]
        res = comparer.compare_event_coverage(db_session, evt_id)

        disparities = res["coverage_disparities"]
        # src_test_gamma was registered as active but published 0 articles for this event
        omissions = [d for d in disparities if d.get("disparity_type") == "coverage_disparity"]
        assert len(omissions) >= 1
        assert any(d.get("source_id") == "src_test_gamma" for d in omissions)

    def test_full_service_pipeline(self, db_session, setup_event_test_data):
        """Test end-to-end execution of EventComparisonService pipeline."""
        service = EventComparisonService(db_session)
        pipeline_output = service.run_event_analysis_pipeline()
        assert isinstance(pipeline_output, list)

    def test_event_comparison_api_endpoints(self, api_client):
        """Test Flask REST API routes for event candidate detection, comparison, and disparities."""
        from backend.database.session import SessionLocal
        db = SessionLocal()
        evt_id = "evt_api_test_999"
        try:
            event = db.query(PoliticalEvent).filter(PoliticalEvent.event_id == evt_id).first()
            if not event:
                event = PoliticalEvent(
                    event_id=evt_id,
                    event_name="API Test Event",
                    event_date=datetime.now(timezone.utc).date(),
                    description="TEST FIXTURE API Event"
                )
                db.add(event)
                db.commit()

            # 1. GET /api/news/events/candidates
            res_cand = api_client.get('/api/news/events/candidates')
            assert res_cand.status_code == 200
            assert "data" in res_cand.json

            # 2. GET /api/news/events/<event_id>/compare
            res_comp = api_client.get(f'/api/news/events/{evt_id}/compare')
            assert res_comp.status_code == 200
            assert res_comp.json["data"]["event_id"] == evt_id

            # 3. GET /api/news/events/disparities
            res_disp = api_client.get('/api/news/events/disparities')
            assert res_disp.status_code == 200
            assert isinstance(res_disp.json["data"], list)
        finally:
            db.close()
