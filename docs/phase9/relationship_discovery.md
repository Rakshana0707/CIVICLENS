# Phase 9.4 — Cross-Phase Relationship Discovery Engine

## 1. Executive Summary & Objective

**Phase 9.4** implements the **Relationship Discovery Engine** for the **Unified Civic Intelligence & Evidence Graph** of **CIVICLENS TN**.

The engine systematically discovers, cross-references, and proposes evidence-backed links between records collected across Phases 1 through 8 (budgets, historical schemes, political promises, news media reports, campaign funding, legislative activities, fact-checked claims, and civic grievances).

### 1.1 Core Principles
1. **Hierarchy of Evidence:** Deterministic and primary documentary evidence is **always** prioritized over similarity-based matching.
2. **Provisional Isolation:** Automatically proposed links are kept strictly separated in `candidate_relationship_proposals` from confirmed `civic_evidence_edges`.
3. **No Automatic Conversion from Similarity:** A high similarity score alone **never** converts a candidate into a verified graph edge.
4. **Epistemic Anti-Hallucination:** Strictly prevents common causal fallacies (e.g., attributing personal culpability from spatial co-location, assuming campaign funding caused a public work, or declaring a promise fulfilled merely because a scheme exists).
5. **Human-in-the-Loop Review:** Authorized reviewers confirm, reject, or defer candidate proposals with complete immutable audit histories.

---

## 2. Multi-Tier Discovery Hierarchy

The discovery engine employs a 4-tier discovery pipeline, prioritizing verified statutory signals over heuristic approximations:

```
+-------------------------------------------------------------------+
|  Rank 1: Exact Identifier Matching (DETERMINISTIC_ID)             |
|  - Demand Numbers (Demand 34 -> MAWS)                             |
|  - Government Order Numbers (G.O. Ms No. 43)                      |
|  - Assembly Petition & Grievance Tokens (PET-2024-TN-101)         |
|  - Electoral Bond Alpha-Numerics & ECI Affidavits                 |
|  - Assembly Constituency Codes (AC-013)                           |
|  Confidence: 0.98 - 1.00                                          |
+-------------------------------------------------------------------+
                                  |
                                  v
+-------------------------------------------------------------------+
|  Rank 2: Documented References (DIRECT_DOCUMENTARY)               |
|  - Shared statutory publications / Gazettes                       |
|  - Primary CAG audit reports / DPI evaluation documents           |
|  - ECI Form 21E official results declarations                     |
|  Confidence: 0.90 - 0.95                                          |
+-------------------------------------------------------------------+
                                  |
                                  v
+-------------------------------------------------------------------+
|  Rank 3: Canonical Entity Resolution (DETERMINISTIC / REVIEWED)   |
|  - Shared Phase 9.2 CanonicalEntity identifier                    |
|  - Departmental scheme administration mappings                    |
|  Confidence: 0.90 - 0.92                                          |
+-------------------------------------------------------------------+
                                  |
                                  v
+-------------------------------------------------------------------+
|  Contextual Compatibility Verification                            |
|  - Temporal Engine: Fiscal year / election term overlap           |
|  - Geographic Engine: District / Assembly Constituency boundary   |
|  (Incompatible timeframes or locations downgrade / flag candidate)|
+-------------------------------------------------------------------+
                                  |
                                  v
+-------------------------------------------------------------------+
|  Rank 4: Text & Semantic Similarity (AUTOMATED_CANDIDATE)         |
|  - Bilingual token overlap, Levenshtein, and stemmed Jaccard      |
|  - Confidence strictly capped at <= 0.70                          |
|  - Strictly provisional; PENDING_REVIEW; NEVER auto-promoted      |
+-------------------------------------------------------------------+
```

---

## 3. Epistemic Anti-Hallucination Guardrails

The discovery engine actively tests every candidate pair against five epistemic guardrails to block false-positive causal assertions:

| Fallacy Guardrail | Condition | Policy / Resolution | Conflict Code |
|:---|:---|:---|:---|
| **Funding $\rightarrow$ Public Outcome** | Donor/Contribution linked to Public Work or Scheme as `funds`/`implements`. | **Blocked.** Political contributions cannot be asserted as direct causes of administrative public works. | `UNSUPPORTED_CAUSATION_FUNDING_TO_OUTCOME` |
| **Representative $\rightarrow$ Issue Culpability** | Civic issue linked to Representative with `concerns`/`implements`/`located_in` solely from spatial co-location. | **Blocked.** Issues are located in constituencies; representatives represent constituencies. Personal blame from spatial proximity is disallowed. | `SPATIAL_COOCCURRENCE_NOT_REPRESENTATIVE_CULPABILITY` |
| **Promise $\rightarrow$ Scheme Fulfillment** | Political promise linked to budget scheme as `implements` without statutory proof. | **Blocked.** Policy alignment is proposed as `relates_to` or `contextualizes`. `implements` is rejected without official Government Order. | `PROMISE_SCHEME_ALIGNMENT_DOES_NOT_PROVE_FULFILLMENT` |
| **News Report $\rightarrow$ Claim Truth** | News article linked to fact-checked claim as `provides_evidence_for` (asserting factual truth). | **Blocked.** Journalistic media can only `reports_on` or `mentions` claims; statutory reports establish evidence. | `MEDIA_REPORTING_DOES_NOT_ESTABLISH_FACTUAL_TRUTH` |
| **Correlation $\rightarrow$ Causation** | Correlated statistical indicators linked as `implements` or `funds`. | **Blocked.** Concurrent statistical trends can only `contextualize` each other. | `STATISTICAL_CORRELATION_DOES_NOT_ESTABLISH_CAUSATION` |

