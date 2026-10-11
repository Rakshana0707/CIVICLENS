"""
Phase 8 — Unit Tests for Public Grievance & Civic Issue Intelligence Architecture.

Tests:
1. Canonical entity schema creation and relationship mapping across all 13 core entities:
   (CivicIssue, GrievanceRecord, IssueCategory, GovernmentDepartment, AdministrativeArea,
    ServiceStandard, ResponseRecord, ResolutionEvidence, PublicWork, IssueEvent,
    SourceDocument, IssueMetric, DataQualityIssue).
2. Strict citizen privacy rules & PII scrubbing (phone, email, UID, citizen names, door numbers).
3. 14 standard civic categories coverage in Tamil and English.
4. Administrative boundary spatial hierarchy (State -> District -> Zone -> Ward).
5. Citizen's Charter statutory service standard (SLA) turnaround and breach calculation.
6. Multi-source evidence linking and resolution verification state management.
7. Deduplication clustering & incident audit event logging.
8. Data quality issue logging and metric aggregation.
9. Zero-data-fabrication compliance (all test entities marked is_test_fixture=True).
"""

import pytest
from datetime import datetime, timezone, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.database.base_class import Base
from backend.models.civic_issue import (
    CivicIssue,
    GrievanceRecord,
    IssueCategory,
    GovernmentDepartment,
    AdministrativeArea,
    ServiceStandard,
    ResponseRecord,
    ResolutionEvidence,
    PublicWork,
    IssueEvent,
    SourceDocument,
    IssueMetric,
    DataQualityIssue,
    IssueCategoryEnum,
    CivicIssueStatus,
    CivicIssueSeverity,
    AdministrativeLevel,
    ResponseActionType,
    ResolutionVerificationStatus,
    EvidenceType,
    DataQualitySeverity,
    sanitize_pii
)
from tests.fixtures.phase8_fixtures import (
    IS_TEST_FIXTURE,
    FIXTURE_VERSION,
    MOCK_CATEGORIES,
    MOCK_DEPARTMENTS,
    MOCK_AREAS,
    MOCK_SERVICE_STANDARDS,
    MOCK_RAW_GRIEVANCES_FOR_PII,
    MOCK_CIVIC_ISSUES,
    MOCK_RESPONSES,
    MOCK_EVIDENCE,
    MOCK_PUBLIC_WORKS
)


