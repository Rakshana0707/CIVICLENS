"""
Unit Test Suite for Geographic & Department Jurisdiction Mapping (Phase 8.5)
=============================================================================
Verifies:
  1. Administrative Area Code Resolution (Districts, GCC Zones, Wards)
  2. Bilingual Tamil & English Text Matching
  3. GPS Coordinate Geodesic Resolution
  4. Department Jurisdiction Routing (Municipal vs State Line Departments)
  5. Citizen's Charter SLA Deadline Calculation
  6. Coarse Geography Data Quality Audit Logging
  7. Unified Database Entity Enrichment Integration
"""

import pytest
from datetime import datetime, timezone, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.models.civic_issue import (
    Base,
    CivicIssue,
    GrievanceRecord,
    IssueCategory,
    IssueCategoryEnum,
    CivicIssueStatus,
    CivicIssueSeverity,
    ResolutionVerificationStatus,
    AdministrativeArea,
    AdministrativeLevel,
    CivicDepartment,
    ServiceStandard,
    DataQualityIssue,
    DataQualitySeverity
)
from backend.services.civic_mapping_service import (
    CivicGeographicMapper,
    CivicDepartmentResolver,
    CivicMappingIntegrationService
)
from tests.fixtures.phase8_fixtures import (
    MOCK_CATEGORIES,
    MOCK_DEPARTMENTS,
    MOCK_AREAS,
    MOCK_SERVICE_STANDARDS
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


# ---------------------------------------------------------------------------
# Test 1: Administrative Area Code Resolution
# ---------------------------------------------------------------------------
def test_1_administrative_area_code_resolution():
    # District resolution
    res_chennai = CivicGeographicMapper.resolve_by_code("ADM-TN-DIST-003-CHENNAI")
    assert res_chennai is not None
    assert res_chennai.area_name_en == "Chennai"
    assert res_chennai.area_name_ta == "சென்னை"
    assert res_chennai.administrative_level == AdministrativeLevel.DISTRICT

    # GCC Zone resolution
    res_zone = CivicGeographicMapper.resolve_by_code("ADM-TN-GCC-ZONE-13-ADYAR")
    assert res_zone is not None
    assert "Adyar" in res_zone.area_name_en
    assert res_zone.administrative_level == AdministrativeLevel.MUNICIPAL_CORPORATION

    # GCC Ward resolution
    res_ward = CivicGeographicMapper.resolve_by_code("ADM-TN-GCC-WARD-174")
    assert res_ward is not None
    assert res_ward.area_code == "ADM-TN-GCC-WARD-174"
    assert res_ward.administrative_level == AdministrativeLevel.WARD
    assert res_ward.is_imprecise is False


# ---------------------------------------------------------------------------
# Test 2: Bilingual Tamil & English Text Matching
# ---------------------------------------------------------------------------
def test_2_bilingual_district_and_locality_text_matching():
    # Tamil script district
    res_ta = CivicGeographicMapper.resolve_by_text(district_text="செங்கல்பட்டு")
    assert res_ta.area_code == "ADM-TN-DIST-002-CHENGALPATTU"
    assert res_ta.area_name_en == "Chengalpattu"

    # Text containing ward specification
    res_ward_text = CivicGeographicMapper.resolve_by_text(locality_text="Besant Nagar Ward 174, near beach road.")
    assert res_ward_text.area_code == "ADM-TN-GCC-WARD-174"
    assert res_ward_text.administrative_level == AdministrativeLevel.WARD

    # Text containing zone specification
    res_zone_text = CivicGeographicMapper.resolve_by_text(locality_text="மண்டலம் 13 அடையாறு பகுதி")
    assert "ZONE-13" in res_zone_text.area_code


# ---------------------------------------------------------------------------
# Test 3: GPS Coordinate Geodesic Resolution
# ---------------------------------------------------------------------------
def test_3_gps_coordinates_spatial_resolution():
    # Chennai Central coordinates (13.0827, 80.2707)
    res_chn = CivicGeographicMapper.resolve_by_coordinates(lat=13.0827, lon=80.2707)
    assert res_chn.area_code == "ADM-TN-DIST-003-CHENNAI"

    # Madurai Meenakshi Amman Temple coordinates (9.9195, 78.1193)
    res_mdu = CivicGeographicMapper.resolve_by_coordinates(lat=9.9195, lon=78.1193)
    assert res_mdu.area_code == "ADM-TN-DIST-013-MADURAI"


# ---------------------------------------------------------------------------
# Test 4: Department Jurisdiction Routing
# ---------------------------------------------------------------------------
def test_4_department_jurisdiction_routing():
    # Electricity statewide -> TANGEDCO
    res_elec = CivicDepartmentResolver.resolve_jurisdiction(
        category_code=IssueCategoryEnum.ELECTRICITY.value,
        area_code="ADM-TN-DIST-013-MADURAI"
    )
    assert res_elec.department_code == "DEPT_TANGEDCO"
    assert res_elec.sla_hours == 24

    # Patta delay statewide -> Revenue Department
    res_patta = CivicDepartmentResolver.resolve_jurisdiction(
        category_code=IssueCategoryEnum.GOVERNMENT_SERVICE_DELAYS.value,
        area_code="ADM-TN-DIST-028-TIRUCHIRAPPALLI"
    )
    assert res_patta.department_code == "DEPT_REVENUE"
    assert res_patta.sla_hours == 360  # 15 days

    # Road in Chennai -> GCC Works
    res_gcc_road = CivicDepartmentResolver.resolve_jurisdiction(
        category_code=IssueCategoryEnum.ROADS.value,
        area_code="ADM-TN-GCC-WARD-174"
    )
    assert res_gcc_road.department_code == "DEPT_GCC"

    # Road outside Chennai -> Highways Department
    res_hw_road = CivicDepartmentResolver.resolve_jurisdiction(
        category_code=IssueCategoryEnum.ROADS.value,
        area_code="ADM-TN-DIST-022-SALEM"
    )
    assert res_hw_road.department_code == "DEPT_HIGHWAYS"


# ---------------------------------------------------------------------------
# Test 5: Citizen's Charter SLA Deadline Computation
# ---------------------------------------------------------------------------
def test_5_citizens_charter_sla_deadline_computation():
    sub_date = datetime(2024, 3, 1, 10, 0, tzinfo=timezone.utc)

    # Streetlight (24-hour turnaround)
    res_light = CivicDepartmentResolver.resolve_jurisdiction(
        category_code=IssueCategoryEnum.STREETLIGHTS.value,
        area_code="ADM-TN-GCC-WARD-174",
        submission_date=sub_date
    )
    assert res_light.sla_hours == 24
    expected_light_deadline = sub_date + timedelta(hours=24)
    assert res_light.target_resolution_date == expected_light_deadline

    # Pothole repair (48-hour turnaround)
    res_pothole = CivicDepartmentResolver.resolve_jurisdiction(
        category_code=IssueCategoryEnum.ROADS.value,
        area_code="ADM-TN-GCC-WARD-174",
        submission_date=sub_date
    )
    assert res_pothole.sla_hours == 48
    expected_pothole_deadline = sub_date + timedelta(hours=48)
    assert res_pothole.target_resolution_date == expected_pothole_deadline


# ---------------------------------------------------------------------------
# Test 6: Coarse Geography Data Quality Audit Logging
# ---------------------------------------------------------------------------
def test_6_coarse_geography_data_quality_audit(db_session):
    # Create issue with only District-level specification (coarse)
    cat_road = db_session.query(IssueCategory).filter_by(code=IssueCategoryEnum.ROADS).first()

    issue = CivicIssue(
        issue_code="ISSUE-TEST-COARSE-01",
        title="Damaged Road in Chennai",
        description="Potholes somewhere on broad road.",
        category_id=cat_road.id,
        reported_date=datetime(2024, 3, 1, 10, 0, tzinfo=timezone.utc),
        status=CivicIssueStatus.OPEN,
        is_test_fixture=True
    )
    db_session.add(issue)
    db_session.flush()

    grievance = GrievanceRecord(
        grievance_id="GRV-COARSE-01",
        source_id="GCC_CHENNAI",
        issue_category=IssueCategoryEnum.ROADS,
        description_or_permitted_summary="Potholes in Chennai",
        administrative_area_id="ADM-TN-DIST-003-CHENNAI",  # District-level, not Ward-level
        submission_date=datetime(2024, 3, 1, 10, 0, tzinfo=timezone.utc),
        is_test_fixture=True
    )

    geo_res, dept_res = CivicMappingIntegrationService.map_and_enrich_issue(
        db_session=db_session,
        civic_issue=issue,
        grievance=grievance
    )
    db_session.commit()

    # Must flag DataQualityIssue for coarse geography
    assert geo_res.is_imprecise is True
    dq_issues = db_session.query(DataQualityIssue).filter_by(civic_issue_id=issue.id).all()
    assert len(dq_issues) >= 1
    assert any(dq.issue_type == "COARSE_GEOGRAPHY" for dq in dq_issues)


# ---------------------------------------------------------------------------
# Test 7: Unified Database Entity Enrichment Integration
# ---------------------------------------------------------------------------
def test_7_unified_database_entity_enrichment_integration(db_session):
    cat_waste = db_session.query(IssueCategory).filter_by(code=IssueCategoryEnum.WASTE_MANAGEMENT).first()

    issue = CivicIssue(
        issue_code="ISSUE-TEST-ENRICH-01",
        title="Overflowing Garbage Bin in Besant Nagar",
        description="Conservancy bin overflowing outside park, Ward 174 Besant Nagar.",
        category_id=cat_waste.id,
        reported_date=datetime(2024, 3, 5, 8, 0, tzinfo=timezone.utc),
        status=CivicIssueStatus.OPEN,
        is_test_fixture=True
    )
    db_session.add(issue)
    db_session.flush()

    grievance = GrievanceRecord(
        grievance_id="GRV-ENRICH-01",
        source_id="GCC_CHENNAI",
        issue_category=IssueCategoryEnum.WASTE_MANAGEMENT,
        description_or_permitted_summary="Conservancy bin overflowing outside park, Ward 174 Besant Nagar.",
        administrative_area_id="ADM-TN-GCC-WARD-174",
        submission_date=datetime(2024, 3, 5, 8, 0, tzinfo=timezone.utc),
        is_test_fixture=True
    )

    geo_res, dept_res = CivicMappingIntegrationService.map_and_enrich_issue(
        db_session=db_session,
        civic_issue=issue,
        grievance=grievance
    )
    db_session.commit()

    assert issue.department_id is not None
    assert issue.target_resolution_date is not None
    assert issue.target_resolution_date.replace(tzinfo=timezone.utc) == datetime(2024, 3, 6, 8, 0, tzinfo=timezone.utc)  # 24h SLA
    assert dept_res.department_code == "DEPT_GCC"
