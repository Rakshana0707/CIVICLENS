"""
Phase 7.6 — Unit Tests for Claim and Evidence Relationship Analysis.

Tests:
1. Direct supporting evidence (high confidence support, matching entity/time/quantity).
2. Direct contradicting evidence (factual refutation, e.g. CAG audit showing shortfall, contradictory text reference extracted).
3. Partially supporting evidence (partial delivery, qualified numbers, or scope divergence).
4. Outdated evidence handling (e.g. 2019 report applied to 2024 claim marked as outdated / contextualizes).
5. Unrelated evidence handling (entity mismatch or geographic mismatch classified as unrelated).
6. Syndicated copies detection (wire stories clustered; syndicated copies flagged; not counted as independent corroboration).
7. Source stance: reporting a claim vs independent fact (news report quoting a speech marked as REPORTING_CLAIM).
8. Absence of document does not prove falsehood (absence of evidence evaluates to UNVERIFIABLE_INSUFFICIENT_EVIDENCE, is_false=False).
9. Keeping contradictory evidence visible (contradictory relationships preserved alongside supporting ones in database and API).
10. Multilingual claim-evidence relationship analysis (Tamil claims matched against English/Tamil statutory evidence).
11. REST API endpoint integration (POST /api/claims/<claim_id>/analyze-evidence and GET /api/claims/<claim_id>/relationships).
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
    EvidenceRelationshipType,
    ReviewStatus,
    SourceTier,
    ClaimCategory,
    ClaimStatus,
    VerificationVerdict
)
from backend.services.evidence_relationship_analyzer import (
    EvidenceRelationshipAnalyzer,
    EntityIdentityChecker,
    TemporalAlignmentChecker,
    GeographicScopeChecker,
    QuantitativeConsistencyChecker,
    SourceStanceClassifier,
    SyndicationDeduplicator
)
from backend.api.app import create_app


@pytest.fixture
def db_session():
    """Isolated in-memory SQLite database session for relationship tests."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    # Prepopulate standard test evidence documents and passages
    # 1. Statutory Support Document
    doc_supp = EvidenceDocument(
        document_id="EDOC-TN-GO-2023",
        source_tier=SourceTier.TIER_1_STATUTORY,
        source_name="Government Order G.O. (Ms) No. 49",
        publisher="Special Programme Implementation Department, TN",
        document_type="GOVERNMENT_ORDER",
        source_category="OFFICIAL_GOVERNMENT",
        title="Implementation Guidelines for Kalaignar Magalir Urimai Thittam 2023-24",
        publication_date=datetime(2023, 7, 15, tzinfo=timezone.utc),
        file_hash_sha256="hash-supp-001",
        language="en",
        is_official=True
    )
    pass_supp = EvidencePassage(
        passage_id="EPASS-GO-49-01",
        document_id="EDOC-TN-GO-2023",
        passage_text="Government Order G.O. (Ms) No. 49 sanctioned ₹7,000 crores to disburse ₹1,000 per month to 1.15 crore eligible women beneficiaries under Kalaignar Magalir Urimai Thittam across Tamil Nadu in 2023-24.",
        numerical_values={"amount_crores": 7000.0, "monthly_stipend": 1000.0, "beneficiaries_crores": 1.15, "year": 2023}
    )

    # 2. Statutory Contradiction Document (CAG Audit)
    doc_contra = EvidenceDocument(
        document_id="EDOC-CAG-AUDIT-2024",
        source_tier=SourceTier.TIER_1_STATUTORY,
        source_name="CAG Audit Report on Welfare Schemes",
        publisher="Comptroller and Auditor General of India",
        document_type="CAG_AUDIT",
        source_category="LEGISLATIVE_RECORD",
        title="Report of the Comptroller and Auditor General for the year ended March 2024",
        publication_date=datetime(2024, 3, 20, tzinfo=timezone.utc),
        file_hash_sha256="hash-contra-002",
        language="en",
        is_official=True
    )
    pass_contra = EvidencePassage(
        passage_id="EPASS-CAG-01",
        document_id="EDOC-CAG-AUDIT-2024",
        passage_text="Audit scrutiny revealed significant shortfall in Kalaignar Magalir Urimai Thittam disbursements with delayed payments and 35 lakh applications rejected without due notice in 2023-24.",
        numerical_values={"year": 2024}
    )

    # 3. Outdated Historical Document
    doc_outdated = EvidenceDocument(
        document_id="EDOC-CAG-OLD-2018",
        source_tier=SourceTier.TIER_1_STATUTORY,
        source_name="CAG Audit Report 2018-19",
        publisher="Comptroller and Auditor General of India",
        document_type="AUDIT_REPORT",
        source_category="OFFICIAL_GOVERNMENT",
        title="Audit of Social Welfare Programs 2018-19",
        publication_date=datetime(2019, 2, 10, tzinfo=timezone.utc),
        file_hash_sha256="hash-outdated-003",
        language="en",
        is_official=True
    )
    pass_outdated = EvidencePassage(
        passage_id="EPASS-OLD-01",
        document_id="EDOC-CAG-OLD-2018",
        passage_text="Review of Tamil Nadu welfare schemes including women assistance during 2018 indicated fiscal delays in disbursements.",
        numerical_values={"year": 2018}
    )

    # 4. Unrelated Other-State Document
    doc_unrelated = EvidenceDocument(
        document_id="EDOC-KAR-SCHEME-2023",
        source_tier=SourceTier.TIER_2_OFFICIAL_AGENCY,
        source_name="Karnataka Finance Bulletin",
        publisher="Government of Karnataka",
        document_type="PRESS_RELEASE",
        source_category="OFFICIAL_GOVERNMENT",
        title="Gruha Lakshmi Scheme Rollout in Karnataka",
        publication_date=datetime(2023, 8, 1, tzinfo=timezone.utc),
        file_hash_sha256="hash-unrelated-004",
        language="en",
        is_official=True
    )
    pass_unrelated = EvidencePassage(
        passage_id="EPASS-UNREL-01",
        document_id="EDOC-KAR-SCHEME-2023",
        passage_text="The Gruha Lakshmi scheme in Karnataka provides ₹2,000 monthly assistance to women heads of households across Bengaluru and Mysuru.",
        numerical_values={"monthly_stipend": 2000.0, "year": 2023}
    )

    session.add_all([doc_supp, pass_supp, doc_contra, pass_contra, doc_outdated, pass_outdated, doc_unrelated, pass_unrelated])
    session.commit()

    yield session
    session.close()