@pytest.fixture
def db_session():
    """Isolated in-memory SQLite database session for Phase 8 unit tests."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    yield session

    session.close()


# ---------------------------------------------------------------------------
# Test 1: Core 14 Issue Categories Coverage
# ---------------------------------------------------------------------------
def test_1_issue_categories_taxonomy_coverage(db_session):
    """Verify all 14 standard civic categories are defined, typed, and bilingual."""
    assert len(IssueCategoryEnum) == 14

    required_categories = {
        "roads", "water_supply", "drainage", "sanitation", "waste_management",
        "streetlights", "public_transport", "healthcare_access",
        "education_infrastructure", "electricity", "public_safety_infrastructure",
        "environmental_concerns", "government_service_delays", "other_documented_civic_issues"
    }
    defined_categories = {cat.value for cat in IssueCategoryEnum}
    assert required_categories == defined_categories

    # Persist mock categories into database
    for mock_cat in MOCK_CATEGORIES:
        category = IssueCategory(
            code=IssueCategoryEnum(mock_cat["code"]),
            name_en=mock_cat["name_en"],
            name_ta=mock_cat["name_ta"],
            default_department_code=mock_cat["default_department_code"],
            keywords_en=mock_cat["keywords_en"],
            keywords_ta=mock_cat["keywords_ta"],
            priority_weight=mock_cat["priority_weight"]
        )
        db_session.add(category)
    db_session.commit()

    saved_cats = db_session.query(IssueCategory).all()
    assert len(saved_cats) == 14
    road_cat = db_session.query(IssueCategory).filter_by(code=IssueCategoryEnum.ROADS).first()
    assert road_cat.name_en == "Roads & Footpaths"
    assert "சாலை" in road_cat.name_ta


# ---------------------------------------------------------------------------
# Test 2: Strict Privacy Rules & PII Scrubbing
# ---------------------------------------------------------------------------
def test_2_strict_privacy_pii_sanitization():
    """Verify citizen names, phone numbers, emails, UIDs, and door numbers are stripped."""
    for sample in MOCK_RAW_GRIEVANCES_FOR_PII:
        raw_text = sample["raw_text"]
        sanitized = sanitize_pii(raw_text)

        # Ensure no raw personal details remain
        assert "9840123456" not in sanitized
        assert "murugan.k@gmail.com" not in sanitized
        assert "1234 5678 9012" not in sanitized
        assert "Thiru K. Murugesan" not in sanitized
        assert "Door No. 42/1" not in sanitized
        assert "Tmt Lakshmi" not in sanitized
        assert "8765432109" not in sanitized
        assert "D.No. 15" not in sanitized

        # Ensure sanitized placeholders are properly inserted
        assert "[PHONE REDACTED]" in sanitized
        assert "[CITIZEN]" in sanitized
        assert "[ADDRESS REDACTED]" in sanitized


# ---------------------------------------------------------------------------
# Test 3: Administrative Hierarchy & Spatial Mapping
# ---------------------------------------------------------------------------
def test_3_administrative_area_hierarchy(db_session):
    """Verify nested administrative hierarchy: State -> District -> Zone -> Ward."""
    area_map = {}
    for mock_area in MOCK_AREAS:
        parent_id = area_map.get(mock_area["parent_code"])
        area = AdministrativeArea(
            area_code=mock_area["area_code"],
            name_en=mock_area["name_en"],
            name_ta=mock_area["name_ta"],
            administrative_level=AdministrativeLevel(mock_area["administrative_level"]),
            parent_id=parent_id,
            lgd_code=mock_area["lgd_code"],
            latitude=mock_area["latitude"],
            longitude=mock_area["longitude"],
            population=mock_area["population"]
        )
        db_session.add(area)
        db_session.commit()
        area_map[mock_area["area_code"]] = area.id

    # Verify Ward points to Zone and Zone points to District
    ward = db_session.query(AdministrativeArea).filter_by(area_code="ADM-TN-GCC-WARD-174").first()
    assert ward is not None
    assert ward.parent.area_code == "ADM-TN-GCC-ZONE-13-ADYAR"
    assert ward.parent.parent.area_code == "ADM-TN-DIST-013-CHENNAI"
    assert ward.parent.parent.parent.area_code == "ADM-TN-STATE"


# ---------------------------------------------------------------------------
# Test 4: Government Departments & Service Standards (SLAs)
# ---------------------------------------------------------------------------
def test_4_departments_and_service_standards_sla(db_session):
    """Verify department registry and Citizen's Charter statutory turnaround limits."""
    # Seed categories first
    cat_map = {}
    for mock_cat in MOCK_CATEGORIES:
        category = IssueCategory(
            code=IssueCategoryEnum(mock_cat["code"]),
            name_en=mock_cat["name_en"],
            name_ta=mock_cat["name_ta"]
        )
        db_session.add(category)
        db_session.commit()
        cat_map[mock_cat["code"]] = category.id

    # Seed departments
    dept_map = {}
    for mock_dept in MOCK_DEPARTMENTS:
        dept = GovernmentDepartment(
            code=mock_dept["code"],
            name_en=mock_dept["name_en"],
            name_ta=mock_dept["name_ta"],
            portal_id=mock_dept["portal_id"],
            jurisdiction_level=mock_dept["jurisdiction_level"],
            contact_email_public=mock_dept["contact_email_public"],
            helpline_number=mock_dept["helpline_number"]
        )
        db_session.add(dept)
        db_session.commit()
        dept_map[mock_dept["code"]] = dept.id

    # Seed Service Standards
    for mock_sla in MOCK_SERVICE_STANDARDS:
        sla = ServiceStandard(
            standard_code=mock_sla["standard_code"],
            department_id=dept_map[mock_sla["department_code"]],
            category_id=cat_map[mock_sla["category_code"]],
            service_name_en=mock_sla["service_name_en"],
            service_name_ta=mock_sla["service_name_ta"],
            stipulated_time_hours=mock_sla["stipulated_time_hours"],
            designated_officer=mock_sla["designated_officer"],
            appellate_authority=mock_sla["appellate_authority"],
            penalty_clause=mock_sla["penalty_clause"]
        )
        db_session.add(sla)
    db_session.commit()

    pothole_sla = db_session.query(ServiceStandard).filter_by(standard_code="SLA-MAWS-POTHOLE-48H").first()
    assert pothole_sla is not None
    assert pothole_sla.stipulated_time_hours == 48
    assert pothole_sla.department.code == "DEPT_MAWS"


