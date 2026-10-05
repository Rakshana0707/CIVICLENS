"""
Political Promise Tracker API Blueprint (Phase 3.12).

Provides comprehensive RESTful endpoints for:
- Parties & Elections
- Manifestos (with provenance metadata)
- Promises (filtering by party, election, category, status, classification, language, search)
- Categories (taxonomy & counts)
- Historical Scheme Matches (Phase 3.8 vector/cosine similarity links)
- Evidence & Evidence Matches (Phase 3.9 & Phase 3.10 multi-signal retrieval)
- Assessments & Assessment History (Phase 3.11 status, confidence, rationale, supporting evidence, source links)
- Sources & Provenance Metadata

Design Rules:
- Dynamic database queries (no hardcoded political data).
- Strict pagination, input validation, error handling, and empty-state handling.
"""
from flask import Blueprint, request
from sqlalchemy import func, or_
from sqlalchemy.orm import Session
from datetime import datetime, timezone
import json

from backend.database.session import SessionLocal
from backend.api.responses import success_response, error_response
from backend.models.manifesto import Manifesto, ManifestoSource, ManifestoDocument
from backend.models.promise import (
    PoliticalPromise,
    PromiseCategory,
    PromiseCategoryMapping,
    PromiseEvidenceLink,
    PromiseSchemeLink,
    PromiseAssessment,
    PromiseAssessmentHistory,
    PromiseStatus
)
from backend.models.common import Evidence
from backend.models.budget import HistoricalScheme, BudgetScheme

promises_bp = Blueprint('promises', __name__, url_prefix='/promises')


def get_db():
    return SessionLocal()


def paginate_query(query, page: int, limit: int):
    page = max(1, page)
    limit = max(1, min(100, limit))
    total = query.count()
    items = query.offset((page - 1) * limit).limit(limit).all()
    pages = (total + limit - 1) // limit if total > 0 else 0
    return items, total, page, limit, pages


# ---------------------------------------------------------------------------
# 1. PARTIES
# ---------------------------------------------------------------------------
@promises_bp.route('/parties', methods=['GET'])
def list_parties():
    db: Session = get_db()
    try:
        results = db.query(
            Manifesto.party,
            func.count(func.distinct(Manifesto.manifesto_id)).label('manifesto_count'),
            func.count(PoliticalPromise.promise_id).label('promise_count')
        ).outerjoin(PoliticalPromise, Manifesto.manifesto_id == PoliticalPromise.manifesto_id)\
         .group_by(Manifesto.party).all()

        parties = []
        for r in results:
            parties.append({
                "party": r.party,
                "manifesto_count": r.manifesto_count,
                "promise_count": r.promise_count
            })

        return success_response(data={"parties": parties, "total": len(parties)})
    except Exception as e:
        return error_response(message="Failed to retrieve parties", error_details=str(e), status_code=500)
    finally:
        db.close()


# ---------------------------------------------------------------------------
# 2. ELECTIONS
# ---------------------------------------------------------------------------
@promises_bp.route('/elections', methods=['GET'])
def list_elections():
    db: Session = get_db()
    try:
        results = db.query(
            Manifesto.election_year,
            Manifesto.election,
            func.count(func.distinct(Manifesto.party)).label('party_count'),
            func.count(PoliticalPromise.promise_id).label('promise_count')
        ).outerjoin(PoliticalPromise, Manifesto.manifesto_id == PoliticalPromise.manifesto_id)\
         .group_by(Manifesto.election_year, Manifesto.election).all()

        elections = []
        for r in results:
            elections.append({
                "election_year": r.election_year,
                "election_title": r.election or f"{r.election_year} Assembly Election",
                "party_count": r.party_count,
                "promise_count": r.promise_count
            })

        return success_response(data={"elections": elections, "total": len(elections)})
    except Exception as e:
        return error_response(message="Failed to retrieve elections", error_details=str(e), status_code=500)
    finally:
        db.close()


# ---------------------------------------------------------------------------
# 3. MANIFESTOS
# ---------------------------------------------------------------------------
@promises_bp.route('/manifestos', methods=['GET'])
def list_manifestos():
    db: Session = get_db()
    try:
        party = request.args.get('party')
        year = request.args.get('election_year', type=int)
        page = request.args.get('page', 1, type=int)
        limit = request.args.get('limit', 20, type=int)

        query = db.query(Manifesto)
        if party:
            query = query.filter(Manifesto.party == party)
        if year:
            query = query.filter(Manifesto.election_year == year)

        items, total, page, limit, pages = paginate_query(query, page, limit)

        manifestos = []
        for m in items:
            manifestos.append({
                "manifesto_id": m.manifesto_id,
                "party": m.party,
                "election": m.election,
                "election_year": m.election_year,
                "language": m.language,
                "title": m.title,
                "format": m.format,
                "extraction_status": m.extraction_status,
                "verification_status": m.verification_status,
                "source_id": m.source_id,
                "document_id": m.document_id
            })

        return success_response(data={
            "items": manifestos,
            "total": total,
            "page": page,
            "limit": limit,
            "pages": pages
        })
    except Exception as e:
        return error_response(message="Failed to retrieve manifestos", error_details=str(e), status_code=500)
    finally:
        db.close()


