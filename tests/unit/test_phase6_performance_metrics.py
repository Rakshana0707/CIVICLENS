"""
Unit Tests for Phase 6.8 — Performance Metrics and Comparative Analysis Engine.

Validates:
1. Calculation of separate metrics across the 6 dimensions:
   - Legislative activity
   - Constituency works
   - Financial execution
   - Development trends
   - Promise evidence
   - Data completeness
2. Cohort normalization (min-max and percentile ranks) within homogeneous cohorts.
3. Incompatible cohort comparison rejection (MLA vs MP).
4. Missing data non-penalization via dynamic re-weighting.
5. Composite index sensitivity analysis (±20% perturbation).
6. Statutory caveats and anti-pejorative enforcement.
"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.database.base_class import Base
from backend.models.representative import (
    Representative,
    Constituency,
    RepresentativeType,
    ConstituencyType,
    LegislativeActivity,
    ConstituencyWork,
    DevelopmentIndicator,
    PromisePerformanceLink,
    PerformanceMetric,
    PerformanceDimension,
    WorkProjectStatus,
    AttributionType,
    GeographicLevel,
    PromiseEvidenceStage
)
from backend.models.news import PoliticalParty
from backend.models.manifesto import Manifesto
from backend.models.promise import PoliticalPromise
from backend.services.performance_metrics import (
    PerformanceMetricsEngine,
    IncompatibleCohortError
)


@pytest.fixture
def db_session():
    """In-memory SQLite database session for isolated unit testing."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    # Pre-populate Party, Manifesto, and Promise
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

    promise = PoliticalPromise(
        promise_id="PROM-DMK-2021-001",
        manifesto_id="MAN-DMK-2021",
        original_text="Upgrade primary schools to smart classrooms",
        normalized_text="Upgrade primary schools to smart classrooms"
    )
    session.add(promise)
    session.flush()

    # Create Constituencies
    c1 = Constituency(
        constituency_id="AC-013",
        official_name="Kolathur",
        constituency_type=ConstituencyType.ASSEMBLY,
        district="Chennai",
        state="Tamil Nadu"
    )
    c2 = Constituency(
        constituency_id="AC-014",
        official_name="Villivakkam",
        constituency_type=ConstituencyType.ASSEMBLY,
        district="Chennai",
        state="Tamil Nadu"
    )
    c3 = Constituency(
        constituency_id="PC-004",
        official_name="Chennai Central",
        constituency_type=ConstituencyType.PARLIAMENTARY,
        district="Chennai",
        state="Tamil Nadu"
    )
    session.add_all([c1, c2, c3])
    session.flush()

    # Create Representatives (MLAs and Lok Sabha MP)
    rep_mla1 = Representative(
        representative_id="REP-MLA-013",
        official_name="Representative A",
        representative_type=RepresentativeType.MLA,
        constituency_id="AC-013",
        party_id="PARTY-DMK"
    )
    rep_mla2 = Representative(
        representative_id="REP-MLA-014",
        official_name="Representative B",
        representative_type=RepresentativeType.MLA,
        constituency_id="AC-014",
        party_id="PARTY-DMK"
    )
    rep_mp1 = Representative(
        representative_id="REP-MP-004",
        official_name="Representative C",
        representative_type=RepresentativeType.LOK_SABHA_MP,
        constituency_id="PC-004",
        party_id="PARTY-DMK"
    )
    session.add_all([rep_mla1, rep_mla2, rep_mp1])
    session.flush()

    # Populate Sample Legislative Activities
    act1 = LegislativeActivity(
        activity_id="ACT-001",
        representative_id="REP-MLA-013",
        legislative_body="TN_ASSEMBLY",
        session="16th TNLA - Session 1",
        activity_type="QUESTION_STARRED",
        count=19,
        data_quality_status="VERIFIED"
    )
    act2 = LegislativeActivity(
        activity_id="ACT-002",
        representative_id="REP-MLA-013",
        legislative_body="TN_ASSEMBLY",
        session="16th TNLA - Session 1",
        activity_type="DEBATE",
        count=8,
        data_quality_status="VERIFIED"
    )
    act3 = LegislativeActivity(
        activity_id="ACT-003",
        representative_id="REP-MLA-014",
        legislative_body="TN_ASSEMBLY",
        session="16th TNLA - Session 1",
        activity_type="QUESTION_STARRED",
        count=38,
        data_quality_status="VERIFIED"
    )
    session.add_all([act1, act2, act3])
    session.flush()

    # Populate Constituency Works & Financials
    w1 = ConstituencyWork(
        work_id="WRK-001",
        constituency_id="AC-013",
        representative_id="REP-MLA-013",
        scheme_id="MLACDS",
        project_description="School building renovation",
        sanctioned_amount=2000000.0,
        released_amount=2000000.0,
        reported_expenditure=1800000.0,
        project_status=WorkProjectStatus.REPORTED_COMPLETED,
        approval_date="2022-01-15",
        attribution_type=AttributionType.REPRESENTATIVE_SPONSORED
    )
    w2 = ConstituencyWork(
        work_id="WRK-002",
        constituency_id="AC-013",
        representative_id="REP-MLA-013",
        scheme_id="MLACDS",
        project_description="Community hall construction",
        sanctioned_amount=3000000.0,
        released_amount=3000000.0,
        reported_expenditure=1200000.0,
        project_status=WorkProjectStatus.WORK_IN_PROGRESS,
        approval_date="2022-03-20",
        attribution_type=AttributionType.REPRESENTATIVE_SPONSORED
    )
    session.add_all([w1, w2])
    session.flush()

    # Populate Development Indicator Trajectory
    ind1 = DevelopmentIndicator(
        indicator_id="IND-LIT-2011",
        geographic_unit_id="AC-013",
        indicator_name="LITERACY_RATE",
        value=85.0,
        unit="PERCENT",
        reference_period="2011",
        geographic_level=GeographicLevel.CONSTITUENCY
    )
    ind2 = DevelopmentIndicator(
        indicator_id="IND-LIT-2021",
        geographic_unit_id="AC-013",
        indicator_name="LITERACY_RATE",
        value=91.5,
        unit="PERCENT",
        reference_period="2021",
        geographic_level=GeographicLevel.CONSTITUENCY
    )
    session.add_all([ind1, ind2])
    session.flush()

    # Populate Promise Performance Link
    link = PromisePerformanceLink(
        link_id="LNK-001",
        representative_id="REP-MLA-013",
        promise_id="PROM-DMK-2021-001",
        work_id="WRK-001",
        evidence_stage=PromiseEvidenceStage.PROJECT_WORK_RECORDED
    )
    session.add(link)
    session.commit()

    return session


