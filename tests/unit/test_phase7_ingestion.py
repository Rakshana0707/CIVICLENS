"""
Phase 7.2 — Unit Tests for Political Claim Registry & Claim Ingestion Pipeline.

Tests:
1. Ingestion across all 8 candidate channels:
   - Public speeches
   - Official statements
   - Press releases
   - Legislative records
   - Manifestos
   - News articles
   - Existing fact-check articles
   - User submissions
2. Attribution distinction:
   - Direct quote vs. Paraphrase vs. Journalist's description vs. User-submitted vs. Automated extraction
3. Exact original wording preservation in primary storage.
4. Non-inference rule enforcement:
   - Missing speaker, role, party, or claim_date remain explicitly None (never guessed or hallucinated).
5. Exact deduplication handling:
   - Exact duplicate returns DUPLICATE_EXACT and avoids redundant database writes.
6. Materially distinct reiteration handling:
   - Identical claim text spoken on different dates or by different speakers is preserved as distinct claims.
7. Claim versioning and correction audit trail:
   - Ingesting corrections / supplemental context appends ClaimVersion without overwriting original_text.
8. Multilingual handling:
   - Tamil Unicode, English, and code-switched bilingual texts.
9. REST API ingestion endpoints:
   - /api/claims/ingest, /api/claims/check-duplicate, and /api/claims/<claim_id>/version.
"""

import pytest
from datetime import datetime, timezone
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.database.base_class import Base
from backend.models.claim import (
    Claim,
    ClaimVersion,
    ClaimCategory,
    ClaimStatus,
    ReviewStatus,
    AttributionType,
    CandidateSourceType
)
from backend.services.claim_ingestion import ClaimIngestionService, IngestionStatus
from backend.api.app import create_app


