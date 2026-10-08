"""
Unit & Integration Test Suite for Phase 4.3 News Ingestion & Raw Article Pipeline.

IMPORTANT:
All test cases use synthetic local HTML fixtures tagged with `is_test_fixture=True`.
No real political news articles or live websites are scraped during tests.
"""

import os
import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock, patch

from backend.database.session import SessionLocal, engine
from backend.database.base import Base
from backend.models.news import NewsSource, Article, NewsIngestionFailure, NewsProcessingQueue
from backend.models.common import Document, Evidence
from backend.acquisition.news_registry import NewsSourceRegistry, SourceConfig
from backend.ingestion.news_pipeline import (
    NewsIngestionPipeline, RawStoreManager, DuplicateDetector,
    FailureTracker, ProcessingQueueManager, MultilingualLanguageDetector
)

SYNTHETIC_TAMIL_HTML = """
<!DOCTYPE html>
<html>
<head>
    <link rel="canonical" href="https://test-fixture.example.com/canonical-ta-news" />
    <meta property="article:published_time" content="2026-10-08T08:00:00Z" />
    <meta name="author" content="Test Reporter Tamil" />
    <title>TEST FIXTURE — சென்னை மெட்ரோ திட்ட பட்ஜெட் அறிக்கை</title>
</head>
<body>
    <h1 class="title">TEST FIXTURE — சென்னை மெட்ரோ திட்ட பட்ஜெட் அறிக்கை</h1>
    <div class="body">
        <p>TEST FIXTURE — NOT REAL NEWS DATA. சென்னை மெட்ரோ இரண்டாம் கட்டப் பணிகளுக்கு நிதி ஒதுக்கீடு செய்யப்பட்டது.</p>
        <p>TEST FIXTURE — NOT REAL NEWS DATA. இந்த திட்டத்தின் மூலம் போக்குவரத்து நெரிசல் குறையும் என அரசு எதிர்பார்க்கிறது.</p>
    </div>
</body>
</html>
"""

SYNTHETIC_MIXED_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>TEST FIXTURE — TN Budget Update & சென்னை மெட்ரோ</title>
</head>
<body>
    <h1>TEST FIXTURE — TN Budget Update & சென்னை மெட்ரோ</h1>
    <div class="body">
        <p>TEST FIXTURE — NOT REAL NEWS DATA. The Tamil Nadu Government presented state budget for Chennai Metro expansion phase two.</p>
        <p>TEST FIXTURE — NOT REAL NEWS DATA. திட்டத்தின் நிதி ஒதுக்கீடு பற்றிய விபரங்கள் கீழே கொடுக்கப்பட்டுள்ளன.</p>
    </div>
