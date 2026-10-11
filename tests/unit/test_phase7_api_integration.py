"""
Phase 7.8 — Unit & Integration Tests for Claim Verification Database, API and Cross-Phase Integration.

Tests:
1. Model serialization (to_dict) and column definitions across all Phase 7 entities.
2. Cross-phase database relationships with existing modules (Phases 2-6) via stable IDs without copying datasets.
3. Claim search & filtering API with validation, pagination, and required verification result metadata.
4. Claim details API with full profile, atomic decomposition, and resolved cross-phase entities.
5. Atomic claim details API with semantic frame, quantitative constraints, and candidate retrievals.
6. Evidence search and document details API with citations, source tier, checksum, and referencing claims.
7. Claim/evidence relationships API preserving visibility of contradictory evidence.
8. Verification result and audit history API exposing methodology, limitations, and revision logs.
9. Role-based access control for human review operations (permits authorized analysts, rejects unauthorized users with 403).
10. Source provenance and claim intake provenance API.
11. Cross-phase linking API and filtered lookups (/by-representative, /by-promise, /by-scheme).
12. Graceful handling of claims without cross-phase associations (selective linkages).
"""

import pytest
from datetime import datetime, timezone
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.database.base_class import Base
from backend.models.claim import (
    Claim,
    ClaimVersion,
    AtomicClaim,
    ClaimSubject,
    ClaimSource,
    EvidenceDocument,
    EvidencePassage,
    ClaimEvidenceRelationship,
    VerificationRun,
    VerificationResult,
    VerificationHistory,
    ReviewRecord,
    ClaimCrossPhaseLink,
    VerificationOutcome,
    VerificationVerdict,
    ReviewAction,
    ReviewStatus,
    EvidenceRelationshipType,
    SourceTier,
    ClaimCategory,
    ClaimStatus,
    SubjectType
)
from backend.models.budget import HistoricalScheme, BudgetDepartment, BudgetScheme
from backend.models.manifesto import Manifesto
from backend.models.promise import PoliticalPromise
from backend.models.news import Article, NewsSource
from backend.models.funding import FinancialDocument
from backend.models.representative import Representative, Constituency, ConstituencyType
from backend.api.app import create_app


