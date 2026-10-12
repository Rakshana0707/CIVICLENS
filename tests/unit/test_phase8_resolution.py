"""
Unit Test Suite for Grievance Response & Resolution Evidence Tracker (Phase 8.6)
================================================================================
Verifies:
  1. Separation of All 9 Canonical Lifecycle States
  2. marked_resolved Does NOT Imply Independently Verified
  3. Independent Verification with Corroborating Evidence
  4. Contradicting Evidence Routes to Disputed Status
  5. Unsupported Resolution Claim for Public Work Linkage is Rejected
  6. Supported Public Work Linkage with Evidentiary Tender Reference
  7. Conflicting Status Detection (Reopened vs Marked Resolved)
  8. Incomplete Response Record Handling
  9. SLA Turnaround and Breach Tracking
  10. Missing Response / Unanswered Backlog Detection
"""

import pytest
from datetime import datetime, timezone, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.models.civic_issue import (
    Base,
    CivicIssue,
    GrievanceRecord,
    ResponseRecord,
    ResolutionEvidence,
    PublicWork,
    IssueEvent,
    CivicTrackingState,
    CivicIssueStatus,
    ResponseActionType,
    ResolutionVerificationStatus,
    EvidenceType,
    DataQualityIssue,
    IssueCategory,
    IssueCategoryEnum,
    CivicDepartment,
    AdministrativeArea,
    AdministrativeLevel
)
from backend.services.civic_resolution_service import (
    CivicResolutionTrackerService,
    ResolutionRecordPayload
)
from tests.fixtures.phase8_fixtures import (
    MOCK_CATEGORIES,
    MOCK_DEPARTMENTS,
    MOCK_AREAS
)


@pytest.fixture(scope="function")
def db_session():
    """In-memory SQLite database session populated with taxonomy fixtures."""
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    # Seed categories
    for cat_data in MOCK_CATEGORIES:
        cat = IssueCategory(
            code=IssueCategoryEnum(cat_data["code"]),
            name_en=cat_data["name_en"],
            name_ta=cat_data["name_ta"],
            default_department_code=cat_data.get("default_department_code"),
            priority_weight=cat_data.get("priority_weight", 1.0)
        )
        session.add(cat)

    # Seed departments
    for dept_data in MOCK_DEPARTMENTS:
        dept = CivicDepartment(
            code=dept_data["code"],
            name_en=dept_data["name_en"],
            name_ta=dept_data["name_ta"],
            portal_id=dept_data["portal_id"],
            jurisdiction_level=dept_data["jurisdiction_level"],
            contact_email_public=dept_data["contact_email_public"],
            helpline_number=dept_data["helpline_number"]
        )
        session.add(dept)

    # Seed administrative areas
    for area_data in MOCK_AREAS:
        area = AdministrativeArea(
            area_code=area_data["area_code"],
            name_en=area_data["name_en"],
            name_ta=area_data["name_ta"],
            administrative_level=AdministrativeLevel(area_data["administrative_level"]),
            lgd_code=area_data.get("lgd_code"),
            latitude=area_data.get("latitude"),
            longitude=area_data.get("longitude"),
            population=area_data.get("population")
        )
        session.add(area)

    session.commit()
    yield session
    session.close()


@pytest.fixture
def sample_civic_issue(db_session):
    """Provisions a baseline CivicIssue for resolution tracking tests."""
    cat = db_session.query(IssueCategory).filter_by(code=IssueCategoryEnum.ROADS).first()
    dept = db_session.query(CivicDepartment).filter_by(code="DEPT_GCC").first()
    area = db_session.query(AdministrativeArea).filter_by(area_code="ADM-TN-GCC-WARD-174").first()

    reported_dt = datetime(2024, 3, 1, 10, 0, tzinfo=timezone.utc)
    target_dt = reported_dt + timedelta(hours=48)  # 48h SLA

    issue = CivicIssue(
        issue_code="ISSUE-2024-TEST-001",
        title="Deep Crater on 4th Main Road Besant Nagar",
        description="Hazardous pothole causing vehicle accidents near bus stop.",
        category_id=cat.id,
        department_id=dept.id,
        administrative_area_id=area.id,
        reported_date=reported_dt,
        target_resolution_date=target_dt,
        status=CivicIssueStatus.OPEN,
        resolution_verification_status=ResolutionVerificationStatus.PENDING_VERIFICATION,
        is_test_fixture=True
    )
    db_session.add(issue)
    db_session.commit()
    return issue


