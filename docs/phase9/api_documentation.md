# Phase 9.7 — Unified Civic Search and Evidence Graph API Specification

## 1. Overview & Architectural Principles

The Phase 9.7 API exposes the **Unified Civic Intelligence and Evidence Graph** across Tamil Nadu public governance data (Phases 1–8). It implements secure, performant, explainable, and privacy-preserving query interfaces connecting budgets, schemes, political promises, news reports, political finance disclosures, representatives, constituencies, claims, civic complaints, and departmental resolutions.

### Epistemic Principles
1. **Reuse Existing Schemas**: Directly resolves to underlying Phase 1–8 relational records without duplicating data.
2. **Deterministic Evidence Priority**: Deterministic identifiers (demands, assembly questions, gazette notifications) take precedence over algorithmic similarity proposals.
3. **Association vs. Causation**: Prohibits unsubstantiated causal claims (e.g., correlation does not imply fulfillment or causation).
4. **Dialectical Tension Preservation**: Contradictory documents (e.g., CAG statutory audit reports vs. departmental press releases) are retained with epistemic weight comparisons rather than silently overwritten.

### Privacy & Security (DPDPA 2023 Compliance)
- **PII Scrubbing**: Citizen telephone numbers, personal emails, door/flat numbers, and personal identifiers are sanitized before leaving the API boundary.
- **Filesystem Path Redaction**: Internal server directory structures (e.g., `E:\CIVCLENS\...`) are stripped to `[REDACTED_SYSTEM_PATH]/...` preventing internal infrastructure reconnaissance.
- **Role-Based Access Control (RBAC)**: Graph mutation and review endpoints require authorized roles (`ADMIN`, `LEAD_REVIEWER`, `SENIOR_FACT_CHECKER`, `DOMAIN_EXPERT`, `AUDITOR`, `RESEARCHER`) passed via the `X-Reviewer-Role` header.

---

## 2. API Endpoints Specification

### Operation 1: Unified Entity Search
Searches canonical entities across Tamil Nadu civic entities with multilingual (Tamil/English) and alias lookup support.

- **Endpoint**: `GET /api/graph/entities/search`
- **Query Parameters**:
  - `q` (string): Query string (Tamil or English).
  - `entity_type` (string, optional): Filter by entity type (`GOVERNMENT_DEPARTMENT`, `SCHEME`, `POLITICAL_PARTY`, `REPRESENTATIVE`, `CONSTITUENCY`, `ADMINISTRATIVE_AREA`, `PUBLIC_CLAIM`, `CIVIC_ISSUE`, `SOURCE_DOCUMENT`, `PUBLIC_WORK`).
  - `source_phase` (string, optional): Filter by phase (`phase1` to `phase8`).
  - `limit` (integer, default `20`, max `100`): Result page limit.
  - `offset` (integer, default `0`): Pagination offset.
- **Sample Response**:
```json
{
  "status": "success",
  "data": {
    "total": 1,
    "limit": 20,
    "offset": 0,
    "results": [
      {
        "node_id": "NODE:DEPT:MAWS",
        "canonical_id": "DEPT-MAWS-TN",
        "label": "Municipal Administration and Water Supply Department",
        "label_ta": "நகராட்சி நிர்வாகம் மற்றும் குடிநீர் வழங்கல் துறை",
        "entity_type": "GOVERNMENT_DEPARTMENT",
        "source_phase": "phase3",
        "match_type": "exact_name",
        "aliases": ["MAWS", "MA&WS Tamil Nadu"],
        "created_at": "2026-10-12T10:00:00"
      }
    ]
  }
}
```

---

### Operation 2: Entity Profile and Source Records
Retrieves complete canonical entity details, aliases, verified source mappings, and connected edge statistics.

- **Endpoint**: `GET /api/graph/nodes/<node_id>`
- **Sample Response**:
```json
{
  "status": "success",
  "data": {
    "node": {
      "node_id": "NODE:DEPT:MAWS",
      "canonical_id": "DEPT-MAWS-TN",
      "label": "Municipal Administration and Water Supply Department",
      "entity_type": "GOVERNMENT_DEPARTMENT",
      "source_phase": "phase3",
      "label_ta": "நகராட்சி நிர்வாகம் மற்றும் குடிநீர் வழங்கல் துறை",
      "properties": {},
      "created_at": "2026-10-12T10:00:00"
    },
    "canonical_profile": {
      "canonical_id": "DEPT-MAWS-TN",
      "canonical_name_en": "Municipal Administration and Water Supply Department",
      "canonical_name_ta": "நகராட்சி நிர்வாகம் மற்றும் குடிநீர் வழங்கல் துறை",
      "description": "Nodal department responsible for urban infrastructure and water supply"
    },
    "aliases": ["MAWS", "MA&WS Tamil Nadu"],
    "source_mappings": [
      {
        "source_system": "TN_DEMAND_FOR_GRANTS",
        "source_record_id": "DEMAND-34",
        "original_name": "Municipal Administration & Water Supply Dept"
      }
    ],
    "edge_statistics": {
      "outbound_count": 2,
      "inbound_count": 0,
      "outbound_by_type": {
        "implements": 1,
        "funds": 1
      },
      "inbound_by_type": {}
    }
  }
}
```

