"""
Evidence-Based Promise Assessment Engine (Phase 3.11).

Creates a transparent, deterministic rule-based framework for evaluating the implementation status of a promise.

Supported Status Taxonomy:
- `not_assessed`: Promise has not been evaluated against evidence sources.
- `no_evidence_found`: Zero verifiable government evidence was found. (CRITICAL: Absence of evidence != Not Implemented).
- `announced`: Verified government announcement/press release, but formal GO or budget is pending.
- `policy_action`: Official Government Order (G.O.) or policy framework issued.
- `partially_implemented`: Initial budget allocation or Phase 1 rollout verified.
- `implemented`: Full government order fulfillment, budget execution, or operational delivery verified.
- `unclear`: Matched evidence is vague or low confidence, preventing definitive classification.
- `disputed`: Conflicting official reports or disputed implementation claims.

ML Limitation Rule:
ML retrieves and ranks candidate evidence; it does NOT independently make political judgments.
Assessment decisions follow an auditable, deterministic rule engine (methodology: `deterministic_rule_engine_v1`).
"""

import logging
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy.orm import Session

from backend.models.promise import (
    PoliticalPromise,
    PromiseAssessment,
    PromiseAssessmentHistory,
    PromiseEvidenceLink,
    PromiseSchemeLink,
    PromiseStatus
)
from backend.models.common import Evidence

logger = logging.getLogger(__name__)

METHODOLOGY_ID = "deterministic_rule_engine_v1"


