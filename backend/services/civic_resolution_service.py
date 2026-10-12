"""
Grievance Response & Resolution Evidence Tracker Service (CIVICLENS TN - Phase 8.6)
===================================================================================
Connects grievance records with publicly documented responses, action-taken reports,
and empirical resolution evidence.

Tracks the 9 canonical lifecycle states:
  - submitted
  - acknowledged
  - under_review
  - action_reported
  - marked_resolved
  - independently_verified_resolved
  - reopened
  - disputed
  - unknown

Core Principles & Safeguards:
  - Only uses states supported by source evidence.
  - marked_resolved means the official source claims resolution; it does NOT
    automatically establish that the physical issue was fixed.
  - For each response record, stores:
      issue_id, response_date, response_summary, source_document_id,
      reported_status, verification_status, supporting_evidence, review_notes.
  - Strict Public Work Linkage Guard: Never claims that a public work resolved
    a grievance unless the relationship is corroborated by evidence.
  - Handles missing responses, conflicting statuses, incomplete records, and
    unsupported resolution claims.
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple, Any
from sqlalchemy.orm import Session

from backend.models.civic_issue import (
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
    DataQualitySeverity,
    CivicDepartment
)


# Mapping of raw departmental action remarks / keywords to 9 canonical states
STATUS_MAPPING_RULES: Dict[str, CivicTrackingState] = {
    # marked_resolved
    "resolved": CivicTrackingState.MARKED_RESOLVED,
    "closed": CivicTrackingState.MARKED_RESOLVED,
    "completed": CivicTrackingState.MARKED_RESOLVED,
    "disposed": CivicTrackingState.MARKED_RESOLVED,
    "action taken and closed": CivicTrackingState.MARKED_RESOLVED,
    "தீர்க்கப்பட்டது": CivicTrackingState.MARKED_RESOLVED,
    "முடிவுற்றது": CivicTrackingState.MARKED_RESOLVED,

    # action_reported
    "action taken": CivicTrackingState.ACTION_REPORTED,
    "work order issued": CivicTrackingState.ACTION_REPORTED,
    "field inspection completed": CivicTrackingState.ACTION_REPORTED,
    "நடவடிக்கை எடுக்கப்பட்டது": CivicTrackingState.ACTION_REPORTED,

    # under_review
    "under enquiry": CivicTrackingState.UNDER_REVIEW,
    "in progress": CivicTrackingState.UNDER_REVIEW,
    "under investigation": CivicTrackingState.UNDER_REVIEW,
    "assigned to ae": CivicTrackingState.UNDER_REVIEW,
    "பரிசீலனையில் உள்ளது": CivicTrackingState.UNDER_REVIEW,
    "விசாரணையில் உள்ளது": CivicTrackingState.UNDER_REVIEW,

    # acknowledged
    "acknowledged": CivicTrackingState.ACKNOWLEDGED,
    "registered": CivicTrackingState.ACKNOWLEDGED,
    "admitted": CivicTrackingState.ACKNOWLEDGED,
    "பதிவு செய்யப்பட்டது": CivicTrackingState.ACKNOWLEDGED,

    # reopened
    "reopened": CivicTrackingState.REOPENED,
    "unsatisfactory closure appeal": CivicTrackingState.REOPENED,
    "மறுதிறப்பு செய்யப்பட்டது": CivicTrackingState.REOPENED,

    # disputed
    "disputed": CivicTrackingState.DISPUTED,
    "false closure contested": CivicTrackingState.DISPUTED,
    "மறுப்பு தெரிவிக்கப்பட்டது": CivicTrackingState.DISPUTED,

    # submitted
    "submitted": CivicTrackingState.SUBMITTED,
    "lodged": CivicTrackingState.SUBMITTED,
    "விண்ணப்பிக்கப்பட்டது": CivicTrackingState.SUBMITTED
}


@dataclass
class ResolutionRecordPayload:
    """Input payload for recording official response or resolution update."""
    issue_id: int
    response_date: datetime
    response_summary: str
    source_document_id: Optional[int] = None
    reported_status: str = CivicTrackingState.ACKNOWLEDGED.value
    verification_status: ResolutionVerificationStatus = ResolutionVerificationStatus.PENDING_VERIFICATION
    supporting_evidence: Optional[Dict[str, Any]] = None
    review_notes: Optional[str] = None
    department_id: Optional[int] = None
    public_work_id: Optional[int] = None
    action_type: ResponseActionType = ResponseActionType.ACKNOWLEDGED


class CivicResolutionTrackerService:
    """
    Core service tracking grievance responses, validating resolution claims,
    and linking empirical evidence.
    """

    @classmethod
    def parse_reported_status(cls, raw_status: Optional[str]) -> CivicTrackingState:
        """
        Maps raw departmental status string to one of the 9 canonical tracking states.
        Defaults to UNKNOWN if missing or unparseable.
        """
        if not raw_status:
            return CivicTrackingState.UNKNOWN

        clean = raw_status.strip().lower()
        if clean in STATUS_MAPPING_RULES:
            return STATUS_MAPPING_RULES[clean]

        for phrase, state in STATUS_MAPPING_RULES.items():
            if phrase in clean:
                return state

        return CivicTrackingState.UNKNOWN

    @classmethod
    def record_official_response(
        cls,
        db_session: Session,
        payload: ResolutionRecordPayload,
        is_test_fixture: bool = False
    ) -> ResponseRecord:
        """
        Records an official departmental response or Action Taken Report (ATR).
        Enforces strict distinction between marked_resolved and verified_resolved.
        """
        issue = db_session.query(CivicIssue).filter_by(id=payload.issue_id).first()
        if not issue:
            raise ValueError(f"CivicIssue with ID {payload.issue_id} not found.")

        now_utc = datetime.now(timezone.utc)
        resp_dt = payload.response_date
        if resp_dt and resp_dt.tzinfo is None:
            resp_dt = resp_dt.replace(tzinfo=timezone.utc)

        # ---------------------------------------------------------------------
        # Guard 1: Incomplete Record Handling
        # ---------------------------------------------------------------------
        status_enum = cls.parse_reported_status(payload.reported_status)
        is_incomplete = False
        if not payload.response_summary or len(payload.response_summary.strip()) < 3:
            status_enum = CivicTrackingState.UNKNOWN
            is_incomplete = True

        # ---------------------------------------------------------------------
        # Guard 2: Conflicting Status Detection
        # ---------------------------------------------------------------------
        # Check if existing responses on this issue conflict with incoming status
        existing_responses = db_session.query(ResponseRecord).filter_by(civic_issue_id=issue.id).all()
        has_conflict = False
        conflict_notes = []

        if existing_responses:
            latest_existing = sorted(existing_responses, key=lambda r: r.action_taken_date, reverse=True)[0]
            # Conflict scenario: previous was REOPENED or DISPUTED, incoming asserts marked_resolved without evidence
            if latest_existing.reported_status in (CivicTrackingState.REOPENED.value, CivicTrackingState.DISPUTED.value):
                if status_enum == CivicTrackingState.MARKED_RESOLVED and not payload.supporting_evidence:
                    has_conflict = True
                    status_enum = CivicTrackingState.DISPUTED
                    conflict_notes.append(
                        f"Status Conflict: Source asserts marked_resolved while active dispute/reopening remains unaddressed without evidence."
                    )

        # ---------------------------------------------------------------------
        # Guard 3: SLA Turnaround & Breach Calculation
        # ---------------------------------------------------------------------
        sla_breached = False
        delay_hours = 0.0

        if issue.target_resolution_date and resp_dt:
            target_dt = issue.target_resolution_date
            if target_dt.tzinfo is None:
                target_dt = target_dt.replace(tzinfo=timezone.utc)

            if resp_dt > target_dt:
                sla_breached = True
                delay_hours = round((resp_dt - target_dt).total_seconds() / 3600.0, 2)

        # ---------------------------------------------------------------------
        # Guard 4: Non-Fabrication of Resolution (marked_resolved != verified)
        # ---------------------------------------------------------------------
        verification_status = payload.verification_status
        is_evidence_supported = bool(payload.supporting_evidence and payload.supporting_evidence.get("evidence_url"))

        if status_enum == CivicTrackingState.MARKED_RESOLVED:
            # Source reports resolution, but physical resolution is NOT yet verified!
            verification_status = ResolutionVerificationStatus.PENDING_VERIFICATION
            issue.status = CivicIssueStatus.RESOLVED
            issue.actual_resolution_date = resp_dt
        elif status_enum == CivicTrackingState.INDEPENDENTLY_VERIFIED_RESOLVED:
            verification_status = ResolutionVerificationStatus.VERIFIED
            issue.status = CivicIssueStatus.VERIFIED_RESOLVED
            issue.resolution_verification_status = ResolutionVerificationStatus.VERIFIED
            issue.actual_resolution_date = resp_dt
        elif status_enum == CivicTrackingState.REOPENED:
            issue.status = CivicIssueStatus.OPEN
            issue.resolution_verification_status = ResolutionVerificationStatus.PENDING_VERIFICATION
        elif status_enum == CivicTrackingState.DISPUTED:
            issue.status = CivicIssueStatus.DISPUTED
            issue.resolution_verification_status = ResolutionVerificationStatus.CONTRADICTED

        # Compile review notes
        all_notes = []
        if payload.review_notes:
            all_notes.append(payload.review_notes)
        if conflict_notes:
            all_notes.extend(conflict_notes)
        if is_incomplete:
            all_notes.append("Incomplete Record: Insufficient response summary provided by source.")
        review_notes_str = " | ".join(all_notes) if all_notes else None

        response_code = f"RESP-{uuid.uuid4().hex[:10].upper()}"

        record = ResponseRecord(
            response_code=response_code,
            civic_issue_id=payload.issue_id,
            department_id=payload.department_id or issue.department_id,
            source_document_id=payload.source_document_id,
            action_type=payload.action_type,
            official_remark=payload.response_summary,
            response_summary=payload.response_summary,
            action_taken_date=resp_dt,
            sla_breached=sla_breached,
            delay_hours=delay_hours,
            reported_status=status_enum.value,
            verification_status=verification_status,
            supporting_evidence=payload.supporting_evidence,
            review_notes=review_notes_str,
            public_work_id=payload.public_work_id,
            is_evidence_supported=is_evidence_supported,
            is_test_fixture=is_test_fixture
        )
        db_session.add(record)
        db_session.flush()

        # Emit chronological IssueEvent
        event_notes = f"Department response logged: {status_enum.value}. SLA breach: {sla_breached}."
        if sla_breached:
            event_notes += f" Delay: {delay_hours:.1f} hours beyond Citizen's Charter standard."
        if has_conflict:
            event_notes += " Conflicting status flagged: Routed to DISPUTED."

        event = IssueEvent(
            civic_issue_id=issue.id,
            event_timestamp=now_utc,
            event_type="RESPONSE_LOGGED",
            actor_type="DEPARTMENT_PORTAL",
            notes=event_notes
        )
        db_session.add(event)

        # Flag DataQualityIssue for incomplete record or conflict
        if is_incomplete:
            dq = DataQualityIssue(
                civic_issue_id=issue.id,
                severity=DataQualitySeverity.WARNING,
                issue_type="INCOMPLETE_RESPONSE_RECORD",
                description="Action taken response logged with empty or uninformative remark."
            )
            db_session.add(dq)

        if has_conflict:
            dq = DataQualityIssue(
                civic_issue_id=issue.id,
                severity=DataQualitySeverity.ERROR,
                issue_type="CONFLICTING_STATUS",
                description="Department marked resolved while issue has unaddressed citizen dispute."
            )
            db_session.add(dq)

        return record

    @classmethod
    def verify_resolution_with_evidence(
        cls,
        db_session: Session,
        response_id: int,
        evidence_type: EvidenceType,
        title: str,
        description: str,
        evidence_url: Optional[str] = None,
        sha256_hash: Optional[str] = None,
        is_corroborating: bool = True,
        verified_by: Optional[str] = "Independent Auditor",
        is_test_fixture: bool = False
    ) -> Tuple[ResolutionEvidence, bool]:
        """
        Validates official response against empirical resolution evidence:
          - If corroborating evidence is confirmed -> advances status to independently_verified_resolved.
          - If contradicting evidence is supplied -> routes status to disputed / CONTRADICTED.
        """
        response = db_session.query(ResponseRecord).filter_by(id=response_id).first()
        if not response:
            raise ValueError(f"ResponseRecord with ID {response_id} not found.")

        issue = response.civic_issue
        now_utc = datetime.now(timezone.utc)

        evidence = ResolutionEvidence(
            response_id=response.id,
            evidence_type=evidence_type,
            title=title,
            description=description,
            evidence_url=evidence_url,
            sha256_hash=sha256_hash,
            is_verified=is_corroborating,
            verified_by=verified_by,
            verification_date=now_utc,
            is_test_fixture=is_test_fixture
        )
        db_session.add(evidence)
        db_session.flush()

        if is_corroborating and (evidence_url or sha256_hash or evidence_type in (EvidenceType.COMPLETION_CERTIFICATE, EvidenceType.CITIZEN_AUDIT)):
            # Valid empirical evidence validates the resolution!
            response.verification_status = ResolutionVerificationStatus.VERIFIED
            response.reported_status = CivicTrackingState.INDEPENDENTLY_VERIFIED_RESOLVED.value
            response.is_evidence_supported = True

            issue.resolution_verification_status = ResolutionVerificationStatus.VERIFIED
            issue.status = CivicIssueStatus.VERIFIED_RESOLVED

            event = IssueEvent(
                civic_issue_id=issue.id,
                event_timestamp=now_utc,
                event_type="INDEPENDENTLY_VERIFIED_RESOLVED",
                actor_type="CIVIC_AUDIT_ENGINE",
                notes=f"Resolution independently corroborated by {evidence_type.value}: {title}."
            )
            db_session.add(event)
            return evidence, True
        else:
            # Contradicting or insufficient evidence
            response.verification_status = ResolutionVerificationStatus.CONTRADICTED
            response.reported_status = CivicTrackingState.DISPUTED.value
            issue.resolution_verification_status = ResolutionVerificationStatus.CONTRADICTED
            issue.status = CivicIssueStatus.DISPUTED

            event = IssueEvent(
                civic_issue_id=issue.id,
                event_timestamp=now_utc,
                event_type="RESOLUTION_CONTRADICTED",
                actor_type="CIVIC_AUDIT_ENGINE",
                notes=f"Claimed resolution contradicted by empirical evidence {evidence_type.value}: {title}."
            )
            db_session.add(event)
            return evidence, False

    @classmethod
    def validate_and_link_public_work(
        cls,
        db_session: Session,
        issue_id: int,
        public_work_id: int,
        tender_reference_match: bool = False,
        explicit_source_reference: Optional[str] = None
    ) -> Tuple[bool, str]:
        """
        Validates linkage between a capital PublicWork and a CivicIssue.
        CRITICAL RULE: Do not claim that a public work resolved a grievance
        unless the relationship is corroborated by evidence.
        """
        issue = db_session.query(CivicIssue).filter_by(id=issue_id).first()
        work = db_session.query(PublicWork).filter_by(id=public_work_id).first()

        if not issue or not work:
            return False, "Issue or PublicWork entity not found."

        # Verification Criteria: Must have explicit tender reference match, or matching source reference
        has_evidentiary_support = False
        reasons = []

        if tender_reference_match and work.tender_ref:
            has_evidentiary_support = True
            reasons.append(f"Matching tender reference: {work.tender_ref}")

        if explicit_source_reference:
            has_evidentiary_support = True
            reasons.append(f"Explicit source document link: {explicit_source_reference}")

        # Check if work commenced before grievance was even reported
        if work.completion_date and issue.reported_date:
            work_comp = work.completion_date if work.completion_date.tzinfo else work.completion_date.replace(tzinfo=timezone.utc)
            issue_rep = issue.reported_date if issue.reported_date.tzinfo else issue.reported_date.replace(tzinfo=timezone.utc)
            if work_comp < issue_rep:
                # Work finished before complaint was lodged! Impossible for it to remediate this complaint
                has_evidentiary_support = False
                reasons = ["Public work completion date precedes issue reported date."]

        if has_evidentiary_support:
            # Formally link
            work.civic_issue_id = issue.id
            now_utc = datetime.now(timezone.utc)
            event = IssueEvent(
                civic_issue_id=issue.id,
                event_timestamp=now_utc,
                event_type="PUBLIC_WORK_LINKED",
                actor_type="CIVIC_AUDIT_ENGINE",
                notes=f"Linked remediating public work '{work.work_title}' ({work.work_code}). Evidence: {', '.join(reasons)}."
            )
            db_session.add(event)
            return True, f"Successfully linked public work: {', '.join(reasons)}"
        else:
            # Reject link!
            dq = DataQualityIssue(
                civic_issue_id=issue.id,
                severity=DataQualitySeverity.WARNING,
                issue_type="UNSUPPORTED_RESOLUTION_CLAIM",
                description=(
                    f"Rejected public work linkage: Attempted to link public work '{work.work_code}' "
                    f"to issue '{issue.issue_code}' without supporting tender or completion evidence."
                )
            )
            db_session.add(dq)
            return False, "UNSUPPORTED_RESOLUTION_CLAIM: Public work does not possess evidentiary link to civic issue."
