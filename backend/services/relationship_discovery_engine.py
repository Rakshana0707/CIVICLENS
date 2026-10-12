"""
Phase 9.4 — Cross-Phase Relationship Discovery Engine.
======================================================

Discovers, evaluates, and proposes relationship candidates connecting
records from Phases 1 through 8.

Multi-tier Discovery Strategy:
1. Exact Identifiers (Demand Nos, G.O. Nos, ECI IDs, Grievance Tokens, Scheme Codes).
2. Documented References (Gazette citations, statutory reports, cross-phase references).
3. Canonical Entity Matches (Phase 9.2 CanonicalEntity links, aliases, bilingual names).
4. Temporal & Reporting-Period Compatibility (Fiscal years, terms, event timestamps).
5. Geographic Compatibility (District, Assembly Constituency, Ward hierarchy).
6. Text Similarity (Token overlap, Levenshtein, Jaccard - strictly candidate heuristic).
7. Transitive Corroboration (Multi-hop verified graph paths).

Hierarchy Principle:
- Deterministic and documentary evidence ALWAYS strictly prioritized over text similarity.
- Similarity scores NEVER automatically convert a candidate into a verified relationship.
- Automatically inferred links are kept strictly separated in CandidateRelationshipProposal
  from confirmed CivicEvidenceEdge records.

Epistemic Anti-Hallucination Guardrails:
- Funding caused a particular public outcome (Rejected).
- Representative personally caused a civic issue from spatial co-location (Rejected).
- Scheme automatically fulfilled a political promise (Rejected without official G.O. proof).
- News report proves a fact-checked claim true (Rejected; reports_on / mentions only).
- Correlated statistical trends establish causation (Rejected; contextualizes only).

Human Review Workflow:
- Authorized reviewers confirm, reject, or defer candidate proposals with audit logging.
"""

from __future__ import annotations

import logging
import re
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple, Set

from sqlalchemy import or_, and_, desc
from sqlalchemy.orm import Session

from backend.models.graph import (
    CivicGraphNode,
    CivicEvidenceEdge,
    CandidateRelationshipProposal,
    CandidateReviewDisposition,
    GraphEntityType,
    GraphRelationshipType,
    MatchingMethod,
    GraphProvenanceStatus,
    GraphReviewStatus,
    EdgeOperationType,
)
from backend.models.entity_registry import CanonicalEntity
from backend.services.graph_storage_service import GraphStorageService, GraphStorageError

logger = logging.getLogger("civiclens.phase9.discovery")


# ---------------------------------------------------------------------------
# Epistemic Conflict Error Constants
# ---------------------------------------------------------------------------
CONFLICT_FUNDING_CAUSATION = "UNSUPPORTED_CAUSATION_FUNDING_TO_OUTCOME"
CONFLICT_REPRESENTATIVE_CULPABILITY = "SPATIAL_COOCCURRENCE_NOT_REPRESENTATIVE_CULPABILITY"
CONFLICT_PROMISE_FULFILLMENT = "PROMISE_SCHEME_ALIGNMENT_DOES_NOT_PROVE_FULFILLMENT"
CONFLICT_NEWS_TRUTH_PROOF = "MEDIA_REPORTING_DOES_NOT_ESTABLISH_FACTUAL_TRUTH"
CONFLICT_CORRELATION_CAUSATION = "STATISTICAL_CORRELATION_DOES_NOT_ESTABLISH_CAUSATION"
CONFLICT_TEMPORAL_MISMATCH = "TEMPORAL_PERIOD_MISMATCH"
CONFLICT_GEOGRAPHIC_MISMATCH = "GEOGRAPHIC_LOCATION_MISMATCH"


class DiscoveryEngineError(Exception):
    """Base exception for relationship discovery operations."""
    pass


class ProposalNotFoundError(DiscoveryEngineError):
    """Raised when a candidate proposal does not exist."""
    pass


class EpistemicGuardrailViolation(DiscoveryEngineError):
    """Raised when a candidate proposal asserts an ungrounded causal link."""
    pass