# ---------------------------------------------------------------------------
# Test 1: Direct Supporting Evidence
# ---------------------------------------------------------------------------
def test_1_direct_supporting_evidence(db_session):
    analyzer = EvidenceRelationshipAnalyzer(db=db_session)

    claim = Claim(
        claim_id="CLM-TEST-SUPP-01",
        original_text="Kalaignar Magalir Urimai Thittam provides ₹1,000 per month to 1.15 crore women beneficiaries in Tamil Nadu in 2023-24.",
        normalized_text="kalaignar magalir urimai thittam provides 1000 per month to 1.15 crore women beneficiaries in tamil nadu in 2023-24",
        claim_category=ClaimCategory.GOVERNMENT_SCHEMES,
        temporal_scope="2023-24",
        geographic_scope="Tamil Nadu",
        claim_date=datetime(2023, 9, 15, tzinfo=timezone.utc)
    )
    atomic = AtomicClaim(
        atomic_claim_id="ACM-TEST-SUPP-01",
        claim_id=claim.claim_id,
        atomic_claim_text="Kalaignar Magalir Urimai Thittam provides ₹1,000 per month to 1.15 crore women beneficiaries",
        subject="Kalaignar Magalir Urimai Thittam",
        predicate="disburses",
        time_period="2023-24",
        geographic_scope="Tamil Nadu",
        numeric_value=1.15,
        unit="crores",
        denominator="eligible women"
    )

    passage = db_session.query(EvidencePassage).filter_by(passage_id="EPASS-GO-49-01").first()
    document = passage.document

    res = analyzer.analyze_claim_evidence_relationship(
        claim=claim,
        passage=passage,
        document=document,
        atomic_claim=atomic
    )

    assert res["relationship_type"] == EvidenceRelationshipType.SUPPORTS
    assert res["entity_alignment"] == "EXACT_MATCH"
    assert res["temporal_alignment"] == "CONTEMPORANEOUS"
    assert res["geographic_alignment"] == "EXACT_JURISDICTION"
    assert res["is_outdated"] is False
    assert res["supporting_text_reference"] is not None
    assert "₹7,000 crores" in res["supporting_text_reference"] or "1.15 crore" in res["supporting_text_reference"]
    assert res["confidence"] >= 0.80


