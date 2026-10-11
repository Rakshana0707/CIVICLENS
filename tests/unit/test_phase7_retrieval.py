"""
Phase 7.5 — Unit Tests for Claim-to-Evidence Retrieval Engine.

Tests:
1. Exact phrase and keyword matching.
2. Paraphrased statement retrieval via semantic similarity.
3. Active retrieval and flagging of potentially contradictory evidence.
4. Cross-lingual Tamil claim retrieving English evidence documents.
5. Cross-lingual English claim retrieving Tamil evidence documents.
6. Irrelevant documents filtered below minimum relevance threshold.
7. Missing evidence handling (empty candidate list without error).
8. Provenance retention (11 required attributes) and truth-bias disclaimer.
9. REST API endpoint: POST /api/claims/<claim_id>/retrieve-evidence.
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
    ClaimRetrievalCandidate,
    ClaimCategory,
    ClaimStatus,
    SourceTier,
    CandidateSourceType,
    AttributionType
)
from backend.services.evidence_retrieval import (
    EvidenceRetrievalEngine,
    MultilingualSemanticScorer,
    KeywordAndPhraseMatcher,
    EntityAndDateMatcher,
    ContradictoryEvidenceDetector,
    RETRIEVAL_DISCLAIMER
)
from backend.api.app import create_app


@pytest.fixture
def db_session():
    """Isolated in-memory SQLite database session for retrieval tests."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    # Prepopulate standard test evidence documents and passages
    doc1 = EvidenceDocument(
        document_id="EDOC-TN-BUDGET-2024",
        source_tier=SourceTier.TIER_1_STATUTORY,
        source_name="Tamil Nadu Budget Speech 2024-25",
        publisher="Finance Department, Government of Tamil Nadu",
        document_type="BUDGET_DOCUMENT",
        source_category="SCHEME_BUDGET",
        title="Tamil Nadu State Budget Highlights 2024-25",
        publication_date=datetime(2024, 2, 19, tzinfo=timezone.utc),
        source_url="https://tnbudget.tn.gov.in/highlights.html",
        file_hash_sha256="hash_budget_2024_abc123",
        language="en",
        is_official=True,
        is_test_fixture=True
    )
    session.add(doc1)

    pass1 = EvidencePassage(
        passage_id="EPASS-BUDGET-01",
        document_id="EDOC-TN-BUDGET-2024",
        passage_text="The total outlay for Kalaignar Magalir Urimai Thittam is allocated at Rs 13,720 crore in 2024-25.",
        page_number=12,
        section_or_table="Demands for Grants"
    )
    pass2 = EvidencePassage(
        passage_id="EPASS-BUDGET-02",
        document_id="EDOC-TN-BUDGET-2024",
        passage_text="Fiscal deficit is estimated at 3.44 percent of GSDP in the revised budget estimates.",
        page_number=15,
        section_or_table="Fiscal Overview"
    )
    session.add_all([pass1, pass2])

    # Doc 2: CAG Audit Report (Contradictory / Critical counter-evidence)
    doc2 = EvidenceDocument(
        document_id="EDOC-CAG-AUDIT-2024",
        source_tier=SourceTier.TIER_1_STATUTORY,
        source_name="CAG Audit Report on Social Welfare",
        publisher="Comptroller & Auditor General of India",
        document_type="AUDIT_REPORT",
        source_category="SCHEME_BUDGET",
        title="CAG Performance Audit of Direct Benefit Transfers",
        publication_date=datetime(2024, 3, 10, tzinfo=timezone.utc),
        source_url="https://cag.gov.in/reports/tn_welfare.html",
        file_hash_sha256="hash_cag_audit_xyz789",
        language="en",
        is_official=True,
        is_test_fixture=True
    )
    session.add(doc2)

    pass3 = EvidencePassage(
        passage_id="EPASS-CAG-01",
        document_id="EDOC-CAG-AUDIT-2024",
        passage_text="CAG audit reveals shortfall and delayed disbursements under Kalaignar Magalir Urimai Thittam affecting 3 lakh eligible applicants.",
        page_number=45,
        section_or_table="Audit Paragraph 4.2"
    )
    session.add(pass3)

    # Doc 3: Tamil Legislative Order (Tamil language evidence)
    doc3 = EvidenceDocument(
        document_id="EDOC-TN-GO-BUSES",
        source_tier=SourceTier.TIER_1_STATUTORY,
        source_name="Transport Department Government Order",
        publisher="Transport Department TN",
        document_type="GOVERNMENT_ORDER",
        source_category="OFFICIAL_GOVERNMENT",
        title="10,000 புதிய மின்சார பேருந்துகள் கொள்முதல் ஆணை",
        publication_date=datetime(2023, 11, 15, tzinfo=timezone.utc),
        source_url="https://tn.gov.in/go/transport_buses.html",
        file_hash_sha256="hash_tn_go_buses_456",
        language="ta",
        is_official=True,
        is_test_fixture=True
    )
    session.add(doc3)

    pass4 = EvidencePassage(
        passage_id="EPASS-BUSES-01",
        document_id="EDOC-TN-GO-BUSES",
        passage_text="தமிழகத்தில் 10,000 புதிய மின்சார பேருந்துகள் கொள்முதல் செய்ய நிதி ஒதுக்கீடு செய்யப்பட்டு அனுமதி வழங்கப்பட்டுள்ளது.",
        page_number=2,
        section_or_table="GO Order Section 1"
    )
    session.add(pass4)

    # Doc 4: Unrelated noise document (Tourism in Puducherry)
    doc4 = EvidenceDocument(
        document_id="EDOC-PUDU-TOURISM",
        source_tier=SourceTier.TIER_4_SECONDARY_CIVIC,
        source_name="Tourism Guide",
        publisher="Coastal Travel Ltd",
        document_type="TRAVEL_ARTICLE",
        source_category="PUBLIC_NEWS",
        title="Weekend Beaches in Pondicherry",
        publication_date=datetime(2022, 5, 1, tzinfo=timezone.utc),
        source_url="https://travelguide.internal/beaches.html",
        file_hash_sha256="hash_unrelated_travel_000",
        language="en",
        is_official=False,
        is_test_fixture=True
    )
    session.add(doc4)

    pass5 = EvidencePassage(
        passage_id="EPASS-TRAVEL-01",
        document_id="EDOC-PUDU-TOURISM",
        passage_text="Explore the French promenade and coastal seafood cafes on weekend trips.",
        page_number=1,
        section_or_table="Travel Guide"
    )
    session.add(pass5)

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