@promises_bp.route('/manifestos/<manifesto_id>', methods=['GET'])
def get_manifesto(manifesto_id: str):
    db: Session = get_db()
    try:
        m = db.query(Manifesto).filter(Manifesto.manifesto_id == manifesto_id).first()
        if not m:
            return error_response(message=f"Manifesto '{manifesto_id}' not found", status_code=404)

        source_data = None
        if m.source:
            source_data = {
                "source_id": m.source.source_id,
                "organization": m.source.organization,
                "source_url": m.source.source_url,
                "source_type": m.source.source_type,
                "source_tier": m.source.source_tier,
                "retrieval_status": m.source.retrieval_status,
                "checksum": m.source.checksum
            }

        document_data = None
        if m.document:
            document_data = {
                "document_id": m.document.document_id,
                "original_filename": m.document.original_filename,
                "file_format": m.document.file_format,
                "file_size": m.document.file_size,
                "storage_path": m.document.storage_path,
                "checksum": m.document.checksum
            }

        return success_response(data={
            "manifesto_id": m.manifesto_id,
            "party": m.party,
            "election": m.election,
            "election_year": m.election_year,
            "language": m.language,
            "title": m.title,
            "source": source_data,
            "document": document_data
        })
    except Exception as e:
        return error_response(message="Failed to retrieve manifesto details", error_details=str(e), status_code=500)
    finally:
        db.close()


# ---------------------------------------------------------------------------
# 4. CATEGORIES
# ---------------------------------------------------------------------------
@promises_bp.route('/categories', methods=['GET'])
def list_categories():
    db: Session = get_db()
    try:
        cats = db.query(PromiseCategory).all()
        categories = []
        for c in cats:
            promise_count = db.query(PromiseCategoryMapping).filter(PromiseCategoryMapping.category_id == c.id).count()
            categories.append({
                "id": c.id,
                "category_code": c.category_code,
                "name": c.name,
                "description": c.description,
                "promise_count": promise_count
            })

        return success_response(data={"categories": categories, "total": len(categories)})
    except Exception as e:
        return error_response(message="Failed to retrieve categories", error_details=str(e), status_code=500)
    finally:
        db.close()


# ---------------------------------------------------------------------------
# 5. PROMISES
# ---------------------------------------------------------------------------
@promises_bp.route('/', methods=['GET'])
def list_promises():
    db: Session = get_db()
    try:
        party = request.args.get('party')
        year = request.args.get('election_year', type=int)
        category_code = request.args.get('category')
        status = request.args.get('status')
        classification = request.args.get('classification')
        language = request.args.get('language')
        search = request.args.get('search')
        page = request.args.get('page', 1, type=int)
        limit = request.args.get('limit', 20, type=int)

        query = db.query(PoliticalPromise).join(Manifesto, PoliticalPromise.manifesto_id == Manifesto.manifesto_id)

        if party:
            query = query.filter(Manifesto.party == party)
        if year:
            query = query.filter(Manifesto.election_year == year)
        if classification:
            query = query.filter(PoliticalPromise.classification == classification)
        if language:
            query = query.filter(PoliticalPromise.language == language)
        if search:
            search_pattern = f"%{search}%"
            query = query.filter(or_(
                PoliticalPromise.original_text.ilike(search_pattern),
                PoliticalPromise.normalized_text.ilike(search_pattern)
            ))
        if category_code:
            query = query.join(PromiseCategoryMapping, PoliticalPromise.promise_id == PromiseCategoryMapping.promise_id)\
                         .join(PromiseCategory, PromiseCategoryMapping.category_id == PromiseCategory.id)\
                         .filter(PromiseCategory.category_code == category_code)
        if status:
            query = query.join(PromiseAssessment, PoliticalPromise.promise_id == PromiseAssessment.promise_id)\
                         .filter(PromiseAssessment.is_current == True, PromiseAssessment.status == status)

        items, total, page, limit, pages = paginate_query(query, page, limit)

        promises = []
        for p in items:
            # Get current assessment status
            curr_assess = db.query(PromiseAssessment).filter(
                PromiseAssessment.promise_id == p.promise_id,
                PromiseAssessment.is_current == True
            ).first()

            status_str = curr_assess.status.value if (curr_assess and hasattr(curr_assess.status, 'value')) else (curr_assess.status if curr_assess else "not_assessed")

            # Get primary category
            primary_cat_map = db.query(PromiseCategoryMapping).filter(
                PromiseCategoryMapping.promise_id == p.promise_id,
                PromiseCategoryMapping.is_primary == True
            ).first()
            primary_cat = primary_cat_map.category.category_code if (primary_cat_map and primary_cat_map.category) else "Uncategorized"

            promises.append({
                "promise_id": p.promise_id,
                "manifesto_id": p.manifesto_id,
                "party": p.manifesto.party if p.manifesto else "Unknown",
                "election_year": p.manifesto.election_year if p.manifesto else None,
                "original_text": p.original_text,
                "normalized_text": p.normalized_text,
                "page_number": p.page_number,
                "section": p.section,
                "language": p.language,
                "classification": p.classification,
                "primary_category": primary_cat,
                "current_status": status_str,
                "metadata": p.metadata_json or {}
            })

        return success_response(data={
            "items": promises,
            "total": total,
            "page": page,
            "limit": limit,
            "pages": pages
        })
    except Exception as e:
        return error_response(message="Failed to retrieve promises", error_details=str(e), status_code=500)
    finally:
        db.close()


