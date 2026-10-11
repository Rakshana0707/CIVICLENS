"""
Unit tests for Phase 6 Constituency Works and Development Tracking Pipeline.

Tests:
1. Monetary totals, release ratios, and unspent balance calculations.
2. Missing dates detection (completed projects without completion_date, sanctioned without approval_date).
3. Conflicting statuses and audit cross-referencing (portal completion vs audit incomplete).
4. Monetary expenditure overrun conflict flagging.
5. Attribution boundaries (ensuring executive projects are not attributed to representatives).
6. Geographic mapping and constituency aggregation.
7. Duplicate project updates and idempotency.
"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.database.base_class import Base
from backend.models.representative import (
    Representative,
    Constituency,
    ConstituencyWork,
    WorkProjectStatus,
    AttributionType,
    RepresentativeType,
    ConstituencyType
)
from backend.services.constituency_works import (
    ConstituencyWorksService,
    ConflictingStatusError
)


@pytest.fixture
def db_session():
    """In-memory SQLite database session for isolated testing."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    # Pre-populate sample constituency and representative
    const = Constituency(
        constituency_id="AC-013",
        official_name="Kolathur",
        constituency_type=ConstituencyType.ASSEMBLY,
        district="Chennai"
    )
    rep = Representative(
        representative_id="REP-MLA-013",
        official_name="M. K. Stalin",
        representative_type=RepresentativeType.MLA,
        constituency_id="AC-013"
    )
    session.add_all([const, rep])
    session.commit()

    yield session
    session.close()


def test_1_monetary_totals_and_unspent_balance(db_session):
    service = ConstituencyWorksService(db=db_session)

    # Work 1: Fully completed MLACDS work
    service.record_work(
        work_id="WORK-MLACDS-01",
        constituency_id="AC-013",
        representative_id="REP-MLA-013",
        scheme_id="MLACDS",
        project_description="Construction of modern library building",
        sanctioned_amount=2500000.0,
        released_amount=2500000.0,
        reported_expenditure=2450000.0,
        approval_date="2022-06-15",
        completion_date="2023-01-20",
        project_status=WorkProjectStatus.REPORTED_COMPLETED,
        attribution_type=AttributionType.REPRESENTATIVE_SPONSORED
    )

    # Work 2: Work in progress MLACDS work with unspent balance
    service.record_work(
        work_id="WORK-MLACDS-02",
        constituency_id="AC-013",
        representative_id="REP-MLA-013",
        scheme_id="MLACDS",
        project_description="Laying of CC paver roads in Ward 65",
        sanctioned_amount=1500000.0,
        released_amount=1000000.0,
        reported_expenditure=400000.0,
        approval_date="2023-02-10",
        completion_date=None,
        project_status=WorkProjectStatus.WORK_IN_PROGRESS,
        attribution_type=AttributionType.REPRESENTATIVE_SPONSORED
    )

    summary = service.calculate_constituency_summary(constituency_id="AC-013", scheme_id="MLACDS")

    assert summary["total_projects"] == 2
    assert summary["financial_summary"]["total_sanctioned_inr"] == 4000000.0
    assert summary["financial_summary"]["total_released_inr"] == 3500000.0
    assert summary["financial_summary"]["total_expenditure_inr"] == 2850000.0
    # Unspent balance = 3,500,000 - 2,850,000 = 650,000
    assert summary["financial_summary"]["unspent_balance_inr"] == 650000.0
    # Pending release = 4,000,000 - 3,500,000 = 500,000
    assert summary["financial_summary"]["unreleased_funds_inr"] == 500000.0
    assert summary["output_metrics"]["total_completed_projects"] == 1


def test_2_missing_dates_flagged_as_data_quality_issues(db_session):
    service = ConstituencyWorksService(db=db_session)

    # Work completed without completion_date
    w1 = service.record_work(
        work_id="WORK-DATE-01",
        constituency_id="AC-013",
        scheme_id="MLACDS",
        project_description="Stormwater drain upgrade",
        sanctioned_amount=800000.0,
        released_amount=800000.0,
        reported_expenditure=780000.0,
        approval_date="2022-09-01",
        completion_date=None,  # Missing completion date on completed project
        project_status=WorkProjectStatus.REPORTED_COMPLETED
    )
    assert any("MISSING_COMPLETION_DATE" in issue for issue in w1.data_quality_issues)

    # Work active without approval_date
    w2 = service.record_work(
        work_id="WORK-DATE-02",
        constituency_id="AC-013",
        scheme_id="MLACDS",
        project_description="High-mast lamp installation",
        sanctioned_amount=500000.0,
        approval_date=None,  # Missing approval date on sanctioned work
        project_status=WorkProjectStatus.SANCTIONED
    )
    assert any("MISSING_APPROVAL_DATE" in issue for issue in w2.data_quality_issues)