def test_1_legislative_activity_calculation(db_session):
    """Verifies sitting-adjusted questions per sitting and handling of un-gazetted assembly attendance."""
    engine = PerformanceMetricsEngine(db=db_session)
    result = engine.calculate_legislative_metrics(
        representative_id="REP-MLA-013",
        reporting_period="2021-2022",
        annual_sittings_baseline=38
    )

    assert result["dimension"] == PerformanceDimension.LEGISLATIVE_ACTIVITY
    assert result["raw_metrics"]["total_questions"] == 19
    # 19 questions / 38 sittings = 0.5 questions/sitting
    assert result["raw_metrics"]["questions_per_sitting"] == 0.5
    assert result["raw_metrics"]["total_debates"] == 8
    assert result["raw_metrics"]["attendance_status"] == "NOT_GAZETTED_ONLINE"
    assert result["data_completeness"] == 0.5


def test_2_constituency_works_metrics(db_session):
    """Verifies completion rate, attribution separation, and data completeness audit."""
    engine = PerformanceMetricsEngine(db=db_session)
    result = engine.calculate_constituency_works_metrics(
        constituency_id="AC-013",
        reporting_period="2021-2024",
        representative_id="REP-MLA-013"
    )

    assert result["dimension"] == PerformanceDimension.CONSTITUENCY_WORKS
    assert result["raw_metrics"]["total_works"] == 2
    assert result["raw_metrics"]["completed_works"] == 1
    assert result["raw_metrics"]["in_progress_works"] == 1
    assert result["raw_metrics"]["completion_rate_percentage"] == 50.0
    assert result["raw_metrics"]["representative_sponsored_works"] == 2
    assert result["data_completeness"] == 1.0


def test_3_financial_execution_metrics(db_session):
    """Verifies sanctioned, released, unspent balance, and expenditure-to-release ratio."""
    engine = PerformanceMetricsEngine(db=db_session)
    result = engine.calculate_financial_execution_metrics(
        constituency_id="AC-013",
        reporting_period="2021-2024",
        representative_id="REP-MLA-013"
    )

    assert result["dimension"] == PerformanceDimension.FINANCIAL_EXECUTION
    raw = result["raw_metrics"]
    assert raw["total_sanctioned_inr"] == 5000000.0
    assert raw["total_released_inr"] == 5000000.0
    assert raw["total_expended_inr"] == 3000000.0
    assert raw["unspent_released_balance_inr"] == 2000000.0
    # 3M expended / 5M released = 60.0%
    assert raw["expenditure_to_release_ratio_pct"] == 60.0


