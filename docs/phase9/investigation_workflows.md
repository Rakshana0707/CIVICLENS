# Phase 9.9 — Cross-Phase Investigation Workflows and Auditability

## 1. Executive Summary & Epistemic Methodology

The **Cross-Phase Investigation Workflows Engine** of CIVICLENS TN provides structured, verifiable, and auditable inquiry paths connecting empirical data across Phases 1 through 8.

Rather than producing automated, unsupported final "verdicts" or assigning unilateral blame, CIVICLENS TN generates **Auditable Investigation Dossiers** that:
1. **Show records actually available**: Itemizes primary records present in the civic intelligence graph.
2. **Preserve verifiable source links**: Retains issuing authorities, Government Order (G.O.) numbers, Hansard debate citations, and cryptographic SHA-256 hashes.
3. **Expose missing information**: Explicitly flags missing expenditure vouchers, absent ground inspections, or gaps between policy announcements and physical deliverables.
4. **Identify unreviewed links**: Distinguishes confirmed evidence edges from algorithmically proposed candidate links (`PENDING_REVIEW`).
5. **Separate official claims from independent verification**: Differentiates self-reported department Action Taken Reports (ATRs) and ministerial press announcements from independent statutory scrutiny (e.g. Comptroller and Auditor General audits, RTI responses, water telemetry).
6. **Retain reviewer audit history**: Maintains an immutable ledger of human review decisions, rationales, and timestamps.
7. **Formulate non-verdict summaries**: Highlights verifiable facts and poses precise, unresolved governance questions for further statutory scrutiny.

---

## 2. Canonical Investigation Workflows

### WORKFLOW A: Political Promise Delivery
**Chain:** Political Promise → Related Schemes → Capital Budgets → Implementation & Claim Records

- **Analytical Goal**: Traces election manifesto pledges to statutory government orders, capital budget outlays, and physical infrastructure outcomes.
- **Records Evaluated**:
  - `POLITICAL_PROMISE` (Phase 1): Original manifesto text, classification, and election year.
  - `SCHEME` (Phase 2): Cabinet administrative sanction, executing board, head of account.
  - `BUDGET_LINE_ITEM` (Phase 1): Demand for Grants, allocated outlay, revised estimates.
  - `PUBLIC_CLAIM` & `RESOLUTION_EVIDENCE` (Phases 7–8): Departmental commissioning reports vs. field audits.
- **Epistemic Guardrail**:
  > *Allocating budget capital to an associated scheme demonstrates policy activity, but does NOT establish that the pledge was completed without verified end-user service delivery evidence.*
- **Gaps Detected**: Missing audited utilization certificates; budget outlays that reflect administrative overhead rather than new physical assets.

---

### WORKFLOW B: Civic Issue Resolution & Departmental Redressal
**Chain:** Civic Issue Docket → Original Public Record → Department Response → Status Claim vs. Resolution Evidence

- **Analytical Goal**: Investigates localized citizen grievances, municipal response times, and the empirical validity of "resolved" status claims.
- **Records Evaluated**:
  - `CIVIC_ISSUE` (Phase 7): Docket ID, ward, reported date, issue category.
  - `GOVERNMENT_DEPARTMENT` (Phase 3): Nodal executing agency (e.g. CMWSSB, MAWS, GCC).
  - `RESPONSE_RECORD` (Phase 7): Official Action Taken Report (ATR) reply letter.
  - `RESOLUTION_EVIDENCE` (Phase 7): Geo-tagged photos, citizen verification, water meter telemetry.
- **Epistemic Guardrail**:
  > *An administrative status of 'marked_resolved' represents an official department assertion, which is strictly distinguished from 'independently_verified_resolved' corroborated by empirical proof.*
- **Gaps Detected**: Departmental closure marked without citizen sign-off; stop-gap temporary relief (water tankers) substituted for permanent distribution line repairs.

---

### WORKFLOW C: Public Claim Dialectics & Fact Verification
**Chain:** Public Claim → Supporting Citations → Contradicting Documents → Contextual Nuance

- **Analytical Goal**: Rigorously evaluates public claims made by state officials or political leaders by contrasting statutory findings against press statements.
- **Records Evaluated**:
  - `PUBLIC_CLAIM` (Phase 8): Speaker, statement date, forum, verbatim claim text.
  - `SOURCE_DOCUMENT` (Phases 1–8): Government orders, statutory CAG reports, RTI returns.
  - `CIVIC_CONFLICT_RECORD` (Phase 9.6): Persistent dialectical tensions and weight comparisons.
- **Epistemic Guardrail**:
  > *Contradictory evidence is preserved side-by-side. Statutory constitutional audit findings (e.g. CAG Report No. 4 of 2023) carry higher epistemic weight than non-statutory ministerial press conference remarks, but neither is silently erased.*
- **Gaps Detected**: Claims backed only by self-reporting contractors; missing continuous SCADA flow telemetry.

---

### WORKFLOW D: Representative Stewardship & Legislative Accountability
**Chain:** Representative → Constituency → Legislative Activity → Documented Public Works

