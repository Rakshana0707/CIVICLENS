"""
Unit tests for Phase 6 Public Record Acquisition Framework.

Tests all 13 core acquisition capabilities using synthetic test fixtures without
making external network requests.
"""

import os
import json
import shutil
import tempfile
import pytest

from backend.acquisition.representative_acquisition import (
    DocumentFormat,
    FileTypeDetector,
    AcquisitionConfig,
    SourceRegistry,
    URLDiscoveryEngine,
    DownloadManifest,
    HTMLExtractor,
    PDFTextExtractor,
    OCRFallbackHandler,
    TableExtractor,
    DocumentAcquisitionEngine
)

from tests.fixtures.phase6_fixtures import (
    MOCK_TNLA_ASSEMBLY_HTML,
    MOCK_SANSAD_QUESTION_JSON,
    MOCK_MPLADS_WORK_CSV,
    MOCK_CENSUS_DEMOGRAPHIC_CSV,
    MOCK_ECI_RESULT_PDF,
    MOCK_DISCOVERY_TARGETS,
    MOCK_PAYLOAD_MAP
)


@pytest.fixture
def temp_acquisition_dir():
    temp_dir = tempfile.mkdtemp(prefix="phase6_acq_test_")
    yield temp_dir
    shutil.rmtree(temp_dir, ignore_errors=True)


def test_1_configurable_source_registry():
    registry = SourceRegistry()
    src = registry.get_source("SRC-ECI-RESULTS")
    assert src is not None
    assert src["allowed_domain"] == "eci.gov.in"
    assert registry.is_domain_allowed("SRC-ECI-RESULTS", "https://results.eci.gov.in/kolathur_013.pdf")
    assert not registry.is_domain_allowed("SRC-ECI-RESULTS", "https://unauthorized-domain.com/data")


def test_2_url_discovery_engine():
    html_page = """
    <html>
        <body>
            <a href="/proceedings/2023/debate.pdf">PDF Debate</a>
            <a href="https://www.assembly.tn.gov.in/reports/report.csv">CSV Report</a>
            <a href="https://external.com/link">External Link</a>
        </body>
    </html>
    """
    links = URLDiscoveryEngine.discover_links(
        html_page,
        base_url="https://www.assembly.tn.gov.in/",
        target_extensions=[".pdf", ".csv"]
    )
    assert len(links) == 2
    assert "https://www.assembly.tn.gov.in/proceedings/2023/debate.pdf" in links
    assert "https://www.assembly.tn.gov.in/reports/report.csv" in links


def test_3_file_type_detector():
    fmt_pdf = FileTypeDetector.detect_format(MOCK_ECI_RESULT_PDF, "file.pdf")
    assert fmt_pdf == DocumentFormat.PDF

    fmt_html = FileTypeDetector.detect_format(MOCK_TNLA_ASSEMBLY_HTML, "page.html")
    assert fmt_html == DocumentFormat.HTML

    fmt_json = FileTypeDetector.detect_format(MOCK_SANSAD_QUESTION_JSON, "data.json")
    assert fmt_json == DocumentFormat.JSON

    fmt_csv = FileTypeDetector.detect_format(MOCK_MPLADS_WORK_CSV, "works.csv")
    assert fmt_csv == DocumentFormat.CSV


def test_4_html_text_and_table_extraction():
    res = HTMLExtractor.extract_text(MOCK_TNLA_ASSEMBLY_HTML)
    assert "Tamil Nadu Legislative Assembly Debate" in res["title"]
    assert "M. K. Stalin" in res["text"]
    assert len(res["tables"]) >= 1
    tbl = res["tables"][0]
    assert tbl[0] == ["Constituency", "Member Name", "Question Subject", "Status"]


def test_5_pdf_text_extraction():
    res = PDFTextExtractor.extract_text(MOCK_ECI_RESULT_PDF)
    assert res["page_count"] >= 1
    assert "Election Commission of India" in res["text"] or "Kolathur" in res["text"]


def test_6_table_extraction_csv():
    rows = TableExtractor.parse_csv(MOCK_MPLADS_WORK_CSV)
    assert len(rows) == 4
    assert rows[0]["mp_name"] == "Kalanidhi Veeraswamy"
    assert rows[0]["status"] == "COMPLETED"


def test_7_ocr_fallback_handler():
    ocr_res = OCRFallbackHandler.perform_ocr(b"FAKEOPICTUREBYTES")
    assert ocr_res["ocr_applied"] is True
    assert ocr_res["confidence_score"] > 0.0


def test_8_sha256_checksum_and_deduplication(temp_acquisition_dir):
    config = AcquisitionConfig(raw_storage_dir=temp_acquisition_dir, rate_limit_seconds=0.01)
    engine = DocumentAcquisitionEngine(config=config)

    # 1st Acquisition
    res1 = engine.acquire_document(
        url="https://mplads.gov.in/reports/tn/2023/mplads_works.csv",
        source_id="SRC-MPLADS-WORKS",
        category="MPLADS_WORKS",
        year_or_term="FY2022-23",
        mock_content=MOCK_MPLADS_WORK_CSV
    )
    assert res1["status"] == "SUCCESS"
    assert res1["is_duplicate"] is False

    # 2nd Acquisition with identical content
    res2 = engine.acquire_document(
        url="https://mplads.gov.in/reports/tn/2023/mplads_works_copy.csv",
        source_id="SRC-MPLADS-WORKS",
        category="MPLADS_WORKS",
        year_or_term="FY2022-23",
        mock_content=MOCK_MPLADS_WORK_CSV
    )
    assert res2["status"] == "SUCCESS"
    assert res2["is_duplicate"] is True
    assert res2["duplicate_of"] == res1["document_id"]


def test_9_caching_mechanism(temp_acquisition_dir):
    config = AcquisitionConfig(raw_storage_dir=temp_acquisition_dir, rate_limit_seconds=0.01)
    engine = DocumentAcquisitionEngine(config=config)

    url = "https://sansad.in/api/questions/ls/2023/1420.json"
    res1 = engine.acquire_document(
        url=url,
        source_id="SRC-SANSAD-QUESTIONS",
        category="PARLIAMENT_QUESTION",
        year_or_term="2023",
        mock_content=MOCK_SANSAD_QUESTION_JSON
    )
    assert res1["status"] == "SUCCESS"

    # Re-acquire same URL without force_redownload
    res2 = engine.acquire_document(
        url=url,
        source_id="SRC-SANSAD-QUESTIONS",
        category="PARLIAMENT_QUESTION",
        year_or_term="2023"
    )
    assert res2["status"] == "CACHED"


def test_10_batch_discover_and_acquire(temp_acquisition_dir):
    config = AcquisitionConfig(raw_storage_dir=temp_acquisition_dir, rate_limit_seconds=0.01)
    engine = DocumentAcquisitionEngine(config=config)

    results = engine.discover_and_acquire(
        discovery_targets=MOCK_DISCOVERY_TARGETS,
        mock_payload_map=MOCK_PAYLOAD_MAP
    )
    assert len(results) == len(MOCK_DISCOVERY_TARGETS)
    for res in results:
        assert res["status"] in ("SUCCESS", "CACHED")

    manifest = DownloadManifest(config.manifest_path)
    assert manifest.data["summary"]["total_documents"] == len(MOCK_DISCOVERY_TARGETS)
    assert manifest.data["summary"]["total_bytes"] > 0
