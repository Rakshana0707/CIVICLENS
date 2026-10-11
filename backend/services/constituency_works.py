"""
Phase 6 — Constituency Works and Development Tracking Service.

Manages public projects, MPLADS, MLACDS, and state development works.
Enforces:
1. Explicit status hierarchy (PROPOSED to INDEPENDENTLY_VERIFIED_COMPLETED).
2. Distinction between Allocation, Sanction, Release, Expenditure, and Actual Outcome.
3. Strict separation of representative-sponsored works from general executive state/central projects.
4. Independent verification cross-referencing and conflict detection.
"""

import logging
from typing import Dict, Any, List, Optional, Tuple, Set
from datetime import datetime, timezone
from sqlalchemy.orm import Session

from backend.models.representative import (
    Constituency,
    Representative,
    ConstituencyWork,
    WorkProjectStatus,
    AttributionType
)

logger = logging.getLogger("civiclens.phase6.works")
logging.basicConfig(level=logging.INFO)


class ConflictingStatusError(Exception):
    """Raised when conflicting implementation reports contradict project status."""
    pass


class ConstituencyWorksService:
    """
    Core service for tracking constituency works, financial utilization,
    project lifecycles, and verification audits.
    """

    def __init__(self, db: Optional[Session] = None):
        self.db = db

    def record_work(
        self,
        work_id: str,
        constituency_id: str,
        scheme_id: str,
        project_description: str,
        sanctioned_amount: float,
        released_amount: float = 0.0,
        reported_expenditure: float = 0.0,
        approval_date: Optional[str] = None,
        completion_date: Optional[str] = None,
        project_status: str = WorkProjectStatus.PROPOSED,
        representative_id: Optional[str] = None,
        implementing_agency: Optional[str] = None,
        source_document_id: Optional[str] = None,
        source_reference: Optional[str] = None,
        attribution_type: str = AttributionType.REPRESENTATIVE_SPONSORED,
        verification_source: Optional[str] = None,
        last_updated: Optional[str] = None
    ) -> ConstituencyWork:
        """
        Records or updates a constituency development project with automated
        financial integrity assertions and data quality validation.
        """
        # Status validation
        valid_statuses = {s.value for s in WorkProjectStatus}
        if project_status not in valid_statuses:
            logger.warning(f"Unrecognized project status '{project_status}', defaulting to UNKNOWN")
            project_status = WorkProjectStatus.UNKNOWN

        data_issues: List[str] = []
        has_conflict = False

        # 1. Date completeness checks
        if project_status in (WorkProjectStatus.REPORTED_COMPLETED, WorkProjectStatus.INDEPENDENTLY_VERIFIED_COMPLETED) and not completion_date:
            data_issues.append("MISSING_COMPLETION_DATE: Project marked completed but completion_date is missing.")

        if project_status in (WorkProjectStatus.SANCTIONED, WorkProjectStatus.FUNDS_RELEASED, WorkProjectStatus.WORK_IN_PROGRESS) and not approval_date:
            data_issues.append("MISSING_APPROVAL_DATE: Project active but approval_date is missing.")

        # 2. Financial validation: Allocation != Released != Spent
        if reported_expenditure > released_amount and released_amount > 0.0:
            data_issues.append(f"EXPENDITURE_EXCEEDS_RELEASE: Reported expenditure (₹{reported_expenditure:,.2f}) exceeds released amount (₹{released_amount:,.2f}).")
            has_conflict = True

        if released_amount > sanctioned_amount and sanctioned_amount > 0.0:
            data_issues.append(f"RELEASE_EXCEEDS_SANCTION: Released funds (₹{released_amount:,.2f}) exceed sanctioned amount (₹{sanctioned_amount:,.2f}).")

        # 3. Attribution rule: Executive projects must NOT be attributed to individual representatives
        if attribution_type in (AttributionType.EXECUTIVE_STATE_PROJECT, AttributionType.EXECUTIVE_CENTRAL_PROJECT):
            if representative_id is not None:
                logger.info(f"Clearing representative_id for executive project {work_id} to prevent false personal attribution.")
                representative_id = None

        work = None
        if self.db:
            work = self.db.query(ConstituencyWork).filter(ConstituencyWork.work_id == work_id).first()

        if work:
            work.constituency_id = constituency_id
            work.scheme_id = scheme_id
            work.project_description = project_description
            work.sanctioned_amount = sanctioned_amount
            work.released_amount = released_amount
            work.reported_expenditure = reported_expenditure
            work.approval_date = approval_date
            work.completion_date = completion_date
            work.project_status = project_status
            work.representative_id = representative_id
            work.implementing_agency = implementing_agency
            work.source_document_id = source_document_id
            work.source_reference = source_reference
            work.attribution_type = attribution_type
            work.verification_source = verification_source
            work.has_conflicting_status = has_conflict or work.has_conflicting_status
            work.data_quality_issues = list(set((work.data_quality_issues or []) + data_issues))
            work.last_updated = last_updated or datetime.now(timezone.utc).strftime("%Y-%m-%d")
        else:
            work = ConstituencyWork(
                work_id=work_id,
                representative_id=representative_id,
                constituency_id=constituency_id,
                scheme_id=scheme_id,
                project_description=project_description,
                sanctioned_amount=sanctioned_amount,
                released_amount=released_amount,
                reported_expenditure=reported_expenditure,
                approval_date=approval_date,
                completion_date=completion_date,
                project_status=project_status,
                implementing_agency=implementing_agency,
                source_document_id=source_document_id,
                source_reference=source_reference,
                attribution_type=attribution_type,
                verification_source=verification_source,
                has_conflicting_status=has_conflict,
                data_quality_issues=data_issues,
                last_updated=last_updated or datetime.now(timezone.utc).strftime("%Y-%m-%d")
            )
            if self.db:
                self.db.add(work)

        if self.db:
            self.db.commit()
            self.db.refresh(work)

        logger.info(f"Recorded constituency work {work_id} in {constituency_id} (Status: {project_status}, Scheme: {scheme_id})")
        return work

    def cross_reference_verification(
        self,
        work_id: str,
        independent_status: str,
        audit_source_id: str,
        audit_notes: Optional[str] = None
    ) -> ConstituencyWork:
        """
        Cross-references self-reported project status with an independent implementation/audit report.
        Detects conflicts between portal claims and on-the-ground audit findings.
        """
        work = None
        if self.db:
            work = self.db.query(ConstituencyWork).filter(ConstituencyWork.work_id == work_id).first()

        if not work:
            raise ValueError(f"Work ID '{work_id}' not found.")

        current_status = work.project_status

        # Detect conflicting status: Portal claims completed, but audit reveals incomplete
        if current_status == WorkProjectStatus.REPORTED_COMPLETED and independent_status in (WorkProjectStatus.WORK_IN_PROGRESS, WorkProjectStatus.SANCTIONED, WorkProjectStatus.PROPOSED):
            work.has_conflicting_status = True
            issue = f"AUDIT_STATUS_CONFLICT: Portal self-reported COMPLETED, but audit {audit_source_id} found {independent_status}. Note: {audit_notes or ''}"
            work.data_quality_issues = list(set((work.data_quality_issues or []) + [issue]))
            work.verification_source = audit_source_id
            logger.warning(issue)
        elif independent_status == WorkProjectStatus.INDEPENDENTLY_VERIFIED_COMPLETED:
            work.project_status = WorkProjectStatus.INDEPENDENTLY_VERIFIED_COMPLETED
            work.verification_source = audit_source_id
            work.has_conflicting_status = False

        if self.db:
            self.db.commit()
            self.db.refresh(work)

        return work

    def calculate_constituency_summary(
        self,
        constituency_id: str,
        scheme_id: Optional[str] = None,
        representative_id: Optional[str] = None,
        works_cache: Optional[List[ConstituencyWork]] = None
    ) -> Dict[str, Any]:
        """
        Aggregates financial expenditure, project lifecycles, and verification metrics
        for a constituency or representative.
        """
        works: List[ConstituencyWork] = []
        if works_cache is not None:
            works = [
                w for w in works_cache
                if w.constituency_id == constituency_id
                and (scheme_id is None or w.scheme_id == scheme_id)
                and (representative_id is None or w.representative_id == representative_id)
            ]
        elif self.db:
            q = self.db.query(ConstituencyWork).filter(ConstituencyWork.constituency_id == constituency_id)
            if scheme_id:
                q = q.filter(ConstituencyWork.scheme_id == scheme_id)
            if representative_id:
                q = q.filter(ConstituencyWork.representative_id == representative_id)
            works = q.all()

        total_works = len(works)
        total_sanctioned = sum(w.sanctioned_amount for w in works)
        total_released = sum(w.released_amount for w in works)
        total_expenditure = sum(w.reported_expenditure for w in works)

        unspent_balance = max(0.0, total_released - total_expenditure)
        unreleased_funds = max(0.0, total_sanctioned - total_released)

        status_counts: Dict[str, int] = {s.value: 0 for s in WorkProjectStatus}
        attribution_counts: Dict[str, int] = {a.value: 0 for a in AttributionType}
        conflicting_status_count = 0

        for w in works:
            status_counts[w.project_status] = status_counts.get(w.project_status, 0) + 1
            attribution_counts[w.attribution_type] = attribution_counts.get(w.attribution_type, 0) + 1
            if w.has_conflicting_status:
                conflicting_status_count += 1

        completed_reported = status_counts.get(WorkProjectStatus.REPORTED_COMPLETED, 0)
        completed_verified = status_counts.get(WorkProjectStatus.INDEPENDENTLY_VERIFIED_COMPLETED, 0)
        total_completed = completed_reported + completed_verified

        # Rates & Ratios
        fund_utilization_ratio = round((total_expenditure / total_released * 100), 2) if total_released > 0 else 0.0
        physical_completion_rate = round((total_completed / total_works * 100), 2) if total_works > 0 else 0.0
        independent_verification_rate = round((completed_verified / total_completed * 100), 2) if total_completed > 0 else 0.0

        return {
            "constituency_id": constituency_id,
            "scheme_id": scheme_id or "ALL_SCHEMES",
            "representative_id": representative_id,
            "total_projects": total_works,
            "financial_summary": {
                "total_sanctioned_inr": total_sanctioned,
                "total_released_inr": total_released,
                "total_expenditure_inr": total_expenditure,
                "unspent_balance_inr": unspent_balance,
                "unreleased_funds_inr": unreleased_funds,
                "fund_utilization_percent": fund_utilization_ratio
            },
            "status_breakdown": status_counts,
            "attribution_breakdown": attribution_counts,
            "data_quality": {
                "conflicting_status_projects": conflicting_status_count,
                "independent_verification_percent": independent_verification_rate
            },
            "output_metrics": {
                "physical_completion_percent": physical_completion_rate,
                "total_completed_projects": total_completed
            },
            "methodology_disclaimers": {
                "expenditure_disclaimer": "Sanctioned funds and released amounts do not represent actual expenditure until verified.",
                "outcome_disclaimer": "Physical completion of works does not guarantee developmental outcome or service functionality.",
                "attribution_disclaimer": "General state and central executive projects in the constituency are not attributed to the elected representative."
            }
        }
