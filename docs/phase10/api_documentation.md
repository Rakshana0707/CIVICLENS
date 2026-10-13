# CIVICLENS TN — Phase 10: Policy Evaluation API Documentation

## Overview

The Policy Evaluation API exposes structured endpoints for exploring Tamil Nadu public policy and scheme outcomes, budget execution metrics, target vs. actual outputs, indicator trajectories, and evidence-synthesized findings.

All endpoints adhere to CIVICLENS REST conventions:
- Base path: `/api/policy-evaluation`
- Standard response envelopes: `{"success": true, "data": ...}` or `{"success": false, "error": ...}`
- Role-based authorization for administrative and review actions via the `X-Reviewer-Role` HTTP header (`ADMIN`, `POLICY_ANALYST`, `REVIEWER`, `RESEARCHER`).

---

## Non-Causal Epistemic Guardrail

In accordance with strict public policy evaluation methodology, CIVICLENS enforces:
```json
"causal_claim_from_association_permitted": false
```
Association between a department or legislative representative and a geographic constituency or scheme **must never be interpreted or presented as causal proof** of policy success or failure without a formal counterfactual evaluation design.

---

## API Operations

### 1. Search Policies
- **Endpoint**: `GET /api/policy-evaluation/policies/search`
- **Query Parameters**:
  - `q`: Search query string across policy names, codes, and aliases.
  - `department`: Filter by responsible department.
  - `status`: Filter by evaluation status (`DRAFT`, `UNDER_REVIEW`, `ACTIVE`, `COMPLETED`, `ARCHIVED`).
  - `page`: Page number (default: 1).
  - `per_page`: Page size (default: 20, max: 100).
- **Response**: Paginated list of matching policy records with pagination metadata.

### 2. Policy Details
- **Endpoint**: `GET /api/policy-evaluation/policies/<policy_id>`
- **Response**: Full policy details including objectives, beneficiary groups, implementation activities, and canonical scheme mappings.

### 3. Evaluation Plans
- **Endpoint**: `GET /api/policy-evaluation/plans`
- **Query Parameters**:
  - `policy_id`: Filter by policy.
  - `page`, `per_page`: Pagination parameters.
- **Endpoint**: `GET /api/policy-evaluation/plans/<plan_id>`
- **Response**: Evaluation questions, indicator definitions, baseline/comparison periods, stated vs. inferred targets, and calculation methodologies.

### 4. Indicator Definitions
- **Endpoint**: `GET /api/policy-evaluation/indicators`
- **Query Parameters**:
  - `policy_id`: Filter indicators by policy.
  - `indicator_type`: `OUTPUT`, `OUTCOME`, `BUDGET`, `INTERMEDIATE_OUTCOME`.
- **Endpoint**: `GET /api/policy-evaluation/indicators/<indicator_id>`
- **Response**: Indicator definitions, units, reporting frequencies, formulas, and data limitations.

### 5. Baseline and Follow-up Observations
- **Endpoint**: `GET /api/policy-evaluation/indicators/<indicator_id>/observations`
- **Query Parameters**:
  - `observation_type`: `BASELINE`, `FOLLOW_UP`, `INTERIM`, `TARGET`.
  - `geographic_level`: `STATE`, `DISTRICT`, `BLOCK`, `VILLAGE_PANCHAYAT`.
- **Response**: Chronological observations with preserved `None` (missing data is never converted to zero).

### 6. Budget Execution and Output Analytics
- **Endpoint**: `GET /api/policy-evaluation/policies/<policy_id>/budget-analysis`
- **Response**:
  - Financial year allocations, revised estimates, actual expenditures.
  - Expenditure ratios and utilization rates.
  - Explicit warning: *Underspending alone is not proof of failure; overspending is not proof of success.*
- **Endpoint**: `GET /api/policy-evaluation/policies/<policy_id>/output-analysis`
- **Response**: Stated implementation targets vs. verified outputs and completion ratios.

### 7. Outcome Comparisons
- **Endpoint**: `GET /api/policy-evaluation/indicators/<indicator_id>/compare`
- **Query Parameters**:
  - `baseline_period`: e.g. `2021-22`
  - `followup_period`: e.g. `2023-24`
  - `geographic_scope`: Optional geographic filter
- **Response**: Absolute change, percentage change (when baseline != 0), calculation method, and explicit non-causal disclaimer.

### 8. Evaluation Findings
- **Endpoint**: `GET /api/policy-evaluation/findings`
- **Query Parameters**:
  - `policy_id`: Filter findings by policy.
  - `finding_type`: Filter by finding classification:
    - `IMPLEMENTATION_EVIDENCE_AVAILABLE`
    - `TARGET_ACHIEVEMENT_DOCUMENTED`
    - `OUTCOME_CHANGE_OBSERVED`
    - `CONFLICTING_FINDINGS`
    - `INSUFFICIENT_EVIDENCE`
    - `EVALUATION_PENDING_REVIEW`
  - `review_status`: Filter by status (`DRAFT`, `PEER_REVIEWED`, `VERIFIED`, `DISPUTED`).
- **Endpoint**: `GET /api/policy-evaluation/findings/<finding_id>`
- **Response**: Finding statement, strength rating, limitations, deterministic calculations, and source references.

### 9. Supporting and Contradicting Evidence
- **Endpoint**: `GET /api/policy-evaluation/findings/<finding_id>/evidence`
- **Response**: Complete evidence synthesis breakdown:
  - `supporting_evidence`: Verified citations directly corroborating the finding.
  - `contradicting_evidence`: Documented discrepancies or counter-evidence.
  - `contextual_evidence`: Methodological background and regional context.

### 10. Study Details and Methodological Rigor
- **Endpoint**: `GET /api/policy-evaluation/studies/<study_id>`
- **Response**: Full methodology documentation, design types, limitations, and study metadata.

### 11. Evidence Graph Connections
- **Endpoint**: `GET /api/policy-evaluation/policies/<policy_id>/graph-connections`
- **Response**: Subgraph connecting the policy to:
  - Canonical schemes and budget records
  - Manifesto promises
  - Claim verifications
  - Civic issues and public works
  - Relevant representative and constituency nodes (with strict epistemic non-causal attribution metadata)

### 12. Review Findings (Authorized Action)
- **Endpoint**: `POST /api/policy-evaluation/findings/<finding_id>/review`
- **Headers**: `X-Reviewer-Role: REVIEWER` or `ADMIN`
- **Body**:
  ```json
  {
    "review_status": "VERIFIED",
    "notes": "Peer review completed against CAG audit reports."
  }
  ```
- **Response**: Updated finding record with reviewer audit trail.

---

## Status Codes

| Code | Meaning |
|---|---|
| `200 OK` | Request succeeded. |
| `400 Bad Request` | Missing required parameters or validation error. |
| `403 Forbidden` | Missing or insufficient `X-Reviewer-Role` header. |
| `404 Not Found` | Requested entity not found. |
| `500 Server Error` | Unexpected backend error. |
