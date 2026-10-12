"""
Phase 9.5 — Explainable Evidence Traversal Engine.
==================================================

Provides depth-bounded, cycle-safe, explainable graph traversal across the
Unified Civic Intelligence & Evidence Graph connecting Phases 1 through 8.

Key Features:
1. Multi-hop Evidence Walks:
   - Starts from any civic entity node and discovers connected records
     through permitted relationship types.
   - Explores investigation paths with granular hop-by-hop metadata.
2. Complete Path Explainability:
   - Displays every intermediate entity and relationship type.
   - Retains source document, page/table citations, and SHA-256 hashes for each edge.
   - Distinguishes direct documentary links from heuristic candidate/inferred links.
   - Exposes uncertain, provisional, or disputed relationships.
   - Identifies missing evidence along expected investigation sequences.
   - Distinguishes mere association from causation with explicit epistemic caveats.
3. Anti-Fabrication Principle:
   - NEVER manufactures or bridges disconnected paths when an intermediate link is missing.
4. Traversal Safeguards:
   - Cycle prevention using path-scoped visited tracking.
   - Configurable depth bounds (default 4, maximum 6).
   - Configurable result limits (max_paths) and node visit thresholds to protect against
     expensive combinatorial explosion.
   - Permitted relationship type filtering and directional control (outgoing, incoming, both).
5. Specialized Investigation Templates:
   - Political Promise -> Scheme -> Budget Document -> Implementation Evidence.
   - Public Claim -> Supporting & Contradicting Evidence -> Verification Assessment.
   - Civic Issue -> Official Record -> Department Response -> Resolution Evidence.
   - Representative -> Constituency -> Legislative / Public Work Records.
   - Funding Disclosure -> Disclosed Entity -> Source Document.
"""

from __future__ import annotations

import logging
from collections import deque
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set, Tuple

from sqlalchemy import or_, and_
from sqlalchemy.orm import Session

from backend.models.graph import (
    CivicGraphNode,
    CivicEvidenceEdge,
    GraphEntityType,
    GraphRelationshipType,
    MatchingMethod,
    GraphProvenanceStatus,
    GraphReviewStatus,
)

logger = logging.getLogger("civiclens.phase9.traversal")


class TraversalError(Exception):
    """Base exception for evidence traversal engine."""
    pass


class NodeNotFoundError(TraversalError):
    """Raised when the specified start or target node does not exist."""
    pass