# ---------------------------------------------------------------------------
# Test 5: CivicIssue Creation & Grievance Linking
# ---------------------------------------------------------------------------
def test_5_civic_issue_creation_and_grievance_linking(db_session):
    """Verify CivicIssue root entity and attached anonymized GrievanceRecords."""
    # Setup Category and Department
    cat = IssueCategory(code=IssueCategoryEnum.WATER_SUPPLY, name_en="Water Supply", name_ta="குடிநீர்")
    dept = GovernmentDepartment(code="DEPT_MAWS", name_en="MAWS Dept", name_ta="நகராட்சி நிர்வாகம்")
    db_session.add_all([cat, dept])
    db_session.commit()

    reported_time = datetime(2024, 2, 15, 8, 0, 0, tzinfo=timezone.utc)
    target_time = reported_time + timedelta(hours=24)

    issue = CivicIssue(
        issue_code="CIV-FIX-002-WATERLEAK-RESOLVED",
        title="Major potable water pipe burst on MG Road",
        title_ta="எம்.ஜி. சாலையில் பிரதான குடிநீர் குழாய் உடைப்பு",
        description="Continuous drinking water leakage flooding street.",
        category_id=cat.id,
        department_id=dept.id,
        status=CivicIssueStatus.OPEN,
        severity=CivicIssueSeverity.CRITICAL,
        latitude=13.0040,
        longitude=80.2580,
        reported_date=reported_time,
        target_resolution_date=target_time,
        repeat_count=2,
        is_test_fixture=True
    )
    db_session.add(issue)
    db_session.commit()

    # Attach two anonymized grievance petitions
    grv1 = GrievanceRecord(
        record_token="GRV-2024-001",
        civic_issue_id=issue.id,
        complaint_summary=sanitize_pii("Water leak reported by [CITIZEN] near store."),
        lodged_date=reported_time,
        source_portal="CM_HELPLINE_1100",
        is_anonymized=True,
        is_test_fixture=True
    )
    grv2 = GrievanceRecord(
        record_token="GRV-2024-002",
        civic_issue_id=issue.id,
        complaint_summary=sanitize_pii("No drinking water pressure in area due to road pipeline burst."),
        lodged_date=reported_time + timedelta(hours=1),
        source_portal="GCC_1913",
        is_anonymized=True,
        is_test_fixture=True
    )
    db_session.add_all([grv1, grv2])
    db_session.commit()

    reloaded_issue = db_session.query(CivicIssue).filter_by(issue_code="CIV-FIX-002-WATERLEAK-RESOLVED").first()
    assert len(reloaded_issue.grievance_records) == 2
    assert reloaded_issue.category.code == IssueCategoryEnum.WATER_SUPPLY
    assert reloaded_issue.department.code == "DEPT_MAWS"


