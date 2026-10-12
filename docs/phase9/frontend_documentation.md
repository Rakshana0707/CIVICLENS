# Phase 9.8 — Unified Civic Intelligence Evidence Graph Explorer Frontend

## 1. Architectural & Epistemic Principles

The **Evidence Graph Explorer** (`frontend/pages/9_Evidence_Graph_Explorer.py`) is the unified visual interface connecting records across all 8 foundational analytical modules of **CIVICLENS TN**.

### Core Epistemic Safeguards
1. **Association is Not Causation**:
   - Visual layouts avoid directional blame arrows or deceptive layouts that imply causation.
   - For example, an edge showing that a government department `implements` a desalination scheme does not establish that the scheme was successfully completed; an edge showing that a civic grievance is `located_in` an assembly constituency does not establish the individual elected legislator's legal or administrative fault.
2. **Strict Candidate Separation**:
   - Unreviewed algorithmic proposals discovered by the Phase 9.4 engine are rendered with **dashed amber lines** and explicit warnings:
     > *"Candidate links are proposed by algorithmic heuristics and are NOT established facts until verified by human domain auditors."*
3. **Dialectical Tension Preservation**:
   - Rather than erasing or overwriting contradictory records, opposing documents (e.g. Comptroller and Auditor General statutory constitutional audit reports vs. departmental press conference announcements) are preserved side-by-side with explicit epistemic weights.
4. **Accessible Alternative Representations**:
   - Every graph visualization is paired with structured, accessible tables and expandable cards designed for screen readers and tabular data auditing.

---

## 2. Supported Entity Types (All 10 Categories)

| Entity Type | English Name | Tamil Name (தமிழ்) | Originating Phase | Target Dashboard Link |
| :--- | :--- | :--- | :--- | :--- |
| `SCHEME` | Scheme | அரசுத் திட்டம் | Phase 2 | `pages/1_Budget_&_Schemes.py` |
| `BUDGET_LINE_ITEM` | Budget Line Item | நிதிநிலை ஒதுக்கீடு | Phase 1 | `pages/1_Budget_&_Schemes.py` |
| `POLITICAL_PROMISE` | Political Promise | தேர்தல் வாக்குறுதி | Phase 1 | `pages/2_Political_Promises.py` |
| `POLITICAL_PARTY` | Political Party | அரசியல் கட்சி | Phase 5 | `pages/5_Political_Funding.py` |
| `REPRESENTATIVE` | Representative | மக்கள் பிரதிநிதி | Phase 6 | `pages/4_Representatives.py` |
| `CONSTITUENCY` | Constituency | சட்டமன்றத் தொகுதி | Phase 6 | `pages/4_Representatives.py` |
| `PUBLIC_CLAIM` | Public Claim | பொதுக் கூற்று | Phase 8 | `pages/6_Claim_Verification.py` |
| `CIVIC_ISSUE` | Civic Issue | குடிமைப் பிரச்சினை | Phase 7 | `pages/8_Civic_Issue_Intelligence.py` |
| `GOVERNMENT_DEPARTMENT` | Department | அரசுத் துறை | Phase 3 | `pages/8_Civic_Issue_Intelligence.py` |
| `SOURCE_DOCUMENT` | Source Document | சான்று ஆவணம் | Phases 1–8 | Primary Gazette / Report Inspector |

---

## 3. Explicit Relationship Vocabulary & Governance Meanings

The graph supports strictly documented relationship types with plain-language civic accountability definitions:

- **`funds`**: Authorizes statutory financial outlay or grants budget capital without guaranteeing physical completion or individual benefit.
- **`implements`**: Nodal department or executing board administratively sanctions and executes the project or scheme.
- **`promises`**: Political party election manifesto officially pledges policy delivery or project realization.
- **`relates_to`**: Documented institutional, organizational, or statutory affiliation connects both entities.
- **`reports_on`**: Journalistic or administrative document provides monitored coverage regarding the subject entity.
- **`mentions`**: Primary document text directly references or cites the entity identifier.
- **`concerns`**: Grievance, petition, or inquiry substantively concerns the domain of the target entity.
- **`represents`**: Representative holds constitutional democratic mandate to represent voters of the constituency.
- **`responds_to`**: Official action-taken report, reply letter, or repair order responds to the grievance docket.
- **`provides_evidence_for`**: Statutory audit, gazette order, or field measurement provides documentary corroboration supporting the claim.
- **`contradicts`**: Verified empirical audit, field measurement, or statutory finding directly contradicts the claim.
- **`contextualizes`**: Supplies background geographic, demographic, or legal framework explaining the context.
- **`located_in`**: Physical or civic event took place within the territorial boundary of the administrative unit.
- **`derived_from`**: Data entity was computed, extracted, or synthesized from the primary source document.

