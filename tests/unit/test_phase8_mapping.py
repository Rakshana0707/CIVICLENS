"""
Unit Test Suite for Geographic & Department Jurisdiction Mapping (Phase 8.5)
=============================================================================
Verifies:
  1. Administrative Area Code Resolution (Districts, GCC Zones, Wards)
  2. Bilingual Tamil & English Text Matching
  3. Missing Location Safeguard (Does not invent ward/district; flags MISSING_LOCATION)
  4. Historical Boundary Changes (Nov 2019 bifurcations: Chengalpattu, Ranipet, etc.)
  5. Ambiguous Place Names (Refuses to guess Chennai for uncontextualized homonyms)
  6. GPS Coordinate Geodesic Resolution
  7. Department Jurisdiction Routing (Municipal vs State Line Departments)
  8. Shared Department Responsibility (State Highway in Corporation Limits)
  9. Unclear / Disputed Department Responsibility (Unresolved status + Candidate depts)
  10. Citizen's Charter SLA Deadline Calculation
  11. Canonical CivicMappingRecord Serialization (All 8 mandatory fields verified)
  12. Unified Database Entity Enrichment Integration
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
    CivicMappingIntegrationService,
    CivicMappingRecord
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


# ---------------------------------------------------------------------------
# Test 1: Administrative Area Code Resolution
# ---------------------------------------------------------------------------
def test_1_administrative_area_code_resolution():
    res_chennai = CivicGeographicMapper.resolve_by_code("ADM-TN-DIST-003-CHENNAI")
    assert res_chennai is not None
    assert res_chennai.area_name_en == "Chennai"
    assert res_chennai.administrative_level == AdministrativeLevel.DISTRICT

    res_zone = CivicGeographicMapper.resolve_by_code("ADM-TN-GCC-ZONE-13-ADYAR")
    assert res_zone is not None
    assert "Adyar" in res_zone.area_name_en
    assert res_zone.administrative_level == AdministrativeLevel.MUNICIPAL_CORPORATION

    res_ward = CivicGeographicMapper.resolve_by_code("ADM-TN-GCC-WARD-174")
    assert res_ward is not None
    assert res_ward.area_code == "ADM-TN-GCC-WARD-174"
    assert res_ward.administrative_level == AdministrativeLevel.WARD
    assert res_ward.is_imprecise is False


# ---------------------------------------------------------------------------
# Test 2: Bilingual Tamil & English Text Matching
# ---------------------------------------------------------------------------
def test_2_bilingual_district_and_locality_text_matching():
    res_ta = CivicGeographicMapper.resolve_by_text(district_text="செங்கல்பட்டு")
    assert res_ta.area_code == "ADM-TN-DIST-002-CHENGALPATTU"
    assert res_ta.area_name_en == "Chengalpattu"

    res_ward_text = CivicGeographicMapper.resolve_by_text(locality_text="Besant Nagar Ward 174, near beach road.")
    assert res_ward_text.area_code == "ADM-TN-GCC-WARD-174"
    assert res_ward_text.administrative_level == AdministrativeLevel.WARD

    res_zone_text = CivicGeographicMapper.resolve_by_text(locality_text="மண்டலம் 13 அடையாறு பகுதி")
    assert "ZONE-13" in res_zone_text.area_code


# ---------------------------------------------------------------------------
# Test 3: Missing Location Safeguard
# ---------------------------------------------------------------------------
def test_3_missing_location_safeguard():
    # Empty or generic text without location
    res_missing = CivicGeographicMapper.resolve_by_text(district_text="", locality_text="")
    assert res_missing.area_code == "ADM-TN-STATE"
    assert res_missing.administrative_level == AdministrativeLevel.STATE
    assert res_missing.is_imprecise is True
    assert res_missing.warning_flag == "MISSING_LOCATION"
    assert res_missing.confidence < 0.50
    # Crucial safeguard: Never invents a ward or district!
    assert "WARD" not in res_missing.area_code
    assert "DIST" not in res_missing.area_code


# ---------------------------------------------------------------------------
# Test 4: Historical Boundary Reorganizations
# ---------------------------------------------------------------------------
def test_4_historical_boundary_reorganizations():
    # Tambaram was in Kancheepuram prior to Nov 2019, now in Chengalpattu
    res_tambaram = CivicGeographicMapper.resolve_by_text(
        district_text="Kancheepuram",
        locality_text="Tambaram Sanatorium bus stand road"
    )
    assert res_tambaram.area_code == "ADM-TN-DIST-002-CHENGALPATTU"
    assert res_tambaram.warning_flag == "HISTORICAL_BOUNDARY_SPLIT"
    assert res_tambaram.historical_context is not None
    assert "Kancheepuram" in res_tambaram.historical_context

    # Arakkonam was in Vellore prior to Nov 2019, now in Ranipet
    res_arakkonam = CivicGeographicMapper.resolve_by_text(locality_text="Arakkonam railway station road")
    assert res_arakkonam.area_code == "ADM-TN-DIST-021-RANIPET"
    assert res_arakkonam.warning_flag == "HISTORICAL_BOUNDARY_SPLIT"


# ---------------------------------------------------------------------------
# Test 5: Ambiguous Place Name Disambiguation
# ---------------------------------------------------------------------------
def test_5_ambiguous_place_name_disambiguation():
    # 'Anna Nagar' without district context: Refuse to assume Chennai!
    res_ambiguous = CivicGeographicMapper.resolve_by_text(locality_text="Water leakage on 2nd avenue, Anna Nagar")
    assert res_ambiguous.area_code == "ADM-TN-STATE"
    assert res_ambiguous.warning_flag == "AMBIGUOUS_PLACE_NAME"
    assert res_ambiguous.is_imprecise is True
    assert len(res_ambiguous.candidate_areas) > 1
    assert "Madurai" in str(res_ambiguous.candidate_areas)

    # 'Anna Nagar' WITH explicit Madurai district: Resolves cleanly to Madurai!
    res_disambiguated = CivicGeographicMapper.resolve_by_text(
        district_text="Madurai",
        locality_text="Anna Nagar, Madurai near bus stand"
    )
    assert res_disambiguated.area_code == "ADM-TN-DIST-013-MADURAI"
    assert res_disambiguated.warning_flag == "COARSE_GEOGRAPHY"  # Mapped to district, not ambiguous


# ---------------------------------------------------------------------------
# Test 6: GPS Coordinate Geodesic Resolution
# ---------------------------------------------------------------------------
def test_6_gps_coordinates_spatial_resolution():
    res_chn = CivicGeographicMapper.resolve_by_coordinates(lat=13.0827, lon=80.2707)
    assert res_chn.area_code == "ADM-TN-DIST-003-CHENNAI"

    res_mdu = CivicGeographicMapper.resolve_by_coordinates(lat=9.9195, lon=78.1193)
    assert res_mdu.area_code == "ADM-TN-DIST-013-MADURAI"


# ---------------------------------------------------------------------------
# Test 7: Department Jurisdiction Routing
# ---------------------------------------------------------------------------
def test_7_department_jurisdiction_routing():
    # Electricity statewide -> TANGEDCO
    res_elec = CivicDepartmentResolver.resolve_jurisdiction(
        category_code=IssueCategoryEnum.ELECTRICITY.value,
        area_code="ADM-TN-DIST-013-MADURAI"
    )
    assert res_elec.department_code == "DEPT_TANGEDCO"
    assert res_elec.sla_hours == 24
    assert res_elec.department_status == "RESOLVED"
    assert "TANGEDCO" in (res_elec.responsible_local_authority or "")

    # Patta delay statewide -> Revenue Department
    res_patta = CivicDepartmentResolver.resolve_jurisdiction(
        category_code=IssueCategoryEnum.GOVERNMENT_SERVICE_DELAYS.value,
        area_code="ADM-TN-DIST-028-TIRUCHIRAPPALLI"
    )
    assert res_patta.department_code == "DEPT_REVENUE"
    assert res_patta.sla_hours == 360  # 15 days


# ---------------------------------------------------------------------------
# Test 8: Shared Department Responsibility
# ---------------------------------------------------------------------------
def test_8_shared_department_responsibility():
    # State Highway road passing within GCC limits
    res_shared = CivicDepartmentResolver.resolve_jurisdiction(
        category_code=IssueCategoryEnum.ROADS.value,
        area_code="ADM-TN-GCC-WARD-174",
        description_text="Potholes on State Highway corridor passing through Besant Nagar."
    )
    assert res_shared.is_shared_responsibility is True
    assert res_shared.department_status == "SHARED"
    assert "DEPT_HIGHWAYS" in res_shared.candidate_departments
    assert "DEPT_GCC" in res_shared.candidate_departments
    assert res_shared.responsible_local_authority is not None


# ---------------------------------------------------------------------------
# Test 9: Unclear / Disputed Department Responsibility
# ---------------------------------------------------------------------------
def test_9_unclear_or_disputed_department_responsibility():
    # Disputed boundary or unclassified issue
    res_unclear = CivicDepartmentResolver.resolve_jurisdiction(
        category_code=IssueCategoryEnum.OTHER_CIVIC_ISSUES.value,
        description_text="Boundary dispute and disputed encroachment near public canal."
    )
    assert res_unclear.department_code is None
    assert res_unclear.department_status == "UNRESOLVED"
    assert res_unclear.is_shared_responsibility is True
    assert len(res_unclear.candidate_departments) >= 2
    assert res_unclear.review_status == "PENDING_HUMAN_REVIEW"


# ---------------------------------------------------------------------------
# Test 10: Citizen's Charter SLA Deadline Computation
# ---------------------------------------------------------------------------
def test_10_citizens_charter_sla_deadline_computation():
    sub_date = datetime(2024, 3, 1, 10, 0, tzinfo=timezone.utc)

    # Streetlight (24-hour turnaround)
    res_light = CivicDepartmentResolver.resolve_jurisdiction(
        category_code=IssueCategoryEnum.STREETLIGHTS.value,
        area_code="ADM-TN-GCC-WARD-174",
        submission_date=sub_date
    )
    assert res_light.sla_hours == 24
    assert res_light.target_resolution_date == sub_date + timedelta(hours=24)

    # Pothole repair (48-hour turnaround)
    res_pothole = CivicDepartmentResolver.resolve_jurisdiction(
        category_code=IssueCategoryEnum.ROADS.value,
        area_code="ADM-TN-GCC-WARD-174",
        submission_date=sub_date
    )
    assert res_pothole.sla_hours == 48
    assert res_pothole.target_resolution_date == sub_date + timedelta(hours=48)


# ---------------------------------------------------------------------------
# Test 11: Canonical CivicMappingRecord Serialization
# ---------------------------------------------------------------------------
def test_11_canonical_mapping_record_serialization(db_session):
    cat_road = db_session.query(IssueCategory).filter_by(code=IssueCategoryEnum.ROADS).first()

    issue = CivicIssue(
        issue_code="ISSUE-TEST-RECORD-01",
        title="Damaged Road in GCC Ward 174",
        description="Large potholes on 4th Main Road.",
        category_id=cat_road.id,
        reported_date=datetime(2024, 3, 1, 10, 0, tzinfo=timezone.utc),
        status=CivicIssueStatus.OPEN,
        is_test_fixture=True
    )
    db_session.add(issue)
    db_session.flush()

    grievance = GrievanceRecord(
        grievance_id="GRV-MAPPING-REC-01",
        source_id="GCC_CHENNAI",
        source_record_reference="GCC/2024/REC/01",
        issue_category=IssueCategoryEnum.ROADS,
        description_or_permitted_summary="Potholes on 4th Main Road, Ward 174",
        administrative_area_id="ADM-TN-GCC-WARD-174",
        submission_date=datetime(2024, 3, 1, 10, 0, tzinfo=timezone.utc),
        is_test_fixture=True
    )

    geo_res, dept_res, mapping_record = CivicMappingIntegrationService.map_and_enrich_issue(
        db_session=db_session,
        civic_issue=issue,
        grievance=grievance
    )
    db_session.commit()

    # All 8 mandatory fields from Phase 8.5 must be populated
    assert isinstance(mapping_record, CivicMappingRecord)
    assert mapping_record.issue_id == issue.id
    assert mapping_record.administrative_area_id == "ADM-TN-GCC-WARD-174"
    assert mapping_record.geographic_level == "WARD"
    assert mapping_record.department_id == "DEPT_GCC"
    assert mapping_record.mapping_method == "EXACT_CODE"
    assert mapping_record.source_reference == "GCC/2024/REC/01"
    assert mapping_record.confidence >= 0.90
    assert mapping_record.review_status == "AUTOMATED_VERIFIED"

    # Serializes to dictionary properly
    rec_dict = mapping_record.to_dict()
    assert rec_dict["issue_id"] == issue.id
    assert rec_dict["administrative_area_id"] == "ADM-TN-GCC-WARD-174"
    assert rec_dict["geographic_level"] == "WARD"
    assert rec_dict["department_id"] == "DEPT_GCC"


# ---------------------------------------------------------------------------
# Test 12: Unified Database Entity Enrichment Integration
# ---------------------------------------------------------------------------
def test_12_unified_database_entity_enrichment_integration(db_session):
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

    geo_res, dept_res, mapping_rec = CivicMappingIntegrationService.map_and_enrich_issue(
        db_session=db_session,
        civic_issue=issue,
        grievance=grievance
    )
    db_session.commit()

    assert issue.department_id is not None
    assert issue.target_resolution_date is not None
    assert issue.target_resolution_date.replace(tzinfo=timezone.utc) == datetime(2024, 3, 6, 8, 0, tzinfo=timezone.utc)  # 24h SLA
    assert dept_res.department_code == "DEPT_GCC"
