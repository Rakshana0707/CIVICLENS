"""
CIVICLENS TN — Phase 8.7 Unit Test Suite
========================================
Validates the Civic Issue Analytics and Trend Detection Engine.
Tests all 10 core metrics, missing data handling, diverse reporting periods,
small sample guards, statistical anomaly detection, and population context controls.
"""

from datetime import datetime, timedelta, timezone
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.models.civic_issue import (
    Base,
    CivicIssue,
    CivicIssueStatus,
    CivicIssueSeverity,
    CivicTrackingState,
    GrievanceRecord,
    IssueCategoryEnum,
    IssueMetric,
    ResolutionVerificationStatus,
    ResponseRecord,
)
from backend.services.civic_analytics_service import (
    CivicAnalyticsEngine,
    GENERAL_ANALYTICS_DISCLAIMER,
    AREA_COMPARISON_CAVEAT,
    ANOMALY_INVESTIGATION_NOTICE,
    MIN_ANOMALY_SAMPLE_SIZE,
)


@pytest.fixture
def in_memory_db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    yield session
    session.close()


@pytest.fixture
def analytics_engine():
    return CivicAnalyticsEngine(default_source="TN_CIVIC_ANALYTICS_TEST")


# ---------------------------------------------------------------------------
# Test 1: Category Counts Calculation
# ---------------------------------------------------------------------------
def test_calculate_category_counts(analytics_engine):
    records = [
        {"issue_category": IssueCategoryEnum.ROADS},
        {"issue_category": IssueCategoryEnum.ROADS},
        {"issue_category": IssueCategoryEnum.WATER_SUPPLY},
        {"issue_category": IssueCategoryEnum.DRAINAGE},
        {"issue_category": IssueCategoryEnum.STREETLIGHTS},
    ]

    res = analytics_engine.calculate_category_counts(records, period="2024-Q1", data_source="GCC_1913")

    assert res.metric_code == "ISSUE_COUNT_BY_CATEGORY"
    assert res.sample_size == 5
    assert res.period == "2024-Q1"
    assert res.data_source == "GCC_1913"
    assert res.distribution["counts"]["roads"] == 2
    assert res.distribution["counts"]["water_supply"] == 1
    assert res.distribution["percentages"]["roads"] == 40.0
    assert "Category counts reflect citizen reporting propensity" in res.caveats


# ---------------------------------------------------------------------------
# Test 2: Administrative Area Counts & Population Rates
# ---------------------------------------------------------------------------
def test_calculate_area_counts_with_and_without_population(analytics_engine):
    records = [
        {"administrative_area_id": "ADM-TN-DIST-002-CHENNAI"},
        {"administrative_area_id": "ADM-TN-DIST-002-CHENNAI"},
        {"administrative_area_id": "ADM-TN-DIST-002-CHENNAI"},
        {"administrative_area_id": "ADM-TN-DIST-013-MADURAI"},
        {"administrative_area_id": "ADM-TN-DIST-038-TENKASI"},
    ]

    pop_map = {
        "ADM-TN-DIST-002-CHENNAI": 7_000_000,
        "ADM-TN-DIST-013-MADURAI": 3_000_000,
        # Tenkasi omitted to test missing population
    }

    res = analytics_engine.calculate_area_counts(records, period="2024", population_map=pop_map)

    assert res.metric_code == "ISSUE_COUNT_BY_AREA"
    assert res.sample_size == 5
    assert res.distribution["counts"]["ADM-TN-DIST-002-CHENNAI"] == 3
    assert res.distribution["counts"]["ADM-TN-DIST-038-TENKASI"] == 1

    # Check per-100k rates
    chennai_rate = res.distribution["rate_per_100k_population"]["ADM-TN-DIST-002-CHENNAI"]
    assert chennai_rate == round((3 / 7_000_000) * 100_000, 2)
    assert res.distribution["rate_per_100k_population"]["ADM-TN-DIST-038-TENKASI"] is None

    assert "POPULATION & ACCESS DISPARITY" in res.caveats


