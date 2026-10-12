# Phase 9.3 — Evidence Graph Storage and Relationship Validation

## 1. Executive Summary & Design Rationale

**Phase 9.3** implements the storage, integrity, and validation engine of the **Unified Civic Intelligence & Evidence Graph** for **CIVICLENS TN**.

### 1.1 Relational Graph Storage vs External Graph Databases
A primary architectural question for Phase 9 was whether to introduce a dedicated external graph database (such as Neo4j, Amazon Neptune, or Memgraph). Following a thorough audit of the project infrastructure, an external graph database was deliberately rejected for the following technical and operational reasons:
1. **Relational Co-location:** All underlying domain records from Phases 1 through 8 (budgets, manifestos, promises, media articles, financial disclosures, MLAs, claim verifications, civic issues) reside in relational SQLAlchemy tables (SQLite in local development, PostgreSQL in production). Maintaining a separate graph database creates data synchronization latency, distributed transaction failure modes, and deployment complexity.
2. **First-Class Provenance & Cryptographic Audit:** Unlike traditional property graph databases where edges are lightweight pointers, every edge in CIVICLENS TN is an evidence citation with a source document reference, page/table citations, SHA-256 artifact hashes, confidence scores, temporal validity ranges, and human-in-the-loop review statuses. Relational tables with strict foreign key constraints and immutable audit log tables provide stronger referential integrity.
3. **Low Graph Depth Traversal:** Civic intelligence queries in Tamil Nadu are typically 1- to 3-hop contextual traversals (e.g., *Promise -> Scheme -> Budget Record* or *Civic Grievance -> Administrative Area -> Representative*), which relational indexed join queries execute with sub-millisecond latency.
4. **Compatibility & Zero Additional Dependencies:** Using SQLAlchemy declarative models maintains 100% compatibility with existing test runners, database migrations (Alembic), FastAPI/Flask route conventions, and offline audit tooling.

---

## 2. Graph Storage Schema Architecture

The graph storage layer consists of three interconnected relational models:

```
+------------------------------------+
|          CanonicalEntity           | (Phase 9.2 Registry)
|  - entity_id (PK)                  |
|  - canonical_name_en / ta          |
+------------------------------------+
                  ^
                  | canonical_entity_id (FK, ON DELETE SET NULL)
+------------------------------------+
|          CivicGraphNode            |
|  - node_id (PK)                    |
|  - entity_type (Enum)              |
|  - canonical_id                    |
|  - label / label_ta                |
|  - source_phase                    |
+------------------------------------+
        ^                      ^
        | source_node_id       | target_node_id
+-------------------------------------------------------------+
|                     CivicEvidenceEdge                       |
|  - edge_id (PK)                                             |
|  - relationship_type (Enum)                                 |
|  - evidence_reference (Quote / Table Cell / Excerpt)        |
|  - source_document_id / url / SHA-256 hash                  |
|  - matching_method (DOCUMENTARY / CANDIDATE / REVIEWED)     |
|  - confidence_score                                         |
|  - review_status (PENDING_REVIEW / VERIFIED / REJECTED)     |
|  - provenance_status (VALID / RETRACTED / SUPERSEDED)       |
|  - valid_from / valid_to (Temporal Validity)                |
+-------------------------------------------------------------+
                               ^
                               | edge_id (FK, ON DELETE CASCADE)
+-------------------------------------------------------------+
|                   CivicEdgeAuditRecord                      |
|  - audit_id (PK)                                            |
|  - operation_type (CREATE / CORRECT / RETRACT / RESTORE)    |
|  - rationale (Mandatory justification)                      |
|  - performed_by (Auditor / System identifier)               |
|  - previous_state_json / new_state_json                     |
|  - timestamp                                                |
+-------------------------------------------------------------+
```

### 2.1 Node Definition: `CivicGraphNode`
- **Primary Key:** `node_id` (e.g., `NODE:REP:STALIN`, `NODE:SCHEME:BREAKFAST`).
- **Canonical Registry Link:** `canonical_entity_id` foreign key referencing `canonical_entities.entity_id` (Phase 9.2).
- **Domain Identity:** `entity_type` (33 domain entity types across Phases 1–8) and `canonical_id` (original table primary key).
- **Unique Constraint:** `(entity_type, canonical_id)` ensures deterministic 1:1 mapping between domain records and graph nodes.

