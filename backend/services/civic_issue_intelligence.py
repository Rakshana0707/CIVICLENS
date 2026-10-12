"""
Civic Issue Intelligence and Duplicate Detection Service (CIVICLENS TN - Phase 8.4)
===================================================================================
Intelligence service that analyzes relationships between incoming grievance records
and real-world CivicIssue clusters.

Distinguishes 5 distinct civic relationships:
  1. DUPLICATE: Exact same docket/fingerprint re-ingested or submitted simultaneously.
  2. MULTIPLE_COMPLAINTS_SAME_ISSUE: Separate citizens reporting the exact same physical
     problem in the same location during an active concurrent period.
  3. RECURRING_ISSUE: Same location and category, but temporally separated after prior
     resolution or past dormancy (e.g. pothole reappearing after monsoon repair).
  4. SEPARATE_ISSUES_SAME_AREA: Different issues in the same ward/area (e.g. water leak
     vs streetlight fault, or distinct streets).
  5. UNRELATED_SIMILAR_REPORTS: Similar textual complaints in different areas/districts.
     STRICT RULE: Records are NEVER merged solely because they share similar words.

Core Constraints:
  - Preserves links from clustered issues to every underlying source record.
  - Repeated complaints do NOT automatically prove that every complaint is valid
    (keeps resolution_verification_status as PENDING_VERIFICATION).
  - Emits immutable IssueEvent audit trail entries for every link, merge, or recurrence.
"""

import math
import re
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from enum import Enum
from typing import Dict, List, Optional, Tuple, Any
from sqlalchemy.orm import Session

from backend.models.civic_issue import (
    CivicIssue,
    GrievanceRecord,
    IssueEvent,
    IssueCategory,
    IssueCategoryEnum,
    CivicIssueStatus,
    CivicIssueSeverity,
    ResolutionVerificationStatus,
    AdministrativeArea,
    CivicDepartment
)
from backend.nlp.civic_classifier import CivicIssueClassifier, CivicClassificationResult


# Spatial and temporal clustering thresholds
SPATIAL_CLUSTER_RADIUS_METERS = 350.0  # Geodesic distance threshold for coordinate clustering
CONCURRENT_ACTIVE_WINDOW_DAYS = 45     # Active concurrent grievance window
RECURRENCE_TIME_GAP_DAYS = 60          # Temporal gap indicating recurrence of resolved/dormant issue


class IssueRelationshipType(str, Enum):
    DUPLICATE = "DUPLICATE"
    MULTIPLE_COMPLAINTS_SAME_ISSUE = "MULTIPLE_COMPLAINTS_SAME_ISSUE"
    RECURRING_ISSUE = "RECURRING_ISSUE"
    SEPARATE_ISSUES_SAME_AREA = "SEPARATE_ISSUES_SAME_AREA"
    UNRELATED_SIMILAR_REPORTS = "UNRELATED_SIMILAR_REPORTS"
    NEW_ISSUE = "NEW_ISSUE"