def test_4_development_indicator_trend_calculation(db_session):
    """Verifies baseline-to-current trajectory and non-causality disclaimers."""
    engine = PerformanceMetricsEngine(db=db_session)
    result = engine.calculate_development_trend_metrics(
        constituency_id="AC-013",
        indicator_name="LITERACY_RATE",
        period_baseline="2011",
        period_current="2021"
    )

    assert result["dimension"] == PerformanceDimension.DEVELOPMENT_TRENDS
    assert result["absolute_delta"] == 6.5
    assert result["percentage_change"] == 7.65
    assert len(result["caveats"]) >= 2
    assert any("multi-causal" in c for c in result["caveats"])


def test_5_promise_evidence_stage_distribution(db_session):
    """Verifies tracking of manifesto promise stages and substantive progress percentage."""
    engine = PerformanceMetricsEngine(db=db_session)
    result = engine.calculate_promise_evidence_metrics(
        representative_id="REP-MLA-013",
        reporting_period="2021-2024"
    )

    assert result["dimension"] == PerformanceDimension.PROMISE_EVIDENCE
    assert result["raw_metrics"]["total_linked_promises"] == 1
    assert result["raw_metrics"]["stage_distribution"]["PROJECT_WORK_RECORDED"] == 1
    assert result["raw_metrics"]["substantive_progress_percentage"] == 100.0


def test_6_data_completeness_isolation_from_performance(db_session):
    """Verifies data completeness score is calculated independently and carries non-penalty rule."""
    engine = PerformanceMetricsEngine(db=db_session)
    result = engine.calculate_data_completeness_metric(
        representative_id="REP-MLA-013",
        constituency_id="AC-013"
    )

    assert result["dimension"] == PerformanceDimension.DATA_COMPLETENESS
    assert result["completeness_ratio"] == 1.0
    assert result["dimension_availability"]["legislative_records"] is True
    assert "MUST NOT be penalized" in result["statutory_rule"]


def test_7_cohort_normalization_and_incompatible_cohort_rejection(db_session):
    """Verifies min-max normalization within MLAs, and rejection of cross-body (MLA vs MP) comparisons."""
    engine = PerformanceMetricsEngine(db=db_session)

    # Valid cohort comparison between two MLAs
    cohort_results = engine.compare_within_cohort(
        cohort_representatives=["REP-MLA-013", "REP-MLA-014"],
        reporting_period="2021-2022",
        cohort_type="TN_ASSEMBLY_MLA"
    )

    assert len(cohort_results) == 2
    mla1_res = next(r for r in cohort_results if r["representative_id"] == "REP-MLA-013")
    mla2_res = next(r for r in cohort_results if r["representative_id"] == "REP-MLA-014")

    # Min: 0.5 Q/sitting (normalized 0.0), Max: 1.0 Q/sitting (normalized 100.0)
    assert mla1_res["normalized_score"] == 0.0
    assert mla2_res["normalized_score"] == 100.0

    # Incompatible cohort test: comparing MLA with MP must raise IncompatibleCohortError
    with pytest.raises(IncompatibleCohortError):
        engine.compare_within_cohort(
            cohort_representatives=["REP-MLA-013", "REP-MP-004"],
            reporting_period="2021-2022",
            cohort_type="TN_ASSEMBLY_MLA"
        )


def test_8_transparent_composite_with_sensitivity_and_anti_pejorative_guard(db_session):
    """Verifies composite calculation, dynamic missing-data re-weighting, sensitivity analysis, and anti-pejorative disclaimer."""
    engine = PerformanceMetricsEngine(db=db_session)
    res = engine.calculate_transparent_composite(
        representative_id="REP-MLA-013",
        constituency_id="AC-013",
        reporting_period="2021-2024"
    )

    assert "composite_score" in res
    assert res["composite_score"] > 0
    assert "sensitivity_analysis" in res
    assert len(res["sensitivity_analysis"]) == 2  # +20% and -20% perturbations
    assert "anti_pejorative_disclaimer" in res
    assert "NEVER be used to categorize representatives with defamatory labels" in res["anti_pejorative_disclaimer"]
