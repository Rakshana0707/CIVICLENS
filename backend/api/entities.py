"""
Phase 9.2 — Cross-Phase Entity Registry & Resolution REST API Router.
=====================================================================

Endpoints:
- GET  /api/entities/lookup                  Disambiguated entity lookup by name, alias, or source ID
- GET  /api/entities/<entity_id>             Fetch full canonical entity profile, aliases, and source mappings
- GET  /api/entities/<entity_id>/history     Retrieve full immutable audit ledger for merges, splits, and updates
- GET  /api/entities/duplicates              Retrieve detected duplicate pairs and uncertain matches
- POST /api/entities/merge                   Merge two canonical entities with mandatory rationale and audit record
- POST /api/entities/split                   Split an entity into two distinct entities with audit log
- POST /api/entities/candidates/<cand_id>/review  Human review of uncertain match candidates
"""

from __future__ import annotations

import logging
from typing import Any, Dict

from flask import Blueprint, request
from sqlalchemy.orm import Session

from backend.api.responses import error_response, success_response
from backend.database.session import SessionLocal
from backend.models.entity_registry import (
    CanonicalEntity,
    DuplicateCandidateReview,
    DuplicateReviewStatus,
    EntityAuditRecord,
    RegistryEntityType,
)
from backend.services.entity_resolution_service import EntityResolutionService

logger = logging.getLogger("civiclens.phase9.api.entities")

entities_bp = Blueprint("entities", __name__, url_prefix="/entities")


@entities_bp.route("/lookup", methods=["GET"])
def lookup_entity():
    """
    Looks up a canonical entity across Phase 1–8 records with multilingual support,
    alias matching, and contextual disambiguation.
    """
    query_name = request.args.get("name", "").strip()
    entity_type_str = request.args.get("type", "").strip()
    source_system = request.args.get("source_system", "").strip() or None
    source_record_id = request.args.get("source_record_id", "").strip() or None
    district = request.args.get("district", "").strip() or None
    party = request.args.get("party", "").strip() or None
    year = request.args.get("year", "").strip() or None

    if not query_name and not (source_system and source_record_id):
        return error_response(
            message="Either 'name' or both 'source_system' and 'source_record_id' must be provided.",
            status_code=400,
        )

    entity_type = None
    if entity_type_str:
        try:
            entity_type = RegistryEntityType.from_string(entity_type_str)
        except ValueError:
            return error_response(
                message=f"Invalid entity type: {entity_type_str}",
                status_code=400,
            )

    context = {}
    if district:
        context["district"] = district
    if party:
        context["party"] = party
    if year:
        context["year"] = year

    db: Session = SessionLocal()
    try:
        service = EntityResolutionService(db)
        result = service.resolve_entity(
            query_name=query_name,
            entity_type=entity_type,
            source_system=source_system,
            source_record_id=source_record_id,
            context=context,
        )
        return success_response(data=result, message="Entity resolution evaluated.")
    except Exception as e:
        logger.error(f"Entity lookup failed: {e}", exc_info=True)
        return error_response(message="Failed to resolve entity.", error_details=str(e), status_code=500)
    finally:
        db.close()


@entities_bp.route("/<entity_id>", methods=["GET"])
def get_entity_profile(entity_id: str):
    """
    Returns full profile of a canonical entity, including aliases and source identifier mappings.
    """
    db: Session = SessionLocal()
    try:
        entity = db.query(CanonicalEntity).filter_by(entity_id=entity_id).first()
        if not entity:
            return error_response(message=f"Entity '{entity_id}' not found.", status_code=404)

        data = entity.to_dict()
        data["aliases"] = [a.to_dict() for a in entity.aliases]
        data["source_mappings"] = [m.to_dict() for m in entity.source_mappings]
        return success_response(data=data, message="Canonical entity profile retrieved.")
    finally:
        db.close()


@entities_bp.route("/<entity_id>/history", methods=["GET"])
def get_entity_audit_history(entity_id: str):
    """
    Returns immutable audit ledger records for merges, splits, and updates on an entity.
    """
    db: Session = SessionLocal()
    try:
        records = (
            db.query(EntityAuditRecord)
            .filter_by(primary_entity_id=entity_id)
            .order_by(EntityAuditRecord.timestamp.desc())
            .all()
        )
        return success_response(
            data={"entity_id": entity_id, "audit_records": [r.to_dict() for r in records]},
            message="Entity audit history retrieved.",
        )
    finally:
        db.close()