# ---------------------------------------------------------------------------
# Test 3: Department Counts & Unassigned Tracking
# ---------------------------------------------------------------------------
def test_calculate_department_counts(analytics_engine):
    records = [
        {"department_id": "DEPT-MAWS-001"},
        {"department_id": "DEPT-MAWS-001"},
        {"department_id": "DEPT-HIGHWAYS-002"},
        {"department_id": None},  # unassigned
        {"department_id": "   "},  # blank / unassigned
    ]

    res = analytics_engine.calculate_department_counts(records, period="2024-03")

    assert res.metric_code == "ISSUE_COUNT_BY_DEPARTMENT"
    assert res.sample_size == 5
    assert res.distribution["counts"]["DEPT-MAWS-001"] == 2
    assert res.distribution["counts"]["DEPT-HIGHWAYS-002"] == 1
    assert res.distribution["unassigned_count"] == 2
    assert res.distribution["unassigned_percentage"] == 40.0
    assert "Shared and contested jurisdictions" in res.caveats


# ---------------------------------------------------------------------------
# Test 4: Temporal Trends & Month-over-Month Growth
# ---------------------------------------------------------------------------
def test_calculate_temporal_trends(analytics_engine):
    records = [
        {"submission_date": datetime(2024, 1, 10, tzinfo=timezone.utc)},
        {"submission_date": datetime(2024, 1, 15, tzinfo=timezone.utc)},
        {"submission_date": datetime(2024, 2, 5, tzinfo=timezone.utc)},
        {"submission_date": datetime(2024, 2, 20, tzinfo=timezone.utc)},
        {"submission_date": datetime(2024, 2, 25, tzinfo=timezone.utc)},
        {"submission_date": datetime(2024, 3, 1, tzinfo=timezone.utc)},
        {"submission_date": None},  # Missing date handling
    ]

    res = analytics_engine.calculate_temporal_trends(records, period="2024-Q1")

    assert res.metric_code == "TEMPORAL_TRENDS_MONTHLY_YEARLY"
    monthly = res.distribution["monthly_counts"]
    assert monthly["2024-01"] == 2
    assert monthly["2024-02"] == 3
    assert monthly["2024-03"] == 1
    assert monthly["UNKNOWN_DATE"] == 1

    # Check month-over-month percentage change (from 2 in Jan to 3 in Feb = +50%)
    mom = res.distribution["month_over_month_change_pct"]
    assert mom["2024-02"] == 50.0
    assert mom["2024-03"] == -66.67


# ---------------------------------------------------------------------------
# Test 5: Turnaround Times (Acknowledgement and Resolution)
# ---------------------------------------------------------------------------
def test_calculate_turnaround_times(analytics_engine):
    base_time = datetime(2024, 1, 1, 10, 0, tzinfo=timezone.utc)
    records = [
        # Record 1: ack in 2 hours, resolved in 3 days
        {
            "submission_date": base_time,
            "acknowledgement_date": base_time + timedelta(hours=2),
            "resolution_date": base_time + timedelta(days=3),
        },
        # Record 2: ack in 4 hours, resolved in 7 days
        {
            "submission_date": base_time,
            "acknowledgement_date": base_time + timedelta(hours=4),
            "resolution_date": base_time + timedelta(days=7),
        },
        # Record 3: ack in 6 hours, unresolved
        {
            "submission_date": base_time,
            "acknowledgement_date": base_time + timedelta(hours=6),
            "resolution_date": None,
        },
        # Record 4: completely missing dates
        {
            "submission_date": None,
            "acknowledgement_date": None,
            "resolution_date": None,
        },
    ]

    res = analytics_engine.calculate_turnaround_times(records, period="2024-01")

    assert res.metric_code == "ACKNOWLEDGEMENT_AND_RESOLUTION_TIME"
    ack_stats = res.distribution["acknowledgement_hours"]
    assert ack_stats["count"] == 3
    assert ack_stats["mean"] == 4.0
    assert ack_stats["median"] == 4.0

    res_stats = res.distribution["reported_resolution_days"]
    assert res_stats["count"] == 2
    assert res_stats["mean"] == 5.0
    assert res_stats["median"] == 7.0 or res_stats["median"] == 5.0
    assert "measures administrative docket closure" in res.caveats


