"""
Unit tests for Phase 5 Document Parsing & Table Extraction Engine.

Verifies:
1. Amount normalization and strict value status distinction (ZERO, MISSING, NOT_DISCLOSED, NOT_APPLICABLE, EXTRACTION_FAILURE).
2. Scanned PDF page detection via text density analysis.
3. Table header and column pattern detection.
4. Financial Year and Party Code extraction.
5. Full payload processing with page-level provenance, confidence scoring, and record retention.
"""

from backend.funding.processor import (
    AmountNormalizer,
    AmountStatus,
    ScannedPdfDetector,
    HeaderColumnDetector,
    FinancialDocumentProcessor,
    ExtractionMethod
)
from tests.fixtures.phase5_processing_fixtures import (
    MOCK_NATIVE_DOC_PAYLOAD,
    MOCK_SCANNED_PAGE_TEXT
)


class TestAmountNormalizer:

    def test_valid_numeric_amounts(self):
        val1, status1, raw1 = AmountNormalizer.normalize("50,00,000")
        assert val1 == 5000000.0
        assert status1 == AmountStatus.VALID_NUMERIC

        val2, status2, raw2 = AmountNormalizer.normalize("25 Lakhs")
        assert val2 == 2500000.0
        assert status2 == AmountStatus.VALID_NUMERIC

        val3, status3, raw3 = AmountNormalizer.normalize("1.5 Crore")
        assert val3 == 15000000.0
        assert status3 == AmountStatus.VALID_NUMERIC

        val4, status4, raw4 = AmountNormalizer.normalize("₹ 1,00,000/-")
        assert val4 == 100000.0
        assert status4 == AmountStatus.VALID_NUMERIC

    def test_explicit_zero_amounts(self):
        val1, status1, _ = AmountNormalizer.normalize("Nil")
        assert val1 == 0.0
        assert status1 == AmountStatus.ZERO

        val2, status2, _ = AmountNormalizer.normalize("0")
        assert val2 == 0.0
        assert status2 == AmountStatus.ZERO

        val3, status3, _ = AmountNormalizer.normalize("NIL")
        assert val3 == 0.0
        assert status3 == AmountStatus.ZERO

    def test_missing_amounts(self):
        val1, status1, _ = AmountNormalizer.normalize("")
        assert val1 is None
        assert status1 == AmountStatus.MISSING

        val2, status2, _ = AmountNormalizer.normalize(None)
        assert val2 is None
        assert status2 == AmountStatus.MISSING

    def test_not_disclosed_amounts(self):
        val1, status1, _ = AmountNormalizer.normalize("Undisclosed")
        assert val1 is None
        assert status1 == AmountStatus.NOT_DISCLOSED

        val2, status2, _ = AmountNormalizer.normalize("Redacted")
        assert val2 is None
        assert status2 == AmountStatus.NOT_DISCLOSED

    def test_not_applicable_amounts(self):
        val1, status1, _ = AmountNormalizer.normalize("N/A")
        assert val1 is None
        assert status1 == AmountStatus.NOT_APPLICABLE

        val2, status2, _ = AmountNormalizer.normalize("-")
        assert val2 is None
        assert status2 == AmountStatus.NOT_APPLICABLE

    def test_extraction_failure_amounts(self):
        val1, status1, _ = AmountNormalizer.normalize("invalid#num")
        assert val1 is None
        assert status1 == AmountStatus.EXTRACTION_FAILURE


class TestScannedPdfDetector:

    def test_native_page_detection(self):
        native_text = "ELECTION COMMISSION OF INDIA FORM 24A REPORT OF CONTRIBUTIONS RECEIVED BY DMK FOR FY 2021-22"
        is_scanned = ScannedPdfDetector.inspect_page_text_density(native_text)
        assert is_scanned is False

    def test_scanned_page_detection(self):
        is_scanned = ScannedPdfDetector.inspect_page_text_density(MOCK_SCANNED_PAGE_TEXT)
        assert is_scanned is True


class TestHeaderColumnDetector:

    def test_detect_donor_name_column(self):
        col = HeaderColumnDetector.detect_column_type("Name of Donor / Contributor")
        assert col == "donor_name"

    def test_detect_amount_column(self):
        col = HeaderColumnDetector.detect_column_type("Amount (in Rs.)")
        assert col == "amount"

    def test_detect_payment_mode_column(self):
        col = HeaderColumnDetector.detect_column_type("Mode of Payment (Cheque/DD/EFT)")
        assert col == "payment_mode"


class TestFinancialDocumentProcessor:

    def test_financial_year_extraction(self):
        text = "Form 24A contribution report for FY 2021-22 submitted to ECI"
        fy = FinancialDocumentProcessor.extract_financial_year(text)
        assert fy == "FY2021-22"

    def test_party_code_extraction(self):
        text = "Report of contributions received by Dravida Munnetra Kazhagam during FY 2021-22"
        party = FinancialDocumentProcessor.extract_party_code(text)
        assert party == "DMK"

    def test_full_document_payload_processing(self):
        payload = MOCK_NATIVE_DOC_PAYLOAD
        res = FinancialDocumentProcessor.process_raw_document_payload(
            document_id=payload["document_id"],
            source_url=payload["source_url"],
            raw_text_pages=payload["raw_text_pages"],
            default_party_code=payload["default_party_code"],
            default_financial_year=payload["default_financial_year"]
        )

        assert res["document_id"] == "DOC_2021_DMK_24A_TEST"
        assert res["party_code"] == "DMK"
        assert res["financial_year"] == "FY2021-22"
        assert res["total_pages"] == 2
        assert res["total_records_extracted"] == 7

        records = res["records"]
        # Record 1: 50,00,000 -> VALID_NUMERIC
        r1 = records[0]
        assert r1["normalized_amount_inr"] == 5000000.0
        assert r1["amount_status"] == AmountStatus.VALID_NUMERIC.value
        assert r1["donor_name"] == "Apex Enterprise Ltd"
        assert r1["page_number"] == 1

        # Record 2: 25 Lakhs -> VALID_NUMERIC (2,500,000)
        r2 = records[1]
        assert r2["normalized_amount_inr"] == 2500000.0
        assert r2["amount_status"] == AmountStatus.VALID_NUMERIC.value

        # Record 3: Nil -> ZERO (0.0)
        r3 = records[2]
        assert r3["normalized_amount_inr"] == 0.0
        assert r3["amount_status"] == AmountStatus.ZERO.value

        # Record 4: Undisclosed -> NOT_DISCLOSED (None)
        r4 = records[3]
        assert r4["normalized_amount_inr"] is None
        assert r4["amount_status"] == AmountStatus.NOT_DISCLOSED.value

        # Record 5: invalid#num -> EXTRACTION_FAILURE
        r5 = records[4]
        assert r5["normalized_amount_inr"] is None
        assert r5["amount_status"] == AmountStatus.EXTRACTION_FAILURE.value

        # Record 6: 1.5 Crore -> VALID_NUMERIC (15,000,000)
        r6 = records[5]
        assert r6["normalized_amount_inr"] == 15000000.0
        assert r6["page_number"] == 2
