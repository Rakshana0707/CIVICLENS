"""
Phase 5 Data Validation Test Fixtures.

Contains explicitly labelled mock contributions, financial statements, and party profiles
designed to test all 10 automated validation rules (V-01 to V-10) and non-merging policies.
"""

from typing import Dict, Any, List

MOCK_RAW_CONTRIBUTIONS_FOR_VALIDATION: List[Dict[str, Any]] = [
    # 1. Valid record
    {
        "record_id": "REC_VAL_001",
        "document_id": "DOC_2021_DMK_24A",
        "party_code": "DMK",
        "financial_year": "FY2021-22",
        "donor_name": "Apex Enterprise Ltd",
        "raw_amount_str": "50,00,000",
        "normalized_amount_inr": 5000000.0,
        "amount_status": "VALID_NUMERIC",
        "payment_mode": "Cheque",
        "payment_date": "15/06/2021",
        "raw_row": "1 | Apex Enterprise Ltd | 50,00,000 | Cheque | 15/06/2021",
        "extraction_confidence": 0.95,
        "page_number": 1
    },
    # 2. V-01 Missing Party
    {
        "record_id": "REC_VAL_002",
        "document_id": "DOC_2021_UNK_24A",
        "party_code": "UNRECOGNIZED_XYZ_PARTY",
        "financial_year": "FY2021-22",
        "donor_name": "Unknown Supporter",
        "raw_amount_str": "10,00,000",
        "normalized_amount_inr": 1000000.0,
        "amount_status": "VALID_NUMERIC",
        "payment_mode": "EFT",
        "payment_date": "20/07/2021",
        "raw_row": "2 | Unknown Supporter | 10,00,000 | EFT | 20/07/2021",
        "extraction_confidence": 0.90,
        "page_number": 1
    },
    # 3. V-02 Negative Amount
    {
        "record_id": "REC_VAL_003",
        "document_id": "DOC_2021_DMK_24A",
        "party_code": "DMK",
        "financial_year": "FY2021-22",
        "donor_name": "Refunded Donor Corp",
        "raw_amount_str": "-500000",
        "normalized_amount_inr": -500000.0,
        "amount_status": "VALID_NUMERIC",
        "payment_mode": "Cheque",
        "payment_date": "10/08/2021",
        "raw_row": "3 | Refunded Donor Corp | -500000 | Cheque | 10/08/2021",
        "extraction_confidence": 0.85,
        "page_number": 1
    },
    # 4. V-03 Invalid Currency
    {
        "record_id": "REC_VAL_004",
        "document_id": "DOC_2021_DMK_24A",
        "party_code": "DMK",
        "financial_year": "FY2021-22",
        "donor_name": "Corrupt Cell Donor",
        "raw_amount_str": "invalid#num",
        "normalized_amount_inr": None,
        "amount_status": "EXTRACTION_FAILURE",
        "payment_mode": "Cash",
        "payment_date": "01/09/2021",
        "raw_row": "4 | Corrupt Cell Donor | invalid#num | Cash | 01/09/2021",
        "extraction_confidence": 0.40,
        "page_number": 1
    },
    # 5. V-04 Malformed Date & V-09 FY Mismatch (Date in 2020 for FY2021-22)
    {
        "record_id": "REC_VAL_005",
        "document_id": "DOC_2021_DMK_24A",
        "party_code": "DMK",
        "financial_year": "FY2021-22",
        "donor_name": "Early Date Corp",
        "raw_amount_str": "2,00,000",
        "normalized_amount_inr": 200000.0,
        "amount_status": "VALID_NUMERIC",
        "payment_mode": "DD",
        "payment_date": "15/05/2020",  # FY2020-21 date inside FY2021-22 record
        "raw_row": "5 | Early Date Corp | 2,00,000 | DD | 15/05/2020",
        "extraction_confidence": 0.85,
        "page_number": 1
    },
    # 6. V-05 Duplicate row (identical to REC_VAL_001)
    {
        "record_id": "REC_VAL_006",
        "document_id": "DOC_2021_DMK_24A",
        "party_code": "DMK",
        "financial_year": "FY2021-22",
        "donor_name": "Apex Enterprise Ltd",
        "raw_amount_str": "50,00,000",
        "normalized_amount_inr": 5000000.0,
        "amount_status": "VALID_NUMERIC",
        "payment_mode": "Cheque",
        "payment_date": "15/06/2021",
        "raw_row": "1 | Apex Enterprise Ltd | 50,00,000 | Cheque | 15/06/2021",
        "extraction_confidence": 0.95,
        "page_number": 1
    }
]

# Mock financial statement for cross-validation testing
MOCK_STATEMENT_FOR_CROSS_VALIDATION: Dict[str, Any] = {
    "statement_id": "STMT_DMK_2021",
    "party_code": "DMK",
    "financial_year": "FY2021-22",
    "income_categories": {
        "donations_above_20k": 1000000.0,  # 10 Lakhs summary, but itemized sum in REC_VAL_001 is 50 Lakhs -> V-07 mismatch
    },
    "total_income": 4000000.0  # 40 Lakhs total, but itemized sum is 50 Lakhs -> V-10 source inconsistency
}
