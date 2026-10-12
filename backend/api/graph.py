"""
Phase 9.5 — Unified Civic Evidence Graph REST API Router.
=========================================================

Endpoints:
- POST /api/graph/traverse                 General graph path discovery with depth and filters
- GET  /api/graph/investigate/<mode>       Investigation walk templates (promise, claim, civic_issue, representative, funding)
- GET  /api/graph/proposals                List candidate relationship proposals by status
- POST /api/graph/proposals/<id>/confirm   Confirm candidate relationship into verified edge
- POST /api/graph/proposals/<id>/reject    Reject candidate proposal with rationale
- POST /api/graph/proposals/<id>/defer     Defer candidate proposal
- GET  /api/graph/nodes/<id>/edges         Retrieve edges connected to a specific graph node
"""

from __future__ import annotations

import logging
from typing import Any, Dict

from flask import Blueprint, request
from sqlalchemy.orm import Session

from backend.api.responses import error_response, success_response
from backend.database.session import SessionLocal
from backend.models.graph import (
    CivicGraphNode,
    CivicEvidenceEdge,
    CandidateRelationshipProposal,
    CandidateReviewDisposition,
    GraphEntityType,
    GraphRelationshipType,
)
from backend.services.evidence_traversal_engine import EvidenceTraversalEngine, NodeNotFoundError
from backend.services.relationship_discovery_engine import RelationshipDiscoveryEngine, ProposalNotFoundError, EpistemicGuardrailViolation
from backend.services.graph_storage_service import GraphStorageService

logger = logging.getLogger("civiclens.phase9.api.graph")

graph_bp = Blueprint("graph", __name__, url_prefix="/graph")


@graph_bp.route("/traverse", methods=["POST"])
def traverse_evidence_paths():
    """
    General depth-bounded evidence path discovery.
    Request JSON:
    {
        "start_node_id": "NODE:...",
        "target_node_id": "NODE:...",        # Optional
        "target_entity_types": [...],        # Optional
        "permitted_relationships": [...],    # Optional
        "direction": "outgoing"|"incoming"|"both",
        "max_depth": 4,
        "max_paths": 20,
        "active_only": true
    }
    """
    data = request.get_json(silent=True) or {}
    start_node_id = data.get("start_node_id")
    if not start_node_id:
        return error_response(message="'start_node_id' is required.", status_code=400)

    db: Session = SessionLocal()
    try:
        paths = EvidenceTraversalEngine.find_paths(
            session=db,
            start_node_id=start_node_id,
            target_node_id=data.get("target_node_id"),
            target_entity_types=data.get("target_entity_types"),
            permitted_relationships=data.get("permitted_relationships"),
            direction=data.get("direction", "outgoing"),
            max_depth=int(data.get("max_depth", 4)),
            max_paths=int(data.get("max_paths", 20)),
            active_only=bool(data.get("active_only", True)),
        )
        return success_response(data={"paths": paths, "total_paths": len(paths)})
    except NodeNotFoundError as e:
        return error_response(message=str(e), status_code=404)
    except Exception as e:
        logger.exception("Error during evidence traversal")
        return error_response(message=f"Traversal failed: {str(e)}", status_code=500)
    finally:
        db.close()


@graph_bp.route("/investigate/<mode>", methods=["GET"])
def investigate_named_path(mode: str):
    """
    Executes a structured investigation template walk:
    - promise: Promise -> Scheme -> Budget -> Implementation
    - claim: Claim -> Evidence -> Verification
    - civic_issue: Issue -> Official Record -> Department Response -> Resolution
    - representative: Representative -> Constituency -> Works / Activities
    - funding: Funding Disclosure -> Party/Donor -> Source Document
    """
    node_id = request.args.get("node_id")
    if not node_id:
        return error_response(message="'node_id' query parameter is required.", status_code=400)

    max_depth = int(request.args.get("max_depth", 4))

    db: Session = SessionLocal()
    try:
        clean_mode = mode.lower().strip()
        if clean_mode in ("promise", "promise_fulfillment"):
            paths = EvidenceTraversalEngine.investigate_promise_fulfillment(db, node_id, max_depth)
        elif clean_mode in ("claim", "claim_veracity"):
            paths = EvidenceTraversalEngine.investigate_claim_veracity(db, node_id, max_depth)
        elif clean_mode in ("civic_issue", "issue", "civic_issue_resolution"):
            paths = EvidenceTraversalEngine.investigate_civic_issue_resolution(db, node_id, max_depth)
        elif clean_mode in ("representative", "representative_works"):
            paths = EvidenceTraversalEngine.investigate_representative_works(db, node_id, max_depth)
        elif clean_mode in ("funding", "funding_lineage"):
            paths = EvidenceTraversalEngine.investigate_funding_lineage(db, node_id, max_depth)
        else:
            return error_response(
                message=f"Unknown investigation mode '{mode}'. Choose from: promise, claim, civic_issue, representative, funding.",
                status_code=400,
            )

        return success_response(data={"mode": mode, "node_id": node_id, "paths": paths, "total_paths": len(paths)})
    except NodeNotFoundError as e:
        return error_response(message=str(e), status_code=404)
    finally:
        db.close()