# ---------------------------------------------------------------------------
# Test 2: Direct Contradicting Evidence
# ---------------------------------------------------------------------------
def test_2_direct_contradicting_evidence(db_session):
    analyzer = EvidenceRelationshipAnalyzer(db=db_session)

    claim = Claim(
        claim_id="CLM-TEST-CONTRA-01",
        original_text="Kalaignar Magalir Urimai Thittam disbursed funds without any shortfall to all applicants in 2023-24.",
        normalized_text="kalaignar magalir urimai thittam disbursed funds without any shortfall to all applicants in 2023-24",
        claim_category=ClaimCategory.GOVERNMENT_SCHEMES,
        temporal_scope="2023-24",
        geographic_scope="Tamil Nadu"
    )
    atomic = AtomicClaim(
        atomic_claim_id="ACM-TEST-CONTRA-01",
        claim_id=claim.claim_id,
        atomic_claim_text="Kalaignar Magalir Urimai Thittam disbursed funds without shortfall in 2023-24",
        subject="Kalaignar Magalir Urimai Thittam",
        time_period="2023-24"
    )

    passage = db_session.query(EvidencePassage).filter_by(passage_id="EPASS-CAG-01").first()
    document = passage.document

    res = analyzer.analyze_claim_evidence_relationship(
        claim=claim,
        passage=passage,
        document=document,
        atomic_claim=atomic
    )

    assert res["relationship_type"] == EvidenceRelationshipType.CONTRADICTS
    assert res["contradicting_text_reference"] is not None
    assert "shortfall" in res["contradicting_text_reference"].lower()
    assert res["confidence"] >= 0.80


# ---------------------------------------------------------------------------
# Test 3: Partially Supporting Evidence
# ---------------------------------------------------------------------------
def test_3_partially_supporting_evidence(db_session):
    analyzer = EvidenceRelationshipAnalyzer(db=db_session)

    # Document showing pilot implementation of breakfast scheme in 1,545 schools
    doc_pilot = EvidenceDocument(
        document_id="EDOC-TN-PILOT-2022",
        source_tier=SourceTier.TIER_1_STATUTORY,
        source_name="School Education Department GO 2022",
        document_type="GOVERNMENT_ORDER",
        title="Breakfast Scheme Pilot Notification",
        publication_date=datetime(2022, 5, 7, tzinfo=timezone.utc),
        file_hash_sha256="hash-pilot-001"
    )
    pass_pilot = EvidencePassage(
        passage_id="EPASS-PILOT-01",
        document_id="EDOC-TN-PILOT-2022",
        passage_text="The Chief Minister's Breakfast Scheme was notified for pilot implementation in 1,545 government primary schools across Tamil Nadu in 2022-23.",
        numerical_values={"schools_count": 1545.0, "year": 2022}
    )
    db_session.add_all([doc_pilot, pass_pilot])
    db_session.commit()

    # Claim asserts complete state-wide delivery of 33,000 schools
    claim = Claim(
        claim_id="CLM-TEST-PARTIAL-01",
        original_text="The breakfast scheme covered all 33,000 schools in Tamil Nadu in 2022.",
        normalized_text="the breakfast scheme covered all 33000 schools in tamil nadu in 2022",
        claim_category=ClaimCategory.GOVERNMENT_SCHEMES,
        temporal_scope="2022"
    )
    atomic = AtomicClaim(
        atomic_claim_id="ACM-TEST-PARTIAL-01",
        claim_id=claim.claim_id,
        atomic_claim_text="The breakfast scheme covered all 33,000 schools in 2022",
        subject="Breakfast Scheme",
        numeric_value=33000.0,
        unit="schools",
        time_period="2022"
    )

    res = analyzer.analyze_claim_evidence_relationship(
        claim=claim,
        passage=pass_pilot,
        document=doc_pilot,
        atomic_claim=atomic
    )

    # Since 1545 vs 33000 is a significant variance, it is classified as contradiction or partial support
    assert res["relationship_type"] in [EvidenceRelationshipType.PARTIALLY_SUPPORTS, EvidenceRelationshipType.CONTRADICTS]
    assert res["entity_alignment"] in ["EXACT_MATCH", "RELATED_ENTITY"]


