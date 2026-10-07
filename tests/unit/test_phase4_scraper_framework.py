"""
Unit & Integration Test Suite for Phase 4.2 Reusable News Scraping Framework.

IMPORTANT:
All test cases use synthetic local HTML fixtures tagged with `is_test_fixture=True`.
No real political news articles or live websites are scraped during tests.
"""

import os
import time
import pytest
import requests
from unittest.mock import MagicMock, patch

from backend.acquisition.news_registry import NewsSourceRegistry, SourceConfig
from backend.acquisition.news_adapters import (
    adapter_registry, BaseSourceAdapter, GenericSourceAdapter, TheHinduAdapter
)
from backend.acquisition.news_scraper_framework import (
    RateLimiter, RobotsChecker, CacheManager, Fetcher, Deduplicator,
    ContentExtractor, MetadataExtractor, ArticleParser, SourceScraper
)

SYNTHETIC_HTML_PAGE = """
<!DOCTYPE html>
<html>
<head>
    <link rel="canonical" href="https://test-fixture.example.com/canonical-article-123" />
    <meta property="article:published_time" content="2026-10-07T10:00:00Z" />
    <meta name="author" content="Test Reporter" />
    <title>TEST FIXTURE — Local News Headline</title>
</head>
<body>
    <h1 class="title">TEST FIXTURE — Local News Headline</h1>
    <div class="body">
        <p>TEST FIXTURE — NOT REAL NEWS DATA. This is paragraph one of synthetic test article text for framework verification.</p>
        <p>TEST FIXTURE — NOT REAL NEWS DATA. This is paragraph two containing political coverage details and district report.</p>
    </div>
</body>
</html>
"""

SYNTHETIC_RSS_FEED = """<?xml version="1.0" encoding="UTF-8" ?>
<rss version="2.0">
<channel>
    <title>Test Fixture Feed</title>
    <item>
        <title>TEST FIXTURE Article 1</title>
        <link>https://test-fixture.example.com/test/article-1</link>
    </item>
    <item>
        <title>TEST FIXTURE Article 2</title>
        <link>https://test-fixture.example.com/test/article-2</link>
    </item>
</channel>
</rss>
"""


@pytest.fixture
def tmp_cache_dir(tmp_path):
    """Temporary directory fixture for CacheManager."""
    cache_dir = str(tmp_path / "cache")
    return cache_dir