class PromiseAssessmentEngine:
    """
    Transparent, rule-based assessment engine evaluating promise status against evidence.
    """

    def __init__(self, db_session: Session):
        self.db = db_session

    def evaluate_promise(
        self,
        promise: PoliticalPromise,
        persist: bool = True,
        evaluator_id: str = METHODOLOGY_ID
    ) -> Dict[str, Any]:
        """
        Evaluates the current status of a PoliticalPromise using rule-based evidence analysis.
        Returns a complete assessment dictionary.
        """
        now = datetime.now(timezone.utc)
        now_iso = now.isoformat()

        # Retrieve linked evidence candidates (Phase 3.10)
        evidence_links = self.db.query(PromiseEvidenceLink).filter(
            PromiseEvidenceLink.promise_id == promise.promise_id
        ).all()

        # Retrieve linked historical/budget scheme candidates (Phase 3.8)
        scheme_links = self.db.query(PromiseSchemeLink).filter(
            PromiseSchemeLink.promise_id == promise.promise_id
        ).all()

        evidence_ids = []
        source_tiers_map: Dict[int, int] = {}
        highest_evidence_score = 0.0
        has_go_document = False
        has_budget_allocation = False
        has_press_release = False
        has_dispute = False

        for link in evidence_links:
            score = link.relevance_score or link.similarity_score or 0.0
            if score > highest_evidence_score:
                highest_evidence_score = score

            ev = link.evidence
            if ev:
                evidence_ids.append(ev.id)
                supp = ev.supporting_values or {}
                tier = supp.get("source_tier", 1)
                source_tiers_map[tier] = source_tiers_map.get(tier, 0) + 1

                src_type = str(supp.get("source_type", "")).lower()
                content_lower = (ev.content or "").lower()

                if "disputed" in content_lower or "contradict" in content_lower:
                    has_dispute = True

                if "government order" in src_type or "g.o." in content_lower or "go ms" in content_lower:
                    has_go_document = True

                if "budget" in src_type or "demand no" in content_lower or "allocation" in content_lower:
                    has_budget_allocation = True

                if "press release" in src_type or "dipr" in src_type or "announced" in content_lower:
                    has_press_release = True

        # Deterministic Status Decision Logic
        if promise.is_ambiguous and not evidence_ids:
            status = PromiseStatus.UNCLEAR
            confidence = 0.4
            explanation = "Promise text is ambiguous and no evidence was retrieved."
        elif not evidence_links:
            # CRITICAL RULE: No evidence -> no_evidence_found (NEVER "not implemented")
            status = PromiseStatus.NO_EVIDENCE_FOUND
            confidence = 0.5
            explanation = (
                "No verifiable government evidence (GOs, budget demands, department pages) "
                "was found for this promise. Note: Absence of evidence is not proof of non-implementation."
            )
        elif has_dispute:
            status = PromiseStatus.DISPUTED
            confidence = 0.6
            explanation = "Disputed status assigned due to conflicting official reports or disputed implementation claims."
        elif highest_evidence_score < 0.2:
            status = PromiseStatus.UNCLEAR
            confidence = 0.45
            explanation = "Retrieved evidence candidate scores are below the relevance threshold, preventing definitive classification."
        elif has_go_document and has_budget_allocation:
            if highest_evidence_score >= 0.8:
                status = PromiseStatus.IMPLEMENTED
                confidence = 0.95
                explanation = "Verifiable government evidence (Government Order and budget allocation) confirms implementation of the promise."
            else:
                status = PromiseStatus.PARTIALLY_IMPLEMENTED
                confidence = 0.85
                explanation = "Government Order and budget allocation verified, but full numeric/monetary targets remain ongoing."
        elif has_go_document:
            status = PromiseStatus.POLICY_ACTION
            confidence = 0.85
            explanation = "Official Government Order (G.O.) or policy note issued sanctioning the framework for this promise."
        elif has_budget_allocation:
            status = PromiseStatus.PARTIALLY_IMPLEMENTED
            confidence = 0.80
            explanation = "Budget allocation verified in official state budget demands."
        elif has_press_release:
            status = PromiseStatus.ANNOUNCED
            confidence = 0.70
            explanation = "Official government announcement or press release verified, but formal Government Order or budget allocation is pending."
        else:
            if highest_evidence_score >= 0.5:
                status = PromiseStatus.ANNOUNCED
                confidence = 0.65
                explanation = "Related government documentation found, confirming announcement status."
            else:
                status = PromiseStatus.UNCLEAR
                confidence = 0.50
                explanation = "Evidence found has moderate alignment, but clear policy action or GO could not be confirmed."

        assessment_payload = {
            "promise_id": promise.promise_id,
            "status": status.value if hasattr(status, "value") else str(status),
            "confidence": confidence,
            "explanation": explanation,
            "evidence_ids": evidence_ids,
            "source_tiers": source_tiers_map,
            "assessment_date": now_iso,
            "methodology": evaluator_id
        }

        if persist:
            self._persist_assessment(promise.promise_id, status, confidence, explanation, evaluator_id, assessment_payload, now)

        return assessment_payload

    def _persist_assessment(
        self,
        promise_id: str,
        status: PromiseStatus,
        confidence: float,
        explanation: str,
        evaluator_id: str,
        payload: Dict[str, Any],
        now: datetime
    ):
        # Fetch current active assessment
        current_assessment = self.db.query(PromiseAssessment).filter(
            PromiseAssessment.promise_id == promise_id,
            PromiseAssessment.is_current == True
        ).first()

        previous_status_str = None
        if current_assessment:
            previous_status_str = current_assessment.status.value if hasattr(current_assessment.status, "value") else str(current_assessment.status)

            # Check if status has changed
            if previous_status_str == (status.value if hasattr(status, "value") else str(status)):
                # Update existing current assessment
                current_assessment.confidence_score = confidence
                current_assessment.rationale = explanation
                current_assessment.assessed_by = evaluator_id
                current_assessment.assessment_date = now
                current_assessment.assessment_metadata = payload
                self.db.commit()
                return

            # Status changed: mark previous as not current
            current_assessment.is_current = False

        # Create new current assessment
        new_assessment = PromiseAssessment(
            promise_id=promise_id,
            status=status,
            confidence_score=confidence,
            rationale=explanation,
            assessed_by=evaluator_id,
            assessment_date=now,
            is_current=True,
            assessment_metadata=payload
        )
        self.db.add(new_assessment)
        self.db.commit()

        # Audit history log entry
        new_status_str = status.value if hasattr(status, "value") else str(status)
        history_entry = PromiseAssessmentHistory(
            promise_id=promise_id,
            assessment_id=new_assessment.id,
            previous_status=previous_status_str,
            new_status=new_status_str,
            change_reason=f"Status updated from {previous_status_str} to {new_status_str} via {evaluator_id}",
            changed_by=evaluator_id,
            changed_at=now
        )
        self.db.add(history_entry)
        self.db.commit()

    def evaluate_all_promises(self, evaluator_id: str = METHODOLOGY_ID) -> Dict[str, Any]:
        """
        Evaluates status for all political promises in the database.
        """
        promises = self.db.query(PoliticalPromise).all()
        summary = {
            "total_promises": len(promises),
            "status_counts": {}
        }

        for p in promises:
            res = self.evaluate_promise(p, persist=True, evaluator_id=evaluator_id)
            st = res["status"]
            summary["status_counts"][st] = summary["status_counts"].get(st, 0) + 1

        return summary