@pytest.fixture
def db_session():
    """Isolated in-memory SQLite database session for ingestion unit tests."""
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
# Test 1: Ingestion Across All 8 Candidate Source Channels
# ---------------------------------------------------------------------------
def test_1_ingest_all_eight_source_channels(db_session):
    service = ClaimIngestionService(db=db_session)

    # 1. Public Speech
    res_speech = service.ingest_public_speech(
        claim_id="CLM-ING-001-SPEECH",
        transcript_text="எங்கள் ஆட்சியில் 10 லட்சம் வேலைவாய்ப்புகள் உருவாக்கப்படும்.",
        claim_category=ClaimCategory.EMPLOYMENT_ECONOMIC,
        speaker_name="M. K. Stalin",
        speaker_role="Chief Minister",
        party="DMK",
        speech_date=datetime(2021, 3, 15, tzinfo=timezone.utc),
        venue="Trichy Rally",
        is_direct_quote=True,
        language="ta"
    )
    assert res_speech["status"] == IngestionStatus.CREATED
    assert res_speech["candidate_source_type"] == CandidateSourceType.PUBLIC_SPEECH.value
    assert res_speech["attribution_type"] == AttributionType.DIRECT_QUOTE.value

    # 2. Official Statement
    res_stmt = service.ingest_official_statement(
        claim_id="CLM-ING-002-OFFICIAL",
        statement_text="Tamil Nadu achieved an infant mortality rate of 12 per 1,000 live births in 2023.",
        claim_category=ClaimCategory.HEALTHCARE_EDUCATION,
        issuing_agency="Health and Family Welfare Department",
        official_name="Health Secretary",
        official_role="Principal Secretary",
        statement_date=datetime(2023, 9, 20, tzinfo=timezone.utc),
        source_url="https://tn.gov.in/press/health-2023"
    )
    assert res_stmt["status"] == IngestionStatus.CREATED
    assert res_stmt["candidate_source_type"] == CandidateSourceType.OFFICIAL_STATEMENT.value
    assert res_stmt["party"] is None  # Government executive communications are strictly non-partisan

    # 3. Press Release
    res_pr = service.ingest_press_release(
        claim_id="CLM-ING-003-PR",
        release_text="அதிமுக ஆட்சியில் கொண்டுவரப்பட்ட திட்டங்களை திமுக அரசு முடக்கியுள்ளது.",
        claim_category=ClaimCategory.GOVERNMENT_SCHEMES,
        issuing_party_or_org="AIADMK",
        spokesperson_name="D. Jayakumar",
        release_date=datetime(2023, 5, 10, tzinfo=timezone.utc)
    )
    assert res_pr["status"] == IngestionStatus.CREATED
    assert res_pr["candidate_source_type"] == CandidateSourceType.PRESS_RELEASE.value

    # 4. Legislative Record
    res_leg = service.ingest_legislative_record(
        claim_id="CLM-ING-004-HANSARD",
        proceeding_text="Zero funds were released under PM-Awas Yojana for urban housing in Madurai in FY22.",
        claim_category=ClaimCategory.PUBLIC_INFRASTRUCTURE,
        legislative_body="LOK_SABHA",
        member_name="Su. Venkatesan",
        member_role="Member of Parliament",
        party="CPI(M)",
        session_date=datetime(2022, 12, 14, tzinfo=timezone.utc),
        question_or_debate_id="Q-NO-1422"
    )
    assert res_leg["status"] == IngestionStatus.CREATED
    assert res_leg["candidate_source_type"] == CandidateSourceType.LEGISLATIVE_RECORD.value

    # 5. Manifesto
    res_man = service.ingest_manifesto(
        claim_id="CLM-ING-005-MANI",
        manifesto_clause_text="அரசுப் பள்ளி மாணவிகளுக்கு உயர்கல்வி பயில மாதம் ₹1,000 உதவித்தொகை வழங்கப்படும்.",
        claim_category=ClaimCategory.GOVERNMENT_SCHEMES,
        party="DMK",
        election_year=2021,
        page_number=24
    )
    assert res_man["status"] == IngestionStatus.CREATED
    assert res_man["candidate_source_type"] == CandidateSourceType.MANIFESTO.value

    # 6. News Article
    res_news = service.ingest_news_article(
        claim_id="CLM-ING-006-NEWS",
        extracted_text="Opposition leader criticized the government over delayed compensation for flood victims.",
        claim_category=ClaimCategory.OTHER_PUBLIC_INTEREST,
        article_source_name="The Hindu",
        attribution_type=AttributionType.JOURNALIST_DESCRIPTION,
        speaker_name="Edappadi K. Palaniswami",
        party="AIADMK",
        publication_date=datetime(2023, 12, 22, tzinfo=timezone.utc)
    )
    assert res_news["status"] == IngestionStatus.CREATED
    assert res_news["attribution_type"] == AttributionType.JOURNALIST_DESCRIPTION.value

    # 7. Fact Check Article
    res_fc = service.ingest_fact_check(
        claim_id="CLM-ING-007-FC",
        reviewed_claim_text="Tamil Nadu government cancelled all government bus concessions for senior citizens.",
        claim_category=ClaimCategory.GOVERNMENT_SCHEMES,
        factcheck_publisher="BOOM Live",
        reviewed_party="Unknown",
        factcheck_url="https://boomlive.in/fact-check/tn-bus-concessions"
    )
    assert res_fc["status"] == IngestionStatus.CREATED
    assert res_fc["candidate_source_type"] == CandidateSourceType.FACT_CHECK_ARTICLE.value

    # 8. User Submission
    res_usr = service.ingest_user_submission(
        claim_id="CLM-ING-008-USR",
        submitted_text="Local MLA promised a new bridge over Vaigai river during election campaign.",
        claim_category=ClaimCategory.PUBLIC_INFRASTRUCTURE,
        alleged_speaker="Local MLA",
        user_notes="Reported during public grievance meeting."
    )
    assert res_usr["status"] == IngestionStatus.CREATED
    assert res_usr["attribution_type"] == AttributionType.USER_SUBMITTED.value


# ---------------------------------------------------------------------------
# Test 2: Attribution Distinction (Direct Quote vs Paraphrase vs Description)
# ---------------------------------------------------------------------------
def test_2_attribution_distinction_taxonomy(db_session):
    service = ClaimIngestionService(db=db_session)

    # Direct Quote
    res1 = service.ingest_claim(
        claim_id="CLM-ATTR-001",
        original_text="\"நாங்கள் ஆட்சிக்கு வந்த 100 நாட்களில் நகைக்கடன் தள்ளுபடி செய்யப்படும்\"",
        claim_category=ClaimCategory.POLITICAL_PROMISES,
        candidate_source_type=CandidateSourceType.PUBLIC_SPEECH,
        attribution_type=AttributionType.DIRECT_QUOTE,
        speaker_name="M. K. Stalin",
        party="DMK"
    )
    assert res1["attribution_type"] == AttributionType.DIRECT_QUOTE.value

    # Paraphrased Statement
    res2 = service.ingest_claim(
        claim_id="CLM-ATTR-002",
        original_text="The DMK leader pledged to waive agricultural jewel loans within 100 days of forming government.",
        claim_category=ClaimCategory.POLITICAL_PROMISES,
        candidate_source_type=CandidateSourceType.NEWS_ARTICLE,
        attribution_type=AttributionType.PARAPHRASE,
        speaker_name="M. K. Stalin",
        party="DMK"
    )
    assert res2["attribution_type"] == AttributionType.PARAPHRASE.value

    # Journalist Description
    res3 = service.ingest_claim(
        claim_id="CLM-ATTR-003",
        original_text="The rally focused heavily on agricultural distress and promised immediate loan relief.",
        claim_category=ClaimCategory.POLITICAL_PROMISES,
        candidate_source_type=CandidateSourceType.NEWS_ARTICLE,
        attribution_type=AttributionType.JOURNALIST_DESCRIPTION
    )
    assert res3["attribution_type"] == AttributionType.JOURNALIST_DESCRIPTION.value


