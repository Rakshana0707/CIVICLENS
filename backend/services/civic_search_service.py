"""
Phase 9.7 — Unified Civic Search and Cross-Phase Resolution Service.
=====================================================================

Provides unified search, cross-phase original record retrieval, neighbor exploration,
conflict reporting, and provenance audit queries across Phases 1–8.

Epistemic & Security Principles:
- Strictly reuse existing database records and schemas without duplicating data.
- Stable entity IDs and verified source document references.
- Automated PII and internal system path sanitization (DPDPA 2023 compliance).
- Role-based authorization for administrative and review operations.
"""

from __future__ import annotations

import logging
import re
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import or_, and_, desc
from sqlalchemy.orm import Session

from backend.models.entity_registry import (
    CanonicalEntity,
    EntityAlias,
    EntityAuditRecord,
    SourceIdentifierMapping,
    RegistryEntityType,
)
from backend.models.graph import (
    CivicGraphNode,
    CivicEvidenceEdge,
    CandidateRelationshipProposal,
    CandidateReviewDisposition,
    CivicConflictRecord,
    ConflictTypeEnum,
    ConflictSeverityEnum,
    ConflictResolutionStatus,
    GraphEntityType,
    GraphRelationshipType,
    MatchingMethod,
    GraphReviewStatus,
    GraphProvenanceStatus,
)
from backend.services.evidence_quality_service import EvidenceQualityService
from backend.models.civic_issue import sanitize_pii

logger = logging.getLogger("civiclens.phase9.search_service")

# Authorized roles permitted to execute review, audit, and mutation actions
AUTHORIZED_GRAPH_ROLES = {
    "ADMIN",
    "LEAD_REVIEWER",
    "SENIOR_FACT_CHECKER",
    "DOMAIN_EXPERT",
    "AUDITOR",
    "RESEARCHER",
}


class GraphSearchError(Exception):
    """Base exception for search service errors."""
    pass


class NodeNotFoundError(GraphSearchError):
    """Raised when a requested node does not exist."""
    pass


class EdgeNotFoundError(GraphSearchError):
    """Raised when a requested edge does not exist."""
    pass


class UnauthorizedActionError(GraphSearchError):
    """Raised when an unauthenticated or unauthorized role attempts a privileged action."""
    pass


def sanitize_system_paths(text: str) -> str:
    """
    Scrubs local filesystem paths (Windows or UNIX) and source file references
    from public-facing responses to avoid leaking server internals.
    """
    if not isinstance(text, str):
        return text

    # Windows drive paths (e.g. C:\Users\..., E:\CIVCLENS\...)
    text = re.sub(r'[A-Za-z]:\\[\w\s.\\\-_]+', '[INTERNAL_PATH_REDACTED]', text)
    # Unix system paths (e.g. /home/..., /var/..., /tmp/...)
    text = re.sub(r'/(?:home|var|tmp|etc|usr|opt)/[\w\-./]+', '[INTERNAL_PATH_REDACTED]', text)
    # Python source script references
    text = re.sub(r'[\w\-]+\.py\b', '[SOURCE_FILE]', text)
    return text


def sanitize_payload(obj: Any, is_auditor: bool = False) -> Any:
    """
    Recursively scrubs PII, system file paths, and secret tokens from API responses.
    """
    if isinstance(obj, dict):
        sanitized = {}
        for k, v in obj.items():
            k_lower = k.lower()
            if any(secret_kw in k_lower for secret_kw in ("password", "secret", "token", "credential", "api_key")):
                sanitized[k] = "[REDACTED_CREDENTIAL]"
            elif not is_auditor and any(pii_kw in k_lower for pii_kw in ("citizen_name", "reporter_name", "phone", "email", "door_no")):
                sanitized[k] = "[PII_REDACTED]"
            else:
                sanitized[k] = sanitize_payload(v, is_auditor)
        return sanitized
    elif isinstance(obj, list):
        return [sanitize_payload(item, is_auditor) for item in obj]
    elif isinstance(obj, str):
        cleaned = sanitize_pii(obj)
        cleaned = sanitize_system_paths(cleaned)
        return cleaned
    return obj


