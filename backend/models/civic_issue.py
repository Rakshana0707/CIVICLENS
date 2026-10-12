"""
Phase 8 — Public Grievance & Civic Issue Intelligence Database Models.

Defines canonical SQLAlchemy ORM entities for:
1. CivicIssue
2. GrievanceRecord
3. IssueCategory
4. GovernmentDepartment
5. AdministrativeArea
6. ServiceStandard
7. ResponseRecord
8. ResolutionEvidence
9. PublicWork
10. IssueEvent
11. SourceDocument
12. IssueMetric
13. DataQualityIssue

Adheres strictly to core Phase 8 principles:
- Strict citizen privacy & automated PII scrubbing (DPDPA 2023 compliance)
- Support for 14 standardized civic categories in Tamil and English
- Hierarchical administrative boundary mapping
- Department routing and service standard SLA benchmarking
- Multi-source resolution corroboration
- Zero real-data fabrication (clear test fixture markers)
"""

import enum
import re
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from sqlalchemy import (
    Column, Integer, String, Text, DateTime, ForeignKey, Float, Boolean, Enum, JSON, UniqueConstraint
)
from sqlalchemy.orm import relationship
from backend.database.base_class import Base


# ---------------------------------------------------------------------------
# Privacy & PII Scrubbing Utility
# ---------------------------------------------------------------------------
def sanitize_pii(text: Optional[str]) -> str:
    """
    Scrubs Personal Identifiable Information (PII) from civic descriptions
    in compliance with DPDPA 2023.

    Redacts:
    - Indian mobile/landline numbers (+91, 0, or 10-digit formats starting with 6-9)
    - RFC-5322 email addresses
    - Aadhaar / 12-digit tokens
    - Common name prefix patterns (Thiru, Tmt, Selvi, Mr, Mrs, Shri, Smt, Dr) with initials
    - Private door / apartment numbers
    """
    if not text:
        return ""

    sanitized = text

    # Redact email addresses (excluding trailing periods/punctuation)
    email_pattern = r'\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b'
    sanitized = re.sub(email_pattern, '[EMAIL REDACTED]', sanitized)

    # Redact Indian phone numbers
    phone_pattern = r'(?:\+91[-\s]?|0)?[6-9]\d{4}[-\s]?\d{5}\b'
    sanitized = re.sub(phone_pattern, '[PHONE REDACTED]', sanitized)

    # Redact landline with STD prefix (e.g. 044-24567890)
    landline_pattern = r'\b0\d{2,4}[-\s]?\d{6,8}\b'
    sanitized = re.sub(landline_pattern, '[PHONE REDACTED]', sanitized)

    # Redact 12-digit UID/Aadhaar patterns
    uid_pattern = r'\b\d{4}\s\d{4}\s\d{4}\b'
    sanitized = re.sub(uid_pattern, '[ID REDACTED]', sanitized)

    # Redact door numbers and flat addresses first to prevent name overlap
    door_pattern = r'\b(?:Door\s*No\.?|D\.No\.?|Flat\s*No\.?|Plot\s*No\.?)\s*[:#]?\s*\w+[\/-]?\w*\b'
    sanitized = re.sub(door_pattern, '[ADDRESS REDACTED]', sanitized, flags=re.IGNORECASE)

    # Redact name prefixes followed by name words, including initials (e.g. Thiru K. Murugesan, Tmt Lakshmi)
    salutation_pattern = r'\b(Thiru|Tmt|Selvi|Mr\.?|Mrs\.?|Ms\.?|Shri|Smt\.?|Dr\.?)\s+(?:[A-Z]\.?\s*)*[A-Za-z]+(?:\s+[A-Z][a-z]+)*\b'
    sanitized = re.sub(salutation_pattern, '[CITIZEN]', sanitized)

    return sanitized


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------
class IssueCategoryEnum(str, enum.Enum):
    """
    Standardized 14 civic categories supported by CIVICLENS TN.
    """
    ROADS = "roads"
    WATER_SUPPLY = "water_supply"
    DRAINAGE = "drainage"
    SANITATION = "sanitation"
    WASTE_MANAGEMENT = "waste_management"
    STREETLIGHTS = "streetlights"
    PUBLIC_TRANSPORT = "public_transport"
    HEALTHCARE_ACCESS = "healthcare_access"
    EDUCATION_INFRASTRUCTURE = "education_infrastructure"
    ELECTRICITY = "electricity"
    PUBLIC_SAFETY_INFRASTRUCTURE = "public_safety_infrastructure"
    ENVIRONMENTAL_CONCERNS = "environmental_concerns"
    GOVERNMENT_SERVICE_DELAYS = "government_service_delays"
    OTHER_CIVIC_ISSUES = "other_documented_civic_issues"