# ---------------------------------------------------------------------------
# Test 1: Separation of All 9 Canonical Lifecycle States
# ---------------------------------------------------------------------------
def test_1_track_nine_canonical_lifecycle_states():
    assert CivicResolutionTrackerService.parse_reported_status("Submitted") == CivicTrackingState.SUBMITTED
    assert CivicResolutionTrackerService.parse_reported_status("Registered") == CivicTrackingState.ACKNOWLEDGED
    assert CivicResolutionTrackerService.parse_reported_status("In Progress") == CivicTrackingState.UNDER_REVIEW
    assert CivicResolutionTrackerService.parse_reported_status("Action Taken") == CivicTrackingState.ACTION_REPORTED
    assert CivicResolutionTrackerService.parse_reported_status("Completed") == CivicTrackingState.MARKED_RESOLVED
    assert CivicResolutionTrackerService.parse_reported_status("தீர்க்கப்பட்டது") == CivicTrackingState.MARKED_RESOLVED
    assert CivicResolutionTrackerService.parse_reported_status("Reopened") == CivicTrackingState.REOPENED
    assert CivicResolutionTrackerService.parse_reported_status("Disputed") == CivicTrackingState.DISPUTED
    assert CivicResolutionTrackerService.parse_reported_status("Garbled xyz") == CivicTrackingState.UNKNOWN
    assert CivicResolutionTrackerService.parse_reported_status(None) == CivicTrackingState.UNKNOWN


# ---------------------------------------------------------------------------
# Test 2: marked_resolved Does NOT Imply Independently Verified
# ---------------------------------------------------------------------------
def test_2_marked_resolved_does_not_imply_verified(db_session, sample_civic_issue):
    payload = ResolutionRecordPayload(
        issue_id=sample_civic_issue.id,
        response_date=datetime(2024, 3, 2, 12, 0, tzinfo=timezone.utc),
        response_summary="Pothole patchwork completed by Zonal Contractor.",
        reported_status="completed"
    )

    response = CivicResolutionTrackerService.record_official_response(
        db_session=db_session,
        payload=payload,
        is_test_fixture=True
    )
    db_session.commit()

    # Reported status is marked_resolved
    assert response.reported_status == CivicTrackingState.MARKED_RESOLVED.value
    # CRITICAL DIRECTIVE: Verification status must remain PENDING_VERIFICATION!
    assert response.verification_status == ResolutionVerificationStatus.PENDING_VERIFICATION
    assert sample_civic_issue.resolution_verification_status == ResolutionVerificationStatus.PENDING_VERIFICATION
    # Issue status is marked as RESOLVED (source reports closure), but NOT VERIFIED_RESOLVED
    assert sample_civic_issue.status == CivicIssueStatus.RESOLVED


# ---------------------------------------------------------------------------
# Test 3: Independent Verification with Corroborating Evidence
# ---------------------------------------------------------------------------
def test_3_independent_verification_with_corroborating_evidence(db_session, sample_civic_issue):
    payload = ResolutionRecordPayload(
        issue_id=sample_civic_issue.id,
        response_date=datetime(2024, 3, 2, 12, 0, tzinfo=timezone.utc),
        response_summary="Pothole restored by GCC Works division.",
        reported_status="completed"
    )
    response = CivicResolutionTrackerService.record_official_response(
        db_session=db_session,
        payload=payload,
        is_test_fixture=True
    )
    db_session.commit()

    # Supply independent corroborating evidence (Work completion certificate)
    evidence, verified = CivicResolutionTrackerService.verify_resolution_with_evidence(
        db_session=db_session,
        response_id=response.id,
        evidence_type=EvidenceType.COMPLETION_CERTIFICATE,
        title="GCC Work Completion Certificate No. 4481",
        description="Site inspection confirmed asphalt resurfaced. Signed by AE.",
        evidence_url="https://chennaicorporation.gov.in/certs/4481.pdf",
        sha256_hash="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        is_corroborating=True,
        verified_by="Independent Citizen Auditor",
        is_test_fixture=True
    )
    db_session.commit()

    assert verified is True
    assert response.verification_status == ResolutionVerificationStatus.VERIFIED
    assert response.reported_status == CivicTrackingState.INDEPENDENTLY_VERIFIED_RESOLVED.value
    assert sample_civic_issue.resolution_verification_status == ResolutionVerificationStatus.VERIFIED
    assert sample_civic_issue.status == CivicIssueStatus.VERIFIED_RESOLVED

    # Check audit event
    event = db_session.query(IssueEvent).filter_by(
        civic_issue_id=sample_civic_issue.id,
        event_type="INDEPENDENTLY_VERIFIED_RESOLVED"
    ).first()
    assert event is not None


