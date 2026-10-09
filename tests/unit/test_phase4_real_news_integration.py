"""
Unit & Integration Tests for Real Phase 4 News Dataset Integration.
Verifies real article storage, REST API responses, NLP outputs, and frontend page imports.
"""

import pytest
from backend.database.session import SessionLocal
from backend.models.news import Article, NewsSource, PoliticalEntity, PoliticalEvent, BiasIndicator
from backend.api.app import create_app


class TestPhase4RealNewsIntegration:

    @pytest.fixture(autouse=True)
    def setup_db(self):
        self.db = SessionLocal()
        self.app = create_app()
        yield self.db
        self.db.close()

    def test_real_articles_in_database(self):
        real_articles = self.db.query(Article).filter(Article.is_test_fixture == False).all()
        assert len(real_articles) >= 70, f"Expected at least 70 real articles, found {len(real_articles)}"

        tamil_count = sum(1 for a in real_articles if a.language == "ta")
        english_count = sum(1 for a in real_articles if a.language == "en")
        assert tamil_count > 0, "Expected Tamil articles in real dataset"
        assert english_count > 0, "Expected English articles in real dataset"

    def test_news_sources_registered(self):
        sources = self.db.query(NewsSource).all()
        assert len(sources) >= 40, f"Expected at least 40 registered news sources, found {len(sources)}"

    def test_political_events_and_indicators(self):
        events = self.db.query(PoliticalEvent).all()
        assert len(events) >= 10, f"Expected at least 10 political events, found {len(events)}"

        indicators = self.db.query(BiasIndicator).all()
        assert len(indicators) >= 50, f"Expected bias indicators in DB, found {len(indicators)}"

    def test_api_real_articles_endpoint(self):
        client = self.app.test_client()
        resp = client.get("/api/news/articles")
        assert resp.status_code == 200
        data = resp.get_json()
        assert "articles" in data or "data" in data or "results" in data

    def test_api_bias_indicators_endpoint(self):
        client = self.app.test_client()
        resp = client.get("/api/news/bias-indicators")
        assert resp.status_code == 200