---

## 4. UI Layout & Component Hierarchy

### A. Sidebar Controls
- **Keyword Search**: Multilingual search matching English labels, Tamil titles, canonical IDs, and node identifiers.
- **Entity Type Selector**: Filter graph to specific entity categories or view all.
- **Source Phase Filter**: Slice records by originating analytical phase (`phase1` through `phase8`).
- **Visualization Mode**:
  1. *Interactive Network Graph (Plotly)*: 2D zoomable network with custom node styling, hover cards, and edge markers.
  2. *Structural Diagram (Graphviz)*: Hierarchical SVG graph for topological overview.
  3. *Accessible Tabular & List View*: High-contrast dataframes and card lists for screen reader accessibility.
- **Investigation Walk Selector**: Direct jump to pre-configured accountability walk templates.

### B. Tabbed Investigation Workspace
1. **🕸️ Graph Explorer & Edge Inspector**:
   - Filter by relationship type, review status (`VERIFIED`, `PENDING_REVIEW`, `REJECTED`), and provenance lifecycle (`VALID`, `DISPUTED`, `SUPERSEDED`).
   - Node Focus Selector: Focuses view onto a specific entity and isolates its direct network neighborhood.
   - **Edge Inspector Modal**:
     - *Meaning*: What the relationship means in civic accountability terms.
     - *Record Connection*: Clear card linking Source Record ➜ Target Record.
     - *Supporting Evidence*: Primary citations, document IDs, URLs, and cryptographic SHA-256 hashes.
     - *Epistemic Limits*: Plain-language explanation of what remains uncertain and data caveats.
2. **🔍 Entity Directory & Detail**:
   - Full canonical entity profiles with Tamil transliterations.
   - Cross-Phase Navigation pill button to jump directly to dedicated phase dashboards (`st.page_link`).
   - Stored record properties and table of all direct network neighbors.
3. **🛤️ Evidence-Path Walks**:
   - Step-by-step traversal along canonical accountability chains:
     - **Path 1**: Political Promise → Relevant Scheme → Budget Document → Resolution.
     - **Path 2**: Public Claim → Supporting & Contradicting Evidence → Verification.
     - **Path 3**: Civic Issue → Official Record → Department Response → Resolution.
     - **Path 4**: Representative → Constituency → Documented Works.
     - **Path 5**: Political Funding Disclosure → Disclosed Entity → Source Document.
   - Metric displays for Path Completeness % and Direct vs. Inferred status.
4. **⚖️ Contradictions & Candidate Links**:
   - Persistent conflict records with severity ratings and dialectical comparisons (statutory authority vs media statements).
   - Unreviewed candidate proposals banner and cards with confidence scores and risk warnings.
5. **📄 Source Documents & Lineage**:
   - Inspection of primary source gazettes, CAG audit reports, government orders, and election commission returns.
   - Display of issuing authority, publication dates, and verifiable SHA-256 hashes.

---

## 5. Offline Fallback & Fault Tolerance

The frontend implements an **API-First with Seamless Fixture Fallback** pattern:
- When connected to the live backend REST API, real-time database graph nodes, edges, proposals, and conflict records are loaded.
- If the backend is temporarily unreachable or returning empty query results, the UI gracefully falls back to rich, verified Phase 9 test fixtures (`frontend/pages/nine_graph_fixtures.py`) without throwing uncaught exceptions or blank screens.
- Current status is clearly indicated via a status badge in the sidebar (`🟢 Live Backend API` vs `🟡 Offline (Rich Fixture Mode)`).

---

## 6. Verification & Automated Testing

The frontend is verified via `tests/unit/test_phase9_frontend.py` covering:
1. `APIClient` methods for all Phase 9 endpoints.
2. AST compilation and syntax integrity of Streamlit source files.
3. Coverage of all 10 civic entity domains.
4. Completeness of relationship definitions and non-causality notes.
5. Plotly and Graphviz diagram generation.
6. Accessible tabular DataFrame construction.
7. Preservation of contradictory evidence and statutory weight rules.
8. Candidate proposal separation and warning flags.
9. 5 canonical multi-hop investigation paths.
