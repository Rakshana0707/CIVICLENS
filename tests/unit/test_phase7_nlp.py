"""
Phase 7.4 — Unit Tests for Multilingual Claim Decomposition & NLP Pipeline.

Tests:
1. Language detection across Tamil, English, and mixed-language (Tanglish) text.
2. Unicode text normalization (NFC composition, zero-width stripping, whitespace).
3. Verifiability classification: distinguishing factual claims from opinions, predictions,
   value judgments, rhetorical questions, slogans, and ambiguous wording.
4. Quantitative attribute extraction (Crores, Lakhs, INR, %, discrete units, denominators).
5. Comparison operators and baselines (increased from X to Y, greater than, etc.).
6. Temporal scope and fiscal year extraction (2024-25, last 3 years, கடந்த 3 ஆண்டுகளில்).
7. Negation detection in Tamil and English (did not, இல்லை, வழங்கப்படவில்லை).
8. Multi-part compound claim decomposition with subject inheritance.
9. Tamil text integrity: verbatim original text preserved, auxiliary translation generated.
10. End-to-end processing and database persistence into atomic_claims table.
11. REST API endpoints: /api/claims/nlp-process and /api/claims/<id>/decompose.
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
    ClaimCategory,
    ClaimStatus,
    ReviewStatus,
    AttributionType,
    CandidateSourceType,
    VerifiabilityStatus,
    AtomicClaimType
)
from backend.nlp.claim_decomposition import (
    LanguageDetector,
    TextNormalizer,
    VerifiabilityClassifier,
    QuantitativeExtractor,
    EntityAndNegationExtractor,
    AtomicClaimDecomposer,
    MultilingualClaimPipeline
)
from backend.api.app import create_app


@pytest.fixture
def db_session():
    """Isolated in-memory SQLite database session for NLP unit tests."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()

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


def test_1_language_detection_tamil_english_mixed():
    """
    Verifies accurate identification of Tamil ('ta'), English ('en'), and mixed ('mixed') scripts.
    """
    # 1. Pure Tamil
    ta_text = "கலைஞர் மகளிர் உரிமைத் திட்டத்திற்கு ரூ.13,720 கோடி நிதி ஒதுக்கப்பட்டுள்ளது."
    assert LanguageDetector.detect(ta_text) == "ta"

    # 2. Pure English
    en_text = "Tamil Nadu government allocated Rs 13,720 crore for the welfare scheme."
    assert LanguageDetector.detect(en_text) == "en"

    # 3. Mixed / Code-switched (Tanglish)
    mixed_text = "KMUT scheme-il 1000 rupees மகளிர் உரிமைத் தொகை வழங்கப்பட்டுள்ளது."
    assert LanguageDetector.detect(mixed_text) == "mixed"


def test_2_text_normalization_unicode_nfc_and_zero_width():
    """
    Verifies Unicode NFC canonical composition, zero-width space/joiner stripping,
    and whitespace cleanup while leaving original string intact.
    """
    # Raw string containing zero-width non-joiner (\u200C), zero-width space (\u200B), and tabs
    raw_text = "கலைஞர்\u200C மகளிர் \u200B உரிமைத்\t  திட்டம்\n\nரூ.1000"
    normalized = TextNormalizer.normalize(raw_text)

    # Invisible characters should be stripped
    assert "\u200C" not in normalized
    assert "\u200B" not in normalized
    assert "\t" not in normalized
    assert "\n" not in normalized
    assert normalized == "கலைஞர் மகளிர் உரிமைத் திட்டம் ரூ.1000"


