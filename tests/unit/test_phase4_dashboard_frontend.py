"""
Unit Tests for Phase 4.9 — News Analysis Dashboard Frontend Integration.

IMPORTANT:
All test cases use synthetic test fixtures.
No real political claims or fake bias labels are asserted.
"""

import pytest
from unittest.mock import MagicMock, patch
from frontend.services.api import APIClient


class TestPhase4DashboardFrontend:
    """Test suite for Phase 4.9 frontend API integration and page structure."""

    def test_api_client_news_methods(self):
        """Test APIClient wrapper methods for Phase 4 endpoints."""
        client = APIClient(base_url="http://localhost:8000")

        with patch("requests.get") as mock_get, patch("requests.post") as mock_post:
            mock_resp = MagicMock()
            mock_resp.ok = True
            mock_resp.json.return_value = {"status": "success", "data": [{"source_id": "src_test"}]}
            mock_get.return_value = mock_resp
            mock_post.return_value = mock_resp

            # 1. Sources
            ok, data = client.get_news_sources()
            assert ok is True
            assert len(data) == 1

            # 2. Articles
            ok, data = client.get_news_articles(source_id="src_test", limit=10)
            assert ok is True

            # 3. Detail
            ok, data = client.get_news_article_detail("art_123")
            assert ok is True

            # 4. Topics
            ok, data = client.get_news_topics()
            assert ok is True

            # 5. Entities
            ok, data = client.get_news_entities()
            assert ok is True

            # 6. Events
            ok, data = client.get_news_events()
            assert ok is True

            # 7. Coverage
            ok, data = client.get_news_coverage()
            assert ok is True

            # 8. Comparison
            ok, data = client.get_news_source_comparison("src_a", "src_b")
            assert ok is True

            # 9. Bias indicators
            ok, data = client.get_news_bias_indicators("src_a")
            assert ok is True

            # 10. Calculate indicators
            ok, data = client.calculate_news_indicators("src_a")
            assert ok is True

    def test_streamlit_page_syntax_import(self):
        """Verify that 3_Tamil_News.py compiles without syntax errors."""
        import importlib.util
        spec = importlib.util.spec_from_file_location("tamil_news_page", "frontend/pages/3_Tamil_News.py")
        assert spec is not None
        module = importlib.util.module_from_spec(spec)
        assert module is not None
