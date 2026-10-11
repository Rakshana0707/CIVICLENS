# CIVICLENS TN — Phase 7.8: Claim Verification Database, API and Cross-Phase Integration

## 1. Executive Summary and Architecture

Phase 7.8 connects the Political Claim Verification & Evidence Intelligence module with the core CIVICLENS TN backend database and modular API routers. By integrating across all preceding phases (Phase 2 Schemes, Phase 3 Promises, Phase 4 News, Phase 5 Funding, Phase 6 Representatives), the verification system grounds claims in empirical, statutory, and journalistic records without data duplication.

```
+--------------------------------------------------------------------------------------------------+
|                                    CIVICLENS TN BACKEND                                          |
+--------------------------------------------------------------------------------------------------+
|   PHASE 2: Historical Schemes & Budget Line Items (historical_schemes, budget_schemes)           |
|   PHASE 3: Political Manifesto Promises (political_promises, promise_assessments)                 |
|   PHASE 4: News Articles & Editorial Media (news_articles, news_sources)                         |
|   PHASE 5: Political Funding & Disclosures (financial_documents, contributions)                  |
|   PHASE 6: Representatives & Constituencies (representatives, constituencies)                    |
+--------------------------------------------------------------------------------------------------+
                                                ^
                                                | Stable Foreign Keys & ClaimCrossPhaseLink
                                                v
+--------------------------------------------------------------------------------------------------+
|                              PHASE 7: CLAIM VERIFICATION MODULE                                   |
+--------------------------------------------------------------------------------------------------+
|  Claim <-> ClaimVersion <-> AtomicClaim <-> ClaimSource <-> ClaimRetrievalCandidate              |
|        <-> ClaimEvidenceRelationship <-> EvidenceDocument <-> EvidencePassage                    |
|        <-> VerificationRun <-> VerificationResult <-> VerificationHistory <-> ReviewRecord       |
+--------------------------------------------------------------------------------------------------+
```

### Core Epistemic Safeguards
1. **Lightweight Identifiers Instead of Data Duplication**: Records from earlier phases are referenced strictly via stable primary keys (`historical_scheme_id`, `promise_id`, `news_article_id`, `financial_document_id`, `representative_id`, `constituency_id`), avoiding duplicate copies and synchronization drift.
2. **Selective Associations**: The engine never assumes every claim relates to a promise, funding report, or representative. Nullable linkages gracefully accommodate public statements without cross-module ties.
3. **Mandatory Epistemic Disclaimers**: Every verification API response exposes its supporting and contradicting evidence IDs, methodology specification, and structural limitations.
4. **Permanent Audit Preservation**: Baseline automated results are preserved alongside human review modifications.

---

## 2. Database Schema and Entity Relationships

### 2.1 Core Entities

| Table | Entity | Description |
|---|---|---|
| `political_claims` | `Claim` | Immutable original utterance, metadata, review status, and direct foreign keys. |
| `claim_versions` | `ClaimVersion` | Audit trail for transcript revisions, corrections, and translations. |
| `atomic_claims` | `AtomicClaim` | Decomposed verifiable propositions with SPO semantic frames and quantitative metrics. |
| `claim_sources` | `ClaimSource` | Intake provenance capturing speech rallies, press conferences, manifestos, and checksums. |
| `evidence_documents` | `EvidenceDocument` | Canonical statutory documents, gazettes, budget books, and fact-check reports. |
| `evidence_passages` | `EvidencePassage` | Granular excerpts, tables, or speech sections providing factual citations. |
| `claim_evidence_relationships` | `ClaimEvidenceRelationship` | Stance classification (`supports`, `contradicts`, `partially_supports`, etc.) and alignment checks. |
| `verification_runs` | `VerificationRun` | Execution trace recording pipeline version and model parameters. |
| `verification_results` | `VerificationResult` | Synthesized verification assessment with 8 standardized outcome labels and diversity metrics. |
| `verification_history` | `VerificationHistory` | Immutable transition log recording verdict and outcome changes over time. |
| `review_records` | `ReviewRecord` | Human-in-the-loop expert analyst validations and workflow modifications. |
| `claim_cross_phase_links` | `ClaimCrossPhaseLink` | Multi-way junction entity linking claims to Phase 2-6 entities with relationship natures. |