class CivicIssueStatus(str, enum.Enum):
    OPEN = "OPEN"
    IN_PROGRESS = "IN_PROGRESS"
    RESOLVED = "RESOLVED"
    VERIFIED_RESOLVED = "VERIFIED_RESOLVED"
    ESCALATED = "ESCALATED"
    CLOSED_UNRESOLVED = "CLOSED_UNRESOLVED"
    DISPUTED = "DISPUTED"


class CivicTrackingState(str, enum.Enum):
    """
    Standard 9 lifecycle tracking states for grievance resolution tracking.
    """
    SUBMITTED = "submitted"
    ACKNOWLEDGED = "acknowledged"
    UNDER_REVIEW = "under_review"
    ACTION_REPORTED = "action_reported"
    MARKED_RESOLVED = "marked_resolved"
    INDEPENDENTLY_VERIFIED_RESOLVED = "independently_verified_resolved"
    REOPENED = "reopened"
    DISPUTED = "disputed"
    UNKNOWN = "unknown"


class CivicIssueSeverity(str, enum.Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class AdministrativeLevel(str, enum.Enum):
    STATE = "STATE"
    DISTRICT = "DISTRICT"
    TALUK = "TALUK"
    BLOCK = "BLOCK"
    MUNICIPAL_CORPORATION = "MUNICIPAL_CORPORATION"
    MUNICIPALITY = "MUNICIPALITY"
    TOWN_PANCHAYAT = "TOWN_PANCHAYAT"
    WARD = "WARD"
    ASSEMBLY_CONSTITUENCY = "ASSEMBLY_CONSTITUENCY"
    PARLIAMENTARY_CONSTITUENCY = "PARLIAMENTARY_CONSTITUENCY"


class ResponseActionType(str, enum.Enum):
    ACKNOWLEDGED = "ACKNOWLEDGED"
    INSPECTION_CONDUCTED = "INSPECTION_CONDUCTED"
    WORK_SANCTIONED = "WORK_SANCTIONED"
    CONTRACT_AWARDED = "CONTRACT_AWARDED"
    RESOLVED = "RESOLVED"
    REJECTED = "REJECTED"
    ESCALATED = "ESCALATED"


class ResolutionVerificationStatus(str, enum.Enum):
    PENDING_VERIFICATION = "PENDING_VERIFICATION"
    VERIFIED = "VERIFIED"
    CONTRADICTED = "CONTRADICTED"
    INCONCLUSIVE = "INCONCLUSIVE"


class EvidenceType(str, enum.Enum):
    WORK_ORDER = "WORK_ORDER"
    COMPLETION_CERTIFICATE = "COMPLETION_CERTIFICATE"
    FIELD_INSPECTION_REPORT = "FIELD_INSPECTION_REPORT"
    NEWS_REPORT = "NEWS_REPORT"
    PHOTOGRAPHIC_EVIDENCE = "PHOTOGRAPHIC_EVIDENCE"
    CITIZEN_AUDIT = "CITIZEN_AUDIT"
    RTI_RESPONSE = "RTI_RESPONSE"


class DataQualitySeverity(str, enum.Enum):
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


# ---------------------------------------------------------------------------
# 1. IssueCategory Entity
# ---------------------------------------------------------------------------
class IssueCategory(Base):
    """
    Standardized classification taxonomy for public civic issues.
    """
    __tablename__ = "civic_issue_categories"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(Enum(IssueCategoryEnum), unique=True, nullable=False, index=True)
    name_en = Column(String(100), nullable=False)
    name_ta = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    default_department_code = Column(String(50), nullable=True)
    keywords_en = Column(JSON, nullable=True)
    keywords_ta = Column(JSON, nullable=True)
    priority_weight = Column(Float, default=1.0)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    civic_issues = relationship("CivicIssue", back_populates="category")
    service_standards = relationship("ServiceStandard", back_populates="category")


# ---------------------------------------------------------------------------
# 2. CivicDepartment / GovernmentDepartment Entity
# ---------------------------------------------------------------------------
class CivicDepartment(Base):
    """
    State Secretariat department, directorate, or municipal local body agency.
    """
    __tablename__ = "civic_departments"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(50), unique=True, nullable=False, index=True)
    name_en = Column(String(200), nullable=False)
    name_ta = Column(String(300), nullable=False)
    portal_id = Column(String(50), nullable=True, index=True)
    jurisdiction_level = Column(String(50), default="STATE")
    contact_email_public = Column(String(100), nullable=True)
    helpline_number = Column(String(50), nullable=True)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    civic_issues = relationship("CivicIssue", back_populates="department")
    service_standards = relationship("ServiceStandard", back_populates="department")
    responses = relationship("ResponseRecord", back_populates="department")
    metrics = relationship("IssueMetric", back_populates="department")