# ---------------------------------------------------------------------------
# Test 4: Outdated Evidence Handling
# ---------------------------------------------------------------------------
def test_4_outdated_evidence_handling(db_session):
    """
    Verifies that an older audit report (2018) is flagged as outdated relative to
    a 2023-24 claim and classified as CONTEXTUALIZES rather than a direct contradiction.
    """
    analyzer = EvidenceRelationshipAnalyzer(db=db_session)

    claim = Claim(
        claim_id="CLM-TEST-OUTDATED-01",
        original_text="Kalaignar Magalir Urimai Thittam achieved 100% distribution in 2023-24.",
        normalized_text="kalaignar magalir urimai thittam achieved 100% distribution in 2023-24",
        claim_category=ClaimCategory.GOVERNMENT_SCHEMES,
        temporal_scope="2023-24"
    )
    atomic = AtomicClaim(
        atomic_claim_id="ACM-TEST-OUTDATED-01",
        claim_id=claim.claim_id,
        atomic_claim_text="Kalaignar Magalir Urimai Thittam achieved 100% distribution in 2023-24",
        subject="Kalaignar Magalir Urimai Thittam",
        time_period="2023-24"
    )

    passage = db_session.query(EvidencePassage).filter_by(passage_id="EPASS-OLD-01").first()
    document = passage.document

    res = analyzer.analyze_claim_evidence_relationship(
        claim=claim,
        passage=passage,
        document=document,
        atomic_claim=atomic
    )

    assert res["relationship_type"] == EvidenceRelationshipType.CONTEXTUALIZES
    assert res["is_outdated"] is True
    assert res["temporal_alignment"] == "OUTDATED"
    assert "outdated" in res["reasoning_summary"].lower()


# ---------------------------------------------------------------------------
# Test 5: Unrelated Evidence Handling
# ---------------------------------------------------------------------------
def test_5_unrelated_evidence_handling(db_session):
    """
    Verifies that a document discussing Karnataka Gruha Lakshmi is classified as UNRELATED
    when checked against a Tamil Nadu Kalaignar Magalir Urimai claim.
    """
    analyzer = EvidenceRelationshipAnalyzer(db=db_session)

    claim = Claim(
        claim_id="CLM-TEST-UNREL-01",
        original_text="Kalaignar Magalir Urimai Thittam provides ₹1,000 per month in Tamil Nadu.",
        normalized_text="kalaignar magalir urimai thittam provides 1000 per month in tamil nadu",
        claim_category=ClaimCategory.GOVERNMENT_SCHEMES,
        geographic_scope="Tamil Nadu"
    )
    atomic = AtomicClaim(
        atomic_claim_id="ACM-TEST-UNREL-01",
        claim_id=claim.claim_id,
        atomic_claim_text="Kalaignar Magalir Urimai Thittam provides ₹1,000 per month",
        subject="Kalaignar Magalir Urimai Thittam",
        geographic_scope="Tamil Nadu"
    )

    passage = db_session.query(EvidencePassage).filter_by(passage_id="EPASS-UNREL-01").first()
    document = passage.document

    res = analyzer.analyze_claim_evidence_relationship(
        claim=claim,
        passage=passage,
        document=document,
        atomic_claim=atomic
    )

    assert res["relationship_type"] == EvidenceRelationshipType.UNRELATED
    assert res["geographic_alignment"] == "GEOGRAPHIC_MISMATCH" or res["entity_alignment"] == "ENTITY_MISMATCH"