### 2.2 Cross-Phase Foreign Keys & Junction Model

```python
# Direct nullable foreign keys on Claim
promise_id = Column(String, ForeignKey("political_promises.promise_id", ondelete="SET NULL"), nullable=True)
historical_scheme_id = Column(Integer, ForeignKey("historical_schemes.id", ondelete="SET NULL"), nullable=True)
news_article_id = Column(String, ForeignKey("news_articles.article_id", ondelete="SET NULL"), nullable=True)
financial_document_id = Column(String, ForeignKey("financial_documents.document_id", ondelete="SET NULL"), nullable=True)
representative_id = Column(String, ForeignKey("representatives.representative_id", ondelete="SET NULL"), nullable=True)
constituency_id = Column(String, ForeignKey("constituencies.constituency_id", ondelete="SET NULL"), nullable=True)

# Explicit Junction Table: ClaimCrossPhaseLink
class ClaimCrossPhaseLink(Base):
    __tablename__ = "claim_cross_phase_links"
    link_id = Column(String, primary_key=True)
    claim_id = Column(String, ForeignKey("political_claims.claim_id", ondelete="CASCADE"), nullable=False)
    atomic_claim_id = Column(String, ForeignKey("atomic_claims.atomic_claim_id", ondelete="CASCADE"), nullable=True)
    target_phase = Column(String, nullable=False)  # PHASE_2_SCHEME, PHASE_3_PROMISE, PHASE_4_NEWS, etc.
    entity_type = Column(String, nullable=False)   # HISTORICAL_SCHEME, POLITICAL_PROMISE, ARTICLE, etc.
    entity_id = Column(String, nullable=False)     # Stable primary key in target module
    relationship_nature = Column(String, nullable=True) # evaluates_promise, grounded_in_scheme, etc.
    relevance_score = Column(Float, default=1.0)
```

---

## 3. REST API Specification

### 3.1 Claim Search and Retrieval

#### `GET /api/claims/` or `GET /api/claims/search`
Retrieves paginated claims with comprehensive multi-criteria filtering.
- **Parameters**:
  - `q`: Free-text search matching verbatim or normalized claim text.
  - `category`: Filter by `ClaimCategory`.
  - `status`: Filter by `ClaimStatus`.
  - `outcome`: Filter by `VerificationOutcome`.
  - `party`: Speaker's political party.
  - `speaker`: Speaker name (substring).
  - `language`: `ta`, `en`, `bilingual`.
  - `representative_id`: Filter by linked representative.
  - `promise_id`: Filter by linked political promise.
  - `scheme_id`: Filter by linked historical scheme.
  - `skip`: Pagination offset (default: 0).
  - `limit`: Pagination limit (default: 50, max: 100).
- **Response**:
  ```json
  {
    "status": "success",
    "data": {
      "total": 42,
      "skip": 0,
      "limit": 20,
      "claims": [
        {
          "claim_id": "CLM-2024-001",
          "original_text": "Tamil Nadu established 1,000 new primary health centres in 2023.",
          "language": "en",
          "claim_category": "HEALTHCARE_EDUCATION",
          "speaker_name": "Health Minister",
          "speaker_party": "DMK",
          "claim_date": "2024-02-15T00:00:00Z",
          "status": "VERIFIED",
          "verdict": "PARTIALLY_SUPPORTED",
          "confidence_score": 0.85,
          "cross_phase_identifiers": {
            "representative_id": "REP-TN-MLA-042",
            "promise_id": "PRM-2021-DMK-112",
            "historical_scheme_id": null
          },
          "verification": {
            "outcome": "partially_supported",
            "explanation": "Part 1 ['1,000 new PHCs']: PARTIALLY_SUPPORTED. Sanctions issued for 1,000; 480 operationalized.",
            "supporting_evidence_ids": ["CER-01"],
            "contradicting_evidence_ids": [],
            "methodology": "Methodology METHODOLOGY_V1: Multi-signal hybrid retrieval...",
            "limitations": "Evidence assessment reflects available empirical records..."
          }
        }
      ]
    }
  }
  ```

