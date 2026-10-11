# Phase 6: Traceability & Evidence Audit Report

**CIVICLENS TN — Phase 6.11 Implementation Audit**  
**Audit Date:** 2026-10-11  
**Scope:** Verification of End-to-End Evidence Traceability across Phases 6.1–6.10

---

## 1. Audit Framework & Classification Criteria

Every analytical category in Phase 6 is audited against five foundational traceability requirements:
1. **Source Document Provenance:** Can the record be linked to an explicit source document entity with publisher, date, format, and checksum?
2. **Granular Reference:** Does the record preserve specific page numbers, table headers, gazette volume numbers, or unminuted notifications?
3. **Reproducibility of Derived Calculations:** For aggregate metrics (e.g., expenditure ratios, questions per sitting), are the underlying raw inputs, mathematical formulas, and transformations transparently stored and exposed?
4. **Dispute & Conflict Preservation:** If two public documents present conflicting values or statuses, are both records preserved without silent overwriting?
5. **Audit Trail History:** Are data transformations, manual verifications, or status adjustments recorded in an immutable ledger?

---

## 2. Category-by-Category Audit Findings

| Category | Description | Current Status | Findings & Identified Gaps |
|---|---|---|---|
| **1. Representative Identity & Historical Terms** | Canonical MP/MLA identities, election cycles, party affiliations, and aliases. | **Partially Implemented** | `Representative` and `RepresentativeTerm` store `source_document_ids` as a JSON array. However, they lack direct links to a structured `SourceDocument` table with page/line citations, publisher metadata, and SHA-256 validation. |
| **2. Legislative Activity Records** | Starred/Unstarred Questions, Debates participated, and session attendance %. | **Partially Implemented** | `LegislativeActivity` stores `source_document_id` and `source_reference` (e.g. "Q.No 1420", "PRS MP Track"). Needs formal linkage to structured evidence registry with excerpt extraction and verification status. |
| **3. Constituency Works & Project Statuses** | MPLADS / MLACDS works, sanctioned amounts, WIP status, and completions. | **Partially Implemented** | `ConstituencyWork` has `source_document_id`, `source_reference`, `verification_source`, and `has_conflicting_status`. However, granular page/row references and multiple conflicting audit reports require explicit conflict modeling. |
| **4. Financial Allocations, Releases & Expenditure** | Sanctioned vs. released funds, reported utilization, and unspent balances. | **Partially Implemented** | Handled within `ConstituencyWork` and `PerformanceMetricsEngine`. Lacks lineage model linking the aggregate expenditure metric to its constituent project vouchers. |
| **5. Development Indicators** | Census 2011 & DES TN district/constituency indicators across reference periods. | **Partially Implemented** | Stores `source_document_id`, `source_reference`, `calculation_method`, and `data_quality_status`. Lacks explicit document registry foreign key and page/table citation. |
| **6. Promise-to-Scheme Relationships** | Cross-references between Phase 3 manifesto promises and empirical delivery. | **Complete** | `PromisePerformanceLink` strictly references Phase 3 `political_promises`, Phase 2 schemes, `evidence.id`, `work_id`, and `indicator_id` with 6 fulfillment stages and conflict flags. |
| **7. Performance Metrics & Lineage** | Sitting-adjusted metrics, cohort percentiles, transparent composite index. | **Partially Implemented** | `PerformanceMetric` exposes weights, sensitivity margins ($\pm 20\%$), and caveats, but lacks explicit tracking of `input_record_ids` and formula definitions in an auditable lineage model. |
| **8. Data-Quality & Conflicting Records** | Missing attendance in Assembly, conflicting audit reports, date discrepancies. | **Partially Implemented** | Flags exist in models (`has_conflicting_status`, `has_conflicting_dates`), but no dedicated `ConflictingEvidence` entity exists to store diverging values side-by-side with resolution bases. |

---

## 3. Summary of Implementation Gaps

1. **Gap 1: Structured `SourceDocumentRegistry`:**
   - Datasets currently reference string IDs (e.g., `"D4-001"`, `"D8-001"`). An explicit `SourceDocument` entity with publisher, publication date, SHA-256 hash, URL, file format, and verification status is required.
2. **Gap 2: Reusable `FactEvidenceLink` Model:**
   - Need a unified, polymorphic or explicit evidence relationship linking facts (representative, activity, work, indicator, metric) to document citations with page numbers, table names, excerpt quotations, and extraction methods.
3. **Gap 3: Metric Lineage Engine (`MetricLineage`):**
   - Need explicit storage of `formula_expression`, `input_record_ids`, and `calculation_version` so any aggregate score can be drilled down to its exact constituent rows.
4. **Gap 4: Conflicting Evidence Registry (`ConflictingEvidenceRecord`):**
   - Discrepant reports (e.g., PWD vs. CAG completion status, or conflicting expenditure figures) must be stored side-by-side with conflict magnitude and resolution basis.
5. **Gap 5: Audit Trail Ledger (`AuditTrailEvent`):**
   - Need an event ledger recording ingestion, extraction, normalization, and verification updates.
6. **Gap 6: Evidence Detail API & UI:**
   - Need endpoints exposing source documents, citations, metric lineage, and frontend "View Evidence" modals/expanders.