# ---------------------------------------------------------------------------
# Test 6: Known Status Percentage Calculation
# ---------------------------------------------------------------------------
def test_calculate_known_status_percentage(analytics_engine):
    records = [
        {"status": "submitted"},
        {"status": "action_reported"},
        {"status": "marked_resolved"},
        {"status": "unknown"},
        {"status": ""},
        {"status": None},
    ]

    res = analytics_engine.calculate_known_status_percentage(records, period="2024-Q1")

    assert res.metric_code == "KNOWN_STATUS_PERCENTAGE"
    assert res.sample_size == 6
    assert res.distribution["known_count"] == 3
    assert res.distribution["unknown_count"] == 3
    assert res.metric_value == 50.0


# ---------------------------------------------------------------------------
# Test 7: Recurring Issue Clusters & Hotspots
# ---------------------------------------------------------------------------
def test_calculate_recurring_clusters(analytics_engine):
    records = [
        {"administrative_area_id": "WARD-110", "issue_category": "roads", "repeat_count": 3, "is_recurring": True},
        {"administrative_area_id": "WARD-110", "issue_category": "roads", "repeat_count": 2, "is_recurring": True},
        {"administrative_area_id": "WARD-110", "issue_category": "water_supply", "repeat_count": 1, "is_recurring": False},
        {"administrative_area_id": "WARD-112", "issue_category": "streetlights", "repeat_count": 1, "is_recurring": False},
    ]

    res = analytics_engine.calculate_recurring_clusters(records, period="2024")

    assert res.metric_code == "RECURRING_ISSUE_CLUSTERS"
    assert res.distribution["recurring_records_count"] == 2
    assert res.distribution["recurrence_rate_pct"] == 50.0
    assert "WARD-110:roads" in res.distribution["top_hotspots"]
    assert res.distribution["top_hotspots"]["WARD-110:roads"] == 2


# ---------------------------------------------------------------------------
# Test 8: Reopened Issue Counts
# ---------------------------------------------------------------------------
def test_calculate_reopened_issues(analytics_engine):
    records = [
        {"status": "reopened"},
        {"status": "disputed"},
        {"status": "marked_resolved"},
        {"status": "independently_verified_resolved"},
        {"status": "under_review"},
    ]

    res = analytics_engine.calculate_reopened_issues(records, period="2024-Q1")

    assert res.metric_code == "REOPENED_ISSUE_METRICS"
    assert res.sample_size == 5
    assert res.distribution["reopened_count"] == 2
    assert res.distribution["resolved_count"] == 2
    assert res.distribution["reopen_rate_of_total_pct"] == 40.0
    assert res.distribution["reopen_rate_of_closed_pct"] == 50.0
    assert "Portals lacking an online reopen" in res.caveats


# ---------------------------------------------------------------------------
# Test 9: Documented Departmental Response Rate
# ---------------------------------------------------------------------------
def test_calculate_documented_response_rate(analytics_engine):
    records = [
        {"responses": [{"id": 1, "summary": "Inspection done"}]},
        {"responses": []},
        {"responses": None, "acknowledgement_date": datetime.now(timezone.utc)},
        {"responses": [], "acknowledgement_date": None, "resolution_date": None},
    ]

    res = analytics_engine.calculate_documented_response_rate(records, period="2024-Q1")

    assert res.metric_code == "DOCUMENTED_RESPONSE_RATE"
    assert res.sample_size == 4
    # Records 1 and 3 have documented responses/acknowledgements
    assert res.distribution["records_with_documented_response"] == 2
    assert res.metric_value == 50.0


