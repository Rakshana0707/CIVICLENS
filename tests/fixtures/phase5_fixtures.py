"""
Phase 5 Test Fixtures for CIVICLENS TN Political Funding Transparency Analyzer.

IMPORTANT: All datasets and records contained in this file are EXPLICITLY MOCK
TEST FIXTURES used exclusively for verifying system architecture, database schemas,
data validators, and statistical anomaly algorithms.
They do NOT represent real financial records or real political transactions.
"""

from typing import Dict, Any, List

# Explicitly labelled mock political parties fixture
MOCK_PARTIES_FIXTURE: List[Dict[str, Any]] = [
    {
        "party_id": "PARTY_TN_DMK",
        "party_name": "Dravida Munnetra Kazhagam",
        "party_code": "DMK",
        "party_type": "STATE_RECOGNIZED_TN",
        "symbol": "Rising Sun",
        "eci_registration_no": "ECI/REG/TN/001",
        "hq_state": "Tamil Nadu"
    },
    {
        "party_id": "PARTY_TN_AIADMK",
        "party_name": "All India Anna Dravida Munnetra Kazhagam",
        "party_code": "AIADMK",
        "party_type": "STATE_RECOGNIZED_TN",
        "symbol": "Two Leaves",
        "eci_registration_no": "ECI/REG/TN/002",
        "hq_state": "Tamil Nadu"
    },
    {
        "party_id": "PARTY_NAT_INC",
        "party_name": "Indian National Congress",
        "party_code": "INC",
        "party_type": "NATIONAL",
        "symbol": "Hand",
        "eci_registration_no": "ECI/REG/NAT/001",
        "hq_state": "New Delhi"
    }
]

# Explicitly labelled mock financial documents fixture
MOCK_FINANCIAL_DOCUMENTS_FIXTURE: List[Dict[str, Any]] = [
    {
        "document_id": "DOC_2021_DMK_24A",
        "source_id": "SRC-ECI-01",
        "party_id": "PARTY_TN_DMK",
        "financial_year_id": "FY2021-22",
        "filing_type": "Form24A",
        "file_path": "scratch/raw_funding_docs/SRC-ECI-01/FY2021-22/DMK_Form24A_FY2021-22.pdf",
        "file_hash_sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        "submission_date": "2022-09-15",
        "page_count": 14,
        "ocr_applied": False
    },
    {
        "document_id": "DOC_2021_DMK_AUDIT",
        "source_id": "SRC-ECI-01",
        "party_id": "PARTY_TN_DMK",
        "financial_year_id": "FY2021-22",
        "filing_type": "AnnualAudit",
        "file_path": "scratch/raw_funding_docs/SRC-ECI-01/FY2021-22/DMK_Audit_FY2021-22.pdf",
        "file_hash_sha256": "8f4e3c2b1a90d876543210feebcdab9876543210feebcdab9876543210feebcd",
        "submission_date": "2022-10-31",
        "page_count": 28,
        "ocr_applied": True
    }
]

# Explicitly labelled mock contributions fixture (Form 24A > 20k)
MOCK_CONTRIBUTIONS_FIXTURE: List[Dict[str, Any]] = [
    {
        "contribution_id": "CONT_2021_001",
        "document_id": "DOC_2021_DMK_24A",
        "party_id": "PARTY_TN_DMK",
        "donor_id": "DONOR_CORP_101",
        "financial_year_id": "FY2021-22",
        "amount_inr": 5000000.0,
        "payment_mode": "Cheque",
        "contribution_date": "2021-06-15",
        "pan_or_cin_provided": True,
        "raw_donor_name": "Test Infrastructure Pvt Ltd"
    },
    {
        "contribution_id": "CONT_2021_002",
        "document_id": "DOC_2021_DMK_24A",
        "party_id": "PARTY_TN_DMK",
        "donor_id": "DONOR_CORP_102",
        "financial_year_id": "FY2021-22",
        "amount_inr": 3000000.0,
        "payment_mode": "EFT",
        "contribution_date": "2021-08-20",
        "pan_or_cin_provided": True,
        "raw_donor_name": "Apex Enterprise Ltd"
    },
    {
        "contribution_id": "CONT_2021_003",
        "document_id": "DOC_2021_DMK_24A",
        "party_id": "PARTY_TN_DMK",
        "donor_id": "DONOR_TRUST_201",
        "financial_year_id": "FY2021-22",
        "amount_inr": 10000000.0,
        "payment_mode": "ElectoralTrust",
        "contribution_date": "2021-11-10",
        "pan_or_cin_provided": True,
        "raw_donor_name": "Prudent Electoral Trust"
    }
]

# Explicitly labelled mock party financial statement fixture
MOCK_FINANCIAL_STATEMENT_FIXTURE: Dict[str, Any] = {
    "statement_id": "STMT_2021_DMK",
    "party_id": "PARTY_TN_DMK",
    "financial_year_id": "FY2021-22",
    "total_income": 300000000.0,
    "total_expenditure": 220000000.0,
    "net_surplus_deficit": 80000000.0,
    "grant_from_electoral_trusts": 100000000.0,
    "donations_above_20k": 18000000.0,
    "donations_below_20k": 50000000.0,
    "electoral_bond_income": 120000000.0,
    "other_income": 12000000.0,
    "auditor_name": "Mock Audit Associates",
    "audit_date": "2022-10-25"
}

# Explicitly labelled mock transaction stream for Benford's Law testing
MOCK_BENFORD_NORMAL_STREAM: List[float] = [
    124000.0, 185000.0, 192000.0, 245000.0, 290000.0, 310000.0, 350000.0,
    420000.0, 480000.0, 530000.0, 610000.0, 720000.0, 840000.0, 910000.0,
    1150000.0, 1380000.0, 1750000.0, 2100000.0, 2600000.0, 3400000.0
]

MOCK_BENFORD_ANOMALOUS_STREAM: List[float] = [
    500000.0, 550000.0, 520000.0, 580000.0, 590000.0, 510000.0, 540000.0,
    570000.0, 530000.0, 560000.0, 500000.0, 550000.0, 520000.0, 580000.0
]
