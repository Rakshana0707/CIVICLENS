"""
Unit Tests for Phase 4 — Tamil News Bias & Political Coverage Analyzer.

IMPORTANT:
All test cases below use strictly synthetic test fixtures.
No real political conclusions or real-world news articles are fabricated or asserted.
All synthetic fixtures are tagged with `is_test_fixture=True`.
"""

import pytest
from datetime import datetime, timezone
from backend.database.session import SessionLocal, engine
from backend.database.base import Base
from backend.models.news import NewsSource, Article, ActiveStatus, SourceType
from backend.models.common import Document, Evidence
from backend.acquisition.news_scraper import NewsScraper
from backend.nlp.news_analyzer import TamilNewsAnalyzer
from backend.services.news_service import NewsService
from backend.api.app import create_app

# --- TEST FIXTURES ---
SYNTHETIC_TAMIL_ARTICLE = {
    "title": "TEST FIXTURE — சென்னை மெட்ரோ திட்டம் மற்றும் பட்ஜெட் தகவல்",
    "text": "TEST FIXTURE — NOT REAL NEWS DATA. சென்னை மெட்ரோ இரண்டாம் கட்டப் பணிகளுக்குத் தமிழ் நிலத்தின் பட்ஜெட் நிதி ஒதுக்கீடு செய்யப்பட்டுள்ளது. திமுக மற்றும் அதிமுக தலைவர்கள் இந்த அறிக்கையை பரிசீலித்தனர்.",
    "url": "https://test-fixture.example.com/ta/metro-budget-test",
    "source_id": "src_test_ta",
    "source_name": "Test Tamil Daily",
    "domain": "test-fixture.example.com"
}

SYNTHETIC_ENGLISH_ARTICLE = {
    "title": "TEST FIXTURE — TN State Budget Metro Infrastructure Allocation",
    "text": "TEST FIXTURE — NOT REAL NEWS DATA. The Tamil Nadu State Budget allocated funds for urban metro expansion. M.K. Stalin and Opposition Leaders discussed the development plans.",
    "url": "https://test-fixture.example.com/en/metro-budget-test",
    "source_id": "src_test_en",
    "source_name": "Test English Daily",
    "domain": "test-fixture-en.example.com"
}


@pytest.fixture(scope="function")
def db_session():
    """Creates temporary in-memory database tables for unit testing."""
    Base.metadata.create_all(bind=engine)
    session = SessionLocal()
    yield session
    session.close()


@pytest.fixture
def api_client():
    """Flask test client."""
    app = create_app()
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client