@promises_bp.route('/<promise_id>', methods=['GET'])
def get_promise(promise_id: str):
    db: Session = get_db()
    try:
        p = db.query(PoliticalPromise).filter(PoliticalPromise.promise_id == promise_id).first()
        if not p:
            return error_response(message=f"Promise '{promise_id}' not found", status_code=404)

        categories = []
        for cm in p.categories:
            categories.append({
                "category_code": cm.category.category_code,
                "name": cm.category.name,
                "is_primary": cm.is_primary,
                "confidence": cm.confidence
            })

        curr_assess = db.query(PromiseAssessment).filter(
            PromiseAssessment.promise_id == p.promise_id,
            PromiseAssessment.is_current == True
        ).first()

        status_str = curr_assess.status.value if (curr_assess and hasattr(curr_assess.status, 'value')) else (curr_assess.status if curr_assess else "not_assessed")

        return success_response(data={
            "promise_id": p.promise_id,
            "manifesto_id": p.manifesto_id,
            "party": p.manifesto.party if p.manifesto else "Unknown",
            "election_year": p.manifesto.election_year if p.manifesto else None,
            "original_text": p.original_text,
            "normalized_text": p.normalized_text,
            "page_number": p.page_number,
            "section": p.section,
            "language": p.language,
            "classification": p.classification,
            "extraction_confidence": p.extraction_confidence,
            "categories": categories,
            "current_status": status_str,
            "metadata": p.metadata_json or {}
        })
    except Exception as e:
        return error_response(message="Failed to retrieve promise details", error_details=str(e), status_code=500)
    finally:
        db.close()


# ---------------------------------------------------------------------------
# 6. HISTORICAL SCHEME MATCHES
# ---------------------------------------------------------------------------
@promises_bp.route('/<promise_id>/scheme-matches', methods=['GET'])
def get_promise_scheme_matches(promise_id: str):
    db: Session = get_db()
    try:
        p = db.query(PoliticalPromise).filter(PoliticalPromise.promise_id == promise_id).first()
        if not p:
            return error_response(message=f"Promise '{promise_id}' not found", status_code=404)

        links = db.query(PromiseSchemeLink).filter(PromiseSchemeLink.promise_id == promise_id).order_by(PromiseSchemeLink.similarity_score.desc()).all()

        matches = []
        for l in links:
            scheme_info = None
            if l.historical_scheme:
                scheme_info = {
                    "scheme_id": l.historical_scheme.id,
                    "scheme_name": l.historical_scheme.scheme_name,
                    "financial_year": l.historical_scheme.financial_year,
                    "department": l.historical_scheme.department.name if l.historical_scheme.department else "Unknown",
                    "description": l.historical_scheme.description
                }
            matches.append({
                "promise_id": l.promise_id,
                "scheme_id": l.historical_scheme_id or l.budget_scheme_id,
                "similarity_score": l.similarity_score,
                "matching_method": l.matching_method,
                "model_name": l.model_name,
                "model_version": l.model_version,
                "notes": l.notes,
                "scheme_details": scheme_info
            })

        return success_response(data={"promise_id": promise_id, "scheme_matches": matches, "total": len(matches)})
    except Exception as e:
        return error_response(message="Failed to retrieve scheme matches", error_details=str(e), status_code=500)
    finally:
        db.close()


