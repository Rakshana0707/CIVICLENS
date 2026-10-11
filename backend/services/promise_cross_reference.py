"""
Phase 6 — Political Promise Cross-Reference and Performance Indicators Service.

Connects elected representatives and their party manifesto promises (Phase 3)
with government schemes (Phase 2), statutory evidence, local constituency works,
and socioeconomic development indicators.

Enforces:
1. Strict reuse of Phase 3 PoliticalPromise records (no new promise creation).
2. 6-tier fulfillment evidence stages (PROMISE_IDENTIFIED to OUTCOME_INDICATOR_OBSERVED).
3. Non-inference: Scheme existence != Promise fulfillment.
4. Non-inference: Project completion != Broad developmental outcome.
5. Conflicting date detection (e.g. pre-existing schemes claimed as new election promises).
"""

import logging
from typing import Dict, Any, List, Optional, Tuple, Set
from datetime import datetime, timezone
from sqlalchemy.orm import Session

from backend.models.representative import (
    Representative,
    RepresentativeTerm,
    ConstituencyWork,
    DevelopmentIndicator,
    PromisePerformanceLink,
    PromiseEvidenceStage
)
from backend.models.promise import PoliticalPromise
from backend.models.common import Evidence

logger = logging.getLogger("civiclens.phase6.promises")
logging.basicConfig(level=logging.INFO)


class PromiseNotFoundError(Exception):
    """Raised when attempting to link a promise that does not exist in Phase 3 database."""
    pass


class RepresentativeNotFoundError(Exception):
    """Raised when representative cannot be resolved."""
    pass


