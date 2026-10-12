"""
Unit Test Suite for Civic Issue Classification & Intelligence (Phase 8.4)
==========================================================================
Verifies:
  1. Authoritative Rule-Based Portal Category Classification
  2. Pure Tamil Text Classification & Stemming
  3. Pure English Text Classification
  4. Mixed-Language / Tanglish Code-Switched Classification
  5. Low Confidence Routing to Human Review (PENDING_HUMAN_REVIEW)
  6. Exact Duplicate Detection (No Issue Inflation)
  7. Multiple Complaints About the Same Issue (Clustering + Source Links Preserved)
  8. Recurring Issues at the Same Location (Temporal Gap / Post-Resolution)
  9. Separate Issues in the Same Area (Never Merged Across Categories)
  10. Unrelated Similar Reports (Never Merged Solely on Similar Words)
  11. Verification Status Integrity (Repeated complaints != verified validity)
"""

import pytest
from datetime import datetime, timezone
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.models.civic_issue import (
    Base,
    CivicIssue,
    GrievanceRecord,
    IssueCategory,
    IssueCategoryEnum,
    CivicIssueStatus,
    ResolutionVerificationStatus,
    AdministrativeArea,
    AdministrativeLevel,
    CivicDepartment,
    IssueEvent
)
from backend.nlp.civic_classifier import CivicIssueClassifier
from backend.services.civic_issue_intelligence import (
    CivicIssueIntelligenceService,
    IssueRelationshipType
)
from tests.fixtures.phase8_fixtures import (
    MOCK_CLASSIFICATION_RECORDS,
    MOCK_RELATIONSHIP_SCENARIOS,
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
# Test 1: Rule-Based Portal Category Classification
# ---------------------------------------------------------------------------
def test_1_rule_based_portal_category_classification():
    # GCC rule
    gcc_res = CivicIssueClassifier.classify(raw_category="Potholes on Road")
    assert gcc_res.classification_method == "RULE_BASED"
    assert gcc_res.normalized_category == IssueCategoryEnum.ROADS.value
    assert gcc_res.confidence >= 0.95
    assert gcc_res.review_status == "AUTOMATED_VERIFIED"

    # CM Helpline Tamil rule
    cm_res = CivicIssueClassifier.classify(raw_category="சாலை சீரமைப்பு")
    assert cm_res.classification_method == "RULE_BASED"
    assert cm_res.normalized_category == IssueCategoryEnum.ROADS.value
    assert cm_res.confidence >= 0.95
    assert cm_res.review_status == "AUTOMATED_VERIFIED"

    # Patta delay rule
    patta_res = CivicIssueClassifier.classify(raw_category="பட்டா மாறுதல் தாமதம்")
    assert patta_res.classification_method == "RULE_BASED"
    assert patta_res.normalized_category == IssueCategoryEnum.GOVERNMENT_SERVICE_DELAYS.value
    assert patta_res.confidence >= 0.95


# ---------------------------------------------------------------------------
# Test 2: Tamil Text Classification & Language Detection
# ---------------------------------------------------------------------------
def test_2_tamil_text_classification():
    record_water = MOCK_CLASSIFICATION_RECORDS[0]
    res_water = CivicIssueClassifier.classify(
        raw_category=record_water["raw_category"],
        description=record_water["description"]
    )
    assert res_water.normalized_category == IssueCategoryEnum.WATER_SUPPLY.value
    assert res_water.detected_language == "ta"
    assert res_water.confidence >= 0.75
    assert res_water.review_status == "AUTOMATED_VERIFIED"

    record_elec = MOCK_CLASSIFICATION_RECORDS[1]
    res_elec = CivicIssueClassifier.classify(
        raw_category=record_elec["raw_category"],
        description=record_elec["description"]
    )
    assert res_elec.normalized_category == IssueCategoryEnum.ELECTRICITY.value
    assert res_elec.detected_language == "ta"
    assert res_elec.confidence >= 0.75


# ---------------------------------------------------------------------------
# Test 3: English Text Classification
# ---------------------------------------------------------------------------
def test_3_english_text_classification():
    record_light = MOCK_CLASSIFICATION_RECORDS[2]
    res_light = CivicIssueClassifier.classify(
        raw_category=record_light["raw_category"],
        description=record_light["description"]
    )
    assert res_light.normalized_category == IssueCategoryEnum.STREETLIGHTS.value
    assert res_light.detected_language == "en"
    assert res_light.confidence >= 0.70

    record_waste = MOCK_CLASSIFICATION_RECORDS[3]
    res_waste = CivicIssueClassifier.classify(
        raw_category=record_waste["raw_category"],
        description=record_waste["description"]
    )
    assert res_waste.normalized_category == IssueCategoryEnum.WASTE_MANAGEMENT.value
    assert res_waste.detected_language == "en"
    assert res_waste.confidence >= 0.70


# ---------------------------------------------------------------------------
# Test 4: Mixed-Language / Tanglish Classification
# ---------------------------------------------------------------------------
def test_4_mixed_language_tanglish_classification():
    # Mixed road complaint
    rec_road = MOCK_CLASSIFICATION_RECORDS[4]
    res_road = CivicIssueClassifier.classify(
        raw_category=rec_road["raw_category"],
        description=rec_road["description"]
    )
    assert res_road.normalized_category == IssueCategoryEnum.ROADS.value
    assert res_road.detected_language == "mixed"

    # Mixed electricity complaint
    rec_elec = MOCK_CLASSIFICATION_RECORDS[5]
    res_elec = CivicIssueClassifier.classify(
        raw_category=rec_elec["raw_category"],
        description=rec_elec["description"]
    )
    assert res_elec.normalized_category == IssueCategoryEnum.ELECTRICITY.value
    assert res_elec.detected_language == "mixed"

    # Mixed patta delay
    rec_patta = MOCK_CLASSIFICATION_RECORDS[6]
    res_patta = CivicIssueClassifier.classify(
        raw_category=rec_patta["raw_category"],
        description=rec_patta["description"]
    )
    assert res_patta.normalized_category == IssueCategoryEnum.GOVERNMENT_SERVICE_DELAYS.value
    assert res_patta.detected_language == "mixed"


# ---------------------------------------------------------------------------
# Test 5: Uncertain Classification Triggers Human Review
# ---------------------------------------------------------------------------
def test_5_uncertain_classification_triggers_human_review():
    rec_uncertain = MOCK_CLASSIFICATION_RECORDS[7]
    res = CivicIssueClassifier.classify(
        raw_category=rec_uncertain["raw_category"],
        description=rec_uncertain["description"]
    )
    assert res.review_status == "PENDING_HUMAN_REVIEW"
    assert res.confidence < 0.65
    assert res.normalized_category == IssueCategoryEnum.OTHER_CIVIC_ISSUES.value


# ---------------------------------------------------------------------------
# Test 6: Exact Duplicate Records Detection
# ---------------------------------------------------------------------------
def test_6_exact_duplicate_records_detection(db_session):
    pair = MOCK_RELATIONSHIP_SCENARIOS["duplicate_pair"]

    # Ingest first grievance
    g1 = GrievanceRecord(
        grievance_id=pair[0]["grievance_id"],
        source_id=pair[0]["source_id"],
        source_record_reference=pair[0]["source_record_reference"],
        issue_category=pair[0]["issue_category"],
        description_or_permitted_summary=pair[0]["description_or_permitted_summary"],
        administrative_area_id=pair[0]["administrative_area_id"],
        submission_date=datetime(2024, 3, 1, 10, 0, tzinfo=timezone.utc),
        is_test_fixture=True
    )
    db_session.add(g1)
    db_session.commit()

    issue1, match1 = CivicIssueIntelligenceService.process_and_cluster_grievance(
        db_session=db_session,
        grievance=g1,
        is_test_fixture=True
    )
    db_session.commit()
    assert match1.relationship_type == IssueRelationshipType.NEW_ISSUE
    assert issue1 is not None

    # Ingest identical duplicate grievance
    g2 = GrievanceRecord(
        grievance_id=pair[1]["grievance_id"],
        source_id=pair[1]["source_id"],
        source_record_reference=pair[1]["source_record_reference"],  # Identical reference
        issue_category=pair[1]["issue_category"],
        description_or_permitted_summary=pair[1]["description_or_permitted_summary"],
        administrative_area_id=pair[1]["administrative_area_id"],
        submission_date=datetime(2024, 3, 1, 10, 0, tzinfo=timezone.utc),
        is_test_fixture=True
    )

    issue2, match2 = CivicIssueIntelligenceService.process_and_cluster_grievance(
        db_session=db_session,
        grievance=g2,
        is_test_fixture=True
    )
    db_session.commit()

    # Must be detected as exact duplicate
    assert match2.relationship_type == IssueRelationshipType.DUPLICATE
    assert match2.target_issue_id == issue1.id
    # Complaint count must NOT be inflated by duplicates
    assert issue1.repeat_count == 1


# ---------------------------------------------------------------------------
# Test 7: Multiple Complaints About the Same Active Issue (Clustering + Veracity)
# ---------------------------------------------------------------------------
def test_7_multiple_complaints_same_active_issue_clustering(db_session):
    pair = MOCK_RELATIONSHIP_SCENARIOS["multiple_complaints_same_issue"]

    # First citizen grievance
    g1 = GrievanceRecord(
        grievance_id=pair[0]["grievance_id"],
        source_id=pair[0]["source_id"],
        source_record_reference=pair[0]["source_record_reference"],
        issue_category=pair[0]["issue_category"],
        description_or_permitted_summary=pair[0]["description_or_permitted_summary"],
        administrative_area_id=pair[0]["administrative_area_id"],
        submission_date=datetime(2024, 3, 10, 9, 0, tzinfo=timezone.utc),
        is_test_fixture=True
    )
    db_session.add(g1)
    db_session.commit()

    issue1, match1 = CivicIssueIntelligenceService.process_and_cluster_grievance(
        db_session=db_session,
        grievance=g1,
        is_test_fixture=True
    )
    db_session.commit()
    assert match1.relationship_type == IssueRelationshipType.NEW_ISSUE
    assert issue1.repeat_count == 1

    # Second citizen grievance (different petitioner docket, same location 4 days later)
    g2 = GrievanceRecord(
        grievance_id=pair[1]["grievance_id"],
        source_id=pair[1]["source_id"],
        source_record_reference=pair[1]["source_record_reference"],
        issue_category=pair[1]["issue_category"],
        description_or_permitted_summary=pair[1]["description_or_permitted_summary"],
        administrative_area_id=pair[1]["administrative_area_id"],
        submission_date=datetime(2024, 3, 14, 11, 0, tzinfo=timezone.utc),
        is_test_fixture=True
    )
    db_session.add(g2)
    db_session.commit()

    issue2, match2 = CivicIssueIntelligenceService.process_and_cluster_grievance(
        db_session=db_session,
        grievance=g2,
        is_test_fixture=True
    )
    db_session.commit()

    # Must be clustered under the same CivicIssue
    assert match2.relationship_type == IssueRelationshipType.MULTIPLE_COMPLAINTS_SAME_ISSUE
    assert issue2.id == issue1.id
    assert issue1.repeat_count == 2

    # Preserves links to EVERY underlying source record
    underlying_records = db_session.query(GrievanceRecord).filter_by(civic_issue_id=issue1.id).all()
    assert len(underlying_records) == 2
    assert {r.grievance_id for r in underlying_records} == {pair[0]["grievance_id"], pair[1]["grievance_id"]}

    # CRITICAL PROJECT DIRECTIVE: "Do not interpret repeated complaints as proof that every complaint is valid"
    assert issue1.resolution_verification_status == ResolutionVerificationStatus.PENDING_VERIFICATION

    # Check that IssueEvent was logged
    event = db_session.query(IssueEvent).filter_by(
        civic_issue_id=issue1.id,
        event_type="LINKED_MULTIPLE_COMPLAINT"
    ).first()
    assert event is not None


# ---------------------------------------------------------------------------
# Test 8: Recurring Issues at Same Location (Post-Resolution or Gap)
# ---------------------------------------------------------------------------
def test_8_recurring_issue_detection_at_same_location(db_session):
    pair = MOCK_RELATIONSHIP_SCENARIOS["recurring_issue_pair"]

    # Historical grievance resolved in January
    g_hist = GrievanceRecord(
        grievance_id=pair[0]["grievance_id"],
        source_id=pair[0]["source_id"],
        source_record_reference=pair[0]["source_record_reference"],
        issue_category=pair[0]["issue_category"],
        description_or_permitted_summary=pair[0]["description_or_permitted_summary"],
        administrative_area_id=pair[0]["administrative_area_id"],
        submission_date=datetime(2024, 1, 5, 9, 0, tzinfo=timezone.utc),
        status="RESOLVED",
        is_test_fixture=True
    )
    db_session.add(g_hist)
    db_session.commit()

    issue_hist, match_hist = CivicIssueIntelligenceService.process_and_cluster_grievance(
        db_session=db_session,
        grievance=g_hist,
        is_test_fixture=True
    )
    issue_hist.status = CivicIssueStatus.RESOLVED
    db_session.commit()

    # New complaint 9 months later during monsoon
    g_new = GrievanceRecord(
        grievance_id=pair[1]["grievance_id"],
        source_id=pair[1]["source_id"],
        source_record_reference=pair[1]["source_record_reference"],
        issue_category=pair[1]["issue_category"],
        description_or_permitted_summary=pair[1]["description_or_permitted_summary"],
        administrative_area_id=pair[1]["administrative_area_id"],
        submission_date=datetime(2024, 10, 15, 10, 0, tzinfo=timezone.utc),
        is_test_fixture=True
    )
    db_session.add(g_new)
    db_session.commit()

    issue_new, match_new = CivicIssueIntelligenceService.process_and_cluster_grievance(
        db_session=db_session,
        grievance=g_new,
        is_test_fixture=True
    )
    db_session.commit()

    # Must detect recurrence
    assert match_new.relationship_type == IssueRelationshipType.RECURRING_ISSUE
    assert issue_new.repeat_count >= 2

    # IssueEvent audit trail logged
    rec_event = db_session.query(IssueEvent).filter_by(
        civic_issue_id=issue_new.id,
        event_type="RECURRENCE_DETECTED"
    ).first()
    assert rec_event is not None


# ---------------------------------------------------------------------------
# Test 9: Separate Issues in the Same Area Are Never Merged
# ---------------------------------------------------------------------------
def test_9_separate_issues_in_same_area_never_merged(db_session):
    pair = MOCK_RELATIONSHIP_SCENARIOS["separate_issues_same_area"]

    # Issue 1: Road pothole in Ward 174
    g1 = GrievanceRecord(
        grievance_id=pair[0]["grievance_id"],
        source_id=pair[0]["source_id"],
        source_record_reference=pair[0]["source_record_reference"],
        issue_category=pair[0]["issue_category"],
        description_or_permitted_summary=pair[0]["description_or_permitted_summary"],
        administrative_area_id=pair[0]["administrative_area_id"],
        submission_date=datetime(2024, 3, 10, 10, 0, tzinfo=timezone.utc),
        is_test_fixture=True
    )
    db_session.add(g1)
    db_session.commit()

    issue1, match1 = CivicIssueIntelligenceService.process_and_cluster_grievance(
        db_session=db_session,
        grievance=g1,
        is_test_fixture=True
    )
    db_session.commit()

    # Issue 2: Broken streetlight in same Ward 174
    g2 = GrievanceRecord(
        grievance_id=pair[1]["grievance_id"],
        source_id=pair[1]["source_id"],
        source_record_reference=pair[1]["source_record_reference"],
        issue_category=pair[1]["issue_category"],  # Streetlights
        description_or_permitted_summary=pair[1]["description_or_permitted_summary"],
        administrative_area_id=pair[1]["administrative_area_id"],
        submission_date=datetime(2024, 3, 11, 10, 0, tzinfo=timezone.utc),
        is_test_fixture=True
    )
    db_session.add(g2)
    db_session.commit()

    issue2, match2 = CivicIssueIntelligenceService.process_and_cluster_grievance(
        db_session=db_session,
        grievance=g2,
        is_test_fixture=True
    )
    db_session.commit()

    # Must be separate issues
    assert match2.relationship_type == IssueRelationshipType.SEPARATE_ISSUES_SAME_AREA
    assert issue1.id != issue2.id
    assert issue1.category_id != issue2.category_id


# ---------------------------------------------------------------------------
# Test 10: Unrelated Similar Reports Across Areas Are Never Merged
# ---------------------------------------------------------------------------
def test_10_unrelated_similar_reports_across_areas_never_merged(db_session):
    pair = MOCK_RELATIONSHIP_SCENARIOS["unrelated_similar_reports"]

    # Grievance in Chennai Ward 174
    g_chennai = GrievanceRecord(
        grievance_id=pair[0]["grievance_id"],
        source_id=pair[0]["source_id"],
        source_record_reference=pair[0]["source_record_reference"],
        issue_category=pair[0]["issue_category"],
        description_or_permitted_summary=pair[0]["description_or_permitted_summary"],
        administrative_area_id=pair[0]["administrative_area_id"],
        submission_date=datetime(2024, 3, 10, 10, 0, tzinfo=timezone.utc),
        is_test_fixture=True
    )
    db_session.add(g_chennai)
    db_session.commit()

    issue_chennai, _ = CivicIssueIntelligenceService.process_and_cluster_grievance(
        db_session=db_session,
        grievance=g_chennai,
        is_test_fixture=True
    )
    db_session.commit()

    # Grievance in Madurai with IDENTICAL text description
    g_madurai = GrievanceRecord(
        grievance_id=pair[1]["grievance_id"],
        source_id=pair[1]["source_id"],
        source_record_reference=pair[1]["source_record_reference"],
        issue_category=pair[1]["issue_category"],
        description_or_permitted_summary=pair[1]["description_or_permitted_summary"],  # Identical text!
        administrative_area_id=pair[1]["administrative_area_id"],  # Madurai
        submission_date=datetime(2024, 3, 10, 10, 0, tzinfo=timezone.utc),
        is_test_fixture=True
    )
    db_session.add(g_madurai)
    db_session.commit()

    issue_madurai, match_madurai = CivicIssueIntelligenceService.process_and_cluster_grievance(
        db_session=db_session,
        grievance=g_madurai,
        is_test_fixture=True
    )
    db_session.commit()

    # CRITICAL DIRECTIVE: "Do not merge records solely because they contain similar words."
    assert match_madurai.relationship_type == IssueRelationshipType.UNRELATED_SIMILAR_REPORTS
    assert issue_chennai.id != issue_madurai.id
    assert issue_chennai.administrative_area_id != issue_madurai.administrative_area_id
