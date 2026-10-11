"""
Unit tests for Phase 6 Political Promise Cross-Reference and Performance Indicators Pipeline.

Tests:
1. Linking representative to Phase 3 promise and government scheme.
2. Rejection of non-existent promises (raising PromiseNotFoundError).
3. Evidence links and progression to POLICY_ACTION_DOCUMENTED.
4. Constituency work links and progression to PROJECT_WORK_RECORDED.
5. Development indicator links and progression to OUTCOME_INDICATOR_OBSERVED.
6. Conflicting dates detection and classification as INSUFFICIENT_EVIDENCE.
7. Representative promise scorecard aggregation and methodology disclaimers.
"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.database.base_class import Base
from backend.models.representative import (
    Representative,
    Constituency,
    ConstituencyWork,
    DevelopmentIndicator,
    PromisePerformanceLink,
    PromiseEvidenceStage,
    RepresentativeType,
    ConstituencyType
)
from backend.models.promise import PoliticalPromise
from backend.models.manifesto import Manifesto
from backend.models.common import Evidence, Source, Document
from backend.models.news import PoliticalParty
from backend.services.promise_cross_reference import (
    PromiseCrossReferenceService,
    PromiseNotFoundError,
    RepresentativeNotFoundError
)


@pytest.fixture
def db_session():
    """In-memory SQLite database session for isolated testing."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    # Pre-populate party, manifesto, and representative
    party = PoliticalParty(party_id="PARTY-DMK", party_name="DMK", party_code="DMK")
    session.add(party)
    session.flush()

    manifesto = Manifesto(
        manifesto_id="MAN-DMK-2021",
        party="DMK",
        election_year=2021
    )
    session.add(manifesto)
    session.flush()

    rep = Representative(
        representative_id="REP-MLA-013",
        official_name="M. K. Stalin",
        representative_type=RepresentativeType.MLA,
        party_id="PARTY-DMK",
        election_id="TN_ASSEMBLY_2021"
    )
    session.add(rep)

    # Pre-populate Phase 3 Political Promise
    promise = PoliticalPromise(
        promise_id="PROM-DMK-2021-042",
        manifesto_id="MAN-DMK-2021",
        original_text="Provide smart classrooms in all government schools across North Chennai",
        normalized_text="Smart classrooms in government schools across North Chennai"
    )
    session.add(promise)
    session.commit()

    yield session
    session.close()


def test_1_link_representative_to_promise_and_scheme(db_session):
    service = PromiseCrossReferenceService(db=db_session)

    link = service.link_promise_to_performance(
        link_id="LNK-01",
        representative_id="REP-MLA-013",
        promise_id="PROM-DMK-2021-042",
        scheme_id="SAMAGRA_SHIKSHA_TN",
        matching_method="PARTY_MANIFESTO_DIRECT",
        evidence_summary="Matched DMK 2021 Manifesto Promise 42 with State Education Scheme."
    )

    assert link.link_id == "LNK-01"
    assert link.representative_id == "REP-MLA-013"
    assert link.promise_id == "PROM-DMK-2021-042"
    assert link.scheme_id == "SAMAGRA_SHIKSHA_TN"
    assert link.evidence_stage == PromiseEvidenceStage.RELEVANT_SCHEME_IDENTIFIED
    assert link.has_conflicting_dates is False


def test_2_rejection_of_non_existent_phase3_promise(db_session):
    """
    CRITICAL RULE: Do not create promise records if Phase 3 does not contain them.
    Attempting to link an unverified promise_id MUST raise PromiseNotFoundError.
    """
    service = PromiseCrossReferenceService(db=db_session)

    with pytest.raises(PromiseNotFoundError):
        service.link_promise_to_performance(
            link_id="LNK-FAIL",
            representative_id="REP-MLA-013",
            promise_id="NON_EXISTENT_PROMISE_999",  # Not in Phase 3
            scheme_id="SOME_SCHEME"
        )


