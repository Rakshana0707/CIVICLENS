# Phase 7.9 — Political Claim Verification Dashboard

## 1. Executive Overview

The **Political Claim Verification & Evidence Intelligence Dashboard** is the public accountability and investigative interface for Phase 7 of CIVICLENS TN. Built using Streamlit and conforming strictly to existing CIVICLENS TN design patterns, it surfaces evidence-grounded verifications of political assertions, policy claims, and economic statistics without subjective editorializing.

### Epistemic Integrity & Statutory Charter
1. **Strictly No Politician Truthfulness Scores or Leaderboards:** CIVICLENS TN prohibits aggregate politician honesty metrics, party scorecards, or competitive ranking tables.
2. **Neutral Evidentiary Wording:** All outcomes evaluate the *degree of evidentiary support in public records* (`supported_by_available_evidence`, `contradicted_by_available_evidence`, `partially_supported`, `missing_important_context`, `insufficient_evidence`, `disputed_evidence`, `unverifiable`, `pending_review`). They never pass judgment on personal intent, character, or morality.
3. **Prominent Conflicting Evidence:** Opposing and contradictory records are prominently displayed in high-contrast callouts rather than hidden behind a single outcome tag.
4. **Transparent Automated vs. Human Distinction:** Algorithmic extractions are clearly labelled as `Automated Initial Assessment` until verified and sealed by credentialed human fact-checkers (`Confirmed by Human Fact-Checker` or `Peer Reviewed`).
5. **Absence of Proof is Not Proof of Falsehood:** Delayed or un-gazetted records result in `insufficient_evidence` or `pending_review`, never `contradicted`.

---

## 2. Nine Dedicated Dashboard Views

