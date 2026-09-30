# Historical Scheme Data Sources

This document identifies authoritative public sources containing historical information on Tamil Nadu government schemes. These sources have been verified to exist and are prioritized for ingestion in Phase 2.

## 1. Departmental Policy Notes
*   **Organization:** Individual Government Departments (e.g., Social Welfare, Agriculture, Education), Government of Tamil Nadu
*   **Source URL:** `https://tnbudget.tn.gov.in/` (Under "Policy Notes" / "Documents") and individual department portals (e.g., `cms.tn.gov.in/sites/default/files/documents/`)
*   **Financial-Year Coverage:** Multiple years (Annual publications accompanying the state budget).
*   **Document Format:** PDF (some recent years may also have HTML summaries).
*   **Contents Verified:**
    *   **Scheme Names:** Yes
    *   **Objectives:** Yes
    *   **Descriptions:** Yes (Detailed narrative sections per scheme)
    *   **Beneficiaries:** Yes
    *   **Allocations:** Yes (Usually high-level estimates for the upcoming year)
    *   **Implementation Details:** Yes (Often includes physical targets, administering bodies, and rollout strategies)
*   **Limitations:** Document structure and formatting vary wildly across different departments and different years. Older PDFs (pre-2015) may be scanned images with poor OCR readability. Naming conventions for identical schemes might shift.

## 2. Annual Budget Speeches
*   **Organization:** Finance Department, Government of Tamil Nadu
*   **Source URL:** `https://tnbudget.tn.gov.in/`
*   **Financial-Year Coverage:** Multiple years (Annual).
*   **Document Format:** PDF / HTML.
*   **Contents Verified:**
    *   **Scheme Names:** Yes (Particularly for new announcements or major flagship schemes)
    *   **Objectives:** Yes (High-level political/social intent)
    *   **Descriptions:** Yes (Brief introductions)
    *   **Beneficiaries:** Yes (Broad target groups mentioned)
    *   **Allocations:** Yes (Specific financial commitments announced)
    *   **Implementation Details:** Limited (Usually restricted to launch dates or high-level executing bodies)
*   **Limitations:** Primarily a narrative and political document. It does not contain comprehensive lists of all ongoing minor schemes, focusing instead on new initiatives and major outlays. Granular eligibility criteria are rarely included.

## 3. Departmental Performance Budgets
*   **Organization:** Individual Government Departments, Government of Tamil Nadu
*   **Source URL:** Available via specific department websites (e.g., `tn.gov.in/department`)
*   **Financial-Year Coverage:** Annual (Availability varies by department).
*   **Document Format:** PDF.
*   **Contents Verified:**
    *   **Scheme Names:** Yes
    *   **Objectives:** Yes (Brief)
    *   **Descriptions:** Limited
    *   **Beneficiaries:** Yes (Often presented as numerical targets, e.g., "Number of students benefited")
    *   **Allocations:** Yes (Financial outlays vs. actual expenditure)
    *   **Implementation Details:** Yes (Physical targets and achievements)
*   **Limitations:** Not consistently published or easy to locate centrally for all departments. Focuses heavily on quantitative physical/financial targets rather than rich semantic policy descriptions.

## 4. Government Orders (G.O.s)
*   **Organization:** Various Departments, accessed via the TN Government Portal
*   **Source URL:** `https://www.tn.gov.in/go_view`
*   **Financial-Year Coverage:** Ongoing (Daily publications).
*   **Document Format:** PDF.
*   **Contents Verified:**
    *   **Scheme Names:** Yes
    *   **Objectives:** Yes
    *   **Descriptions:** Yes (Highly detailed administrative guidelines)
    *   **Beneficiaries:** Yes
    *   **Allocations:** Yes (Administrative sanction amounts)
    *   **Implementation Details:** Yes (Strict eligibility criteria, required documents, administrative hierarchies)
*   **Limitations:** G.O.s are highly specific and vast in number. Isolating G.O.s specifically related to the overarching launch or guidelines of a major scheme requires targeted searching, making bulk extraction difficult. 