---

### Operation 3: Direct Neighbor Exploration
Retrieves directly connected neighbor entities and their linking evidence edges.

- **Endpoint**: `GET /api/graph/nodes/<node_id>/neighbors`
- **Query Parameters**:
  - `direction` (string, default `both`): `outgoing`, `incoming`, or `both`.
  - `relationship_type` (string, optional): Filter by type (e.g., `funds`, `implements`, `promises`).
  - `target_type` (string, optional): Filter neighbor entity type.
  - `limit` (int, default `20`, max `100`).
  - `offset` (int, default `0`).
- **Sample Response**:
```json
{
  "status": "success",
  "data": {
    "center_node_id": "NODE:DEPT:MAWS",
    "total_edges": 1,
    "limit": 20,
    "offset": 0,
    "neighbors": [
      {
        "neighbor_node": {
          "node_id": "NODE:SCHEME:DESAL_NEMMELI",
          "canonical_id": "SCHEME-NEMMELI-150MLD",
          "label": "Nemmeli 150 MLD Desalination Plant Augmentation Scheme",
          "entity_type": "SCHEME",
          "source_phase": "phase2"
        },
        "edge": {
          "edge_id": "EDGE:DEPT:SCHEME:001",
          "relationship_type": "implements",
          "direction": "outbound",
          "evidence_reference": "GO Ms. No. 42 MAWS Department Budget Allotment 2023-24",
          "confidence_score": 0.95,
          "review_status": "VERIFIED",
          "provenance_status": "VALID",
          "source_document_id": "GO-MS-42-MAWS-2023"
        }
      }
    ]
  }
}
```

---

### Operation 4: Explainable Graph Traversal & Investigation
Executes multi-hop traversal with cycle protection, maximum depth limits, and canonical investigation templates.

- **Endpoint**: `GET /api/graph/traverse`
- **Query Parameters**:
  - `start_node_id` (string, required): Root node identifier.
  - `max_depth` (int, default `3`, max `6`): Traversal hop limit.
  - `allowed_relationship_types` (string, optional): Comma-separated relationships.
  - `min_confidence` (float, default `0.0`): Minimum edge confidence.
  - `limit` (int, default `50`).

- **Endpoint**: `GET /api/graph/investigate/<mode>`
- **Supported Investigation Modes**:
  1. `promise_delivery`: Political Promise → Scheme → Budget → Resolution.
  2. `claim_verification`: Claim → Supporting/Contradicting Evidence → Verification.
  3. `civic_accountability`: Civic Issue → Department → Response → Public Work.
  4. `representative_stewardship`: Representative → Constituency → Public Works.
  5. `political_finance`: Political Party → Donor Disclosure → Source Gazette.

- **Sample Response**:
```json
{
  "status": "success",
  "data": {
    "start_node_id": "NODE:PROM:DMK_DESAL",
    "investigation_mode": "promise_delivery",
    "paths_found": 1,
    "paths": [
      {
        "hop_count": 2,
        "nodes": [
          {"node_id": "NODE:PROM:DMK_DESAL", "label": "DMK Manifesto 2021 Item 114: Water Desalination", "entity_type": "POLITICAL_PROMISE"},
          {"node_id": "NODE:SCHEME:DESAL_NEMMELI", "label": "Nemmeli 150 MLD Desalination Scheme", "entity_type": "SCHEME"},
          {"node_id": "NODE:BUDGET:DEMAND_34", "label": "Demand 34 Capital Outlay for Water Infrastructure", "entity_type": "BUDGET_LINE_ITEM"}
        ],
        "edges": [
          {"edge_id": "EDGE:PROM:SCHEME:001", "relationship_type": "promises", "evidence_reference": "Manifesto Item 114 matches Scheme Title"},
          {"edge_id": "EDGE:SCHEME:BUDGET:001", "relationship_type": "funds", "evidence_reference": "Budget Grant 34 Head 4215"}
        ],
        "is_direct": true,
        "min_path_confidence": 0.90
      }
    ]
  }
}
```

---

