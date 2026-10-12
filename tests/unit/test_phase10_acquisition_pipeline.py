"""
Phase 10.2 — Policy Evaluation Data Acquisition Pipeline Unit Tests.
=====================================================================

Validates:
1. Source Registry integration and domain whitelist compliance.
2. File type detection via magic byte signatures and content sniffing.
3. Publication date extraction (Government Orders, CAG reports, fiscal years).
4. Structured CSV dataset ingestion.
5. Structured JSON dataset ingestion.
6. HTML text and structured table parsing.
7. PDF extraction and OCR fallback detection for raster/scanned documents.
8. Corrupted/unreadable document error handling and logging.
9. Cryptographic SHA-256 checksums and duplicate payload detection.
10. DPDPA 2023 citizen privacy and PII sanitization.
11. Robots and disallowed path restriction enforcement.
12. End-to-end acquisition pipeline with metadata sidecar preservation.
"""

import os
import shutil
import tempfile
import pytest
from datetime import datetime

from backend.acquisition.policy_evaluation_acquisition import (
    PolicySourceConfig,
    PolicyEvaluationSourceRegistry,
    FileTypeDetector,
    PublicationDateExtractor,
    PolicyPDFExtractor,
    PolicyOCRFallbackHandler,
    PolicyHTMLExtractor,
    StructuredDatasetIngestor,
    PolicyStorageManager,
    PolicyAcquisitionLogger,
    PolicyEvaluationAcquisitionPipeline,
    PolicyAcquisitionResult,
)
from tests.fixtures.phase10_acquisition_fixtures import (
    get_sample_budget_csv,
    get_sample_beneficiaries_json,
    get_sample_policy_html,
    get_sample_scanned_pdf_bytes,
    get_sample_corrupted_pdf_bytes,
    get_sample_go_text,
    get_sample_cag_audit_text,
    get_sample_pii_text,
)


@pytest.fixture
def temp_storage():
    """Provides an isolated temporary directory for raw payload storage."""
    temp_dir = tempfile.mkdtemp(prefix="civiclens_phase10_test_")
    yield temp_dir
    shutil.rmtree(temp_dir, ignore_errors=True)


def test_1_source_registry_configuration():
    """Verify registry contains all authorized Phase 10 public sources."""
    registry = PolicyEvaluationSourceRegistry()
    sources = registry.list_sources()
    assert len(sources) >= 8

    source_ids = [s.source_id for s in sources]
    expected_ids = [
        "TN_BUDGET", "TN_GOV_POLICY", "CAG_AUDIT", "DATA_GOV_IN",
        "CENSUS_SRS", "SANSAD_PARLIAMENT", "TN_SPC", "LOCAL_FIXTURE"
    ]
    for exp in expected_ids:
        assert exp in source_ids, f"Expected source {exp} missing from registry"

    # Test URL lookup
    cag_config = registry.get_by_url("https://cag.gov.in/en/audit-reports/tamil-nadu")
    assert cag_config is not None
    assert cag_config.source_id == "CAG_AUDIT"
    assert cag_config.source_tier == 1

    tn_budget_config = registry.get_by_url("https://tnbudget.tn.gov.in/documents/ddg.pdf")
    assert tn_budget_config is not None
    assert tn_budget_config.source_id == "TN_BUDGET"


def test_2_file_type_detection():
    """Verify magic bytes and content-based file type detection."""
    # PDF Magic bytes
    pdf_fmt, pdf_mime = FileTypeDetector.detect_type(b"%PDF-1.4\nsome content")
    assert pdf_fmt == "PDF"
    assert pdf_mime == "application/pdf"

    # CSV Text
    csv_bytes = get_sample_budget_csv().encode("utf-8")
    csv_fmt, _ = FileTypeDetector.detect_type(csv_bytes, url_or_filename="budget_demands.csv")
    assert csv_fmt == "CSV"

    # JSON Text
    json_bytes = get_sample_beneficiaries_json().encode("utf-8")
    json_fmt, _ = FileTypeDetector.detect_type(json_bytes)
    assert json_fmt == "JSON"

    # HTML
    html_bytes = get_sample_policy_html().encode("utf-8")
    html_fmt, _ = FileTypeDetector.detect_type(html_bytes)
    assert html_fmt == "HTML"

    # Fallback extension
    txt_fmt, _ = FileTypeDetector.detect_type(b"Plain text note", url_or_filename="notes.txt")
    assert txt_fmt == "TXT"