def test_3_distinguishing_factual_claims_from_non_factual_speech_acts():
    """
    Verifies that the classifier distinguishes verifiable factual propositions from
    opinions, predictions, value judgments, rhetorical questions, slogans, and vague generalities.
    """
    # 1. Opinion
    op_en = "In my opinion, this government has provided the best administration in the country."
    status, conf, rat = VerifiabilityClassifier.evaluate(op_en)
    assert status == VerifiabilityStatus.OPINION

    op_ta = "இது மிகச் சிறந்த மக்கள் நல அரசு என்று நான் கருதுகிறேன்."
    status, conf, rat = VerifiabilityClassifier.evaluate(op_ta)
    assert status == VerifiabilityStatus.OPINION

    # 2. Prediction
    pred_en = "By 2030 Tamil Nadu will become a 1 trillion dollar economy."
    status, conf, rat = VerifiabilityClassifier.evaluate(pred_en)
    assert status == VerifiabilityStatus.PREDICTION

    pred_ta = "அடுத்த தேர்தலில் நாங்கள் 200 தொகுதிகளில் வெல்வோம்."
    status, conf, rat = VerifiabilityClassifier.evaluate(pred_ta)
    assert status == VerifiabilityStatus.PREDICTION

    # 3. Value Judgment
    val_en = "The decision of the opposition is corrupt to the core and immoral."
    status, conf, rat = VerifiabilityClassifier.evaluate(val_en)
    assert status == VerifiabilityStatus.VALUE_JUDGMENT

    # 4. Rhetorical Question
    rq_en = "Can anyone deny our historic progress?"
    status, conf, rat = VerifiabilityClassifier.evaluate(rq_en)
    assert status == VerifiabilityStatus.RHETORICAL_QUESTION

    rq_ta = "கடந்த 10 ஆண்டுகளில் மக்களுக்கு இந்த அரசு என்ன செய்தது?"
    status, conf, rat = VerifiabilityClassifier.evaluate(rq_ta)
    assert status == VerifiabilityStatus.RHETORICAL_QUESTION

    # 5. Slogan
    slogan_ta = "வெல்வோம்! வெல்வோம்! வளர்க தமிழ்நாடு!"
    status, conf, rat = VerifiabilityClassifier.evaluate(slogan_ta)
    assert status == VerifiabilityStatus.SLOGAN

    # 6. Ambiguous / Vague
    amb_en = "Development is visible everywhere in the state."
    status, conf, rat = VerifiabilityClassifier.evaluate(amb_en)
    assert status == VerifiabilityStatus.AMBIGUOUS_UNVERIFIABLE

    # 7. Verifiable Factual
    fact_en = "The state government allocated Rs 44,042 crore for school education in 2024-25."
    status, conf, rat = VerifiabilityClassifier.evaluate(fact_en)
    assert status == VerifiabilityStatus.VERIFIABLE_FACTUAL


def test_4_quantitative_extraction_numbers_scales_units_denominators():
    """
    Verifies extraction of Crore, Lakh, INR, percentages, and denominators.
    """
    # 1. Crore extraction in Tamil
    text_crore = "பட்ஜெட்டில் கலைஞர் மகளிர் உரிமைத் திட்டத்திற்கு ரூ.13,720 கோடி ஒதுக்கப்பட்டுள்ளது."
    quant1 = QuantitativeExtractor.extract(text_crore)
    assert quant1["numeric_value"] == 13720.0
    assert quant1["unit"] == "crore"

    # 2. Lakh and discrete unit in English
    text_lakh = "Over 1.15 lakh students enrolled under Pudhumai Penn scheme."
    quant2 = QuantitativeExtractor.extract(text_lakh)
    assert quant2["numeric_value"] == 1.15
    assert quant2["unit"] == "lakh"

    # 3. Percentage and Denominator
    text_pct = "Fiscal deficit was reduced to 3.44 percent of GSDP."
    quant3 = QuantitativeExtractor.extract(text_pct)
    assert quant3["numeric_value"] == 3.44
    assert quant3["unit"] == "percent"
    assert quant3["denominator"] == "of GSDP"

    # 4. Monthly allowance
    text_monthly = "Monthly allowance of Rs 1000 per month is provided to women."
    quant4 = QuantitativeExtractor.extract(text_monthly)
    assert quant4["numeric_value"] == 1000.0
    assert quant4["denominator"] == "per month"


def test_5_comparison_operators_and_baselines():
    """
    Verifies comparison operators and baseline-to-target extraction (from X to Y).
    """
    # English baseline increase
    en_comp = "Old age pension was increased from Rs 500 to Rs 1000 per month."
    quant_en = QuantitativeExtractor.extract(en_comp)
    assert quant_en["comparison_operator"] == "INCREASE_BY"
    assert quant_en["baseline_value"] == 500.0
    assert quant_en["numeric_value"] == 1000.0

    # Tamil baseline increase
    ta_comp = "முதியோர் உதவித்தொகை ரூ.500 இலிருந்து ரூ.1000 ஆக உயர்த்தப்பட்டுள்ளது."
    quant_ta = QuantitativeExtractor.extract(ta_comp)
    assert quant_ta["comparison_operator"] == "INCREASE_BY"
    assert quant_ta["baseline_value"] == 500.0
    assert quant_ta["numeric_value"] == 1000.0