# ---------------------------------------------------------------------------
# Test 6: Syndicated Copies Detection & Deduplication
# ---------------------------------------------------------------------------
def test_6_syndicated_copies_detection_and_deduplication(db_session):
    """
    Verifies that identical PTI wire copies are recognized as syndicated echoes,
    clustered together, and flagged so they are not counted as independent corroboration.
    """
    analyzer = EvidenceRelationshipAnalyzer(db=db_session)

    doc_news1 = EvidenceDocument(
        document_id="EDOC-WIRE-NEWS-01",
        source_tier=SourceTier.TIER_3_ACCREDITED_FACTCHECK,
        source_name="Daily News Portal A",
        publisher="Daily News A (PTI Wire)",
        document_type="NEWS_ARTICLE",
        title="TN launches Kalaignar Magalir Urimai scheme",
        file_hash_sha256="hash-wire-01"
    )
    pass_news1 = EvidencePassage(
        passage_id="EPASS-WIRE-01",
        document_id="EDOC-WIRE-NEWS-01",
        passage_text="PTI News: Tamil Nadu Chief Minister launched the Kalaignar Magalir Urimai Thittam today to provide monthly assistance of 1000 rupees to women household heads in Chennai."
    )

    doc_news2 = EvidenceDocument(
        document_id="EDOC-WIRE-NEWS-02",
        source_tier=SourceTier.TIER_3_ACCREDITED_FACTCHECK,
        source_name="Daily News Portal B",
        publisher="Daily News B (PTI Wire)",
        document_type="NEWS_ARTICLE",
        title="Stalin launches women assistance scheme",
        file_hash_sha256="hash-wire-02"
    )
    pass_news2 = EvidencePassage(
        passage_id="EPASS-WIRE-02",
        document_id="EDOC-WIRE-NEWS-02",
        passage_text="PTI News: Tamil Nadu Chief Minister launched the Kalaignar Magalir Urimai Thittam today to provide monthly assistance of 1000 rupees to women household heads in Chennai."
    )

    db_session.add_all([doc_news1, pass_news1, doc_news2, pass_news2])
    db_session.commit()

    claim = Claim(
        claim_id="CLM-TEST-SYND-01",
        original_text="Chief Minister launched Kalaignar Magalir Urimai Thittam in Chennai.",
        normalized_text="chief minister launched kalaignar magalir urimai thittam in chennai",
        claim_category=ClaimCategory.GOVERNMENT_SCHEMES
    )

    # First copy
    cluster_list = []
    res1 = analyzer.analyze_claim_evidence_relationship(
        claim=claim,
        passage=pass_news1,
        document=doc_news1,
        known_cluster_passages=cluster_list
    )
    assert res1["is_syndicated_copy"] is False
    cluster_list.append({
        "passage_text": pass_news1.passage_text,
        "cluster_id": res1["syndication_cluster_id"],
        "fingerprint": SyndicationDeduplicator.compute_passage_fingerprint(pass_news1.passage_text),
        "document_id": doc_news1.document_id
    })

    # Second copy (identical PTI wire feed)
    res2 = analyzer.analyze_claim_evidence_relationship(
        claim=claim,
        passage=pass_news2,
        document=doc_news2,
        known_cluster_passages=cluster_list
    )
    assert res2["is_syndicated_copy"] is True
    assert res2["syndication_cluster_id"] == res1["syndication_cluster_id"]
    assert "syndicated copy" in res2["reasoning_summary"].lower()


# ---------------------------------------------------------------------------
# Test 7: Source Stance (Reporting a Claim vs Independent Fact)
# ---------------------------------------------------------------------------
def test_7_source_stance_reporting_vs_independent_fact(db_session):
    """
    Verifies that a news article quoting a politician's speech is classified as REPORTING_CLAIM,
    not independent factual proof.
    """
    analyzer = EvidenceRelationshipAnalyzer(db=db_session)

    doc_speech_report = EvidenceDocument(
        document_id="EDOC-NEWS-SPEECH-01",
        source_tier=SourceTier.TIER_4_SECONDARY_CIVIC,
        source_name="Chennai Morning Gazette",
        document_type="NEWS_ARTICLE",
        title="Rally Speech Coverage",
        file_hash_sha256="hash-speech-01"
    )
    pass_speech_report = EvidencePassage(
        passage_id="EPASS-SPEECH-01",
        document_id="EDOC-NEWS-SPEECH-01",
        passage_text="Addressing an election rally in Madurai, the spokesperson claimed that the scheme reached 2 crore women across Tamil Nadu."
    )
    db_session.add_all([doc_speech_report, pass_speech_report])
    db_session.commit()

    claim = Claim(
        claim_id="CLM-TEST-STANCE-01",
        original_text="The scheme reached 2 crore women across Tamil Nadu.",
        normalized_text="the scheme reached 2 crore women across tamil nadu",
        claim_category=ClaimCategory.GOVERNMENT_SCHEMES
    )

    res = analyzer.analyze_claim_evidence_relationship(
        claim=claim,
        passage=pass_speech_report,
        document=doc_speech_report
    )

    assert res["source_stance"] == "REPORTING_CLAIM"
    assert res["relationship_type"] == EvidenceRelationshipType.CONTEXTUALIZES


