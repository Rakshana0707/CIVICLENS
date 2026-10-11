"""
Unit tests for Phase 6 Public Representative & Constituency Registry.

Tests:
1. Canonical representative, constituency, election, and term registration.
2. Duplicate name disambiguation using multi-attribute context.
3. Ambiguous identity detection (raising AmbiguousIdentityError when context is missing).
4. Historical terms and party affiliation preservation across career transitions.
5. Constituency boundary and naming changes across delimitation eras.
6. Rajya Sabha representatives (state-wide, non-constituency representation).
7. Multilingual and alias-based identity resolution.
8. Missing and unknown record handling.
"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.database.base_class import Base
from backend.models.news import PoliticalParty
from backend.models.representative import (
    Representative,
    Constituency,
    Election,
    RepresentativeTerm,
    ConstituencyBoundaryHistory,
    RepresentativeType,
    ConstituencyType,
    ElectionType
)
from backend.services.representative_registry import (
    RepresentativeRegistryService,
    AmbiguousIdentityError,
    EntityNotFoundError
)


@pytest.fixture
def db_session():
    """In-memory SQLite database session for isolated testing."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    # Pre-populate sample political parties
    parties = [
        PoliticalParty(party_id="PARTY-DMK", party_name="Dravida Munnetra Kazhagam", party_code="DMK"),
        PoliticalParty(party_id="PARTY-AIADMK", party_name="All India Anna Dravida Munnetra Kazhagam", party_code="AIADMK"),
        PoliticalParty(party_id="PARTY-INC", party_name="Indian National Congress", party_code="INC")
    ]
    for p in parties:
        session.add(p)
    session.commit()

    yield session
    session.close()


def test_1_register_canonical_representative_and_constituency(db_session):
    service = RepresentativeRegistryService(db=db_session)

    # 1. Register Constituency
    const = service.register_constituency(
        constituency_id="AC-013-2008",
        official_name="Kolathur",
        constituency_type=ConstituencyType.ASSEMBLY,
        district="Chennai",
        valid_from="2008",
        reservation_status="GENERAL",
        source_document_ids=["DOC-ECI-DELIMITATION-2008"]
    )
    assert const.constituency_id == "AC-013-2008"
    assert const.official_name == "Kolathur"

    # 2. Register Representative
    rep = service.register_representative(
        representative_id="REP-MLA-013-STALIN",
        official_name="M. K. Stalin",
        representative_type=RepresentativeType.MLA,
        aliases=["MK Stalin", "மு.க. ஸ்டாலின்", "Muthuvel Karunanidhi Stalin"],
        party_id="PARTY-DMK",
        constituency_id="AC-013-2008",
        term_start="2021-05-07",
        source_document_ids=["DOC-ECI-2021-RETURN"]
    )
    assert rep.representative_id == "REP-MLA-013-STALIN"
    assert "MK Stalin" in rep.aliases
    assert "மு.க. ஸ்டாலின்" in rep.aliases