def test_1_exact_phrase_and_keyword_retrieval(db_session):
    """
    Verifies that an atomic claim with exact keywords and numbers retrieves the
    target statutory budget passage with high keyword and composite scores.
    """
    engine = EvidenceRetrievalEngine(db=db_session)
    claim_id = "CLM-TEST-EXACT-01"
    query = "Kalaignar Magalir Urimai Thittam allocated Rs 13,720 crore in 2024-25."

    results = engine.retrieve_candidate_evidence(
        claim_id=claim_id,
        query_text=query,
        time_period="2024-25",
        subject="Kalaignar Magalir Urimai Thittam",
        top_k=5
    )

    assert len(results) >= 1
    top = results[0]
    assert top["evidence_passage_id"] == "EPASS-BUDGET-01"
    assert top["evidence_document_id"] == "EDOC-TN-BUDGET-2024"
    assert top["keyword_match"] >= 0.70
    assert top["entity_match"] == 1.0
    assert top["date_match"] == 1.0
    assert top["retrieval_score"] >= 0.75
    assert "Rs 13,720 crore" in top["passage_text"]


def test_2_paraphrase_retrieval_via_semantic_similarity(db_session):
    """
    Verifies that a paraphrased claim lacking exact keyword phrasing still retrieves
    the correct statutory evidence via semantic similarity scoring.
    """
    engine = EvidenceRetrievalEngine(db=db_session)
    claim_id = "CLM-TEST-PARA-01"
    # Paraphrased wording: "set aside thirteen thousand crore for women financial assistance"
    paraphrase_query = "State government set aside thirteen thousand seven hundred crore for women assistance scheme in budget."

    results = engine.retrieve_candidate_evidence(
        claim_id=claim_id,
        query_text=paraphrase_query,
        subject="Kalaignar Magalir Urimai Thittam",
        top_k=5
    )

    assert len(results) >= 1
    # Should retrieve the budget or CAG passage
    passage_ids = [r["evidence_passage_id"] for r in results]
    assert "EPASS-BUDGET-01" in passage_ids
    matched = next(r for r in results if r["evidence_passage_id"] == "EPASS-BUDGET-01")
    assert matched["semantic_similarity"] > 0.15
    assert matched["retrieval_score"] >= 0.45


