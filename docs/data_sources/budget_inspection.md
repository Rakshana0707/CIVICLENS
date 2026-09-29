# Raw Budget Dataset Inspection

**Status:** Inspected
**Date:** 2026-09-29

## Inspection Summary
The raw data directory (`data/raw/budget/`) now contains four full financial years of official Tamil Nadu budget datasets spanning from 2019-2020 through 2022-2023. These were successfully extracted from bulk ZIP archives.

Total identified datasets: **336**

## Structural Analysis
*   **Format**: PDF format (e.g., `2019-2020_d01.pdf`).
*   **Source**: Finance Department, Government of Tamil Nadu.
*   **Structure**: Detailed Demand for Grants (DDG). 
*   **Language**: Bilingual (Tamil and English) text. 
*   **Length**: Variable (typically 20-50 pages per document).

## Table Extraction Quality (pdfplumber)
A preliminary inspection of the PDF layout (e.g., `2019-2020_d01.pdf` Demand 1 - State Legislature) via `pdfplumber` reveals:
1.  **Introductory Text**: The first 7-8 pages consist of descriptive text and classification documentation regarding changes in Head of Account structures (e.g., IFHRMS updates).
2.  **Core Tables**: Starting around page 9, standard tabular matrices define the Budgetary allocations.
3.  **Headers Present**:
    - `HEAD OF ACCOUNT`
    - `Accounts 2017-18` (Actual Expenditure for T-2)
    - `Budget Estimate 2018-19` (BE for T-1)
    - `Revised Estimate 2018-19` (RE for T-1)
    - `Budget Estimate 2019-20` (BE for Target Year)
4.  **Row Logic**: Each row dictates a granular budget subdivision (Major Head -> Minor Head -> Detailed Head).

## Known Limitations and Challenges
- **Vertical Spanning**: Columns are often merged or texts wrap across multiple visual rows inside the PDF tables, meaning naive line-by-line CSV conversions will misalign header identifiers with numeric floats.
- **Bilingual Conflation**: Tamil string rendering alongside English strings requires tight spatial grouping to avoid data ingestion mismatching the `department_name` and `scheme_name`.
- **No Direct Excel Output**: The datasets are purely vector PDFs. All ingestion logic must route through spatial `pdfplumber` table extractors prior to validation.

## Traceability Check
The dataset IDs strictly follow the naming convention `TN_BUDGET_[YEAR]_[DEMAND_ID]`. Every single one of the 336 PDFs is currently mirrored inside `manifest.json` under a `verified` collection status.