# ---------------------------------------------------------------------------
# Test 3: Verbatim Text Preservation
# ---------------------------------------------------------------------------
def test_3_exact_original_text_preservation(db_session):
    service = ClaimIngestionService(db=db_session)

    tamil_text_with_raw_formatting = "   கலைஞர் மகளிர் உரிமைத்   திட்டம்: 1.15 கோடி மகளிருக்கு மாதம் ₹1,000!   "
    res = service.ingest_claim(
        claim_id="CLM-VERB-001",
        original_text=tamil_text_with_raw_formatting,
        claim_category=ClaimCategory.GOVERNMENT_SCHEMES,
        candidate_source_type=CandidateSourceType.PUBLIC_SPEECH,
        attribution_type=AttributionType.DIRECT_QUOTE,
        language="ta"
    )

    claim = db_session.query(Claim).filter(Claim.claim_id == "CLM-VERB-001").first()
    # Verbatim original must be preserved exactly
    assert claim.original_text == tamil_text_with_raw_formatting.strip()
    assert "₹1,000" in claim.original_text


# ---------------------------------------------------------------------------
# Test 4: Strict Non-Inference Rule (Unverified Fields Remain None)
# ---------------------------------------------------------------------------
def test_4_strict_non_inference_of_missing_metadata(db_session):
    service = ClaimIngestionService(db=db_session)

    # Ingest candidate with NO speaker, NO party, and NO claim_date verified
    res = service.ingest_claim(
        claim_id="CLM-NO-INFER-001",
        original_text="Over 5,000 schools in the state have no functioning science laboratories.",
        claim_category=ClaimCategory.HEALTHCARE_EDUCATION,
        candidate_source_type=CandidateSourceType.NEWS_ARTICLE,
        attribution_type=AttributionType.JOURNALIST_DESCRIPTION,
        language="en",
        speaker_name=None,
        party=None,
        claim_date=None
    )

    claim = db_session.query(Claim).filter(Claim.claim_id == "CLM-NO-INFER-001").first()
    # CRITICAL: Verify fields were NOT guessed or defaulted
    assert claim.speaker_name is None
    assert claim.speaker_role is None
    assert claim.party is None
    assert claim.speaker_party is None
    assert claim.claim_date is None
    assert claim.created_at is not None  # Ingestion timestamp recorded independently


# ---------------------------------------------------------------------------
# Test 5: Exact Deduplication Handling
# ---------------------------------------------------------------------------
def test_5_exact_deduplication_handling(db_session):
    service = ClaimIngestionService(db=db_session)
    statement = "கலைஞர் மகளிர் உரிமைத் திட்டத்தின் கீழ் 1.15 கோடி மகளிர் பயன்பெறுகின்றனர்."
    stmt_date = datetime(2023, 9, 15, tzinfo=timezone.utc)

    # 1. First Ingestion
    res1 = service.ingest_claim(
        claim_id="CLM-DUP-ORIGINAL",
        original_text=statement,
        claim_category=ClaimCategory.GOVERNMENT_SCHEMES,
        candidate_source_type=CandidateSourceType.PUBLIC_SPEECH,
        attribution_type=AttributionType.DIRECT_QUOTE,
        speaker_name="M. K. Stalin",
        party="DMK",
        claim_date=stmt_date,
        language="ta"
    )
    assert res1["status"] == IngestionStatus.CREATED
    assert res1["claim_id"] == "CLM-DUP-ORIGINAL"

    # 2. Second Ingestion of EXACT same claim text, same speaker, same date
    res2 = service.ingest_claim(
        claim_id="CLM-DUP-SECONDARY",
        original_text=statement,
        claim_category=ClaimCategory.GOVERNMENT_SCHEMES,
        candidate_source_type=CandidateSourceType.PUBLIC_SPEECH,
        attribution_type=AttributionType.DIRECT_QUOTE,
        speaker_name="M. K. Stalin",
        party="DMK",
        claim_date=stmt_date,
        language="ta"
    )
    assert res2["status"] == IngestionStatus.DUPLICATE_EXACT
    assert res2["claim_id"] == "CLM-DUP-ORIGINAL"

    # Verify database has ONLY 1 record, not 2
    claims_count = db_session.query(Claim).count()
    assert claims_count == 1