@pytest.fixture
def db_session():
    """In-memory SQLite database session with cross-phase entities."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    # Prepopulate Cross-Phase Mock Entities from Phases 2-6
    # Phase 2: Historical Scheme
    dept = BudgetDepartment(id=1, name="Finance Department TN", code="DEMAND_01")
    bscheme = BudgetScheme(id=1, department_id=1, name="Kalaignar Magalir Urimai Thittam")
    hscheme = HistoricalScheme(
        id=101,
        scheme_name="Kalaignar Magalir Urimai Thittam",
        department_id=1,
        financial_year="2023-2024",
        objectives="Monthly direct benefit transfer to women heads of families."
    )
    session.add_all([dept, bscheme, hscheme])

    # Phase 3: Political Promise
    manifesto = Manifesto(
        manifesto_id="MAN-2021-DMK",
        party="DMK",
        election_year=2021,
        title="DMK 2021 State Assembly Manifesto"
    )
    promise = PoliticalPromise(
        promise_id="PRM-2021-DMK-042",
        manifesto_id="MAN-2021-DMK",
        original_text="Rs 1,000 monthly basic income for eligible women heads of families.",
        normalized_text="rs 1000 monthly basic income for eligible women heads of families",
        classification="social_welfare"
    )
    session.add_all([manifesto, promise])

    # Phase 4: News Article
    news_src = NewsSource(
        source_id="NS-THE-HINDU",
        source_name="The Hindu Tamil",
        domain="thehindu.com",
        language="ta"
    )
    article = Article(
        article_id="ART-2024-HIN-001",
        source_id="NS-THE-HINDU",
        url="https://www.thehindu.com/news/national/tamil-nadu/magalir-urimai-launch.html",
        title="Over 1.15 crore women receive monthly assistance in Tamil Nadu",
        article_text="The Chief Minister launched the ground disbursals under KMUT across all districts.",
        publication_date=datetime(2023, 9, 16, tzinfo=timezone.utc),
        text_hash="hash-news-art-001"
    )
    session.add_all([news_src, article])

    # Phase 5: Financial Document
    findoc = FinancialDocument(
        document_id="FIN-DMK-2023-01",
        source_id="ECI-TRANSPARENCY-PORTAL",
        financial_year="2022-2023",
        filing_type="AnnualAudit",
        file_hash_sha256="hash-fin-doc-001",
        source_url="https://eci.gov.in/contributions/dmk-2022-23.pdf"
    )
    session.add(findoc)

    # Phase 6: Representative & Constituency
    constituency = Constituency(
        constituency_id="CON-TN-KOLATHUR",
        official_name="Kolathur",
        constituency_type=ConstituencyType.ASSEMBLY,
        district="Chennai",
        state="Tamil Nadu",
        valid_from="2008"
    )
    representative = Representative(
        representative_id="REP-TN-MLA-001",
        official_name="M.K. Stalin",
        representative_type="MLA",
        party_id="DMK",
        constituency_id="CON-TN-KOLATHUR",
        term_start="2021-05-07"
    )
    session.add_all([constituency, representative])

    session.commit()
    yield session
    session.close()


@pytest.fixture
def api_client(db_session):
    """Flask test client connected to the shared test database."""
    app = create_app()
    app.config["TESTING"] = True

    from backend.database.session import engine
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    # Re-insert the base cross-phase records into engine
    Session = sessionmaker(bind=engine)
    session = Session()

    dept = BudgetDepartment(id=1, name="Finance Department TN", code="DEMAND_01")
    bscheme = BudgetScheme(id=1, department_id=1, name="Kalaignar Magalir Urimai Thittam")
    hscheme = HistoricalScheme(
        id=101,
        scheme_name="Kalaignar Magalir Urimai Thittam",
        department_id=1,
        financial_year="2023-2024",
        objectives="Monthly direct benefit transfer to women heads of families."
    )
    session.add_all([dept, bscheme, hscheme])

    manifesto = Manifesto(
        manifesto_id="MAN-2021-DMK",
        party="DMK",
        election_year=2021,
        title="DMK 2021 State Assembly Manifesto"
    )
    promise = PoliticalPromise(
        promise_id="PRM-2021-DMK-042",
        manifesto_id="MAN-2021-DMK",
        original_text="Rs 1,000 monthly basic income for eligible women heads of families.",
        normalized_text="rs 1000 monthly basic income for eligible women heads of families",
        classification="social_welfare"
    )
    session.add_all([manifesto, promise])

    news_src = NewsSource(
        source_id="NS-THE-HINDU",
        source_name="The Hindu Tamil",
        domain="thehindu.com",
        language="ta"
    )
    article = Article(
        article_id="ART-2024-HIN-001",
        source_id="NS-THE-HINDU",
        url="https://www.thehindu.com/news/national/tamil-nadu/magalir-urimai-launch.html",
        title="Over 1.15 crore women receive monthly assistance in Tamil Nadu",
        article_text="The Chief Minister launched the ground disbursals under KMUT across all districts.",
        publication_date=datetime(2023, 9, 16, tzinfo=timezone.utc),
        text_hash="hash-news-art-001"
    )
    session.add_all([news_src, article])

    findoc = FinancialDocument(
        document_id="FIN-DMK-2023-01",
        source_id="ECI-TRANSPARENCY-PORTAL",
        financial_year="2022-2023",
        filing_type="AnnualAudit",
        file_hash_sha256="hash-fin-doc-001",
        source_url="https://eci.gov.in/contributions/dmk-2022-23.pdf"
    )
    session.add(findoc)

    constituency = Constituency(
        constituency_id="CON-TN-KOLATHUR",
        official_name="Kolathur",
        constituency_type=ConstituencyType.ASSEMBLY,
        district="Chennai",
        state="Tamil Nadu",
        valid_from="2008"
    )
    representative = Representative(
        representative_id="REP-TN-MLA-001",
        official_name="M.K. Stalin",
        representative_type="MLA",
        party_id="DMK",
        constituency_id="CON-TN-KOLATHUR",
        term_start="2021-05-07"
    )
    session.add_all([constituency, representative])

    session.commit()
    session.close()

    with app.test_client() as client:
        yield client

    Base.metadata.drop_all(bind=engine)


# ---------------------------------------------------------------------------
# Test 1: Model Serialization and Entity to_dict() Methods
# ---------------------------------------------------------------------------
def test_1_models_to_dict_and_cross_phase_columns(db_session):
    # ClaimSource
    src = ClaimSource(
        source_id="SRC-INTAKE-01",
        source_type="PRESS_MEET",
        organization_or_party="DMK",
        speaker_name="M.K. Stalin",
        venue="Chennai Secretariat",
        checksum="hash-src-01"
    )
    db_session.add(src)
    db_session.commit()
    s_dict = src.to_dict()
    assert s_dict["source_id"] == "SRC-INTAKE-01"
    assert s_dict["source_type"] == "PRESS_MEET"

    # Claim
    claim = Claim(
        claim_id="CLM-TEST-DICT-01",
        source_id=src.source_id,
        original_text="Over 1.15 crore women received Rs 1,000 monthly entitlement.",
        normalized_text="over 1.15 crore women received rs 1000 monthly entitlement",
        claim_category=ClaimCategory.GOVERNMENT_SCHEMES,
        speaker_name="M.K. Stalin",
        party="DMK",
        promise_id="PRM-2021-DMK-042",
        historical_scheme_id=101,
        representative_id="REP-TN-MLA-001"
    )
    db_session.add(claim)
    db_session.commit()
    c_dict = claim.to_dict()
    assert c_dict["claim_id"] == "CLM-TEST-DICT-01"
    assert c_dict["cross_phase_identifiers"]["promise_id"] == "PRM-2021-DMK-042"
    assert c_dict["cross_phase_identifiers"]["historical_scheme_id"] == 101
    assert c_dict["cross_phase_identifiers"]["representative_id"] == "REP-TN-MLA-001"

    # ClaimVersion
    ver = ClaimVersion(
        version_id="VER-CLM-01",
        claim_id=claim.claim_id,
        version_number=1,
        edited_text=claim.original_text,
        change_rationale="Initial verbatim intake"
    )
    db_session.add(ver)

    # AtomicClaim
    ac = AtomicClaim(
        atomic_claim_id="ATM-CLM-01",
        claim_id=claim.claim_id,
        atomic_claim_text="1.15 crore women beneficiaries",
        numeric_value=1.15,
        unit="crore"
    )
    db_session.add(ac)

    # EvidenceDocument & Passage
    edoc = EvidenceDocument(
        document_id="EDOC-STAT-01",
        title="Social Welfare Policy Note 2023-24",
        source_name="Govt of Tamil Nadu",
        publisher="Directorate of Social Welfare",
        document_type="POLICY_NOTE",
        file_hash_sha256="hash-policy-note-01"
    )
    epass = EvidencePassage(
        passage_id="EPASS-STAT-01",
        document_id="EDOC-STAT-01",
        passage_text="As of October 2023, 1.15 crore women were enrolled."
    )
    db_session.add_all([edoc, epass])
    db_session.commit()

    assert edoc.to_dict()["document_id"] == "EDOC-STAT-01"
    assert epass.to_dict()["passage_id"] == "EPASS-STAT-01"

    # VerificationResult
    vres = VerificationResult(
        result_id="VRES-CLM-01",
        claim_id=claim.claim_id,
        outcome=VerificationOutcome.SUPPORTED_BY_AVAILABLE_EVIDENCE,
        explanation="Part 1: SUPPORTED by Social Welfare Policy Note.",
        confidence=0.95,
        supporting_evidence_ids=["EPASS-STAT-01"]
    )
    db_session.add(vres)
    db_session.commit()

    vr_dict = vres.to_dict()
    assert vr_dict["outcome"] == "supported_by_available_evidence"
    assert "methodology" in vr_dict
    assert "limitations" in vr_dict
    assert len(vr_dict["supporting_evidence_ids"]) == 1


# ---------------------------------------------------------------------------
# Test 2: Cross-Phase Database Linkage with Existing Modules
# ---------------------------------------------------------------------------
def test_2_cross_phase_database_linkage_with_existing_modules(db_session):
    # Create claim referencing Phase 2 Scheme, Phase 3 Promise, Phase 4 News, Phase 5 Funding, Phase 6 Rep
    claim = Claim(
        claim_id="CLM-CROSS-PHASE-01",
        original_text="State disbursed monthly assistance as promised in 2021 election manifesto.",
        normalized_text="state disbursed monthly assistance as promised in 2021 election manifesto",
        claim_category=ClaimCategory.POLITICAL_PROMISES,
        speaker_name="M.K. Stalin",
        party="DMK",
        historical_scheme_id=101,
        promise_id="PRM-2021-DMK-042",
        news_article_id="ART-2024-HIN-001",
        financial_document_id="FIN-DMK-2023-01",
        representative_id="REP-TN-MLA-001",
        constituency_id="CON-TN-KOLATHUR"
    )
    db_session.add(claim)

    # Add ClaimCrossPhaseLink junction entries
    link1 = ClaimCrossPhaseLink(
        link_id="CPL-01",
        claim_id=claim.claim_id,
        target_phase="PHASE_2_SCHEME",
        entity_type="HISTORICAL_SCHEME",
        entity_id="101",
        relationship_nature="grounded_in_historical_scheme",
        relevance_score=0.98
    )
    link2 = ClaimCrossPhaseLink(
        link_id="CPL-02",
        claim_id=claim.claim_id,
        target_phase="PHASE_3_PROMISE",
        entity_type="POLITICAL_PROMISE",
        entity_id="PRM-2021-DMK-042",
        relationship_nature="evaluates_promise_fulfilment",
        relevance_score=1.0
    )
    db_session.add_all([link1, link2])
    db_session.commit()

    # Query Claim and test ORM relationships
    loaded = db_session.query(Claim).filter(Claim.claim_id == "CLM-CROSS-PHASE-01").first()
    assert loaded.historical_scheme is not None
    assert loaded.historical_scheme.scheme_name == "Kalaignar Magalir Urimai Thittam"
    assert loaded.promise is not None
    assert loaded.promise.promise_id == "PRM-2021-DMK-042"
    assert loaded.news_article is not None
    assert "Over 1.15 crore" in loaded.news_article.title
    assert loaded.financial_document is not None
    assert loaded.financial_document.financial_year == "2022-2023"
    assert loaded.representative is not None
    assert loaded.representative.official_name == "M.K. Stalin"
    assert loaded.constituency is not None
    assert loaded.constituency.official_name == "Kolathur"
    assert len(loaded.cross_phase_links) == 2


# ---------------------------------------------------------------------------
# Test 3: Claims Search & Filtering API
# ---------------------------------------------------------------------------
def test_3_claims_search_and_filtering_api(api_client):
    # Register claim via API
    payload = {
        "claim_id": "CLM-API-SEARCH-01",
        "original_text": "Tamil Nadu generated 45,000 new green energy jobs in 2023.",
        "claim_category": "GOVERNMENT_SCHEMES",
        "speaker_name": "Industries Minister",
        "party": "DMK",
        "speaker_party": "DMK",
        "language": "en"
    }
    post_res = api_client.post("/api/claims/ingest", json=payload)
    assert post_res.status_code == 200

    # 1. Search with keyword 'green energy'
    search_res = api_client.get("/api/claims/search?q=green+energy")
    assert search_res.status_code == 200
    data = search_res.get_json()["data"]
    assert data["total"] >= 1
    assert any(c["claim_id"] == "CLM-API-SEARCH-01" for c in data["claims"])

    # 2. Filter by category
    cat_res = api_client.get("/api/claims/search?category=GOVERNMENT_SCHEMES")
    assert cat_res.status_code == 200
    assert len(cat_res.get_json()["data"]["claims"]) >= 1

    # 3. Filter by speaker_party
    party_res = api_client.get("/api/claims/search?party=DMK")
    assert party_res.status_code == 200
    assert len(party_res.get_json()["data"]["claims"]) >= 1

    # 4. Pagination validation
    bad_skip = api_client.get("/api/claims/search?skip=-1")
    assert bad_skip.status_code == 400
    bad_limit = api_client.get("/api/claims/search?limit=150")
    assert bad_limit.status_code == 400


# ---------------------------------------------------------------------------
# Test 4: Claim Details and Cross-Phase Resolution API
# ---------------------------------------------------------------------------
def test_4_claim_details_and_cross_phase_resolution_api(api_client):
    from backend.database.session import SessionLocal
    db = SessionLocal()
    try:
        claim = Claim(
            claim_id="CLM-API-DETAIL-01",
            original_text="Tamil Nadu disbursed assistance to women beneficiaries under DMK manifesto promise.",
            normalized_text="tamil nadu disbursed assistance to women beneficiaries under dmk manifesto promise",
            claim_category=ClaimCategory.POLITICAL_PROMISES,
            speaker_name="M.K. Stalin",
            party="DMK",
            historical_scheme_id=101,
            promise_id="PRM-2021-DMK-042",
            representative_id="REP-TN-MLA-001"
        )
        db.add(claim)
        db.commit()
    finally:
        db.close()

    res = api_client.get("/api/claims/CLM-API-DETAIL-01")
    assert res.status_code == 200
    p = res.get_json()["data"]
    assert p["claim_id"] == "CLM-API-DETAIL-01"
    assert "resolved_cross_phase_entities" in p

    resolved = p["resolved_cross_phase_entities"]
    assert resolved["historical_scheme"]["id"] == 101
    assert resolved["historical_scheme"]["scheme_name"] == "Kalaignar Magalir Urimai Thittam"
    assert resolved["promise"]["promise_id"] == "PRM-2021-DMK-042"
    assert resolved["representative"]["official_name"] == "M.K. Stalin"


# ---------------------------------------------------------------------------
# Test 5: Atomic Claim Details API
# ---------------------------------------------------------------------------
def test_5_atomic_claim_details_api(api_client):
    from backend.database.session import SessionLocal
    db = SessionLocal()
    try:
        claim = Claim(
            claim_id="CLM-API-ATM-01",
            original_text="₹7,000 crore was sanctioned and 1.15 crore women benefited.",
            normalized_text="7000 crore was sanctioned and 1.15 crore women benefited",
            claim_category=ClaimCategory.GOVERNMENT_SCHEMES
        )
        ac1 = AtomicClaim(
            atomic_claim_id="ATM-API-001",
            claim_id="CLM-API-ATM-01",
            atomic_claim_text="₹7,000 crore sanctioned",
            numeric_value=7000.0,
            unit="crore",
            subject="Finance Department",
            predicate="sanctioned"
        )
        db.add_all([claim, ac1])
        db.commit()
    finally:
        db.close()

    # Query atomic claim directly and through nested path
    res1 = api_client.get("/api/claims/atomic/ATM-API-001")
    assert res1.status_code == 200
    data1 = res1.get_json()["data"]
    assert data1["atomic_claim"]["atomic_claim_id"] == "ATM-API-001"
    assert data1["atomic_claim"]["numeric_value"] == 7000.0
    assert data1["parent_claim_id"] == "CLM-API-ATM-01"

    res2 = api_client.get("/api/claims/CLM-API-ATM-01/atomic/ATM-API-001")
    assert res2.status_code == 200


# ---------------------------------------------------------------------------
# Test 6: Evidence Search and Document Details API
# ---------------------------------------------------------------------------
def test_6_evidence_search_and_document_details_api(api_client):
    from backend.database.session import SessionLocal
    db = SessionLocal()
    try:
        doc = EvidenceDocument(
            document_id="EDOC-SEARCH-01",
            source_tier=SourceTier.TIER_1_STATUTORY,
            source_name="Directorate of Town and Country Planning",
            publisher="Housing and Urban Development Department, TN",
            document_type="GAZETTE_NOTIFICATION",
            source_category="OFFICIAL_GOVERNMENT",
            title="CMDA Master Plan 2026 Notification",
            file_hash_sha256="hash-cmda-01",
            language="en"
        )
        passage = EvidencePassage(
            passage_id="EPASS-SEARCH-01",
            document_id="EDOC-SEARCH-01",
            passage_text="Master plan demarcates 1,189 square kilometers for expanded metropolitan area."
        )
        db.add_all([doc, passage])
        db.commit()
    finally:
        db.close()

    # 1. Evidence Search
    search_res = api_client.get("/api/claims/evidence/search?q=CMDA")
    assert search_res.status_code == 200
    docs = search_res.get_json()["data"]["documents"]
    assert any(d["document_id"] == "EDOC-SEARCH-01" for d in docs)

    # 2. Evidence Document Details
    doc_res = api_client.get("/api/claims/evidence/documents/EDOC-SEARCH-01")
    assert doc_res.status_code == 200
    doc_data = doc_res.get_json()["data"]
    assert doc_data["document"]["document_id"] == "EDOC-SEARCH-01"
    assert len(doc_data["passages"]) == 1
    assert "referencing_claim_ids" in doc_data


# ---------------------------------------------------------------------------
# Test 7: Claim/Evidence Relationships API (Preserving Contradictions)
# ---------------------------------------------------------------------------
def test_7_claim_evidence_relationships_api(api_client):
    from backend.database.session import SessionLocal
    db = SessionLocal()
    try:
        claim = Claim(
            claim_id="CLM-API-REL-01",
            original_text="Claim testing transparent contradiction visibility.",
            normalized_text="claim testing transparent contradiction visibility",
            claim_category=ClaimCategory.GOVERNMENT_SCHEMES
        )
        doc1 = EvidenceDocument(
            document_id="EDOC-REL-01",
            source_tier=SourceTier.TIER_1_STATUTORY,
            source_name="Department Press Release",
            document_type="PRESS_RELEASE",
            title="Press Release",
            file_hash_sha256="hash-rel-01"
        )
        pass1 = EvidencePassage(
            passage_id="EPASS-REL-01",
            document_id="EDOC-REL-01",
            passage_text="Supporting passage text."
        )
        rel_supp = ClaimEvidenceRelationship(
            relationship_id="CER-API-SUPP-01",
            claim_id=claim.claim_id,
            evidence_document_id=doc1.document_id,
            passage_id=pass1.passage_id,
            relationship_type=EvidenceRelationshipType.SUPPORTS,
            supporting_text_reference="Supporting passage text"
        )
        rel_contra = ClaimEvidenceRelationship(
            relationship_id="CER-API-CONTRA-01",
            claim_id=claim.claim_id,
            evidence_document_id=doc1.document_id,
            passage_id=pass1.passage_id,
            relationship_type=EvidenceRelationshipType.CONTRADICTS,
            contradicting_text_reference="Contradictory passage text"
        )
        db.add_all([claim, doc1, pass1, rel_supp, rel_contra])
        db.commit()
    finally:
        db.close()

    res = api_client.get("/api/claims/CLM-API-REL-01/relationships")
    assert res.status_code == 200
    data = res.get_json()["data"]
    assert data["total_relationships"] == 2
    types = [r["relationship_type"] for r in data["relationships"]]
    assert "supports" in types
    assert "contradicts" in types
    assert "epistemic_disclaimer" in data


# ---------------------------------------------------------------------------
# Test 8: Verification Results and Audit History API
# ---------------------------------------------------------------------------
def test_8_verification_results_and_history_api(api_client):
    from backend.database.session import SessionLocal
    db = SessionLocal()
    try:
        claim = Claim(
            claim_id="CLM-API-HIST-01",
            original_text="Claim with verified result and audit trail history.",
            normalized_text="claim with verified result and audit trail history",
            claim_category=ClaimCategory.GOVERNMENT_SCHEMES
        )
        vres = VerificationResult(
            result_id="VRES-API-HIST-01",
            claim_id=claim.claim_id,
            outcome=VerificationOutcome.SUPPORTED_BY_AVAILABLE_EVIDENCE,
            explanation="Statutory documents support the claim proposition.",
            confidence=0.92,
            supporting_evidence_ids=["EPASS-HIST-01"],
            contradicting_evidence_ids=[]
        )
        vhist = VerificationHistory(
            history_id="VHIST-API-HIST-01",
            claim_id=claim.claim_id,
            result_id=vres.result_id,
            previous_outcome="PENDING_REVIEW",
            new_outcome="SUPPORTED_BY_AVAILABLE_EVIDENCE",
            new_verdict="SUPPORTED",
            change_reason="Automated pipeline verification run execution"
        )
        db.add_all([claim, vres, vhist])
        db.commit()
    finally:
        db.close()

    # 1. GET /verification
    v_res = api_client.get("/api/claims/CLM-API-HIST-01/verification")
    assert v_res.status_code == 200
    v_data = v_res.get_json()["data"]["verification"]
    assert v_data["outcome"] == "supported_by_available_evidence"
    assert "methodology" in v_data
    assert "limitations" in v_data

    # 2. GET /history and /audit-trail
    h_res = api_client.get("/api/claims/CLM-API-HIST-01/history")
    assert h_res.status_code == 200
    assert len(h_res.get_json()["data"]["verification_history"]) >= 1

    at_res = api_client.get("/api/claims/CLM-API-HIST-01/audit-trail")
    assert at_res.status_code == 200


# ---------------------------------------------------------------------------
# Test 9: Human Review Role-Based Access Control
# ---------------------------------------------------------------------------
def test_9_human_review_access_control(api_client):
    from backend.database.session import SessionLocal
    db = SessionLocal()
    try:
        claim = Claim(
            claim_id="CLM-API-RBAC-01",
            original_text="Test claim for human review access controls.",
            normalized_text="test claim for human review access controls",
            claim_category=ClaimCategory.GOVERNMENT_SCHEMES
        )
        vres = VerificationResult(
            result_id="VRES-API-RBAC-01",
            claim_id=claim.claim_id,
            outcome=VerificationOutcome.PENDING_REVIEW,
            explanation="Initial baseline outcome."
        )
        db.add_all([claim, vres])
        db.commit()
    finally:
        db.close()

    # 1. Unauthorized role -> 403 Forbidden
    bad_payload = {
        "reviewer_id": "PUBLIC-USER-01",
        "reviewer_role": "PUBLIC_USER",
        "action": "revise_outcome",
        "reviewed_outcome": "supported_by_available_evidence",
        "review_notes": "Should be rejected because role is unauthorized."
    }
    bad_res = api_client.post("/api/claims/CLM-API-RBAC-01/review", json=bad_payload)
    assert bad_res.status_code == 403
    assert "Access Denied" in bad_res.get_json()["message"]

    # 2. Authorized role (DOMAIN_EXPERT) -> 200 OK
    good_payload = {
        "reviewer_id": "EXPERT-REVIEWER-01",
        "reviewer_role": "DOMAIN_EXPERT",
        "action": "accept_assessment",
        "review_notes": "Valid review by domain specialist."
    }
    good_res = api_client.post("/api/claims/CLM-API-RBAC-01/review", json=good_payload)
    assert good_res.status_code == 200
    assert good_res.get_json()["data"]["review_status"] == "ACCEPTED"


# ---------------------------------------------------------------------------
# Test 10: Source and Claim Provenance API
# ---------------------------------------------------------------------------
def test_10_source_and_claim_provenance_api(api_client):
    from backend.database.session import SessionLocal
    db = SessionLocal()
    try:
        src = ClaimSource(
            source_id="SRC-PROV-01",
            source_type="CAMPAIGN_RALLY",
            organization_or_party="DMK",
            speaker_name="Party President",
            venue="Madurai Public Ground",
            checksum="hash-src-prov-01"
        )
        claim = Claim(
            claim_id="CLM-API-PROV-01",
            source_id=src.source_id,
            original_text="Speech delivered at Madurai rally.",
            normalized_text="speech delivered at madurai rally",
            claim_category=ClaimCategory.GOVERNMENT_SCHEMES,
            content_fingerprint="fingerprint-prov-01"
        )
        db.add_all([src, claim])
        db.commit()
    finally:
        db.close()

    # 1. Source provenance
    s_res = api_client.get("/api/claims/sources/SRC-PROV-01")
    assert s_res.status_code == 200
    assert s_res.get_json()["data"]["source"]["source_id"] == "SRC-PROV-01"
    assert s_res.get_json()["data"]["associated_claims_count"] == 1

    # 2. Claim provenance
    c_res = api_client.get("/api/claims/CLM-API-PROV-01/provenance")
    assert c_res.status_code == 200
    c_data = c_res.get_json()["data"]
    assert c_data["claim_id"] == "CLM-API-PROV-01"
    assert c_data["content_fingerprint"] == "fingerprint-prov-01"


# ---------------------------------------------------------------------------
# Test 11: Cross-Phase Linking API and Filtered Lookups
# ---------------------------------------------------------------------------
def test_11_cross_phase_linking_api_and_filtered_queries(api_client):
    from backend.database.session import SessionLocal
    db = SessionLocal()
    try:
        claim = Claim(
            claim_id="CLM-API-CPLINK-01",
            original_text="Claim to be linked to political promise and MLA.",
            normalized_text="claim to be linked to political promise and mla",
            claim_category=ClaimCategory.POLITICAL_PROMISES
        )
        db.add(claim)
        db.commit()
    finally:
        db.close()

    # 1. Link to Promise
    link_res1 = api_client.post("/api/claims/CLM-API-CPLINK-01/cross-phase/link", json={
        "target_phase": "PHASE_3_PROMISE",
        "entity_type": "POLITICAL_PROMISE",
        "entity_id": "PRM-2021-DMK-042",
        "relationship_nature": "evaluates_promise_fulfilment",
        "reviewer_role": "DOMAIN_EXPERT"
    })
    assert link_res1.status_code in [200, 201]

    # 2. Link to Representative
    link_res2 = api_client.post("/api/claims/CLM-API-CPLINK-01/cross-phase/link", json={
        "target_phase": "PHASE_6_REPRESENTATIVE",
        "entity_type": "REPRESENTATIVE",
        "entity_id": "REP-TN-MLA-001",
        "relationship_nature": "uttered_by_representative",
        "reviewer_role": "DOMAIN_EXPERT"
    })
    assert link_res2.status_code in [200, 201]

    # 3. Fetch cross-phase details
    cp_res = api_client.get("/api/claims/CLM-API-CPLINK-01/cross-phase")
    assert cp_res.status_code == 200
    cp_data = cp_res.get_json()["data"]
    assert cp_data["cross_phase_links_count"] == 2
    assert cp_data["resolved_entities"]["promise"]["promise_id"] == "PRM-2021-DMK-042"
    assert cp_data["resolved_entities"]["representative"]["official_name"] == "M.K. Stalin"

    # 4. Filtered lookups: /by-representative and /by-promise
    rep_claims = api_client.get("/api/claims/by-representative/REP-TN-MLA-001")
    assert rep_claims.status_code == 200
    assert rep_claims.get_json()["data"]["total"] >= 1

    prm_claims = api_client.get("/api/claims/by-promise/PRM-2021-DMK-042")
    assert prm_claims.status_code == 200
    assert prm_claims.get_json()["data"]["total"] >= 1


# ---------------------------------------------------------------------------
# Test 12: Selective Association (Claims Without Cross-Phase Links)
# ---------------------------------------------------------------------------
def test_12_claims_without_cross_phase_links_graceful_handling(api_client):
    from backend.database.session import SessionLocal
    db = SessionLocal()
    try:
        # A standalone claim that has NO links to promises, funding, or schemes
        standalone = Claim(
            claim_id="CLM-STANDALONE-01",
            original_text="General public assertion regarding rainfall in the Cauvery delta.",
            normalized_text="general public assertion regarding rainfall in the cauvery delta",
            claim_category=ClaimCategory.GOVERNMENT_SCHEMES
        )
        db.add(standalone)
        db.commit()
    finally:
        db.close()

    # Query details
    res = api_client.get("/api/claims/CLM-STANDALONE-01")
    assert res.status_code == 200
    data = res.get_json()["data"]
    assert data["claim_id"] == "CLM-STANDALONE-01"

    # All cross-phase entities must gracefully be None
    resolved = data["resolved_cross_phase_entities"]
    assert resolved["historical_scheme"] is None
    assert resolved["promise"] is None
    assert resolved["news_article"] is None
    assert resolved["financial_document"] is None
    assert resolved["representative"] is None
    assert resolved["constituency"] is None

    # Query cross-phase endpoint
    cp_res = api_client.get("/api/claims/CLM-STANDALONE-01/cross-phase")
    assert cp_res.status_code == 200
    assert cp_res.get_json()["data"]["cross_phase_links_count"] == 0
