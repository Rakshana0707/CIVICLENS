"""
Phase 8.2 — Unit Tests for Civic Data Acquisition & Web Scraping Framework.

Tests:
1. Configurable source registry & domain whitelisting.
2. URL discovery adhering to allowed domains and disallowed robots paths.
3. HTML table extraction and structured dict conversion.
4. Tabular data parsing for CSV and JSON datasets.
5. PDF parsing with text/table extraction and OCR fallback detection.
6. Cryptographic SHA-256 checksums, disk caching, and deduplication.
7. Per-domain polite rate limiting.
8. Structured failure logging and audit tracking.
9. Manual document import interface for OTP/CAPTCHA restricted portals.
10. End-to-end engine acquisition on local mock fixtures with PII scrubbing.
"""

import os
import io
import time
import pytest
import tempfile
import shutil
from datetime import datetime, timezone

from backend.acquisition.civic_acquisition_framework import (
    CivicSourceConfig,
    CivicSourceRegistry,
    CivicAcquisitionEngine,
    HTMLTableExtractor,
    PDFCivicParser,
    OCRFallbackHandler,
    TabularDataParser,
    ManualDocumentImporter,
    ChecksumCacheManager,
    URLDiscoverer,
    RateLimiter,
    FailureLogManager,
    AcquisitionResult
)
from tests.fixtures.phase8_fixtures import (
    MOCK_HTML_PAGE_WITH_TABLE,
    MOCK_CSV_DATA,
    MOCK_JSON_DATA
)


@pytest.fixture
def temp_cache_dir():
    """Isolated temporary cache directory for testing."""
    temp_dir = tempfile.mkdtemp(prefix="civiclens_cache_test_")
    yield temp_dir
    shutil.rmtree(temp_dir, ignore_errors=True)


# ---------------------------------------------------------------------------
# Test 1: Configurable Source Registry
# ---------------------------------------------------------------------------
def test_1_source_registry_and_whitelisting():
    registry = CivicSourceRegistry()

    # Verify default statutory civic sources are registered
    sources = registry.list_sources()
    source_ids = {s.source_id for s in sources}
    assert "TN_PORTAL" in source_ids
    assert "DARPG_CPGRAMS" in source_ids
    assert "TNEGA_CM_HELPLINE" in source_ids
    assert "GCC_CHENNAI" in source_ids
    assert "TN_TENDERS" in source_ids
    assert "DATA_GOV_IN" in source_ids
    assert "LOCAL_FIXTURE" in source_ids

    # Test URL domain lookup
    cfg_tn = registry.get_by_url("https://www.tn.gov.in/charters/maws.pdf")
    assert cfg_tn is not None
    assert cfg_tn.source_id == "TN_PORTAL"

    cfg_gcc = registry.get_by_url("https://chennaicorporation.gov.in/gcc/council_resolutions.html")
    assert cfg_gcc is not None
    assert cfg_gcc.source_id == "GCC_CHENNAI"

    # Test unregistered domain lookup
    cfg_unknown = registry.get_by_url("https://unauthorized-leak-portal.com/data")
    assert cfg_unknown is None


# ---------------------------------------------------------------------------
# Test 2: URL Discovery with Robots & Whitelist Enforcement
# ---------------------------------------------------------------------------
def test_2_url_discovery_filtering():
    registry = CivicSourceRegistry()
    config = registry.get("TN_PORTAL")
    assert config is not None

    base_url = "https://www.tn.gov.in/reports/"
    discovered = URLDiscoverer.discover_urls(
        html_content=MOCK_HTML_PAGE_WITH_TABLE,
        base_url=base_url,
        config=config
    )

    # Valid relative links on allowed domain should be discovered
    assert "https://www.tn.gov.in/reports/march_2024.pdf" in discovered
    assert "https://www.tn.gov.in/data/grievances_2024.csv" in discovered

    # Disallowed path (/admin) must NOT be discovered
    assert not any("/admin" in u for u in discovered)

    # External unauthorized domain must NOT be discovered
    assert not any("external-unauthorized.com" in u for u in discovered)