# ---------------------------------------------------------------------------
# Test 8: Absence of Evidence Does Not Prove Falsehood
# ---------------------------------------------------------------------------
def test_8_absence_of_evidence_does_not_prove_falsehood(db_session):
    """
    Enforces core epistemic principle:
    Absence of a document is NEVER classified as refuting the claim.
    """
    claim = Claim(
        claim_id="CLM-TEST-ABSENCE-01",
        original_text="Village library built in Melur in 1985.",
        normalized_text="village library built in melur in 1985",
        claim_category=ClaimCategory.POLITICAL_PROMISES
    )

    eval_result = EvidenceRelationshipAnalyzer.evaluate_absence_of_evidence(
        claim=claim,
        retrieved_candidates_count=0
    )

    assert eval_result["verdict"] == VerificationVerdict.UNVERIFIABLE_INSUFFICIENT_EVIDENCE
    assert eval_result["is_false"] is False
    assert "Absence of evidence does not constitute evidence of absence" in eval_result["disclaimer"]


# ---------------------------------------------------------------------------
# Test 9: Keeping Contradictory Evidence Visible
# ---------------------------------------------------------------------------
def test_9_keeping_contradictory_evidence_visible(db_session):
    """
    Verifies that contradictory evidence is persisted and retained in relationships list
    alongside supporting evidence.
    """
    analyzer = EvidenceRelationshipAnalyzer(db=db_session)

    claim = Claim(
        claim_id="CLM-TEST-VISIBILITY-01",
        original_text="Kalaignar Magalir Urimai Thittam in 2023-24.",
        normalized_text="kalaignar magalir urimai thittam in 2023-24",
        claim_category=ClaimCategory.GOVERNMENT_SCHEMES
    )
    db_session.add(claim)
    db_session.commit()

    # Link both supporting and contradictory passages
    pass_supp = db_session.query(EvidencePassage).filter_by(passage_id="EPASS-GO-49-01").first()
    pass_contra = db_session.query(EvidencePassage).filter_by(passage_id="EPASS-CAG-01").first()

    from backend.models.claim import ClaimRetrievalCandidate
    c1 = ClaimRetrievalCandidate(
        candidate_id="CAN-VIS-01",
        claim_id=claim.claim_id,
        evidence_document_id=pass_supp.document_id,
        evidence_passage_id=pass_supp.passage_id,
        retrieval_score=0.9
    )
    c2 = ClaimRetrievalCandidate(
        candidate_id="CAN-VIS-02",
        claim_id=claim.claim_id,
        evidence_document_id=pass_contra.document_id,
        evidence_passage_id=pass_contra.passage_id,
        retrieval_score=0.8,
        is_potentially_contradictory=True
    )
    db_session.add_all([c1, c2])
    db_session.commit()

    saved = analyzer.analyze_and_persist_relationships(claim_id=claim.claim_id)
    types = [s.relationship_type for s in saved]

    assert EvidenceRelationshipType.SUPPORTS in types
    assert EvidenceRelationshipType.CONTRADICTS in types
    # Ensure contradiction is preserved in DB
    contra_rel = next(s for s in saved if s.relationship_type == EvidenceRelationshipType.CONTRADICTS)
    assert contra_rel.contradicting_text_reference is not None


