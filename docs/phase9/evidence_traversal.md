# Phase 9.5 — Evidence Paths and Explainable Graph Traversal

## 1. Executive Summary & Design Rationale

**Phase 9.5** implements the **Explainable Evidence Traversal Engine** for **CIVICLENS TN**.

The engine enables investigative journalists, civic auditors, and citizens to start from any civic intelligence entity and discover connected records across Phases 1 through 8 via permitted, evidence-backed relationship types.

### 1.1 Core Principles
1. **Explainable Multi-Hop Traversal:** Every discovered path returns the complete sequence of intermediate nodes, relationship types, source document citations, and cryptographic hashes.
2. **Direct vs Inferred Link Discrimination:** Links established by primary documents (`DIRECT_DOCUMENTARY`) or exact tokens (`DETERMINISTIC_ID`) are clearly distinguished from candidate/transitive inferences (`AUTOMATED_CANDIDATE`).
3. **Exposing Uncertainty and Disputes:** Relationships with unverified review status (`PENDING_REVIEW`, `REJECTED`, `DISPUTED`) or provisional confidence (<0.85) are explicitly surfaced with diagnostic warnings.
4. **Missing Evidence Identification:** If a step along an expected investigative path lacks statutory documentation (e.g. scheme without budget sub-head, or promise without Government Order), the engine flags the exact missing evidence gap.
5. **Association vs Causation Guardrails:** Epistemic caveats accompany every path to prevent unsupported causal conclusions (policy alignment $\neq$ fulfillment, territorial presence $\neq$ representative blame, political donation $\neq$ procurement causality).
6. **Strict Anti-Fabrication Safeguard:** The engine **never manufactures** a path or bridges disconnected records when an intermediate relationship is missing.

---

## 2. Investigation Walk Templates

The engine provides 5 canonical investigation walk templates designed for civic accountability in Tamil Nadu:

```
Investigation Walk 1: Promise to Implementation
[Political Promise] --(relates_to)--> [Budget Scheme] <-- (funds) -- [Budget Record] --(implements)--> [Public Work / Evidence]

Investigation Walk 2: Public Claim Dialectical Verification
[Statutory Report / DPI] --(provides_evidence_for)--> [Public Claim] <--(contradicts)-- [Audit Report / CAG]

Investigation Walk 3: Civic Issue Resolution Pipeline
[Civic Issue] --(concerns)--> [Grievance Record] <--(responds_to)-- [Department Response] <--(provides_evidence_for)-- [Resolution Lab Cert]

Investigation Walk 4: Representative Legislative & Public Works
[MLA / Representative] --(represents)--> [Constituency] <--(located_in)-- [Public Work / Legislative Record]

Investigation Walk 5: Campaign Funding Disclosure Lineage
[Electoral Bond Contribution] --(funds)--> [Political Party] --(derived_from)--> [ECI Statutory Affidavit]
```

---

## 3. Explainable Path Data Structure

Every path returned by `EvidenceTraversalEngine.find_paths` or `investigate_*` contains granular metadata:

```json
{
  "path_id": "PATH:1",
  "start_node_id": "NODE:PROM:BREAKFAST_2021",
  "end_node_id": "NODE:IMPL:PRIMARY_SCHOOL_KITCHENS",
  "length": 3,
  "nodes": [
    { "node_id": "NODE:PROM:BREAKFAST_2021", "entity_type": "POLITICAL_PROMISE", "label": "DMK 2021 Manifesto Promise 314" },
    { "node_id": "NODE:SCHEME:BREAKFAST_TN", "entity_type": "HISTORICAL_SCHEME", "label": "Chief Minister Breakfast Scheme" },
    { "node_id": "NODE:IMPL:PRIMARY_SCHOOL_KITCHENS", "entity_type": "PUBLIC_WORK", "label": "Centralized Kitchen Infrastructure" }
  ],
  "edges": [
    {
      "edge_id": "EDGE:RELATES_TO:PROM:SCHEME:DOC_MAN",
      "relationship_type": "relates_to",
      "matching_method": "DIRECT_DOCUMENTARY",
      "is_direct": true,
      "is_uncertain_or_disputed": false,
      "source_document_id": "DOC-MAN-DMK-2021",
      "evidence_reference": "Manifesto Item 314 shares primary policy target"
    }
  ],
  "is_direct_path": true,
  "has_uncertain_edges": false,
  "missing_evidence": [],
  "epistemic_caveats": [
    "Policy Intent Association: Political promise relates to scheme as policy alignment. This link does NOT constitute proof of promise fulfillment without audited Government Orders and expenditure line items."
  ],
  "conflicting_evidence": [],
  "summary": "Evidence path of 3 hop(s): [Promise] -> [Scheme] -> [Public Work]. Verification: Direct documentary path. All edges verified."
}
```

