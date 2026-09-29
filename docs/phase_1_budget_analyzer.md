# Phase 1: Budget & Scheme Analyzer

## Overview
Phase 1 focuses on extracting, validating, and structuring Tamil Nadu state budget data. The core goal is to generate actionable insights into scheme distributions, year-over-year variances, and mathematical anomalies using unsupervised ML techniques (K-Means, DBSCAN, Isolation Forests).

## Current Status
**Status:** Infrastructure Complete (Awaiting Raw Data Seeding)

The technological pipeline for Phase 1 has been built, tested, and verified end-to-end (E2E). However, official Tamil Nadu budget datasets (PDFs/Excel) have not yet been collected and digitized. Because of this, the infrastructure is operating on strictly isolated mock test fixtures. **No fabricated data is presented as official in the production UI.**

## Key Components

1. **Ingestion & Validation Pipeline**
   - **`BudgetIngestor`**: Uses declarative JSON manifests to track datasets by collection status, mapping CSV extracts into the SQLite/PostgreSQL schema.
   - **`BudgetValidator` & `BudgetCleaner`**: Strictly enforces data standards (normalizing `YYYY-YYYY` financial years to `YYYY-YY`, stripping whitespace, detecting batch duplicates).

2. **Backend & Architecture**
   - **Database (`backend/models/budget.py`)**: Hierarchical schema nesting `BudgetDepartment` -> `BudgetScheme` -> `BudgetRecord`. Follows rigid constraint relationships preventing orphaned records.
   - **Service Layer**: Houses logic for budget aggregations, scheme-level historical comparisons, and cross-stage evaluations (`budget_estimate` vs. `actual_expenditure`).
   - **Traceability**: All aggregated records store a mapping (`source_document_id`) linking them to the raw ingestion manifest file to ensure complete provenance.

3. **Machine Learning Pipeline**
   - **Feature Engineering**: Robust imputation avoiding data-leakage. Categorical keys are stripped before standard scaling.
   - **Algorithms Implemented**:
     - *K-Means*: Parametric clustering mapping variance.
     - *DBSCAN*: Density-based spatial clustering capable of isolating noise points (`-1`).
     - *Principal Component Analysis (PCA)*: Dimensionality reduction exclusively utilized to project orthogonal variance on 2D space.
     - *Isolation Forest*: Bound-scoring algorithm exposing structural budget outliers.
   - **Constraints Enforced**: Clear semantic warnings exist in both backend HTTP layers and Frontend UIs declaring that mathematical clustering is purely geometric and *does not* denote substantive policy relationships or political wrongdoing.

4. **Frontend Citizen Dashboard**
   - **Streamlit (`frontend/`)**: Modular pages connected to the Flask API using the `requests` library.
   - Includes standard table paginations, scheme trend analysis metrics, and an interactive **Budget Insights** tab mapping Plotly charts to dynamic PCA parameters.

## Known Limitations & Pending Tasks
- **Official Data Missing**: The core limitation is the lack of official data.
- **Naive Heuristics**: The `_map_raw_to_canonical` fallback inside the ingestor currently relies on naive dictionary matching to extract `budget_estimate` vs `actual_expenditure`. As official horizontal PDF architectures become standardized, this ingestion parser will require strict columnar rules.
- **Null Variance Constraints**: Algorithms like PCA drop un-imputed NaNs natively. To retain schemes with missing historical YoY metrics, we impute a `0.0` variance before scaling.

## Readiness for Next Phase
The Phase 1 infrastructure meets all software requirements for scale, safety, schema rigidity, and error handling (92 passing tests). The project is ready to transition into **Phase 2: Historical Scheme Intelligence & NLP**.
