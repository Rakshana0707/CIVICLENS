"""
Unit tests for Phase 5 Financial Document Acquisition Engine.

Verifies acquisition configuration, format detection (PDF, HTML, CSV, XLSX, JSON),
SHA-256 checksum generation, caching, duplicate detection, retries, error logging,
filtering rules, and manifest tracking.
"""

import os
import json
import tempfile
import shutil
import pytest
from backend.funding.acquisition import (
    DocumentAcquisitionEngine,
    AcquisitionConfig,
    SourceRegistry,
    FileTypeDetector,
    DocumentFormat,
    DownloadManifest
)


@pytest.fixture
def temp_acquisition_dir():
    temp_dir = tempfile.mkdtemp(prefix="civiclens_test_funding_")
    yield temp_dir
    shutil.rmtree(temp_dir, ignore_errors=True)


class TestFileTypeDetector:

    def test_pdf_detection(self):
        pdf_bytes = b"%PDF-1.4 sample pdf document header content"
        fmt = FileTypeDetector.detect_format(pdf_bytes, "report.pdf")
        assert fmt == DocumentFormat.PDF

    def test_html_detection(self):
        html_bytes = b"<!DOCTYPE html><html><head><title>ECI Report</title></head><body>Test</body></html>"
        fmt = FileTypeDetector.detect_format(html_bytes, "report.html")
        assert fmt == DocumentFormat.HTML

    def test_csv_detection(self):
        csv_bytes = b"party_code,donor_name,amount_inr\nDMK,Corp A,500000\nAIADMK,Corp B,300000\n"
        fmt = FileTypeDetector.detect_format(csv_bytes, "data.csv")
        assert fmt == DocumentFormat.CSV

    def test_xlsx_detection(self):
        xlsx_bytes = b"PK\x03\x04\x14\x00\x06\x00 sample zip spreadsheet content"
        fmt = FileTypeDetector.detect_format(xlsx_bytes, "financials.xlsx")
        assert fmt == DocumentFormat.XLSX

    def test_json_detection(self):
        json_bytes = b'{"party": "DMK", "year": "FY2021-22", "income": 300000000}'
        fmt = FileTypeDetector.detect_format(json_bytes, "feed.json")
        assert fmt == DocumentFormat.JSON