# ---------------------------------------------------------------------------
# Test 3: HTML Table Extraction with Automatic PII Scrubbing
# ---------------------------------------------------------------------------
def test_3_html_table_extraction_and_pii_sanitization():
    tables = HTMLTableExtractor.extract_tables(MOCK_HTML_PAGE_WITH_TABLE)
    assert len(tables) == 1

    rows = tables[0]
    assert len(rows) == 3

    # Check columns
    assert "District" in rows[0]
    assert "Category" in rows[0]
    assert "Total Received" in rows[0]
    assert "Disposed" in rows[0]
    assert "Officer Contact" in rows[0]

    # Check row data and PII sanitization
    chennai_row = rows[0]
    assert chennai_row["District"] == "Chennai"
    assert chennai_row["Category"] == "roads"
    assert chennai_row["Total Received"] == "1420"
    # PII: Phone 9840112233 must be redacted, Thiru S. Raman must be [CITIZEN]
    assert "9840112233" not in chennai_row["Officer Contact"]
    assert "Thiru S. Raman" not in chennai_row["Officer Contact"]
    assert "[PHONE REDACTED]" in chennai_row["Officer Contact"]
    assert "[CITIZEN]" in chennai_row["Officer Contact"]

    # Check row 2: Email valli.k@tn.gov.in must be redacted
    madurai_row = rows[1]
    assert "valli.k@tn.gov.in" not in madurai_row["Officer Contact"]
    assert "[EMAIL REDACTED]" in madurai_row["Officer Contact"]

    # Check row 3: Door number D.No. 4 must be redacted
    cbe_row = rows[2]
    assert "D.No. 4" not in cbe_row["Officer Contact"]
    assert "[ADDRESS REDACTED]" in cbe_row["Officer Contact"]


# ---------------------------------------------------------------------------
# Test 4: Tabular Data Parsing (CSV and JSON)
# ---------------------------------------------------------------------------
def test_4_tabular_data_parsing_csv_and_json():
    # 1. Parse CSV
    csv_rows = TabularDataParser.parse_csv(MOCK_CSV_DATA)
    assert len(csv_rows) == 5
    assert csv_rows[0]["district"] == "Chennai"
    assert csv_rows[0]["category"] == "roads"
    assert csv_rows[0]["received_count"] == "1420"
    # PII scrubbing on officer notes
    assert "9876543210" not in csv_rows[0]["officer_notes"]
    assert "Thiru Ramesh" not in csv_rows[0]["officer_notes"]
    assert "[PHONE REDACTED]" in csv_rows[0]["officer_notes"]
    assert "[CITIZEN]" in csv_rows[0]["officer_notes"]

    # 2. Parse JSON
    json_rows = TabularDataParser.parse_json(MOCK_JSON_DATA)
    assert isinstance(json_rows, list)
    assert len(json_rows) == 2
    assert json_rows[0]["portal"] == "CM_HELPLINE_1100"
    assert json_rows[0]["total_receipts"] == 15420
    # PII scrubbing
    assert "9444012345" not in json_rows[0]["contact_phone"]
    assert "[PHONE REDACTED]" in json_rows[0]["contact_phone"]
    assert "priya.gcc@gmail.com" not in json_rows[1]["contact_email"]
    assert "[EMAIL REDACTED]" in json_rows[1]["contact_email"]


# ---------------------------------------------------------------------------
# Test 5: PDF Text & Table Extraction with OCR Fallback Flagging
# ---------------------------------------------------------------------------
def test_5_pdf_parsing_and_ocr_fallback():
    # Test on synthetic minimal PDF bytes
    # A dummy non-PDF byte stream tests graceful error handling
    corrupt_bytes = b"Not a real PDF stream"
    res_corrupt = PDFCivicParser.parse_pdf(corrupt_bytes)
    assert res_corrupt["ocr_status"] == "PDF_CORRUPT_OR_UNREADABLE"

    # Test OCR Fallback Handler directly
    fallback_res = OCRFallbackHandler.process_scanned_page(page_index=1, image_data=b"dummy_image_bytes")
    assert fallback_res["page_index"] == 1
    assert "ocr_status" in fallback_res
    # When pytesseract is not configured or in sandbox, returns graceful fallback flag
    assert "OCR" in fallback_res["ocr_status"]
    assert "OCR REQUIRED" in fallback_res["text"]


# ---------------------------------------------------------------------------
# Test 6: Checksum, Disk Caching, and Deduplication
# ---------------------------------------------------------------------------
def test_6_checksum_caching_and_deduplication(temp_cache_dir):
    cache_mgr = ChecksumCacheManager(cache_dir=temp_cache_dir)
    data = b"Official Government Order Ms. No. 112 Municipal Administration Dept"

    # Compute SHA-256
    sha256 = cache_mgr.compute_sha256(data)
    assert len(sha256) == 64

    # Not cached initially
    assert cache_mgr.is_cached(sha256) is False
    assert cache_mgr.is_duplicate(sha256) is False

    # Write to cache
    cache_mgr.write_cache(sha256, data)
    assert cache_mgr.is_cached(sha256) is True
    assert cache_mgr.is_duplicate(sha256) is True

    # Read from cache
    cached_data = cache_mgr.read_cache(sha256)
    assert cached_data == data


# ---------------------------------------------------------------------------
# Test 7: Rate Limiter Politeness
# ---------------------------------------------------------------------------
def test_7_rate_limiter_politeness():
    limiter = RateLimiter()
    domain = "tn.gov.in"

    # First request: immediate
    start_t = time.time()
    limiter.wait_if_needed(domain, delay_seconds=0.1)
    duration_1 = time.time() - start_t
    assert duration_1 < 0.05

    # Second request immediately after: should wait ~0.1s
    start_t2 = time.time()
    limiter.wait_if_needed(domain, delay_seconds=0.1)
    duration_2 = time.time() - start_t2
    assert duration_2 >= 0.08