def test_2_duplicate_name_disambiguation(db_session):
    """
    Test two distinct representatives with the identical official name 'R. Chandrasekar'.
    Disambiguation MUST distinguish them using constituency and election attributes.
    """
    service = RepresentativeRegistryService(db=db_session)

    # Register two constituencies
    service.register_constituency(
        constituency_id="AC-139",
        official_name="Manapparai",
        constituency_type=ConstituencyType.ASSEMBLY,
        district="Tiruchirappalli"
    )
    service.register_constituency(
        constituency_id="AC-204",
        official_name="Sattur",
        constituency_type=ConstituencyType.ASSEMBLY,
        district="Virudhunagar"
    )

    # Register Rep 1: R. Chandrasekar in Manapparai
    rep1 = service.register_representative(
        representative_id="REP-MLA-139-CHANDRASEKAR",
        official_name="R. Chandrasekar",
        representative_type=RepresentativeType.MLA,
        party_id="PARTY-AIADMK",
        constituency_id="AC-139",
        term_start="2016-05-23"
    )
    service.register_term(
        term_id="TERM-139-2016",
        representative_id=rep1.representative_id,
        constituency_id="AC-139",
        party_id="PARTY-AIADMK",
        house_type="TN_ASSEMBLY",
        term_start="2016-05-23",
        term_end="2021-05-03"
    )

    # Register Rep 2: R. Chandrasekar in Sattur
    rep2 = service.register_representative(
        representative_id="REP-MLA-204-CHANDRASEKAR",
        official_name="R. Chandrasekar",
        representative_type=RepresentativeType.MLA,
        party_id="PARTY-DMK",
        constituency_id="AC-204",
        term_start="2021-05-07"
    )
    service.register_term(
        term_id="TERM-204-2021",
        representative_id=rep2.representative_id,
        constituency_id="AC-204",
        party_id="PARTY-DMK",
        house_type="TN_ASSEMBLY",
        term_start="2021-05-07",
        is_active_term=True
    )

    # Query with Manapparai constituency context -> MUST resolve to Rep 1
    resolved_1 = service.resolve_representative(
        query_name="R. Chandrasekar",
        constituency_id="AC-139"
    )
    assert resolved_1.representative_id == "REP-MLA-139-CHANDRASEKAR"

    # Query with Sattur constituency context -> MUST resolve to Rep 2
    resolved_2 = service.resolve_representative(
        query_name="R. Chandrasekar",
        constituency_id="AC-204"
    )
    assert resolved_2.representative_id == "REP-MLA-204-CHANDRASEKAR"


def test_3_ambiguous_identity_without_context_raises_error(db_session):
    """
    Querying an ambiguous name when multiple candidates exist without context
    MUST raise AmbiguousIdentityError.
    """
    service = RepresentativeRegistryService(db=db_session)

    service.register_representative(
        representative_id="REP-001-KUMAR",
        official_name="P. Kumar",
        representative_type=RepresentativeType.MLA,
        constituency_id="AC-100"
    )
    service.register_representative(
        representative_id="REP-002-KUMAR",
        official_name="P. Kumar",
        representative_type=RepresentativeType.MLA,
        constituency_id="AC-101"
    )

    with pytest.raises(AmbiguousIdentityError) as exc_info:
        service.resolve_representative(query_name="P. Kumar")

    assert len(exc_info.value.candidate_ids) == 2
    assert "REP-001-KUMAR" in exc_info.value.candidate_ids
    assert "REP-002-KUMAR" in exc_info.value.candidate_ids


def test_4_historical_terms_and_party_preservation(db_session):
    """
    Verifies that representative party changes over time are accurately preserved in historical terms
    and not overwritten by current party affiliation.
    """
    service = RepresentativeRegistryService(db=db_session)

    rep = service.register_representative(
        representative_id="REP-MLA-SAMPLE-SWITCHER",
        official_name="K. S. Thennarasu",
        representative_type=RepresentativeType.MLA,
        party_id="PARTY-DMK",  # Current party
        term_start="2021-05-07"
    )

    # Term 1: 2011 to 2016 under AIADMK
    service.register_term(
        term_id="TERM-THENNARASU-2011",
        representative_id=rep.representative_id,
        party_id="PARTY-AIADMK",
        house_type="TN_ASSEMBLY",
        term_start="2011-05-23",
        term_end="2016-05-21"
    )

    # Term 2: 2021 to Present under DMK
    service.register_term(
        term_id="TERM-THENNARASU-2021",
        representative_id=rep.representative_id,
        party_id="PARTY-DMK",
        house_type="TN_ASSEMBLY",
        term_start="2021-05-07",
        is_active_term=True
    )

    # Check historical party for 2013 -> MUST be AIADMK
    party_2013 = service.get_historical_party_for_term(
        representative_id=rep.representative_id,
        year=2013
    )
    assert party_2013 == "PARTY-AIADMK"

    # Check historical party for 2022 -> MUST be DMK
    party_2022 = service.get_historical_party_for_term(
        representative_id=rep.representative_id,
        year=2022
    )
    assert party_2022 == "PARTY-DMK"