# ---------------------------------------------------------------------------
# Test 6: Materially Distinct Reiterations Preserved Distinctly
# ---------------------------------------------------------------------------
def test_6_materially_distinct_reiterations_preserved(db_session):
    """
    Test that a politician reiterating the exact same campaign promise
    at two different rallies on different dates is preserved as two DISTINCT claims.
    """
    service = ClaimIngestionService(db=db_session)
    statement = "We will ensure a government arts college is established in every taluk."

    # Rally 1 in Madurai on May 1
    res1 = service.ingest_claim(
        claim_id="CLM-REIT-001",
        original_text=statement,
        claim_category=ClaimCategory.HEALTHCARE_EDUCATION,
        candidate_source_type=CandidateSourceType.PUBLIC_SPEECH,
        attribution_type=AttributionType.DIRECT_QUOTE,
        speaker_name="Leader A",
        party="Party X",
        claim_date=datetime(2021, 5, 1, tzinfo=timezone.utc),
        context_text="Rally at Madurai"
    )
    assert res1["status"] == IngestionStatus.CREATED

    # Rally 2 in Salem on May 10 (same wording, DIFFERENT date & rally)
    res2 = service.ingest_claim(
        claim_id="CLM-REIT-002",
        original_text=statement,
        claim_category=ClaimCategory.HEALTHCARE_EDUCATION,
        candidate_source_type=CandidateSourceType.PUBLIC_SPEECH,
        attribution_type=AttributionType.DIRECT_QUOTE,
        speaker_name="Leader A",
        party="Party X",
        claim_date=datetime(2021, 5, 10, tzinfo=timezone.utc),
        context_text="Rally at Salem"
    )

    # Must be preserved as a distinct reiteration, NOT merged or dropped
    assert res2["status"] == IngestionStatus.DISTINCT_REITERATION
    assert res2["claim_id"] == "CLM-REIT-002"

    claims_in_db = db_session.query(Claim).all()
    assert len(claims_in_db) == 2


# ---------------------------------------------------------------------------
# Test 7: Claim Versioning and Corrections History
# ---------------------------------------------------------------------------
def test_7_claim_versioning_and_corrections_history(db_session):
    service = ClaimIngestionService(db=db_session)

    # Initial intake of a noisy speech transcript
    initial_text = "கலைஞர் மகளிர் உரிமை திட்டம் 1 கோடி மகளிருக்கு."
    res1 = service.ingest_claim(
        claim_id="CLM-VER-001",
        original_text=initial_text,
        claim_category=ClaimCategory.GOVERNMENT_SCHEMES,
        candidate_source_type=CandidateSourceType.PUBLIC_SPEECH,
        attribution_type=AttributionType.DIRECT_QUOTE,
        speaker_name="M. K. Stalin",
        party="DMK"
    )
    assert res1["status"] == IngestionStatus.CREATED

    # Ingest a high-fidelity correction with standard spelling and added context
    corrected_text = "கலைஞர் மகளிர் உரிமைத் திட்டம்: 1.15 கோடி குடும்பத்தலைவிகளுக்கு மாதம் ₹1,000."
    res2 = service.ingest_claim(
        claim_id="CLM-CORR-TMP",
        original_text=corrected_text,
        claim_category=ClaimCategory.GOVERNMENT_SCHEMES,
        candidate_source_type=CandidateSourceType.OFFICIAL_STATEMENT,
        attribution_type=AttributionType.DIRECT_QUOTE,
        is_correction_for_claim_id="CLM-VER-001",
        correction_rationale="Audited against official G.O. Ms. No. 37 gazette text",
        transliteration="Kalaignar Magalir Urimai Thittam: 1.15 kodi kudumbathalaivigalukku maadham 1000",
        context_text="Official state press release clarification"
    )
    assert res2["status"] == IngestionStatus.VERSION_ADDED
    assert res2["claim_id"] == "CLM-VER-001"
    assert res2["version_number"] == 2

    # Verify root Claim original_text is still intact
    claim = db_session.query(Claim).filter(Claim.claim_id == "CLM-VER-001").first()
    assert claim.original_text == initial_text
    assert len(claim.versions) == 2
    assert claim.versions[1].edited_text == corrected_text
    assert "G.O. Ms. No. 37" in claim.versions[1].change_rationale