# ---------------------------------------------------------------------------
# Test 10: Resolution Evidence Coverage
# ---------------------------------------------------------------------------
def test_calculate_resolution_evidence_coverage(analytics_engine):
    records = [
        # Closure 1: verified with empirical evidence
        {
            "status": "marked_resolved",
            "resolution_verification_status": ResolutionVerificationStatus.VERIFIED,
            "is_evidence_supported": True,
        },
        # Closure 2: independently verified resolved
        {
            "status": "independently_verified_resolved",
            "resolution_verification_status": ResolutionVerificationStatus.VERIFIED,
            "is_evidence_supported": True,
        },
        # Closure 3: marked resolved without corroborating evidence
        {
            "status": "marked_resolved",
            "resolution_verification_status": ResolutionVerificationStatus.PENDING_VERIFICATION,
            "is_evidence_supported": False,
        },
        # Record 4: still open (not part of denominator)
        {
            "status": "under_review",
            "resolution_verification_status": ResolutionVerificationStatus.PENDING_VERIFICATION,
            "is_evidence_supported": False,
        },
    ]

    res = analytics_engine.calculate_resolution_evidence_coverage(records, period="2024-Q1")

    assert res.metric_code == "RESOLUTION_EVIDENCE_COVERAGE"
    assert res.sample_size == 3  # 3 marked closures
    assert res.distribution["verified_with_evidence"] == 2
    assert res.distribution["unverified_closures"] == 1
    assert res.metric_value == 66.67
    assert res.distribution["evidence_gap_pct"] == 33.33
    assert "An unverified closure does not imply falsehood" in res.caveats


# ---------------------------------------------------------------------------
# Test 11: Small Sample Guard in Anomaly Detection
# ---------------------------------------------------------------------------
def test_anomaly_detection_small_sample_protection(analytics_engine):
    # N = 10, which is below the threshold of 30
    small_records = [
        {"submission_date": datetime(2024, 1, 1, tzinfo=timezone.utc)} for _ in range(10)
    ]

    res = analytics_engine.detect_volume_anomalies(small_records)

    assert res.status == "INSUFFICIENT_DATA"
    assert res.sample_size == 10
    assert "Sample size (N=10) is below the minimum threshold" in res.reason


def test_anomaly_detection_insufficient_periods(analytics_engine):
    # N = 35, but all in the same month (only 1 baseline period, need >= 3)
    records = [
        {"submission_date": datetime(2024, 1, 15, tzinfo=timezone.utc)} for _ in range(35)
    ]

    res = analytics_engine.detect_volume_anomalies(records)

    assert res.status == "INSUFFICIENT_DATA"
    assert res.sample_size == 35
    assert "Baseline periods count (1) is below minimum requirement" in res.reason


# ---------------------------------------------------------------------------
# Test 12: Anomaly Detection with Sufficient Data & Labeling
# ---------------------------------------------------------------------------
def test_anomaly_detection_sufficient_data_and_labeling(analytics_engine):
    # Construct 4 baseline periods with ~10 records, and a spike of 60 records in month 5
    records = []
    # 4 normal months
    for month in range(1, 5):
        for day in range(1, 11):
            records.append({"submission_date": datetime(2024, month, day, tzinfo=timezone.utc)})

    # Month 5 spike
    for day in range(1, 31):
        records.append({"submission_date": datetime(2024, 5, min(day, 28), tzinfo=timezone.utc)})
        records.append({"submission_date": datetime(2024, 5, min(day, 28), tzinfo=timezone.utc)})

    assert len(records) == 40 + 60  # 100 records > 30, across 5 periods >= 3

    res = analytics_engine.detect_volume_anomalies(records, z_threshold=1.5)

    assert res.status == "SUFFICIENT_DATA"
    assert res.baseline_periods_count == 5
    assert len(res.anomalies) > 0

    spike_anomaly = [a for a in res.anomalies if a.period == "2024-05"][0]
    assert spike_anomaly.observed_count == 60
    assert spike_anomaly.z_score > 1.5

    # STRICT LABEL CHECK: Must be exploratory investigation indicator
    assert spike_anomaly.indicator_label == "INVESTIGATION_INDICATOR_UNUSUAL_VOLUME"
    assert "NOT proof of administrative negligence" in spike_anomaly.interpretation_note
    assert "EXPLORATORY INDICATOR" in res.interpretative_notice