# ---------------------------------------------------------------------------
# 7. EVIDENCE & EVIDENCE MATCHES
# ---------------------------------------------------------------------------
@promises_bp.route('/evidence', methods=['GET'])
def list_evidence():
    db: Session = get_db()
    try:
        result_id = request.args.get('result_id')
        page = request.args.get('page', 1, type=int)
        limit = request.args.get('limit', 20, type=int)

        query = db.query(Evidence)
        if result_id:
            query = query.filter(Evidence.result_id == result_id)

        items, total, page, limit, pages = paginate_query(query, page, limit)

        evidence_list = []
        for ev in items:
            evidence_list.append({
                "id": ev.id,
                "content": ev.content,
                "page_number": ev.page_number,
                "context": ev.context,
                "explanation": ev.explanation,
                "supporting_values": ev.supporting_values or {},
                "result_type": ev.result_type,
                "result_id": ev.result_id,
                "created_at": ev.created_at.isoformat() if ev.created_at else None
            })

        return success_response(data={
            "items": evidence_list,
            "total": total,
            "page": page,
            "limit": limit,
            "pages": pages
        })
    except Exception as e:
        return error_response(message="Failed to retrieve evidence", error_details=str(e), status_code=500)
    finally:
        db.close()


@promises_bp.route('/evidence/<int:evidence_id>', methods=['GET'])
def get_evidence_item(evidence_id: int):
    db: Session = get_db()
    try:
        ev = db.query(Evidence).filter(Evidence.id == evidence_id).first()
        if not ev:
            return error_response(message=f"Evidence '{evidence_id}' not found", status_code=404)

        return success_response(data={
            "id": ev.id,
            "content": ev.content,
            "page_number": ev.page_number,
            "context": ev.context,
            "explanation": ev.explanation,
            "supporting_values": ev.supporting_values or {},
            "result_type": ev.result_type,
            "result_id": ev.result_id,
            "created_at": ev.created_at.isoformat() if ev.created_at else None
        })
    except Exception as e:
        return error_response(message="Failed to retrieve evidence item", error_details=str(e), status_code=500)
    finally:
        db.close()


@promises_bp.route('/<promise_id>/evidence-matches', methods=['GET'])
def get_promise_evidence_matches(promise_id: str):
    db: Session = get_db()
    try:
        p = db.query(PoliticalPromise).filter(PoliticalPromise.promise_id == promise_id).first()
        if not p:
            return error_response(message=f"Promise '{promise_id}' not found", status_code=404)

        links = db.query(PromiseEvidenceLink).filter(PromiseEvidenceLink.promise_id == promise_id).order_by(PromiseEvidenceLink.relevance_score.desc()).all()

        matches = []
        for l in links:
            ev_info = None
            if l.evidence:
                ev_info = {
                    "id": l.evidence.id,
                    "content": l.evidence.content,
                    "page_number": l.evidence.page_number,
                    "context": l.evidence.context,
                    "supporting_values": l.evidence.supporting_values or {}
                }

            matches.append({
                "promise_id": l.promise_id,
                "evidence_id": l.evidence_id,
                "relevance_score": l.relevance_score or l.similarity_score,
                "matching_method": l.matching_method,
                "model_name": l.model_name,
                "model_version": l.model_version,
                "matched_metadata": l.matched_metadata or {},
                "relevance_notes": l.relevance_notes,
                "evidence_details": ev_info
            })

        return success_response(data={"promise_id": promise_id, "evidence_matches": matches, "total": len(matches)})
    except Exception as e:
        return error_response(message="Failed to retrieve evidence matches", error_details=str(e), status_code=500)
    finally:
        db.close()