# Canonical alias for Phase 8 data entity specification
GovernmentDepartment = CivicDepartment


# ---------------------------------------------------------------------------
# 3. AdministrativeArea Entity
# ---------------------------------------------------------------------------
class AdministrativeArea(Base):
    """
    Spatial hierarchy representing administrative jurisdictions in Tamil Nadu.
    """
    __tablename__ = "administrative_areas"

    id = Column(Integer, primary_key=True, index=True)
    area_code = Column(String(100), unique=True, nullable=False, index=True)
    name_en = Column(String(150), nullable=False, index=True)
    name_ta = Column(String(200), nullable=False)
    administrative_level = Column(Enum(AdministrativeLevel), nullable=False, index=True)
    parent_id = Column(Integer, ForeignKey("administrative_areas.id"), nullable=True)
    lgd_code = Column(String(50), nullable=True, index=True)
    census_code = Column(String(50), nullable=True)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    population = Column(Integer, nullable=True)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    parent = relationship("AdministrativeArea", remote_side=[id], backref="children")
    civic_issues = relationship("CivicIssue", back_populates="administrative_area")
    metrics = relationship("IssueMetric", back_populates="administrative_area")


# ---------------------------------------------------------------------------
# 4. ServiceStandard Entity
# ---------------------------------------------------------------------------
class ServiceStandard(Base):
    """
    Citizen's Charter statutory service standard and turnaround limit (SLA).
    """
    __tablename__ = "service_standards"

    id = Column(Integer, primary_key=True, index=True)
    standard_code = Column(String(100), unique=True, nullable=False, index=True)
    department_id = Column(Integer, ForeignKey("civic_departments.id"), nullable=False)
    category_id = Column(Integer, ForeignKey("civic_issue_categories.id"), nullable=True)
    service_name_en = Column(String(200), nullable=False)
    service_name_ta = Column(String(300), nullable=False)
    stipulated_time_hours = Column(Integer, nullable=False)  # e.g. 48 hours
    designated_officer = Column(String(150), nullable=False)
    appellate_authority = Column(String(150), nullable=True)
    penalty_clause = Column(Text, nullable=True)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    department = relationship("CivicDepartment", back_populates="service_standards")
    category = relationship("IssueCategory", back_populates="service_standards")


# ---------------------------------------------------------------------------
# 5. SourceDocument Entity
# ---------------------------------------------------------------------------
class SourceDocument(Base):
    """
    Primary statutory document, gazette notification, or council resolution.
    """
    __tablename__ = "civic_source_documents"

    id = Column(Integer, primary_key=True, index=True)
    document_code = Column(String(100), unique=True, nullable=False, index=True)
    title = Column(String(300), nullable=False)
    source_tier = Column(Integer, default=2)  # 1 to 5
    source_url = Column(String(500), nullable=True)
    publisher = Column(String(200), nullable=False)
    published_date = Column(DateTime, nullable=True)
    sha256_hash = Column(String(64), nullable=True)
    file_format = Column(String(20), default="PDF")

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    grievances = relationship("GrievanceRecord", back_populates="source_document")
    responses = relationship("ResponseRecord", back_populates="source_document")