# ---------------------------------------------------------------------------
# Test 4: Contradicting Evidence Routes to Disputed Status
# ---------------------------------------------------------------------------
def test_4_contradicting_evidence_routes_to_disputed(db_session, sample_civic_issue):
    payload = ResolutionRecordPayload(
        issue_id=sample_civic_issue.id,
        response_date=datetime(2024, 3, 2, 12, 0, tzinfo=timezone.utc),
        response_summary="Closed by helpline operator as resolved.",
        reported_status="completed"
    )
    response = CivicResolutionTrackerService.record_official_response(
        db_session=db_session,
        payload=payload,
        is_test_fixture=True
    )
    db_session.commit()

    # Supply contradicting evidence (Citizen field audit shows crater still exists)
    evidence, verified = CivicResolutionTrackerService.verify_resolution_with_evidence(
        db_session=db_session,
        response_id=response.id,
        evidence_type=EvidenceType.CITIZEN_AUDIT,
        title="Field Inspection Photograph",
        description="Pothole has NOT been repaired; water filled crater remains unaddressed.",
        is_corroborating=False,  # Contradicts claimed resolution!
        verified_by="Ward 174 Residents Welfare Association",
        is_test_fixture=True
    )
    db_session.commit()

    assert verified is False
    assert response.verification_status == ResolutionVerificationStatus.CONTRADICTED
    assert response.reported_status == CivicTrackingState.DISPUTED.value
    assert sample_civic_issue.resolution_verification_status == ResolutionVerificationStatus.CONTRADICTED
    assert sample_civic_issue.status == CivicIssueStatus.DISPUTED


# ---------------------------------------------------------------------------
# Test 5: Unsupported Resolution Claim for Public Work Linkage is Rejected
# ---------------------------------------------------------------------------
def test_5_unsupported_resolution_claim_public_work_linkage_rejected(db_session, sample_civic_issue):
    # Public work in unrelated area without matching tender reference
    work = PublicWork(
        work_code="PW-2024-UNRELATED-99",
        work_title="Bridge expansion in Tambaram",
        executing_agency="Highways Dept",
        tender_ref="TNDR-TAMB-88",
        status="COMPLETED",
        completion_date=datetime(2024, 3, 10, tzinfo=timezone.utc),
        is_test_fixture=True
    )
    db_session.add(work)
    db_session.commit()

    # Attempt to claim this public work resolved the Besant Nagar pothole without evidence
    success, reason = CivicResolutionTrackerService.validate_and_link_public_work(
        db_session=db_session,
        issue_id=sample_civic_issue.id,
        public_work_id=work.id,
        tender_reference_match=False,
        explicit_source_reference=None
    )
    db_session.commit()

    # CRITICAL DIRECTIVE: Must be rejected!
    assert success is False
    assert "UNSUPPORTED_RESOLUTION_CLAIM" in reason
    assert work.civic_issue_id is None

    # DataQualityIssue must be logged
    dq = db_session.query(DataQualityIssue).filter_by(
        civic_issue_id=sample_civic_issue.id,
        issue_type="UNSUPPORTED_RESOLUTION_CLAIM"
    ).first()
    assert dq is not None


# ---------------------------------------------------------------------------
# Test 6: Supported Public Work Linkage with Evidentiary Tender Reference
# ---------------------------------------------------------------------------
def test_6_supported_public_work_linkage(db_session, sample_civic_issue):
    work = PublicWork(
        work_code="PW-2024-BESANT-01",
        work_title="Resurfacing of 4th Main Road Besant Nagar",
        executing_agency="GCC Works Department",
        tender_ref="GCC-ZONE13-2024-T09",
        status="COMPLETED",
        completion_date=datetime(2024, 3, 3, tzinfo=timezone.utc),
        is_test_fixture=True
    )
    db_session.add(work)
    db_session.commit()

    # Link supported by explicit tender reference match
    success, reason = CivicResolutionTrackerService.validate_and_link_public_work(
        db_session=db_session,
        issue_id=sample_civic_issue.id,
        public_work_id=work.id,
        tender_reference_match=True
    )
    db_session.commit()

    assert success is True
    assert work.civic_issue_id == sample_civic_issue.id

    # Event logged
    ev = db_session.query(IssueEvent).filter_by(
        civic_issue_id=sample_civic_issue.id,
        event_type="PUBLIC_WORK_LINKED"
    ).first()
    assert ev is not None