# ---------------------------------------------------------------------------
# 8. ASSESSMENTS & ASSESSMENT HISTORY
# ---------------------------------------------------------------------------
@promises_bp.route('/<promise_id>/assessment', methods=['GET'])
def get_promise_assessment(promise_id: str):
    """
    REQUIRED RESPONSE FORMAT:
    - promise
    - status
    - confidence
    - explanation
    - supporting_evidence
    - source_links
    """
    db: Session = get_db()
    try:
        p = db.query(PoliticalPromise).filter(PoliticalPromise.promise_id == promise_id).first()
        if not p:
            return error_response(message=f"Promise '{promise_id}' not found", status_code=404)

        curr_assess = db.query(PromiseAssessment).filter(
            PromiseAssessment.promise_id == promise_id,
            PromiseAssessment.is_current == True
        ).first()

        status_str = curr_assess.status.value if (curr_assess and hasattr(curr_assess.status, 'value')) else (curr_assess.status if curr_assess else "not_assessed")
        confidence = curr_assess.confidence_score if curr_assess else 0.0
        explanation = curr_assess.rationale if curr_assess else "Promise has not been evaluated against evidence sources."

        # Primary category
        primary_cat_map = db.query(PromiseCategoryMapping).filter(
            PromiseCategoryMapping.promise_id == promise_id,
            PromiseCategoryMapping.is_primary == True
        ).first()
        category_name = primary_cat_map.category.name if (primary_cat_map and primary_cat_map.category) else "Uncategorized"

        promise_info = {
            "promise_id": p.promise_id,
            "manifesto_id": p.manifesto_id,
            "party": p.manifesto.party if p.manifesto else "Unknown",
            "election_year": p.manifesto.election_year if p.manifesto else None,
            "original_text": p.original_text,
            "normalized_text": p.normalized_text,
            "category": category_name,
            "classification": p.classification
        }

        # Supporting evidence & source links
        evidence_links = db.query(PromiseEvidenceLink).filter(PromiseEvidenceLink.promise_id == promise_id).all()
        supporting_evidence = []
        source_links = []
        seen_urls = set()

        for l in evidence_links:
            if l.evidence:
                ev = l.evidence
                supp = ev.supporting_values or {}
                supporting_evidence.append({
                    "evidence_id": ev.id,
                    "content": ev.content,
                    "page_number": ev.page_number,
                    "context": ev.context,
                    "source_type": supp.get("source_type", "Government Evidence"),
                    "relevance_score": l.relevance_score or l.similarity_score
                })

                url = supp.get("source_url")
                if url and url not in seen_urls:
                    seen_urls.add(url)
                    source_links.append({
                        "url": url,
                        "domain": supp.get("source_domain"),
                        "source_name": supp.get("source_name", "Government Source"),
                        "source_tier": supp.get("source_tier", 1),
                        "publication_date": supp.get("publication_date")
                    })

        return success_response(data={
            "promise": promise_info,
            "status": status_str,
            "confidence": confidence,
            "explanation": explanation,
            "supporting_evidence": supporting_evidence,
            "source_links": source_links,
            "assessment_date": curr_assess.assessment_date.isoformat() if (curr_assess and curr_assess.assessment_date) else None,
            "methodology": curr_assess.assessed_by if curr_assess else "deterministic_rule_engine_v1"
        })
    except Exception as e:
        return error_response(message="Failed to retrieve promise assessment", error_details=str(e), status_code=500)
    finally:
        db.close()


@promises_bp.route('/<promise_id>/history', methods=['GET'])
def get_promise_assessment_history(promise_id: str):
    db: Session = get_db()
    try:
        p = db.query(PoliticalPromise).filter(PoliticalPromise.promise_id == promise_id).first()
        if not p:
            return error_response(message=f"Promise '{promise_id}' not found", status_code=404)

        entries = db.query(PromiseAssessmentHistory).filter(
            PromiseAssessmentHistory.promise_id == promise_id
        ).order_by(PromiseAssessmentHistory.changed_at.asc()).all()

        history = []
        for h in entries:
            history.append({
                "id": h.id,
                "promise_id": h.promise_id,
                "assessment_id": h.assessment_id,
                "previous_status": h.previous_status,
                "new_status": h.new_status,
                "change_reason": h.change_reason,
                "changed_by": h.changed_by,
                "changed_at": h.changed_at.isoformat() if h.changed_at else None
            })

        return success_response(data={"promise_id": promise_id, "history": history, "total": len(history)})
    except Exception as e:
        return error_response(message="Failed to retrieve assessment history", error_details=str(e), status_code=500)
    finally:
        db.close()


# ---------------------------------------------------------------------------
# 9. SOURCES
# ---------------------------------------------------------------------------
@promises_bp.route('/sources', methods=['GET'])
def list_sources():
    db: Session = get_db()
    try:
        manifesto_sources = db.query(ManifestoSource).all()
        sources = []
        for s in manifesto_sources:
            sources.append({
                "source_id": s.source_id,
                "organization": s.organization,
                "source_url": s.source_url,
                "source_type": s.source_type,
                "source_tier": s.source_tier,
                "retrieval_status": s.retrieval_status,
                "checksum": s.checksum
            })

        return success_response(data={"sources": sources, "total": len(sources)})
    except Exception as e:
        return error_response(message="Failed to retrieve sources", error_details=str(e), status_code=500)
    finally:
        db.close()
