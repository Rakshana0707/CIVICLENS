"""
Unit & Integration Tests for Phase 4.8 — News Analysis Database and API Integration.

IMPORTANT:
All test cases use synthetic test fixtures tagged with `is_test_fixture=True`.
No real political conclusions or unverified claims are asserted.
"""

import pytest
import hashlib
from datetime import datetime, timezone, timedelta
from backend.database.session import SessionLocal
from backend.models.news import (
    NewsSource, Article, Topic, PoliticalEntity, PoliticalPerson, PoliticalParty,
    GovernmentDepartment, PoliticalEvent, ArticleEntity, ArticleTopic,
    ArticleEvent, ArticleFeature, CoverageMetric, BiasIndicator, SourceComparison,
    ActiveStatus, SourceType
)
from backend.models.common import Document, Evidence


@pytest.fixture
def setup_api_database_fixtures():
    """Sets up synthetic news sources, articles, entities, topics, events, features, and provenance records."""
    db = SessionLocal()
    now = datetime.now(timezone.utc)
    try:
        # 1. Sources
        src1 = db.query(NewsSource).filter(NewsSource.source_id == "src_api_phase48_ta").first()
        if not src1:
            src1 = NewsSource(
                source_id="src_api_phase48_ta",
                source_name="Phase48 Tamil Daily",
                domain="p48ta.example.com",
                language="ta",
                source_type=SourceType.PRINT_DIGITAL,
                active_status=ActiveStatus.ACTIVE
            )
            db.add(src1)

        src2 = db.query(NewsSource).filter(NewsSource.source_id == "src_api_phase48_en").first()
        if not src2:
            src2 = NewsSource(
                source_id="src_api_phase48_en",
                source_name="Phase48 English Times",
                domain="p48en.example.com",
                language="en",
                source_type=SourceType.DIGITAL_NATIVE,
                active_status=ActiveStatus.ACTIVE
            )
            db.add(src2)
        db.commit()

        # 2. Topic
        top = db.query(Topic).filter(Topic.topic_id == "TOPIC_P48_GOVERNANCE").first()
        if not top:
            top = Topic(
                topic_id="TOPIC_P48_GOVERNANCE",
                topic_code="TOPIC_P48_GOVERNANCE",
                topic_name="Governance & State Policy",
                description="TEST FIXTURE Policy Area"
            )
            db.add(top)
            db.commit()

        # 3. Entity
        ent = db.query(PoliticalEntity).filter(PoliticalEntity.entity_id == "ent_p48_leader").first()
        if not ent:
            ent = PoliticalEntity(
                entity_id="ent_p48_leader",
                entity_type="person",
                name="Phase48 State Leader",
                normalized_name="Phase48 State Leader"
            )
            db.add(ent)
            db.commit()

        # 4. Event
        evt = db.query(PoliticalEvent).filter(PoliticalEvent.event_id == "evt_p48_assembly_session").first()
        if not evt:
            evt = PoliticalEvent(
                event_id="evt_p48_assembly_session",
                event_name="Phase48 Assembly Legislative Session",
                event_date=now.date(),
                description="TEST FIXTURE Assembly session."
            )
            db.add(evt)
            db.commit()

        # 5. Articles
        art1_text = "TEST FIXTURE — NOT REAL NEWS DATA. தமிழ் நிலத்தின் பட்ஜெட் சட்டப்பேரவைக் கூட்டம் நடைபெற்றது."
        art1 = db.query(Article).filter(Article.article_id == "art_p48_001").first()
        if not art1:
            art1 = Article(
                article_id="art_p48_001",
                source_id="src_api_phase48_ta",
                url="https://p48ta.example.com/assembly-news-1",
                canonical_url="https://p48ta.example.com/assembly-news-1",
                title="TEST FIXTURE — சட்டமன்றத் தகவல்கள்",
                article_text=art1_text,
                text_hash=hashlib.sha256(art1_text.encode('utf-8')).hexdigest(),
                publication_date=now - timedelta(hours=3),
                language="ta",
                word_count=150,
                is_test_fixture=True
            )
            db.add(art1)
            db.commit()

            # Attach Relationships & Features
            db.add(ArticleTopic(article_id="art_p48_001", topic_id="TOPIC_P48_GOVERNANCE", relevance_score=0.95))
            db.add(ArticleEntity(article_id="art_p48_001", entity_id="ent_p48_leader", mention_count=4, prominence_score=0.85))
            db.add(ArticleEvent(article_id="art_p48_001", event_id="evt_p48_assembly_session", relevance_score=1.0))
            db.add(ArticleFeature(
                article_id="art_p48_001",
                headline_sentiment=0.2,
                body_sentiment=0.1,
                quote_count=2,
                official_source_citation_count=3
            ))
            db.commit()

        # 6. Provenance Document & Evidence Links
        doc = db.query(Document).filter(Document.title == "TEST FIXTURE — சட்டமன்றத் தகவல்கள்").first()
        if not doc:
            doc = Document(
                title="TEST FIXTURE — சட்டமன்றத் தகவல்கள்",
                content=art1_text,
                url="https://p48ta.example.com/assembly-news-1"
            )
            db.add(doc)
            db.commit()

            evidence = Evidence(
                document_id=doc.id,
                content="TEST FIXTURE extracted claim text",
                result_id="art_p48_001"
            )
            db.add(evidence)
            db.commit()

        return {
            "source_ta": "src_api_phase48_ta",
            "source_en": "src_api_phase48_en",
            "article_id": "art_p48_001",
            "topic_id": "TOPIC_P48_GOVERNANCE",
            "entity_id": "ent_p48_leader",
            "event_id": "evt_p48_assembly_session"
        }
    finally:
        db.close()


