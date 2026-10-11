"""
Phase 6 — Legislative Activity Analysis Service.

Provides ingestion, aggregation, institutional contextualization, and comparative
analysis for parliamentary (Lok Sabha / Rajya Sabha) and state assembly (TNLA) activity.

Enforces:
1. Clear distinction between zero activity and unavailable records.
2. Contextual normalization between MPs and MLAs (rejecting raw count parity).
3. Non-inference of legislative effectiveness from volume alone.
"""

import logging
from typing import Dict, Any, List, Optional, Tuple, Set
from datetime import datetime, timezone
from sqlalchemy.orm import Session

from backend.models.representative import (
    Representative,
    LegislativeActivity,
    LegislativeActivityType,
    DataQualityStatus,
    RepresentativeType
)

logger = logging.getLogger("civiclens.phase6.legislative")
logging.basicConfig(level=logging.INFO)


class InstitutionalContext:
    """Institutional characteristics, sitting baselines, and floor rules per legislative body."""

    PROFILES: Dict[str, Dict[str, Any]] = {
        "TN_ASSEMBLY": {
            "body_name": "Tamil Nadu Legislative Assembly",
            "tier": "STATE_ASSEMBLY",
            "average_annual_sittings": 38,
            "question_hour_rules": "Oral Starred Questions with supplementaries; Unstarred replies published in synopses.",
            "attendance_publishing_practice": "Attendance registers are maintained internally; daily member-wise attendance percentages are NOT publicly gazetted online.",
            "debate_formats": ["Budget Demands on Grants", "Call Attention (Rule 55)", "Rule 110 Statements", "Zero Hour Mentions"],
            "minister_exclusion_rule": True  # Ministers do not submit questions or private member bills
        },
        "LOK_SABHA": {
            "body_name": "Lok Sabha (House of the People)",
            "tier": "PARLIAMENT_LOWER",
            "average_annual_sittings": 65,
            "question_hour_rules": "Computerized ballot; max 5 questions admitted per MP per day (1 Starred + 4 Unstarred).",
            "attendance_publishing_practice": "Official electronic sign-in registers published per session on Sansad portal / PRS India.",
            "debate_formats": ["Rule 193 Discussions", "Calling Attention", "Zero Hour", "Budget Debates", "Special Mentions"],
            "minister_exclusion_rule": True
        },
        "RAJYA_SABHA": {
            "body_name": "Rajya Sabha (Council of States)",
            "tier": "PARLIAMENT_UPPER",
            "average_annual_sittings": 62,
            "question_hour_rules": "Balloted Starred and Unstarred questions; max 5 per day.",
            "attendance_publishing_practice": "Official attendance portal published per session.",
            "debate_formats": ["Special Mentions", "Short Duration Discussions", "Government Bills"],
            "minister_exclusion_rule": True
        }
    }

    @classmethod
    def get_profile(cls, legislative_body: str) -> Dict[str, Any]:
        return cls.PROFILES.get(legislative_body, {
            "body_name": legislative_body,
            "tier": "UNKNOWN",
            "average_annual_sittings": 50,
            "attendance_publishing_practice": "Unknown",
            "minister_exclusion_rule": True
        })