@graph_bp.route("/proposals", methods=["GET"])
def list_proposals():
    """List candidate relationship proposals."""
    status_str = request.args.get("status")
    min_confidence = float(request.args.get("min_confidence", 0.0))
    source_node_id = request.args.get("source_node_id")
    target_node_id = request.args.get("target_node_id")

    status = None
    if status_str:
        try:
            status = CandidateReviewDisposition(status_str.upper())
        except ValueError:
            return error_response(message=f"Invalid status '{status_str}'", status_code=400)

    db: Session = SessionLocal()
    try:
        proposals = RelationshipDiscoveryEngine.list_proposals(
            session=db,
            review_status=status,
            min_confidence=min_confidence,
            source_node_id=source_node_id,
            target_node_id=target_node_id,
        )
        return success_response(data={"proposals": [p.to_dict() for p in proposals], "total": len(proposals)})
    finally:
        db.close()


@graph_bp.route("/proposals/<proposal_id>/confirm", methods=["POST"])
def confirm_proposal(proposal_id: str):
    """Confirm candidate proposal and promote to verified CivicEvidenceEdge."""
    data = request.get_json(silent=True) or {}
    reviewer_id = data.get("reviewer_id", "SYSTEM_REVIEWER")
    notes = data.get("reviewer_notes", "Confirmed via API review")
    override_rel = data.get("relationship_type")

    db: Session = SessionLocal()
    try:
        prop, edge = RelationshipDiscoveryEngine.confirm_candidate(
            session=db,
            proposal_id=proposal_id,
            reviewer_id=reviewer_id,
            reviewer_notes=notes,
            override_relationship_type=override_rel,
        )
        db.commit()
        return success_response(data={"proposal": prop.to_dict(), "confirmed_edge": edge.to_dict()})
    except ProposalNotFoundError as e:
        return error_response(message=str(e), status_code=404)
    except EpistemicGuardrailViolation as e:
        return error_response(message=str(e), status_code=422)
    finally:
        db.close()


@graph_bp.route("/proposals/<proposal_id>/reject", methods=["POST"])
def reject_proposal(proposal_id: str):
    """Reject candidate proposal."""
    data = request.get_json(silent=True) or {}
    reviewer_id = data.get("reviewer_id", "SYSTEM_REVIEWER")
    notes = data.get("reviewer_notes", "Rejected via API review")

    db: Session = SessionLocal()
    try:
        prop = RelationshipDiscoveryEngine.reject_candidate(
            session=db,
            proposal_id=proposal_id,
            reviewer_id=reviewer_id,
            reviewer_notes=notes,
        )
        db.commit()
        return success_response(data={"proposal": prop.to_dict()})
    except ProposalNotFoundError as e:
        return error_response(message=str(e), status_code=404)
    finally:
        db.close()


@graph_bp.route("/nodes/<node_id>/edges", methods=["GET"])
def get_node_edges_endpoint(node_id: str):
    """Retrieve edges connected to a node."""
    direction = request.args.get("direction", "both")
    rel_type = request.args.get("relationship_type")
    active_only = request.args.get("active_only", "true").lower() == "true"

    db: Session = SessionLocal()
    try:
        edges = GraphStorageService.get_node_edges(
            session=db,
            node_id=node_id,
            direction=direction,
            relationship_type=rel_type,
            active_only=active_only,
        )
        return success_response(data={"node_id": node_id, "edges": [e.to_dict() for e in edges], "total": len(edges)})
    finally:
        db.close()