- **Analytical Goal**: Audits an elected legislator's democratic tenure, assembly questions, and constituency development works without falling into false causal blame.
- **Records Evaluated**:
  - `REPRESENTATIVE` (Phase 6): Official name, term, political party alliance.
  - `CONSTITUENCY` (Phase 6): Delimitation boundaries, electorate, ward mapping.
  - `LEGISLATIVE_ACTIVITY` (Phase 6): Starred/unstarred assembly questions, debate speeches.
  - `PUBLIC_WORK` & `CIVIC_ISSUE` (Phases 7–8): Local engineering works, grievance counts.
- **Epistemic Guardrail**:
  > *Anti-Causality & Non-Defamation Rule: A representative's democratic tenure in an assembly constituency does NOT establish personal culpability or legal liability for municipal service disruptions or infrastructure delays.*
- **Gaps Detected**: Missing MLACDS (MLA Constituency Development Scheme) expenditure utilization certificates; lack of assembly questions addressing local civic hotspots.

---

### WORKFLOW E: Political Funding Disclosures & Supported Entities
**Chain:** Political Funding Record → Statutory ECI / SBI Source Document → Supported Entities

- **Analytical Goal**: Traces corporate and individual campaign contributions to statutory disclosure documents and supported entities.
- **Records Evaluated**:
  - `POLITICAL_PARTY` / `DONOR` (Phase 5): Contributor name, political party recipient.
  - `CONTRIBUTION` (Phase 5): Transaction amount, date, disclosure portal receipt.
  - `SOURCE_DOCUMENT` (Phase 5): Official Election Commission of India (ECI) Form 24A and State Bank of India disclosure filings.
- **Epistemic Guardrail**:
  > *Statutory Disclosure Rule: Statutory campaign contributions reflect mandatory transparency disclosures. They do NOT establish corrupt intent or unlawful quid-pro-quo without independent judicial or statutory findings.*
- **Gaps Detected**: Anonymous bearer instruments prior to Supreme Court disclosure verdict; missing contribution dates.

---

## 3. Auditable Investigation Report Schema

When exported via `GET /api/graph/investigate/report/export` or the UI download button, reports conform to the following privacy-sanitized schema:

```json
{
  "metadata": {
    "report_title": "CIVICLENS TN Auditable Investigation Report — WORKFLOW_A_PROMISE_DELIVERY",
    "generated_at_utc": "2026-10-12T15:45:00Z",
    "subject_identifier": "NODE:PROM:DMK_DESAL",
    "subject_label": "DMK Manifesto 2021 Item 114: Water Desalination",
    "data_governance": "DPDPA 2023 Compliant (Automated PII & Internal Path Sanitization)",
    "epistemic_standard": "CIVICLENS TN Dialectical Evidentiary Methodology"
  },
  "investigation_summary": {
    "workflow": "WORKFLOW_A_PROMISE_DELIVERY",
    "records_available": {
      "promise_node": { "node_id": "NODE:PROM:DMK_DESAL", "label": "DMK Manifesto Item 114" },
      "related_schemes": [ { "node_id": "NODE:SCHEME:DESAL_NEMMELI" } ],
      "budget_allocations": [ { "node_id": "NODE:BUDGET:DEMAND_34_CAPITAL" } ]
    },
    "missing_information": [
      "Audited final utilization certificate for FY 2023-24 not yet published in CAG state accounts."
    ],
    "unreviewed_candidate_links": [
      {
        "proposal_id": "PROP-CANDIDATE-001",
        "review_status": "PENDING_REVIEW",
        "confidence_score": 0.76
      }
    ],
    "official_reporting_vs_independent_verification": [
      {
        "edge_id": "EDGE:DEPT:SCHEME:001",
        "relationship_type": "implements",
        "evidence_nature": "OFFICIAL_ADMINISTRATIVE_REPORTING",
        "review_status": "VERIFIED"
      },
      {
        "edge_id": "EDGE:SCHEME:BUDGET:001",
        "relationship_type": "funds",
        "evidence_nature": "INDEPENDENT_VERIFICATION",
        "review_status": "VERIFIED"
      }
    ],
    "reviewer_audit_history": [
      {
        "record_type": "PROPOSAL_REVIEW_DECISION",
        "reviewed_by": "LEAD_REVIEWER_TN",
        "disposition": "CONFIRMED",
        "rationale": "Verified through official Gazette No. 42"
      }
    ],
    "unresolved_questions": [
      "Does the budget outlay Head of Account represent new dedicated capacity or recurring administrative overhead?",
      "Has an independent social audit verified that treated water reached targeted consumers?"
    ],
    "epistemic_guardrail": "Policy Association Rule: Funding a scheme does not prove promise completion without end-user verification."
  }
}
```

---

## 4. Privacy & Data Governance (DPDPA 2023)

- **Automated PII Scrubbing**: Citizen telephone numbers, personal emails, flat/door numbers, and petitioner names are filtered through `sanitize_pii`.
- **System Path Redaction**: Raw local disk paths (e.g. `E:\CIVCLENS\...`) are stripped by `sanitize_system_paths` into `[INTERNAL_PATH_REDACTED]`.
- **Credential Protection**: Database passwords, session cookies, and internal secret tokens are automatically replaced with `[REDACTED_CREDENTIAL]`.
