"""
Phase 10.2 — Policy Evaluation Acquisition Pipeline Test Fixtures.
===================================================================

Provides realistic offline test fixtures for:
1. Detailed Demands for Grants (CSV)
2. Scheme Beneficiary Monitoring Datasets (JSON)
3. Government Department Policy Note web page (HTML with tables)
4. Valid raster/scanned PDF bytes (triggering OCR fallback)
5. Corrupted PDF bytes (testing error handling and logging)
6. Government Order with date metadata
7. CAG Audit Report text with report number and year
8. Raw citizen grievance records with PII for sanitization validation

All fixtures carry is_test_fixture=True or are strictly labeled test utilities.
"""

import io
from typing import Dict, Any, List


def get_sample_budget_csv() -> str:
    """Detailed Demands for Grants (DDG) sample table in CSV."""
    return (
        "demand_no,scheme_head,scheme_name,budget_estimate_cr,revised_estimate_cr,actual_expenditure_cr\n"
        "15,2215-01-102-AA,Rural Water Supply Mission,450.00,420.50,398.20\n"
        "20,2210-01-110-AB,Makkalai Thedi Maruthuvam,250.00,240.00,235.80\n"
        "45,2235-02-103-AD,Pudhumai Penn Higher Education,1000.00,980.00,950.40\n"
        "45,2235-02-103-AE,Kalaignar Magalir Urimai Thittam,12000.00,11850.00,11620.00\n"
    )


def get_sample_beneficiaries_json() -> str:
    """Scheme beneficiary observation dataset in JSON."""
    return (
        '[\n'
        '  {"district": "Chennai", "scheme_id": "SCH-TEST-KMUT", "registered_beneficiaries": 850200, "disbursed_cr": 85.02},\n'
        '  {"district": "Madurai", "scheme_id": "SCH-TEST-KMUT", "registered_beneficiaries": 420100, "disbursed_cr": 42.01},\n'
        '  {"district": "Coimbatore", "scheme_id": "SCH-TEST-KMUT", "registered_beneficiaries": 395400, "disbursed_cr": 39.54},\n'
        '  {"district": "Dharmapuri", "scheme_id": "SCH-TEST-KMUT", "registered_beneficiaries": 240800, "disbursed_cr": 24.08}\n'
        ']'
    )


def get_sample_policy_html() -> str:
    """Department Policy Note web page containing structured HTML table and text."""
    return """<!DOCTYPE html>
<html lang="en">
<head>
    <title>Social Welfare Department - Policy Note 2024-2025</title>
</head>
<body>
    <h1>Government of Tamil Nadu - Social Welfare and Women Empowerment Department</h1>
    <p>Policy Note for Demand No. 45 for the year 2024-2025. Published on 25th June, 2024.</p>
    <div class="content">
        <h2>Pudhumai Penn Scheme Progress</h2>
        <table border="1" id="pudhumai-progress">
            <thead>
                <tr>
                    <th>Academic Year</th>
                    <th>Target Students</th>
                    <th>Enrolled Beneficiaries</th>
                    <th>Disbursement Cr</th>
                </tr>
            </thead>
            <tbody>
                <tr>
                    <td>2022-2023</td>
                    <td>250000</td>
                    <td>238000</td>
                    <td>238.00</td>
                </tr>
                <tr>
                    <td>2023-2024</td>
                    <td>400000</td>
                    <td>412000</td>
                    <td>412.00</td>
                </tr>
            </tbody>
        </table>
    </div>
</body>
</html>"""


def get_sample_scanned_pdf_bytes() -> bytes:
    """Generates valid PDF bytes without text layer (simulating scanned raster document)."""
    try:
        import pypdfium2  # type: ignore
        pdf = pypdfium2.PdfDocument.new()
        pdf.new_page(595, 842)  # A4 blank page
        buf = io.BytesIO()
        pdf.save(buf)
        return buf.getvalue()
    except Exception:
        # Fallback minimal valid single-page PDF
        return (
            b"%PDF-1.4\n"
            b"1 0 obj <</Type /Catalog /Pages 2 0 R>> endobj\n"
            b"2 0 obj <</Type /Pages /Kids [3 0 R] /Count 1>> endobj\n"
            b"3 0 obj <</Type /Page /Parent 2 0 R /MediaBox [0 0 612 792]>> endobj\n"
            b"xref\n0 4\n0000000000 65535 f \n0000000010 00000 n \n0000000060 00000 n \n0000000117 00000 n \n"
            b"trailer <</Size 4 /Root 1 0 R>>\nstartxref\n193\n%%EOF\n"
        )


def get_sample_corrupted_pdf_bytes() -> bytes:
    """Malformed PDF bytes to test failure and error logging."""
    return b"%PDF-1.4\n[CORRUPTED BYTES ERROR TEST FIXTURE - JUNK DATA WITHOUT PROPER XREF OR STREAM]%%\n"


def get_sample_go_text() -> str:
    """Government Order text with explicit date metadata."""
    return (
        "GOVERNMENT OF TAMIL NADU\n"
        "Social Welfare and Women Empowerment Department\n"
        "G.O. (Ms.) No. 84 Dated: 18.08.2023\n"
        "Subject: Social Welfare — Kalaignar Magalir Urimai Thittam — Guidelines and Implementation Framework — Orders Issued.\n"
        "Read: G.O. (Ms.) No. 45 Dated: 22.05.2023."
    )


def get_sample_cag_audit_text() -> str:
    """CAG audit report text with report number and year."""
    return (
        "Report of the Comptroller and Auditor General of India\n"
        "State Finances Audit Report for the year ended 31 March 2023\n"
        "Government of Tamil Nadu\n"
        "Report No. 2 of 2024\n"
        "This Report has been prepared for submission to the Governor of Tamil Nadu under Article 151 of the Constitution."
    )


def get_sample_pii_text() -> str:
    """Citizen grievance text with mobile phone and email to verify DPDPA scrubbing."""
    return (
        "Citizen Thiru K. Senthil kumar submitted grievance regarding delay in stipend.\n"
        "Contact: +91 9841023456 or email senthil.kumar99@gmail.com at 14/2 Gandhi Street, Chennai."
    )
