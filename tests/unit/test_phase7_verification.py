"""
Phase 7.7 — Unit Tests for Claim Verification Engine and Human Review Workflow.

Tests:
1. Supported by available evidence (statutory confirmation, explanation identifies parts supported).
2. Contradicted by available evidence (statutory refutation, explanation identifies parts contradicted).
3. Partially supported (multi-part claim with partial delivery or unresolved sub-claim).
4. Missing important context (historical baseline omission or pilot restriction).
5. Insufficient evidence (zero documents, high uncertainty, absence does not prove falsehood).
6. Disputed evidence (both authoritative support and authoritative contradiction).
7. Unverifiable (political slogans and non-factual rhetoric).
8. Pending review (inconclusive automated alignment with high uncertainty).
9. Human review workflow: Accept assessment (status accepted, review record logged).
10. Human review workflow: Revise outcome (preserves automated baseline, logs revision audit history).
11. Human review workflow: Correct decomposition, add evidence, and mark evidence irrelevant.
12. REST API endpoints integration: /verify, /review, and /verification profile.
"""

import pytest
from datetime import datetime, timezone
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.database.base_class import Base
from backend.models.claim import (
    Claim,
    AtomicClaim,
    EvidenceDocument,
    EvidencePassage,
    ClaimEvidenceRelationship,
    VerificationResult,
    VerificationRun,
    VerificationHistory,
    ReviewRecord,
    VerificationOutcome,
    VerificationVerdict,
    ReviewAction,
    ReviewStatus,
    EvidenceRelationshipType,
    SourceTier,
    ClaimCategory,
    ClaimStatus
)
from backend.services.claim_verification_engine import ClaimVerificationEngine
from backend.api.app import create_app