# ---------------------------------------------------------------------------
# 6. CivicIssue Entity (Root)
# ---------------------------------------------------------------------------
class CivicIssue(Base):
    """
    Canonical real-world civic problem (e.g. chronic waterlogging, damaged transformer).
    """
    __tablename__ = "civic_issues"

    id = Column(Integer, primary_key=True, index=True)
    issue_code = Column(String(100), unique=True, nullable=False, index=True)
    title = Column(String(300), nullable=False)
    title_ta = Column(String(400), nullable=True)
    description = Column(Text, nullable=False)
    category_id = Column(Integer, ForeignKey("civic_issue_categories.id"), nullable=False)
    department_id = Column(Integer, ForeignKey("civic_departments.id"), nullable=True)
    administrative_area_id = Column(Integer, ForeignKey("administrative_areas.id"), nullable=True)
    status = Column(Enum(CivicIssueStatus), default=CivicIssueStatus.OPEN, index=True)
    severity = Column(Enum(CivicIssueSeverity), default=CivicIssueSeverity.MEDIUM, index=True)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    reported_date = Column(DateTime, nullable=False, index=True)
    target_resolution_date = Column(DateTime, nullable=True)
    actual_resolution_date = Column(DateTime, nullable=True)
    repeat_count = Column(Integer, default=1)
    resolution_verification_status = Column(
        Enum(ResolutionVerificationStatus), default=ResolutionVerificationStatus.PENDING_VERIFICATION
    )
    is_test_fixture = Column(Boolean, default=False, nullable=False)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    category = relationship("IssueCategory", back_populates="civic_issues")
    department = relationship("CivicDepartment", back_populates="civic_issues")
    administrative_area = relationship("AdministrativeArea", back_populates="civic_issues")
    grievance_records = relationship("GrievanceRecord", back_populates="civic_issue")
    responses = relationship("ResponseRecord", back_populates="civic_issue")
    events = relationship("IssueEvent", back_populates="civic_issue")
    public_works = relationship("PublicWork", back_populates="civic_issue")
    metrics = relationship("IssueMetric", back_populates="civic_issue")
    quality_issues = relationship("DataQualityIssue", back_populates="civic_issue")


# ---------------------------------------------------------------------------
# 7. GrievanceRecord Entity
# ---------------------------------------------------------------------------
class GrievanceRecord(Base):
    """
    Individual public complaint petition, strictly anonymized with zero PII.
    Conforms to the Phase 8.3 canonical grievance record schema.
    """
    __tablename__ = "grievance_records"

    id = Column(Integer, primary_key=True, index=True)
    # Canonical Phase 8.3 schema fields
    grievance_id = Column(String(100), unique=True, nullable=False, index=True)
    source_id = Column(String(100), nullable=False, index=True, default="CM_HELPLINE_1100")
    issue_category = Column(Enum(IssueCategoryEnum), nullable=True, index=True)
    description_or_permitted_summary = Column(Text, nullable=False)
    submission_date = Column(DateTime, nullable=False, index=True)
    department_id = Column(String(50), nullable=True, index=True)
    administrative_area_id = Column(String(100), nullable=True, index=True)
    status = Column(String(50), default="PENDING", index=True)
    acknowledgement_date = Column(DateTime, nullable=True)
    resolution_date = Column(DateTime, nullable=True)
    source_document_id = Column(Integer, ForeignKey("civic_source_documents.id"), nullable=True)
    source_record_reference = Column(String(150), nullable=True, index=True)
    ingestion_timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    data_quality_status = Column(String(50), default="VALID", index=True)

    # Classification & Review Metadata (Phase 8.4)
    original_category = Column(String(200), nullable=True)
    classification_method = Column(String(50), default="RULE_BASED", nullable=True)
    classification_confidence = Column(Float, default=1.0, nullable=True)
    classification_model_version = Column(String(50), default="civic_classifier_v1.0", nullable=True)
    review_status = Column(String(50), default="AUTOMATED_VERIFIED", index=True)

    # Legacy & relational compatibility columns
    record_token = Column(String(100), nullable=True, index=True)
    complaint_summary = Column(Text, nullable=True)
    complaint_summary_ta = Column(Text, nullable=True)
    lodged_date = Column(DateTime, nullable=True)
    source_portal = Column(String(100), nullable=True)
    civic_issue_id = Column(Integer, ForeignKey("civic_issues.id"), nullable=True)
    is_anonymized = Column(Boolean, default=True, nullable=False)
    raw_metadata = Column(JSON, nullable=True)
    is_test_fixture = Column(Boolean, default=False, nullable=False)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    def __init__(self, **kwargs):
        # Synchronize legacy and canonical field aliases
        if "record_token" in kwargs and "grievance_id" not in kwargs:
            kwargs["grievance_id"] = kwargs["record_token"]
        elif "grievance_id" in kwargs and "record_token" not in kwargs:
            kwargs["record_token"] = kwargs["grievance_id"]

        if "complaint_summary" in kwargs and "description_or_permitted_summary" not in kwargs:
            kwargs["description_or_permitted_summary"] = kwargs["complaint_summary"]
        elif "description_or_permitted_summary" in kwargs and "complaint_summary" not in kwargs:
            kwargs["complaint_summary"] = kwargs["description_or_permitted_summary"]

        if "lodged_date" in kwargs and "submission_date" not in kwargs:
            kwargs["submission_date"] = kwargs["lodged_date"]
        elif "submission_date" in kwargs and "lodged_date" not in kwargs:
            kwargs["lodged_date"] = kwargs["submission_date"]

        if "source_portal" in kwargs and "source_id" not in kwargs:
            kwargs["source_id"] = kwargs["source_portal"]
        elif "source_id" in kwargs and "source_portal" not in kwargs:
            kwargs["source_portal"] = kwargs["source_id"]

        super().__init__(**kwargs)

    # Relationships
    civic_issue = relationship("CivicIssue", back_populates="grievance_records")
    source_document = relationship("SourceDocument", back_populates="grievances")