The dashboard organizes complex claim-evidence interactions across 9 specialized tabs:

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│               CIVICLENS TN — POLITICAL CLAIM VERIFICATION DASHBOARD                    │
├─────────────┬─────────────┬─────────────┬─────────────┬─────────────┬──────────────────┤
│ 1. Explorer │ 2. Detail   │ 3. Evidence │ 4. Support  │ 5. Conflict │ 6. Context       │
├─────────────┼─────────────┼─────────────┼─────────────┼─────────────┼──────────────────┤
│ 7. History  │ 8. Review   │ 9. Provenance                                              │
└─────────────┴─────────────┴─────────────┴─────────────┴─────────────┴──────────────────┘
```

### Tab 1: Claim Explorer
- **Multi-Parametric Filter Panel:**
  - **Category:** `ECONOMIC_METRICS`, `GOVERNMENT_SCHEMES`, `INFRASTRUCTURE`, `POLITICAL_PROMISES`, `STATISTICAL_CLAIMS`, `LEGISLATIVE_RECORDS`, `PUBLIC_HEALTH`, `ELECTION_LAW`.
  - **Outcome:** All 8 standardized evidentiary outcomes.
  - **Audit Status:** `UNREVIEWED`, `AUTOMATED_INITIAL`, `PEER_REVIEWED`, `CONFIRMED`, `REVISED`, `pending_review`.
  - **Language:** Tamil (`ta`), English (`en`), Mixed bilingual.
  - **Political Affiliation:** `DMK`, `AIADMK`, `TVK`, `BJP`, `INC`, `Independent`.
  - **Speaker / Keyword Query:** Full-text fuzzy search across claim IDs, speaker names, and verbatim texts.
- **Card-Based Inspection Grid:** Highlights claim text, speaker, party, category, outcome badge, and quick-navigation links to detailed dossiers.

### Tab 2: Claim Detail (Strict 8-Stage Evidentiary Flow)
The detail view strictly enforces the required sequence of transparent inquiry:
1. **📌 ORIGINAL CLAIM:** Verbatim preservation of statement, attribution type, candidate channel, and timestamp.
2. **🔬 ATOMIC CLAIMS:** Granular decomposition into subject, predicate, object, quantitative values, units, and temporal horizons.
3. **🟢 SUPPORTING EVIDENCE:** Gazetted documents, policy notes, and statistical bulletins corroborating the assertion.
4. **🔴 CONTRADICTING EVIDENCE:** Prominently exposed opposing records, divergent figures, or contradicted baselines.
5. **ℹ️ CONTEXT & NUANCE:** Omitted variables, differing definitions (e.g. gross vs net admissions, MoUs vs actual capital expenditure).
6. **⚖️ VERIFICATION OUTCOME:** Plain-language outcome explanation, algorithm confidence, and human review certification.
7. **🛡️ METHODOLOGY & LIMITATIONS:** Epistemic uncertainty, sample limitations, and non-ranking disclaimers.
8. **📄 SOURCE DOCUMENTS & CROSS-PHASE LINKS:** Direct link to original source, file SHA-256 hash, and bidirectional foreign key links to Phase 2 (Schemes), Phase 3 (Promises), Phase 4 (News), Phase 5 (Funding), and Phase 6 (Representatives/Constituencies).

### Tab 3: Evidence Viewer
- Central repository of acquired evidence documents with document ID, publisher, date, open access status, and content checksums (SHA-256).
- Search and filter passages by publisher and source category (`GOVERNMENT_PORTAL`, `LEGISLATIVE_RECORD`, `STATISTICAL_BUREAU`, etc.).

### Tab 4: Supporting Evidence View
- Focused analysis of all corroborated statements across registered claims.
- Compares speaker assertions against gazetted audit logs and department policy notes.

### Tab 5: Contradicting Evidence View
- Prominently isolates all discrepancies where official gazettes contradict political claims.
- Displays side-by-side comparisons of claimed values vs. officially audited numbers.

### Tab 6: Context and Limitations View
- Methodological breakdown of common public communications pitfalls:
  - *Gross vs. Net Changes:* E.g. gross application counts vs net verified additions.
  - *Nominal vs. Real Values:* Distortions caused by ignoring inflation over multi-year periods.
  - *Pipeline Commitments vs. Realized Outlays:* Memoranda of Understanding (MoUs) spanning multi-year horizons mistaken for annual realized expenditures.
  - *Absence of Proof vs. Proof of Absence:* Preventing premature false verdicts.

### Tab 7: Verification History (Audit Trail)
- Immutable chronological audit trail recording ingestion, decomposition, automated initial model runs, reviewer overrides, and determination timestamps.

### Tab 8: Human Review Queue
- Interactive review workspace for fact-checkers and editors.
- Role-governed review controls (`SENIOR_FACT_CHECKER`, `LEAD_REVIEWER`, `DOMAIN_EXPERT`, `AUDITOR`).
- Supported actions: `accept_assessment`, `revise_outcome`, `correct_decomposition`, `add_evidence`, `mark_evidence_irrelevant`.
- Reviewer credential logging and justification note recording.

### Tab 9: Source Provenance View
- End-to-end provenance graph linking claims to origin records.
- Verifies copyright fair-dealing compliance (< 300 words excerpt cap) and non-circumvention policies.

---

## 3. Verified Test Fixtures

Until production ingestion of all 2024-2026 Tamil Nadu gazetted datasets is finalized, the dashboard incorporates 9 comprehensive, bilingual test fixtures covering every outcome state:

| Fixture ID | Category | Language | Speaker | Outcome | Review Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `TEST_FIXTURE_CLM_01` | Economic Metrics | Tamil | Finance Minister | `supported_by_available_evidence` | `CONFIRMED` |
| `TEST_FIXTURE_CLM_02` | Govt Schemes | English | Opposition Spokesperson | `contradicted_by_available_evidence` | `PEER_REVIEWED` |
| `TEST_FIXTURE_CLM_03` | Govt Schemes | Tamil | Chief Minister | `supported_by_available_evidence` | `CONFIRMED` |
| `TEST_FIXTURE_CLM_04` | Infrastructure | English | Infrastructure Spokesperson | `partially_supported` | `AUTOMATED_INITIAL` |
| `TEST_FIXTURE_CLM_05` | Economic Metrics | English | Industries Representative | `missing_important_context` | `PEER_REVIEWED` |
| `TEST_FIXTURE_CLM_06` | Statistical Claims | English | Policy Critic | `disputed_evidence` | `PEER_REVIEWED` |
| `TEST_FIXTURE_CLM_07` | Political Promises | English | Campaign Spokesperson | `unverifiable` | `AUTOMATED_INITIAL` |
| `TEST_FIXTURE_CLM_08` | Infrastructure | English | Energy Representative | `insufficient_evidence` | `pending_review` |
| `TEST_FIXTURE_CLM_09` | Public Health | English | Water Supply Representative | `pending_review` | `pending_review` |

---

## 4. API Client Integration ([`frontend/services/api.py`](file:///e:/CIVCLENS/frontend/services/api.py))

The frontend consumes backend REST endpoints with automatic test-fixture fallbacks:
- `search_claims(filters, skip, limit)` $\rightarrow$ `GET /api/claims/search`
- `get_claim_detail(claim_id)` $\rightarrow$ `GET /api/claims/<claim_id>`
- `get_atomic_claim_detail(claim_id, atomic_id)` $\rightarrow$ `GET /api/claims/<claim_id>/atomic/<atomic_id>`
- `search_evidence(q, doc_type, category, skip, limit)` $\rightarrow$ `GET /api/claims/evidence/search`
- `get_evidence_document(document_id)` $\rightarrow$ `GET /api/claims/evidence/documents/<document_id>`
- `get_claim_relationships(claim_id)` $\rightarrow$ `GET /api/claims/<claim_id>/relationships`
- `get_claim_verification(claim_id)` $\rightarrow$ `GET /api/claims/<claim_id>/verification`
- `get_claim_history(claim_id)` $\rightarrow$ `GET /api/claims/<claim_id>/history`
- `submit_claim_review(claim_id, payload, role)` $\rightarrow$ `POST /api/claims/<claim_id>/review`
- `get_claim_source(source_id)` $\rightarrow$ `GET /api/claims/sources/<source_id>`
- `get_claim_provenance(claim_id)` $\rightarrow$ `GET /api/claims/<claim_id>/provenance`
- `get_claim_cross_phase(claim_id)` $\rightarrow$ `GET /api/claims/<claim_id>/cross-phase`

---

## 5. Test Suite Verification

Comprehensive unit and integration test suites:
- `tests/unit/test_phase7_dashboard_frontend.py`: 10 passed.
- Full Phase 7 regression test suite (Phase 7.1 to 7.9): **98 tests passed** with zero regressions.