### Operation 5: Edge Filtering and Querying
Filters evidence edges by relationship type, review status, matching method, and provenance.

- **Endpoint**: `GET /api/graph/edges`
- **Query Parameters**:
  - `relationship_type` (string, optional): e.g. `funds`, `implements`, `reports_on`.
  - `matching_method` (string, optional): `DIRECT_DOCUMENTARY`, `DETERMINISTIC_ID`, `AUTOMATED_CANDIDATE`, `HUMAN_REVIEWED`.
  - `review_status` (string, optional): `PENDING_REVIEW`, `VERIFIED`, `REJECTED`, `OVERRIDDEN`.
  - `source_node_id` / `target_node_id` (string, optional): Node endpoints.
  - `source_document_id` (string, optional): Document filter.
  - `min_confidence` (float, default `0.0`).
  - `active_only` (bool, default `true`): Excludes `RETRACTED` and `SUPERSEDED` edges.
  - `limit` (int, default `20`), `offset` (int, default `0`).

---

### Operation 6: Evidence Details for Individual Relationship
Retrieves complete evidentiary lineage, source document hashes, verification status, and quality scorecards.

- **Endpoint**: `GET /api/graph/edges/<edge_id>`
- **Sample Response**:
```json
{
  "status": "success",
  "data": {
    "edge_id": "EDGE:DEPT:SCHEME:001",
    "source_node": {"node_id": "NODE:DEPT:MAWS", "label": "Municipal Administration and Water Supply Department"},
    "target_node": {"node_id": "NODE:SCHEME:DESAL_NEMMELI", "label": "Nemmeli 150 MLD Desalination Scheme"},
    "relationship_type": "implements",
    "evidence_reference": "GO Ms. No. 42 MAWS Department Budget Allotment 2023-24",
    "source_document_id": "GO-MS-42-MAWS-2023",
    "source_document_hash": "a1b2c3d4e5f67890abcdef1234567890abcdef1234567890abcdef1234567890",
    "matching_method": "DIRECT_DOCUMENTARY",
    "confidence_score": 0.95,
    "review_status": "VERIFIED",
    "provenance_status": "VALID",
    "quality_scorecard": {
      "overall_quality_score": 0.92,
      "factors": {
        "source_authenticity": 1.0,
        "directness_of_evidence": 0.95,
        "document_availability": 1.0,
        "temporal_consistency": 0.90,
        "geographic_compatibility": 0.95
      }
    },
    "active_conflicts": []
  }
}
```

---

### Operation 7: Listing Unresolved Relationship Candidates
Lists candidate proposals generated by Phase 9.4 discovery engine awaiting human audit review.

- **Endpoint**: `GET /api/graph/proposals/unresolved`
- **Query Parameters**:
  - `min_confidence` (float, default `0.0`).
  - `source_node_id` / `target_node_id` (string, optional).
  - `limit` (int, default `20`), `offset` (int, default `0`).
- **Sample Response**:
```json
{
  "status": "success",
  "data": {
    "total": 1,
    "limit": 20,
    "offset": 0,
    "unresolved_proposals": [
      {
        "proposal_id": "PROP-CANDIDATE-001",
        "source_node_id": "NODE:SCHEME:DESAL_NEMMELI",
        "target_node_id": "NODE:ISSUE:WATER_SHORTAGE_VELACHERY",
        "relationship_type": "responds_to",
        "evidence_supporting_candidate": "Scheme augmentation addresses localized distribution complaints",
        "matching_method": "AUTOMATED_CANDIDATE",
        "confidence_score": 0.74,
        "review_status": "PENDING_REVIEW"
      }
    ]
  }
}
```

---

### Operation 8: Contradictory and Disputed Evidence
Retrieves dialetical contradictions, statutory vs. departmental report tensions, and disputed edges.

- **Endpoint**: `GET /api/graph/conflicts`
- **Endpoint**: `GET /api/graph/disputes`
- **Query Parameters**:
  - `node_id` (string, optional): Associated node.
  - `conflict_type` (string, optional): e.g. `CONTRADICTORY_CLAIM_EVIDENCE`, `TEMPORAL_INCOMPATIBILITY`.
  - `severity` (string, optional): `CRITICAL`, `HIGH`, `MEDIUM`, `LOW`.
  - `resolution_status` (string, optional): `UNRESOLVED`, `EXPLAINED_DIALECTIC`, `RESOLVED`.