# ---------------------------------------------------------------------------
# Test 8: Failure Logger
# ---------------------------------------------------------------------------
def test_8_failure_logger():
    log_mgr = FailureLogManager()

    log_mgr.record_failure(
        url="https://tn.gov.in/missing_bulletin.pdf",
        source_id="TN_PORTAL",
        error_type="HTTP_404_NOT_FOUND",
        error_message="Document not found on server",
        status_code=404,
        retry_count=0
    )

    logs = log_mgr.get_logs()
    assert len(logs) == 1
    assert logs[0].source_id == "TN_PORTAL"
    assert logs[0].error_type == "HTTP_404_NOT_FOUND"
    assert logs[0].status_code == 404

    # Filter by source ID
    assert len(log_mgr.get_logs("TN_PORTAL")) == 1
    assert len(log_mgr.get_logs("UNKNOWN")) == 0


# ---------------------------------------------------------------------------
# Test 9: Manual Document Import Interface (Restricted Portals)
# ---------------------------------------------------------------------------
def test_9_manual_document_importer(temp_cache_dir):
    cache_mgr = ChecksumCacheManager(cache_dir=temp_cache_dir)
    importer = ManualDocumentImporter(cache_mgr)

    csv_bytes = MOCK_CSV_DATA.encode("utf-8")
    result = importer.import_document(
        file_path_or_bytes=csv_bytes,
        source_id="TNEGA_CM_HELPLINE",
        document_title="Mudhalvarin Mugavari March 2024 Aggregate Redressal",
        file_format="CSV",
        origin_url="https://cmhelpline.tnega.org/reports/march_2024.csv",
        custom_metadata={"reporting_period": "2024-03", "tier": 2}
    )

    assert isinstance(result, AcquisitionResult)
    assert result.status == "SUCCESS"
    assert result.source_id == "TNEGA_CM_HELPLINE"
    assert result.file_format == "CSV"
    assert len(result.extracted_tables) == 1
    assert len(result.extracted_tables[0]) == 5
    assert result.extracted_metadata["imported_manually"] is True
    assert result.sha256_hash != ""

    # Re-importing identical document should be flagged as DUPLICATE
    result_dup = importer.import_document(
        file_path_or_bytes=csv_bytes,
        source_id="TNEGA_CM_HELPLINE",
        document_title="Mudhalvarin Mugavari March 2024 Duplicate Import",
        file_format="CSV"
    )
    assert result_dup.status == "DUPLICATE"
    assert result_dup.is_duplicate is True


# ---------------------------------------------------------------------------
# Test 10: End-to-End Engine Acquisition with Local Fixtures
# ---------------------------------------------------------------------------
def test_10_end_to_end_engine_local_fixtures(temp_cache_dir):
    registry = CivicSourceRegistry()
    cache_mgr = ChecksumCacheManager(cache_dir=temp_cache_dir)
    failure_logger = FailureLogManager()
    engine = CivicAcquisitionEngine(
        registry=registry,
        cache_manager=cache_mgr,
        failure_logger=failure_logger
    )

    # Write a local HTML fixture to temporary disk
    fixture_html_path = os.path.join(temp_cache_dir, "test_bulletin.html")
    with open(fixture_html_path, "w", encoding="utf-8") as f:
        f.write(MOCK_HTML_PAGE_WITH_TABLE)

    file_url = f"file:///{fixture_html_path.replace(os.sep, '/')}"

    # Acquire via local file protocol
    result = engine.acquire_url(url=file_url, source_id="LOCAL_FIXTURE")

    assert result.status == "SUCCESS"
    assert result.file_format == "HTML"
    assert result.raw_bytes_len > 0
    assert len(result.extracted_tables) == 1
    assert result.retrieved_at is not None
    # Verify PII scrubbing on parsed text
    assert "9840112233" not in result.parsed_text
    assert "[PHONE REDACTED]" in result.parsed_text

    # Second acquisition of same URL without force_refresh should hit cache
    cached_result = engine.acquire_url(url=file_url, source_id="LOCAL_FIXTURE")
    assert cached_result.status == "CACHED"
    assert cached_result.is_cached is True

    # Test unauthorized domain rejection
    unauthorized_res = engine.acquire_url(url="https://darkweb-leaks.org/data.json")
    assert unauthorized_res.status == "FAILED"
    assert "not registered" in unauthorized_res.error_message
    assert len(failure_logger.get_logs("UNKNOWN")) == 1

    # Test OTP-gated portal disallowed path triggering manual import requirement
    gated_url = "https://cmhelpline.tnega.org/portal/en/signin"
    gated_res = engine.acquire_url(url=gated_url, source_id="TNEGA_CM_HELPLINE")
    assert gated_res.status == "MANUAL_IMPORT_REQUIRED"
    assert "manual import" in gated_res.error_message