---

## 4. Traversal Safeguards & Performance Protections

| Safeguard | Risk Mitigated | Implementation Mechanism |
|:---|:---|:---|
| **Cycle Prevention** | Infinite recursion and duplicate visits in cyclic subgraphs. | Branch-scoped visited tracking (`if next_node_id in path_node_ids: continue`). |
| **Depth Bounds** | Combinatorial query explosion in dense subgraphs. | Configurable `max_depth` (default 4, hard cap at 6 hops). |
| **Result Limits** | Out-of-memory errors on broad traversals. | Configurable `max_paths` (default 20) and 500-node exploration cap. |
| **Directional Filtering** | Irrelevant reverse or forward traversals. | Configurable `direction`: `"outgoing"`, `"incoming"`, or `"both"`. |
| **Relationship Filtering** | Noise from tangential associations. | Explicit `permitted_relationships` set filter. |
| **Active-Only Ingestion** | Retracted or superseded links polluting active investigations. | `active_only=True` queries only `provenance_status == VALID`. |
| **Anti-Fabrication** | Groundless synthetic bridging between disconnected records. | Traversal strictly follows verified database edges; missing intermediate links terminate the path. |

---

## 5. REST API Reference

Mounted under the central router at `/api/graph`:

### 5.1 General Traversal: `POST /api/graph/traverse`
**Request Body:**
```json
{
  "start_node_id": "NODE:CLAIM:ATTENDANCE_18_PCT",
  "direction": "both",
  "max_depth": 3,
  "max_paths": 20,
  "active_only": true
}
```
**Response (200 OK):**
```json
{
  "status": "success",
  "data": {
    "paths": [...],
    "total_paths": 2
  }
}
```

### 5.2 Named Investigation Walk: `GET /api/graph/investigate/<mode>`
- **Supported Modes:** `promise`, `claim`, `civic_issue`, `representative`, `funding`.
- **Query Parameters:** `node_id` (mandatory), `max_depth` (optional, default 4).
- **Example:** `GET /api/graph/investigate/claim?node_id=NODE:CLAIM:ATTENDANCE_18_PCT&max_depth=3`

### 5.3 Node Edges Lookup: `GET /api/graph/nodes/<node_id>/edges`
- **Query Parameters:** `direction` (`outgoing`, `incoming`, `both`), `relationship_type`, `active_only`.

---

## 6. Test Suite Verification

Verified by 10 comprehensive unit tests in [`tests/unit/test_phase9_evidence_traversal.py`](file:///e:/CIVCLENS/tests/unit/test_phase9_evidence_traversal.py):

| Test Case | Verification Objective | Status |
|:---|:---|:---:|
| `test_1_investigation_path_1_promise_scheme_budget_impl` | Promise -> Scheme -> Budget -> Implementation completeness and fulfillment caveat. | **PASSED** |
| `test_2_investigation_path_2_claim_dialectical_evidence` | Simultaneous supporting and contradicting evidence branches exposed. | **PASSED** |
| `test_3_investigation_path_3_civic_issue_resolution` | Issue -> Grievance -> Response -> Lab clearance certificate pipeline. | **PASSED** |
| `test_4_investigation_path_4_representative_constituency` | Representative -> Constituency -> Works with spatial non-culpability caveat. | **PASSED** |
| `test_5_investigation_path_5_funding_disclosure_lineage` | Contribution -> Party -> ECI affidavit lineage with non-causation caveat. | **PASSED** |
| `test_6_anti_fabrication_missing_intermediate_edges` | Missing edges terminate path; engine never manufactures artificial bridges. | **PASSED** |
| `test_7_cycle_prevention_safeguard` | Cyclic topology (A -> B -> C -> A) terminates cleanly without node duplication. | **PASSED** |
| `test_8_depth_and_result_limits` | `max_depth` and `max_paths` strictly enforce search boundaries. | **PASSED** |
| `test_9_direct_vs_inferred_links_uncertain_edges` | Distinguishes documentary paths from candidate/unreviewed edges with warnings. | **PASSED** |
| `test_10_rest_api_traversal_and_investigation_endpoints` | REST API routes `/api/graph/traverse` and `/api/graph/investigate/<mode>` operational. | **PASSED** |