def test_3_publication_date_extraction():
    """Verify publication date extraction from Government Orders, CAG reports, and fiscal cycles."""
    # Government Order Dated line
    go_text = get_sample_go_text()
    go_date = PublicationDateExtractor.extract_date(go_text)
    assert go_date == "2023-08-18"

    # CAG Report year
    cag_text = get_sample_cag_audit_text()
    cag_date = PublicationDateExtractor.extract_date(cag_text)
    assert cag_date == "2024-03-31"

    # Spelled out date in HTML
    html_text = get_sample_policy_html()
    html_date = PublicationDateExtractor.extract_date(html_text)
    assert html_date == "2024-06-25"

    # Fiscal Year string
    fy_date = PublicationDateExtractor.extract_date("Budget Estimates for the financial cycle 2024-2025")
    assert fy_date == "2024-2025"


def test_4_structured_csv_dataset_ingestion():
    """Verify structured CSV parsing with column headers and cell sanitization."""
    csv_data = get_sample_budget_csv()
    rows = StructuredDatasetIngestor.ingest_csv(csv_data)
    assert len(rows) == 4

    pudhumai_row = next(r for r in rows if "Pudhumai Penn" in r["scheme_name"])
    assert pudhumai_row["demand_no"] == "45"
    assert float(pudhumai_row["budget_estimate_cr"]) == 1000.00
    assert float(pudhumai_row["actual_expenditure_cr"]) == 950.40


def test_5_structured_json_dataset_ingestion():
    """Verify structured JSON dataset ingestion."""
    json_data = get_sample_beneficiaries_json()
    records = StructuredDatasetIngestor.ingest_json(json_data)
    assert isinstance(records, list)
    assert len(records) == 4

    chennai_record = next(r for r in records if r["district"] == "Chennai")
    assert chennai_record["registered_beneficiaries"] == 850200
    assert chennai_record["disbursed_cr"] == 85.02


def test_6_html_page_and_table_extraction():
    """Verify HTML table extraction into structured dictionaries and clean plain text."""
    html_data = get_sample_policy_html()
    extracted = PolicyHTMLExtractor.extract(html_data)

    assert "Social Welfare and Women Empowerment" in extracted["text"]
    assert len(extracted["tables"]) == 1

    table = extracted["tables"][0]
    assert len(table) == 2
    assert table[0]["Academic Year"] == "2022-2023"
    assert table[0]["Target Students"] == "250000"
    assert table[1]["Academic Year"] == "2023-2024"
    assert table[1]["Enrolled Beneficiaries"] == "412000"


def test_7_scanned_pdf_and_ocr_fallback():
    """Verify OCR fallback detection when a PDF lacks a digital text layer."""
    scanned_bytes = get_sample_scanned_pdf_bytes()
    pdf_res = PolicyPDFExtractor.parse_pdf(scanned_bytes)

    assert pdf_res["page_count"] >= 1
    assert pdf_res["scanned_pages"] >= 1
    assert pdf_res["ocr_status"] in ("OCR_REQUIRED_FALLBACK", "OCR_SUCCESS")
    assert "OCR REQUIRED" in pdf_res["text"] or pdf_res["ocr_used"] is True


def test_8_corrupted_pdf_error_handling_and_logging():
    """Verify that corrupt or unreadable PDF bytes fail gracefully without crashing."""
    corrupted_bytes = get_sample_corrupted_pdf_bytes()
    pdf_res = PolicyPDFExtractor.parse_pdf(corrupted_bytes)

    assert pdf_res["ocr_status"] == "PDF_CORRUPT_OR_UNREADABLE"
    assert "[PDF PARSE ERROR" in pdf_res["text"]