class LegislativeActivityService:
    """
    Core service for recording, aggregating, and contextualizing legislative participation.
    """

    def __init__(self, db: Optional[Session] = None):
        self.db = db

    def record_activity(
        self,
        activity_id: str,
        representative_id: str,
        legislative_body: str,
        session: str,
        activity_type: str,
        activity_date: Optional[str] = None,
        count: int = 1,
        value: Optional[float] = None,
        title_subject: Optional[str] = None,
        ministry_or_department: Optional[str] = None,
        source_document_id: Optional[str] = None,
        source_reference: Optional[str] = None,
        data_quality_status: str = DataQualityStatus.VERIFIED,
        notes: Optional[str] = None
    ) -> LegislativeActivity:
        """Records an itemized legislative activity entry with complete provenance."""
        act = None
        if self.db:
            act = self.db.query(LegislativeActivity).filter(LegislativeActivity.activity_id == activity_id).first()

        if act:
            act.representative_id = representative_id
            act.legislative_body = legislative_body
            act.session = session
            act.activity_type = activity_type
            act.activity_date = activity_date
            act.count = count
            act.value = value
            act.title_subject = title_subject
            act.ministry_or_department = ministry_or_department
            act.source_document_id = source_document_id
            act.source_reference = source_reference
            act.data_quality_status = data_quality_status
            act.notes = notes
        else:
            act = LegislativeActivity(
                activity_id=activity_id,
                representative_id=representative_id,
                legislative_body=legislative_body,
                session=session,
                activity_type=activity_type,
                activity_date=activity_date,
                count=count,
                value=value,
                title_subject=title_subject,
                ministry_or_department=ministry_or_department,
                source_document_id=source_document_id,
                source_reference=source_reference,
                data_quality_status=data_quality_status,
                notes=notes
            )
            if self.db:
                self.db.add(act)

        if self.db:
            self.db.commit()
            self.db.refresh(act)

        logger.info(f"Recorded activity {activity_id} for {representative_id} ({activity_type} in {legislative_body})")
        return act

    def record_unavailable_indicator(
        self,
        representative_id: str,
        legislative_body: str,
        session: str,
        activity_type: str,
        reason: str,
        source_document_id: Optional[str] = None
    ) -> LegislativeActivity:
        """
        Records an explicit indicator that a metric is UNAVAILABLE/NOT_RECORDED.
        Crucial for preventing missing records from being misinterpreted as zero activity!
        """
        act_id = f"UNAVAIL_{representative_id}_{legislative_body}_{session}_{activity_type}"
        return self.record_activity(
            activity_id=act_id,
            representative_id=representative_id,
            legislative_body=legislative_body,
            session=session,
            activity_type=activity_type,
            count=0,
            value=None,
            source_document_id=source_document_id,
            source_reference=f"Notice: Metric not officially published ({reason})",
            data_quality_status=DataQualityStatus.UNAVAILABLE,
            notes=reason
        )

    def calculate_summary(
        self,
        representative_id: str,
        legislative_body: Optional[str] = None,
        session: Optional[str] = None,
        activities_cache: Optional[List[LegislativeActivity]] = None
    ) -> Dict[str, Any]:
        """
        Calculates supported legislative activity metrics for a representative.
        Distinguishes unavailable records from zero activity.
        """
        activities: List[LegislativeActivity] = []
        if activities_cache is not None:
            activities = [
                a for a in activities_cache
                if a.representative_id == representative_id
                and (legislative_body is None or a.legislative_body == legislative_body)
                and (session is None or a.session == session)
            ]
        elif self.db:
            q = self.db.query(LegislativeActivity).filter(LegislativeActivity.representative_id == representative_id)
            if legislative_body:
                q = q.filter(LegislativeActivity.legislative_body == legislative_body)
            if session:
                q = q.filter(LegislativeActivity.session == session)
            activities = q.all()

        starred_questions = 0
        unstarred_questions = 0
        debates_count = 0
        bills_count = 0
        committee_count = 0
        call_attention_count = 0

        attendance_values: List[float] = []
        attendance_status = DataQualityStatus.NOT_RECORDED
        questions_status = DataQualityStatus.VERIFIED
        debates_status = DataQualityStatus.VERIFIED

        # Track sources
        source_refs: Set[str] = set()

        for a in activities:
            if a.source_reference:
                source_refs.add(a.source_reference)

            # Check for unavailable markers
            if a.data_quality_status in (DataQualityStatus.UNAVAILABLE, DataQualityStatus.NOT_RECORDED):
                if a.activity_type == LegislativeActivityType.ATTENDANCE:
                    attendance_status = DataQualityStatus.UNAVAILABLE
                continue

            if a.activity_type == LegislativeActivityType.QUESTION_STARRED:
                starred_questions += a.count
            elif a.activity_type == LegislativeActivityType.QUESTION_UNSTARRED:
                unstarred_questions += a.count
            elif a.activity_type == LegislativeActivityType.DEBATE:
                debates_count += a.count
            elif a.activity_type == LegislativeActivityType.BILL:
                bills_count += a.count
            elif a.activity_type == LegislativeActivityType.COMMITTEE:
                committee_count += a.count
            elif a.activity_type == LegislativeActivityType.CALL_ATTENTION:
                call_attention_count += a.count
            elif a.activity_type == LegislativeActivityType.ATTENDANCE:
                if a.value is not None:
                    attendance_values.append(a.value)
                    attendance_status = DataQualityStatus.VERIFIED

        total_questions = starred_questions + unstarred_questions
        avg_attendance = (sum(attendance_values) / len(attendance_values)) if attendance_values else None

        # Contextual metadata
        body_key = legislative_body or (activities[0].legislative_body if activities else "UNKNOWN")
        inst_profile = InstitutionalContext.get_profile(body_key)

        return {
            "representative_id": representative_id,
            "legislative_body": body_key,
            "session": session or "ALL_SESSIONS",
            "starred_questions_count": starred_questions,
            "unstarred_questions_count": unstarred_questions,
            "total_questions_count": total_questions,
            "debates_and_speeches_count": debates_count,
            "call_attention_motions_count": call_attention_count,
            "private_member_bills_count": bills_count,
            "committee_participations_count": committee_count,
            "attendance": {
                "percentage": avg_attendance,
                "status": attendance_status.value if isinstance(attendance_status, DataQualityStatus) else attendance_status,
                "is_available": avg_attendance is not None,
                "note": "Official individual attendance registers are published." if avg_attendance is not None else inst_profile["attendance_publishing_practice"]
            },
            "institutional_context": {
                "body_name": inst_profile["body_name"],
                "average_annual_sittings": inst_profile["average_annual_sittings"],
                "question_hour_rules": inst_profile.get("question_hour_rules", "")
            },
            "source_references_count": len(source_refs),
            "source_references_sample": list(source_refs)[:5],
            "methodology_disclaimer": "Activity counts reflect documented participation volume, not legislative quality or policy effectiveness."
        }

    def compare_representatives(
        self,
        summary_a: Dict[str, Any],
        summary_b: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Compares two representatives.
        Crucial requirement: Explains differences in institutional roles, reporting practices,
        and available opportunities, and avoids raw count parity between MPs and MLAs.
        """
        body_a = summary_a["legislative_body"]
        body_b = summary_b["legislative_body"]

        is_cross_institutional = (body_a != body_b)
        institutional_warning = None

        if is_cross_institutional:
            inst_a = summary_a["institutional_context"]["body_name"]
            inst_b = summary_b["institutional_context"]["body_name"]
            sittings_a = summary_a["institutional_context"]["average_annual_sittings"]
            sittings_b = summary_b["institutional_context"]["average_annual_sittings"]

            institutional_warning = (
                f"CROSS-INSTITUTIONAL COMPARISON CAUTION: Comparing {summary_a['representative_id']} ({inst_a}) "
                f"with {summary_b['representative_id']} ({inst_b}) using raw counts is methodologically invalid. "
                f"{inst_a} sits approximately {sittings_a} days/year, whereas {inst_b} sits {sittings_b} days/year. "
                f"Question balloting procedures, debate allocations, and attendance reporting differ fundamentally."
            )

        # Compute normalized rates per 10 sittings
        sittings_a = summary_a["institutional_context"]["average_annual_sittings"]
        sittings_b = summary_b["institutional_context"]["average_annual_sittings"]

        norm_questions_a = round((summary_a["total_questions_count"] / max(1, sittings_a)) * 10, 2)
        norm_questions_b = round((summary_b["total_questions_count"] / max(1, sittings_b)) * 10, 2)

        norm_debates_a = round((summary_a["debates_and_speeches_count"] / max(1, sittings_a)) * 10, 2)
        norm_debates_b = round((summary_b["debates_and_speeches_count"] / max(1, sittings_b)) * 10, 2)

        return {
            "representative_a": summary_a["representative_id"],
            "representative_b": summary_b["representative_id"],
            "is_cross_institutional": is_cross_institutional,
            "institutional_warning": institutional_warning,
            "comparison_metrics": {
                "raw_comparison": {
                    "total_questions": {"rep_a": summary_a["total_questions_count"], "rep_b": summary_b["total_questions_count"]},
                    "debates": {"rep_a": summary_a["debates_and_speeches_count"], "rep_b": summary_b["debates_and_speeches_count"]}
                },
                "normalized_per_10_sittings": {
                    "questions_per_10_sittings": {"rep_a": norm_questions_a, "rep_b": norm_questions_b},
                    "debates_per_10_sittings": {"rep_a": norm_debates_a, "rep_b": norm_debates_b}
                },
                "attendance_availability": {
                    "rep_a_available": summary_a["attendance"]["is_available"],
                    "rep_b_available": summary_b["attendance"]["is_available"]
                }
            },
            "effectiveness_disclaimer": "Higher participation count does not directly indicate legislative effectiveness or civic impact."
        }
