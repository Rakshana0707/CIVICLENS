"""
Unit tests for Phase 6 Legislative Activity Analysis Pipeline.

Tests:
1. MP parliamentary activity calculation with officially published attendance.
2. MLA assembly activity calculation with unavailable attendance handling (ensuring None, not 0%).
3. Explicit distinction between zero activity and unavailable records.
4. Cross-institutional comparison caution and normalization between MPs and MLAs.
5. Traceable source references retention.
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
    LegislativeActivity,
    LegislativeActivityType,
    DataQualityStatus,
    RepresentativeType,
    ConstituencyType
)
from backend.services.legislative_activity import (
    LegislativeActivityService,
    InstitutionalContext
)


@pytest.fixture
def db_session():
    """In-memory SQLite database session for isolated testing."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    # Pre-populate sample representative records
    rep_mp = Representative(
        representative_id="REP-MP-001",
        official_name="Dr. Kalanidhi Veeraswamy",
        representative_type=RepresentativeType.LOK_SABHA_MP,
        term_start="2019-05-23"
    )
    rep_mla = Representative(
        representative_id="REP-MLA-013",
        official_name="M. K. Stalin",
        representative_type=RepresentativeType.MLA,
        term_start="2021-05-07"
    )
    session.add_all([rep_mp, rep_mla])
    session.commit()

    yield session
    session.close()


def test_1_record_and_calculate_mp_parliamentary_activity(db_session):
    service = LegislativeActivityService(db=db_session)

    # Record Lok Sabha MP activities
    service.record_activity(
        activity_id="ACT-MP-001-Q1",
        representative_id="REP-MP-001",
        legislative_body="LOK_SABHA",
        session="17th Lok Sabha - Session 11",
        activity_type=LegislativeActivityType.QUESTION_STARRED,
        activity_date="2023-03-15",
        count=1,
        title_subject="Desalination Projects in Chennai",
        ministry_or_department="Ministry of Jal Shakti",
        source_document_id="DOC-SANSAD-Q1420",
        source_reference="Lok Sabha Starred Q.No 1420"
    )

    service.record_activity(
        activity_id="ACT-MP-001-Q2",
        representative_id="REP-MP-001",
        legislative_body="LOK_SABHA",
        session="17th Lok Sabha - Session 11",
        activity_type=LegislativeActivityType.QUESTION_UNSTARRED,
        activity_date="2023-03-20",
        count=3,
        title_subject="Coastal Aquaculture Subsidies",
        ministry_or_department="Ministry of Fisheries",
        source_document_id="DOC-SANSAD-Q2100",
        source_reference="Lok Sabha Unstarred Q.No 2100"
    )

    service.record_activity(
        activity_id="ACT-MP-001-DEB1",
        representative_id="REP-MP-001",
        legislative_body="LOK_SABHA",
        session="17th Lok Sabha - Session 11",
        activity_type=LegislativeActivityType.DEBATE,
        activity_date="2023-03-22",
        count=1,
        title_subject="Discussion on General Budget 2023-24",
        source_document_id="DOC-SANSAD-DEB-03",
        source_reference="Lok Sabha Debates, 22-03-2023, col. 104"
    )

    # Official Attendance recorded (86.0%)
    service.record_activity(
        activity_id="ACT-MP-001-ATT",
        representative_id="REP-MP-001",
        legislative_body="LOK_SABHA",
        session="17th Lok Sabha - Session 11",
        activity_type=LegislativeActivityType.ATTENDANCE,
        value=86.0,
        source_document_id="DOC-SANSAD-ATT-S11",
        source_reference="Sansad Attendance Register Session 11"
    )

    summary = service.calculate_summary(
        representative_id="REP-MP-001",
        session="17th Lok Sabha - Session 11"
    )

    assert summary["starred_questions_count"] == 1
    assert summary["unstarred_questions_count"] == 3
    assert summary["total_questions_count"] == 4
    assert summary["debates_and_speeches_count"] == 1
    assert summary["attendance"]["percentage"] == 86.0
    assert summary["attendance"]["is_available"] is True
    assert summary["attendance"]["status"] == "VERIFIED"
    assert summary["source_references_count"] >= 3