def test_5_constituency_boundary_and_naming_changes(db_session):
    """
    Test pre- and post-2008 delimitation constituency boundaries and history tracking.
    """
    service = RepresentativeRegistryService(db=db_session)

    # Pre-2008 constituency (Triplicane - abolished/merged in 2008)
    c_pre = service.register_constituency(
        constituency_id="AC-TRIPLICANE-1977",
        official_name="Triplicane",
        constituency_type=ConstituencyType.ASSEMBLY,
        district="Chennai",
        valid_from="1977",
        valid_to="2008",
        delimitation_year=1976,
        successor_id="AC-CHEPAUK-THIRUVALLIKENI-2008"
    )

    # Post-2008 constituency (Chepauk-Thiruvallikeni)
    c_post = service.register_constituency(
        constituency_id="AC-CHEPAUK-THIRUVALLIKENI-2008",
        official_name="Chepauk-Thiruvallikeni",
        constituency_type=ConstituencyType.ASSEMBLY,
        district="Chennai",
        valid_from="2008",
        valid_to=None,  # Active
        delimitation_year=2008,
        predecessor_id="AC-TRIPLICANE-1977"
    )

    # Record history
    hist = service.record_boundary_change(
        history_id="HIST-CHEP-01",
        constituency_id=c_post.constituency_id,
        historical_name="Triplicane & Chepauk Wards",
        delimitation_order="Delimitation 2008",
        valid_from="2008",
        change_summary="Triplicane and Chepauk merged into unified Chepauk-Thiruvallikeni constituency."
    )
    assert hist.history_id == "HIST-CHEP-01"

    # Test as_of_year lookups
    c_1996 = service.get_constituency_as_of("AC-TRIPLICANE-1977", as_of_year=1996)
    assert c_1996 is not None
    assert c_1996.official_name == "Triplicane"

    c_2021 = service.get_constituency_as_of("AC-CHEPAUK-THIRUVALLIKENI-2008", as_of_year=2021)
    assert c_2021 is not None
    assert c_2021.official_name == "Chepauk-Thiruvallikeni"


def test_6_rajya_sabha_representative_no_constituency(db_session):
    """
    Test Rajya Sabha MPs who represent the state at large (constituency_id=None).
    """
    service = RepresentativeRegistryService(db=db_session)

    rs_rep = service.register_representative(
        representative_id="REP-RS-VAIKO",
        official_name="Vaiko",
        representative_type=RepresentativeType.RAJYA_SABHA_MP,
        aliases=["V. Gopalasamy", "வைக்கோ"],
        party_id="PARTY-DMK",
        constituency_id=None,  # State-wide representative
        term_start="2019-07-25"
    )

    resolved = service.resolve_representative(
        query_name="வைக்கோ",
        representative_type=RepresentativeType.RAJYA_SABHA_MP
    )
    assert resolved.representative_id == "REP-RS-VAIKO"
    assert resolved.constituency_id is None


def test_7_multilingual_and_alias_resolution(db_session):
    """
    Test resolving canonical representative using Tamil script and English nicknames.
    """
    service = RepresentativeRegistryService(db=db_session)

    service.register_representative(
        representative_id="REP-MLA-013-STALIN",
        official_name="M. K. Stalin",
        representative_type=RepresentativeType.MLA,
        aliases=["MK Stalin", "மு.க. ஸ்டாலின்"],
        constituency_id="AC-013"
    )

    # Resolve using Tamil alias
    res_ta = service.resolve_representative(query_name="மு.க. ஸ்டாலின்")
    assert res_ta.representative_id == "REP-MLA-013-STALIN"

    # Resolve using informal English nickname
    res_en = service.resolve_representative(query_name="MK Stalin")
    assert res_en.representative_id == "REP-MLA-013-STALIN"


def test_8_missing_and_unknown_records(db_session):
    """
    Test graceful handling and exceptions for non-existent entities.
    """
    service = RepresentativeRegistryService(db=db_session)

    with pytest.raises(EntityNotFoundError):
        service.resolve_representative(query_name="Non Existent Politician 999")

    with pytest.raises(EntityNotFoundError):
        service.resolve_representative(query_name="")
