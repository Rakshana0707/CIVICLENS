# Historical Scheme Data Inspection Report

## Overview
This document details the inspection of the raw historical scheme documents collected in Phase 2.3. The goal is to assess data availability, structural integrity, and text extraction quality before building the intelligence ingestion pipeline.

*   **Number of Documents Inspected:** 2
*   **Files Inspected:**
    *   `data/raw/schemes/2023-2024/Appendix_Budget_Speech.pdf` (92 pages)
    *   `data/raw/schemes/2023-2024/Policy_Note_School_Ed.pdf` (165 pages)
*   **Financial-Year Coverage:** 2023-2024 (Note: The School Education document header indicates Budget Estimates for 2026-2027, suggesting projection data or an overlapping financial cycle).
*   **Department Coverage:**
    *   Finance Department (Statewide macro-budget)
    *   School Education Department (Demand 43)

## Data Availability
Based on manual inspection of the extracted text layers, the following fields are present:

*   **Available Fields:**
    *   **Financial Year:** Clearly stated in headers.
    *   **Department:** Explicitly declared (e.g., "DEMAND 43 SCHOOL EDUCATION DEPARTMENT").
    *   **Scheme Names:** Present in English (e.g., "Welfare of Scheduled Castes", "Development Action Plan for Scheduled Castes").
    *   **Sector/Category:** Present (e.g., "Welfare of Backward Classes and Minorities").
    *   **Allocation Information:** Present (Structured tabular data showing Accounts, Budget Estimate, Revised Estimate).
    *   **Source Page Numbers:** Available and trackable.
*   **Missing Fields:**
    *   **Scheme Descriptions:** Mostly missing. The collected documents are highly tabular and lack the rich, narrative paragraphs typical of actual Policy Notes.
    *   **Detailed Objectives:** Missing.
    *   **Beneficiary Eligibility Criteria:** Missing.
    *   **Implementation Information:** Minimal.

## Technical Analysis and Limitations

### 1. Text Extraction Quality (Severe Issues)
The extraction quality using standard PDF parsers (like `pdfplumber`) is extremely poor for non-English text. 
*   **CID Font Mapping:** `Appendix_Budget_Speech.pdf` contains unmapped `(cid:12)` tags. This occurs when the PDF creator does not embed a Unicode mapping (ToUnicode table) for custom fonts.
*   **Legacy ASCII-Tamil Fonts:** The Tamil text in `Policy_Note_School_Ed.pdf` extracts as gibberish (e.g., `!"#$%! 43 &'($ !)*+ ,%-`). This indicates the document uses legacy, non-Unicode bilingual fonts (like BAMINI, TAB, or TAM) where Tamil glyphs are mapped to standard ASCII symbol slots.

### 2. Document Structure
*   **Tables and Structured Sections:** Both documents are heavily tabular. The School Education document contains massive nested tables spanning multiple pages with columns for `State's Expenditure`, `Accounts`, and `Budget Estimate`.
*   **Scanned Pages:** The initial inspection indicates that while the documents have text layers, the missing font mappings make them behave similarly to scanned pages requiring OCR for the regional language portions.

### 3. Duplicate and Renamed Schemes
*   **Duplicate Issues:** While not explicitly deduped yet, the tabular nature shows that schemes (like "Welfare of Backward Classes") appear repeatedly under different sub-major heads (e.g., 2225 02, 2225 03).
*   **Renamed/Merged Schemes:** No explicit narrative indications of merged schemes were found in these specific files due to their tabular, non-narrative format.

## Conclusion and Source Limitations
The primary limitation discovered during this inspection is a **misclassification of source type**. The document collected as `Policy_Note_School_Ed.pdf` is functionally a "Detailed Demand for Grant" book rather than a narrative "Policy Note". Because it is purely tabular financial data, it cannot fulfill the semantic requirements of Phase 2 (descriptions, objectives, implementations) on its own. Furthermore, the legacy font encoding will require either a specialized mapping dictionary (TAB-to-Unicode) or a fallback to Vision-based OCR (like Tesseract or Google Cloud Vision) to extract Tamil scheme names accurately.