- **Sample Response**:
```json
{
  "status": "success",
  "data": {
    "total_conflicts": 1,
    "conflicts": [
      {
        "conflict_id": "CONF-DESAL-OUTPUT-01",
        "conflict_type": "CONTRADICTORY_CLAIM_EVIDENCE",
        "severity": "HIGH",
        "primary_node_id": "NODE:CLAIM:DESAL_OUTPUT",
        "description": "CAG audit para 3.8 contradicts departmental press release on effective daily output",
        "epistemic_weight_comparison": {
          "statutory_weight": 0.95,
          "media_weight": 0.65,
          "rule": "Newer press release does not automatically invalidate statutory audit"
        },
        "resolution_status": "EXPLAINED_DIALECTIC"
      }
    ],
    "total_disputed_edges": 1,
    "disputed_edges": [
      {
        "edge_id": "EDGE:CLAIM:SCHEME:001",
        "relationship_type": "provides_evidence_for",
        "provenance_status": "DISPUTED",
        "evidence_reference": "Preliminary contractor statement disputed by independent scrutiny"
      }
    ]
  }
}
```

---

### Operation 9: Graph Provenance and Review History
Inspects immutable review and audit actions across relationship confirmations, rejections, deferrals, and entity lifecycle operations.

- **Endpoint**: `GET /api/graph/history`
- **Query Parameters**:
  - `node_id` / `edge_id` (string, optional).
  - `reviewer_id` (string, optional).
  - `action` (string, optional): e.g. `CONFIRMED`, `REJECTED`, `DEFERRED`.
  - `limit` (int, default `20`), `offset` (int, default `0`).
- **Sample Response**:
```json
{
  "status": "success",
  "data": {
    "total": 1,
    "history": [
      {
        "record_type": "PROPOSAL_REVIEW",
        "proposal_id": "PROP-CANDIDATE-001",
        "reviewer_id": "REVIEWER_OFFICIAL_42",
        "disposition": "CONFIRMED",
        "rationale": "Verified through official gazette notification cross-reference",
        "reviewed_at": "2026-10-12T11:30:00"
      }
    ]
  }
}
```

---

### Operation 10: Original Phase Module Record Resolution
Resolves a graph node directly to its underlying Phase 1–8 database record, returning the original source model attributes with automated PII masking.

- **Endpoint**: `GET /api/graph/nodes/<node_id>/original-record`
- **Supported Phase Model Mappings**:
  - `POLITICAL_PROMISE` → `PoliticalPromise` (Phase 1)
  - `SCHEME` → `Scheme` / `BudgetLineItem` (Phase 2)
  - `GOVERNMENT_DEPARTMENT` → `Department` (Phase 3)
  - `NEWS_ARTICLE` / `FACT_CHECK` → `NewsArticle` / `FactCheck` (Phase 4)
  - `POLITICAL_PARTY` / `DONOR` → `Party` / `ElectoralBondTransaction` (Phase 5)
  - `REPRESENTATIVE` / `CONSTITUENCY` → `Representative` / `Constituency` (Phase 6)
  - `CIVIC_ISSUE` / `RESOLUTION` → `CivicIssue` / `IssueResolutionEvidence` (Phase 7)
  - `PUBLIC_CLAIM` → `Claim` (Phase 8)
- **Sample Response**:
```json
{
  "status": "success",
  "data": {
    "node_id": "NODE:PROM:DMK_DESAL",
    "canonical_id": "PROM-DMK-2021-WATER",
    "source_phase": "phase1",
    "model_name": "PoliticalPromise",
    "record": {
      "promise_id": "PROM-DMK-2021-WATER",
      "manifesto_id": "MAN-DMK-2021",
      "original_text": "Ensure 24x7 treated water supply to South Chennai through modern desalination",
      "classification": "water_infrastructure",
      "metadata_json": {
        "status": "IN_PROGRESS"
      }
    }
  }
}
```

---

### Candidate Proposal Review Actions (RBAC Guarded)
Requires `X-Reviewer-Role` header with an authorized role (`ADMIN`, `LEAD_REVIEWER`, `SENIOR_FACT_CHECKER`, `DOMAIN_EXPERT`, `AUDITOR`, `RESEARCHER`).

- **Confirm**: `POST /api/graph/proposals/<proposal_id>/confirm`
  - Body: `{"reviewer_id": "REV_42", "rationale": "Gazette reference verified"}`
  - Promotes proposal to active `CivicEvidenceEdge`.
- **Reject**: `POST /api/graph/proposals/<proposal_id>/reject`
  - Body: `{"reviewer_id": "REV_42", "rationale": "False positive entity match"}`
  - Sets disposition to `REJECTED`, preventing spurious edge creation.
- **Defer**: `POST /api/graph/proposals/<proposal_id>/defer`
  - Body: `{"reviewer_id": "REV_42", "rationale": "Pending assembly question response"}`
  - Sets disposition to `DEFERRED` for future review.