def test_3_evidence_link_and_policy_action_advancement(db_session):
    service = PromiseCrossReferenceService(db=db_session)

    # Create mock statutory evidence
    ev = Evidence(
        id=101,
        content="G.O. Ms. No. 45 - Sanction of Smart Classroom Equipment for Kolathur Schools",
        explanation="Formal Government Order allocating budget for promise execution."
    )
    db_session.add(ev)
    db_session.commit()

    link = service.link_promise_to_performance(
        link_id="LNK-EVID-01",
        representative_id="REP-MLA-013",
        promise_id="PROM-DMK-2021-042",
        scheme_id="SAMAGRA_SHIKSHA_TN",
        evidence_id=101
    )

    assert link.evidence_stage == PromiseEvidenceStage.POLICY_ACTION_DOCUMENTED
    assert link.evidence_id == 101


def test_4_constituency_work_advancement_to_project_recorded(db_session):
    service = PromiseCrossReferenceService(db=db_session)

    # Create constituency work
    work = ConstituencyWork(
        work_id="WORK-SMART-01",
        constituency_id="AC-013",
        scheme_id="MLACDS",
        project_description="Supply of interactive smart boards to 5 government schools",
        sanctioned_amount=1500000.0,
        reported_expenditure=1500000.0
    )
    db_session.add(work)
    db_session.commit()

    link = service.link_promise_to_performance(
        link_id="LNK-WORK-01",
        representative_id="REP-MLA-013",
        promise_id="PROM-DMK-2021-042",
        scheme_id="MLACDS",
        work_id="WORK-SMART-01"
    )

    assert link.evidence_stage == PromiseEvidenceStage.PROJECT_WORK_RECORDED
    assert link.work_id == "WORK-SMART-01"


def test_5_development_indicator_advancement_to_outcome_observed(db_session):
    service = PromiseCrossReferenceService(db=db_session)

    # Create development indicator
    ind = DevelopmentIndicator(
        indicator_id="IND-DIGITAL-01",
        geographic_unit_id="AC-013",
        indicator_name="DIGITAL_CLASSROOM_COVERAGE_PCT",
        value=95.0,
        unit="PERCENT",
        reference_period="2023",
        geographic_level="CONSTITUENCY"
    )
    db_session.add(ind)
    db_session.commit()

    link = service.link_promise_to_performance(
        link_id="LNK-OUTCOME-01",
        representative_id="REP-MLA-013",
        promise_id="PROM-DMK-2021-042",
        indicator_id="IND-DIGITAL-01"
    )

    assert link.evidence_stage == PromiseEvidenceStage.OUTCOME_INDICATOR_OBSERVED
    assert link.indicator_id == "IND-DIGITAL-01"


def test_6_conflicting_dates_detection_and_insufficient_evidence(db_session):
    """
    If a government action took place in 2018, but the promise was made in the 2021 election,
    the service MUST flag has_conflicting_dates = True and downgrade to INSUFFICIENT_EVIDENCE.
    """
    service = PromiseCrossReferenceService(db=db_session)

    link = service.link_promise_to_performance(
        link_id="LNK-CONFLICT-01",
        representative_id="REP-MLA-013",
        promise_id="PROM-DMK-2021-042",
        scheme_id="OLD_HISTORICAL_SCHEME",
        promise_year=2021,  # 2021 Manifesto Promise
        action_year=2018    # Historical action executed 3 years prior to promise!
    )

    assert link.has_conflicting_dates is True
    assert link.evidence_stage == PromiseEvidenceStage.INSUFFICIENT_EVIDENCE


def test_7_representative_promise_scorecard_aggregation(db_session):
    service = PromiseCrossReferenceService(db=db_session)

    # Create two links for representative
    service.link_promise_to_performance(
        link_id="LNK-SC-01",
        representative_id="REP-MLA-013",
        promise_id="PROM-DMK-2021-042",
        scheme_id="SCHEME-A"
    )

    scorecard = service.get_representative_promise_scorecard("REP-MLA-013")

    assert scorecard["representative_id"] == "REP-MLA-013"
    assert scorecard["total_manifesto_promises_linked"] >= 1
    assert "A scheme's existence does not prove that a particular political promise was fulfilled." in scorecard["methodology_disclaimers"]["scheme_disclaimer"]
    assert "A constituency project's completion does not automatically prove the achievement" in scorecard["methodology_disclaimers"]["work_disclaimer"]