@dataclass
class IssueClusterMatch:
    """Detailed outcome of relationship determination."""
    relationship_type: IssueRelationshipType
    target_issue_id: Optional[int] = None
    target_issue_code: Optional[str] = None
    confidence: float = 1.0
    reason: str = ""
    distance_meters: Optional[float] = None
    time_delta_days: Optional[float] = None


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Computes great-circle distance between two GPS coordinates in meters.
    """
    R = 6371000.0  # Earth's radius in meters
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = math.sin(delta_phi / 2.0)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0)**2
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return R * c


def extract_street_landmark_tokens(text: str) -> List[str]:
    """
    Extracts micro-location tokens (street, road, nagar, avenue, ward numbers).
    """
    if not text:
        return []
    normalized = text.lower()
    # Match patterns like: 4th main road, 2nd cross, besant nagar, anna salai, ward 174
    patterns = [
        r'\b\d+(?:st|nd|rd|th)?\s+(?:main\s+road|cross\s+street|avenue|street|road)\b',
        r'\b[a-z\s]+(?:nagar|salai|colony|puram|pakkam|street|road)\b',
        r'\bward\s*[-#:]?\s*\d+\b'
    ]
    tokens = []
    for pat in patterns:
        matches = re.findall(pat, normalized)
        for m in matches:
            tokens.append(m.strip())
    return tokens


class CivicIssueIntelligenceService:
    """
    Comprehensive civic issue intelligence, classification, and deduplication service.
    """

    @classmethod
    def classify_and_tag_grievance(cls, grievance: GrievanceRecord) -> CivicClassificationResult:
        """
        Classifies incoming grievance and tags the record with metadata fields.
        """
        raw_cat = grievance.original_category or (grievance.issue_category.value if grievance.issue_category else None)
        desc = grievance.description_or_permitted_summary or grievance.complaint_summary or ""

        result = CivicIssueClassifier.classify(
            raw_category=raw_cat,
            description=desc,
            source_id=grievance.source_id
        )

        # Set classification tracking metadata
        grievance.original_category = result.original_category
        # Map to IssueCategoryEnum
        try:
            grievance.issue_category = IssueCategoryEnum(result.normalized_category)
        except ValueError:
            grievance.issue_category = IssueCategoryEnum.OTHER_CIVIC_ISSUES

        grievance.classification_method = result.classification_method
        grievance.classification_confidence = result.confidence
        grievance.classification_model_version = result.model_version
        grievance.review_status = result.review_status

        # Synchronize raw metadata
        if grievance.raw_metadata is None:
            grievance.raw_metadata = {}
        grievance.raw_metadata["classification"] = result.to_dict()

        return result

    @classmethod
    def analyze_relationship(
        cls,
        candidate_grievance: GrievanceRecord,
        existing_issues: List[CivicIssue],
        candidate_lat: Optional[float] = None,
        candidate_lon: Optional[float] = None
    ) -> IssueClusterMatch:
        """
        Analyzes relationship between candidate grievance and existing issues.
        Enforces strict zero-false-merge rules.
        """
        cand_cat = candidate_grievance.issue_category.value if candidate_grievance.issue_category else None
        cand_area = candidate_grievance.administrative_area_id
        cand_sub_date = candidate_grievance.submission_date
        if cand_sub_date and cand_sub_date.tzinfo is None:
            cand_sub_date = cand_sub_date.replace(tzinfo=timezone.utc)

        cand_text = candidate_grievance.description_or_permitted_summary or ""
        cand_landmarks = extract_street_landmark_tokens(cand_text)

        # Step 1: Check for Exact Duplicate against existing grievance records
        for issue in existing_issues:
            for g in issue.grievance_records:
                # Same record reference or token from same source
                if g.source_record_reference and candidate_grievance.source_record_reference:
                    if (g.source_record_reference == candidate_grievance.source_record_reference and
                            g.source_id == candidate_grievance.source_id):
                        return IssueClusterMatch(
                            relationship_type=IssueRelationshipType.DUPLICATE,
                            target_issue_id=issue.id,
                            target_issue_code=issue.issue_code,
                            confidence=1.0,
                            reason=f"Exact source record reference match: {g.source_record_reference}"
                        )
                # Grievance ID match
                if g.grievance_id and candidate_grievance.grievance_id:
                    if g.grievance_id == candidate_grievance.grievance_id:
                        return IssueClusterMatch(
                            relationship_type=IssueRelationshipType.DUPLICATE,
                            target_issue_id=issue.id,
                            target_issue_code=issue.issue_code,
                            confidence=1.0,
                            reason=f"Exact grievance ID match: {g.grievance_id}"
                        )

        # Step 2: Evaluate candidates for cluster matching
        best_match: Optional[IssueClusterMatch] = None

        for issue in existing_issues:
            issue_cat = issue.category.code if issue.category else None
            issue_area_code = issue.administrative_area.area_code if issue.administrative_area else None
            issue_reported_dt = issue.reported_date
            if issue_reported_dt and issue_reported_dt.tzinfo is None:
                issue_reported_dt = issue_reported_dt.replace(tzinfo=timezone.utc)

            # Compute time delta in days
            time_delta_days = 0.0
            if cand_sub_date and issue_reported_dt:
                time_delta_days = abs((cand_sub_date - issue_reported_dt).total_seconds()) / 86400.0

            # -----------------------------------------------------------------
            # GUARD 1: Different Geographic Area -> UNRELATED_SIMILAR_REPORTS
            # Never merge complaints in different areas even if descriptions are identical!
            # -----------------------------------------------------------------
            if cand_area and issue_area_code and cand_area != issue_area_code:
                # If high textual similarity but different area, strictly flag unrelated
                continue

            # -----------------------------------------------------------------
            # GUARD 2: Same Area, Different Category -> SEPARATE_ISSUES_SAME_AREA
            # Water supply vs Streetlights in the same ward must NEVER be merged!
            # -----------------------------------------------------------------
            if cand_cat and issue_cat and cand_cat != issue_cat:
                continue

            # -----------------------------------------------------------------
            # Spatial Evaluation (Coordinates or Micro-Landmark)
            # -----------------------------------------------------------------
            is_spatial_match = False
            distance_meters = None

            if (candidate_lat is not None and candidate_lon is not None and
                    issue.latitude is not None and issue.longitude is not None):
                distance_meters = haversine_distance(
                    candidate_lat, candidate_lon, issue.latitude, issue.longitude
                )
                if distance_meters <= SPATIAL_CLUSTER_RADIUS_METERS:
                    is_spatial_match = True
                else:
                    # Same ward and category, but coordinates > 350m apart -> Separate issues!
                    continue
            else:
                # Inspect extracted street / landmark tokens
                issue_text = f"{issue.title} {issue.description}"
                issue_landmarks = extract_street_landmark_tokens(issue_text)

                if cand_landmarks and issue_landmarks:
                    # Common landmark found
                    common = set(cand_landmarks).intersection(set(issue_landmarks))
                    if common:
                        is_spatial_match = True
                    else:
                        # Conflicting distinct streets in same ward (e.g. 1st Main Rd vs 10th Cross)
                        continue
                elif cand_area and issue_area_code and cand_area == issue_area_code:
                    # Same granular area (e.g. Ward) without conflicting street specifics
                    is_spatial_match = True

            if not is_spatial_match:
                continue

            # -----------------------------------------------------------------
            # Temporal Gap & Resolution Status -> MULTIPLE_COMPLAINTS vs RECURRENCE
            # -----------------------------------------------------------------
            # If issue was formally marked RESOLVED or elapsed gap > 60 days
            is_resolved = (issue.status == CivicIssueStatus.RESOLVED)
            if is_resolved or time_delta_days > RECURRENCE_TIME_GAP_DAYS:
                return IssueClusterMatch(
                    relationship_type=IssueRelationshipType.RECURRING_ISSUE,
                    target_issue_id=issue.id,
                    target_issue_code=issue.issue_code,
                    confidence=0.90,
                    reason=(
                        f"Recurring issue detected at same location/category. "
                        f"Prior status: {issue.status.value}, time elapsed: {time_delta_days:.1f} days."
                    ),
                    distance_meters=distance_meters,
                    time_delta_days=time_delta_days
                )

            # Concurrent complaint during ongoing active window
            if time_delta_days <= CONCURRENT_ACTIVE_WINDOW_DAYS and not is_resolved:
                return IssueClusterMatch(
                    relationship_type=IssueRelationshipType.MULTIPLE_COMPLAINTS_SAME_ISSUE,
                    target_issue_id=issue.id,
                    target_issue_code=issue.issue_code,
                    confidence=0.95,
                    reason=(
                        f"Multiple complaints about identical active physical issue. "
                        f"Time delta: {time_delta_days:.1f} days."
                    ),
                    distance_meters=distance_meters,
                    time_delta_days=time_delta_days
                )

        # Check if candidate is in same area as any existing issue (different problem)
        if cand_area:
            same_area_issues = [i for i in existing_issues if i.administrative_area and i.administrative_area.area_code == cand_area]
            if same_area_issues:
                return IssueClusterMatch(
                    relationship_type=IssueRelationshipType.SEPARATE_ISSUES_SAME_AREA,
                    target_issue_id=same_area_issues[0].id,
                    target_issue_code=same_area_issues[0].issue_code,
                    confidence=1.0,
                    reason=f"Separate issue occurring within same administrative area ({cand_area})."
                )

        # Check if candidate has similar wording to any issue in a DIFFERENT area
        if existing_issues:
            return IssueClusterMatch(
                relationship_type=IssueRelationshipType.UNRELATED_SIMILAR_REPORTS,
                confidence=1.0,
                reason="Unrelated report: distinct geographic location despite possible category/word overlap."
            )

        # No existing issues
        return IssueClusterMatch(
            relationship_type=IssueRelationshipType.NEW_ISSUE,
            confidence=1.0,
            reason="Initial report for new civic problem."
        )

    @classmethod
    def process_and_cluster_grievance(
        cls,
        db_session: Session,
        grievance: GrievanceRecord,
        candidate_lat: Optional[float] = None,
        candidate_lon: Optional[float] = None,
        is_test_fixture: bool = False
    ) -> Tuple[Optional[CivicIssue], IssueClusterMatch]:
        """
        Integrates a GrievanceRecord into the CivicIssue intelligence layer:
          1. Classifies and tags the record.
          2. Determines relationship against existing issues in DB.
          3. Links, recurs, or provisions new CivicIssue.
          4. Emits immutable IssueEvent audit log entries.
        """
        # Step 1: Classify grievance
        cls.classify_and_tag_grievance(grievance)

        # Step 2: Fetch existing issues for matching
        existing_issues = db_session.query(CivicIssue).all()

        # Step 3: Analyze relationship
        match = cls.analyze_relationship(
            candidate_grievance=grievance,
            existing_issues=existing_issues,
            candidate_lat=candidate_lat,
            candidate_lon=candidate_lon
        )

        now_utc = datetime.now(timezone.utc)

        # ---------------------------------------------------------------------
        # Action A: DUPLICATE
        # ---------------------------------------------------------------------
        if match.relationship_type == IssueRelationshipType.DUPLICATE:
            # Do not create new issue or link duplicate
            target_issue = db_session.query(CivicIssue).filter_by(id=match.target_issue_id).first()
            return target_issue, match

        # ---------------------------------------------------------------------
        # Action B: MULTIPLE_COMPLAINTS_SAME_ISSUE
        # ---------------------------------------------------------------------
        if match.relationship_type == IssueRelationshipType.MULTIPLE_COMPLAINTS_SAME_ISSUE:
            target_issue = db_session.query(CivicIssue).filter_by(id=match.target_issue_id).first()
            if target_issue:
                # Link underlying source record to preserved issue
                grievance.civic_issue_id = target_issue.id
                target_issue.repeat_count = (target_issue.repeat_count or 1) + 1
                target_issue.updated_at = now_utc

                # CRITICAL DIRECTIVE: "Do not interpret repeated complaints as proof that every complaint is valid"
                # Keep verification status as PENDING_VERIFICATION
                target_issue.resolution_verification_status = ResolutionVerificationStatus.PENDING_VERIFICATION

                # Emit IssueEvent audit log
                event = IssueEvent(
                    civic_issue_id=target_issue.id,
                    event_timestamp=now_utc,
                    event_type="LINKED_MULTIPLE_COMPLAINT",
                    actor_type="INTELLIGENCE_PIPELINE",
                    notes=(
                        f"Linked grievance {grievance.grievance_id} as additional citizen petition on "
                        f"{target_issue.issue_code}. Total complaints: {target_issue.repeat_count}. "
                        f"Verification remains PENDING_VERIFICATION."
                    )
                )
                db_session.add(event)
                return target_issue, match

        # ---------------------------------------------------------------------
        # Action C: RECURRING_ISSUE
        # ---------------------------------------------------------------------
        if match.relationship_type == IssueRelationshipType.RECURRING_ISSUE:
            prior_issue = db_session.query(CivicIssue).filter_by(id=match.target_issue_id).first()
            # Provision recurrence incident
            new_issue_code = f"ISSUE-REC-{uuid.uuid4().hex[:8].upper()}"
            title = f"Recurring Issue: {prior_issue.title if prior_issue else 'Civic Problem'}"
            desc = grievance.description_or_permitted_summary or (prior_issue.description if prior_issue else "")

            rec_issue = CivicIssue(
                issue_code=new_issue_code,
                title=title,
                description=desc,
                category_id=prior_issue.category_id if prior_issue else None,
                department_id=prior_issue.department_id if prior_issue else None,
                administrative_area_id=prior_issue.administrative_area_id if prior_issue else None,
                status=CivicIssueStatus.OPEN,
                severity=prior_issue.severity if prior_issue else CivicIssueSeverity.MEDIUM,
                latitude=candidate_lat or (prior_issue.latitude if prior_issue else None),
                longitude=candidate_lon or (prior_issue.longitude if prior_issue else None),
                reported_date=grievance.submission_date,
                repeat_count=(prior_issue.repeat_count if prior_issue else 1) + 1,
                resolution_verification_status=ResolutionVerificationStatus.PENDING_VERIFICATION,
                is_test_fixture=is_test_fixture
            )
            db_session.add(rec_issue)
            db_session.flush()

            grievance.civic_issue_id = rec_issue.id

            # Emit Recurrence Event
            event = IssueEvent(
                civic_issue_id=rec_issue.id,
                event_timestamp=now_utc,
                event_type="RECURRENCE_DETECTED",
                actor_type="INTELLIGENCE_PIPELINE",
                notes=(
                    f"Recurrence detected linking to prior issue {prior_issue.issue_code if prior_issue else 'N/A'}. "
                    f"Recurrence count: {rec_issue.repeat_count}."
                )
            )
            db_session.add(event)
            return rec_issue, match

        # ---------------------------------------------------------------------
        # Action D: NEW_ISSUE / SEPARATE_ISSUES_SAME_AREA / UNRELATED_SIMILAR_REPORTS
        # ---------------------------------------------------------------------
        # Resolve category entity
        if isinstance(grievance.issue_category, IssueCategoryEnum):
            cat_enum = grievance.issue_category
        elif isinstance(grievance.issue_category, str):
            try:
                cat_enum = IssueCategoryEnum(grievance.issue_category)
            except ValueError:
                cat_enum = IssueCategoryEnum.OTHER_CIVIC_ISSUES
        else:
            cat_enum = IssueCategoryEnum.OTHER_CIVIC_ISSUES

        cat_enum_val = cat_enum.value
        cat_entity = db_session.query(IssueCategory).filter_by(code=cat_enum).first()

        # Resolve administrative area entity
        area_entity = None
        if grievance.administrative_area_id:
            area_entity = db_session.query(AdministrativeArea).filter_by(area_code=grievance.administrative_area_id).first()

        # Resolve department entity
        dept_entity = None
        if grievance.department_id:
            dept_entity = db_session.query(CivicDepartment).filter_by(code=grievance.department_id).first()

        issue_suffix = uuid.uuid4().hex[:8].upper()
        area_part = (grievance.administrative_area_id or "TN").replace("ADM-TN-", "").replace("-", "")[:8]
        issue_code = f"ISSUE-{cat_enum_val[:4].upper()}-{area_part}-{issue_suffix}"

        title_en = f"Civic Issue: {cat_enum_val.replace('_', ' ').title()} in {grievance.administrative_area_id or 'Tamil Nadu'}"
        desc = grievance.description_or_permitted_summary or f"Reported civic issue relating to {cat_enum_val}."

        new_issue = CivicIssue(
            issue_code=issue_code,
            title=title_en,
            description=desc,
            category_id=cat_entity.id if cat_entity else 1,
            department_id=dept_entity.id if dept_entity else None,
            administrative_area_id=area_entity.id if area_entity else None,
            status=CivicIssueStatus.OPEN,
            severity=CivicIssueSeverity.MEDIUM,
            latitude=candidate_lat,
            longitude=candidate_lon,
            reported_date=grievance.submission_date,
            repeat_count=1,
            resolution_verification_status=ResolutionVerificationStatus.PENDING_VERIFICATION,
            is_test_fixture=is_test_fixture
        )
        db_session.add(new_issue)
        db_session.flush()

        grievance.civic_issue_id = new_issue.id

        # Emit Creation Event
        event = IssueEvent(
            civic_issue_id=new_issue.id,
            event_timestamp=now_utc,
            event_type="CREATED",
            actor_type="INTELLIGENCE_PIPELINE",
            notes=f"Created canonical CivicIssue {new_issue.issue_code} for grievance {grievance.grievance_id}."
        )
        db_session.add(event)

        return new_issue, match