def test_3_contradictory_evidence_retrieval(db_session):
    """
    Verifies that the engine retrieves and flags counter-evidence (CAG audit shortfall report)
    alongside affirmative budget allocations.
    """
    engine = EvidenceRetrievalEngine(db=db_session)
    claim_id = "CLM-TEST-CONTRA-01"
    # Affirmative claim that everything was disbursed without issue
    affirmative_claim = "Kalaignar Magalir Urimai Thittam disbursed funds to all eligible women without any delay."

    results = engine.retrieve_candidate_evidence(
        claim_id=claim_id,
        query_text=affirmative_claim,
        subject="Kalaignar Magalir Urimai Thittam",
        is_negated=False,
        top_k=5
    )

    # Must retrieve both affirmative budget document and critical CAG audit report
    passage_ids = [r["evidence_passage_id"] for r in results]
    assert "EPASS-CAG-01" in passage_ids

    cag_result = next(r for r in results if r["evidence_passage_id"] == "EPASS-CAG-01")
    # Verify that contradictory signal is flagged
    assert cag_result["is_potentially_contradictory"] is True
    assert "CAG audit reveals shortfall and delayed disbursements" in cag_result["passage_text"]


def test_4_cross_lingual_tamil_to_english_retrieval(db_session):
    """
    Verifies cross-lingual retrieval: A Tamil claim finds the relevant English Budget document.
    """
    engine = EvidenceRetrievalEngine(db=db_session)
    claim_id = "CLM-TEST-TA2EN-01"
    tamil_query = "கலைஞர் மகளிர் உரிமைத் திட்டத்திற்கு ரூ.13,720 கோடி நிதி ஒதுக்கப்பட்டுள்ளது."
    aux_trans = "Kalaignar Magalir Urimai Thittam allocated 13720.0 crore"

    results = engine.retrieve_candidate_evidence(
        claim_id=claim_id,
        query_text=tamil_query,
        subject="Kalaignar Magalir Urimai Thittam",
        language="ta",
        auxiliary_translation=aux_trans,
        top_k=5
    )

    assert len(results) >= 1
    top = results[0]
    assert top["evidence_passage_id"] in ["EPASS-BUDGET-01", "EPASS-CAG-01"]
    assert top["retrieval_score"] >= 0.50


def test_5_cross_lingual_english_to_tamil_retrieval(db_session):
    """
    Verifies cross-lingual retrieval: An English claim finds the Tamil Government Order.
    """
    engine = EvidenceRetrievalEngine(db=db_session)
    claim_id = "CLM-TEST-EN2TA-01"
    english_query = "Government sanctioned 10,000 new electric buses in Tamil Nadu."

    results = engine.retrieve_candidate_evidence(
        claim_id=claim_id,
        query_text=english_query,
        top_k=5
    )

    assert len(results) >= 1
    bus_result = next((r for r in results if r["evidence_passage_id"] == "EPASS-BUSES-01"), None)
    assert bus_result is not None
    assert "10,000 புதிய மின்சார பேருந்துகள்" in bus_result["passage_text"]


def test_6_irrelevant_results_filtered_out(db_session):
    """
    Verifies that unrelated evidence (e.g. Puducherry beach tourism) scores below
    the minimum threshold (0.25) and is excluded from candidate results.
    """
    engine = EvidenceRetrievalEngine(db=db_session)
    claim_id = "CLM-TEST-FILTER-01"
    query = "Tamil Nadu fiscal deficit estimated at 3.44 percent of GSDP."

    results = engine.retrieve_candidate_evidence(
        claim_id=claim_id,
        query_text=query,
        min_score_threshold=0.25,
        top_k=10
    )

    retrieved_doc_ids = [r["evidence_document_id"] for r in results]
    # Fiscal passage should be retrieved
    assert "EDOC-TN-BUDGET-2024" in retrieved_doc_ids
    # Unrelated beach guide should NOT be retrieved
    assert "EDOC-PUDU-TOURISM" not in retrieved_doc_ids


def test_7_missing_evidence_handling(db_session):
    """
    Verifies that querying for an unknown / nonexistent claim returns an empty list
    cleanly without raising errors.
    """
    engine = EvidenceRetrievalEngine(db=db_session)
    claim_id = "CLM-TEST-EMPTY-01"
    nonexistent_query = "XYZ Scheme delivered 5 million flying cars across Mars colony."

    results = engine.retrieve_candidate_evidence(
        claim_id=claim_id,
        query_text=nonexistent_query,
        min_score_threshold=0.35,
        top_k=5
    )

    assert results == []


