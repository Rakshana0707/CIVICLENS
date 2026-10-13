# Phase 10.7 — Policy Evaluation Findings and Evidence Synthesis Methodology

## 1. Overview
The **Policy Evaluation Evidence Synthesis Layer** (`PolicyEvidenceSynthesisService` in `backend/services/policy_evidence_synthesis_service.py` and `EvaluationFinding` / `FindingEvidenceLink` in `backend/models/policy_evaluation.py`) connects quantitative and documentary evaluation results to original primary source documents and **Phase 9's Unified Civic Intelligence & Evidence Graph** (`CivicGraphNode`, `CivicEvidenceEdge`).

Every synthesized finding is governed by four strict rules:
1. **Evidence Classifications, Not Political Verdicts**: Findings classify the state and consistency of empirical evidence (`IMPLEMENTATION_EVIDENCE_AVAILABLE`, `TARGET_ACHIEVEMENT_DOCUMENTED`, `OUTCOME_CHANGE_OBSERVED`, `CONFLICTING_FINDINGS`, `INSUFFICIENT_EVIDENCE`, `EVALUATION_PENDING_REVIEW`). Rhetoric or partisan verdicts (`"historic triumph"`, `"total failure"`, `"corrupt scheme"`) are rejected with `UnsupportedFindingConclusionError("POLITICAL_VERDICT_PROHIBITED")`.
2. **Evidence-Strength Ceiling**: A finding must **never** be stronger than the evidence supporting it. Substantive conclusions lacking supporting documentary links are rejected (`STRONGER_THAN_EVIDENCE`) or downgraded to `INSUFFICIENT_EVIDENCE`. One-sided positive conclusions that ignore contradicting documents (such as a CAG Audit Report contradicting a Departmental Policy Note) are rejected (`UNACKNOWLEDGED_CONFLICTING_EVIDENCE`) or reclassified as `CONFLICTING_FINDINGS`.
3. **Deterministic Calculations vs. Extracted Statements**: Numerical metrics (`deterministic_calculated_value`) are computed deterministically by code from `indicator_values_used` and checked against `quantified_effect` (`NumericalInconsistencyError("NUMERICAL_MISMATCH")` raised on divergence). Extracted or LLM-summarized documentary passages are tagged `statement_origin = "EXTRACTED_FROM_SOURCE_DOCUMENT"` and must cite a verified `source_document_id` and `quotation_excerpt`.
4. **No Unsupported Explanations for Why an Outcome Occurred**: Statements attributing why an outcome changed (`"because of"`, `"due to"`, `"caused by"`, `"driven by"`) are blocked with `UNSUPPORTED_CAUSAL_EXPLANATION` unless backed by both a verified Grade A/B causal study (`is_causally_identified = True`) and a supporting evidence passage with `documents_causal_mechanism = True`.

---

## 2. Mandatory 12 Attributes Recorded per Finding
Every `EvaluationFinding` record persists and serializes the following 12 attributes:

| # | Attribute | Column / Property | Description |
| :--- | :--- | :--- | :--- |
| 1 | **Evaluation ID** | `evaluation_id` (`study_id`) | Canonical FK to `evaluation_studies.study_id`. |
| 2 | **Policy ID** | `policy_id` | Canonical FK to `policy_registry.policy_id`. |
| 3 | **Evaluation Question** | `evaluation_question` | Exact question being answered by the finding. |
| 4 | **Finding Statement** | `finding_statement` (`finding_text`) | Objective, non-partisan synthesis statement. |
| 5 | **Evidence References** | `evidence_references` | Structured list of cited `source_document_id`, `page_number`, `table_reference`, `stance`, and `document_hash`. |
| 6 | **Indicator Values Used** | `indicator_values_used` | JSON map of exact inputs (`baseline_value`, `followup_value`, `target_value`, `actual_value`), `deterministic_calculated_value`, and `extracted_document_statements`. |
| 7 | **Calculation Method** | `calculation_method` | Deterministic formula (`ABSOLUTE_CHANGE`, `PERCENTAGE_CHANGE`, `TARGET_REALIZATION_PCT`, `BUDGET_EXECUTION_RATE_PCT`). |
| 8 | **Supporting Evidence** | `supporting_evidence` | List of verified `SUPPORTS` passages with `source_document_id` and verbatim `quotation_excerpt`. |
| 9 | **Contradicting / Contextual Evidence** | `contradicting_or_contextual_evidence` | List of `CONTRADICTS`, `QUALIFIES`, or `NEUTRAL` passages preserved alongside supporting evidence. |
| 10 | **Limitations** | `limitations` | Methodological caveats, missing-data notes, and non-causal warnings. |
| 11 | **Review Status** | `review_status` | `PENDING_REVIEW`, `VERIFIED`, `FLAGGED_CONFLICTING`, or `REJECTED_UNSUPPORTED`. |
| 12 | **Creation Timestamp** | `created_at` | UTC ISO-8601 creation timestamp. |

---

## 3. Supported Evidence-Classification Finding Types
`FindingType` supports the following evidence classifications:

- **`IMPLEMENTATION_EVIDENCE_AVAILABLE`**: Documentary evidence confirms input expenditure, procurement, or physical output delivery (`INPUT` / `ACTIVITY` / `OUTPUT` tiers), without claiming downstream outcome improvement.
- **`TARGET_ACHIEVEMENT_DOCUMENTED`**: Verified administrative or audit records document the realization ratio against an officially stated quantitative target.
- **`OUTCOME_CHANGE_OBSERVED`**: Compatible baseline and follow-up indicator observations document a measurable change in an `OUTCOME` or `IMPACT` indicator.
- **`CONFLICTING_FINDINGS`**: Official sources or independent audits report materially different figures or conclusions (e.g., Departmental Policy Note vs. CAG Performance Audit). Both sources are preserved and linked.
- **`INSUFFICIENT_EVIDENCE`**: Available primary documents or indicator observations are missing, incomplete, or methodologically incompatible to answer the evaluation question.
- **`EVALUATION_PENDING_REVIEW`**: Preliminary evidence synthesis awaiting human methodological verification.

---

## 4. Phase 9 Evidence Graph Integration
`PolicyEvidenceSynthesisService.sync_finding_to_evidence_graph()` connects every synthesized finding directly into Phase 9's Unified Evidence Graph without creating a duplicate graph:
- Creates `NODE:FINDING:{finding_id}` (`GraphEntityType.EVALUATION_FINDING`).
- Creates an `EVALUATES` edge from `NODE:FINDING:{finding_id}` to `NODE:POLICY:{policy_id}`.
- Creates `NODE:DOC:{source_document_id}` (`GraphEntityType.EVIDENCE_DOCUMENT`) for each cited source document and links:
  - Supporting documents via `GraphRelationshipType.PROVIDES_EVIDENCE_FOR`
  - Contradicting documents via `GraphRelationshipType.CONTRADICTS`
  - Contextual/qualifying documents via `GraphRelationshipType.CONTEXTUALIZES`