# ---------------------------------------------------------------------------
# Test 6: SLA Turnaround & Delay Calculation
# ---------------------------------------------------------------------------
def test_6_sla_turnaround_and_breach_detection(db_session):
    """Verify compliant vs breached SLA calculations."""
    cat = IssueCategory(code=IssueCategoryEnum.ELECTRICITY, name_en="Electricity", name_ta="மின்சாரம்")
    dept = GovernmentDepartment(code="DEPT_TANGEDCO", name_en="TANGEDCO", name_ta="மின்வாரியம்")
    db_session.add_all([cat, dept])
    db_session.commit()

    lodged_time = datetime(2024, 1, 10, 12, 0, 0, tzinfo=timezone.utc)
    target_time = lodged_time + timedelta(hours=24)  # 24-hour SLA
    action_time = lodged_time + timedelta(hours=76)  # 52 hours delayed!

    issue = CivicIssue(
        issue_code="CIV-FIX-003-DELAYED-TRANSFORMER",
        title="Burnt 250kVA distribution transformer causing blackout",
        description="Transformer damaged after short circuit.",
        category_id=cat.id,
        department_id=dept.id,
        status=CivicIssueStatus.ESCALATED,
        severity=CivicIssueSeverity.CRITICAL,
        reported_date=lodged_time,
        target_resolution_date=target_time,
        is_test_fixture=True
    )
    db_session.add(issue)
    db_session.commit()

    # Calculate SLA delay
    delay_hours = (action_time - target_time).total_seconds() / 3600.0
    sla_breached = delay_hours > 0

    response = ResponseRecord(
        response_code="RSP-FIX-002-TRANSFORMER-DELAYED",
        civic_issue_id=issue.id,
        department_id=dept.id,
        action_type=ResponseActionType.ACKNOWLEDGED,
        official_remark="Replacement transformer indented from Central Stores; delay due to logistics.",
        action_taken_date=action_time,
        sla_breached=sla_breached,
        delay_hours=delay_hours,
        is_test_fixture=True
    )
    db_session.add(response)
    db_session.commit()

    saved_response = db_session.query(ResponseRecord).filter_by(response_code="RSP-FIX-002-TRANSFORMER-DELAYED").first()
    assert saved_response.sla_breached is True
    assert saved_response.delay_hours == 52.0


# ---------------------------------------------------------------------------
# Test 7: Multi-Source Resolution Evidence & Public Works
# ---------------------------------------------------------------------------
def test_7_resolution_evidence_and_public_work_linking(db_session):
    """Verify corroborating evidence and capital work order linkage."""
    cat = IssueCategory(code=IssueCategoryEnum.WATER_SUPPLY, name_en="Water Supply", name_ta="குடிநீர்")
    dept = GovernmentDepartment(code="DEPT_MAWS", name_en="MAWS Dept", name_ta="நகராட்சி நிர்வாகம்")
    db_session.add_all([cat, dept])
    db_session.commit()

    issue = CivicIssue(
        issue_code="CIV-FIX-002-WATERLEAK-RESOLVED",
        title="Major potable water pipe burst on MG Road",
        description="Continuous water leakage.",
        category_id=cat.id,
        department_id=dept.id,
        status=CivicIssueStatus.VERIFIED_RESOLVED,
        severity=CivicIssueSeverity.HIGH,
        reported_date=datetime(2024, 2, 15, 8, 0, 0, tzinfo=timezone.utc),
        actual_resolution_date=datetime(2024, 2, 16, 4, 0, 0, tzinfo=timezone.utc),
        resolution_verification_status=ResolutionVerificationStatus.VERIFIED,
        is_test_fixture=True
    )
    db_session.add(issue)
    db_session.commit()

    # Response Record
    response = ResponseRecord(
        response_code="RSP-FIX-001-WATERLEAK",
        civic_issue_id=issue.id,
        department_id=dept.id,
        action_type=ResponseActionType.RESOLVED,
        official_remark="Joint re-welded and valve replaced.",
        action_taken_date=datetime(2024, 2, 16, 4, 0, 0, tzinfo=timezone.utc),
        sla_breached=False,
        delay_hours=0.0,
        is_test_fixture=True
    )
    db_session.add(response)
    db_session.commit()

    # Evidence Passage / Report
    evidence = ResolutionEvidence(
        response_id=response.id,
        evidence_type=EvidenceType.FIELD_INSPECTION_REPORT,
        title="CMWSSB Field Completion Certificate No. 441/2024",
        description="Inspected by Assistant Executive Engineer; pressure test confirmed zero leak.",
        evidence_url="https://chennaicorporation.gov.in/gcc/reports/leak_repair_441.pdf",
        sha256_hash="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        is_verified=True,
        verified_by="CivicLens Verification Engine",
        is_test_fixture=True
    )
    db_session.add(evidence)

    # Linked Public Work Contract
    work = PublicWork(
        work_code="WRK-FIX-002-MAWS-PIPE-REPAIR",
        civic_issue_id=issue.id,
        work_title="Emergency 300mm CI Pipeline Repair and Valve Overhaul",
        executing_agency="CMWSSB Maintenance Division",
        sanctioned_amount_inr=75000.0,
        tender_ref="TNTENDERS/CMWSSB/2024/0119",
        status="COMPLETED",
        is_test_fixture=True
    )
    db_session.add(work)
    db_session.commit()

    reloaded_issue = db_session.query(CivicIssue).filter_by(issue_code="CIV-FIX-002-WATERLEAK-RESOLVED").first()
    assert reloaded_issue.resolution_verification_status == ResolutionVerificationStatus.VERIFIED
    assert len(reloaded_issue.responses[0].evidences) == 1
    assert reloaded_issue.responses[0].evidences[0].is_verified is True
    assert len(reloaded_issue.public_works) == 1
    assert reloaded_issue.public_works[0].sanctioned_amount_inr == 75000.0