def test_8_stored_candidate_provenance_and_disclaimer(db_session):
    """
    Verifies that all 11 required fields are recorded in the database
    and that the explicit verification disclaimer is attached.
    """
    # Create parent Claim
    claim = Claim(
        claim_id="CLM-PROV-01",
        original_text="Outlay of Rs 13,720 crore for KMUT welfare scheme.",
        normalized_text="Outlay of Rs 13,720 crore for KMUT welfare scheme.",
        claim_category=ClaimCategory.BUDGET_EXPENDITURE,
        status=ClaimStatus.PENDING,
        language="en"
    )
    db_session.add(claim)
    db_session.commit()

    engine = EvidenceRetrievalEngine(db=db_session)
    results = engine.retrieve_candidate_evidence(
        claim_id=claim.claim_id,
        query_text=claim.original_text,
        subject="Kalaignar Magalir Urimai Thittam",
        persist_candidates=True
    )

    assert len(results) >= 1
    top = results[0]

    # Verify all 11 required fields
    assert "claim_id" in top
    assert "evidence_document_id" in top
    assert "evidence_passage_id" in top
    assert "retrieval_score" in top
    assert "semantic_similarity" in top
    assert "keyword_match" in top
    assert "entity_match" in top
    assert "date_match" in top
    assert "retrieval_method" in top
    assert "model_version" in top
    assert "retrieval_timestamp" in top

    # Verify disclaimer
    assert top["disclaimer"] == RETRIEVAL_DISCLAIMER
    assert "Do not interpret retrieval rank as evidence of truth" in top["disclaimer"]

    # Verify database persistence into claim_retrieval_candidates
    db_cands = db_session.query(ClaimRetrievalCandidate).filter(
        ClaimRetrievalCandidate.claim_id == claim.claim_id
    ).all()
    assert len(db_cands) >= 1
    cand_row = db_cands[0]
    assert cand_row.retrieval_score > 0.0
    assert cand_row.retrieval_method == "HYBRID_MULTI_SIGNAL_V1"
    assert cand_row.rank == 1


def test_9_rest_api_retrieve_evidence_endpoint(api_client):
    """
    Verifies REST API endpoint: POST /api/claims/<claim_id>/retrieve-evidence.
    """
    # 1. Ingest a claim
    ingest_resp = api_client.post("/api/claims/ingest", json={
        "claim_id": "CLM-API-RET-01",
        "original_text": "Tamil Nadu budget allocated Rs 13,720 crore for Kalaignar Magalir Urimai Thittam.",
        "claim_category": "GOVERNMENT_SCHEMES",
        "candidate_source_type": "OFFICIAL_STATEMENT",
        "language": "en"
    })
    assert ingest_resp.status_code == 200

    # 2. Add an evidence document and passage to the API's database
    from backend.database.session import SessionLocal
    db = SessionLocal()
    try:
        doc = EvidenceDocument(
            document_id="EDOC-API-TEST-01",
            source_tier=SourceTier.TIER_1_STATUTORY,
            source_name="Official Budget Bulletin",
            publisher="Finance Department",
            document_type="BUDGET_DOCUMENT",
            source_category="SCHEME_BUDGET",
            title="State Budget Highlights",
            publication_date=datetime(2024, 2, 19, tzinfo=timezone.utc),
            file_hash_sha256="hash_api_test_123",
            language="en"
        )
        db.add(doc)
        passage = EvidencePassage(
            passage_id="EPASS-API-TEST-01",
            document_id="EDOC-API-TEST-01",
            passage_text="Allocation of Rs 13,720 crore for Kalaignar Magalir Urimai Thittam finalized.",
            page_number=1
        )
        db.add(passage)
        db.commit()
    finally:
        db.close()

    # 3. Call retrieval endpoint
    ret_resp = api_client.post("/api/claims/CLM-API-RET-01/retrieve-evidence", json={
        "top_k": 5,
        "min_score_threshold": 0.20
    })
    assert ret_resp.status_code == 200
    ret_json = ret_resp.get_json()["data"]
    assert ret_json["claim_id"] == "CLM-API-RET-01"
    assert ret_json["candidates_count"] >= 1
    candidates = ret_json["candidates"]
    assert candidates[0]["evidence_passage_id"] == "EPASS-API-TEST-01"
    assert candidates[0]["retrieval_score"] >= 0.70
    assert "disclaimer" in candidates[0]