class TestPhase4ScraperFramework:
    """Comprehensive test suite for Phase 4.2 news acquisition framework components."""

    def test_url_discovery(self):
        """Test URL discovery from RSS feed XML and HTML link parsing."""
        scraper = SourceScraper()
        
        # Test RSS link discovery
        with patch.object(scraper.fetcher, 'fetch', return_value=SYNTHETIC_RSS_FEED):
            source_cfg = SourceConfig(
                source_id="src_test", source_name="Test Source", domain="test-fixture.example.com",
                rss_urls=["https://test-fixture.example.com/rss.xml"]
            )
            urls = scraper.discover_urls_from_rss(source_cfg)
            assert len(urls) == 2
            assert "https://test-fixture.example.com/test/article-1" in urls

        # Test HTML link discovery with pattern matching
        html_links = """
        <a href="/test/match-1">Matching Link 1</a>
        <a href="/other/ignore-1">Ignored Link</a>
        """
        source_cfg_pattern = SourceConfig(
            source_id="src_test", source_name="Test Source", domain="test-fixture.example.com",
            article_url_patterns=["/test/.*"]
        )
        discovered = scraper.discover_urls_from_html(html_links, "https://test-fixture.example.com", source_cfg_pattern)
        assert len(discovered) == 1
        assert "https://test-fixture.example.com/test/match-1" in discovered

    def test_article_detection_and_parsing(self):
        """Test detection and parsing of synthetic article content."""
        parser = ArticleParser()
        source_cfg = SourceConfig(
            source_id="src_test", source_name="Test Source", domain="test-fixture.example.com",
            selectors={"title": "h1.title", "body": "div.body p"}
        )
        parsed = parser.parse(SYNTHETIC_HTML_PAGE, "https://test-fixture.example.com/raw-url", source_cfg)
        
        assert parsed is not None
        assert parsed["canonical_url"] == "https://test-fixture.example.com/canonical-article-123"
        assert "TEST FIXTURE — Local News Headline" in parsed["title"]
        assert "TEST FIXTURE — NOT REAL NEWS DATA" in parsed["article_text"]
        assert parsed["word_count"] > 15
        assert parsed["text_hash"] is not None

    def test_duplicate_url_and_hash_deduplication(self):
        """Test URL canonical deduplication and exact text hash deduplication."""
        dedup = Deduplicator()
        
        # 1. URL Deduplication
        url1 = "https://example.com/news/123?utm_source=rss"
        url2 = "https://example.com/news/123?utm_source=twitter"
        assert not dedup.is_duplicate_url(url1)
        assert dedup.is_duplicate_url(url2) # Same canonical URL base

        # 2. Text Hash Deduplication
        text = "TEST FIXTURE duplicate body content."
        hash_val = GenericSourceAdapter.compute_text_hash(text)
        assert not dedup.is_duplicate_text(hash_val)
        assert dedup.is_duplicate_text(hash_val)

    def test_canonical_url_extraction(self):
        """Test canonical URL extraction from HTML head link tags."""
        adapter = GenericSourceAdapter()
        canonical = adapter.extract_canonical_url(SYNTHETIC_HTML_PAGE, "https://example.com/fallback")
        assert canonical == "https://test-fixture.example.com/canonical-article-123"

        # Fallback when canonical tag is absent
        no_canon_html = "<html><head><title>Test</title></head><body><h1>Title</h1></body></html>"
        fallback = adapter.extract_canonical_url(no_canon_html, "https://example.com/fallback")
        assert fallback == "https://example.com/fallback"

    def test_retries_and_exponential_backoff(self):
        """Test HTTP fetcher retry mechanism on network errors."""
        rate_limiter = RateLimiter(default_delay=0.01)
        cache_mgr = CacheManager(cache_dir="scratch/test_cache_tmp")
        robots = RobotsChecker("TestBot")
        fetcher = Fetcher(rate_limiter, cache_mgr, robots, max_retries=3, backoff_factor=1.1)

        # Mock session to fail twice then succeed
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = "SUCCESS"
        mock_resp.headers = {}
        mock_resp.raise_for_status = MagicMock()

        with patch.object(fetcher.session, 'get', side_effect=[requests.RequestException("Err 1"), requests.RequestException("Err 2"), mock_resp]):
            content = fetcher.fetch("https://test-fixture.example.com/retry-test", use_cache=False)
            assert content == "SUCCESS"


    def test_rate_limiting(self):
        """Test per-domain rate limiter delay calculation."""
        limiter = RateLimiter(default_delay=0.1)
        domain = "test-rate-limit.example.com"
        
        # First call has no delay
        w1 = limiter.wait(domain)
        assert w1 == 0.0
        
        # Immediate second call incurs delay
        w2 = limiter.wait(domain, custom_delay=0.1)
        assert w2 > 0.0

    def test_cache_hit_and_persistence(self, tmp_cache_dir):
        """Test CacheManager hit vs miss and disk persistence."""
        cache_mgr = CacheManager(cache_dir=tmp_cache_dir, ttl_seconds=3600)
        url = "https://test-fixture.example.com/cache-article"
        content = "CACHED_CONTENT_FIXTURE"

        # Initial miss
        assert cache_mgr.get(url) is None

        # Store in cache
        cache_mgr.set(url, content)

        # Instant hit
        assert cache_mgr.get(url) == content

        # Verify disk persistence by re-instantiating CacheManager
        cache_mgr_new = CacheManager(cache_dir=tmp_cache_dir, ttl_seconds=3600)
        assert cache_mgr_new.get(url) == content

    def test_parser_failure_fallback(self):
        """Test fallback to generic adapter when custom adapter yields empty content."""
        parser = ArticleParser()
        
        # Create a failing custom adapter returning None
        failing_adapter = MagicMock()
        failing_adapter.parse_article.return_value = None
        adapter_registry.register_adapter("failing_adapter", failing_adapter)

        source_cfg = SourceConfig(
            source_id="src_fail", source_name="Fail Source", domain="example.com",
            parser_type="failing_adapter"
        )

        # Parsing should trigger fallback to generic adapter and return content
        parsed = parser.parse(SYNTHETIC_HTML_PAGE, "https://example.com/fallback-test", source_cfg)
        assert parsed is not None
        assert "TEST FIXTURE — Local News Headline" in parsed["title"]

    def test_robots_and_access_policy_handling(self):
        """Test RobotsChecker policy auditing and disallow directive handling."""
        robots = RobotsChecker("TestBot")
        
        # Permissive check on unknown domain
        assert robots.is_allowed("https://test-permissive.example.com/news")

        # Mock robots.txt disallowing /private/
        mock_rp = MagicMock()
        mock_rp.can_fetch.side_effect = lambda ua, url: False if "/private/" in url else True
        robots.parsers["disallowed.example.com"] = mock_rp

        assert not robots.is_allowed("https://disallowed.example.com/private/article")
        assert robots.is_allowed("https://disallowed.example.com/public/article")