@entities_bp.route("/duplicates", methods=["GET"])
def list_duplicate_candidates():
    """
    Returns potential duplicate pairs detected across canonical entities.
    """
    entity_type_str = request.args.get("type", "").strip()
    entity_type = None
    if entity_type_str:
        try:
            entity_type = RegistryEntityType.from_string(entity_type_str)
        except ValueError:
            return error_response(message=f"Invalid entity type: {entity_type_str}", status_code=400)

    db: Session = SessionLocal()
    try:
        service = EntityResolutionService(db)
        candidates = service.detect_duplicate_candidates(entity_type=entity_type)
        return success_response(
            data={"count": len(candidates), "candidates": candidates},
            message="Duplicate candidates scanned.",
        )
    finally:
        db.close()


@entities_bp.route("/merge", methods=["POST"])
def merge_entities():
    """
    Merges two canonical entities into one. Primary entity survives and inherits mappings.
    Requires mandatory rationale and actor identification.
    """
    payload = request.get_json() or {}
    primary_id = payload.get("primary_entity_id")
    secondary_id = payload.get("secondary_entity_id")
    rationale = payload.get("rationale")
    performed_by = payload.get("performed_by", "CIVIC_AUDITOR")

    if not primary_id or not secondary_id or not rationale:
        return error_response(
            message="Fields 'primary_entity_id', 'secondary_entity_id', and 'rationale' are required.",
            status_code=400,
        )

    db: Session = SessionLocal()
    try:
        service = EntityResolutionService(db)
        result = service.merge_entities(
            primary_entity_id=primary_id,
            secondary_entity_id=secondary_id,
            rationale=rationale,
            performed_by=performed_by,
        )
        return success_response(data=result, message="Entities merged successfully.")
    except ValueError as ve:
        return error_response(message=str(ve), status_code=400)
    except Exception as e:
        logger.error(f"Merge error: {e}", exc_info=True)
        return error_response(message="Failed to merge entities.", error_details=str(e), status_code=500)
    finally:
        db.close()


@entities_bp.route("/split", methods=["POST"])
def split_entity():
    """
    Splits an over-aggregated entity into two distinct entities with complete audit history.
    """
    payload = request.get_json() or {}
    original_id = payload.get("original_entity_id")
    new_entity_data = payload.get("new_entity_data")
    split_mapping_ids = payload.get("split_mapping_ids", [])
    rationale = payload.get("rationale")
    performed_by = payload.get("performed_by", "CIVIC_AUDITOR")

    if not original_id or not new_entity_data or not rationale:
        return error_response(
            message="Fields 'original_entity_id', 'new_entity_data', and 'rationale' are required.",
            status_code=400,
        )

    db: Session = SessionLocal()
    try:
        service = EntityResolutionService(db)
        result = service.split_entity(
            original_entity_id=original_id,
            new_entity_data=new_entity_data,
            split_mapping_ids=split_mapping_ids,
            rationale=rationale,
            performed_by=performed_by,
        )
        return success_response(data=result, message="Entity split successfully.")
    except ValueError as ve:
        return error_response(message=str(ve), status_code=400)
    except Exception as e:
        logger.error(f"Split error: {e}", exc_info=True)
        return error_response(message="Failed to split entity.", error_details=str(e), status_code=500)
    finally:
        db.close()


@entities_bp.route("/candidates/<candidate_id>/review", methods=["POST"])
def review_candidate(candidate_id: str):
    """
    Records expert human review on an uncertain match candidate pair.
    """
    payload = request.get_json() or {}
    disposition_str = payload.get("disposition")
    reviewer = payload.get("reviewed_by", "EXPERT_AUDITOR")
    notes = payload.get("notes")

    if not disposition_str:
        return error_response(message="Field 'disposition' is required.", status_code=400)

    try:
        disposition = DuplicateReviewStatus(disposition_str)
    except ValueError:
        return error_response(
            message=f"Invalid disposition: {disposition_str}. Allowed: {[s.value for s in DuplicateReviewStatus]}",
            status_code=400,
        )

    db: Session = SessionLocal()
    try:
        service = EntityResolutionService(db)
        result = service.review_duplicate_candidate(
            candidate_id=candidate_id,
            disposition=disposition,
            reviewer=reviewer,
            notes=notes,
        )
        return success_response(data=result, message="Candidate review recorded.")
    except ValueError as ve:
        return error_response(message=str(ve), status_code=400)
    except Exception as e:
        logger.error(f"Review error: {e}", exc_info=True)
        return error_response(message="Failed to record review.", error_details=str(e), status_code=500)
    finally:
        db.close()
