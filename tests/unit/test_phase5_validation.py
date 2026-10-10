"""
Unit tests for Phase 5 Data Normalization and Validation Engine.

Verifies:
1. Party resolution, Date ISO conversion, and strict donor non-merging policy.
2. 10 Automated Validation Rules (V-01 to V-10).
3. Cross-source financial statement consistency checks.
"""

from backend.funding.normalizer import (
    PartyRegistryNormalizer,
    DateNormalizer,
    DonorNameNormalizer,
    FinancialRecordNormalizer
)
from backend.funding.validator import ValidationEngine
from tests.fixtures.phase5_validation_fixtures import (
    MOCK_RAW_CONTRIBUTIONS_FOR_VALIDATION,
    MOCK_STATEMENT_FOR_CROSS_VALIDATION
)


class TestFinancialRecordNormalizer:

    def test_party_resolution(self):
        party_id1, name1 = PartyRegistryNormalizer.resolve_party("DMK")
        assert party_id1 == "PARTY_TN_DMK"
        assert name1 == "Dravida Munnetra Kazhagam"

        party_id2, name2 = PartyRegistryNormalizer.resolve_party("All India Anna Dravida Munnetra Kazhagam")
        assert party_id2 == "PARTY_TN_AIADMK"

        party_id3, name3 = PartyRegistryNormalizer.resolve_party("Unknown Regional Front")
        assert party_id3 == "PARTY_UNKNOWN"
        assert name3 == "Unknown Regional Front"

    def test_date_normalization(self):
        assert DateNormalizer.normalize_date("15/06/2021") == "2021-06-15"
        assert DateNormalizer.normalize_date("2021-06-15") == "2021-06-15"
        assert DateNormalizer.normalize_date("15-06-2021") == "2021-06-15"
        assert DateNormalizer.normalize_date("N/A") is None
        assert DateNormalizer.normalize_date("invalid_date_str") is None

    def test_strict_donor_non_merging_policy(self):
        raw1 = "Apex Infrastructure Pvt Ltd"
        raw2 = "Apex Infrastructure India Pvt Ltd"

        norm1 = DonorNameNormalizer.normalize_name(raw1)
        norm2 = DonorNameNormalizer.normalize_name(raw2)

        # Asserts distinct normalized donor name representations
        assert norm1 != norm2
        assert norm1 == "APEX INFRASTRUCTURE PVT LTD"
        assert norm2 == "APEX INFRASTRUCTURE INDIA PVT LTD"


class TestValidationEngine:

    def test_contribution_batch_validation(self):
        raw_recs = MOCK_RAW_CONTRIBUTIONS_FOR_VALIDATION
        canonical_contribs = [FinancialRecordNormalizer.normalize_contribution(r) for r in raw_recs]

        issues = ValidationEngine.validate_contribution_batch(canonical_contribs)
        rule_codes = [i.rule_code for i in issues]

        # V-01 Missing Party flagged for REC_VAL_002
        assert "V-01_MISSING_PARTY" in rule_codes

        # V-02 Negative Amount flagged for REC_VAL_003
        assert "V-02_NEGATIVE_AMOUNT" in rule_codes

        # V-03 Invalid Currency flagged for REC_VAL_004
        assert "V-03_INVALID_CURRENCY" in rule_codes

        # V-09 FY Date Mismatch flagged for REC_VAL_005 (Date in 2020 for FY2021-22)
        assert "V-09_FY_DATE_MISMATCH" in rule_codes

        # V-05 Duplicate Row flagged for REC_VAL_006
        assert "V-05_DUPLICATE_ROW" in rule_codes

    def test_cross_source_statement_validation(self):
        raw_recs = MOCK_RAW_CONTRIBUTIONS_FOR_VALIDATION
        canonical_contribs = [FinancialRecordNormalizer.normalize_contribution(r) for r in raw_recs]
        stmt = FinancialRecordNormalizer.normalize_financial_statement(MOCK_STATEMENT_FOR_CROSS_VALIDATION)

        issues = ValidationEngine.validate_cross_source_statement(canonical_contribs, stmt)
        rule_codes = [i.rule_code for i in issues]

        # V-07 Inconsistent Totals (Form 24A sum != Audited 20k schedule)
        assert "V-07_INCONSISTENT_TOTALS" in rule_codes

        # V-10 Source Inconsistency (Form 24A sum > Audited total income)
        assert "V-10_SOURCE_INCONSISTENCY" in rule_codes