### 2.2 Edge Definition: `CivicEvidenceEdge`
- **Primary Key:** `edge_id` (deterministic format: `EDGE:{RELATIONSHIP}:{SOURCE}:{TARGET}:{DOC_SLUG}`).
- **Directed Reference:** `source_node_id` and `target_node_id` referencing `civic_graph_nodes.node_id`.
- **Vocabulary:** Strongly typed `GraphRelationshipType` (`funds`, `implements`, `promises`, `relates_to`, `reports_on`, `mentions`, `concerns`, `represents`, `responds_to`, `provides_evidence_for`, `contradicts`, `contextualizes`, `located_in`, `derived_from`).
- **Granular Evidence Provenance:**
  - `evidence_reference`: Exact text excerpt, statutory table row, or gazette paragraph.
  - `source_document_id`: Reference to statutory publication, gazette, report, or ECI affidavit.
  - `source_document_url`: Official government/statutory URI.
  - `source_document_hash`: SHA-256 cryptographic hash of originating artifact.
- **Methodology & Review:**
  - `matching_method`: `DIRECT_DOCUMENTARY`, `DETERMINISTIC_ID`, `AUTOMATED_CANDIDATE`, or `HUMAN_REVIEWED`.
  - `confidence_score`: Float between 0.0 and 1.0.
  - `review_status`: `PENDING_REVIEW`, `VERIFIED`, `REJECTED`, or `OVERRIDDEN`.
  - `provenance_status`: `VALID`, `PROVISIONAL`, `DISPUTED`, `SUPERSEDED`, or `RETRACTED`.
- **Temporal Validity:**
  - `valid_from`: String ISO date or fiscal year (e.g., `2021-05-07`, `2022-23`).
  - `valid_to`: String ISO date, fiscal year, or `None` if currently open/active.
- **Deduplication Unique Constraint:** `(source_node_id, target_node_id, relationship_type, source_document_id)`.

### 2.3 Immutable Edge Audit Ledger: `CivicEdgeAuditRecord`
- Tracks all lifecycle mutations without deleting historical records:
  - `operation_type`: `CREATE`, `UPDATE`, `CORRECT`, `RETRACT`, `SUPERSEDE`, `RESTORE`.
  - `rationale`: Mandatory explanation for why the edge was modified, retracted, or restored.
  - `performed_by`: Audit actor or process token.
  - `previous_state_json` & `new_state_json`: Complete state snapshots before and after the operation.

---

## 3. Epistemic Validation Rules

The core validation engine (`GraphStorageService.validate_relationship`) enforces five epistemic constraints prior to creating or mutating edges:

### Rule 1 — Response to Civic Issue
> *“A response can relate to a civic issue only when supported by a source or reviewed matching decision.”*
- **Constraint:** When connecting a `RESPONSE_RECORD` / `RESOLUTION_EVIDENCE` to a `CIVIC_ISSUE` / `GRIEVANCE_RECORD`:
- **Validation:** If the matching method is `AUTOMATED_CANDIDATE`, it is **rejected** unless either:
  1. It cites a verified official `source_document_id`, OR
  2. It has been reviewed and verified by a human auditor (`review_status == VERIFIED` or `matching_method == HUMAN_REVIEWED`).
- **Rationale:** Heuristic NLP similarity must not falsely link an official response to an unresolved public grievance without documentary proof.

### Rule 2 — Promise to Scheme (Non-Automatic Fulfillment)
> *“A promise can relate to a scheme without automatically proving the promise was fulfilled.”*
- **Constraint:** A `POLITICAL_PROMISE` can relate to a `BUDGET_SCHEME` or `HISTORICAL_SCHEME` using `relates_to` or `contextualizes`.
- **Validation:** Asserting `implements` or `provides_evidence_for` (which claims direct implementation or fulfillment) is **strictly rejected** unless accompanied by explicit documentary proof of fulfillment in properties (e.g., official Government Order `G.O. (Ms) No.`, verified budget expenditure line item).
- **Rationale:** A political party promising a scheme in an election manifesto does not prove the resulting administrative scheme fulfilled the promise.

### Rule 3 — Funding Disclosure Identity Support
> *“A funding disclosure can relate to a party or donor only when the identity match is supported.”*
- **Constraint:** Linking a `CONTRIBUTION`, `FINANCIAL_DOCUMENT`, `ELECTION_EXPENDITURE`, or `ELECTORAL_TRUST` to a `POLITICAL_PARTY` or `DONOR`:
- **Validation:** Automated candidate matches with confidence score below `0.70` are **rejected** without verified human review. Edges flagged with `unsupported_match: true` are categorically rejected.
- **Rationale:** Financial and electoral contributions carry severe legal and ethical implications; speculative or low-confidence donor matches must not contaminate the evidence graph.

### Rule 4 — Claim Dialectic (Coexistence of Supporting and Contradicting Evidence)
> *“A claim can have supporting and contradicting evidence simultaneously.”*
- **Constraint:** Fact-checked claims often involve contested public data or competing audits.
- **Validation:** Both `provides_evidence_for` and `contradicts` edges are explicitly permitted to exist concurrently on the same `CLAIM` node without triggering conflict rejections.
- **Rationale:** Preserves multi-source pluralism and democratic contestability.

