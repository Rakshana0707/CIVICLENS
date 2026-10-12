"""
Phase 8.3 — Unit Tests for Grievance Data Ingestion and Normalization Pipeline.

Tests:
1. DARPG CPGRAMS schema adapter and canonical field mapping.
2. Greater Chennai Corporation (GCC) schema adapter and ward/zone mapping.
3. Mudhalvarin Mugavari (TNeGA CM Helpline) schema adapter with Tamil text.
4. Missing status handling: strictly sets status='UNKNOWN' and never defaults to 'RESOLVED'.
5. Date normalization across diverse formats (DD/MM/YYYY, YYYY-MM-DD, DD-Mon-YYYY) and anomaly detection.
6. Bilingual category normalization across 14 standard civic categories.
7. Department normalization across English and Tamil department names and acronyms.
8. Duplicate detection across primary references and content fingerprints.
9. Database ORM persistence and schema integrity for CanonicalGrievanceRecord.
10. Batch normalization report generation and data quality metrics tracking.
"""

import pytest
from datetime import datetime, timezone, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.database.base_class import Base
from backend.models.civic_issue import GrievanceRecord, IssueCategoryEnum
from backend.ingestion.grievance_normalizer import (
    CanonicalGrievanceRecord,
    GrievanceNormalizer,
    DateNormalizer,
    CategoryNormalizer,
    DepartmentNormalizer,
    AreaNormalizer,
    StatusNormalizer,
    GrievanceDuplicateDetector,
    IngestionReport
)
from tests.fixtures.phase8_fixtures import (
    MOCK_DARPG_RECORDS,
    MOCK_GCC_RECORDS,
    MOCK_CM_HELPLINE_RECORDS
)