class PromiseCrossReferenceService:
    """
    Core service linking representatives to party manifesto promises and empirical delivery.
    """

    def __init__(self, db: Optional[Session] = None):
        self.db = db

    def link_promise_to_performance(
        self,
        link_id: str,
        representative_id: str,
        promise_id: str,
        scheme_id: Optional[str] = None,
        evidence_id: Optional[int] = None,
        work_id: Optional[str] = None,
        indicator_id: Optional[str] = None,
        matching_method: str = "PARTY_MANIFESTO_DIRECT",
        match_confidence: float = 1.0,
        promise_year: Optional[int] = None,
        action_year: Optional[int] = None,
        evidence_summary: Optional[str] = None
    ) -> PromisePerformanceLink:
        """
        Creates a verified link between a representative and a Phase 3 manifesto promise.
        Validates presence in Phase 3, checks temporal alignment, and classifies evidence stage.
        """
        if self.db:
            # 1. Verify representative exists
            rep = self.db.query(Representative).filter(Representative.representative_id == representative_id).first()
            if not rep:
                raise RepresentativeNotFoundError(f"Representative '{representative_id}' not found.")

            # 2. Verify promise exists in Phase 3 (Strict Non-Creation Rule)
            prom = self.db.query(PoliticalPromise).filter(PoliticalPromise.promise_id == promise_id).first()
            if not prom:
                raise PromiseNotFoundError(
                    f"Promise '{promise_id}' does not exist in Phase 3 PoliticalPromise database. "
                    f"Phase 6 does not create promise records if Phase 3 does not contain them."
                )
            party_id = rep.party_id
            election_id = rep.election_id
        else:
            party_id = "PARTY-DEFAULT"
            election_id = "ELECTION-DEFAULT"

        # 3. Temporal Validation (Conflicting Dates Detection)
        has_conflicting_dates = False
        if promise_year and action_year:
            if action_year < promise_year:
                has_conflicting_dates = True
                logger.warning(
                    f"TEMPORAL CONFLICT: Action year {action_year} predates promise manifesto year {promise_year} for link {link_id}."
                )

        # 4. Determine Evidence Stage
        evidence_stage = PromiseEvidenceStage.PROMISE_IDENTIFIED
        if has_conflicting_dates:
            evidence_stage = PromiseEvidenceStage.INSUFFICIENT_EVIDENCE
        elif indicator_id:
            evidence_stage = PromiseEvidenceStage.OUTCOME_INDICATOR_OBSERVED
        elif work_id:
            evidence_stage = PromiseEvidenceStage.PROJECT_WORK_RECORDED
        elif evidence_id:
            evidence_stage = PromiseEvidenceStage.POLICY_ACTION_DOCUMENTED
        elif scheme_id:
            evidence_stage = PromiseEvidenceStage.RELEVANT_SCHEME_IDENTIFIED

        link = None
        if self.db:
            link = self.db.query(PromisePerformanceLink).filter(PromisePerformanceLink.link_id == link_id).first()

        if link:
            link.representative_id = representative_id
            link.promise_id = promise_id
            link.party_id = party_id
            link.election_id = election_id
            link.scheme_id = scheme_id
            link.evidence_id = evidence_id
            link.work_id = work_id
            link.indicator_id = indicator_id
            link.evidence_stage = evidence_stage
            link.matching_method = matching_method
            link.match_confidence = match_confidence
            link.has_conflicting_dates = has_conflicting_dates
            link.evidence_summary = evidence_summary
        else:
            link = PromisePerformanceLink(
                link_id=link_id,
                representative_id=representative_id,
                promise_id=promise_id,
                party_id=party_id,
                election_id=election_id,
                scheme_id=scheme_id,
                evidence_id=evidence_id,
                work_id=work_id,
                indicator_id=indicator_id,
                evidence_stage=evidence_stage,
                matching_method=matching_method,
                match_confidence=match_confidence,
                has_conflicting_dates=has_conflicting_dates,
                evidence_summary=evidence_summary
            )
            if self.db:
                self.db.add(link)

        if self.db:
            self.db.commit()
            self.db.refresh(link)

        logger.info(f"Recorded promise performance link {link_id} ({representative_id} -> {promise_id}, Stage: {evidence_stage})")
        return link

    def get_representative_promise_scorecard(
        self,
        representative_id: str,
        links_cache: Optional[List[PromisePerformanceLink]] = None
    ) -> Dict[str, Any]:
        """
        Generates an aggregated promise cross-reference scorecard for a representative.
        Surfaces stage distributions, evidence citations, and mandatory disclaimers.
        """
        links: List[PromisePerformanceLink] = []
        if links_cache is not None:
            links = [l for l in links_cache if l.representative_id == representative_id]
        elif self.db:
            links = self.db.query(PromisePerformanceLink).filter(
                PromisePerformanceLink.representative_id == representative_id
            ).all()

        total_links = len(links)
        stage_counts = {s.value: 0 for s in PromiseEvidenceStage}
        conflicting_dates_count = 0

        linked_schemes = set()
        linked_works = set()
        linked_indicators = set()
        linked_evidences = set()

        for l in links:
            stage_counts[l.evidence_stage] = stage_counts.get(l.evidence_stage, 0) + 1
            if l.has_conflicting_dates:
                conflicting_dates_count += 1
            if l.scheme_id:
                linked_schemes.add(l.scheme_id)
            if l.work_id:
                linked_works.add(l.work_id)
            if l.indicator_id:
                linked_indicators.add(l.indicator_id)
            if l.evidence_id:
                linked_evidences.add(l.evidence_id)

        return {
            "representative_id": representative_id,
            "total_manifesto_promises_linked": total_links,
            "stage_breakdown": stage_counts,
            "network_coverage": {
                "unique_schemes_count": len(linked_schemes),
                "unique_constituency_works_count": len(linked_works),
                "unique_development_indicators_count": len(linked_indicators),
                "unique_official_evidences_count": len(linked_evidences)
            },
            "data_quality": {
                "conflicting_dates_count": conflicting_dates_count,
                "insufficient_evidence_count": stage_counts.get(PromiseEvidenceStage.INSUFFICIENT_EVIDENCE, 0)
            },
            "methodology_disclaimers": {
                "scheme_disclaimer": "A scheme's existence does not prove that a particular political promise was fulfilled.",
                "work_disclaimer": "A constituency project's completion does not automatically prove the achievement of a broader development outcome.",
                "evidence_disclaimer": "Fulfillment status requires independent official proof beyond budget announcements or party claims."
            }
        }