def test_2_record_and_calculate_mla_assembly_activity_with_unavailable_attendance(db_session):
    """
    Test TNLA MLA participation where attendance register is NOT publicly published online.
    MUST return attendance.percentage = None and status = 'UNAVAILABLE' (never 0.0%).
    """
    service = LegislativeActivityService(db=db_session)

    # Record MLA debates and questions
    service.record_activity(
        activity_id="ACT-MLA-013-DEB1",
        representative_id="REP-MLA-013",
        legislative_body="TN_ASSEMBLY",
        session="16th Assembly - Session 4",
        activity_type=LegislativeActivityType.DEBATE,
        activity_date="2023-04-12",
        count=2,
        title_subject="Discussion on Demands for Grants - School Education",
        source_document_id="DOC-TNLA-2023-D4",
        source_reference="TNLA Hansard 12-04-2023, p. 28-34"
    )

    service.record_activity(
        activity_id="ACT-MLA-013-CALL1",
        representative_id="REP-MLA-013",
        legislative_body="TN_ASSEMBLY",
        session="16th Assembly - Session 4",
        activity_type=LegislativeActivityType.CALL_ATTENTION,
        activity_date="2023-04-15",
        count=1,
        title_subject="Call Attention on Drinking Water Supply in North Chennai",
        source_document_id="DOC-TNLA-2023-CA1",
        source_reference="TNLA Proceedings 15-04-2023, item 4"
    )

    # Mark attendance as UNAVAILABLE as it is not gazetted online
    service.record_unavailable_indicator(
        representative_id="REP-MLA-013",
        legislative_body="TN_ASSEMBLY",
        session="16th Assembly - Session 4",
        activity_type=LegislativeActivityType.ATTENDANCE,
        reason="TN Legislative Assembly does not publish daily individual member attendance online."
    )

    summary = service.calculate_summary(
        representative_id="REP-MLA-013",
        session="16th Assembly - Session 4"
    )

    assert summary["debates_and_speeches_count"] == 2
    assert summary["call_attention_motions_count"] == 1
    # Critical requirement: Attendance must NOT be 0%
    assert summary["attendance"]["percentage"] is None
    assert summary["attendance"]["is_available"] is False
    assert summary["attendance"]["status"] == "UNAVAILABLE"
    assert "Attendance registers are maintained internally" in summary["attendance"]["note"]


def test_3_distinguish_zero_activity_from_unavailable_activity(db_session):
    """
    Verifies that 0 recorded activity (e.g., 0 bills introduced) is clearly distinguished
    from unrecorded/unavailable metrics (e.g., unrecorded attendance).
    """
    service = LegislativeActivityService(db=db_session)

    # Record that MP was active, but introduced 0 bills
    service.record_activity(
        activity_id="ACT-MP-001-Q1",
        representative_id="REP-MP-001",
        legislative_body="LOK_SABHA",
        session="17th Lok Sabha - Session 12",
        activity_type=LegislativeActivityType.QUESTION_STARRED,
        count=2,
        source_reference="Sansad Starred Q.No 204"
    )

    # Explicitly mark committee participation as unavailable for this session
    service.record_unavailable_indicator(
        representative_id="REP-MP-001",
        legislative_body="LOK_SABHA",
        session="17th Lok Sabha - Session 12",
        activity_type=LegislativeActivityType.ATTENDANCE,
        reason="Session suspended due to recess; attendance logs not finalized."
    )

    summary = service.calculate_summary(
        representative_id="REP-MP-001",
        session="17th Lok Sabha - Session 12"
    )

    # Zero activity where tracked: bills count is 0
    assert summary["private_member_bills_count"] == 0
    # Unavailable metric: attendance is None, not 0.0%
    assert summary["attendance"]["percentage"] is None
    assert summary["attendance"]["status"] == "UNAVAILABLE"


def test_4_mp_vs_mla_comparison_triggers_institutional_warning(db_session):
    """
    Verifies that comparing an MP and an MLA flags cross-institutional caution
    and refuses uncontextualized raw league tables.
    """
    service = LegislativeActivityService(db=db_session)

    summary_mp = {
        "representative_id": "REP-MP-001",
        "legislative_body": "LOK_SABHA",
        "total_questions_count": 50,
        "debates_and_speeches_count": 12,
        "attendance": {"is_available": True, "percentage": 85.0},
        "institutional_context": InstitutionalContext.get_profile("LOK_SABHA")
    }

    summary_mla = {
        "representative_id": "REP-MLA-013",
        "legislative_body": "TN_ASSEMBLY",
        "total_questions_count": 25,
        "debates_and_speeches_count": 15,
        "attendance": {"is_available": False, "percentage": None},
        "institutional_context": InstitutionalContext.get_profile("TN_ASSEMBLY")
    }

    comp = service.compare_representatives(summary_mp, summary_mla)

    assert comp["is_cross_institutional"] is True
    assert comp["institutional_warning"] is not None
    assert "CROSS-INSTITUTIONAL COMPARISON CAUTION" in comp["institutional_warning"]
    assert "sits approximately 65 days/year" in comp["institutional_warning"]
    assert comp["effectiveness_disclaimer"] is not None

    # Normalized rate: MLA has higher debate rate per sittings despite lower raw count
    norm_debates = comp["comparison_metrics"]["normalized_per_10_sittings"]["debates_per_10_sittings"]
    assert norm_debates["rep_b"] > norm_debates["rep_a"]  # MLA debate rate > MP debate rate per sitting!


def test_5_source_reference_traceability(db_session):
    """
    Verifies that all activity records preserve traceable citations and source references.
    """
    service = LegislativeActivityService(db=db_session)

    service.record_activity(
        activity_id="ACT-TRACE-01",
        representative_id="REP-MP-001",
        legislative_body="LOK_SABHA",
        session="17th Lok Sabha - Session 10",
        activity_type=LegislativeActivityType.QUESTION_STARRED,
        source_document_id="DOC-SANSAD-789",
        source_reference="Sansad Portal Q.No 789 (Starred)"
    )

    summary = service.calculate_summary(
        representative_id="REP-MP-001",
        session="17th Lok Sabha - Session 10"
    )

    assert summary["source_references_count"] == 1
    assert "Sansad Portal Q.No 789 (Starred)" in summary["source_references_sample"]