# ---------------------------------------------------------------------------
# Test 13: Area Comparison with Mandatory Population and Context Controls
# ---------------------------------------------------------------------------
def test_compare_areas_context_and_caveats(analytics_engine):
    # Area A: Chennai (100 records, 7M population)
    records_a = [{"id": i} for i in range(100)]
    # Area B: Tenkasi (20 records, 1.4M population)
    records_b = [{"id": i} for i in range(20)]

    comp_valid = analytics_engine.compare_areas(
        area_a_code="CHENNAI",
        area_a_name="Greater Chennai Corporation",
        records_a=records_a,
        area_b_code="TENKASI",
        area_b_name="Tenkasi District",
        records_b=records_b,
        area_a_pop=7_000_000,
        area_b_pop=1_400_000,
    )

    assert comp_valid.comparison_valid is True
    assert comp_valid.area_a_rate_per_100k == round((100 / 7_000_000) * 100_000, 2)
    assert comp_valid.area_b_rate_per_100k == round((20 / 1_400_000) * 100_000, 2)
    assert "POPULATION & ACCESS DISPARITY" in comp_valid.interpretative_caveat

    # Test when population is missing
    comp_missing_pop = analytics_engine.compare_areas(
        area_a_code="CHENNAI",
        area_a_name="Greater Chennai Corporation",
        records_a=records_a,
        area_b_code="TENKASI",
        area_b_name="Tenkasi District",
        records_b=records_b,
        area_a_pop=None,
        area_b_pop=None,
    )

    assert comp_missing_pop.comparison_valid is False
    assert "CRITICAL WARNING: Population data is missing" in comp_missing_pop.required_context


# ---------------------------------------------------------------------------
# Test 14: Comprehensive Report & Database Persistence
# ---------------------------------------------------------------------------
def test_comprehensive_report_and_db_persistence(analytics_engine, in_memory_db):
    sample_records = [
        GrievanceRecord(
            grievance_id="TN-TEST-G001",
            source_id="GCC_1913",
            issue_category=IssueCategoryEnum.ROADS,
            description_or_permitted_summary="Pothole on Main Road",
            submission_date=datetime(2024, 1, 10, tzinfo=timezone.utc),
            acknowledgement_date=datetime(2024, 1, 10, 14, 0, tzinfo=timezone.utc),
            resolution_date=datetime(2024, 1, 15, tzinfo=timezone.utc),
            department_id="DEPT-GCC-ENG",
            administrative_area_id="ADM-TN-DIST-002-CHENNAI",
            status="marked_resolved",
            is_test_fixture=True,
        ),
        GrievanceRecord(
            grievance_id="TN-TEST-G002",
            source_id="CM_HELPLINE_1100",
            issue_category=IssueCategoryEnum.WATER_SUPPLY,
            description_or_permitted_summary="Low pressure drinking water",
            submission_date=datetime(2024, 1, 12, tzinfo=timezone.utc),
            department_id="DEPT-CMWSSB",
            administrative_area_id="ADM-TN-DIST-002-CHENNAI",
            status="under_review",
            is_test_fixture=True,
        ),
    ]

    report = analytics_engine.generate_comprehensive_report(
        records=sample_records,
        period="2024-01",
        data_source="TN_CIVIC_PORTAL_FIXTURES",
    )

    assert report.total_records == 2
    assert report.reporting_period == "2024-01"
    assert len(report.metrics) == 10
    assert "ISSUE_COUNT_BY_CATEGORY" in report.metrics
    assert "RESOLUTION_EVIDENCE_COVERAGE" in report.metrics
    assert "COMPLAINTS DO NOT EQUAL PREVALENCE" in report.general_disclaimer

    # Test persistence to database
    db_metrics = analytics_engine.persist_report_to_db(in_memory_db, report, is_test_fixture=True)

    assert len(db_metrics) == 10
    persisted = in_memory_db.query(IssueMetric).filter_by(period="2024-01").all()
    assert len(persisted) == 10

    m1_persisted = in_memory_db.query(IssueMetric).filter_by(metric_code="ISSUE_COUNT_BY_CATEGORY").first()
    assert m1_persisted.data_source == "TN_CIVIC_PORTAL_FIXTURES"
    assert m1_persisted.sample_size == 2
    assert m1_persisted.caveats is not None