---

## 4. Architectural Separation: Candidate Proposals vs Confirmed Edges

Automatically proposed links are stored in `candidate_relationship_proposals` to prevent unreviewed heuristics from contaminating the verified evidence graph:

### Table Schema: `candidate_relationship_proposals`
- **`proposal_id` (PK):** Deterministic candidate identifier (e.g. `PROP:FUNDS:NODE_A:NODE_B:e4f8b9a1`).
- **`source_node_id` & `target_node_id`:** Foreign keys to `civic_graph_nodes.node_id`.
- **`relationship_type`:** Standardized `GraphRelationshipType`.
- **`evidence_supporting_candidate`:** Textual evidence explanation (shared ID, primary document, or lexical overlap).
- **`matching_method`:** `DETERMINISTIC_ID`, `DIRECT_DOCUMENTARY`, or `AUTOMATED_CANDIDATE`.
- **`confidence_score`:** Calibrated float score ($0.0 - 1.0$; capped at $\le 0.70$ for text similarity).
- **`temporal_validity_json`:** Analysis of fiscal year / date compatibility (`{"compatible": true, ...}`).
- **`geographic_context_json`:** Analysis of administrative area compatibility (`{"compatible": true, ...}`).
- **`possible_conflicts_json`:** List of flagged epistemic caveats or boundary conflicts.
- **`review_status`:** Enum disposition (`PENDING_REVIEW`, `CONFIRMED`, `REJECTED`, `DEFERRED`).
- **`confirmed_edge_id`:** Foreign reference to the created `civic_evidence_edges` row once approved.

---

## 5. Human Review Workflow Engine

Authorized domain auditors review candidates through three auditable transitions:

```
               +--------------------------------------+
               | Candidate Relationship Proposal      |
               | (review_status = PENDING_REVIEW)     |
               +--------------------------------------+
                     /           |            \
       Confirm      /    Reject  |      Defer  \
      [No Fatal    /             |              \
       Conflicts] /              |               \
                 v               v                v
      +--------------+   +--------------+   +--------------+
      |  CONFIRMED   |   |   REJECTED   |   |   DEFERRED   |
      +--------------+   +--------------+   +--------------+
             |
             v
+-----------------------------+
| Promoted to verified        |
| CivicEvidenceEdge           |
| (review_status = VERIFIED)  |
| with CivicEdgeAuditRecord   |
+-----------------------------+
```

### Review Operations:
1. **Confirm (`confirm_candidate`):**
   - Validates that the proposal contains **no fatal epistemic conflicts**.
   - Invokes `GraphStorageService.add_evidence_edge` with `matching_method = HUMAN_REVIEWED` and `review_status = VERIFIED`.
   - Sets proposal `review_status = CONFIRMED`, records `reviewer_id`, `reviewed_at`, `reviewer_notes`, and links `confirmed_edge_id`.
2. **Reject (`reject_candidate`):**
   - Sets proposal `review_status = REJECTED` with reviewer rationale.
   - Retains candidate record in database for audit history; no edge is created.
3. **Defer (`defer_candidate`):**
   - Sets proposal `review_status = DEFERRED` when awaiting future data releases or legislative sessions.

---

## 6. Test Suite Verification

The discovery engine and epistemic filters are verified by 10 comprehensive unit tests in [`tests/unit/test_phase9_relationship_discovery.py`](file:///e:/CIVCLENS/tests/unit/test_phase9_relationship_discovery.py):

| Test Case | Verification Objective | Result |
|:---|:---|:---:|
| `test_1_exact_identifier_discovery_priority` | Demand No and Petition ID exact matches yield `DETERMINISTIC_ID` ($\ge 0.95$). | **PASSED** |
| `test_2_documented_reference_discovery` | Shared primary source documents yield `DIRECT_DOCUMENTARY` citations. | **PASSED** |
| `test_3_canonical_entity_match_discovery` | Entities sharing Phase 9.2 canonical authority resolve with high confidence. | **PASSED** |
| `test_4_temporal_and_geographic_compatibility` | Mismatched fiscal years and distinct districts detected and flagged. | **PASSED** |
| `test_5_text_similarity_candidate_separation` | Lexical similarity generates provisional candidates ($\le 0.70$); isolated from edge table. | **PASSED** |
| `test_6_false_positive_funding_to_public_outcome` | Corporate funding to public work flagged as fallacy; confirmation blocked. | **PASSED** |
| `test_7_false_positive_representative_culpability` | Spatial co-location culpability flagged as fallacy; confirmation blocked. | **PASSED** |
| `test_8_false_positive_promise_scheme_fulfillment` | `implements` between promise and scheme blocked; `relates_to` approved. | **PASSED** |
| `test_9_false_positive_news_report_claim_truth` | Media report proving fact-checked claim blocked; `reports_on` approved. | **PASSED** |
| `test_10_human_review_workflow_confirm_reject_defer` | Full review lifecycle: confirm (creates verified edge), reject, and defer. | **PASSED** |