def verify_graph_authorization(role: Optional[str]) -> Tuple[bool, Optional[str]]:
    """
    Validates reviewer authorization role.
    Returns (True, None) if authorized, (False, error_message) otherwise.
    """
    if not role:
        return False, "Access Denied: Missing authentication/authorization role header."
    clean_role = role.strip().upper()
    if clean_role not in AUTHORIZED_GRAPH_ROLES:
        return (
            False,
            f"Access Denied: Role '{role}' is not authorized. Authorized roles: {sorted(list(AUTHORIZED_GRAPH_ROLES))}",
        )
    return True, None


class UnifiedCivicSearchService:
    """
    Central search and retrieval service for the Unified Civic Intelligence & Evidence Graph.
    """

    @staticmethod
    def search_entities(
        session: Session,
        query: Optional[str] = None,
        entity_type: Optional[str] = None,
        source_phase: Optional[str] = None,
        min_confidence: float = 0.0,
        limit: int = 20,
        offset: int = 0,
    ) -> Dict[str, Any]:
        """
        Searches canonical entities across Phases 1–8.
        Supports English, Tamil, alias searches, and filter criteria with pagination.
        """
        limit = max(1, min(limit, 100))
        offset = max(0, offset)

        q = session.query(CivicGraphNode)

        if entity_type:
            try:
                clean_et = entity_type.strip().upper()
                et = None
                for candidate in GraphEntityType:
                    if candidate.value.upper() == clean_et or candidate.name.upper() == clean_et:
                        et = candidate
                        break
                if et:
                    q = q.filter(CivicGraphNode.entity_type == et)
            except Exception:
                pass

        if source_phase:
            q = q.filter(CivicGraphNode.source_phase == source_phase.upper())

        if query and query.strip():
            clean_query = query.strip()
            pattern = f"%{clean_query}%"
            # Match on label, canonical_id, or node_id
            q = q.filter(
                or_(
                    CivicGraphNode.label.ilike(pattern),
                    CivicGraphNode.canonical_id.ilike(pattern),
                    CivicGraphNode.node_id.ilike(pattern),
                )
            )

        total_count = q.count()
        nodes = q.order_by(CivicGraphNode.label).offset(offset).limit(limit).all()

        results = []
        for n in nodes:
            item = {
                "node_id": n.node_id,
                "canonical_id": n.canonical_id,
                "label": n.label,
                "label_ta": n.label_ta,
                "entity_type": n.entity_type.value if hasattr(n.entity_type, "value") else str(n.entity_type),
                "source_phase": n.source_phase,
                "created_at": n.created_at.isoformat() if n.created_at else None,
                "properties": sanitize_payload(n.attributes_json or {}),
            }
            results.append(item)

        return {
            "items": results,
            "total": total_count,
            "limit": limit,
            "offset": offset,
        }

    @staticmethod
    def get_entity_profile(session: Session, node_id: str, is_auditor: bool = False) -> Dict[str, Any]:
        """
        Retrieves a canonical entity node, its registry profile, aliases, source mappings,
        and connected edge summary.
        """
        node = session.query(CivicGraphNode).filter(CivicGraphNode.node_id == node_id).first()
        if not node:
            raise NodeNotFoundError(f"Node '{node_id}' not found.")

        # Canonical entity profile
        canonical_profile = None
        aliases = []
        source_mappings = []

        if node.canonical_id:
            can_ent = (
                session.query(CanonicalEntity)
                .filter(CanonicalEntity.entity_id == node.canonical_id)
                .first()
            )
            if can_ent:
                canonical_profile = {
                    "canonical_id": can_ent.entity_id,
                    "canonical_name": can_ent.canonical_name_en,
                    "tamil_name": can_ent.canonical_name_ta,
                    "entity_type": can_ent.entity_type.value if hasattr(can_ent.entity_type, "value") else str(can_ent.entity_type),
                    "status": can_ent.status.value if hasattr(can_ent.status, "value") else str(can_ent.status),
                    "created_at": can_ent.created_at.isoformat() if can_ent.created_at else None,
                }
                aliases = [
                    {
                        "alias_name": a.alias_name,
                        "alias_type": a.alias_type.value if hasattr(a.alias_type, "value") else str(a.alias_type),
                        "language": a.language,
                        "source": a.source_reference,
                    }
                    for a in getattr(can_ent, "aliases", [])
                ]
                source_mappings = [
                    {
                        "source_system": sm.source_system,
                        "source_record_id": sm.source_record_id,
                        "original_name": sm.source_record_name,
                    }
                    for sm in getattr(can_ent, "source_mappings", [])
                ]

        # Connected edge statistics
        out_edges = (
            session.query(CivicEvidenceEdge)
            .filter(
                CivicEvidenceEdge.source_node_id == node_id,
                CivicEvidenceEdge.provenance_status.notin_([GraphProvenanceStatus.RETRACTED, GraphProvenanceStatus.SUPERSEDED]),
            )
            .all()
        )
        in_edges = (
            session.query(CivicEvidenceEdge)
            .filter(
                CivicEvidenceEdge.target_node_id == node_id,
                CivicEvidenceEdge.provenance_status.notin_([GraphProvenanceStatus.RETRACTED, GraphProvenanceStatus.SUPERSEDED]),
            )
            .all()
        )

        edge_stats = {
            "outbound_count": len(out_edges),
            "inbound_count": len(in_edges),
            "outbound_by_type": {},
            "inbound_by_type": {},
        }
        for e in out_edges:
            rel = e.relationship_type.value if hasattr(e.relationship_type, "value") else str(e.relationship_type)
            edge_stats["outbound_by_type"][rel] = edge_stats["outbound_by_type"].get(rel, 0) + 1
        for e in in_edges:
            rel = e.relationship_type.value if hasattr(e.relationship_type, "value") else str(e.relationship_type)
            edge_stats["inbound_by_type"][rel] = edge_stats["inbound_by_type"].get(rel, 0) + 1

        return {
            "node": {
                "node_id": node.node_id,
                "canonical_id": node.canonical_id,
                "label": node.label,
                "entity_type": node.entity_type.value if hasattr(node.entity_type, "value") else str(node.entity_type),
                "source_phase": node.source_phase,
                "label_ta": node.label_ta,
                "properties": sanitize_payload(node.attributes_json or {}, is_auditor=is_auditor),
                "created_at": node.created_at.isoformat() if node.created_at else None,
            },
            "canonical_profile": canonical_profile,
            "aliases": aliases,
            "source_mappings": source_mappings,
            "edge_statistics": edge_stats,
        }

    @staticmethod
    def get_connected_entities(
        session: Session,
        node_id: str,
        direction: str = "both",
        relationship_type: Optional[str] = None,
        target_type: Optional[str] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> Dict[str, Any]:
        """
        Retrieves directly connected neighbor entities and their linking evidence edges.
        """
        limit = max(1, min(limit, 100))
        offset = max(0, offset)

        node = session.query(CivicGraphNode).filter(CivicGraphNode.node_id == node_id).first()
        if not node:
            raise NodeNotFoundError(f"Node '{node_id}' not found.")

        edges_query = session.query(CivicEvidenceEdge).filter(
            CivicEvidenceEdge.provenance_status.notin_([GraphProvenanceStatus.RETRACTED, GraphProvenanceStatus.SUPERSEDED])
        )

        dir_clean = direction.lower().strip()
        if dir_clean == "outgoing":
            edges_query = edges_query.filter(CivicEvidenceEdge.source_node_id == node_id)
        elif dir_clean == "incoming":
            edges_query = edges_query.filter(CivicEvidenceEdge.target_node_id == node_id)
        else:
            edges_query = edges_query.filter(
                or_(
                    CivicEvidenceEdge.source_node_id == node_id,
                    CivicEvidenceEdge.target_node_id == node_id,
                )
            )

        if relationship_type:
            try:
                rt = GraphRelationshipType(relationship_type.lower())
                edges_query = edges_query.filter(CivicEvidenceEdge.relationship_type == rt)
            except ValueError:
                pass

        total_edges = edges_query.count()
        edges = edges_query.order_by(desc(CivicEvidenceEdge.confidence_score)).offset(offset).limit(limit).all()

        results = []
        for edge in edges:
            is_outbound = edge.source_node_id == node_id
            neighbor_id = edge.target_node_id if is_outbound else edge.source_node_id

            neighbor_node = session.query(CivicGraphNode).filter(CivicGraphNode.node_id == neighbor_id).first()
            if not neighbor_node:
                continue

            if target_type:
                n_type_str = (
                    neighbor_node.entity_type.value
                    if hasattr(neighbor_node.entity_type, "value")
                    else str(neighbor_node.entity_type)
                )
                if n_type_str.upper() != target_type.upper():
                    continue

            results.append({
                "edge_id": edge.edge_id,
                "direction": "outgoing" if is_outbound else "incoming",
                "relationship_type": edge.relationship_type.value if hasattr(edge.relationship_type, "value") else str(edge.relationship_type),
                "matching_method": edge.matching_method.value if hasattr(edge.matching_method, "value") else str(edge.matching_method),
                "confidence_score": edge.confidence_score,
                "review_status": edge.review_status.value if hasattr(edge.review_status, "value") else str(edge.review_status),
                "provenance_status": edge.provenance_status.value if hasattr(edge.provenance_status, "value") else str(edge.provenance_status),
                "evidence_reference": sanitize_system_paths(edge.evidence_reference or ""),
                "source_document_id": edge.source_document_id,
                "source_document_url": edge.source_document_url,
                "source_document_hash": edge.source_document_hash,
                "valid_from": str(edge.valid_from) if edge.valid_from else None,
                "valid_to": str(edge.valid_to) if edge.valid_to else None,
                "neighbor_node": {
                    "node_id": neighbor_node.node_id,
                    "canonical_id": neighbor_node.canonical_id,
                    "label": neighbor_node.label,
                    "entity_type": neighbor_node.entity_type.value if hasattr(neighbor_node.entity_type, "value") else str(neighbor_node.entity_type),
                    "source_phase": neighbor_node.source_phase,
                },
            })

        return {
            "node_id": node_id,
            "direction": direction,
            "connected_entities": results,
            "total": total_edges,
            "limit": limit,
            "offset": offset,
        }

    @staticmethod
    def filter_edges(
        session: Session,
        relationship_type: Optional[str] = None,
        source_phase: Optional[str] = None,
        source_document_id: Optional[str] = None,
        matching_method: Optional[str] = None,
        review_status: Optional[str] = None,
        min_confidence: float = 0.0,
        source_node_id: Optional[str] = None,
        target_node_id: Optional[str] = None,
        active_only: bool = True,
        limit: int = 20,
        offset: int = 0,
    ) -> Dict[str, Any]:
        """
        Filters graph edges by relationship type, source phase, document ID, review status, and confidence.
        """
        limit = max(1, min(limit, 100))
        offset = max(0, offset)

        q = session.query(CivicEvidenceEdge)
        if active_only:
            q = q.filter(
                CivicEvidenceEdge.provenance_status.notin_([GraphProvenanceStatus.RETRACTED, GraphProvenanceStatus.SUPERSEDED])
            )

        if relationship_type:
            try:
                rt = GraphRelationshipType(relationship_type.lower())
                q = q.filter(CivicEvidenceEdge.relationship_type == rt)
            except ValueError:
                pass

        if source_node_id:
            q = q.filter(CivicEvidenceEdge.source_node_id == source_node_id)
        if target_node_id:
            q = q.filter(CivicEvidenceEdge.target_node_id == target_node_id)
        if source_document_id:
            q = q.filter(CivicEvidenceEdge.source_document_id == source_document_id)

        if matching_method:
            try:
                mm = MatchingMethod(matching_method.upper())
                q = q.filter(CivicEvidenceEdge.matching_method == mm)
            except ValueError:
                pass

        if review_status:
            try:
                rs = GraphReviewStatus(review_status.upper())
                q = q.filter(CivicEvidenceEdge.review_status == rs)
            except ValueError:
                pass

        if min_confidence > 0.0:
            q = q.filter(CivicEvidenceEdge.confidence_score >= min_confidence)

        total = q.count()
        edges = q.order_by(desc(CivicEvidenceEdge.confidence_score)).offset(offset).limit(limit).all()

        results = []
        for e in edges:
            results.append({
                "edge_id": e.edge_id,
                "source_node_id": e.source_node_id,
                "target_node_id": e.target_node_id,
                "relationship_type": e.relationship_type.value if hasattr(e.relationship_type, "value") else str(e.relationship_type),
                "evidence_reference": sanitize_system_paths(e.evidence_reference or ""),
                "source_document_id": e.source_document_id,
                "source_document_url": e.source_document_url,
                "source_document_hash": e.source_document_hash,
                "matching_method": e.matching_method.value if hasattr(e.matching_method, "value") else str(e.matching_method),
                "confidence_score": e.confidence_score,
                "review_status": e.review_status.value if hasattr(e.review_status, "value") else str(e.review_status),
                "provenance_status": e.provenance_status.value if hasattr(e.provenance_status, "value") else str(e.provenance_status),
                "valid_from": str(e.valid_from) if e.valid_from else None,
                "valid_to": str(e.valid_to) if e.valid_to else None,
                "properties": sanitize_payload(e.properties_json or {}),
            })

        return {
            "edges": results,
            "total": total,
            "limit": limit,
            "offset": offset,
        }

    @staticmethod
    def get_edge_evidence(session: Session, edge_id: str) -> Dict[str, Any]:
        """
        Retrieves full documentary evidence, provenance, and 9-factor scorecard for an edge.
        """
        edge = session.query(CivicEvidenceEdge).filter(CivicEvidenceEdge.edge_id == edge_id).first()
        if not edge:
            raise EdgeNotFoundError(f"Edge '{edge_id}' not found.")

        source_node = session.query(CivicGraphNode).filter(CivicGraphNode.node_id == edge.source_node_id).first()
        target_node = session.query(CivicGraphNode).filter(CivicGraphNode.node_id == edge.target_node_id).first()

        scorecard = EvidenceQualityService.assess_edge_evidence_quality(edge)

        # Check if edge is involved in any active conflicts
        conflicts = (
            session.query(CivicConflictRecord)
            .filter(or_(CivicConflictRecord.edge_a_id == edge_id, CivicConflictRecord.edge_b_id == edge_id))
            .all()
        )

        return {
            "edge_id": edge.edge_id,
            "source_node": {
                "node_id": source_node.node_id if source_node else edge.source_node_id,
                "label": source_node.label if source_node else "Unknown",
                "entity_type": source_node.entity_type.value if source_node and hasattr(source_node.entity_type, "value") else "UNKNOWN",
            },
            "target_node": {
                "node_id": target_node.node_id if target_node else edge.target_node_id,
                "label": target_node.label if target_node else "Unknown",
                "entity_type": target_node.entity_type.value if target_node and hasattr(target_node.entity_type, "value") else "UNKNOWN",
            },
            "relationship_type": edge.relationship_type.value if hasattr(edge.relationship_type, "value") else str(edge.relationship_type),
            "evidence_reference": sanitize_system_paths(edge.evidence_reference or ""),
            "source_document_id": edge.source_document_id,
            "source_document_url": edge.source_document_url,
            "source_document_hash": edge.source_document_hash,
            "matching_method": edge.matching_method.value if hasattr(edge.matching_method, "value") else str(edge.matching_method),
            "confidence_score": edge.confidence_score,
            "review_status": edge.review_status.value if hasattr(edge.review_status, "value") else str(edge.review_status),
            "provenance_status": edge.provenance_status.value if hasattr(edge.provenance_status, "value") else str(edge.provenance_status),
            "valid_from": str(edge.valid_from) if edge.valid_from else None,
            "valid_to": str(edge.valid_to) if edge.valid_to else None,
            "quality_scorecard": scorecard,
            "active_conflicts": [c.to_dict() for c in conflicts],
        }

    @staticmethod
    def get_unresolved_proposals(
        session: Session,
        min_confidence: float = 0.0,
        source_node_id: Optional[str] = None,
        target_node_id: Optional[str] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> Dict[str, Any]:
        """
        Lists unresolved relationship candidates discovered across Phase 1–8 records.
        """
        limit = max(1, min(limit, 100))
        offset = max(0, offset)

        q = session.query(CandidateRelationshipProposal).filter(
            CandidateRelationshipProposal.review_status == CandidateReviewDisposition.PENDING_REVIEW
        )

        if min_confidence > 0.0:
            q = q.filter(CandidateRelationshipProposal.confidence_score >= min_confidence)
        if source_node_id:
            q = q.filter(CandidateRelationshipProposal.source_node_id == source_node_id)
        if target_node_id:
            q = q.filter(CandidateRelationshipProposal.target_node_id == target_node_id)

        total = q.count()
        proposals = q.order_by(desc(CandidateRelationshipProposal.confidence_score)).offset(offset).limit(limit).all()

        return {
            "unresolved_proposals": [p.to_dict() for p in proposals],
            "total": total,
            "limit": limit,
            "offset": offset,
        }

    @staticmethod
    def get_conflicts_and_disputes(
        session: Session,
        node_id: Optional[str] = None,
        conflict_type: Optional[str] = None,
        severity: Optional[str] = None,
        resolution_status: Optional[str] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> Dict[str, Any]:
        """
        Retrieves contradictory or disputed evidence records and dialectical tensions.
        """
        limit = max(1, min(limit, 100))
        offset = max(0, offset)

        # 1. Query persistent conflicts
        q = session.query(CivicConflictRecord)
        if node_id:
            q = q.filter(
                or_(
                    CivicConflictRecord.primary_node_id == node_id,
                    CivicConflictRecord.secondary_node_id == node_id,
                )
            )
        if conflict_type:
            try:
                ct = ConflictTypeEnum(conflict_type.upper())
                q = q.filter(CivicConflictRecord.conflict_type == ct)
            except ValueError:
                pass
        if severity:
            try:
                sev = ConflictSeverityEnum(severity.upper())
                q = q.filter(CivicConflictRecord.severity == sev)
            except ValueError:
                pass
        if resolution_status:
            try:
                res = ConflictResolutionStatus(resolution_status.upper())
                q = q.filter(CivicConflictRecord.resolution_status == res)
            except ValueError:
                pass

        total_conflicts = q.count()
        conflicts = q.order_by(desc(CivicConflictRecord.detected_at)).offset(offset).limit(limit).all()

        # 2. Query edges marked as DISPUTED
        disputed_q = session.query(CivicEvidenceEdge).filter(
            CivicEvidenceEdge.provenance_status == GraphProvenanceStatus.DISPUTED
        )
        if node_id:
            disputed_q = disputed_q.filter(
                or_(
                    CivicEvidenceEdge.source_node_id == node_id,
                    CivicEvidenceEdge.target_node_id == node_id,
                )
            )
        disputed_edges = disputed_q.limit(limit).all()

        return {
            "conflicts": [c.to_dict() for c in conflicts],
            "disputed_edges": [
                {
                    "edge_id": de.edge_id,
                    "source_node_id": de.source_node_id,
                    "target_node_id": de.target_node_id,
                    "relationship_type": de.relationship_type.value if hasattr(de.relationship_type, "value") else str(de.relationship_type),
                    "evidence_reference": sanitize_system_paths(de.evidence_reference or ""),
                    "provenance_status": "DISPUTED",
                }
                for de in disputed_edges
            ],
            "total_conflicts": total_conflicts,
            "total_disputed_edges": len(disputed_edges),
            "limit": limit,
            "offset": offset,
        }

    @staticmethod
    def get_graph_history(
        session: Session,
        node_id: Optional[str] = None,
        edge_id: Optional[str] = None,
        reviewer_id: Optional[str] = None,
        action: Optional[str] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> Dict[str, Any]:
        """
        Retrieves graph provenance and review history across proposals, edges, and entity merges/splits.
        """
        limit = max(1, min(limit, 100))
        offset = max(0, offset)

        history_items: List[Dict[str, Any]] = []

        # 1. Proposals reviewed (confirmed/rejected/deferred)
        prop_q = session.query(CandidateRelationshipProposal).filter(
            CandidateRelationshipProposal.review_status != CandidateReviewDisposition.PENDING_REVIEW
        )
        if reviewer_id:
            prop_q = prop_q.filter(CandidateRelationshipProposal.reviewed_by == reviewer_id)
        if node_id:
            prop_q = prop_q.filter(
                or_(
                    CandidateRelationshipProposal.source_node_id == node_id,
                    CandidateRelationshipProposal.target_node_id == node_id,
                )
            )
        if edge_id:
            prop_q = prop_q.filter(CandidateRelationshipProposal.confirmed_edge_id == edge_id)

        reviewed_props = prop_q.order_by(desc(CandidateRelationshipProposal.reviewed_at)).limit(limit).all()
        for p in reviewed_props:
            history_items.append({
                "audit_type": "PROPOSAL_REVIEW",
                "record_id": p.proposal_id,
                "action": p.review_status.value if hasattr(p.review_status, "value") else str(p.review_status),
                "reviewer_id": p.reviewed_by,
                "reviewed_at": p.reviewed_at.isoformat() if p.reviewed_at else None,
                "notes": sanitize_system_paths(p.reviewer_notes or ""),
                "confirmed_edge_id": p.confirmed_edge_id,
                "source_node_id": p.source_node_id,
                "target_node_id": p.target_node_id,
            })

        # 2. Entity audit history (merges, splits, updates)
        audit_q = session.query(EntityAuditRecord)
        if reviewer_id:
            audit_q = audit_q.filter(EntityAuditRecord.performed_by == reviewer_id)
        if action:
            audit_q = audit_q.filter(EntityAuditRecord.rationale.ilike(f"%{action}%"))

        entity_audits = audit_q.order_by(desc(EntityAuditRecord.timestamp)).limit(limit).all()
        for ea in entity_audits:
            history_items.append({
                "audit_type": "ENTITY_REGISTRY_MUTATION",
                "record_id": ea.audit_id,
                "action": ea.operation_type.value if hasattr(ea.operation_type, "value") else str(ea.operation_type),
                "reviewer_id": ea.performed_by,
                "reviewed_at": ea.timestamp.isoformat() if ea.timestamp else None,
                "notes": sanitize_system_paths(ea.rationale or ""),
                "canonical_id": ea.primary_entity_id,
                "before_state": sanitize_payload(ea.previous_state_json or {}),
                "after_state": sanitize_payload(ea.new_state_json or {}),
            })

        # Sort combined history by timestamp descending
        history_items.sort(key=lambda x: x.get("reviewed_at") or "", reverse=True)
        paginated_history = history_items[offset : offset + limit]

        return {
            "history": paginated_history,
            "total": len(history_items),
            "limit": limit,
            "offset": offset,
        }

    @staticmethod
    def get_original_phase_record(
        session: Session,
        node_id: str,
        is_auditor: bool = False,
    ) -> Dict[str, Any]:
        """
        Dynamically fetches and resolves relevant records from the original Phase 1–8 modules
        without duplicating datasets. Scrubs PII and local paths.
        """
        node = session.query(CivicGraphNode).filter(CivicGraphNode.node_id == node_id).first()
        if not node:
            raise NodeNotFoundError(f"Node '{node_id}' not found.")

        phase = (node.source_phase or "").upper()
        entity_type_str = node.entity_type.value if hasattr(node.entity_type, "value") else str(node.entity_type)
        cid = node.canonical_id or ""

        resolved_record: Dict[str, Any] = {
            "node_id": node.node_id,
            "canonical_id": node.canonical_id,
            "source_phase": phase,
            "entity_type": entity_type_str,
            "module_data": None,
        }

        try:
            # Phase 1 & 2: Budgets and Historical Schemes
            if phase in ("PHASE_1", "PHASE_2") or entity_type_str in ("BUDGET_RECORD", "BUDGET_SCHEME", "GOVERNMENT_DEPARTMENT"):
                from backend.models.budget import BudgetScheme, BudgetDepartment, BudgetRecord
                attrs = node.attributes_json or {}
                scheme = session.query(BudgetScheme).filter(
                    or_(BudgetScheme.name == node.label, BudgetScheme.id == attrs.get("scheme_id"))
                ).first()
                if scheme:
                    resolved_record["module_data"] = {
                        "scheme_id": scheme.id,
                        "scheme_name": scheme.name,
                        "head_of_account": scheme.head_of_account,
                        "department": scheme.department.name if scheme.department else None,
                    }
                else:
                    dept = session.query(BudgetDepartment).filter(
                        or_(BudgetDepartment.name == node.label, BudgetDepartment.code == cid)
                    ).first()
                    if dept:
                        resolved_record["module_data"] = {
                            "department_id": dept.id,
                            "department_name": dept.name,
                            "code": dept.code,
                        }

            # Phase 3: Manifesto Promises
            elif phase == "PHASE_3" or entity_type_str == "POLITICAL_PROMISE":
                from backend.models.promise import PoliticalPromise
                p = session.query(PoliticalPromise).filter(
                    or_(PoliticalPromise.promise_id == cid, PoliticalPromise.original_text.ilike(f"%{node.label}%"))
                ).first()
                if p:
                    resolved_record["module_data"] = {
                        "promise_id": p.promise_id,
                        "original_text": p.original_text,
                        "classification": p.classification,
                        "manifesto_id": p.manifesto_id,
                        "metadata": p.metadata_json or {},
                    }

            # Phase 4: News Articles
            elif phase == "PHASE_4" or entity_type_str == "NEWS_ARTICLE":
                from backend.models.news import Article
                art = session.query(Article).filter(
                    or_(Article.article_id == cid, Article.title.ilike(f"%{node.label}%"))
                ).first()
                if art:
                    resolved_record["module_data"] = {
                        "article_id": art.article_id,
                        "title": art.title,
                        "url": art.url,
                        "source_name": art.source.source_name if art.source else None,
                        "published_date": art.published_date.isoformat() if getattr(art, "published_date", None) else None,
                    }

            # Phase 5: Political Funding & Donors
            elif phase == "PHASE_5" or entity_type_str in ("POLITICAL_PARTY", "DONOR_ENTITY", "FUNDING_DISCLOSURE"):
                from backend.models.funding import PoliticalParty, FinancialDocument
                party = session.query(PoliticalParty).filter(
                    or_(PoliticalParty.party_id == cid, PoliticalParty.party_name.ilike(f"%{node.label}%"))
                ).first()
                if party:
                    resolved_record["module_data"] = {
                        "party_id": party.party_id,
                        "party_name": party.party_name,
                        "abbreviation": party.abbreviation,
                    }

            # Phase 6: Public Claims & Fact Checks
            elif phase == "PHASE_6" or entity_type_str == "CLAIM":
                from backend.models.claim import Claim
                claim = session.query(Claim).filter(
                    or_(Claim.claim_id == cid, Claim.original_text.ilike(f"%{node.label}%"))
                ).first()
                if claim:
                    resolved_record["module_data"] = {
                        "claim_id": claim.claim_id,
                        "claim_text": claim.original_text,
                        "status": claim.status.value if hasattr(claim.status, "value") else str(claim.status),
                        "speaker_name": claim.speaker_name,
                    }

            # Phase 7: Civic Grievances & Responses
            elif phase == "PHASE_7" or entity_type_str == "CIVIC_ISSUE":
                from backend.models.civic_issue import CivicIssue
                issue = session.query(CivicIssue).filter(
                    or_(CivicIssue.issue_code == cid, CivicIssue.title.ilike(f"%{node.label}%"))
                ).first()
                if issue:
                    resolved_record["module_data"] = {
                        "issue_code": issue.issue_code,
                        "title": issue.title,
                        "description": sanitize_pii(issue.description or "") if not is_auditor else issue.description,
                        "status": issue.status.value if hasattr(issue.status, "value") else str(issue.status),
                    }

            # Phase 8: Representatives & Constituencies
            elif phase == "PHASE_8" or entity_type_str in ("REPRESENTATIVE", "CONSTITUENCY", "PUBLIC_WORK"):
                from backend.models.representative import Representative, Constituency
                rep = session.query(Representative).filter(
                    or_(Representative.representative_id == cid, Representative.official_name.ilike(f"%{node.label}%"))
                ).first()
                if rep:
                    resolved_record["module_data"] = {
                        "representative_id": rep.representative_id,
                        "official_name": rep.official_name,
                        "representative_type": rep.representative_type,
                        "party_id": rep.party_id,
                        "constituency_id": rep.constituency_id,
                    }
                else:
                    const = session.query(Constituency).filter(
                        or_(Constituency.constituency_id == cid, Constituency.name.ilike(f"%{node.label}%"))
                    ).first()
                    if const:
                        resolved_record["module_data"] = {
                            "constituency_id": const.constituency_id,
                            "name": const.name,
                            "constituency_type": const.constituency_type,
                            "district": const.district,
                        }

        except Exception as e:
            logger.warning(f"Failed to resolve original phase record for node {node_id}: {e}")

        # If no specific table matched, provide properties fallback
        if not resolved_record["module_data"]:
            resolved_record["module_data"] = sanitize_payload(node.attributes_json or {}, is_auditor=is_auditor)

        resolved_record["module_data"] = sanitize_payload(resolved_record["module_data"], is_auditor=is_auditor)
        return resolved_record