@pytest.fixture
def db_session():
    """Isolated in-memory SQLite database session."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    yield session

    session.close()


# ---------------------------------------------------------------------------
# Test 1: DARPG CPGRAMS Adapter & PII Redaction
# ---------------------------------------------------------------------------
def test_1_darpg_cpgrams_adapter():
    normalizer = GrievanceNormalizer()
    raw = MOCK_DARPG_RECORDS[0]

    record, outcome = normalizer.normalize_single_record(
        raw_record=raw,
        source_id="DARPG_CPGRAMS"
    )

    assert outcome == "VALID"
    assert record is not None
    assert record.source_id == "DARPG_CPGRAMS"
    assert record.source_record_reference == "DARPG/TN/2024/0001"
    assert record.grievance_id == "GRV-DARPG_CPGRAMS-DARPG-TN-2024-0001"
    assert record.issue_category == "water_supply"
    assert record.department_id == "DEPT_MAWS"
    assert record.administrative_area_id == "ADM-TN-DIST-013-CHENNAI"
    assert record.status == "RESOLVED"
    assert record.submission_date == datetime(2024, 3, 14, 0, 0, 0, tzinfo=timezone.utc)
    assert record.resolution_date == datetime(2024, 3, 20, 0, 0, 0, tzinfo=timezone.utc)

    # Verify PII scrubbing on description
    assert "9840234567" not in record.description_or_permitted_summary
    assert "Thiru R. Mani" not in record.description_or_permitted_summary
    assert "[PHONE REDACTED]" in record.description_or_permitted_summary
    assert "[CITIZEN]" in record.description_or_permitted_summary


# ---------------------------------------------------------------------------
# Test 2: GCC 1913 Adapter & Ward/Zone Hierarchy
# ---------------------------------------------------------------------------
def test_2_gcc_adapter_ward_zone_mapping():
    normalizer = GrievanceNormalizer()
    raw = MOCK_GCC_RECORDS[0]

    record, outcome = normalizer.normalize_single_record(
        raw_record=raw,
        source_id="GCC_CHENNAI"
    )

    assert outcome == "VALID"
    assert record is not None
    assert record.source_id == "GCC_CHENNAI"
    assert record.source_record_reference == "GCC/2024/1913/0101"
    assert record.issue_category == "roads"
    assert record.department_id == "DEPT_GCC"
    assert record.administrative_area_id == "ADM-TN-GCC-WARD-174"
    assert record.status == "RESOLVED"
    assert record.submission_date == datetime(2024, 3, 10, 0, 0, 0, tzinfo=timezone.utc)
    assert record.resolution_date == datetime(2024, 3, 12, 0, 0, 0, tzinfo=timezone.utc)

    # PII scrubbing
    assert "9444123456" not in record.description_or_permitted_summary
    assert "Tmt Revathi" not in record.description_or_permitted_summary
    assert "[PHONE REDACTED]" in record.description_or_permitted_summary
    assert "[CITIZEN]" in record.description_or_permitted_summary


# ---------------------------------------------------------------------------
# Test 3: Mudhalvarin Mugavari Adapter (Tamil Transliteration)
# ---------------------------------------------------------------------------
def test_3_cm_helpline_adapter_tamil_support():
    normalizer = GrievanceNormalizer()
    raw = MOCK_CM_HELPLINE_RECORDS[0]

    record, outcome = normalizer.normalize_single_record(
        raw_record=raw,
        source_id="TNEGA_CM_HELPLINE"
    )

    assert outcome == "VALID"
    assert record is not None
    assert record.source_id == "TNEGA_CM_HELPLINE"
    assert record.source_record_reference == "MM-2024-88901"
    assert record.issue_category == "roads"
    assert record.department_id == "DEPT_HIGHWAYS"
    assert record.administrative_area_id == "ADM-TN-DIST-014-CHENGALPATTU"
    assert record.status == "RESOLVED"
    assert record.submission_date == datetime(2024, 2, 15, 0, 0, 0, tzinfo=timezone.utc)
    assert record.resolution_date == datetime(2024, 2, 25, 0, 0, 0, tzinfo=timezone.utc)


# ---------------------------------------------------------------------------
# Test 4: Missing Status Rule — Never Default to Resolved
# ---------------------------------------------------------------------------
def test_4_missing_status_never_defaults_to_resolved():
    normalizer = GrievanceNormalizer()
    raw = MOCK_CM_HELPLINE_RECORDS[1]  # current_status is None

    record, outcome = normalizer.normalize_single_record(
        raw_record=raw,
        source_id="TNEGA_CM_HELPLINE"
    )

    assert outcome == "VALID"
    assert record is not None
    # Crucial Project Requirement: Never assume missing status is 'RESOLVED'
    assert record.status == "UNKNOWN"
    assert record.status != "RESOLVED"
    assert record.data_quality_status == "MISSING_STATUS"


# ---------------------------------------------------------------------------
# Test 5: Date Normalization & Quality Checks
# ---------------------------------------------------------------------------
def test_5_date_normalization_variations_and_anomalies():
    # 1. Standard Indian slash format
    dt, warn = DateNormalizer.parse_date("25/04/2023")
    assert warn is None
    assert dt == datetime(2023, 4, 25, 0, 0, 0, tzinfo=timezone.utc)

    # 2. ISO format with time
    dt, warn = DateNormalizer.parse_date("2023-11-05T14:30:00Z")
    assert warn is None
    assert dt == datetime(2023, 11, 5, 14, 30, 0, tzinfo=timezone.utc)

    # 3. Mon format (12-Oct-2023)
    dt, warn = DateNormalizer.parse_date("12-Oct-2023")
    assert warn is None
    assert dt == datetime(2023, 10, 12, 0, 0, 0, tzinfo=timezone.utc)

    # 4. Future Date Check (Flagged as SUSPECT_DATE_IN_FUTURE)
    future_date_str = (datetime.now(timezone.utc) + timedelta(days=10)).strftime("%Y-%m-%d")
    dt, warn = DateNormalizer.parse_date(future_date_str)
    assert warn == "SUSPECT_DATE_IN_FUTURE"

    # 5. Pre-2000 Date Check
    dt, warn = DateNormalizer.parse_date("15/08/1995")
    assert warn == "SUSPECT_DATE_PRE_2000"

    # 6. Unparseable string
    dt, warn = DateNormalizer.parse_date("not-a-valid-date")
    assert dt is None
    assert warn == "SUSPECT_DATE_UNPARSEABLE"


# ---------------------------------------------------------------------------
# Test 6: Bilingual Category Normalization
# ---------------------------------------------------------------------------
def test_6_bilingual_category_normalization():
    # English terms
    cat, _ = CategoryNormalizer.normalize_category("street light dark street")
    assert cat == "streetlights"

    cat, _ = CategoryNormalizer.normalize_category("clogged drainage manhole overflow")
    assert cat == "drainage"

    cat, _ = CategoryNormalizer.normalize_category("transformer burst low voltage")
    assert cat == "electricity"

    # Tamil terms
    cat, _ = CategoryNormalizer.normalize_category("குடிநீர் குழாய் உடைப்பு")
    assert cat == "water_supply"

    cat, _ = CategoryNormalizer.normalize_category("திடக்கழிவு குப்பை அள்ளாமை")
    assert cat == "waste_management"

    cat, _ = CategoryNormalizer.normalize_category("அரசு பள்ளி மேற்கூரை சேதம்")
    assert cat == "education_infrastructure"

    # Unknown term fallback
    cat, warn = CategoryNormalizer.normalize_category("Unprecedented random request")
    assert cat == "other_documented_civic_issues"
    assert warn == "AMBIGUOUS_CATEGORY"


# ---------------------------------------------------------------------------
# Test 7: Department Normalization
# ---------------------------------------------------------------------------
def test_7_department_normalization():
    dept, _ = DepartmentNormalizer.normalize_department("Chennai Metro Water Board")
    assert dept == "DEPT_MAWS"

    dept, _ = DepartmentNormalizer.normalize_department("TNEB Distribution")
    assert dept == "DEPT_TANGEDCO"

    dept, _ = DepartmentNormalizer.normalize_department("State Highways Division")
    assert dept == "DEPT_HIGHWAYS"

    dept, _ = DepartmentNormalizer.normalize_department("வருவாய்த்துறை தாசில்தார்")
    assert dept == "DEPT_REVENUE"

    dept, warn = DepartmentNormalizer.normalize_department("Some Unknown Agency")
    assert dept is None
    assert warn == "AMBIGUOUS_DEPARTMENT"


# ---------------------------------------------------------------------------
# Test 8: Duplicate Detection
# ---------------------------------------------------------------------------
def test_8_duplicate_detection():
    detector = GrievanceDuplicateDetector()

    source = "DARPG_CPGRAMS"
    ref = "REG-991"
    sub_dt = datetime(2024, 1, 15, tzinfo=timezone.utc)
    cat = "roads"
    desc = "Pothole on Main Road"

    c_hash = detector.compute_content_hash(source, sub_dt, cat, desc)

    # First check: not duplicate
    assert detector.is_duplicate(source, ref, c_hash) is False
    detector.mark_seen(source, ref, c_hash)

    # Second check with same reference: duplicate!
    assert detector.is_duplicate(source, ref, c_hash) is True

    # Check with different reference but identical content hash: duplicate!
    assert detector.is_duplicate(source, "DIFFERENT-REF", c_hash) is True

    # Check with completely different content: not duplicate
    c_hash_2 = detector.compute_content_hash(source, sub_dt, "water_supply", "Pipe broken")
    assert detector.is_duplicate(source, "NEW-REF", c_hash_2) is False


# ---------------------------------------------------------------------------
# Test 9: Database ORM Conversion & Persistence
# ---------------------------------------------------------------------------
def test_9_database_orm_persistence(db_session):
    normalizer = GrievanceNormalizer()
    raw = MOCK_GCC_RECORDS[1]

    record, outcome = normalizer.normalize_single_record(
        raw_record=raw,
        source_id="GCC_CHENNAI",
        source_document_id=1
    )
    assert outcome == "VALID"

    # Convert to ORM entity
    orm_entity = record.to_orm(is_test_fixture=True)
    assert isinstance(orm_entity, GrievanceRecord)
    assert orm_entity.grievance_id == record.grievance_id
    assert orm_entity.source_id == "GCC_CHENNAI"
    assert orm_entity.status == "IN_PROGRESS"
    assert orm_entity.is_test_fixture is True

    # Persist in DB
    db_session.add(orm_entity)
    db_session.commit()

    # Query back
    saved = db_session.query(GrievanceRecord).filter_by(grievance_id=record.grievance_id).first()
    assert saved is not None
    assert saved.issue_category == IssueCategoryEnum.WASTE_MANAGEMENT
    assert saved.status == "IN_PROGRESS"
    assert saved.submission_date.date() == record.submission_date.date()


# ---------------------------------------------------------------------------
# Test 10: Batch Ingestion & Report Metrics
# ---------------------------------------------------------------------------
def test_10_batch_ingestion_and_report():
    normalizer = GrievanceNormalizer()

    batch_input = [
        MOCK_DARPG_RECORDS[0],
        MOCK_DARPG_RECORDS[1],
        # Add duplicate of record 0
        MOCK_DARPG_RECORDS[0],
        # Add defective record with missing date
        {"Registration Number": "INVALID-1", "Received Date": None, "Category": "roads"}
    ]

    canonical_records, report = normalizer.normalize_batch(
        raw_records=batch_input,
        source_id="DARPG_CPGRAMS"
    )

    assert isinstance(report, IngestionReport)
    assert report.total_processed == 4
    assert report.valid_records == 2
    assert report.duplicates_detected == 1
    assert report.missing_required_fields == 1
    assert len(canonical_records) == 2