# ---------------------------------------------------------------------------
# EvidenceTraversalEngine
# ---------------------------------------------------------------------------
class EvidenceTraversalEngine:
    """
    Traverses evidence paths across Phase 1–8 graph nodes with strict explainability,
    cycle prevention, and epistemic guardrails.
    """

    # -----------------------------------------------------------------------
    # 1. Core General Traversal Engine
    # -----------------------------------------------------------------------
    @classmethod
    def find_paths(
        cls,
        session: Session,
        start_node_id: str,
        target_node_id: Optional[str] = None,
        target_entity_types: Optional[List[GraphEntityType | str]] = None,
        permitted_relationships: Optional[List[GraphRelationshipType | str]] = None,
        direction: str = "outgoing",
        max_depth: int = 4,
        max_paths: int = 20,
        active_only: bool = True,
    ) -> List[Dict[str, Any]]:
        """
        Discovers all paths from start_node_id up to max_depth.
        Returns a list of structured, explainable path dictionaries.
        """
        start_node = session.query(CivicGraphNode).filter(CivicGraphNode.node_id == start_node_id).first()
        if not start_node:
            raise NodeNotFoundError(f"Start node '{start_node_id}' does not exist.")

        if target_node_id:
            target_node = session.query(CivicGraphNode).filter(CivicGraphNode.node_id == target_node_id).first()
            if not target_node:
                raise NodeNotFoundError(f"Target node '{target_node_id}' does not exist.")

        # Normalize filters
        max_depth = max(1, min(max_depth, 6))  # Safety cap at 6 hops
        target_types_set: Optional[Set[GraphEntityType]] = None
        if target_entity_types:
            target_types_set = {
                t if isinstance(t, GraphEntityType) else GraphEntityType(str(t))
                for t in target_entity_types
            }

        rel_filter_set: Optional[Set[GraphRelationshipType]] = None
        if permitted_relationships:
            rel_filter_set = {
                r if isinstance(r, GraphRelationshipType) else GraphRelationshipType.from_string(r)
                for r in permitted_relationships
            }

        # BFS Queue holds tuples: (current_node_id, [node_ids_in_path], [edge_objects_in_path])
        queue = deque([(start_node_id, [start_node_id], [])])
        discovered_paths: List[Dict[str, Any]] = []
        total_paths_explored = 0

        while queue and len(discovered_paths) < max_paths and total_paths_explored < 500:
            current_id, path_node_ids, path_edges = queue.popleft()
            total_paths_explored += 1

            current_depth = len(path_edges)

            # Check if this path should be recorded
            if current_depth > 0:
                current_node = session.query(CivicGraphNode).filter(CivicGraphNode.node_id == current_id).first()
                should_record = False
                if target_node_id:
                    if current_id == target_node_id:
                        should_record = True
                elif target_types_set:
                    if current_node and current_node.entity_type in target_types_set:
                        should_record = True
                else:
                    # General exploration mode: record all discovered paths from start_node
                    should_record = True

                if should_record:
                    built_path = cls._build_explainable_path(
                        session=session,
                        path_node_ids=path_node_ids,
                        path_edges=path_edges,
                        path_index=len(discovered_paths) + 1,
                    )
                    discovered_paths.append(built_path)
                    if len(discovered_paths) >= max_paths:
                        break
                    if target_node_id and current_id == target_node_id:
                        # Found exact target node, don't expand further along this branch
                        continue

            # If depth limit reached, stop branching
            if current_depth >= max_depth:
                continue

            # Query adjacent edges from current_id
            adjacent_edges = cls._fetch_adjacent_edges(
                session=session,
                node_id=current_id,
                direction=direction,
                permitted_relationships=rel_filter_set,
                active_only=active_only,
            )

            for edge in adjacent_edges:
                next_node_id = (
                    edge.target_node_id
                    if edge.source_node_id == current_id
                    else edge.source_node_id
                )

                # Cycle Prevention: Never revisit a node already in the current path branch
                if next_node_id in path_node_ids:
                    continue

                queue.append((
                    next_node_id,
                    path_node_ids + [next_node_id],
                    path_edges + [edge],
                ))

        return discovered_paths

    # -----------------------------------------------------------------------
    # 2. Path Structuring & Explainability Generator
    # -----------------------------------------------------------------------
    @classmethod
    def _build_explainable_path(
        cls,
        session: Session,
        path_node_ids: List[str],
        path_edges: List[CivicEvidenceEdge],
        path_index: int,
    ) -> Dict[str, Any]:
        """
        Transforms raw node and edge sequences into an explainable, auditable path report.
        """
        # Fetch node objects
        nodes_map = {
            n.node_id: n
            for n in session.query(CivicGraphNode).filter(CivicGraphNode.node_id.in_(path_node_ids)).all()
        }

        nodes_list = []
        for nid in path_node_ids:
            node_obj = nodes_map.get(nid)
            if node_obj:
                nodes_list.append(node_obj.to_dict())
            else:
                nodes_list.append({"node_id": nid, "label": "Unknown Node", "attributes": {}})

        edges_list = []
        is_direct_path = True
        has_uncertain = False
        missing_evidence: List[str] = []
        epistemic_caveats: List[str] = []
        conflicting_evidence: List[Dict[str, Any]] = []

        for edge in path_edges:
            # Direct vs Inferred Check
            is_direct = edge.matching_method in (
                MatchingMethod.DIRECT_DOCUMENTARY,
                MatchingMethod.DETERMINISTIC_ID,
            )
            if not is_direct:
                is_direct_path = False

            # Uncertainty / Dispute Check
            is_uncertain = (
                edge.review_status in (GraphReviewStatus.PENDING_REVIEW, GraphReviewStatus.REJECTED)
                or edge.provenance_status != GraphProvenanceStatus.VALID
                or (edge.confidence_score < 0.85 and edge.matching_method == MatchingMethod.AUTOMATED_CANDIDATE)
            )
            if is_uncertain:
                has_uncertain = True

            # Missing Evidence Checks
            has_doc = bool(edge.source_document_id and edge.source_document_id.strip())
            has_ref = bool(edge.evidence_reference and edge.evidence_reference.strip())
            if not has_doc:
                missing_evidence.append(
                    f"Edge '{edge.edge_id}' ({edge.relationship_type.value}) lacks an official primary source document ID."
                )
            if not has_ref:
                missing_evidence.append(
                    f"Edge '{edge.edge_id}' ({edge.relationship_type.value}) lacks an exact excerpt or table cell citation."
                )

            # Epistemic Caveat Generator for Specific Cross-Phase Transitions
            src_node = nodes_map.get(edge.source_node_id)
            tgt_node = nodes_map.get(edge.target_node_id)
            if src_node and tgt_node:
                # 1. Promise -> Scheme (Non-Fulfillment Caveat)
                if (
                    src_node.entity_type == GraphEntityType.POLITICAL_PROMISE
                    and tgt_node.entity_type in (GraphEntityType.BUDGET_SCHEME, GraphEntityType.HISTORICAL_SCHEME)
                ):
                    epistemic_caveats.append(
                        f"Policy Intent Association: Political promise '{src_node.label}' relates to scheme '{tgt_node.label}'. "
                        "This link does NOT constitute proof that the promise was fulfilled. Official fulfillment requires audited "
                        "Government Orders and statutory expenditure line items."
                    )

                # 2. Representative <-> Constituency <-> Public Work / Issue (Spatial Association Caveat)
                types_in_edge = {src_node.entity_type, tgt_node.entity_type}
                if (
                    (GraphEntityType.REPRESENTATIVE in types_in_edge and GraphEntityType.CONSTITUENCY in types_in_edge)
                    or (GraphEntityType.CONSTITUENCY in types_in_edge and types_in_edge.intersection({GraphEntityType.PUBLIC_WORK, GraphEntityType.CIVIC_ISSUE, GraphEntityType.GRIEVANCE_RECORD}))
                    or (types_in_edge.intersection({GraphEntityType.CIVIC_ISSUE, GraphEntityType.GRIEVANCE_RECORD}) and GraphEntityType.REPRESENTATIVE in types_in_edge)
                ):
                    epistemic_caveats.append(
                        "Constituency Spatial Association: A civic issue or public work located within an assembly constituency does NOT establish "
                        "personal administrative culpability or causal blame for the elected representative without formal assembly proceedings."
                    )

                # 3. Funding -> Public Work / Outcome Caveat
                if (
                    src_node.entity_type in (GraphEntityType.CONTRIBUTION, GraphEntityType.DONOR)
                    and tgt_node.entity_type in (GraphEntityType.PUBLIC_WORK, GraphEntityType.BUDGET_SCHEME, GraphEntityType.POLITICAL_PARTY)
                ):
                    epistemic_caveats.append(
                        "Funding Disclosure Caveat: Political donation records reflect statutory contribution disclosures; they do NOT "
                        "establish causal determination or procurement outcome influence over public infrastructure works."
                    )

                # 4. News Report -> Fact-Checked Claim Caveat
                if (
                    src_node.entity_type == GraphEntityType.NEWS_ARTICLE
                    and tgt_node.entity_type in (GraphEntityType.CLAIM, GraphEntityType.ATOMIC_CLAIM)
                ):
                    epistemic_caveats.append(
                        "Media Reporting Caveat: News media reports document public discourse and journalistic reporting on a claim, "
                        "but do not constitute primary statutory fact-verification."
                    )

                # Check for Conflicting Evidence on Target Node (e.g. Claims with conflicting evidence)
                if tgt_node.entity_type in (GraphEntityType.CLAIM, GraphEntityType.ATOMIC_CLAIM):
                    other_edges = (
                        session.query(CivicEvidenceEdge)
                        .filter(
                            CivicEvidenceEdge.target_node_id == tgt_node.node_id,
                            CivicEvidenceEdge.edge_id != edge.edge_id,
                        )
                        .all()
                    )
                    has_contradict = any(e.relationship_type == GraphRelationshipType.CONTRADICTS for e in other_edges)
                    has_support = any(e.relationship_type == GraphRelationshipType.PROVIDES_EVIDENCE_FOR for e in other_edges)
                    if (edge.relationship_type == GraphRelationshipType.PROVIDES_EVIDENCE_FOR and has_contradict) or \
                       (edge.relationship_type == GraphRelationshipType.CONTRADICTS and has_support):
                        conflicting_evidence.append({
                            "node_id": tgt_node.node_id,
                            "label": tgt_node.label,
                            "conflict_type": "DIALECTICAL_CLAIM_EVIDENCE",
                            "explanation": "Claim has simultaneous supporting and contradicting evidence edges from distinct statutory or audit sources.",
                        })

            edge_dict = edge.to_dict()
            edge_dict["is_direct"] = is_direct
            edge_dict["is_uncertain_or_disputed"] = is_uncertain
            edges_list.append(edge_dict)

        # Build narrative summary
        labels_seq = " -> ".join([f"[{n['label']} ({n.get('entity_type', '')})]" for n in nodes_list])
        summary_narrative = (
            f"Evidence path of {len(path_edges)} hop(s): {labels_seq}. "
            f"Verification: {'Direct documentary path' if is_direct_path else 'Contains candidate/inferred links'}. "
            f"{'Warning: Contains provisional or unreviewed edges.' if has_uncertain else 'All edges verified.'}"
        )

        return {
            "path_id": f"PATH:{path_index}",
            "start_node_id": path_node_ids[0],
            "end_node_id": path_node_ids[-1],
            "length": len(path_edges),
            "nodes": nodes_list,
            "edges": edges_list,
            "is_direct_path": is_direct_path,
            "has_uncertain_edges": has_uncertain,
            "missing_evidence": missing_evidence,
            "epistemic_caveats": epistemic_caveats,
            "conflicting_evidence": conflicting_evidence,
            "summary": summary_narrative,
        }

    @staticmethod
    def _fetch_adjacent_edges(
        session: Session,
        node_id: str,
        direction: str = "outgoing",
        permitted_relationships: Optional[Set[GraphRelationshipType]] = None,
        active_only: bool = True,
    ) -> List[CivicEvidenceEdge]:
        """Fetches adjacent edges matching directional and relationship constraints."""
        query = session.query(CivicEvidenceEdge)

        if direction == "outgoing":
            query = query.filter(CivicEvidenceEdge.source_node_id == node_id)
        elif direction == "incoming":
            query = query.filter(CivicEvidenceEdge.target_node_id == node_id)
        else:  # "both"
            query = query.filter(
                or_(
                    CivicEvidenceEdge.source_node_id == node_id,
                    CivicEvidenceEdge.target_node_id == node_id,
                )
            )

        if permitted_relationships:
            query = query.filter(CivicEvidenceEdge.relationship_type.in_(permitted_relationships))

        if active_only:
            query = query.filter(CivicEvidenceEdge.provenance_status == GraphProvenanceStatus.VALID)

        return query.all()

    # -----------------------------------------------------------------------
    # 3. Investigation Walk Templates
    # -----------------------------------------------------------------------
    @classmethod
    def investigate_promise_fulfillment(
        cls,
        session: Session,
        promise_node_id: str,
        max_depth: int = 4,
    ) -> List[Dict[str, Any]]:
        """
        Investigation Walk 1:
        Political promise -> relevant scheme -> budget document -> available implementation evidence.
        """
        return cls.find_paths(
            session=session,
            start_node_id=promise_node_id,
            target_entity_types=[
                GraphEntityType.RESOLUTION_EVIDENCE,
                GraphEntityType.PUBLIC_WORK,
                GraphEntityType.BUDGET_RECORD,
                GraphEntityType.HISTORICAL_SCHEME,
                GraphEntityType.BUDGET_SCHEME,
            ],
            permitted_relationships=[
                GraphRelationshipType.RELATES_TO,
                GraphRelationshipType.PROMISES,
                GraphRelationshipType.FUNDS,
                GraphRelationshipType.IMPLEMENTS,
                GraphRelationshipType.CONTEXTUALIZES,
            ],
            direction="outgoing",
            max_depth=max_depth,
        )

    @classmethod
    def investigate_claim_veracity(
        cls,
        session: Session,
        claim_node_id: str,
        max_depth: int = 3,
    ) -> List[Dict[str, Any]]:
        """
        Investigation Walk 2:
        Public claim -> supporting and contradicting evidence -> verification assessment.
        """
        return cls.find_paths(
            session=session,
            start_node_id=claim_node_id,
            direction="both",
            permitted_relationships=[
                GraphRelationshipType.PROVIDES_EVIDENCE_FOR,
                GraphRelationshipType.CONTRADICTS,
                GraphRelationshipType.RELATES_TO,
                GraphRelationshipType.REPORTS_ON,
                GraphRelationshipType.MENTIONS,
            ],
            max_depth=max_depth,
        )

    @classmethod
    def investigate_civic_issue_resolution(
        cls,
        session: Session,
        issue_node_id: str,
        max_depth: int = 4,
    ) -> List[Dict[str, Any]]:
        """
        Investigation Walk 3:
        Civic issue -> official record -> department response -> resolution evidence.
        """
        return cls.find_paths(
            session=session,
            start_node_id=issue_node_id,
            direction="both",
            permitted_relationships=[
                GraphRelationshipType.RESPONDS_TO,
                GraphRelationshipType.RELATES_TO,
                GraphRelationshipType.CONCERNS,
                GraphRelationshipType.PROVIDES_EVIDENCE_FOR,
                GraphRelationshipType.IMPLEMENTS,
            ],
            max_depth=max_depth,
        )

    @classmethod
    def investigate_representative_works(
        cls,
        session: Session,
        representative_node_id: str,
        max_depth: int = 3,
    ) -> List[Dict[str, Any]]:
        """
        Investigation Walk 4:
        Representative -> constituency -> documented legislative or public-work records.
        """
        return cls.find_paths(
            session=session,
            start_node_id=representative_node_id,
            direction="both",
            permitted_relationships=[
                GraphRelationshipType.REPRESENTS,
                GraphRelationshipType.LOCATED_IN,
                GraphRelationshipType.CONCERNS,
                GraphRelationshipType.RELATES_TO,
            ],
            max_depth=max_depth,
        )

    @classmethod
    def investigate_funding_lineage(
        cls,
        session: Session,
        funding_node_id: str,
        max_depth: int = 3,
    ) -> List[Dict[str, Any]]:
        """
        Investigation Walk 5:
        Political funding disclosure -> disclosed entity -> relevant source document.
        """
        return cls.find_paths(
            session=session,
            start_node_id=funding_node_id,
            direction="both",
            permitted_relationships=[
                GraphRelationshipType.FUNDS,
                GraphRelationshipType.RELATES_TO,
                GraphRelationshipType.DERIVED_FROM,
                GraphRelationshipType.MENTIONS,
            ],
            max_depth=max_depth,
        )
