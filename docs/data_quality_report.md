# Data Quality and Validation Report

**Date:** 2026-09-29
**Phase:** 1 Completion (Real Dataset Integration)

## 1. Validation and Cleaning Protocol
The raw tabular data extracted from the official Tamil Nadu Budget PDFs undergoes processing by `BudgetValidator` and `BudgetCleaner`.

1.  **Format Validation**: Financial year formats must match `YYYY-YY`. Blank values for required fields (`budget_stage`, `amount`) flag the record.
2.  **Schema Alignment**: The raw extraction strips trailing garbage text but preserves Head of Account DP codes exactly as documented by IFHRMS conventions (e.g. `2011 02 101 AA 30100`).
3.  **Missing Value Imputation Constraints**: Strict limits are placed on guessing or fabricating metrics. If a PDF extraction drops an amount or represents it as `...`, the system ingests it as `null`/`None` rather than fabricating `0.0`.

## 2. Ingestion Progress & Statistics

*   **Source Files Processed**: 336 Bilingual "Demand for Grant" PDFs representing 2019-20 through 2022-23.
*   **Vectorization**: The custom `pdfplumber` layout-preservation heuristic bypasses garbled Tamil OCR and correctly aligns numeric actuals/estimates columns to precise `scheme_names`.
*   **Duplication Mitigation**: The schema explicitly relies on an `IntegrityError` block across `BudgetScheme` composite keys, ensuring overlapping DP codes inside consecutive PDF pages do not artificially inflate budget volumes.

## 3. Rejected Records
The most common rejection patterns encountered during testing:
*   **Malformed Financial Year**: Encountered `2019-2020` instead of canonical `2019-20`. Resolved via upstream manifest sanitization.
*   **Unresolved DP Codes**: Table headers incorrectly interpreted as numeric rows. Dropped cleanly by the numerical casting heuristics.

*(Note: Live extraction is currently running and populating thousands of official validated rows into the persistent DB).*
