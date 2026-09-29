# CIVICLENS TN: Phase 1 Completion Report

**Date:** 2026-09-29
**Phase:** 1 (Budget & Scheme Analyzer)

## 1. Summary
Phase 1 is now **Complete and Verified**. The infrastructure successfully processes, cleans, normalizes, and visualizes official Tamil Nadu State budget datasets spanning four complete financial years.

## 2. Integrated Datasets
- **Source**: Finance Department, Government of Tamil Nadu
- **Format**: PDF (Detailed Demand for Grants)
- **Timeframe**: 2019-2020 through 2022-2023 (Four Financial Years)
- **Scale**: 336 individual PDF documents containing granular scheme allocations.
- **Traceability**: `source_document_id` and `source_page_number` are meticulously preserved all the way from the raw extracted arrays through to the frontend Streamlit dashboard widgets. No simulated data is used.

## 3. Data Processing Architecture
1. **Extraction**: A custom layout-aware `pdfplumber` pipeline natively parses the bilingual Head of Account tables.
2. **Validation**: The `BudgetValidator` schema rules correctly format identifiers and isolate structural inaccuracies.
3. **Ingestion**: Duplicate DP code overlaps across consecutive pages are inherently merged by SQLAlchemy `IntegrityError` fallbacks.
4. **Volume**: Generates thousands of individual Canonical records spanning `budget_estimate`, `revised_estimate`, and `actual_expenditure` stages.

## 4. Backend & API Functionality
- Full REST endpoints built in Flask.
- Exposes `department` and `scheme` categorical filters.
- Real-time aggregation of allocations, returning cross-sectional metrics.
- Exposes pure `/api/ml/budget/clustering` and `/api/ml/budget/anomaly` calculations executing deterministically in memory over authentic filtered records.

## 5. ML Models Evaluated
The machine learning pipeline handles legitimate variance in the real datasets:
- **K-Means / DBSCAN**: Computes percentage changes (`yoy_change_be`) across the 4-year span. Imputes 0.0 only for strictly missing variance (e.g., initial scheme launch year).
- **PCA**: Reduces multi-dimensional budget metrics (allocation shares, actuals vs estimate diffs) down to 2 components, explicitly returning the `explained_variance_ratio`.
- **Isolation Forest**: Calculates an anomaly score out of 100 for statistically isolated variations. 
*Constraint Note*: The UI explicitly marks these anomalies as statistical artifacts, not indicators of misconduct.

## 6. Frontend Analytics (Budget Explorer)
- Native Streamlit UI features robust exception handling (e.g. throwing `st.warning` safely if a specific filter combination yields insufficient records for PCA).
- Generates 2D scatter projections with `plotly`.
- Maps hovering tooltips to the original `source_documents` UUID.

## 7. Known Limitations
- The Tamil font arrays within the legacy PDFs do not map correctly under standard unicode extraction; the system relies heavily on the english string descriptors matching the DP codes. 
- Very short-lived schemes (existing < 1 year) are assigned 0.0 YoY variance in the geometric distance models since no longitudinal span exists.

## 8. Status Sign-Off
Phase 1 is officially closed. The infrastructure reliably handles authentic government records without manual intervention.

**Ready to advance to Phase 2: Historical Scheme Intelligence & NLP.**