# ---------------------------------------------------------------------------
# 8. ResponseRecord Entity
# ---------------------------------------------------------------------------
class ResponseRecord(Base):
    """
    Official departmental action taken or status update.
    """
    __tablename__ = "response_records"

    id = Column(Integer, primary_key=True, index=True)
    response_code = Column(String(100), unique=True, nullable=False, index=True)
    civic_issue_id = Column(Integer, ForeignKey("civic_issues.id"), nullable=False)
    department_id = Column(Integer, ForeignKey("civic_departments.id"), nullable=True)
    source_document_id = Column(Integer, ForeignKey("civic_source_documents.id"), nullable=True)
    action_type = Column(Enum(ResponseActionType), default=ResponseActionType.ACKNOWLEDGED)
    official_remark = Column(Text, nullable=False)
    action_taken_date = Column(DateTime, nullable=False)
    sla_breached = Column(Boolean, default=False)
    delay_hours = Column(Float, default=0.0)
    is_test_fixture = Column(Boolean, default=False, nullable=False)

    # Phase 8.6 Resolution Tracker Fields
    reported_status = Column(String(50), default="acknowledged", index=True)
    verification_status = Column(
        Enum(ResolutionVerificationStatus), default=ResolutionVerificationStatus.PENDING_VERIFICATION, index=True
    )
    response_summary = Column(Text, nullable=True)
    supporting_evidence = Column(JSON, nullable=True)
    review_notes = Column(Text, nullable=True)
    public_work_id = Column(Integer, ForeignKey("civic_public_works.id"), nullable=True)
    is_evidence_supported = Column(Boolean, default=False)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    def __init__(self, **kwargs):
        if "response_summary" in kwargs and "official_remark" not in kwargs:
            kwargs["official_remark"] = kwargs["response_summary"]
        elif "official_remark" in kwargs and "response_summary" not in kwargs:
            kwargs["response_summary"] = kwargs["official_remark"]

        if "response_date" in kwargs and "action_taken_date" not in kwargs:
            kwargs["action_taken_date"] = kwargs["response_date"]
        elif "action_taken_date" in kwargs and "response_date" not in kwargs:
            kwargs["response_date"] = kwargs["action_taken_date"]

        if "issue_id" in kwargs and "civic_issue_id" not in kwargs:
            kwargs["civic_issue_id"] = kwargs["issue_id"]

        super().__init__(**kwargs)

    @property
    def issue_id(self):
        return self.civic_issue_id

    @issue_id.setter
    def issue_id(self, val):
        self.civic_issue_id = val

    @property
    def response_date(self):
        return self.action_taken_date

    @response_date.setter
    def response_date(self, val):
        self.action_taken_date = val

    # Relationships
    civic_issue = relationship("CivicIssue", back_populates="responses")
    department = relationship("CivicDepartment", back_populates="responses")
    source_document = relationship("SourceDocument", back_populates="responses")
    evidences = relationship("ResolutionEvidence", back_populates="response")


# ---------------------------------------------------------------------------
# 9. ResolutionEvidence Entity
# ---------------------------------------------------------------------------
class ResolutionEvidence(Base):
    """
    Empirical artifact validating or refuting an official closure claim.
    """
    __tablename__ = "resolution_evidences"

    id = Column(Integer, primary_key=True, index=True)
    response_id = Column(Integer, ForeignKey("response_records.id"), nullable=False)
    evidence_type = Column(Enum(EvidenceType), default=EvidenceType.WORK_ORDER)
    title = Column(String(300), nullable=False)
    description = Column(Text, nullable=False)
    evidence_url = Column(String(500), nullable=True)
    sha256_hash = Column(String(64), nullable=True)
    is_verified = Column(Boolean, default=False)
    verified_by = Column(String(150), nullable=True)
    verification_date = Column(DateTime, nullable=True)
    is_test_fixture = Column(Boolean, default=False, nullable=False)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    response = relationship("ResponseRecord", back_populates="evidences")