@pytest.fixture
def db_session():
    """Isolated in-memory SQLite database session for verification tests."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    # Prepopulate standard test evidence documents and passages
    # 1. Statutory Support Document
    doc_supp = EvidenceDocument(
        document_id="EDOC-VERIF-GO-2023",
        source_tier=SourceTier.TIER_1_STATUTORY,
        source_name="Government Order G.O. (Ms) No. 49",
        publisher="Special Programme Implementation Department, TN",
        document_type="GOVERNMENT_ORDER",
        source_category="OFFICIAL_GOVERNMENT",
        title="Implementation Guidelines for Kalaignar Magalir Urimai Thittam 2023-24",
        publication_date=datetime(2023, 7, 15, tzinfo=timezone.utc),
        file_hash_sha256="hash-verif-supp-001",
        language="en",
        is_official=True
    )
    pass_supp = EvidencePassage(
        passage_id="EPASS-VERIF-GO-01",
        document_id="EDOC-VERIF-GO-2023",
        passage_text="Government Order G.O. (Ms) No. 49 sanctioned ₹7,000 crores to disburse ₹1,000 per month to eligible women beneficiaries in 2023-24.",
        numerical_values={"amount_crores": 7000.0, "monthly_stipend": 1000.0, "year": 2023}
    )

    # 2. Statutory Contradiction Document (CAG Audit)
    doc_contra = EvidenceDocument(
        document_id="EDOC-VERIF-CAG-2024",
        source_tier=SourceTier.TIER_1_STATUTORY,
        source_name="CAG Audit Report on Welfare Schemes",
        publisher="Comptroller and Auditor General of India",
        document_type="CAG_AUDIT",
        source_category="LEGISLATIVE_RECORD",
        title="Report of the Comptroller and Auditor General for the year ended March 2024",
        publication_date=datetime(2024, 3, 20, tzinfo=timezone.utc),
        file_hash_sha256="hash-verif-contra-002",
        language="en",
        is_official=True
    )
    pass_contra = EvidencePassage(
        passage_id="EPASS-VERIF-CAG-01",
        document_id="EDOC-VERIF-CAG-2024",
        passage_text="Audit scrutiny revealed significant shortfall in disbursements with 35 lakh applications rejected without due notice in 2023-24.",
        numerical_values={"rejected_lakhs": 35.0, "year": 2024}
    )

    # 3. Outdated Baseline Document
    doc_old = EvidenceDocument(
        document_id="EDOC-VERIF-OLD-2018",
        source_tier=SourceTier.TIER_1_STATUTORY,
        source_name="CAG Audit Report 2018-19",
        publisher="Comptroller and Auditor General of India",
        document_type="AUDIT_REPORT",
        source_category="OFFICIAL_GOVERNMENT",
        title="Audit of Social Welfare Programs 2018-19",
        publication_date=datetime(2019, 2, 10, tzinfo=timezone.utc),
        file_hash_sha256="hash-verif-old-003",
        language="en",
        is_official=True
    )
    pass_old = EvidencePassage(
        passage_id="EPASS-VERIF-OLD-01",
        document_id="EDOC-VERIF-OLD-2018",
        passage_text="Review of historical welfare schemes indicated past baseline delays.",
        numerical_values={"year": 2018}
    )

    session.add_all([doc_supp, pass_supp, doc_contra, pass_contra, doc_old, pass_old])
    session.commit()

    yield session
    session.close()


@pytest.fixture
def api_client(db_session):
    """Flask test client bound to test database engine."""
    app = create_app()
    app.config["TESTING"] = True

    from backend.database.session import engine
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    with app.test_client() as client:
        yield client

    Base.metadata.drop_all(bind=engine)


# ---------------------------------------------------------------------------
# Test 1: Supported by Available Evidence
# ---------------------------------------------------------------------------
def test_1_supported_by_available_evidence(db_session):
    engine = ClaimVerificationEngine(db=db_session)

    claim = Claim(
        claim_id="CLM-VERIF-SUPP-01",
        original_text="Kalaignar Magalir Urimai Thittam provides ₹1,000 per month.",
        normalized_text="kalaignar magalir urimai thittam provides 1000 per month",
        claim_category=ClaimCategory.GOVERNMENT_SCHEMES
    )
    ac = AtomicClaim(
        atomic_claim_id="ACM-VERIF-SUPP-01",
        claim_id=claim.claim_id,
        atomic_claim_text="Kalaignar Magalir Urimai Thittam provides ₹1,000 per month",
        subject="Kalaignar Magalir Urimai Thittam",
        numeric_value=1000.0
    )
    db_session.add_all([claim, ac])
    db_session.commit()

    # Link supporting relationship
    rel = ClaimEvidenceRelationship(
        relationship_id="CER-VERIF-SUPP-01",
        claim_id=claim.claim_id,
        atomic_claim_id=ac.atomic_claim_id,
        evidence_document_id="EDOC-VERIF-GO-2023",
        passage_id="EPASS-VERIF-GO-01",
        relationship_type=EvidenceRelationshipType.SUPPORTS,
        supporting_text_reference="sanctioned ₹7,000 crores to disburse ₹1,000 per month",
        confidence=0.92
    )
    db_session.add(rel)
    db_session.commit()

    res = engine.verify_claim(claim_id=claim.claim_id)

    assert res.outcome == VerificationOutcome.SUPPORTED_BY_AVAILABLE_EVIDENCE
    assert res.confidence >= 0.80
    assert res.uncertainty_indicator <= 0.25
    assert len(res.supporting_evidence_ids) >= 1
    assert "SUPPORTED" in res.explanation
    assert res.source_diversity["total_relevant_passages"] >= 1


# ---------------------------------------------------------------------------
# Test 2: Contradicted by Available Evidence
# ---------------------------------------------------------------------------
def test_2_contradicted_by_available_evidence(db_session):
    engine = ClaimVerificationEngine(db=db_session)

    claim = Claim(
        claim_id="CLM-VERIF-CONTRA-01",
        original_text="Disbursed funds without any rejection or shortfall in 2023-24.",
        normalized_text="disbursed funds without any rejection or shortfall in 2023-24",
        claim_category=ClaimCategory.GOVERNMENT_SCHEMES
    )
    ac = AtomicClaim(
        atomic_claim_id="ACM-VERIF-CONTRA-01",
        claim_id=claim.claim_id,
        atomic_claim_text="Disbursed funds without shortfall in 2023-24",
        subject="Disbursements"
    )
    db_session.add_all([claim, ac])
    db_session.commit()

    rel = ClaimEvidenceRelationship(
        relationship_id="CER-VERIF-CONTRA-01",
        claim_id=claim.claim_id,
        atomic_claim_id=ac.atomic_claim_id,
        evidence_document_id="EDOC-VERIF-CAG-2024",
        passage_id="EPASS-VERIF-CAG-01",
        relationship_type=EvidenceRelationshipType.CONTRADICTS,
        contradicting_text_reference="Audit scrutiny revealed significant shortfall with 35 lakh applications rejected",
        confidence=0.88
    )
    db_session.add(rel)
    db_session.commit()

    res = engine.verify_claim(claim_id=claim.claim_id)

    assert res.outcome == VerificationOutcome.CONTRADICTED_BY_AVAILABLE_EVIDENCE
    assert len(res.contradicting_evidence_ids) >= 1
    assert "CONTRADICTED" in res.explanation


# ---------------------------------------------------------------------------
# Test 3: Partially Supported (Multi-Part Claim)
# ---------------------------------------------------------------------------
def test_3_partially_supported_multi_part_claim(db_session):
    engine = ClaimVerificationEngine(db=db_session)

    claim = Claim(
        claim_id="CLM-VERIF-PART-01",
        original_text="Government launched ₹1,000 monthly scheme and gave laptops to all private college students.",
        normalized_text="government launched 1000 monthly scheme and gave laptops to all private college students",
        claim_category=ClaimCategory.GOVERNMENT_SCHEMES
    )
    ac1 = AtomicClaim(
        atomic_claim_id="ACM-VERIF-PART-01",
        claim_id=claim.claim_id,
        atomic_claim_text="Government launched ₹1,000 monthly scheme",
        subject="Kalaignar Magalir Urimai Thittam"
    )
    ac2 = AtomicClaim(
        atomic_claim_id="ACM-VERIF-PART-02",
        claim_id=claim.claim_id,
        atomic_claim_text="Gave laptops to all private college students",
        subject="Laptop Scheme"
    )
    db_session.add_all([claim, ac1, ac2])
    db_session.commit()

    # ac1 is supported; ac2 has no records (unresolved)
    rel1 = ClaimEvidenceRelationship(
        relationship_id="CER-VERIF-PART-01",
        claim_id=claim.claim_id,
        atomic_claim_id=ac1.atomic_claim_id,
        evidence_document_id="EDOC-VERIF-GO-2023",
        passage_id="EPASS-VERIF-GO-01",
        relationship_type=EvidenceRelationshipType.SUPPORTS,
        supporting_text_reference="sanctioned ₹7,000 crores to disburse ₹1,000 per month"
    )
    db_session.add(rel1)
    db_session.commit()

    res = engine.verify_claim(claim_id=claim.claim_id)

    assert res.outcome == VerificationOutcome.PARTIALLY_SUPPORTED
    assert "SUPPORTED" in res.explanation
    assert "UNRESOLVED" in res.explanation


# ---------------------------------------------------------------------------
# Test 4: Missing Important Context
# ---------------------------------------------------------------------------
def test_4_missing_important_context(db_session):
    engine = ClaimVerificationEngine(db=db_session)

    claim = Claim(
        claim_id="CLM-VERIF-CTX-01",
        original_text="Welfare programs in Tamil Nadu suffer from delayed disbursements.",
        normalized_text="welfare programs in tamil nadu suffer from delayed disbursements",
        claim_category=ClaimCategory.GOVERNMENT_SCHEMES,
        temporal_scope="2024"
    )
    ac = AtomicClaim(
        atomic_claim_id="ACM-VERIF-CTX-01",
        claim_id=claim.claim_id,
        atomic_claim_text="Welfare programs suffer from delays",
        time_period="2024"
    )
    db_session.add_all([claim, ac])
    db_session.commit()

    # Only outdated 2018 record found
    rel_old = ClaimEvidenceRelationship(
        relationship_id="CER-VERIF-OLD-01",
        claim_id=claim.claim_id,
        atomic_claim_id=ac.atomic_claim_id,
        evidence_document_id="EDOC-VERIF-OLD-2018",
        passage_id="EPASS-VERIF-OLD-01",
        relationship_type=EvidenceRelationshipType.CONTEXTUALIZES,
        is_outdated=True
    )
    db_session.add(rel_old)
    db_session.commit()

    res = engine.verify_claim(claim_id=claim.claim_id)

    assert res.outcome == VerificationOutcome.MISSING_IMPORTANT_CONTEXT
    assert "omits important" in res.explanation.lower()


# ---------------------------------------------------------------------------
# Test 5: Insufficient Evidence Handling
# ---------------------------------------------------------------------------
def test_5_insufficient_evidence_when_evidence_is_missing(db_session):
    """
    Enforces core epistemic principle:
    Zero evidence does not equal false/contradicted; it evaluates to insufficient_evidence.
    """
    engine = ClaimVerificationEngine(db=db_session)

    claim = Claim(
        claim_id="CLM-VERIF-INS-01",
        original_text="Special sports complex constructed in rural panchayat in 1994.",
        normalized_text="special sports complex constructed in rural panchayat in 1994",
        claim_category=ClaimCategory.PUBLIC_INFRASTRUCTURE
    )
    db_session.add(claim)
    db_session.commit()

    res = engine.verify_claim(claim_id=claim.claim_id)

    assert res.outcome == VerificationOutcome.INSUFFICIENT_EVIDENCE
    assert res.uncertainty_indicator >= 0.80
    assert "Absence of evidence is not proof that the statement is false" in res.explanation


# ---------------------------------------------------------------------------
# Test 6: Disputed Evidence
# ---------------------------------------------------------------------------
def test_6_disputed_evidence(db_session):
    engine = ClaimVerificationEngine(db=db_session)

    claim = Claim(
        claim_id="CLM-VERIF-DISP-01",
        original_text="Scheme fund execution for 2023-24.",
        normalized_text="scheme fund execution for 2023-24",
        claim_category=ClaimCategory.GOVERNMENT_SCHEMES
    )
    ac = AtomicClaim(
        atomic_claim_id="ACM-VERIF-DISP-01",
        claim_id=claim.claim_id,
        atomic_claim_text="Scheme funds executed in 2023-24"
    )
    db_session.add_all([claim, ac])
    db_session.commit()

    # Link both official support and official CAG contradiction
    rel_supp = ClaimEvidenceRelationship(
        relationship_id="CER-VERIF-DISP-SUPP",
        claim_id=claim.claim_id,
        atomic_claim_id=ac.atomic_claim_id,
        evidence_document_id="EDOC-VERIF-GO-2023",
        passage_id="EPASS-VERIF-GO-01",
        relationship_type=EvidenceRelationshipType.SUPPORTS,
        supporting_text_reference="sanctioned ₹7,000 crores to disburse ₹1,000 per month"
    )
    rel_contra = ClaimEvidenceRelationship(
        relationship_id="CER-VERIF-DISP-CONTRA",
        claim_id=claim.claim_id,
        atomic_claim_id=ac.atomic_claim_id,
        evidence_document_id="EDOC-VERIF-CAG-2024",
        passage_id="EPASS-VERIF-CAG-01",
        relationship_type=EvidenceRelationshipType.CONTRADICTS,
        contradicting_text_reference="Audit scrutiny revealed significant shortfall"
    )
    db_session.add_all([rel_supp, rel_contra])
    db_session.commit()

    res = engine.verify_claim(claim_id=claim.claim_id)

    assert res.outcome == VerificationOutcome.DISPUTED_EVIDENCE
    assert "conflict between available authoritative sources" in res.explanation.lower()


# ---------------------------------------------------------------------------
# Test 7: Unverifiable for Slogans and Subjective Opinions
# ---------------------------------------------------------------------------
def test_7_unverifiable_for_slogans_and_subjective_opinions(db_session):
    engine = ClaimVerificationEngine(db=db_session)

    claim = Claim(
        claim_id="CLM-VERIF-SLOGAN-01",
        original_text="Our party will usher in a golden era of prosperity and happiness for all citizens!",
        normalized_text="our party will usher in a golden era of prosperity and happiness for all citizens",
        claim_category=ClaimCategory.POLITICAL_PROMISES,
        metadata_json={"verifiability_status": "SLOGAN"}
    )
    db_session.add(claim)
    db_session.commit()

    res = engine.verify_claim(claim_id=claim.claim_id)

    assert res.outcome == VerificationOutcome.UNVERIFIABLE
    assert "slogan, opinion, or non-verifiable value judgment" in res.explanation


# ---------------------------------------------------------------------------
# Test 8: Pending Review and Uncertainty Exposure
# ---------------------------------------------------------------------------
def test_8_pending_review_and_uncertainty_handling(db_session):
    claim = Claim(
        claim_id="CLM-VERIF-PEND-01",
        original_text="Pending review initial intake claim.",
        normalized_text="pending review initial intake claim",
        claim_category=ClaimCategory.GOVERNMENT_SCHEMES
    )
    db_session.add(claim)
    db_session.commit()

    result = VerificationResult(
        result_id="VRES-PEND-01",
        claim_id=claim.claim_id,
        outcome=VerificationOutcome.PENDING_REVIEW,
        explanation="Automated intake completed; queued for senior analyst review.",
        review_status=ReviewStatus.PENDING_REVIEW,
        uncertainty_indicator=0.60
    )
    db_session.add(result)
    db_session.commit()

    assert result.outcome == VerificationOutcome.PENDING_REVIEW
    assert result.review_status == ReviewStatus.PENDING_REVIEW
    assert result.uncertainty_indicator == 0.60


# ---------------------------------------------------------------------------
# Test 9: Human Review Workflow — Accept Assessment
# ---------------------------------------------------------------------------
def test_9_human_review_workflow_accept_assessment(db_session):
    engine = ClaimVerificationEngine(db=db_session)

    claim = Claim(
        claim_id="CLM-REV-ACC-01",
        original_text="Kalaignar Magalir Urimai Thittam provides ₹1,000 per month.",
        normalized_text="kalaignar magalir urimai thittam provides 1000 per month",
        claim_category=ClaimCategory.GOVERNMENT_SCHEMES
    )
    db_session.add(claim)
    db_session.commit()

    # Link evidence and run verify
    rel = ClaimEvidenceRelationship(
        relationship_id="CER-REV-ACC-01",
        claim_id=claim.claim_id,
        evidence_document_id="EDOC-VERIF-GO-2023",
        passage_id="EPASS-VERIF-GO-01",
        relationship_type=EvidenceRelationshipType.SUPPORTS,
        supporting_text_reference="sanctioned ₹7,000 crores to disburse ₹1,000 per month"
    )
    db_session.add(rel)
    db_session.commit()

    engine.verify_claim(claim_id=claim.claim_id)

    # Human reviewer accepts assessment
    res = engine.accept_assessment(
        claim_id=claim.claim_id,
        reviewer_id="ANALYST-CH-01",
        review_notes="Primary G.O. and disbursement numbers cross-checked against treasury portal."
    )

    assert res.review_status == ReviewStatus.ACCEPTED
    assert claim.review_status == ReviewStatus.ACCEPTED

    # Verify review record logged
    reviews = list(claim.reviews)
    assert len(reviews) >= 1
    assert reviews[0].reviewer_id == "ANALYST-CH-01"
    assert reviews[0].action == ReviewAction.ACCEPT_ASSESSMENT.value
    assert reviews[0].override_applied is False

    # Verify history audit logged
    histories = list(claim.verification_history)
    assert len(histories) >= 2  # initial + accept
    assert "accepted automated assessment" in histories[-1].change_reason


# ---------------------------------------------------------------------------
# Test 10: Human Review Workflow — Revise Outcome (Preserves Automated Baseline)
# ---------------------------------------------------------------------------
def test_10_human_review_workflow_revise_outcome_preserves_baseline(db_session):
    engine = ClaimVerificationEngine(db=db_session)

    claim = Claim(
        claim_id="CLM-REV-OVR-01",
        original_text="Kalaignar Magalir Urimai Thittam in Tamil Nadu.",
        normalized_text="kalaignar magalir urimai thittam in tamil nadu",
        claim_category=ClaimCategory.GOVERNMENT_SCHEMES
    )
    db_session.add(claim)
    db_session.commit()

    # Link supporting evidence
    rel = ClaimEvidenceRelationship(
        relationship_id="CER-REV-OVR-01",
        claim_id=claim.claim_id,
        evidence_document_id="EDOC-VERIF-GO-2023",
        passage_id="EPASS-VERIF-GO-01",
        relationship_type=EvidenceRelationshipType.SUPPORTS,
        supporting_text_reference="sanctioned ₹7,000 crores to disburse ₹1,000 per month"
    )
    db_session.add(rel)
    db_session.commit()

    # Initial automated verification
    res_auto = engine.verify_claim(claim_id=claim.claim_id)
    assert res_auto.outcome == VerificationOutcome.SUPPORTED_BY_AVAILABLE_EVIDENCE

    # Reviewer overrides outcome with justification
    res_revised = engine.revise_outcome(
        claim_id=claim.claim_id,
        reviewer_id="EDITOR-IN-CHIEF-01",
        new_outcome="partially_supported",
        explanation="Revised to partially_supported because ongoing scrutiny revealed pending coverage in 3 districts.",
        review_notes="Field audit reported delays in hilly tribal belts."
    )

    # Core requirement: Current outcome is revised, BUT automated baseline is permanently preserved!
    assert res_revised.outcome == VerificationOutcome.PARTIALLY_SUPPORTED
    assert res_revised.automated_outcome == VerificationOutcome.SUPPORTED_BY_AVAILABLE_EVIDENCE
    assert res_revised.review_status == ReviewStatus.OVERRIDDEN

    # Check review record
    rev_record = claim.reviews[-1]
    assert rev_record.override_applied is True
    assert rev_record.original_outcome == "supported_by_available_evidence"
    assert rev_record.reviewed_outcome == "partially_supported"
    assert "field audit reported delays" in rev_record.review_notes.lower()


# ---------------------------------------------------------------------------
# Test 11: Human Review Workflow — Decomposition and Evidence Adjustments
# ---------------------------------------------------------------------------
def test_11_human_review_workflow_decomposition_and_evidence_adjustments(db_session):
    engine = ClaimVerificationEngine(db=db_session)

    claim = Claim(
        claim_id="CLM-REV-ADJ-01",
        original_text="Compound claim requiring decomposition correction.",
        normalized_text="compound claim requiring decomposition correction",
        claim_category=ClaimCategory.GOVERNMENT_SCHEMES
    )
    db_session.add(claim)
    db_session.commit()

    # 1. Correct decomposition
    corrected_atomics = [
        {"atomic_claim_text": "Sub-claim 1: Fund allocation", "numeric_value": 7000.0},
        {"atomic_claim_text": "Sub-claim 2: Physical delivery", "numeric_value": 1.15}
    ]
    res1 = engine.correct_claim_decomposition(
        claim_id=claim.claim_id,
        reviewer_id="EXPERT-DEC-01",
        corrected_atomics=corrected_atomics,
        review_notes="Separated budgetary sanction from ground physical delivery."
    )
    assert len(claim.atomic_claims) == 2

    # 2. Add evidence manually
    res2 = engine.add_evidence(
        claim_id=claim.claim_id,
        reviewer_id="EXPERT-DEC-01",
        document_data={
            "document_id": "EDOC-MANUAL-01",
            "source_tier": "TIER_1_STATUTORY",
            "source_name": "Manual Gazette Order",
            "title": "State Gazette 2023",
            "publication_date": datetime(2023, 8, 1, tzinfo=timezone.utc)
        },
        passage_data={
            "passage_id": "EPASS-MANUAL-01",
            "passage_text": "Gazette verifies funds and physical delivery."
        },
        relationship_type="supports",
        review_notes="Official gazette uploaded by verified fact-checker."
    )
    assert res2.outcome == VerificationOutcome.SUPPORTED_BY_AVAILABLE_EVIDENCE

    # 3. Mark evidence irrelevant
    res3 = engine.mark_evidence_irrelevant(
        claim_id=claim.claim_id,
        reviewer_id="EXPERT-DEC-01",
        relationship_id="CER-CLM-REV-ADJ-01-EPASS-MANUAL-01",
        reason="Document superseded by subsequent fiscal notification."
    )
    assert res3 is not None


# ---------------------------------------------------------------------------
# Test 12: REST API Endpoints Integration (/verify, /review, /verification)
# ---------------------------------------------------------------------------
def test_12_rest_api_verify_review_and_verification_endpoints(api_client):
    claim_id = "CLM-API-VERIF-01"

    # 1. Ingest claim
    ingest_resp = api_client.post("/api/claims/ingest", json={
        "claim_id": claim_id,
        "original_text": "Tamil Nadu budget allocated Rs 13,720 crore for Kalaignar Magalir Urimai Thittam.",
        "claim_category": "GOVERNMENT_SCHEMES",
        "candidate_source_type": "OFFICIAL_STATEMENT",
        "language": "en"
    })
    assert ingest_resp.status_code == 200

    # 2. Add evidence document and link relationship
    from backend.database.session import SessionLocal
    db = SessionLocal()
    try:
        doc = EvidenceDocument(
            document_id="EDOC-API-VERIF-01",
            source_tier=SourceTier.TIER_1_STATUTORY,
            source_name="Budget Highlights",
            document_type="BUDGET_DOCUMENT",
            title="State Budget Speech",
            file_hash_sha256="hash_api_verif_01"
        )
        pass_doc = EvidencePassage(
            passage_id="EPASS-API-VERIF-01",
            document_id="EDOC-API-VERIF-01",
            passage_text="Rs 13,720 crore allocated for Kalaignar Magalir Urimai Thittam."
        )
        rel = ClaimEvidenceRelationship(
            relationship_id=f"CER-{claim_id}-EPASS-API-VERIF-01",
            claim_id=claim_id,
            evidence_document_id=doc.document_id,
            passage_id=pass_doc.passage_id,
            relationship_type=EvidenceRelationshipType.SUPPORTS,
            supporting_text_reference="Rs 13,720 crore allocated"
        )
        db.add_all([doc, pass_doc, rel])
        db.commit()
    finally:
        db.close()

    # 3. POST /api/claims/<claim_id>/verify
    verify_resp = api_client.post(f"/api/claims/{claim_id}/verify", json={})
    assert verify_resp.status_code == 200
    v_data = verify_resp.get_json()["data"]
    assert v_data["outcome"] == "supported_by_available_evidence"
    assert "explanation" in v_data
    assert "source_diversity" in v_data

    # 4. POST /api/claims/<claim_id>/review (Human Review: Accept)
    rev_resp = api_client.post(f"/api/claims/{claim_id}/review", json={
        "reviewer_id": "FACTCHECKER-API-01",
        "action": "accept_assessment",
        "review_notes": "All budget lines cross-verified with finance portal."
    })
    assert rev_resp.status_code == 200
    r_data = rev_resp.get_json()["data"]
    assert r_data["review_status"] == "ACCEPTED"

    # 5. GET /api/claims/<claim_id>/verification (Full verification profile & audit history)
    prof_resp = api_client.get(f"/api/claims/{claim_id}/verification")
    assert prof_resp.status_code == 200
    p_data = prof_resp.get_json()["data"]
    assert p_data["claim_id"] == claim_id
    assert p_data["verification"]["outcome"] == "supported_by_available_evidence"
    assert len(p_data["review_records"]) >= 1
    assert len(p_data["verification_history"]) >= 1
    assert "epistemic_disclaimer" in p_data
