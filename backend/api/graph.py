"""
Phase 9.7 — Unified Civic Search and Evidence Graph REST API Router.
=====================================================================

Provides comprehensive public transparency and review operations:
1.  GET  /api/graph/entities/search           Search canonical entities across Phases 1–8
2.  GET  /api/graph/nodes/<id>                Retrieve canonical entity node and source mappings
3.  GET  /api/graph/nodes/<id>/neighbors      Retrieve directly connected neighbor entities and edges
4.  POST /api/graph/traverse                  Traverse explainable evidence paths with depth limits
5.  GET  /api/graph/investigate/<mode>        Investigation walk templates across Phases 1–8
6.  GET  /api/graph/edges                     Filter evidence edges by type, source, and review status
7.  GET  /api/graph/edges/<id>                Retrieve evidence and 9-factor scorecard for an edge
8.  GET  /api/graph/proposals/unresolved      List pending relationship proposals discovered across phases
9.  GET  /api/graph/conflicts                 Retrieve detected / persistent evidentiary conflicts
10. GET  /api/graph/disputes                  Retrieve disputed or contradictory records
11. GET  /api/graph/history                   Retrieve immutable graph provenance and review history
12. GET  /api/graph/nodes/<id>/history        Retrieve review history for a specific entity node
13. GET  /api/graph/nodes/<id>/original-record Dynamically view underlying Phase 1–8 module record
14. POST /api/graph/proposals/<id>/confirm    Confirm candidate relationship (Requires review authorization)
15. POST /api/graph/proposals/<id>/reject     Reject candidate proposal (Requires review authorization)
16. POST /api/graph/proposals/<id>/defer      Defer candidate proposal (Requires review authorization)
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

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
from backend.services.evidence_traversal_engine import (
    EvidenceTraversalEngine,
    NodeNotFoundError as TraversalNodeNotFoundError,
)
from backend.services.relationship_discovery_engine import (
    RelationshipDiscoveryEngine,
    ProposalNotFoundError,
    EpistemicGuardrailViolation,
)
from backend.services.graph_storage_service import GraphStorageService
from backend.services.evidence_quality_service import EvidenceQualityService
from backend.services.civic_search_service import (
    UnifiedCivicSearchService,
    NodeNotFoundError,
    EdgeNotFoundError,
    verify_graph_authorization,
    AUTHORIZED_GRAPH_ROLES,
)
from backend.services.investigation_service import CrossPhaseInvestigationService

logger = logging.getLogger("civiclens.phase9.api.graph")

graph_bp = Blueprint("graph", __name__, url_prefix="/graph")


def _get_auth_role() -> Optional[str]:
    """Extracts reviewer role from request header or request body."""
    role = request.headers.get("X-Reviewer-Role")
    if not role and request.is_json:
        body = request.get_json(silent=True) or {}
        role = body.get("reviewer_role")
    return role


# ---------------------------------------------------------------------------
# 1. Search Canonical Entities Across Phases 1–8
# ---------------------------------------------------------------------------
@graph_bp.route("/entities/search", methods=["GET"])
@graph_bp.route("/search/entities", methods=["GET"])
def search_entities_endpoint():
    """
    Operation 1: Searches canonical entities across Phases 1–8.
    Query params: q, entity_type, phase, min_confidence, limit, offset.
    """
    query = request.args.get("q") or request.args.get("query")
    entity_type = request.args.get("entity_type")
    phase = request.args.get("phase") or request.args.get("source_phase")
    
    try:
        min_confidence = float(request.args.get("min_confidence", 0.0))
        limit = int(request.args.get("limit", 20))
        offset = int(request.args.get("offset", 0))
    except ValueError:
        return error_response(message="Invalid numeric parameter for min_confidence, limit, or offset.", status_code=400)

    db: Session = SessionLocal()
    try:
        data = UnifiedCivicSearchService.search_entities(
            session=db,
            query=query,
            entity_type=entity_type,
            source_phase=phase,
            min_confidence=min_confidence,
            limit=limit,
            offset=offset,
        )
        return success_response(data=data, message="Canonical entities retrieved.")
    finally:
        db.close()


# ---------------------------------------------------------------------------
# 2. Retrieve Entity and Its Source Records
# ---------------------------------------------------------------------------
@graph_bp.route("/nodes/<node_id>", methods=["GET"])
def get_node_endpoint(node_id: str):
    """
    Operation 2: Retrieves canonical entity node, source mappings, and connected edge summary.
    """
    role = _get_auth_role()
    is_auditor = role in ("ADMIN", "AUDITOR")

    db: Session = SessionLocal()
    try:
        data = UnifiedCivicSearchService.get_entity_profile(
            session=db, node_id=node_id, is_auditor=is_auditor
        )
        return success_response(data=data, message="Entity profile retrieved.")
    except NodeNotFoundError as e:
        return error_response(message=str(e), status_code=404)
    finally:
        db.close()


# ---------------------------------------------------------------------------
# 3. Retrieve Directly Connected Entities
# ---------------------------------------------------------------------------
@graph_bp.route("/nodes/<node_id>/neighbors", methods=["GET"])
@graph_bp.route("/nodes/<node_id>/connected-entities", methods=["GET"])
def get_connected_entities_endpoint(node_id: str):
    """
    Operation 3: Retrieves directly connected neighbor entities and their linking evidence edges.
    Query params: direction (both|outgoing|incoming), relationship_type, target_type, limit, offset.
    """
    direction = request.args.get("direction", "both")
    rel_type = request.args.get("relationship_type")
    target_type = request.args.get("target_type")

    try:
        limit = int(request.args.get("limit", 20))
        offset = int(request.args.get("offset", 0))
    except ValueError:
        return error_response(message="Invalid numeric parameter for limit or offset.", status_code=400)

    db: Session = SessionLocal()
    try:
        data = UnifiedCivicSearchService.get_connected_entities(
            session=db,
            node_id=node_id,
            direction=direction,
            relationship_type=rel_type,
            target_type=target_type,
            limit=limit,
            offset=offset,
        )
        return success_response(data=data, message="Connected entities retrieved.")
    except NodeNotFoundError as e:
        return error_response(message=str(e), status_code=404)
    finally:
        db.close()


# ---------------------------------------------------------------------------
# 4. Traverse Evidence Paths
# ---------------------------------------------------------------------------
@graph_bp.route("/traverse", methods=["POST"])
def traverse_evidence_paths():
    """
    Operation 4: General depth-bounded evidence path discovery.
    """
    data = request.get_json(silent=True) or {}
    start_node_id = data.get("start_node_id")
    if not start_node_id:
        return error_response(message="'start_node_id' is required.", status_code=400)

    try:
        max_depth = int(data.get("max_depth", 4))
        max_paths = int(data.get("max_paths", 20))
    except (ValueError, TypeError):
        return error_response(message="Invalid max_depth or max_paths parameters.", status_code=400)

    if max_depth < 1 or max_depth > 10:
        return error_response(message="max_depth must be between 1 and 10.", status_code=400)
    if max_paths < 1 or max_paths > 50:
        return error_response(message="max_paths must be between 1 and 50.", status_code=400)

    db: Session = SessionLocal()
    try:
        paths = EvidenceTraversalEngine.find_paths(
            session=db,
            start_node_id=start_node_id,
            target_node_id=data.get("target_node_id"),
            target_entity_types=data.get("target_entity_types"),
            permitted_relationships=data.get("permitted_relationships"),
            direction=data.get("direction", "outgoing"),
            max_depth=max_depth,
            max_paths=max_paths,
            active_only=bool(data.get("active_only", True)),
        )
        return success_response(data={"paths": paths, "total_paths": len(paths)})
    except (NodeNotFoundError, TraversalNodeNotFoundError) as e:
        return error_response(message=str(e), status_code=404)
    except Exception as e:
        logger.exception("Error during evidence traversal")
        return error_response(message=f"Traversal failed: {str(e)}", status_code=500)
    finally:
        db.close()


@graph_bp.route("/investigate/<mode>", methods=["GET"])
def investigate_named_path(mode: str):
    """
    Operation 4 Template Walks:
    - promise: Promise -> Scheme -> Budget -> Implementation
    - claim: Claim -> Evidence -> Verification
    - civic_issue: Issue -> Official Record -> Department Response -> Resolution
    - representative: Representative -> Constituency -> Works / Activities
    - funding: Funding Disclosure -> Party/Donor -> Source Document
    """
    node_id = request.args.get("node_id")
    if not node_id:
        return error_response(message="'node_id' query parameter is required.", status_code=400)

    try:
        max_depth = int(request.args.get("max_depth", 4))
    except ValueError:
        return error_response(message="Invalid max_depth parameter.", status_code=400)

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
    except (NodeNotFoundError, TraversalNodeNotFoundError) as e:
        return error_response(message=str(e), status_code=404)
    finally:
        db.close()


# ---------------------------------------------------------------------------
# 5. Filter by Relationship Type and Source
# ---------------------------------------------------------------------------
@graph_bp.route("/edges", methods=["GET"])
def filter_edges_endpoint():
    """
    Operation 5: Filters evidence edges by relationship type, source document, matching method, and status.
    Query params: relationship_type, source_phase, source_document_id, matching_method, review_status, min_confidence, source_node_id, target_node_id, limit, offset.
    """
    rel_type = request.args.get("relationship_type")
    source_phase = request.args.get("source_phase")
    doc_id = request.args.get("source_document_id")
    method = request.args.get("matching_method")
    status = request.args.get("review_status")
    src_node = request.args.get("source_node_id")
    tgt_node = request.args.get("target_node_id")

    try:
        min_conf = float(request.args.get("min_confidence", 0.0))
        limit = int(request.args.get("limit", 20))
        offset = int(request.args.get("offset", 0))
    except ValueError:
        return error_response(message="Invalid numeric parameter for min_confidence, limit, or offset.", status_code=400)

    db: Session = SessionLocal()
    try:
        data = UnifiedCivicSearchService.filter_edges(
            session=db,
            relationship_type=rel_type,
            source_phase=source_phase,
            source_document_id=doc_id,
            matching_method=method,
            review_status=status,
            min_confidence=min_conf,
            source_node_id=src_node,
            target_node_id=tgt_node,
            limit=limit,
            offset=offset,
        )
        return success_response(data=data, message="Edges filtered.")
    finally:
        db.close()


# ---------------------------------------------------------------------------
# 6. Retrieve Evidence for an Individual Relationship
# ---------------------------------------------------------------------------
@graph_bp.route("/edges/<edge_id>", methods=["GET"])
def get_edge_evidence_endpoint(edge_id: str):
    """
    Operation 6: Retrieves evidence, provenance, and 9-factor scorecard for an individual edge.
    """
    db: Session = SessionLocal()
    try:
        data = UnifiedCivicSearchService.get_edge_evidence(session=db, edge_id=edge_id)
        return success_response(data=data, message="Edge evidence retrieved.")
    except EdgeNotFoundError as e:
        return error_response(message=str(e), status_code=404)
    finally:
        db.close()


@graph_bp.route("/edges/<edge_id>/quality", methods=["GET"])
def get_edge_quality_endpoint(edge_id: str):
    """
    Retrieves multi-factor evidence quality scorecard for an edge.
    """
    db: Session = SessionLocal()
    try:
        edge = GraphStorageService.get_edge(db, edge_id)
        if not edge:
            return error_response(message=f"Edge '{edge_id}' not found.", status_code=404)
        scorecard = EvidenceQualityService.assess_edge_evidence_quality(edge)
        return success_response(data={"scorecard": scorecard})
    finally:
        db.close()


# ---------------------------------------------------------------------------
# 7. List Unresolved Relationship Candidates
# ---------------------------------------------------------------------------
@graph_bp.route("/proposals/unresolved", methods=["GET"])
def list_unresolved_proposals():
    """
    Operation 7: Lists pending relationship candidates discovered across Phase 1–8 records.
    Query params: min_confidence, source_node_id, target_node_id, limit, offset.
    """
    src_node = request.args.get("source_node_id")
    tgt_node = request.args.get("target_node_id")

    try:
        min_conf = float(request.args.get("min_confidence", 0.0))
        limit = int(request.args.get("limit", 20))
        offset = int(request.args.get("offset", 0))
    except ValueError:
        return error_response(message="Invalid numeric parameter for min_confidence, limit, or offset.", status_code=400)

    db: Session = SessionLocal()
    try:
        data = UnifiedCivicSearchService.get_unresolved_proposals(
            session=db,
            min_confidence=min_conf,
            source_node_id=src_node,
            target_node_id=tgt_node,
            limit=limit,
            offset=offset,
        )
        return success_response(data=data, message="Unresolved proposals retrieved.")
    finally:
        db.close()


@graph_bp.route("/proposals", methods=["GET"])
def list_proposals():
    """List candidate relationship proposals with status filter."""
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


# ---------------------------------------------------------------------------
# 8. Retrieve Contradictory or Disputed Evidence
# ---------------------------------------------------------------------------
@graph_bp.route("/conflicts", methods=["GET"])
@graph_bp.route("/disputes", methods=["GET"])
def get_conflicts_endpoint():
    """
    Operation 8: Detects and retrieves contradictory, disputed, or incompatible evidence records.
    Query params: node_id, conflict_type, severity, resolution_status, limit, offset.
    """
    node_id = request.args.get("node_id")
    conflict_type = request.args.get("conflict_type")
    severity = request.args.get("severity")
    res_status = request.args.get("resolution_status")

    try:
        limit = int(request.args.get("limit", 20))
        offset = int(request.args.get("offset", 0))
    except ValueError:
        return error_response(message="Invalid numeric parameter for limit or offset.", status_code=400)

    db: Session = SessionLocal()
    try:
        # Detect and persist conflicts for the queried node or graph
        EvidenceQualityService.detect_conflicts(session=db, node_id=node_id, persist_records=True)
        db.commit()

        data = UnifiedCivicSearchService.get_conflicts_and_disputes(
            session=db,
            node_id=node_id,
            conflict_type=conflict_type,
            severity=severity,
            resolution_status=res_status,
            limit=limit,
            offset=offset,
        )
        data["total"] = data.get("total_conflicts", len(data.get("conflicts", [])))
        return success_response(data=data, message="Evidentiary conflicts and disputes retrieved.")
    finally:
        db.close()


# ---------------------------------------------------------------------------
# 9. Retrieve Graph Provenance and Review History
# ---------------------------------------------------------------------------
@graph_bp.route("/history", methods=["GET"])
@graph_bp.route("/provenance/history", methods=["GET"])
@graph_bp.route("/nodes/<node_id>/history", methods=["GET"])
def get_history_endpoint(node_id: Optional[str] = None):
    """
    Operation 9: Retrieves immutable graph provenance, review decisions, and entity mutation history.
    Query params: edge_id, reviewer_id, action, limit, offset.
    """
    edge_id = request.args.get("edge_id")
    reviewer_id = request.args.get("reviewer_id")
    action = request.args.get("action")

    try:
        limit = int(request.args.get("limit", 20))
        offset = int(request.args.get("offset", 0))
    except ValueError:
        return error_response(message="Invalid numeric parameter for limit or offset.", status_code=400)

    db: Session = SessionLocal()
    try:
        data = UnifiedCivicSearchService.get_graph_history(
            session=db,
            node_id=node_id,
            edge_id=edge_id,
            reviewer_id=reviewer_id,
            action=action,
            limit=limit,
            offset=offset,
        )
        return success_response(data=data, message="Provenance and review history retrieved.")
    finally:
        db.close()


# ---------------------------------------------------------------------------
# 10. View Relevant Records from the Original Phase Modules
# ---------------------------------------------------------------------------
@graph_bp.route("/nodes/<node_id>/original-record", methods=["GET"])
def get_original_record_endpoint(node_id: str):
    """
    Operation 10: Dynamically retrieves underlying Phase 1–8 module records with PII scrubbing.
    """
    role = _get_auth_role()
    is_auditor = role in ("ADMIN", "AUDITOR")

    db: Session = SessionLocal()
    try:
        data = UnifiedCivicSearchService.get_original_phase_record(
            session=db, node_id=node_id, is_auditor=is_auditor
        )
        return success_response(data=data, message="Original phase record resolved.")
    except NodeNotFoundError as e:
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


@graph_bp.route("/nodes/<node_id>/completeness", methods=["GET"])
def get_node_completeness_endpoint(node_id: str):
    """Retrieve evidence completeness assessment for a node."""
    db: Session = SessionLocal()
    try:
        completeness = EvidenceQualityService.assess_evidence_completeness(db, node_id)
        return success_response(data={"completeness": completeness})
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Privileged Mutation Endpoints: Candidate Review Workflow with Authorization
# ---------------------------------------------------------------------------
@graph_bp.route("/proposals/<proposal_id>/confirm", methods=["POST"])
def confirm_proposal(proposal_id: str):
    """
    Confirm candidate proposal and promote to verified CivicEvidenceEdge.
    Requires reviewer role in AUTHORIZED_GRAPH_ROLES.
    """
    role = _get_auth_role()
    is_auth, auth_err = verify_graph_authorization(role)
    if not is_auth:
        return error_response(message=auth_err, status_code=403)

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
    """
    Reject candidate proposal with mandatory rationale.
    Requires reviewer role in AUTHORIZED_GRAPH_ROLES.
    """
    role = _get_auth_role()
    is_auth, auth_err = verify_graph_authorization(role)
    if not is_auth:
        return error_response(message=auth_err, status_code=403)

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


@graph_bp.route("/proposals/<proposal_id>/defer", methods=["POST"])
def defer_proposal(proposal_id: str):
    """
    Defer candidate proposal for additional evidence gathering.
    Requires reviewer role in AUTHORIZED_GRAPH_ROLES.
    """
    role = _get_auth_role()
    is_auth, auth_err = verify_graph_authorization(role)
    if not is_auth:
        return error_response(message=auth_err, status_code=403)

    data = request.get_json(silent=True) or {}
    reviewer_id = data.get("reviewer_id", "SYSTEM_REVIEWER")
    notes = data.get("reviewer_notes", "Deferred via API review")

    db: Session = SessionLocal()
    try:
        prop = RelationshipDiscoveryEngine.defer_candidate(
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


# ===========================================================================
# PHASE 9.9: CROSS-PHASE INVESTIGATION WORKFLOWS AND AUDITABILITY
# ===========================================================================

@graph_bp.route("/investigate/workflow-a/promise", methods=["GET"])
def investigate_workflow_a_promise():
    """
    Workflow A: Select a political promise, inspect related schemes and budgets,
    then review available implementation and claim evidence.
    Query params: id (promise node ID or canonical ID)
    """
    identifier = request.args.get("id")
    if not identifier:
        return error_response(message="Parameter 'id' is required for Workflow A.", status_code=400)

    db: Session = SessionLocal()
    try:
        data = CrossPhaseInvestigationService.investigate_promise_delivery(identifier=identifier, session=db)
        return success_response(data=data)
    finally:
        db.close()


@graph_bp.route("/investigate/workflow-b/civic-issue", methods=["GET"])
def investigate_workflow_b_civic_issue():
    """
    Workflow B: Select a civic issue, inspect its original public record, department response,
    reported status, and resolution evidence.
    Query params: id (civic issue node ID or code)
    """
    identifier = request.args.get("id")
    if not identifier:
        return error_response(message="Parameter 'id' is required for Workflow B.", status_code=400)

    db: Session = SessionLocal()
    try:
        data = CrossPhaseInvestigationService.investigate_civic_issue_resolution(identifier=identifier, session=db)
        return success_response(data=data)
    finally:
        db.close()


@graph_bp.route("/investigate/workflow-c/claim", methods=["GET"])
def investigate_workflow_c_claim():
    """
    Workflow C: Select a public claim and explore supporting, contradicting, and contextual records.
    Query params: id (claim node ID or text)
    """
    identifier = request.args.get("id")
    if not identifier:
        return error_response(message="Parameter 'id' is required for Workflow C.", status_code=400)

    db: Session = SessionLocal()
    try:
        data = CrossPhaseInvestigationService.investigate_claim_dialectics(identifier=identifier, session=db)
        return success_response(data=data)
    finally:
        db.close()


@graph_bp.route("/investigate/workflow-d/representative", methods=["GET"])
def investigate_workflow_d_representative():
    """
    Workflow D: Select a representative and inspect documented constituency, legislative,
    scheme, and public-work records without assuming personal responsibility for every associated outcome.
    Query params: id (representative node ID or name)
    """
    identifier = request.args.get("id")
    if not identifier:
        return error_response(message="Parameter 'id' is required for Workflow D.", status_code=400)

    db: Session = SessionLocal()
    try:
        data = CrossPhaseInvestigationService.investigate_representative_stewardship(identifier=identifier, session=db)
        return success_response(data=data)
    finally:
        db.close()


@graph_bp.route("/investigate/workflow-e/funding", methods=["GET"])
def investigate_workflow_e_funding():
    """
    Workflow E: Select a disclosed political funding record and inspect its original document
    and supported entity relationships without inferring wrongdoing.
    Query params: id (party/donor node ID or code)
    """
    identifier = request.args.get("id")
    if not identifier:
        return error_response(message="Parameter 'id' is required for Workflow E.", status_code=400)

    db: Session = SessionLocal()
    try:
        data = CrossPhaseInvestigationService.investigate_political_finance(identifier=identifier, session=db)
        return success_response(data=data)
    finally:
        db.close()


@graph_bp.route("/investigate/report/export", methods=["GET"])
def export_investigation_report_endpoint():
    """
    Exports a source-linked, verifiable investigation report.
    Query params: workflow, id, format (json or markdown)
    """
    workflow = request.args.get("workflow", "workflow_a")
    identifier = request.args.get("id")
    fmt = request.args.get("format", "json").lower()

    if not identifier:
        return error_response(message="Parameter 'id' is required for report export.", status_code=400)

    db: Session = SessionLocal()
    try:
        report = CrossPhaseInvestigationService.export_investigation_report(
            workflow_type=workflow,
            identifier=identifier,
            format=fmt,
            session=db,
        )
        if fmt == "markdown":
            return success_response(data={"report_markdown": report, "format": "markdown"})
        return success_response(data=report)
    except ValueError as e:
        return error_response(message=str(e), status_code=400)
    finally:
        db.close()