def test_6_temporal_scope_and_fiscal_years():
    """
    Verifies detection of fiscal years and relative calendar timeframes.
    """
    # Fiscal year 2024-25
    fy_text = "In 2024-25, school education outlay reached a new milestone."
    quant_fy = QuantitativeExtractor.extract(fy_text)
    assert quant_fy["time_period"] == "2024-25"

    # Relative Tamil timeframe
    ta_rel = "கடந்த 3 ஆண்டுகளில் 10,000 புதிய பேருந்துகள் வாங்கப்பட்டுள்ளன."
    quant_ta = QuantitativeExtractor.extract(ta_rel)
    assert "கடந்த 3 ஆண்டுகளில்" in quant_ta["time_period"]
    assert quant_ta["numeric_value"] == 10000.0


def test_7_negation_detection_tamil_and_english():
    """
    Verifies detection of negative assertions in both languages.
    """
    # 1. English negation
    neg_en = "The government did not fulfill the promise of waiving student education loans."
    assert EntityAndNegationExtractor.detect_negation(neg_en) is True

    # 2. Tamil negation
    neg_ta = "மகளிர் உரிமைத்தொகை தகுதியுள்ள அனைவருக்கும் வழங்கப்படவில்லை."
    assert EntityAndNegationExtractor.detect_negation(neg_ta) is True

    # 3. Positive assertions
    pos_en = "The scheme has distributed 50,000 welfare kits across Salem district."
    assert EntityAndNegationExtractor.detect_negation(pos_en) is False

    pos_ta = "திமுக அரசு 10 லட்சம் மாணவர்களுக்கு மடிக்கணினிகளை வழங்கியுள்ளது."
    assert EntityAndNegationExtractor.detect_negation(pos_ta) is False


def test_8_multi_part_claim_decomposition_and_coreference():
    """
    Verifies splitting compound sentences joined by conjunctions into atomic propositions
    with subject inheritance across dependent clauses.
    """
    compound_text = (
        "DMK government allocated Rs 13,720 crore for Kalaignar Magalir Urimai Thittam "
        "and distributed 10,000 free bicycles in Chennai."
    )
    pipeline = MultilingualClaimPipeline()
    res = pipeline.process_claim(
        claim_id="CLM-MULTI-01",
        original_text=compound_text,
        persist_to_db=False
    )

    assert res["atomic_claims_count"] == 2
    claims = res["atomic_claims"]

    # First Atomic Proposition
    assert claims[0]["atomic_claim_id"] == "ACM-CLM-MULTI-01-01"
    assert "13,720 crore" in claims[0]["atomic_claim_text"]
    assert claims[0]["numeric_value"] == 13720.0
    assert claims[0]["unit"] == "crore"
    assert claims[0]["subject"] == "Kalaignar Magalir Urimai Thittam"
    assert claims[0]["claim_type"] == "SCHEME_BENEFIT"

    # Second Atomic Proposition: inherits "DMK" / "Kalaignar Magalir Urimai Thittam" as subject
    assert claims[1]["atomic_claim_id"] == "ACM-CLM-MULTI-01-02"
    assert "10,000 free bicycles" in claims[1]["atomic_claim_text"]
    assert claims[1]["numeric_value"] == 10000.0
    assert claims[1]["geographic_scope"] == "Chennai"
    assert claims[1]["subject"] is not None


def test_9_tamil_text_preservation_and_auxiliary_translation():
    """
    Verifies that the original Tamil Unicode text is preserved without alterations,
    while generating an auxiliary English translation search helper.
    """
    tamil_statement = "கலைஞர் மகளிர் உரிமைத் திட்டத்திற்கு ரூ.13,720 கோடி நிதி ஒதுக்கப்பட்டுள்ளது."
    pipeline = MultilingualClaimPipeline()
    res = pipeline.process_claim(
        claim_id="CLM-TN-VERB-01",
        original_text=tamil_statement,
        persist_to_db=False
    )

    # 1. Exact original verbatim preservation
    assert res["original_text"] == tamil_statement
    assert res["detected_language"] == "ta"

    atomic = res["atomic_claims"][0]
    # Exact Tamil proposition preserved
    assert atomic["atomic_claim_text"] == tamil_statement
    assert "ரூ.13,720 கோடி" in atomic["atomic_claim_text"]

    # Auxiliary translation helper present for search indexing
    assert atomic["translation_text"] is not None
    assert "13720.0 crore" in atomic["translation_text"]