# ---------------------------------------------------------------------------
# Test 10: Multilingual Tamil Claim Relationship Analysis
# ---------------------------------------------------------------------------
def test_10_multilingual_tamil_claim_relationship(db_session):
    analyzer = EvidenceRelationshipAnalyzer(db=db_session)

    # Tamil claim text with exact original preservation
    claim = Claim(
        claim_id="CLM-TEST-TAMIL-REL-01",
        original_text="கலைஞர் மகளிர் உரிமைத் திட்டம் மூலம் மாதம் ₹1,000 வழங்கப்படுகிறது.",
        normalized_text="கலைஞர் மகளிர் உரிமைத் திட்டம் மூலம் மாதம் 1000 வழங்கப்படுகிறது",
        claim_category=ClaimCategory.GOVERNMENT_SCHEMES,
        language="ta"
    )
    atomic = AtomicClaim(
        atomic_claim_id="ACM-TEST-TAMIL-01",
        claim_id=claim.claim_id,
        atomic_claim_text="கலைஞர் மகளிர் உரிமைத் திட்டம் மூலம் மாதம் ₹1,000 வழங்கப்படுகிறது",
        language="ta",
        subject="மகளிர் உரிமைத் திட்டம்",
        numeric_value=1000.0,
        unit="rupees",
        denominator="per month"
    )

    passage = db_session.query(EvidencePassage).filter_by(passage_id="EPASS-GO-49-01").first()
    document = passage.document

    res = analyzer.analyze_claim_evidence_relationship(
        claim=claim,
        passage=passage,
        document=document,
        atomic_claim=atomic
    )

    assert res["relationship_type"] == EvidenceRelationshipType.SUPPORTS
    assert res["entity_alignment"] == "EXACT_MATCH"
    assert res["supporting_text_reference"] is not None


# ---------------------------------------------------------------------------
# Test 11: REST API Endpoints Integration
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
# Test 11: REST API Endpoints Integration
# ---------------------------------------------------------------------------
def test_11_rest_api_relationship_endpoints(api_client):
    claim_id = "CLM-API-REL-01"

    # 1. Ingest a test claim
    ingest_resp = api_client.post("/api/claims/ingest", json={
        "claim_id": claim_id,
        "original_text": "Kalaignar Magalir Urimai Thittam in Tamil Nadu.",
        "claim_category": "GOVERNMENT_SCHEMES",
        "candidate_source_type": "OFFICIAL_STATEMENT",
        "language": "en"
    })
    assert ingest_resp.status_code == 200

    # 2. Add an evidence document and passage to the database
    from backend.database.session import SessionLocal
    db = SessionLocal()
    try:
        doc = EvidenceDocument(
            document_id="EDOC-API-REL-01",
            source_tier=SourceTier.TIER_1_STATUTORY,
            source_name="Official GO Bulletin",
            publisher="Finance Department TN",
            document_type="GOVERNMENT_ORDER",
            source_category="OFFICIAL_GOVERNMENT",
            title="Kalaignar Magalir Urimai Thittam Guidelines",
            publication_date=datetime(2023, 8, 1, tzinfo=timezone.utc),
            file_hash_sha256="hash_api_rel_test_123",
            language="en"
        )
        db.add(doc)
        passage = EvidencePassage(
            passage_id="EPASS-API-REL-01",
            document_id="EDOC-API-REL-01",
            passage_text="Government Order G.O. (Ms) No. 49 sanctioned funds for Kalaignar Magalir Urimai Thittam.",
            page_number=1
        )
        db.add(passage)
        db.commit()
    finally:
        db.close()

    # 3. POST /api/claims/<claim_id>/analyze-evidence
    post_resp = api_client.post(f"/api/claims/{claim_id}/analyze-evidence", json={})
    assert post_resp.status_code == 200
    post_data = post_resp.get_json()
    assert post_data["status"] == "success"
    assert "relationships" in post_data["data"]
    assert "epistemic_disclaimer" in post_data["data"]

    # 4. GET /api/claims/<claim_id>/relationships
    get_resp = api_client.get(f"/api/claims/{claim_id}/relationships")
    assert get_resp.status_code == 200
    get_data = get_resp.get_json()
    assert get_data["status"] == "success"
    assert "total_relationships" in get_data["data"]
    assert len(get_data["data"]["relationships"]) >= 1