# ---------------------------------------------------------------------------
# 10. PublicWork Entity
# ---------------------------------------------------------------------------
class PublicWork(Base):
    """
    Civil work or maintenance contract sanctioned to remediate a civic issue.
    """
    __tablename__ = "civic_public_works"

    id = Column(Integer, primary_key=True, index=True)
    work_code = Column(String(100), unique=True, nullable=False, index=True)
    civic_issue_id = Column(Integer, ForeignKey("civic_issues.id"), nullable=True)
    work_title = Column(String(300), nullable=False)
    executing_agency = Column(String(200), nullable=False)
    sanctioned_amount_inr = Column(Float, nullable=True)
    tender_ref = Column(String(100), nullable=True)
    status = Column(String(50), default="SANCTIONED")
    commencement_date = Column(DateTime, nullable=True)
    completion_date = Column(DateTime, nullable=True)
    is_test_fixture = Column(Boolean, default=False, nullable=False)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    civic_issue = relationship("CivicIssue", back_populates="public_works")


# ---------------------------------------------------------------------------
# 11. IssueEvent Entity
# ---------------------------------------------------------------------------
class IssueEvent(Base):
    """
    Chronological state transition and audit trail log.
    """
    __tablename__ = "civic_issue_events"

    id = Column(Integer, primary_key=True, index=True)
    civic_issue_id = Column(Integer, ForeignKey("civic_issues.id"), nullable=False)
    event_timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    event_type = Column(String(100), nullable=False)  # CREATED, ASSIGNED, STATUS_CHANGE, REOPENED
    actor_type = Column(String(50), default="SYSTEM")
    notes = Column(Text, nullable=True)

    # Relationships
    civic_issue = relationship("CivicIssue", back_populates="events")


# ---------------------------------------------------------------------------
# 12. IssueMetric Entity
# ---------------------------------------------------------------------------
class IssueMetric(Base):
    """
    Aggregated statistical index computed per area, department, or issue.
    """
    __tablename__ = "civic_issue_metrics"

    id = Column(Integer, primary_key=True, index=True)
    metric_code = Column(String(100), index=True, nullable=False)
    civic_issue_id = Column(Integer, ForeignKey("civic_issues.id"), nullable=True)
    administrative_area_id = Column(Integer, ForeignKey("administrative_areas.id"), nullable=True)
    department_id = Column(Integer, ForeignKey("civic_departments.id"), nullable=True)
    period = Column(String(50), nullable=False)  # e.g. 2024-Q1, 2024-03
    metric_name = Column(String(150), nullable=False)
    metric_value = Column(Float, nullable=False)
    unit = Column(String(50), default="COUNT")

    # Phase 8.7 Analytics Attributes
    data_source = Column(String(150), nullable=True, default="VALIDATED_RECORDS")
    sample_size = Column(Integer, default=0)
    caveats = Column(Text, nullable=True)
    extra_metadata = Column(JSON, nullable=True)
    is_test_fixture = Column(Boolean, default=False, nullable=False)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    civic_issue = relationship("CivicIssue", back_populates="metrics")
    administrative_area = relationship("AdministrativeArea", back_populates="metrics")
    department = relationship("CivicDepartment", back_populates="metrics")


# ---------------------------------------------------------------------------
# 13. DataQualityIssue Entity
# ---------------------------------------------------------------------------
class DataQualityIssue(Base):
    """
    Automated audit finding flagging defects, missing coordinates, or anomalous closures.
    """
    __tablename__ = "civic_data_quality_issues"

    id = Column(Integer, primary_key=True, index=True)
    civic_issue_id = Column(Integer, ForeignKey("civic_issues.id"), nullable=True)
    severity = Column(Enum(DataQualitySeverity), default=DataQualitySeverity.WARNING)
    issue_type = Column(String(100), nullable=False)  # MISSING_COORDINATES, UNKNOWN_DEPARTMENT
    description = Column(Text, nullable=False)
    detected_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    resolved = Column(Boolean, default=False)

    # Relationships
    civic_issue = relationship("CivicIssue", back_populates="quality_issues")