class TestDocumentAcquisitionEngine:

    def test_source_registry_configuration(self):
        registry = SourceRegistry()
        eci_source = registry.get_source("SRC-ECI-24A")
        assert eci_source is not None
        assert eci_source["allowed_domain"] == "eci.gov.in"
        assert registry.is_domain_allowed("SRC-ECI-24A", "https://www.eci.gov.in/contribution-reports")
        assert not registry.is_domain_allowed("SRC-ECI-24A", "https://unauthorized-domain.com/data")

    def test_acquisition_and_checksum_generation(self, temp_acquisition_dir):
        config = AcquisitionConfig(raw_storage_dir=temp_acquisition_dir)
        engine = DocumentAcquisitionEngine(config=config)

        sample_pdf = b"%PDF-1.4 Statutory Form 24A test payload for DMK FY2021-22"
        target_url = "https://www.eci.gov.in/files/Form24A_DMK_FY2021-22.pdf"

        res = engine.acquire_document(
            url=target_url,
            source_id="SRC-ECI-24A",
            party_code="DMK",
            financial_year="FY2021-22",
            mock_content=sample_pdf
        )

        assert res["status"] == "SUCCESS"
        assert res["detected_format"] == DocumentFormat.PDF
        assert res["sha256_hash"] == engine.compute_sha256(sample_pdf)
        assert os.path.exists(res["file_path"])

    def test_caching_mechanism(self, temp_acquisition_dir):
        config = AcquisitionConfig(raw_storage_dir=temp_acquisition_dir)
        engine = DocumentAcquisitionEngine(config=config)

        sample_pdf = b"%PDF-1.4 Cached test content for AIADMK"
        target_url = "https://www.eci.gov.in/files/Form24A_AIADMK_FY2021-22.pdf"

        # First acquisition
        res1 = engine.acquire_document(
            url=target_url,
            source_id="SRC-ECI-24A",
            party_code="AIADMK",
            financial_year="FY2021-22",
            mock_content=sample_pdf
        )
        assert res1["status"] == "SUCCESS"

        # Second acquisition should hit cache
        res2 = engine.acquire_document(
            url=target_url,
            source_id="SRC-ECI-24A",
            party_code="AIADMK",
            financial_year="FY2021-22",
            mock_content=sample_pdf
        )
        assert res2["status"] == "CACHED"
        assert res2["file_path"] == res1["file_path"]

    def test_duplicate_detection(self, temp_acquisition_dir):
        config = AcquisitionConfig(raw_storage_dir=temp_acquisition_dir)
        engine = DocumentAcquisitionEngine(config=config)

        identical_payload = b"%PDF-1.4 Identical binary report payload published under two different URLs"

        url1 = "https://www.eci.gov.in/files/Doc1.pdf"
        url2 = "https://www.eci.gov.in/files/Doc2_Mirror.pdf"

        res1 = engine.acquire_document(
            url=url1,
            source_id="SRC-ECI-24A",
            party_code="INC",
            financial_year="FY2021-22",
            mock_content=identical_payload
        )
        assert res1["is_duplicate"] is False

        res2 = engine.acquire_document(
            url=url2,
            source_id="SRC-ECI-24A",
            party_code="INC",
            financial_year="FY2021-22",
            mock_content=identical_payload
        )
        assert res2["is_duplicate"] is True
        assert res2["duplicate_of"] == res1["document_id"]

    def test_filtering_rules(self, temp_acquisition_dir):
        config = AcquisitionConfig(
            raw_storage_dir=temp_acquisition_dir,
            allowed_parties=["DMK", "AIADMK"],
            allowed_years=["FY2021-22"]
        )
        engine = DocumentAcquisitionEngine(config=config)

        sample_pdf = b"%PDF-1.4 Test content"

        # Disallowed party (BJP) -> SKIPPED
        res1 = engine.acquire_document(
            url="https://www.eci.gov.in/files/BJP.pdf",
            source_id="SRC-ECI-24A",
            party_code="BJP",
            financial_year="FY2021-22",
            mock_content=sample_pdf
        )
        assert res1["status"] == "SKIPPED"

        # Disallowed year (FY2014-15) -> SKIPPED
        res2 = engine.acquire_document(
            url="https://www.eci.gov.in/files/DMK_2014.pdf",
            source_id="SRC-ECI-24A",
            party_code="DMK",
            financial_year="FY2014-15",
            mock_content=sample_pdf
        )
        assert res2["status"] == "SKIPPED"

    def test_failed_download_error_logging(self, temp_acquisition_dir):
        config = AcquisitionConfig(raw_storage_dir=temp_acquisition_dir, max_retries=1)
        engine = DocumentAcquisitionEngine(config=config)

        # Attempt downloading from invalid non-whitelisted domain
        unauthorized_url = "https://unauthorized-domain.org/malicious_report.pdf"
        res = engine.acquire_document(
            url=unauthorized_url,
            source_id="SRC-ECI-24A",
            party_code="DMK",
            financial_year="FY2021-22"
        )

        assert res["status"] == "FAILED"
        assert len(engine.manifest.data["failed_downloads"]) >= 1
        assert engine.manifest.data["failed_downloads"][-1]["url"] == unauthorized_url

    def test_manifest_file_creation_and_update(self, temp_acquisition_dir):
        config = AcquisitionConfig(raw_storage_dir=temp_acquisition_dir)
        engine = DocumentAcquisitionEngine(config=config)

        sample_payload = b'{"party": "DMK", "donations_count": 42}'
        engine.acquire_document(
            url="https://www.eci.gov.in/feed.json",
            source_id="SRC-ECI-24A",
            party_code="DMK",
            financial_year="FY2021-22",
            mock_content=sample_payload
        )

        manifest_file = config.manifest_path
        assert os.path.exists(manifest_file)

        with open(manifest_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        assert data["summary"]["total_documents"] >= 1
        assert data["summary"]["unique_sha256_hashes"] >= 1
        assert len(data["documents"]) >= 1