def test_9_sha256_checksum_and_duplicate_detection(temp_storage):
    """Verify SHA-256 calculation and payload deduplication."""
    storage = PolicyStorageManager(base_storage_dir=temp_storage)
    sample_bytes = b"Sample policy evaluation report raw payload bytes"

    hash1 = storage.compute_sha256(sample_bytes)
    assert len(hash1) == 64

    assert storage.is_duplicate(hash1) is False

    storage_path = storage.save_payload(
        raw_bytes=sample_bytes,
        sha256_hash=hash1,
        file_format="TXT",
        metadata={"title": "Test Report", "source_tier": 1}
    )
    assert os.path.exists(storage_path)

    # Secondary check must detect duplicate
    assert storage.is_duplicate(hash1) is True


def test_10_manual_import_and_pii_sanitization(temp_storage):
    """Verify manual document import and citizen PII sanitization in compliance with DPDPA 2023."""
    pipeline = PolicyEvaluationAcquisitionPipeline(
        storage_manager=PolicyStorageManager(base_storage_dir=temp_storage)
    )

    pii_text = get_sample_pii_text()
    raw_bytes = pii_text.encode("utf-8")

    result = pipeline.acquire_document(
        url_or_path="manual://TN_GOV_POLICY/grievance_sample.txt",
        source_id="TN_GOV_POLICY",
        document_title="Citizen Grievance Review",
        is_manual_import=True,
        file_bytes=raw_bytes
    )

    assert result.status == "SUCCESS"
    assert result.file_size_bytes == len(raw_bytes)
    # Verify PII was redacted
    assert "+91 9841023456" not in result.parsed_text
    assert "senthil.kumar99@gmail.com" not in result.parsed_text
    assert "[PHONE REDACTED]" in result.parsed_text or "[EMAIL REDACTED]" in result.parsed_text or len(result.parsed_text) < len(pii_text)


def test_11_disallowed_paths_and_domain_restriction(temp_storage):
    """Verify that disallowed paths and unwhitelisted domains are rejected and logged."""
    pipeline = PolicyEvaluationAcquisitionPipeline(
        storage_manager=PolicyStorageManager(base_storage_dir=temp_storage)
    )

    # 1. Disallowed path on authorized source
    restricted_url = "https://tnbudget.tn.gov.in/admin/secret_budget_draft.pdf"
    res1 = pipeline.acquire_document(url_or_path=restricted_url, source_id="TN_BUDGET")
    assert res1.status == "FAILED"
    assert "restricted" in res1.error_message.lower()

    # 2. Unwhitelisted domain
    unauthorized_url = "https://unauthorized-malicious-site.com/report.pdf"
    res2 = pipeline.acquire_document(url_or_path=unauthorized_url, source_id="TN_BUDGET")
    assert res2.status == "FAILED"
    assert "not whitelisted" in res2.error_message.lower()

    # Verify structured error logs were captured
    logs = pipeline.logger.get_logs()
    assert len(logs) >= 2


def test_12_end_to_end_acquisition_pipeline(temp_storage):
    """Verify complete pipeline execution: CSV dataset ingestion, date extraction, and sidecar metadata."""
    pipeline = PolicyEvaluationAcquisitionPipeline(
        storage_manager=PolicyStorageManager(base_storage_dir=temp_storage)
    )

    csv_content = get_sample_budget_csv().encode("utf-8")
    result = pipeline.acquire_document(
        url_or_path="file://local_test/budget_demand_45.csv",
        source_id="TN_BUDGET",
        document_title="Detailed Demands for Grants 2024-2025",
        is_manual_import=True,
        file_bytes=csv_content
    )

    assert result.status == "SUCCESS"
    assert result.file_format == "CSV"
    assert result.sha256_hash != ""
    assert len(result.extracted_tables) == 1
    assert len(result.extracted_tables[0]) == 4
    assert result.storage_path is not None
    assert os.path.exists(result.storage_path)

    # Verify sidecar metadata was written
    sidecar_path = os.path.join(temp_storage, f"{result.sha256_hash}.meta.json")
    assert os.path.exists(sidecar_path)

    # Test duplicate submission of same file
    dup_result = pipeline.acquire_document(
        url_or_path="file://local_test/budget_demand_45_dup.csv",
        source_id="TN_BUDGET",
        is_manual_import=True,
        file_bytes=csv_content
    )
    assert dup_result.status == "DUPLICATE"
    assert dup_result.is_duplicate is True
