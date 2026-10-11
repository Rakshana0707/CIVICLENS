"""
Phase 7 — Unit Tests for Political Claim Verification & Evidence Intelligence Architecture.

Tests:
1. Canonical claim registration and immutable verbatim original text preservation.
2. Multi-version claim tracking (ClaimVersion) ensuring original text is never overwritten.
3. Atomic claim decomposition into subjects, schemes, and entities (ClaimSubject).
4. Objective source quality assessment using the 4-dimension scoring rubric (SourceAssessment).
5. Evidence linking and bidirectional relationship classification (ClaimEvidenceRelationship).
6. Automated verification run execution, verdict generation, and history logging (VerificationResult).
7. Contradiction analysis and statutory budget refutation (CONTRADICTED verdict).
8. Uncertainty exposure and limitation reporting for missing records (UNVERIFIABLE_INSUFFICIENT_EVIDENCE).
9. Contextual omission detection and nuance analysis (MISLEADING_CONTEXT).
10. Human-in-the-loop review workflow, override auditing, and history tracking (ReviewRecord).
11. Anti-ranking rule verification (strictly no politician or party truthfulness scorecards).
12. REST API endpoints verification (/api/claims/, /api/claims/<id>, /api/claims/stats).
"""

import pytest
from datetime import datetime, timezone
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.database.base_class import Base
from backend.models.claim import (
    Claim,
    ClaimVersion,
    ClaimSubject,
    ClaimSource,
    EvidenceDocument,
    EvidencePassage,
    ClaimEvidenceRelationship,
    VerificationRun,
    VerificationResult,
    VerificationHistory,
    SourceAssessment,
    ReviewRecord,
    ClaimCategory,
    ClaimStatus,
    SourceTier,
    EvidenceRelationshipType,
    VerificationVerdict,
    ReviewStatus,
    SubjectType
)
from backend.services.claim_verification import ClaimVerificationService
from backend.api.app import create_app
from tests.fixtures.phase7_fixtures import (
    MOCK_CLAIMS,
    MOCK_EVIDENCE_DOCS,
    MOCK_REVIEWS
)