def test_3_conflicting_statuses_and_audit_cross_referencing(db_session):
    service = ConstituencyWorksService(db=db_session)

    # Record portal claim: REPORTED_COMPLETED
    service.record_work(
        work_id="WORK-AUDIT-01",
        constituency_id="AC-013",
        scheme_id="MPLADS",
        project_description="Community health center extension ward",
        sanctioned_amount=3000000.0,
        released_amount=3000000.0,
        reported_expenditure=3000000.0,
        approval_date="2021-08-10",
        completion_date="2022-12-15",
        project_status=WorkProjectStatus.REPORTED_COMPLETED
    )

    # Audit report contradicts portal claim: Work is still incomplete on ground
    verified_work = service.cross_reference_verification(
        work_id="WORK-AUDIT-01",
        independent_status=WorkProjectStatus.WORK_IN_PROGRESS,
        audit_source_id="AUDIT-CAG-TN-2023",
        audit_notes="Inspection on 2023-03 found civil structure unpainted and electrical work pending."
    )

    assert verified_work.has_conflicting_status is True
    assert verified_work.verification_source == "AUDIT-CAG-TN-2023"
    assert any("AUDIT_STATUS_CONFLICT" in issue for issue in verified_work.data_quality_issues)


def test_4_monetary_expenditure_overrun_conflict_flagging(db_session):
    service = ConstituencyWorksService(db=db_session)

    # Expenditure ₹3,500,000 exceeds released funds ₹3,000,000
    work = service.record_work(
        work_id="WORK-OVERRUN-01",
        constituency_id="AC-013",
        scheme_id="MLACDS",
        project_description="Culvert widening project",
        sanctioned_amount=3000000.0,
        released_amount=3000000.0,
        reported_expenditure=3500000.0,  # Overrun
        approval_date="2022-04-10",
        project_status=WorkProjectStatus.WORK_IN_PROGRESS
    )

    assert work.has_conflicting_status is True
    assert any("EXPENDITURE_EXCEEDS_RELEASE" in issue for issue in work.data_quality_issues)


def test_5_attribution_separation_for_executive_projects(db_session):
    service = ConstituencyWorksService(db=db_session)

    # Executive State Project (State Highway PWD flyover)
    # Even if representative_id is passed, service MUST clear it to prevent false attribution
    work = service.record_work(
        work_id="WORK-EXEC-01",
        constituency_id="AC-013",
        representative_id="REP-MLA-013",  # Passed by caller
        scheme_id="STATE_HIGHWAYS_PWD",
        project_description="Construction of Grade Separator at Retteri Junction",
        sanctioned_amount=45000000.0,
        released_amount=40000000.0,
        reported_expenditure=38000000.0,
        approval_date="2020-01-15",
        project_status=WorkProjectStatus.REPORTED_COMPLETED,
        attribution_type=AttributionType.EXECUTIVE_STATE_PROJECT
    )

    # Critical requirement: representative_id must be cleared for executive projects
    assert work.representative_id is None
    assert work.attribution_type == AttributionType.EXECUTIVE_STATE_PROJECT


def test_6_geographic_mapping_and_constituency_aggregation(db_session):
    service = ConstituencyWorksService(db=db_session)

    # Add a second constituency (Edappadi)
    const2 = Constituency(
        constituency_id="AC-115",
        official_name="Edappadi",
        constituency_type=ConstituencyType.ASSEMBLY,
        district="Salem"
    )
    db_session.add(const2)
    db_session.commit()

    service.record_work(
        work_id="WORK-EDP-01",
        constituency_id="AC-115",
        scheme_id="MLACDS",
        project_description="Drinking water borewell and overhead tank",
        sanctioned_amount=1200000.0,
        released_amount=1200000.0,
        reported_expenditure=1200000.0,
        approval_date="2022-05-10",
        completion_date="2022-11-20",
        project_status=WorkProjectStatus.REPORTED_COMPLETED
    )

    summary_kolathur = service.calculate_constituency_summary("AC-013")
    summary_edappadi = service.calculate_constituency_summary("AC-115")

    assert summary_kolathur["constituency_id"] == "AC-013"
    assert summary_edappadi["constituency_id"] == "AC-115"
    assert summary_edappadi["total_projects"] == 1
    assert summary_edappadi["financial_summary"]["total_sanctioned_inr"] == 1200000.0


def test_7_duplicate_project_updates_and_idempotency(db_session):
    service = ConstituencyWorksService(db=db_session)

    # Initial record
    w1 = service.record_work(
        work_id="WORK-DUP-01",
        constituency_id="AC-013",
        scheme_id="MLACDS",
        project_description="Primary school building compound wall",
        sanctioned_amount=600000.0,
        project_status=WorkProjectStatus.PROPOSED
    )
    assert w1.project_status == WorkProjectStatus.PROPOSED

    # Update with progress
    w2 = service.record_work(
        work_id="WORK-DUP-01",
        constituency_id="AC-013",
        scheme_id="MLACDS",
        project_description="Primary school building compound wall",
        sanctioned_amount=600000.0,
        released_amount=600000.0,
        reported_expenditure=550000.0,
        approval_date="2022-10-01",
        completion_date="2023-02-15",
        project_status=WorkProjectStatus.REPORTED_COMPLETED
    )

    assert w2.work_id == "WORK-DUP-01"
    assert w2.project_status == WorkProjectStatus.REPORTED_COMPLETED
    # Count must remain 1
    total_count = db_session.query(ConstituencyWork).filter(ConstituencyWork.work_id == "WORK-DUP-01").count()
    assert total_count == 1