</body>
</html>
"""


@pytest.fixture
def test_source(db_session):
    """Fixture ensuring registered NewsSource exists in isolated test DB."""
    src = db_session.query(NewsSource).filter(NewsSource.source_id == "src_test_fixture").first()
    if not src:
        src = NewsSource(
            source_id="src_test_fixture",
            source_name="Test Fixture Local Outlet",
            domain="test-fixture.example.com",
            language="ta"
        )
        db_session.add(src)
        db_session.commit()
    return src



class TestPhase4IngestionPipeline:
    """Test suite for Phase 4.3 raw article ingestion pipeline."""

    def test_multilingual_language_detection(self):
        """Test Tamil, English, and Code-Mixed language detection."""
        detector = MultilingualLanguageDetector()
        
        ta_text = "சென்னை மெட்ரோ இரண்டாம் கட்டப் பணிகளுக்கு நிதி ஒதுக்கீடு செய்யப்பட்டது."
        en_text = "The Tamil Nadu state budget allocated funds for Chennai Metro phase two expansion."
        mixed_text = "The Tamil Nadu budget update: சென்னை மெட்ரோ திட்ட பணிகளுக்கு Rs 500 crore நிதி ஒதுக்கீடு செய்யப்பட்டது."

        assert detector.detect_language(ta_text) == "ta"
        assert detector.detect_language(en_text) == "en"
        assert detector.detect_language(mixed_text) == "mixed"

    def test_raw_store_manager(self, tmp_path):
        """Test saving raw page HTML to disk hierarchy."""
        store = RawStoreManager(base_dir=str(tmp_path / "raw_store"))
        html = "<html><body>TEST FIXTURE</body></html>"
        path = store.save_raw_html("src_test", "https://example.com/test", html)
        
        assert os.path.exists(path)
        with open(path, "r", encoding="utf-8") as f:
            assert f.read() == html

    def test_multi_tier_duplicate_detection(self, db_session, test_source):
        """Test Tier 1 (URL), Tier 2 (Content Hash), and Tier 3 (Fuzzy Title + Date) duplicate detection."""
        detector = DuplicateDetector()
        
        # Insert baseline article
        pub_date = datetime.now(timezone.utc)
        art = Article(
            article_id="art_dupe_base",
            source_id="src_test_fixture",
            url="https://test-fixture.example.com/base-url-dupe",
            canonical_url="https://test-fixture.example.com/canon-base-dupe",
            title="TEST FIXTURE — Chennai Metro Budget Allocation 2026",
            article_text="TEST FIXTURE — NOT REAL NEWS DATA. Body text content.",
            text_hash="hash_base_12345",
            publication_date=pub_date,
            is_test_fixture=True
        )
        db_session.add(art)
        db_session.commit()

        # Tier 1 Duplicate Check (Matching URL)
        is_dupe1, reason1 = detector.check_duplicate(
            db_session, "https://test-fixture.example.com/base-url-dupe",
            "https://test-fixture.example.com/canon-base-dupe", "hash_new", "Different Title", pub_date
        )
        assert is_dupe1 is True
        assert "Tier 1" in reason1

        # Tier 2 Duplicate Check (Matching Text Hash)
        is_dupe2, reason2 = detector.check_duplicate(
            db_session, "https://test-fixture.example.com/new-url-hash",
            "https://test-fixture.example.com/new-canon-hash", "hash_base_12345", "Different Title", pub_date
        )
        assert is_dupe2 is True
        assert "Tier 2" in reason2

        # Tier 3 Duplicate Check (Fuzzy Title Jaccard Similarity within 48h)
        is_dupe3, reason3 = detector.check_duplicate(
            db_session, "https://test-fixture.example.com/new-url-3",
            "https://test-fixture.example.com/new-canon-3", "hash_new_3",
            "TEST FIXTURE — Chennai Metro Budget Allocation 2026 Update", pub_date
        )
        assert is_dupe3 is True
        assert "Tier 3" in reason3

    def test_failure_tracker_no_silent_drops(self, db_session, test_source):
        """Test recording ingestion failures in DB without silent drops."""
        failure = FailureTracker.record_failure(
            db_session,
            source_id="src_test_fixture",
            url="https://example.com/failed-page-unique",
            failure_type="PARSER_ERROR",
            error_details="Parser produced empty body text.",
            raw_html_path="scratch/raw_articles/fail.html"
        )
        assert failure.id is not None
        assert failure.failure_type == "PARSER_ERROR"

        db_fail = db_session.query(NewsIngestionFailure).filter(NewsIngestionFailure.id == failure.id).first()
        assert db_fail is not None

    def test_processing_queue_manager(self, db_session, test_source):
        """Test enqueuing articles for processing, fetching pending items, and marking complete."""
        queue_mgr = ProcessingQueueManager()
        
        # Create article first
        art = Article(
            article_id="art_queue_test_unique",
            source_id="src_test_fixture",
            url="https://example.com/queue-test-unique",
            title="TEST Queue Title Unique",
            article_text="TEST Queue Text Unique",
            text_hash="hash_queue_123_unique",
            is_test_fixture=True
        )
        db_session.add(art)
        db_session.commit()

        # Enqueue
        item = queue_mgr.enqueue_article(db_session, "art_queue_test_unique")
        assert item.status == "PENDING"

        # Fetch Pending
        pending = queue_mgr.fetch_pending(db_session)
        assert len(pending) >= 1

        # Mark Completed
        queue_mgr.mark_completed(db_session, item.id)
        assert item.status == "COMPLETED"

    def test_full_pipeline_ingestion_flow(self, db_session, test_source):
        """Test end-to-end ingestion flow from raw HTML fetch to raw store, DB insert, and queue entry."""
        pipeline = NewsIngestionPipeline(db_session)

        with patch.object(pipeline.scraper.fetcher, 'fetch', return_value=SYNTHETIC_TAMIL_HTML):
            article = pipeline.process_url(
                source_id="src_test_fixture",
                url="https://test-fixture.example.com/pipeline-art-unique-99",
                is_test_fixture=True
            )

            assert article is not None
            assert article.article_id is not None
            assert article.canonical_url == "https://test-fixture.example.com/canonical-ta-news"
            assert article.language in ["ta", "mixed"]

            assert os.path.exists(article.raw_html_path)

            # Verify Core Provenance Document & Evidence Records
            doc = db_session.query(Document).filter(Document.title == article.title).first()
            assert doc is not None
            evidence = db_session.query(Evidence).filter(Evidence.document_id == doc.id).first()
            assert evidence is not None
            assert evidence.result_id == article.article_id

            # Verify Processing Queue Item
            queue_item = db_session.query(NewsProcessingQueue).filter(NewsProcessingQueue.article_id == article.article_id).first()
            assert queue_item is not None
            assert queue_item.status == "PENDING"