@pytest.fixture
def db_session():
    """Isolated in-memory SQLite database session for unit testing."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    yield session

    session.close()


@pytest.fixture
def api_client(db_session):
    """Flask test client configured with database tables."""
    from backend.database.session import engine as app_engine
    for table in reversed(Base.metadata.sorted_tables):
        if table.name.startswith(("political_claims", "claim_", "verification_", "evidence_", "review_")):
            table.drop(bind=app_engine, checkfirst=True)
    Base.metadata.create_all(bind=app_engine)
    app = create_app()
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


# ---------------------------------------------------------------------------
# Test 1: Verbatim Original Text Preservation
# ---------------------------------------------------------------------------
def test_1_register_claim_verbatim_preservation(db_session):
    service = ClaimVerificationService(db=db_session)

    mock = MOCK_CLAIMS[0]
    claim = service.register_claim(
        claim_id=mock["claim_id"],
        original_text=mock["original_text"],
        claim_category=ClaimCategory(mock["claim_category"]),
        speaker_name=mock["speaker_name"],
        speaker_party=mock["speaker_party"],
        context_text=mock["context_text"],
        language=mock["language"],
        temporal_scope=mock["temporal_scope"],
        geographic_scope=mock["geographic_scope"],
        is_test_fixture=True
    )

    assert claim.claim_id == "CLM-FIX-001-SCHEME"
    assert claim.original_text == mock["original_text"]
    assert claim.status == ClaimStatus.PENDING
    assert claim.language == "ta"

    # Verify Version 1 is automatically initialized
    versions = db_session.query(ClaimVersion).filter(ClaimVersion.claim_id == claim.claim_id).all()
    assert len(versions) == 1
    assert versions[0].version_number == 1
    assert versions[0].edited_text == mock["original_text"]
    assert "Initial registration" in versions[0].change_rationale


# ---------------------------------------------------------------------------
# Test 2: Multi-Version Claim Tracking Without Overwriting Original
# ---------------------------------------------------------------------------
def test_2_claim_versioning_audit_trail(db_session):
    service = ClaimVerificationService(db=db_session)
    mock = MOCK_CLAIMS[0]
    claim = service.register_claim(
        claim_id=mock["claim_id"],
        original_text=mock["original_text"],
        claim_category=ClaimCategory(mock["claim_category"]),
        is_test_fixture=True
    )

    # Add Version 2 (English transliteration and standard spelling)
    v2 = service.add_claim_version(
        claim_id=claim.claim_id,
        edited_text="Kalaignar Magalir Urimai Thittam provides ₹1,000/month to 1.15 crore women.",
        transliterated_text="Kalaignar magalir urimai thittathin keezh 1.15 kodi magalirukku maadham 1000 valangappattu varugiradhu.",
        change_rationale="Added standard English transliteration and translation for bilingual verification.",
        edited_by="analyst_transcription"
    )

    assert v2.version_number == 2
    assert "Kalaignar Magalir Urimai Thittam" in v2.edited_text

    # CRITICAL: Verify original_text in root Claim is COMPLETELY UNTOUCHED
    reloaded = db_session.query(Claim).filter(Claim.claim_id == claim.claim_id).first()
    assert reloaded.original_text == mock["original_text"]
    assert len(reloaded.versions) == 2


# ---------------------------------------------------------------------------
# Test 3: Claim Decomposition into Atomic Subjects
# ---------------------------------------------------------------------------
def test_3_claim_decomposition(db_session):
    service = ClaimVerificationService(db=db_session)
    mock = MOCK_CLAIMS[0]
    claim = service.register_claim(
        claim_id=mock["claim_id"],
        original_text=mock["original_text"],
        claim_category=ClaimCategory(mock["claim_category"]),
        is_test_fixture=True
    )

    subjects = service.decompose_claim(
        claim_id=claim.claim_id,
        subjects=mock["subjects"]
    )

    assert len(subjects) == 3
    assert claim.status == ClaimStatus.DECOMPOSED

    subj_types = [s.subject_type for s in subjects]
    assert SubjectType.POLITICIAN in subj_types
    assert SubjectType.SCHEME in subj_types
    assert SubjectType.GOVERNMENT_DEPARTMENT in subj_types


# ---------------------------------------------------------------------------
# Test 4: Objective Source Quality Assessment Scoring Rubric
# ---------------------------------------------------------------------------
def test_4_source_quality_assessment_scoring(db_session):
    service = ClaimVerificationService(db=db_session)

    # Ingest Tier 1 Document
    tier1_doc = EvidenceDocument(
        document_id="EDOC-STATUTORY-01",
        source_tier=SourceTier.TIER_1_STATUTORY,
        source_name="Govt of Tamil Nadu Gazette",
        document_type="GOVERNMENT_ORDER",
        title="Official G.O. Ms. No. 37",
        file_hash_sha256="hash123456789",
        is_official=True
    )
    db_session.add(tier1_doc)

    # Ingest Tier 5 Document
    tier5_doc = EvidenceDocument(
        document_id="EDOC-BLOG-01",
        source_tier=SourceTier.TIER_5_UNVERIFIED,
        source_name="Anonymous Political Blog",
        document_type="BLOG_POST",
        title="Unverified Gossip Post",
        file_hash_sha256="hash987654321",
        is_official=False
    )
    db_session.add(tier5_doc)
    db_session.commit()

    # Assess Tier 1 Source: 0.35*1.0 + 0.25*1.0 + 0.20*1.0 + 0.20*1.0 = 1.00
    ass1 = service.assess_source_quality(
        document_id="EDOC-STATUTORY-01",
        primary_source_score=1.0,
        institutional_independence_score=1.0,
        verifiability_score=1.0
    )
    assert ass1.composite_quality_score == 1.0
    assert ass1.source_tier == SourceTier.TIER_1_STATUTORY

    # Assess Tier 5 Source: 0.35*0.2 + 0.25*0.3 + 0.20*0.2 + 0.20*0.3 = 0.07 + 0.075 + 0.04 + 0.06 = 0.245
    ass2 = service.assess_source_quality(
        document_id="EDOC-BLOG-01",
        primary_source_score=0.3,
        institutional_independence_score=0.2,
        verifiability_score=0.3
    )
    assert ass2.composite_quality_score < 0.35
    assert ass2.composite_quality_score < ass1.composite_quality_score


# ---------------------------------------------------------------------------
# Test 5: Evidence Linking and Bidirectional Signal Scoring
# ---------------------------------------------------------------------------
def test_5_evidence_linking_and_bidirectional_signals(db_session):
    service = ClaimVerificationService(db=db_session)
    mock_c = MOCK_CLAIMS[0]
    claim = service.register_claim(
        claim_id=mock_c["claim_id"],
        original_text=mock_c["original_text"],
        claim_category=ClaimCategory(mock_c["claim_category"]),
        is_test_fixture=True
    )

    doc_mock = MOCK_EVIDENCE_DOCS[0]
    doc = EvidenceDocument(
        document_id=doc_mock["document_id"],
        source_tier=SourceTier(doc_mock["source_tier"]),
        source_name=doc_mock["source_name"],
        document_type=doc_mock["document_type"],
        title=doc_mock["title"],
        file_hash_sha256=doc_mock["file_hash_sha256"],
        is_official=True
    )
    db_session.add(doc)

    pass_mock = doc_mock["passages"][0]
    passage = EvidencePassage(
        passage_id=pass_mock["passage_id"],
        document_id=doc.document_id,
        passage_text=pass_mock["passage_text"],
        page_number=pass_mock["page_number"],
        section_or_table=pass_mock["section_or_table"],
        numerical_values=pass_mock["numerical_values"]
    )
    db_session.add(passage)
    db_session.commit()

    rel = service.link_evidence(
        claim_id=claim.claim_id,
        passage_id=passage.passage_id,
        relationship_type=EvidenceRelationshipType.SUPPORTS,
        relevance_score=0.98,
        confidence_score=0.95,
        contradiction_score=0.02,
        reconciliation_notes="Direct statutory corroboration in G.O. Ms. No. 37 for 1.15 Cr beneficiaries and ₹1,000/mo."
    )

    assert rel.relationship_type == EvidenceRelationshipType.SUPPORTS
    assert rel.confidence_score == 0.95
    assert claim.status == ClaimStatus.EVIDENCE_LINKED


# ---------------------------------------------------------------------------
# Test 6: Automated Verification Run and SUPPORTED Verdict
# ---------------------------------------------------------------------------
def test_6_automated_verification_run_and_verdict(db_session):
    service = ClaimVerificationService(db=db_session)

    # 1. Register claim
    mock_c = MOCK_CLAIMS[0]
    claim = service.register_claim(
        claim_id=mock_c["claim_id"],
        original_text=mock_c["original_text"],
        claim_category=ClaimCategory(mock_c["claim_category"]),
        is_test_fixture=True
    )

    # 2. Add doc and passage
    doc_mock = MOCK_EVIDENCE_DOCS[0]
    doc = EvidenceDocument(
        document_id=doc_mock["document_id"],
        source_tier=SourceTier(doc_mock["source_tier"]),
        source_name=doc_mock["source_name"],
        document_type=doc_mock["document_type"],
        title=doc_mock["title"],
        file_hash_sha256=doc_mock["file_hash_sha256"]
    )
    db_session.add(doc)
    pass_mock = doc_mock["passages"][0]
    passage = EvidencePassage(
        passage_id=pass_mock["passage_id"],
        document_id=doc.document_id,
        passage_text=pass_mock["passage_text"]
    )
    db_session.add(passage)
    db_session.commit()

    # Assess source
    service.assess_source_quality(doc.document_id)

    # Link evidence
    service.link_evidence(
        claim_id=claim.claim_id,
        passage_id=passage.passage_id,
        relationship_type=EvidenceRelationshipType.SUPPORTS,
        confidence_score=0.96,
        contradiction_score=0.01
    )

    # Execute verification
    result = service.verify_claim(claim_id=claim.claim_id)

    assert result.verdict == VerificationVerdict.SUPPORTED
    assert result.confidence_score >= 0.70
    assert result.is_current is True
    assert claim.status == ClaimStatus.VERIFIED

    # Check VerificationHistory
    history = db_session.query(VerificationHistory).filter(VerificationHistory.claim_id == claim.claim_id).all()
    assert len(history) == 1
    assert history[0].new_verdict == "SUPPORTED"


# ---------------------------------------------------------------------------
# Test 7: Contradiction Analysis and CONTRADICTED Verdict
# ---------------------------------------------------------------------------
def test_7_contradiction_analysis_and_refutation(db_session):
    service = ClaimVerificationService(db=db_session)

    # Claim asserts ₹15,000 Cr allocated for farmer debt relief in 2022-23
    mock_c = MOCK_CLAIMS[1]
    claim = service.register_claim(
        claim_id=mock_c["claim_id"],
        original_text=mock_c["original_text"],
        claim_category=ClaimCategory(mock_c["claim_category"]),
        is_test_fixture=True
    )

    # Ingest actual statutory budget document showing ₹2,393 Cr
    doc_mock = MOCK_EVIDENCE_DOCS[1]
    doc = EvidenceDocument(
        document_id=doc_mock["document_id"],
        source_tier=SourceTier(doc_mock["source_tier"]),
        source_name=doc_mock["source_name"],
        document_type=doc_mock["document_type"],
        title=doc_mock["title"],
        file_hash_sha256=doc_mock["file_hash_sha256"]
    )
    db_session.add(doc)
    pass_mock = doc_mock["passages"][0]
    passage = EvidencePassage(
        passage_id=pass_mock["passage_id"],
        document_id=doc.document_id,
        passage_text=pass_mock["passage_text"],
        numerical_values=pass_mock["numerical_values"]
    )
    db_session.add(passage)
    db_session.commit()

    service.assess_source_quality(doc.document_id)

    # Link as CONTRADICTS
    service.link_evidence(
        claim_id=claim.claim_id,
        passage_id=passage.passage_id,
        relationship_type=EvidenceRelationshipType.CONTRADICTS,
        confidence_score=0.10,
        contradiction_score=0.92,
        reconciliation_notes="Official Budget Demand 5 recorded ₹2,393 Cr for debt relief, refuting claimed ₹15,000 Cr."
    )

    result = service.verify_claim(
        claim_id=claim.claim_id,
        manual_findings={"claimed_inr_cr": 15000.0, "actual_inr_cr": 2393.0, "discrepancy_pct": -84.0}
    )

    assert result.verdict == VerificationVerdict.CONTRADICTED
    assert result.contradiction_score >= 0.50
    assert result.empirical_findings["actual_inr_cr"] == 2393.0


# ---------------------------------------------------------------------------
# Test 8: Uncertainty Exposure and Missing Records (UNVERIFIABLE)
# ---------------------------------------------------------------------------
def test_8_uncertainty_exposure_and_missing_data(db_session):
    service = ClaimVerificationService(db=db_session)

    # Unverifiable secret cabinet assertion with no official records
    mock_c = MOCK_CLAIMS[5]
    claim = service.register_claim(
        claim_id=mock_c["claim_id"],
        original_text=mock_c["original_text"],
        claim_category=ClaimCategory(mock_c["claim_category"]),
        is_test_fixture=True
    )

    # Verify claim with NO linked evidence
    result = service.verify_claim(
        claim_id=claim.claim_id,
        limitations_and_caveats="Data limitations: No public gazettes, cabinet minutes, or transport feasibility studies exist for this assertion."
    )

    assert result.verdict == VerificationVerdict.UNVERIFIABLE_INSUFFICIENT_EVIDENCE
    assert result.uncertainty_score == 1.0
    assert result.confidence_score <= 0.40
    assert "limitations" in result.limitations_and_caveats.lower()


# ---------------------------------------------------------------------------
# Test 9: Contextual Omission Detection (MISLEADING_CONTEXT)
# ---------------------------------------------------------------------------
def test_9_contextual_omission_detection(db_session):
    service = ClaimVerificationService(db=db_session)

    mock_c = MOCK_CLAIMS[6]
    claim = service.register_claim(
        claim_id=mock_c["claim_id"],
        original_text=mock_c["original_text"],
        claim_category=ClaimCategory(mock_c["claim_category"]),
        is_test_fixture=True
    )

    doc = EvidenceDocument(
        document_id="EDOC-RBI-STATE-DEBT",
        source_tier=SourceTier.TIER_2_OFFICIAL_AGENCY,
        source_name="Reserve Bank of India",
        document_type="STATISTICAL_REPORT",
        title="State Finances: A Study of Budgets of 2021-22",
        file_hash_sha256="hashrbistatedebt2021"
    )
    db_session.add(doc)
    passage = EvidencePassage(
        passage_id="EPASS-RBI-01",
        document_id=doc.document_id,
        passage_text="Gross borrowing increased during pandemic year, while GSDP debt ratio remained within FRBM limits."
    )
    db_session.add(passage)
    db_session.commit()

    service.assess_source_quality(doc.document_id)

    service.link_evidence(
        claim_id=claim.claim_id,
        passage_id=passage.passage_id,
        relationship_type=EvidenceRelationshipType.CONTEXTUALIZES,
        relevance_score=0.88,
        confidence_score=0.80,
        reconciliation_notes="Figures omit the COVID revenue collapse and macro FRBM debt limit context."
    )

    result = service.verify_claim(claim_id=claim.claim_id)
    assert result.verdict == VerificationVerdict.MISLEADING_CONTEXT


# ---------------------------------------------------------------------------
# Test 10: Human Review Submission, Override Auditing, and History
# ---------------------------------------------------------------------------
def test_10_human_review_and_override_audit(db_session):
    service = ClaimVerificationService(db=db_session)

    mock_c = MOCK_CLAIMS[3]
    claim = service.register_claim(
        claim_id=mock_c["claim_id"],
        original_text=mock_c["original_text"],
        claim_category=ClaimCategory(mock_c["claim_category"]),
        is_test_fixture=True
    )

    # Initial automated verification
    res = service.verify_claim(claim_id=claim.claim_id, manual_rationale="Initial automated pass.")
    assert res.verdict == VerificationVerdict.UNVERIFIABLE_INSUFFICIENT_EVIDENCE

    # Submit human expert review with OVERRIDE
    review = service.submit_human_review(
        claim_id=claim.claim_id,
        reviewer_id="analyst_parliamentary_02",
        review_status=ReviewStatus.OVERRIDDEN,
        reviewed_verdict=VerificationVerdict.PARTIALLY_SUPPORTED,
        review_notes="Sansad activity records confirm 122 total questions, with 14 relating to coastal ecology.",
        override_applied=True
    )

    assert review.override_applied is True
    assert review.reviewed_verdict == "PARTIALLY_SUPPORTED"

    # Verify updated current result
    updated_res = db_session.query(VerificationResult).filter(
        VerificationResult.claim_id == claim.claim_id,
        VerificationResult.is_current == True
    ).first()
    assert updated_res.verdict == VerificationVerdict.PARTIALLY_SUPPORTED
    assert "Human Review Override" in updated_res.rationale

    # Check VerificationHistory audit trail
    hist_entries = db_session.query(VerificationHistory).filter(
        VerificationHistory.claim_id == claim.claim_id
    ).all()
    assert len(hist_entries) >= 2
    override_hist = next(h for h in hist_entries if "HUMAN_REVIEWER" in h.triggered_by)
    assert override_hist.new_verdict == "PARTIALLY_SUPPORTED"


# ---------------------------------------------------------------------------
# Test 11: Non-Ranking Rule Enforcement
# ---------------------------------------------------------------------------
def test_11_strictly_no_politician_rankings_enforced(db_session):
    service = ClaimVerificationService(db=db_session)

    # Verify that ClaimVerificationService does NOT implement truthfulness rankings
    assert not hasattr(service, "rank_politicians_by_truthfulness")
    assert not hasattr(service, "get_party_honesty_leaderboard")
    assert not hasattr(service, "generate_politician_lie_meter")


# ---------------------------------------------------------------------------
# Test 12: REST API Endpoints Verification
# ---------------------------------------------------------------------------
def test_12_api_endpoints_integration(api_client, db_session):
    # 1. Test POST /api/claims/
    post_payload = {
        "claim_id": "CLM-API-TEST-001",
        "original_text": "Tamil Nadu has the highest Gross Enrollment Ratio in higher education in India.",
        "claim_category": "HEALTHCARE_EDUCATION",
        "speaker_name": "State Education Minister",
        "speaker_party": "DMK",
        "language": "en"
    }
    resp = api_client.post("/api/claims/", json=post_payload)
    assert resp.status_code in [200, 201]
    res_data = resp.get_json()["data"]
    assert res_data["claim_id"] == "CLM-API-TEST-001"

    # 2. Test GET /api/claims/
    get_resp = api_client.get("/api/claims/")
    assert get_resp.status_code == 200
    claims_list = get_resp.get_json()["data"]["claims"]
    assert any(c["claim_id"] == "CLM-API-TEST-001" for c in claims_list)

    # 3. Test GET /api/claims/<id>
    single_resp = api_client.get("/api/claims/CLM-API-TEST-001")
    assert single_resp.status_code == 200
    claim_prof = single_resp.get_json()["data"]
    assert claim_prof["claim_id"] == "CLM-API-TEST-001"
    assert len(claim_prof["versions"]) == 1

    # 4. Test POST /api/claims/<id>/decompose
    decomp_payload = {
        "subjects": [
            {"subject_type": "GOVERNMENT_DEPARTMENT", "canonical_name": "Higher Education Department"},
            {"subject_type": "STATISTICAL_INDICATOR", "canonical_name": "Gross Enrollment Ratio"}
        ]
    }
    decomp_resp = api_client.post("/api/claims/CLM-API-TEST-001/decompose", json=decomp_payload)
    assert decomp_resp.status_code == 200

    # 5. Test POST /api/claims/<id>/verify
    verify_resp = api_client.post("/api/claims/CLM-API-TEST-001/verify", json={
        "rationale": "Verified against AISHE survey report."
    })
    assert verify_resp.status_code == 200
    assert verify_resp.get_json()["data"]["verdict"] == "UNVERIFIABLE_INSUFFICIENT_EVIDENCE"

    # 6. Test GET /api/claims/stats
    stats_resp = api_client.get("/api/claims/stats")
    assert stats_resp.status_code == 200
    stats = stats_resp.get_json()["data"]
    assert "total_claims" in stats
    assert "claims_by_category" in stats
    assert "verdicts_distribution" in stats
    assert "prohibited" in stats["ranking_policy"].lower()