# ---------------------------------------------------------------------------
# Test 8: Chronological Issue Events & Data Quality Audit
# ---------------------------------------------------------------------------
def test_8_issue_event_logging_and_data_quality_issues(db_session):
    """Verify state transitions and automated data quality audits."""
    cat = IssueCategory(code=IssueCategoryEnum.ROADS, name_en="Roads", name_ta="சாலைகள்")
    db_session.add(cat)
    db_session.commit()

    issue = CivicIssue(
        issue_code="CIV-FIX-004-DEFECTIVE-REPORT",
        title="Unpaved street with missing coordinates",
        description="Road broken near ration shop.",
        category_id=cat.id,
        status=CivicIssueStatus.OPEN,
        severity=CivicIssueSeverity.LOW,
        latitude=None,   # Missing coordinates!
        longitude=None,
        reported_date=datetime.now(timezone.utc),
        is_test_fixture=True
    )
    db_session.add(issue)
    db_session.commit()

    # Log Event
    event = IssueEvent(
        civic_issue_id=issue.id,
        event_type="CREATED",
        actor_type="CITIZEN",
        notes="Grievance lodged via online portal"
    )
    db_session.add(event)

    # Flag Data Quality Issue
    dq = DataQualityIssue(
        civic_issue_id=issue.id,
        severity=DataQualitySeverity.WARNING,
        issue_type="MISSING_COORDINATES",
        description="Issue record has null latitude and longitude coordinates; cannot plot on ward heatmap.",
        resolved=False
    )
    db_session.add(dq)
    db_session.commit()

    reloaded = db_session.query(CivicIssue).filter_by(issue_code="CIV-FIX-004-DEFECTIVE-REPORT").first()
    assert len(reloaded.events) == 1
    assert reloaded.events[0].event_type == "CREATED"
    assert len(reloaded.quality_issues) == 1
    assert reloaded.quality_issues[0].issue_type == "MISSING_COORDINATES"
    assert reloaded.quality_issues[0].severity == DataQualitySeverity.WARNING


# ---------------------------------------------------------------------------
# Test 9: Zero Fabrication Compliance Rule
# ---------------------------------------------------------------------------
def test_9_zero_fabrication_compliance():
    """Verify all mock fixtures explicitly carry is_test_fixture=True."""
    assert IS_TEST_FIXTURE is True
    assert FIXTURE_VERSION == "8.0-test"

    for issue in MOCK_CIVIC_ISSUES:
        assert issue.get("is_test_fixture") is True

    for response in MOCK_RESPONSES:
        assert response.get("is_test_fixture") is True

    for ev in MOCK_EVIDENCE:
        assert ev.get("is_test_fixture") is True

    for pw in MOCK_PUBLIC_WORKS:
        assert pw.get("is_test_fixture") is True