#### `GET /api/claims/<claim_id>`
Fetches the full claim profile, decomposed atomic propositions, versions, evidence relationships, verification result, review records, and resolved cross-phase entities.

#### `GET /api/claims/<claim_id>/atomic/<atomic_claim_id>` or `GET /api/claims/atomic/<atomic_claim_id>`
Retrieves atomic proposition detail including structured SPO frame, quantitative constraints, candidate retrievals, and atomic evidence relationships.

---

### 3.2 Evidence Acquisition and Provenance

#### `GET /api/claims/evidence` or `GET /api/claims/evidence/search`
Searches ingested statutory and media evidence documents and passages.
- **Parameters**: `q`, `document_type`, `source_category`, `source_tier`, `publisher`, `language`, `skip`, `limit`.

#### `GET /api/claims/evidence/documents/<document_id>`
Returns full document metadata, granular text passages, file checksums, and list of claims citing this document.

#### `GET /api/claims/<claim_id>/relationships`
Returns established stance classifications for candidate evidence passages. Retains supporting, contextualizing, and contradicting evidence without suppression.

#### `GET /api/claims/sources/<source_id>`
Exposes intake provenance for a press conference, legislative session, or manifesto document, including collection method, checksum, and all associated claims.

#### `GET /api/claims/<claim_id>/provenance`
Exposes the specific intake provenance, attribution taxonomy, content fingerprint, and version history of an individual claim.

---

### 3.3 Verification and Audit Trails

#### `GET /api/claims/<claim_id>/verification`
Fetches current synthesized verification result, multi-part explanation breakdown, source diversity breakdown, automated baseline preservation, and review status.

#### `GET /api/claims/<claim_id>/history` (Alias: `GET /api/claims/<claim_id>/audit-trail`)
Returns the complete audit log: verification history transitions, execution runs, review records, and text version histories.

#### `POST /api/claims/<claim_id>/review`
Executes human-in-the-loop review actions with strict role-based access control.
- **Authorized Roles**: `LEAD_REVIEWER`, `SENIOR_FACT_CHECKER`, `DOMAIN_EXPERT`, `AUDITOR`, `RESEARCHER`, `ADMIN`.
- **Supported Actions**:
  - `accept_assessment`
  - `correct_claim_decomposition`
  - `add_evidence`
  - `mark_evidence_irrelevant`
  - `revise_outcome`
- **Security Check**: Returns `403 Forbidden` if an unauthorized or non-analyst role is supplied.

---

### 3.4 Cross-Phase Integration Endpoints

#### `POST /api/claims/<claim_id>/cross-phase/link`
Links a claim or atomic proposition to an existing record from Phases 2-6.
- **Payload**:
  ```json
  {
    "target_phase": "PHASE_3_PROMISE",
    "entity_type": "POLITICAL_PROMISE",
    "entity_id": "PRM-2021-DMK-042",
    "relationship_nature": "evaluates_promise_implementation",
    "relevance_score": 0.95
  }
  ```
- **Validation**: Verifies existence of the target record in the corresponding table before creating the junction link.

#### `GET /api/claims/<claim_id>/cross-phase`
Returns all cross-phase links with resolved target entity names and attributes.

#### `GET /api/claims/by-representative/<representative_id>`
Lists all political claims voiced by or attributed to a specific representative.

#### `GET /api/claims/by-promise/<promise_id>`
Lists all claims evaluating or addressing a specific manifesto promise.

#### `GET /api/claims/by-scheme/<scheme_id>`
Lists all claims assessing budget allocation or ground delivery of a specific government scheme.

---

## 4. Verification and Security Validation

| Test Target | Validation Mechanism | Expected Result |
|---|---|---|
| Cross-Phase FK Resolution | Database query with joined models | Returns resolved entity attributes without duplicating tables. |
| Access Control | `POST /review` with `PUBLIC_USER` | `403 Forbidden` with role requirement error. |
| Pagination Governance | Negative `skip` or `limit > 100` | `400 Bad Request` validation response. |
| Outcome Integrity | Query verification response | Exposes supporting IDs, contradicting IDs, methodology, and limitations. |
| Non-Ranking Rule | `/claims/stats` | Enforces zero politician/party honesty leaderboards. |