class TestPhase4DatabaseAndAPI:
    """Comprehensive test suite for Phase 4.8 Database Models & REST API Endpoints."""

    def test_sources_api_and_filters(self, api_client, setup_api_database_fixtures):
        """Test GET /api/news/sources with language, source_type, and active_status filters."""
        # Unfiltered list
        res = api_client.get('/api/news/sources')
        assert res.status_code == 200
        assert len(res.json["data"]) >= 2

        # Language filter
        res_ta = api_client.get('/api/news/sources?language=ta')
        assert res_ta.status_code == 200
        assert all(s["language"] == "ta" for s in res_ta.json["data"])

    def test_register_source_post(self, api_client):
        """Test POST /api/news/sources endpoint."""
        payload = {
            "source_id": "src_post_test_999",
            "source_name": "POST Test Publisher",
            "domain": "post-test-999.example.com",
            "language": "ta"
        }
        res = api_client.post('/api/news/sources', json=payload)
        assert res.status_code in [200, 201]
        assert res.json["data"]["source_id"] == "src_post_test_999"

    def test_articles_api_search_and_filters(self, api_client, setup_api_database_fixtures):
        """Test GET /api/news/articles with source, language, topic, entity, event, and search filters."""
        src_ta = setup_api_database_fixtures["source_ta"]
        topic_id = setup_api_database_fixtures["topic_id"]
        entity_id = setup_api_database_fixtures["entity_id"]
        event_id = setup_api_database_fixtures["event_id"]

        # 1. Filter by source_id
        res_src = api_client.get(f'/api/news/articles?source_id={src_ta}')
        assert res_src.status_code == 200
        assert len(res_src.json["data"]) >= 1

        # 2. Filter by topic
        res_top = api_client.get(f'/api/news/articles?topic={topic_id}')
        assert res_top.status_code == 200
        assert len(res_top.json["data"]) >= 1

        # 3. Filter by entity / party / person
        res_ent = api_client.get(f'/api/news/articles?entity_id={entity_id}')
        assert res_ent.status_code == 200
        assert len(res_ent.json["data"]) >= 1

        # 4. Filter by event
        res_evt = api_client.get(f'/api/news/articles?event={event_id}')
        assert res_evt.status_code == 200
        assert len(res_evt.json["data"]) >= 1

        # 5. Search query
        res_srch = api_client.get('/api/news/articles?search=சட்டமன்றத்')
        assert res_srch.status_code == 200
        assert len(res_srch.json["data"]) >= 1

    def test_article_detail_and_provenance(self, api_client, setup_api_database_fixtures):
        """Test GET /api/news/articles/{id} exposing explicit provenance data structure."""
        art_id = setup_api_database_fixtures["article_id"]
        res = api_client.get(f'/api/news/articles/{art_id}')
        assert res.status_code == 200

        data = res.json["data"]
        assert data["article_id"] == art_id
        assert "provenance" in data
        
        prov = data["provenance"]
        assert prov["source_id"] == "src_api_phase48_ta"
        assert prov["text_hash"] is not None
        assert prov["document_id"] is not None
        assert prov["evidence_id"] is not None
        assert prov["is_test_fixture"] is True

    def test_topics_api(self, api_client, setup_api_database_fixtures):
        """Test GET /api/news/topics taxonomy route."""
        res = api_client.get('/api/news/topics')
        assert res.status_code == 200
        assert len(res.json["data"]) >= 1
        topic_codes = [t["topic_code"] for t in res.json["data"]]
        assert "TOPIC_P48_GOVERNANCE" in topic_codes

    def test_entities_api(self, api_client, setup_api_database_fixtures):
        """Test GET /api/news/entities with entity_type and search filters."""
        res = api_client.get('/api/news/entities?entity_type=person')
        assert res.status_code == 200
        assert len(res.json["data"]) >= 1

        res_srch = api_client.get('/api/news/entities?search=Phase48')
        assert res_srch.status_code == 200
        assert len(res_srch.json["data"]) >= 1

    def test_events_api_and_detail(self, api_client, setup_api_database_fixtures):
        """Test GET /api/news/events and GET /api/news/events/{id} detail endpoint."""
        # GET /api/news/events
        res = api_client.get('/api/news/events')
        assert res.status_code == 200
        assert len(res.json["data"]) >= 1

        # GET /api/news/events/{id}
        evt_id = setup_api_database_fixtures["event_id"]
        res_det = api_client.get(f'/api/news/events/{evt_id}')
        assert res_det.status_code == 200
        assert res_det.json["data"]["event_id"] == evt_id
        assert len(res_det.json["data"]["linked_articles"]) >= 1

    def test_coverage_and_comparison_apis(self, api_client, setup_api_database_fixtures):
        """Test GET /api/news/coverage and GET /api/news/source-comparison endpoints."""
        # Coverage
        res_cov = api_client.get('/api/news/coverage')
        assert res_cov.status_code == 200

        # Comparison
        src_a = setup_api_database_fixtures["source_ta"]
        src_b = setup_api_database_fixtures["source_en"]
        res_comp = api_client.get(f'/api/news/source-comparison?source_a={src_a}&source_b={src_b}')
        assert res_comp.status_code == 200
        assert res_comp.json["data"]["source_a_id"] == src_a
        assert res_comp.json["data"]["source_b_id"] == src_b

    def test_bias_indicators_api_neutral_explanations(self, api_client, setup_api_database_fixtures):
        """Test GET /api/news/bias-indicators verifying explanations and non-scalar response framing."""
        src_ta = setup_api_database_fixtures["source_ta"]
        
        # First trigger calculation
        res_calc = api_client.post('/api/news/indicators/calculate', json={"source_id": src_ta, "days_window": 30})
        assert res_calc.status_code == 200

        # Retrieve indicators
        res = api_client.get(f'/api/news/bias-indicators?source_id={src_ta}')
        assert res.status_code == 200
        indicators = res.json["data"]
        assert len(indicators) > 0

        for ind in indicators:
            assert "explanation" in ind
            assert "methodology_version" in ind
            assert "calculation_version" in ind
            assert "Does not imply partisan bias" in ind["explanation"]
            assert "Biased" not in ind["interpretation_label"]