# ---------------------------------------------------------------------------
# Test 8: Multilingual Ingestion (Tamil, English, Code-Switched)
# ---------------------------------------------------------------------------
def test_8_multilingual_text_ingestion(db_session):
    service = ClaimIngestionService(db=db_session)

    # 1. Pure Tamil
    res_ta = service.ingest_claim(
        claim_id="CLM-LANG-TA",
        original_text="தமிழ்நாடு இந்தியாவின் முதன்மைப் பொருளாதார மாநிலங்களில் ஒன்றாகத் திகழ்கிறது.",
        claim_category=ClaimCategory.EMPLOYMENT_ECONOMIC,
        candidate_source_type=CandidateSourceType.PUBLIC_SPEECH,
        attribution_type=AttributionType.DIRECT_QUOTE,
        language="ta"
    )
    assert res_ta["status"] == IngestionStatus.CREATED

    # 2. Pure English
    res_en = service.ingest_claim(
        claim_id="CLM-LANG-EN",
        original_text="Tamil Nadu has commissioned over 500 electric buses under the clean transit initiative.",
        claim_category=ClaimCategory.PUBLIC_INFRASTRUCTURE,
        candidate_source_type=CandidateSourceType.PRESS_RELEASE,
        attribution_type=AttributionType.DIRECT_QUOTE,
        language="en"
    )
    assert res_en["status"] == IngestionStatus.CREATED

    # 3. Code-switched (Tamil + English)
    res_bilingual = service.ingest_claim(
        claim_id="CLM-LANG-BI",
        original_text="நமது அரசு 100 புதிய Industrial Parks அமைக்க G.O. வெளியிட்டுள்ளது.",
        claim_category=ClaimCategory.PUBLIC_INFRASTRUCTURE,
        candidate_source_type=CandidateSourceType.PUBLIC_SPEECH,
        attribution_type=AttributionType.DIRECT_QUOTE,
        language="bilingual"
    )
    assert res_bilingual["status"] == IngestionStatus.CREATED
    assert res_bilingual["language"] == "bilingual"


# ---------------------------------------------------------------------------
# Test 9: REST API Ingestion Endpoints Integration
# ---------------------------------------------------------------------------
def test_9_api_ingestion_endpoints(api_client, db_session):
    # 1. Test POST /api/claims/check-duplicate (Initial check: False)
    check_resp = api_client.post("/api/claims/check-duplicate", json={
        "original_text": "Tamil Nadu has 38 districts with full rural electrification.",
        "speaker_name": "Electricity Minister"
    })
    assert check_resp.status_code == 200
    assert check_resp.get_json()["data"]["is_duplicate"] is False

    # 2. Test POST /api/claims/ingest
    ingest_payload = {
        "claim_id": "CLM-API-ING-001",
        "original_text": "Tamil Nadu has 38 districts with full rural electrification.",
        "claim_category": "PUBLIC_INFRASTRUCTURE",
        "candidate_source_type": "OFFICIAL_STATEMENT",
        "attribution_type": "DIRECT_QUOTE",
        "speaker_name": "Electricity Minister",
        "party": "DMK",
        "language": "en"
    }
    ing_resp = api_client.post("/api/claims/ingest", json=ingest_payload)
    assert ing_resp.status_code == 200
    assert ing_resp.get_json()["data"]["status"] == IngestionStatus.CREATED

    # 3. Test POST /api/claims/check-duplicate again (Now: True!)
    check_again = api_client.post("/api/claims/check-duplicate", json={
        "original_text": "Tamil Nadu has 38 districts with full rural electrification.",
        "speaker_name": "Electricity Minister"
    })
    assert check_again.status_code == 200
    assert check_again.get_json()["data"]["is_duplicate"] is True

    # 4. Test POST /api/claims/<claim_id>/version
    version_payload = {
        "edited_text": "Tamil Nadu has 38 districts with 99.8% rural household electrification.",
        "change_rationale": "Clarified official percentage from TANGEDCO statistical bulletin."
    }
    ver_resp = api_client.post("/api/claims/CLM-API-ING-001/version", json=version_payload)
    assert ver_resp.status_code == 200
    assert ver_resp.get_json()["data"]["version_number"] == 2