# ---------------------------------------------------------------------------
# Test 7: Conflicting Status Detection (Reopened vs Marked Resolved)
# ---------------------------------------------------------------------------
def test_7_conflicting_status_detection(db_session, sample_civic_issue):
    # 1. Citizen reopens grievance
    payload_reopen = ResolutionRecordPayload(
        issue_id=sample_civic_issue.id,
        response_date=datetime(2024, 3, 2, 10, 0, tzinfo=timezone.utc),
        response_summary="Citizen reopened petition: Pothole patch failed within 24 hours.",
        reported_status="reopened"
    )
    CivicResolutionTrackerService.record_official_response(db_session, payload_reopen, is_test_fixture=True)
    db_session.commit()

    # 2. Portal attempts to log 'completed' without addressing the active reopening
    payload_conflict = ResolutionRecordPayload(
        issue_id=sample_civic_issue.id,
        response_date=datetime(2024, 3, 3, 11, 0, tzinfo=timezone.utc),
        response_summary="Disposed by department system.",
        reported_status="completed"
    )
    resp_conflict = CivicResolutionTrackerService.record_official_response(db_session, payload_conflict, is_test_fixture=True)
    db_session.commit()

    # Must detect status conflict and route to DISPUTED
    assert resp_conflict.reported_status == CivicTrackingState.DISPUTED.value
    assert "Status Conflict" in (resp_conflict.review_notes or "")

    dq = db_session.query(DataQualityIssue).filter_by(
        civic_issue_id=sample_civic_issue.id,
        issue_type="CONFLICTING_STATUS"
    ).first()
    assert dq is not None


# ---------------------------------------------------------------------------
# Test 8: Incomplete Response Record Handling
# ---------------------------------------------------------------------------
def test_8_incomplete_response_record_handling(db_session, sample_civic_issue):
    payload_empty = ResolutionRecordPayload(
        issue_id=sample_civic_issue.id,
        response_date=datetime(2024, 3, 2, 10, 0, tzinfo=timezone.utc),
        response_summary="",  # Incomplete response!
        reported_status="action taken"
    )

    resp_incomplete = CivicResolutionTrackerService.record_official_response(db_session, payload_empty, is_test_fixture=True)
    db_session.commit()

    assert resp_incomplete.reported_status == CivicTrackingState.UNKNOWN.value
    assert "Incomplete Record" in (resp_incomplete.review_notes or "")

    dq = db_session.query(DataQualityIssue).filter_by(
        civic_issue_id=sample_civic_issue.id,
        issue_type="INCOMPLETE_RESPONSE_RECORD"
    ).first()
    assert dq is not None


# ---------------------------------------------------------------------------
# Test 9: SLA Turnaround & Breach Detection
# ---------------------------------------------------------------------------
def test_9_sla_turnaround_and_breach_detection(db_session, sample_civic_issue):
    # SLA deadline was reported_date + 48h (2024-03-03 10:00:00 UTC)
    # Action taken on 2024-03-05 10:00:00 UTC (48 hours late!)
    late_resp_dt = sample_civic_issue.reported_date + timedelta(hours=96)

    payload_late = ResolutionRecordPayload(
        issue_id=sample_civic_issue.id,
        response_date=late_resp_dt,
        response_summary="Pothole patchwork completed after delay due to rain.",
        reported_status="completed"
    )
    resp_late = CivicResolutionTrackerService.record_official_response(db_session, payload_late, is_test_fixture=True)
    db_session.commit()

    assert resp_late.sla_breached is True
    assert resp_late.delay_hours == 48.0


# ---------------------------------------------------------------------------
# Test 10: Missing Response / Backlog Detection
# ---------------------------------------------------------------------------
def test_10_missing_response_detection(db_session):
    # Issue reported 10 days ago with zero responses logged in DB
    cat = db_session.query(IssueCategory).filter_by(code=IssueCategoryEnum.STREETLIGHTS).first()
    dept = db_session.query(CivicDepartment).filter_by(code="DEPT_GCC").first()

    issue_backlog = CivicIssue(
        issue_code="ISSUE-2024-BACKLOG-01",
        title="Dark street light not glowing for 10 days",
        description="Flickering streetlight outside government dispensary.",
        category_id=cat.id,
        department_id=dept.id,
        reported_date=datetime(2024, 3, 1, 10, 0, tzinfo=timezone.utc),
        target_resolution_date=datetime(2024, 3, 2, 10, 0, tzinfo=timezone.utc),  # 24h SLA expired
        status=CivicIssueStatus.OPEN,
        is_test_fixture=True
    )
    db_session.add(issue_backlog)
    db_session.commit()

    # Query responses
    responses = db_session.query(ResponseRecord).filter_by(civic_issue_id=issue_backlog.id).all()
    assert len(responses) == 0  # Missing response / pending action

    # Issue status remains OPEN
    assert issue_backlog.status == CivicIssueStatus.OPEN
    # Past SLA
    assert datetime(2024, 3, 12, tzinfo=timezone.utc) > issue_backlog.target_resolution_date.replace(tzinfo=timezone.utc)
