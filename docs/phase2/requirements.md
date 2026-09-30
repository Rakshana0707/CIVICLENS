# Phase 2.1: Historical Scheme Intelligence - Architecture and Data Requirements

## Objective
Design the architecture and data requirements for a system capable of identifying historically similar Tamil Nadu government schemes and comparing them across financial years. This system extends the quantitative foundation built in Phase 1 (Budget & Scheme Analyzer) by introducing semantic and textual intelligence to power search, similarity matching, and qualitative comparisons.

## Dependencies on Phase 1
This phase relies heavily on the existing Phase 1 infrastructure:
*   **Database Schema:** Reusing the normalized `budget_departments`, `budget_schemes`, and `budget_records` tables. Phase 2 data will link to `budget_schemes.id` and `budget_departments.id`.
*   **Source Traceability:** Expanding on the `budget_source_documents` and `manifest.json` ingestion patterns established in Phase 1.
*   **Backend Architecture:** Adhering to the established FastAPI/Flask repository-service pattern.
*   **Testing Conventions:** Maintaining high test coverage through existing `pytest` integration and unit testing structures (e.g., `tests/integration/`, `tests/nlp/`).

## Functional Requirements
The system must support the following capabilities:
*   **Historical Scheme Search:** Full-text and semantic search of schemes based on textual attributes.
*   **Scheme Description Retrieval:** Fetching contextual narratives and policy details.
*   **Scheme-to-Scheme Semantic Similarity:** Quantifying how similar two schemes are based on their objectives, descriptions, and target demographics.
*   **Similar Historical Scheme Recommendations:** Recommending historically related or predecessor schemes.
*   **Cross-Year Scheme Comparison:** Tracking how a scheme's narrative and focus shifted across different financial years.
*   **Department-Wise Historical Scheme Exploration:** Aggregating scheme intelligence by `department_id`.
*   **Scheme Category/Theme Analysis:** Grouping schemes by programmatic sectors or administrative themes.
*   **Similarity Explanations:** Providing human-readable justifications for why two schemes are considered semantically similar.
*   **Source Traceability:** Linking all textual claims and extracted intelligence back to specific source documents and page numbers.

## Data Requirements
To support these functional requirements, the following fields must be captured (where available in historical texts). *Note: It is not assumed that every historical source contains all fields.*

### Core Identification (Linked to Phase 1)
*   **Scheme ID:** Foreign key to Phase 1 `budget_schemes.id`.
*   **Scheme Name:** Official name and aliases.
*   **Department:** Implementing department, linked to Phase 1 `budget_departments.id`.
*   **Financial Year:** The specific year the intelligence applies to, allowing tracking of narrative evolution.

### Semantic & Qualitative Attributes
*   **Scheme Description:** The primary narrative detailing the scheme.
*   **Target Beneficiaries:** Demographic, socioeconomic, or geographic groups targeted.
*   **Sector/Category:** Broad programmatic category (e.g., Education, Public Health, Infrastructure).
*   **Objectives:** The explicit goals and intended outcomes of the policy.
*   **Implementation Information:** Geographic scope, executing agencies, or specific delivery mechanisms.

### Financial Context
*   **Budget Allocation:** Qualitative mentions of funding mechanisms or allocations (corroborating Phase 1 `budget_records`).

### Provenance and Traceability
*   **Source Document:** Reference to the origin document (linking to the source ingestion framework).
*   **Source URL:** Direct link to the digitized document if hosted online.
*   **Source Page/Reference:** Exact page number or section within the document.
*   **Original Source Text:** The raw, unedited text snippet from which intelligence was extracted.

## Source Requirements
Phase 1 utilized annual budget documents. To build Historical Scheme Intelligence, additional textual datasets must be collected:
1.  **Department Policy Notes:** Annual notes detailing departmental goals, ongoing schemes, and target beneficiaries.
2.  **Governor's Addresses:** High-level summaries of major policy initiatives.
3.  **Government Orders (G.O.s):** Detailed administrative directives establishing eligibility and implementation rules for schemes.
4.  **Performance Budgets:** Documents detailing the actual physical/social targets achieved vs. planned.
5.  **Citizen's Charters:** Public-facing documents outlining scheme benefits and eligibility criteria.

## ML Requirements
Phase 1 established unsupervised clustering (K-Means, DBSCAN) and anomaly detection (Isolation Forests) for financial variances. Phase 2 requires:
*   **NLP and Embeddings:** Transitioning from numeric scaling to text vectorization (e.g., using HuggingFace sentence transformers in `ml/embeddings/`).
*   **Semantic Search/Similarity:** Implementing cosine similarity or approximate nearest neighbor (ANN) search for scheme-to-scheme comparisons.
*   **Information Extraction:** (Future) Named Entity Recognition (NER) or rule-based extraction to parse targets and objectives from unstructured text.

## API Requirements
The backend (`backend/api/`) must be extended to include:
*   `GET /api/schemes/{id}/intelligence`: Retrieve qualitative details for a specific scheme.
*   `GET /api/schemes/search`: Semantic and keyword search endpoints.
*   `GET /api/schemes/{id}/similar`: Retrieve a ranked list of similar historical schemes with similarity scores and explanations.
*   `GET /api/departments/{id}/schemes/historical`: Retrieve the evolution of schemes under a specific department.

## Frontend Requirements
The Streamlit frontend (`frontend/pages/`) must be updated to feature:
*   A dedicated "Historical Scheme Intelligence" or "Scheme Search" tab.
*   Rich text components to display Scheme Descriptions, Objectives, and Target Beneficiaries.
*   A comparison view (side-by-side) for cross-year scheme evolution.
*   A recommendation widget showing "Similar Schemes" with expanding sections for similarity explanations and source traceability citations.

## Known Limitations
*   **Data Sparsity:** Historical policy notes often lack standardized structures; some years may have highly detailed eligibility criteria, while others provide only one-sentence summaries.
*   **OCR and Digitization Errors:** Older historical documents may suffer from poor Optical Character Recognition quality, leading to noisy `Original Source Text`.
*   **Alias Resolution:** Determining if a slightly renamed scheme is entirely new or a continuation of an old one requires complex human-in-the-loop validation or advanced semantic thresholds.
*   **Lack of Official Data (Current):** As with Phase 1, no official, production-ready dataset is currently seeded. The system must be built to handle nulls gracefully.