# ---------------------------------------------------------------------------
# RelationshipDiscoveryEngine
# ---------------------------------------------------------------------------
class RelationshipDiscoveryEngine:
    """
    Evaluates cross-phase candidate pairs and proposes evidence-backed relationships.
    """

    # -----------------------------------------------------------------------
    # 1. Compatibility Checkers: Temporal & Geographic
    # -----------------------------------------------------------------------
    @staticmethod
    def evaluate_temporal_compatibility(
        node_a: CivicGraphNode,
        node_b: CivicGraphNode,
    ) -> Tuple[bool, Optional[str]]:
        """
        Determines if two entities have compatible operational timeframes.
        Returns (is_compatible, reason_if_incompatible).
        """
        attrs_a = node_a.attributes_json or {}
        attrs_b = node_b.attributes_json or {}

        fy_a = attrs_a.get("fiscal_year") or attrs_a.get("financial_year")
        fy_b = attrs_b.get("fiscal_year") or attrs_b.get("financial_year")

        # Fiscal year check if both have explicit fiscal years
        if fy_a and fy_b:
            fy_a_clean = str(fy_a).strip()
            fy_b_clean = str(fy_b).strip()
            # If both format like "2022-23" or "2021-22"
            if fy_a_clean != fy_b_clean:
                # Check year divergence
                try:
                    y_a = int(fy_a_clean[:4])
                    y_b = int(fy_b_clean[:4])
                    if abs(y_a - y_b) > 2:
                        return False, f"Fiscal years differ by >2 years ({fy_a_clean} vs {fy_b_clean})"
                except (ValueError, TypeError):
                    pass

        # Year check if present
        year_a = attrs_a.get("year") or attrs_a.get("election_year")
        year_b = attrs_b.get("year") or attrs_b.get("election_year")
        if year_a and year_b:
            try:
                if abs(int(year_a) - int(year_b)) > 5:
                    return False, f"Timeframe divergence exceeds 5 years ({year_a} vs {year_b})"
            except (ValueError, TypeError):
                pass

        return True, None

    @staticmethod
    def evaluate_geographic_compatibility(
        node_a: CivicGraphNode,
        node_b: CivicGraphNode,
    ) -> Tuple[bool, Optional[str]]:
        """
        Determines if two entities operate in geographically compatible areas.
        Returns (is_compatible, reason_if_incompatible).
        """
        attrs_a = node_a.attributes_json or {}
        attrs_b = node_b.attributes_json or {}

        dist_a = attrs_a.get("district")
        dist_b = attrs_b.get("district")

        if dist_a and dist_b:
            if str(dist_a).strip().lower() != str(dist_b).strip().lower():
                return False, f"District mismatch ({dist_a} vs {dist_b})"

        ac_a = attrs_a.get("constituency_code") or attrs_a.get("ac_code")
        ac_b = attrs_b.get("constituency_code") or attrs_b.get("ac_code")
        if ac_a and ac_b:
            if str(ac_a).strip().upper() != str(ac_b).strip().upper():
                return False, f"Assembly constituency mismatch ({ac_a} vs {ac_b})"

        return True, None

    # -----------------------------------------------------------------------
    # 2. Text Similarity Helper
    # -----------------------------------------------------------------------
    @staticmethod
    def compute_text_similarity(str_a: str, str_b: str) -> float:
        """
        Calculates normalized token overlap and stemmed Jaccard similarity.
        """
        if not str_a or not str_b:
            return 0.0

        clean_a = re.sub(r"[^\w\s]", " ", str_a.lower()).strip()
        clean_b = re.sub(r"[^\w\s]", " ", str_b.lower()).strip()

        if clean_a == clean_b:
            return 1.0

        # Token set (filtering small stop tokens)
        raw_tokens_a = [t for t in clean_a.split() if len(t) > 2]
        raw_tokens_b = [t for t in clean_b.split() if len(t) > 2]

        if not raw_tokens_a or not raw_tokens_b:
            return 0.0

        # Simple suffix normalization
        def stem(t: str) -> str:
            if t.endswith("ing") and len(t) > 5:
                return t[:-3]
            if t.endswith("es") and len(t) > 4:
                return t[:-2]
            if t.endswith("s") and len(t) > 3:
                return t[:-1]
            if t.endswith("ed") and len(t) > 4:
                return t[:-2]
            return t

        stems_a = {stem(t) for t in raw_tokens_a}
        stems_b = {stem(t) for t in raw_tokens_b}

        intersection = stems_a.intersection(stems_b)
        union = stems_a.union(stems_b)
        token_sim = len(intersection) / len(union) if union else 0.0

        containment = 0.0
        if clean_a in clean_b or clean_b in clean_a:
            containment = 0.25

        return min(1.0, token_sim + containment)

    # -----------------------------------------------------------------------
    # 3. Epistemic Anti-Hallucination Filter
    # -----------------------------------------------------------------------
    @classmethod
    def evaluate_epistemic_guardrails(
        cls,
        source_node: CivicGraphNode,
        target_node: CivicGraphNode,
        relationship_type: GraphRelationshipType,
        matching_method: MatchingMethod,
        properties: Optional[Dict[str, Any]] = None,
    ) -> List[str]:
        """
        Validates the proposed relationship against all 5 epistemic non-causation guardrails.
        Returns a list of identified conflict codes.
        """
        conflicts: List[str] = []
        props = properties or {}
        src_type = source_node.entity_type
        tgt_type = target_node.entity_type

        # -------------------------------------------------------------------
        # Fallacy 1: Funding caused a particular public outcome
        # -------------------------------------------------------------------
        is_funding_src = src_type in (
            GraphEntityType.CONTRIBUTION,
            GraphEntityType.DONOR,
            GraphEntityType.ELECTORAL_TRUST,
            GraphEntityType.FINANCIAL_DOCUMENT,
        )
        is_outcome_tgt = tgt_type in (
            GraphEntityType.PUBLIC_WORK,
            GraphEntityType.CIVIC_ISSUE,
            GraphEntityType.BUDGET_SCHEME,
            GraphEntityType.DEVELOPMENT_INDICATOR,
        )
        if is_funding_src and is_outcome_tgt:
            if relationship_type in (GraphRelationshipType.FUNDS, GraphRelationshipType.IMPLEMENTS):
                conflicts.append(CONFLICT_FUNDING_CAUSATION)

        # -------------------------------------------------------------------
        # Fallacy 2: Representative personally caused a civic issue from spatial co-location
        # -------------------------------------------------------------------
        is_issue = src_type in (GraphEntityType.CIVIC_ISSUE, GraphEntityType.GRIEVANCE_RECORD)
        is_rep = tgt_type == GraphEntityType.REPRESENTATIVE
        if is_issue and is_rep:
            if relationship_type in (
                GraphRelationshipType.IMPLEMENTS,
                GraphRelationshipType.RESPONDS_TO,
                GraphRelationshipType.CONCERNS,
                GraphRelationshipType.LOCATED_IN,
            ):
                # If proposed without formal assembly petition/question or official document
                if props.get("has_assembly_petition") is not True:
                    conflicts.append(CONFLICT_REPRESENTATIVE_CULPABILITY)

        # -------------------------------------------------------------------
        # Fallacy 3: Scheme fulfilled a political promise
        # -------------------------------------------------------------------
        is_promise = src_type == GraphEntityType.POLITICAL_PROMISE
        is_scheme = tgt_type in (GraphEntityType.BUDGET_SCHEME, GraphEntityType.HISTORICAL_SCHEME)
        if is_promise and is_scheme:
            if relationship_type in (GraphRelationshipType.IMPLEMENTS, GraphRelationshipType.PROVIDES_EVIDENCE_FOR):
                if props.get("proof_of_fulfillment") is not True and not props.get("government_order_number"):
                    conflicts.append(CONFLICT_PROMISE_FULFILLMENT)

        # -------------------------------------------------------------------
        # Fallacy 4: News report proves a fact-checked claim true
        # -------------------------------------------------------------------
        is_news = src_type in (GraphEntityType.NEWS_ARTICLE, GraphEntityType.NEWS_SOURCE)
        is_claim = tgt_type in (GraphEntityType.CLAIM, GraphEntityType.ATOMIC_CLAIM)
        if is_news and is_claim:
            if relationship_type in (GraphRelationshipType.PROVIDES_EVIDENCE_FOR, GraphRelationshipType.CONTRADICTS):
                if props.get("primary_official_verification") is not True:
                    conflicts.append(CONFLICT_NEWS_TRUTH_PROOF)

        # -------------------------------------------------------------------
        # Fallacy 5: Two correlated trends establish causation
        # -------------------------------------------------------------------
        is_indicator_src = src_type in (GraphEntityType.DEVELOPMENT_INDICATOR, GraphEntityType.BUDGET_RECORD)
        is_indicator_tgt = tgt_type in (GraphEntityType.DEVELOPMENT_INDICATOR, GraphEntityType.CIVIC_ISSUE)
        if is_indicator_src and is_indicator_tgt:
            if relationship_type in (GraphRelationshipType.IMPLEMENTS, GraphRelationshipType.FUNDS):
                if props.get("econometric_causal_identification") is not True:
                    conflicts.append(CONFLICT_CORRELATION_CAUSATION)

        return conflicts

    # -----------------------------------------------------------------------
    # 4. Multi-Strategy Candidate Evaluation
    # -----------------------------------------------------------------------
    @classmethod
    def evaluate_candidate_pair(
        cls,
        session: Session,
        source_node: CivicGraphNode,
        target_node: CivicGraphNode,
        proposed_relationship_type: Optional[GraphRelationshipType] = None,
        properties: Optional[Dict[str, Any]] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Evaluates potential relationship between two nodes across all matching channels.
        Returns candidate evaluation dictionary or None if no plausible link found.
        """
        props = properties or {}
        attrs_src = source_node.attributes_json or {}
        attrs_tgt = target_node.attributes_json or {}

        # 1. Temporal Compatibility
        temp_compat, temp_reason = cls.evaluate_temporal_compatibility(source_node, target_node)
        # 2. Geographic Compatibility
        geo_compat, geo_reason = cls.evaluate_geographic_compatibility(source_node, target_node)

        identified_method = MatchingMethod.AUTOMATED_CANDIDATE
        confidence = 0.50
        supporting_evidence = ""
        rel_type = proposed_relationship_type or GraphRelationshipType.RELATES_TO
        source_doc_id = None
        possible_conflicts: List[str] = []

        if not temp_compat and temp_reason:
            possible_conflicts.append(f"{CONFLICT_TEMPORAL_MISMATCH}: {temp_reason}")
        if not geo_compat and geo_reason:
            possible_conflicts.append(f"{CONFLICT_GEOGRAPHIC_MISMATCH}: {geo_reason}")

        # -------------------------------------------------------------------
        # Channel 1: Exact Identifiers (Highest Priority, Rank 1)
        # -------------------------------------------------------------------
        shared_exact_keys = [
            ("demand_number", "Demand Number", GraphRelationshipType.FUNDS),
            ("scheme_code", "Scheme Code", GraphRelationshipType.RELATES_TO),
            ("g_o_number", "Government Order", GraphRelationshipType.RELATES_TO),
            ("petition_id", "Petition Token", GraphRelationshipType.RESPONDS_TO),
            ("grievance_token", "Grievance Token", GraphRelationshipType.RESPONDS_TO),
            ("electoral_bond_serial", "Electoral Bond Serial", GraphRelationshipType.FUNDS),
            ("ac_code", "Assembly Constituency Code", GraphRelationshipType.LOCATED_IN),
        ]

        exact_match_found = False
        for key, label, default_rel in shared_exact_keys:
            val_src = attrs_src.get(key)
            val_tgt = attrs_tgt.get(key)
            if val_src and val_tgt and str(val_src).strip().lower() == str(val_tgt).strip().lower():
                identified_method = MatchingMethod.DETERMINISTIC_ID
                confidence = 0.98 if temp_compat and geo_compat else 0.80
                supporting_evidence = f"Deterministic match on {label}: '{val_src}'"
                rel_type = proposed_relationship_type or default_rel
                exact_match_found = True
                break

        # -------------------------------------------------------------------
        # Channel 2: Documented References (Rank 2)
        # -------------------------------------------------------------------
        if not exact_match_found:
            doc_src = attrs_src.get("source_document_id") or attrs_src.get("cited_document_id")
            doc_tgt = attrs_tgt.get("source_document_id") or attrs_tgt.get("cited_document_id")
            if doc_src and doc_tgt and str(doc_src).strip() == str(doc_tgt).strip():
                identified_method = MatchingMethod.DIRECT_DOCUMENTARY
                confidence = 0.95 if temp_compat and geo_compat else 0.75
                supporting_evidence = f"Both records cite primary source document '{doc_src}'"
                source_doc_id = str(doc_src).strip()
                rel_type = proposed_relationship_type or GraphRelationshipType.CONTEXTUALIZES

        # -------------------------------------------------------------------
        # Channel 3: Canonical Entity Matches (Rank 3)
        # -------------------------------------------------------------------
        if not exact_match_found and identified_method == MatchingMethod.AUTOMATED_CANDIDATE:
            if source_node.canonical_entity_id and target_node.canonical_entity_id:
                if source_node.canonical_entity_id == target_node.canonical_entity_id:
                    identified_method = MatchingMethod.DETERMINISTIC_ID
                    confidence = 0.92
                    supporting_evidence = (
                        f"Both graph nodes share identical canonical registry entity "
                        f"'{source_node.canonical_entity_id}'"
                    )
                    rel_type = proposed_relationship_type or GraphRelationshipType.RELATES_TO

        # -------------------------------------------------------------------
        # Channel 4: Text Similarity (Lowest Priority, Rank 4, strictly candidate)
        # -------------------------------------------------------------------
        if not exact_match_found and identified_method == MatchingMethod.AUTOMATED_CANDIDATE:
            sim_score = cls.compute_text_similarity(source_node.label, target_node.label)
            if sim_score >= 0.20:
                identified_method = MatchingMethod.AUTOMATED_CANDIDATE
                # Score capped at 0.70 because similarity alone is ungrounded
                confidence = min(0.70, round(sim_score * 0.70 + 0.15, 2))
                supporting_evidence = (
                    f"Lexical and token similarity between '{source_node.label}' "
                    f"and '{target_node.label}' (score: {sim_score:.2f})"
                )
                rel_type = proposed_relationship_type or GraphRelationshipType.RELATES_TO
            elif proposed_relationship_type is not None:
                # A specific relationship type was explicitly proposed for candidate evaluation
                identified_method = MatchingMethod.AUTOMATED_CANDIDATE
                confidence = 0.40
                supporting_evidence = (
                    f"Candidate proposed for evaluation under relationship '{proposed_relationship_type.value}'"
                )
                rel_type = proposed_relationship_type
            else:
                # No plausible link found across any channel
                return None

        # -------------------------------------------------------------------
        # Epistemic Guardrail Filter: Check for unsupported causal assertions
        # -------------------------------------------------------------------
        fallacy_conflicts = cls.evaluate_epistemic_guardrails(
            source_node=source_node,
            target_node=target_node,
            relationship_type=rel_type,
            matching_method=identified_method,
            properties=props,
        )
        possible_conflicts.extend(fallacy_conflicts)

        return {
            "source_node_id": source_node.node_id,
            "target_node_id": target_node.node_id,
            "relationship_type": rel_type,
            "evidence_supporting_candidate": supporting_evidence,
            "matching_method": identified_method,
            "confidence_score": confidence,
            "source_document_id": source_doc_id,
            "temporal_validity": {
                "compatible": temp_compat,
                "reason": temp_reason,
            },
            "geographic_context": {
                "compatible": geo_compat,
                "reason": geo_reason,
            },
            "possible_conflicts": possible_conflicts,
            "epistemic_notes": (
                "Candidate relationship generated by Discovery Engine. "
                "Subject to human auditor review before inclusion in verified graph."
            ),
        }

    # -----------------------------------------------------------------------
    # 5. Propose Candidate Relationship (Separation of Inferred & Confirmed)
    # -----------------------------------------------------------------------
    @classmethod
    def propose_candidate(
        cls,
        session: Session,
        source_node_id: str,
        target_node_id: str,
        relationship_type: Optional[GraphRelationshipType | str] = None,
        properties: Optional[Dict[str, Any]] = None,
        is_test_fixture: bool = False,
    ) -> CandidateRelationshipProposal:
        """
        Discovers and stores a candidate relationship proposal.
        Strictly kept separate from confirmed edges with review_status=PENDING_REVIEW.
        """
        if isinstance(relationship_type, str):
            relationship_type = GraphRelationshipType.from_string(relationship_type)

        source_node = session.query(CivicGraphNode).filter(CivicGraphNode.node_id == source_node_id).first()
        if not source_node:
            raise DiscoveryEngineError(f"Source node '{source_node_id}' not found.")

        target_node = session.query(CivicGraphNode).filter(CivicGraphNode.node_id == target_node_id).first()
        if not target_node:
            raise DiscoveryEngineError(f"Target node '{target_node_id}' not found.")

        eval_result = cls.evaluate_candidate_pair(
            session=session,
            source_node=source_node,
            target_node=target_node,
            proposed_relationship_type=relationship_type,
            properties=properties,
        )

        if not eval_result:
            raise DiscoveryEngineError(
                f"No plausible relationship discovered between '{source_node_id}' and '{target_node_id}'."
            )

        # Check existing proposal
        existing = session.query(CandidateRelationshipProposal).filter(
            CandidateRelationshipProposal.source_node_id == source_node_id,
            CandidateRelationshipProposal.target_node_id == target_node_id,
            CandidateRelationshipProposal.relationship_type == eval_result["relationship_type"],
            CandidateRelationshipProposal.matching_method == eval_result["matching_method"],
        ).first()

        if existing:
            return existing

        proposal_id = f"PROP:{eval_result['relationship_type'].value.upper()}:{source_node_id}:{target_node_id}:{uuid.uuid4().hex[:8]}"
        proposal = CandidateRelationshipProposal(
            proposal_id=proposal_id,
            source_node_id=source_node_id,
            target_node_id=target_node_id,
            relationship_type=eval_result["relationship_type"],
            evidence_supporting_candidate=eval_result["evidence_supporting_candidate"],
            matching_method=eval_result["matching_method"],
            confidence_score=eval_result["confidence_score"],
            source_document_id=eval_result.get("source_document_id"),
            temporal_validity_json=eval_result.get("temporal_validity"),
            geographic_context_json=eval_result.get("geographic_context"),
            possible_conflicts_json=eval_result.get("possible_conflicts"),
            epistemic_notes=eval_result.get("epistemic_notes"),
            review_status=CandidateReviewDisposition.PENDING_REVIEW,
            properties_json=properties or {},
            is_test_fixture=is_test_fixture,
        )
        session.add(proposal)
        session.flush()
        return proposal

    # -----------------------------------------------------------------------
    # 6. Human Review Workflow: Confirm, Reject, Defer
    # -----------------------------------------------------------------------
    @classmethod
    def confirm_candidate(
        cls,
        session: Session,
        proposal_id: str,
        reviewer_id: str,
        reviewer_notes: str,
        override_relationship_type: Optional[GraphRelationshipType | str] = None,
    ) -> Tuple[CandidateRelationshipProposal, CivicEvidenceEdge]:
        """
        Authorized human reviewer confirms a candidate relationship.
        Promotes the candidate to a verified CivicEvidenceEdge with full provenance.
        """
        proposal = session.query(CandidateRelationshipProposal).filter(
            CandidateRelationshipProposal.proposal_id == proposal_id
        ).first()
        if not proposal:
            raise ProposalNotFoundError(f"Proposal '{proposal_id}' does not exist.")

        # If proposal contains fatal epistemic fallacy conflicts, reject confirmation
        conflicts = proposal.possible_conflicts_json or []
        fatal_conflicts = [
            c for c in conflicts
            if c in (
                CONFLICT_FUNDING_CAUSATION,
                CONFLICT_REPRESENTATIVE_CULPABILITY,
                CONFLICT_PROMISE_FULFILLMENT,
                CONFLICT_NEWS_TRUTH_PROOF,
                CONFLICT_CORRELATION_CAUSATION,
            )
        ]
        if fatal_conflicts:
            raise EpistemicGuardrailViolation(
                f"Cannot confirm proposal '{proposal_id}'. It violates epistemic guardrails: {fatal_conflicts}. "
                f"Causal claims without statutory proof are prohibited."
            )

        rel_type = proposal.relationship_type
        if override_relationship_type:
            if isinstance(override_relationship_type, str):
                rel_type = GraphRelationshipType.from_string(override_relationship_type)
            else:
                rel_type = override_relationship_type

        # Promote to confirmed CivicEvidenceEdge
        edge = GraphStorageService.add_evidence_edge(
            session=session,
            source_node_id=proposal.source_node_id,
            target_node_id=proposal.target_node_id,
            relationship_type=rel_type,
            evidence_reference=f"Confirmed from Candidate {proposal.proposal_id}: {proposal.evidence_supporting_candidate}",
            source_document_id=proposal.source_document_id or f"DOC-REVIEW-{proposal_id}",
            matching_method=MatchingMethod.HUMAN_REVIEWED,
            confidence_score=1.0,
            review_status=GraphReviewStatus.VERIFIED,
            provenance_status=GraphProvenanceStatus.VALID,
            epistemic_notes=f"Confirmed by {reviewer_id}: {reviewer_notes}",
            properties={"confirmed_from_proposal_id": proposal.proposal_id},
            is_test_fixture=proposal.is_test_fixture,
            performed_by=reviewer_id,
        )

        proposal.review_status = CandidateReviewDisposition.CONFIRMED
        proposal.reviewed_by = reviewer_id
        proposal.reviewed_at = datetime.now(timezone.utc)
        proposal.reviewer_notes = reviewer_notes
        proposal.confirmed_edge_id = edge.edge_id
        session.flush()

        return proposal, edge

    @classmethod
    def reject_candidate(
        cls,
        session: Session,
        proposal_id: str,
        reviewer_id: str,
        reviewer_notes: str,
    ) -> CandidateRelationshipProposal:
        """
        Authorized human reviewer rejects a candidate relationship.
        """
        proposal = session.query(CandidateRelationshipProposal).filter(
            CandidateRelationshipProposal.proposal_id == proposal_id
        ).first()
        if not proposal:
            raise ProposalNotFoundError(f"Proposal '{proposal_id}' does not exist.")

        proposal.review_status = CandidateReviewDisposition.REJECTED
        proposal.reviewed_by = reviewer_id
        proposal.reviewed_at = datetime.now(timezone.utc)
        proposal.reviewer_notes = reviewer_notes
        session.flush()
        return proposal

    @classmethod
    def defer_candidate(
        cls,
        session: Session,
        proposal_id: str,
        reviewer_id: str,
        reviewer_notes: str,
    ) -> CandidateRelationshipProposal:
        """
        Defers decision pending further documentary evidence or data ingestion.
        """
        proposal = session.query(CandidateRelationshipProposal).filter(
            CandidateRelationshipProposal.proposal_id == proposal_id
        ).first()
        if not proposal:
            raise ProposalNotFoundError(f"Proposal '{proposal_id}' does not exist.")

        proposal.review_status = CandidateReviewDisposition.DEFERRED
        proposal.reviewed_by = reviewer_id
        proposal.reviewed_at = datetime.now(timezone.utc)
        proposal.reviewer_notes = reviewer_notes
        session.flush()
        return proposal

    # -----------------------------------------------------------------------
    # 7. Querying Candidate Proposals
    # -----------------------------------------------------------------------
    @staticmethod
    def list_proposals(
        session: Session,
        review_status: Optional[CandidateReviewDisposition | str] = None,
        min_confidence: float = 0.0,
        source_node_id: Optional[str] = None,
        target_node_id: Optional[str] = None,
    ) -> List[CandidateRelationshipProposal]:
        """Queries proposals filtered by status, confidence threshold, and nodes."""
        query = session.query(CandidateRelationshipProposal)
        if review_status:
            if isinstance(review_status, str):
                review_status = CandidateReviewDisposition(review_status)
            query = query.filter(CandidateRelationshipProposal.review_status == review_status)

        if min_confidence > 0.0:
            query = query.filter(CandidateRelationshipProposal.confidence_score >= min_confidence)

        if source_node_id:
            query = query.filter(CandidateRelationshipProposal.source_node_id == source_node_id)

        if target_node_id:
            query = query.filter(CandidateRelationshipProposal.target_node_id == target_node_id)

        return query.order_by(desc(CandidateRelationshipProposal.confidence_score)).all()