def test_10_end_to_end_pipeline_and_db_persistence(db_session):
    """
    Verifies end-to-end decomposition and database persistence into atomic_claims table.
    """
    # Setup parent Claim
    claim = Claim(
        claim_id="CLM-PERSIST-01",
        original_text="Government allocated Rs 44,042 crore for education in 2024-25.",
        normalized_text="Government allocated Rs 44,042 crore for education in 2024-25.",
        claim_category=ClaimCategory.BUDGET_EXPENDITURE,
        status=ClaimStatus.PENDING,
        language="en"
    )
    db_session.add(claim)
    db_session.commit()

    pipeline = MultilingualClaimPipeline(db=db_session)
    res = pipeline.process_claim(
        claim_id=claim.claim_id,
        original_text=claim.original_text,
        persist_to_db=True
    )

    assert res["atomic_claims_count"] == 1

    # Verify atomic_claims record in DB
    db_atomic = db_session.query(AtomicClaim).filter(
        AtomicClaim.claim_id == claim.claim_id
    ).first()
    assert db_atomic is not None
    assert db_atomic.atomic_claim_id == "ACM-CLM-PERSIST-01-01"
    assert db_atomic.numeric_value == 44042.0
    assert db_atomic.unit == "crore"
    assert db_atomic.time_period == "2024-25"
    assert db_atomic.verifiability_status == "VERIFIABLE_FACTUAL"
    assert db_atomic.is_verifiable is True
    assert db_atomic.decomposition_method == "MULTILINGUAL_NLP_V1"


def test_11_rest_api_nlp_process_and_decompose_endpoints(api_client):
    """
    Verifies REST API endpoints:
    - POST /api/claims/nlp-process
    - POST /api/claims/<id>/decompose
    - GET /api/claims/<id>
    """
    # 1. Test direct /nlp-process endpoint without pre-registering a claim
    nlp_resp = api_client.post("/api/claims/nlp-process", json={
        "text": "கலைஞர் மகளிர் உரிமைத் திட்டத்திற்கு ரூ.13,720 கோடி நிதி ஒதுக்கப்பட்டுள்ளது."
    })
    assert nlp_resp.status_code == 200
    nlp_json = nlp_resp.get_json()["data"]
    assert nlp_json["detected_language"] == "ta"
    assert nlp_json["atomic_claims_count"] == 1
    assert nlp_json["atomic_claims"][0]["numeric_value"] == 13720.0

    # 2. Ingest a claim first
    ingest_resp = api_client.post("/api/claims/ingest", json={
        "claim_id": "CLM-API-NLP-01",
        "original_text": "Pudhumai Penn scheme provides Rs 1000 per month for college students.",
        "claim_category": "GOVERNMENT_SCHEMES",
        "candidate_source_type": "OFFICIAL_STATEMENT",
        "language": "en"
    })
    assert ingest_resp.status_code == 200

    # 3. Call /decompose on registered claim
    decomp_resp = api_client.post("/api/claims/CLM-API-NLP-01/decompose", json={})
    assert decomp_resp.status_code == 200
    decomp_json = decomp_resp.get_json()["data"]
    assert decomp_json["claim_id"] == "CLM-API-NLP-01"
    assert decomp_json["atomic_claims_count"] == 1

    # 4. Fetch claim profile via GET /api/claims/<claim_id>
    get_resp = api_client.get("/api/claims/CLM-API-NLP-01")
    assert get_resp.status_code == 200
    claim_profile = get_resp.get_json()["data"]
    assert "atomic_claims" in claim_profile
    assert len(claim_profile["atomic_claims"]) == 1
    assert claim_profile["atomic_claims"][0]["numeric_value"] == 1000.0
    assert claim_profile["atomic_claims"][0]["denominator"] == "per month"
