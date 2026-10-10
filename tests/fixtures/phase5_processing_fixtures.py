"""
Phase 5 Processing Test Fixtures.

Contains explicitly labelled mock document payloads, table matrices, and text pages
used strictly for testing document parsing, scanned PDF detection, table extraction,
amount normalization, and page provenance.
"""

from typing import Dict, Any, List

# Mock native digital PDF document payload (Form 24A style)
MOCK_NATIVE_DOC_PAYLOAD: Dict[str, Any] = {
    "document_id": "DOC_2021_DMK_24A_TEST",
    "source_url": "https://www.eci.gov.in/files/Form24A_DMK_FY2021-22.pdf",
    "default_party_code": "DMK",
    "default_financial_year": "FY2021-22",
    "raw_text_pages": [
        {
            "page_number": 1,
            "text": "ELECTION COMMISSION OF INDIA\nFORM 24A [See rule 8A]\nREPORT OF CONTRIBUTIONS RECEIVED BY DRAVIDA MUNNETRA KAZHAGAM FOR FY 2021-22",
            "tables": [
                [
                    ["Sl No", "Name of Donor", "Address", "Amount (Rs.)", "Payment Mode", "Date", "Remarks"],
                    ["1", "Apex Enterprise Ltd", "12 Main Road Chennai", "50,00,000", "Cheque", "15/06/2021", "PAN Provided"],
                    ["2", "Beta Infra Private Limited", "45 Park Avenue Madurai", "25 Lakhs", "EFT", "20/07/2021", "CIN Provided"],
                    ["3", "Test Donor Person", "78 Beach Road Tuticorin", "Nil", "N/A", "10/08/2021", "Zero Contribution"],
                    ["4", "Confidential Supporter", "Undisclosed", "Undisclosed", "Unknown", "N/A", "Redacted"],
                    ["5", "Malformed Entry Corp", "Address Here", "invalid#num", "Cash", "01/09/2021", "Parse Error"]
                ]
            ]
        },
        {
            "page_number": 2,
            "text": "ELECTION COMMISSION OF INDIA\nFORM 24A CONTINUATION SHEET - DRAVIDA MUNNETRA KAZHAGAM FY 2021-22",
            "tables": [
                [
                    ["Sl No", "Name of Donor", "Address", "Amount (Rs.)", "Payment Mode", "Date", "Remarks"],
                    ["6", "Gamma Holdings Cr", "100 High St Trichy", "1.5 Crore", "DD", "05/10/2021", "DD No 458921"],
                    ["7", "Delta Logistics", "50 Bypass Salem", "100000", "Cheque", "12/11/2021", "-"]
                ]
            ]
        }
    ]
}

# Mock scanned PDF page (low text density)
MOCK_SCANNED_PAGE_TEXT = "   ECI STAMP 2021   "