### Rule 5 — Civic Issue Geographic Association Guardrail
> *“A civic issue's geographic association does not establish an individual representative's responsibility.”*
- **Constraint:** Connecting a `CIVIC_ISSUE` to a `REPRESENTATIVE`:
- **Validation:** 
  1. A civic issue cannot have relationship `located_in` directly to an individual representative (issues are located in `CONSTITUENCY` boundaries).
  2. Attributing personal responsibility solely from geographic co-occurrence (`geographic_association_only: true` or `attribution_basis: "geographic_cooccurrence"`) is **strictly rejected**.
- **Rationale:** An issue occurring in an MLA's constituency does not establish personal administrative culpability without formal assembly proceedings, official petitions, or statutory assignments.

---

## 4. Idempotent Ingestion & Repeatable Imports

To support batch ingestion scripts and repeated pipelines without database corruption:
1. **Deduplication Check:** When `add_evidence_edge` is called, it checks whether an edge with identical `(source_node_id, target_node_id, relationship_type, source_document_id)` already exists.
2. **Active Edge Handling:** If the edge already exists and its `provenance_status` is `VALID`, the service logs a repeatable import notice and returns the existing edge instance.
3. **Re-activation Handling:** If an existing edge was previously `RETRACTED` or `SUPERSEDED`, re-importing it updates the fields, sets status to `VALID`, and creates a restoration audit record in `civic_edge_audit_records`.
4. **Referential Integrity:** Missing source or target nodes raise `NodeNotFoundError` before any edge is queued for insertion. Self-loops raise `EpistemicRuleViolationError`.

---

## 5. Reversible Entity-Link Corrections & Provenance Preservation

CIVICLENS TN enforces a **zero data deletion** policy for evidence links. Corrections are handled through soft-reversals:

| Operation | Method | Status Set To | Audit Operation | Behavior |
|:---|:---|:---|:---|:---|
| **Initial Ingest** | `add_evidence_edge` | `VALID` | `CREATE` | Creates edge and first audit snapshot. |
| **Correction** | `correct_edge` | Unchanged / `VALID` | `CORRECT` | Updates confidence, dates, or notes; logs before/after diff. |
| **Retraction** | `retract_edge` | `RETRACTED` | `RETRACT` | Soft-deactivates edge; hidden from active queries, retained in DB. |
| **Restoration** | `restore_edge` | `VALID` | `RESTORE` | Reactivates a retracted edge with new audit justification. |
| **Supersession** | `supersede_edge` | `SUPERSEDED` | `SUPERSEDED` | Marks old edge as superseded and points to new replacement edge. |

### Querying with Provenance Filtering
- `GraphStorageService.get_node_edges(..., active_only=True)`: Filters strictly for `provenance_status == VALID`.
- `GraphStorageService.get_node_edges(..., active_only=False)`: Returns all edges including historical retractions and supersessions.
- `GraphStorageService.get_edge_audit_records(..., edge_id)`: Retrieves the complete, immutable chronological audit trail for the edge.

---

## 6. Verification & Test Suite Summary

The graph storage and validation layer is verified by a dedicated test suite in [`tests/unit/test_phase9_graph_storage.py`](file:///e:/CIVCLENS/tests/unit/test_phase9_graph_storage.py):

| Test Case | Objective | Status |
|:---|:---|:---:|
| `test_1_referential_integrity_nonexistent_nodes` | Non-existent source/target nodes and self-loops rejected. | **PASSED** |
| `test_2_missing_evidence_rejection` | Unbacked edges missing citations rejected. | **PASSED** |
| `test_3_duplicate_edges_and_repeatable_imports` | Repeat imports idempotent; duplicate rows prevented. | **PASSED** |
| `test_4_epistemic_rule_1_response_to_civic_issue` | Unreviewed candidate responses rejected; documentary approved. | **PASSED** |
| `test_5_epistemic_rule_2_promise_to_scheme_fulfillment_guardrail` | `relates_to` allowed; `implements` rejected without G.O. proof. | **PASSED** |
| `test_6_epistemic_rule_3_funding_disclosure_identity_support` | Low confidence candidate (<0.70) rejected; deterministic allowed. | **PASSED** |
| `test_7_epistemic_rule_4_claim_dialectical_evidence` | Simultaneous `provides_evidence_for` and `contradicts` co-exist cleanly. | **PASSED** |
| `test_8_epistemic_rule_5_civic_issue_geographic_association` | `located_in` to representative rejected; constituency link approved. | **PASSED** |
| `test_9_reversible_edge_corrections_and_soft_reversals` | Retract, restore, supersede, correct lifecycle verified in audit ledger. | **PASSED** |
| `test_10_canonical_entity_linking_and_traversal` | Foreign key linkage to Phase 9.2 `CanonicalEntity` and bidirectional queries. | **PASSED** |
