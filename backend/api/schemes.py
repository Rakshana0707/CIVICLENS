from flask import Blueprint, request
from sqlalchemy.orm import Session
from backend.database.session import get_db
from backend.models.budget import HistoricalScheme, BudgetDepartment, SchemeCategory, SchemeSourceRelationship, BudgetSourceDocument
from backend.api.responses import success_response, error_response

schemes_bp = Blueprint('schemes', __name__, url_prefix='/schemes')

@schemes_bp.route('/search', methods=['GET'])
def search_schemes():
    try:
        db: Session = next(get_db())
    except Exception as e:
        return error_response(f"Database error: {str(e)}", status_code=500)
    
    # Query parameters
    name = request.args.get('name', type=str)
    description = request.args.get('description', type=str)
    year = request.args.get('year', type=str)
    department_id = request.args.get('department_id', type=int)
    category_id = request.args.get('category_id', type=int)
    page = request.args.get('page', 1, type=int)
    limit = request.args.get('limit', 10, type=int)

    # Validation
    if page < 1:
        return error_response("Page must be >= 1", status_code=400)
    if limit < 1 or limit > 100:
        return error_response("Limit must be between 1 and 100", status_code=400)
    
    query = db.query(HistoricalScheme)

    # Filters
    if name:
        query = query.filter(HistoricalScheme.scheme_name.ilike(f"%{name}%"))
    if description:
        query = query.filter(HistoricalScheme.description.ilike(f"%{description}%"))
    if year:
        # e.g., '2023-24'
        if len(year) != 7 or "-" not in year:
            return error_response("Invalid year format. Expected YYYY-YY.", status_code=400)
        query = query.filter(HistoricalScheme.financial_year == year)
    if department_id:
        query = query.filter(HistoricalScheme.department_id == department_id)
    if category_id:
        query = query.filter(HistoricalScheme.category_id == category_id)
        
    total_count = query.count()
    
    schemes = query.offset((page - 1) * limit).limit(limit).all()
    
    data = []
    for s in schemes:
        data.append({
            "id": s.id,
            "scheme_name": s.scheme_name,
            "financial_year": s.financial_year,
            "department_id": s.department_id,
            "category_id": s.category_id,
            "description": s.description,
            "objectives": s.objectives,
            "target_beneficiaries": s.target_beneficiaries,
            "is_uncertain_match": bool(s.is_uncertain_match),
            "match_confidence": s.match_confidence
        })
        
    return success_response({
        "items": data,
        "page": page,
        "limit": limit,
        "total": total_count
    })

@schemes_bp.route('/<int:scheme_id>', methods=['GET'])
def get_scheme(scheme_id: int):
    db: Session = next(get_db())
    scheme = db.query(HistoricalScheme).filter(HistoricalScheme.id == scheme_id).first()
    if not scheme:
        return error_response("Scheme not found", status_code=404)
        
    return success_response({
        "id": scheme.id,
        "scheme_name": scheme.scheme_name,
        "financial_year": scheme.financial_year,
        "department_id": scheme.department_id,
        "category_id": scheme.category_id,
        "description": scheme.description,
        "objectives": scheme.objectives,
        "target_beneficiaries": scheme.target_beneficiaries,
        "is_uncertain_match": bool(scheme.is_uncertain_match)
    })

@schemes_bp.route('/<int:scheme_id>/history', methods=['GET'])
def get_scheme_history(scheme_id: int):
    db: Session = next(get_db())
    scheme = db.query(HistoricalScheme).filter(HistoricalScheme.id == scheme_id).first()
    if not scheme:
        return error_response("Scheme not found", status_code=404)
        
    if not scheme.budget_scheme_id:
        # If it's not linked to a budget scheme, its history is just itself
        history = [scheme]
    else:
        history = db.query(HistoricalScheme).filter(HistoricalScheme.budget_scheme_id == scheme.budget_scheme_id).order_by(HistoricalScheme.financial_year.desc()).all()
        
    data = [{
        "id": h.id,
        "financial_year": h.financial_year,
        "scheme_name": h.scheme_name,
        "description": h.description,
        "objectives": h.objectives,
        "is_uncertain_match": bool(h.is_uncertain_match)
    } for h in history]
    
    return success_response(data)

@schemes_bp.route('/<int:scheme_id>/sources', methods=['GET'])
def get_scheme_sources(scheme_id: int):
    db: Session = next(get_db())
    scheme = db.query(HistoricalScheme).filter(HistoricalScheme.id == scheme_id).first()
    if not scheme:
        return error_response("Scheme not found", status_code=404)
        
    rels = db.query(SchemeSourceRelationship).filter(SchemeSourceRelationship.historical_scheme_id == scheme_id).all()
    
    data = []
    for rel in rels:
        doc = db.query(BudgetSourceDocument).filter(BudgetSourceDocument.id == rel.source_document_id).first()
        data.append({
            "relationship_id": rel.id,
            "source_document_id": rel.source_document_id,
            "document_title": doc.title if doc else None,
            "manifest_dataset_id": doc.manifest_dataset_id if doc else None,
            "source_page_number": rel.source_page_number,
            "extracted_text_snippet": rel.extracted_text[:200] if rel.extracted_text else None
        })
        
    return success_response(data)