class TestPhase4NewsAnalyzer:
    """Test suite for Phase 4 web acquisition, NLP processing, provenance, and API structure."""

    def test_language_detection(self):
        """Test script-based Tamil vs English language detection."""
        analyzer = TamilNewsAnalyzer()
        assert analyzer.detect_language(SYNTHETIC_TAMIL_ARTICLE["text"]) == "ta"
        assert analyzer.detect_language(SYNTHETIC_ENGLISH_ARTICLE["text"]) == "en"

    def test_tamil_text_normalization(self):
        """Test Unicode NFKC normalization and zero-width space removal."""
        analyzer = TamilNewsAnalyzer()
        raw_text = "சென்னை\u200c மெட்\u200dரோ "
        normalized = analyzer.normalize_tamil_text(raw_text)
        assert "\u200c" not in normalized
        assert "\u200d" not in normalized
        assert normalized == "சென்னை மெட்ரோ"

    def test_html_parsing_heuristics(self):
        """Test HTML scraper parsing of headlines, paragraphs, and canonical URLs."""
        scraper = NewsScraper()
        html = """
        <html>
            <head><link rel="canonical" href="https://example.com/canonical-news"/></head>
            <body>
                <h1>TEST FIXTURE — Headline Title</h1>
                <p>This is paragraph one of test fixture news body.</p>
                <p>This is paragraph two containing political coverage details.</p>
            </body>
        </html>
        """
        parsed = scraper.parse_article_html(html, "https://example.com/raw-news")
        assert parsed is not None
        assert parsed["canonical_url"] == "https://example.com/canonical-news"
        assert "TEST FIXTURE — Headline Title" in parsed["title"]
        assert len(parsed["article_text"].split()) >= 15
        assert parsed["text_hash"] is not None

    def test_source_registration_and_article_ingestion(self, db_session):
        """Test registering news sources and ingesting articles with full DB relationships."""
        service = NewsService(db_session)
        
        # 1. Register Source
        source = service.register_source(
            source_id=SYNTHETIC_TAMIL_ARTICLE["source_id"],
            source_name=SYNTHETIC_TAMIL_ARTICLE["source_name"],
            domain=SYNTHETIC_TAMIL_ARTICLE["domain"]
        )
        assert source.source_id == SYNTHETIC_TAMIL_ARTICLE["source_id"]

        # 2. Ingest Article
        article = service.ingest_article(
            source_id=SYNTHETIC_TAMIL_ARTICLE["source_id"],
            url=SYNTHETIC_TAMIL_ARTICLE["url"],
            title=SYNTHETIC_TAMIL_ARTICLE["title"],
            article_text=SYNTHETIC_TAMIL_ARTICLE["text"],
            is_test_fixture=True
        )
        assert article.article_id is not None
        assert article.is_test_fixture is True
        assert article.language == "ta"

        # 3. Verify Provenance (Document & Evidence Link)
        doc = db_session.query(Document).filter(Document.title == SYNTHETIC_TAMIL_ARTICLE["title"]).first()
        assert doc is not None
        evidence = db_session.query(Evidence).filter(Evidence.document_id == doc.id).first()
        assert evidence is not None
        assert evidence.result_id == article.article_id

    def test_duplicate_article_detection(self, db_session):
        """Test exact URL and text hash duplicate detection during ingestion."""
        service = NewsService(db_session)
        service.register_source("src_test_ta", "Test Tamil Daily", "test-fixture.example.com")
        
        art1 = service.ingest_article(
            source_id="src_test_ta",
            url="https://example.com/dupe-test",
            title="TEST Title",
            article_text="TEST FIXTURE content text duplicate check test.",
            is_test_fixture=True
        )
        # Ingest second article with same URL
        art2 = service.ingest_article(
            source_id="src_test_ta",
            url="https://example.com/dupe-test",
            title="TEST Title Different",
            article_text="TEST FIXTURE content text duplicate check test.",
            is_test_fixture=True
        )
        assert art1.article_id == art2.article_id

    def test_entity_and_topic_extraction(self):
        """Test gazetteer-based political entity recognition and topic classification."""
        analyzer = TamilNewsAnalyzer()
        text = "M.K. Stalin presented the Tamil Nadu State Budget allocation for DMK governance."
        
        entities = analyzer.extract_entities(text)
        topics = analyzer.classify_topics(text)

        entity_ids = [e["entity_id"] for e in entities]
        assert "ent_person_cm_mkstalin" in entity_ids
        assert "ent_party_dmk" in entity_ids

        topic_ids = [t["topic_id"] for t in topics]
        assert "TOPIC_BUDGET_ECONOMY" in topic_ids

    def test_neutral_bias_indicators_calculation(self, db_session):
        """Test multi-dimensional neutral statistical indicator generation."""
        service = NewsService(db_session)
        service.register_source("src_test_en", "Test English Daily", "test-fixture-en.example.com")
        service.ingest_article(
            source_id="src_test_en",
            url="https://example.com/bias-test-1",
            title="TEST FIXTURE Budget News",
            article_text="TEST FIXTURE — NOT REAL NEWS DATA. M.K. Stalin announced budget allocation for health education.",
            is_test_fixture=True
        )

        indicators = service.calculate_bias_indicators("src_test_en")
        assert len(indicators) > 0
        for ind in indicators:
            assert ind.indicator_value >= 0.0
            assert "Biased" not in ind.interpretation_label
            assert "Fake News" not in ind.interpretation_label
            assert ind.metric_type in ["topic_emphasis", "entity_prominence"]

    def test_news_api_endpoints(self, api_client, db_session):
        """Test Flask REST API routes under /api/news/."""
        service = NewsService(db_session)
        service.register_source("src_test_ta", "Test Tamil Daily", "test-fixture.example.com")
        service.ingest_article(
            source_id="src_test_ta",
            url="https://example.com/api-test-art",
            title="TEST FIXTURE API Title",
            article_text="TEST FIXTURE — NOT REAL NEWS DATA. Article text for REST testing.",
            is_test_fixture=True
        )

        # GET /api/news/sources
        res_sources = api_client.get('/api/news/sources')
        assert res_sources.status_code == 200
        assert len(res_sources.json["data"]) >= 1

        # GET /api/news/articles
        res_arts = api_client.get('/api/news/articles')
        assert res_arts.status_code == 200
        assert len(res_arts.json["data"]) >= 1

        # GET /api/news/bias-indicators
        res_bias = api_client.get('/api/news/bias-indicators')
        assert res_bias.status_code == 200
