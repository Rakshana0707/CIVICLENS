# Phase 1 Completion Audit Report

## 1. Audit Overview
This audit assesses the state of the CivicLens TN Budget & Scheme Analyzer, comparing the finalized infrastructure against the newly collected real datasets (2019-2023 official PDFs).

## 2. Existing Components
- **Data Ingestion Pipeline**: Built to ingest flattened CSVs using declarative `manifest.json`.
- **Validation & Cleaning (`budget_validation.py`, `budget_cleaning.py`)**: Normalizes schema strings, standardizes financial years, removes blank rows.
- **Relational DB Schema**: Rigid `BudgetDepartment` -> `BudgetScheme` -> `BudgetRecord` models utilizing SQLAlchemy.
- **REST APIs**: Implemented and tested endpoints for filtering datasets by department/scheme and calculating trend comparisons.
- **Frontend Dashboard**: Native Streamlit `1_Budget_Explorer.py` and `2_Budget_Insights.py` displaying tables and graphs.
- **Machine Learning (`ml/budget_clustering.py`, `ml/budget_pca.py`)**: Functional scripts designed to map variance in arrays and plot Isolation Forest anomalies.

## 3. Real Dataset Availability
- **Files Collected**: 336 PDFs spanning four financial years (2019-2020, 2020-2021, 2021-2022, 2022-2023).
- **Format**: Bilingual (Tamil and English) tabular PDFs outlining 'Demand for Grants' for individual departments (e.g., `2019-2020_d01.pdf`).
- **Verification Status**: Validated and imported into `data/raw/budget/manifest.json` as `verified`.

## 4. Incomplete Features & Discovered Issues
1. **PDF Parsing Deficit**: The current `BudgetIngestor` defaults to a naive `pd.read_csv` and does not handle unstructured PDFs. We must integrate `pdfplumber` to flatten the 336 PDFs into the schema expected by the DB.
2. **Heuristic Parsing Flaw**: The original `_map_raw_to_canonical` assumed CSV headers explicitly stated `"budget_estimate"` and `"actuals"`. The real PDFs present horizontal tables grouping multiple years side-by-side. The parser needs a total refactor to extract the precise matrix columns correctly.
3. **ML Testing on Real Data**: ML clustering and anomaly detection have only been run on internal mock fixtures. They must be validated using the authentic 336 parsed Demand documents to tune K-Means bounds and handle potential missing metrics.

## 5. Recommended Execution Order
1. **`fix(budget): align ingestion with official datasets`** - Refactor `BudgetIngestor` to wrap `pdfplumber` for iterating through the authentic PDFs.
2. **`fix(budget): validate and normalize real budget data`** - Push the extracted text through the validation engine.
3. **`feat(budget): complete verified dataset import`** - Load the parsed matrices into SQLite/PostgreSQL.
4. **`feat(ml): train and validate budget analysis models`** - Repopulate the K-Means and Isolation Forest calculations against the real data array.
5. **`test(budget): validate phase 1 end to end`** - Ensure API serialization works for the dashboard.
6. **`docs(budget): finalize phase 1 completion report`** - Formal sign-off.
