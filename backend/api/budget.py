from flask import Blueprint, request
from backend.database.session import SessionLocal
from backend.services.budget import budget_service
from backend.models.budget import BudgetStage
from backend.api.responses import success_response, error_response
from backend.schemas.budget import BudgetRecordResponse, PaginatedResponse, DepartmentResponse, SchemeResponse
from dataclasses import asdict

from backend.repositories.budget import budget_repo

budget_bp = Blueprint('budget', __name__, url_prefix='/budget')

@budget_bp.route('/years', methods=['GET'])
def get_years():
    """Get all available financial years."""
    db = SessionLocal()
    try:
        years = budget_repo.get_available_years(db)
        return success_response(data=years)
    except Exception as e:
        return error_response(str(e), status_code=500)
    finally:
        db.close()

@budget_bp.route('/departments', methods=['GET'])
def get_departments():
    """Get departments, optionally filtered by search_term."""
    search = request.args.get('search')
    db = SessionLocal()
    try:
        depts = budget_repo.get_departments(db, search_term=search)
        data = [asdict(DepartmentResponse(id=d.id, name=d.name)) for d in depts]
        return success_response(data=data)
    except Exception as e:
        return error_response(str(e), status_code=500)
    finally:
        db.close()

@budget_bp.route('/schemes', methods=['GET'])
def get_schemes():
    """Get schemes, optionally filtered by department_id or search_term."""
    search = request.args.get('search')
    dept_id = request.args.get('department_id', type=int)
    db = SessionLocal()
    try:
        schemes = budget_repo.get_schemes(db, department_id=dept_id, search_term=search)
        data = [asdict(SchemeResponse(id=s.id, name=s.name, department_id=s.department_id)) for s in schemes]
        return success_response(data=data)
    except Exception as e:
        return error_response(str(e), status_code=500)
    finally:
        db.close()

@budget_bp.route('/records', methods=['GET'])
def get_records():
    """Retrieve filtered budget records with pagination."""
    try:
        skip = request.args.get('skip', default=0, type=int)
        limit = request.args.get('limit', default=100, type=int)
        year = request.args.get('financial_year')
        dept_id = request.args.get('department_id', type=int)
        scheme_id = request.args.get('scheme_id', type=int)
        stage_str = request.args.get('budget_stage')
        
        stage = None
        if stage_str:
            try:
                stage = BudgetStage(stage_str)
            except ValueError:
                return error_response(f"Invalid budget_stage: {stage_str}", status_code=400)

        db = SessionLocal()
        try:
            records, total = budget_service.get_filtered_records(
                db, skip=skip, limit=limit,
                financial_year=year, department_id=dept_id,
                scheme_id=scheme_id, budget_stage=stage
            )
            
            data = [asdict(BudgetRecordResponse.from_model(r)) for r in records]
            response = asdict(PaginatedResponse(records=data, total_count=total, skip=skip, limit=limit))
            return success_response(data=response)
        finally:
            db.close()
    except Exception as e:
        return error_response(str(e), status_code=500)

@budget_bp.route('/summarize/year', methods=['GET'])
def summarize_year():
    """Summarize budget amounts by year. Requires a specific budget_stage."""
    stage_str = request.args.get('budget_stage')
    if not stage_str:
        return error_response("budget_stage is required for summation.", status_code=400)
    
    try:
        stage = BudgetStage(stage_str)
    except ValueError:
        return error_response(f"Invalid budget_stage: {stage_str}", status_code=400)

    db = SessionLocal()
    try:
        records, _ = budget_service.get_filtered_records(
            db, skip=0, limit=1000000, budget_stage=stage
        )
        summary = budget_service.summarize_by_year(records)
        return success_response(data=summary)
    finally:
        db.close()

@budget_bp.route('/summarize/department', methods=['GET'])
def summarize_department():
    """Summarize budget amounts by department. Requires a specific budget_stage and financial_year."""
    stage_str = request.args.get('budget_stage')
    year = request.args.get('financial_year')
    if not stage_str or not year:
        return error_response("budget_stage and financial_year are required.", status_code=400)
    
    try:
        stage = BudgetStage(stage_str)
    except ValueError:
        return error_response("Invalid budget_stage", status_code=400)

    db = SessionLocal()
    try:
        records, _ = budget_service.get_filtered_records(
            db, skip=0, limit=1000000, budget_stage=stage, financial_year=year
        )
        summary = budget_service.summarize_by_department(records)
        return success_response(data=summary)
    finally:
        db.close()

@budget_bp.route('/summarize/scheme', methods=['GET'])
def summarize_scheme():
    """Summarize budget amounts by scheme. Requires budget_stage and financial_year."""
    stage_str = request.args.get('budget_stage')
    year = request.args.get('financial_year')
    dept_id = request.args.get('department_id', type=int)
    
    if not stage_str or not year:
        return error_response("budget_stage and financial_year are required.", status_code=400)
    
    try:
        stage = BudgetStage(stage_str)
    except ValueError:
        return error_response("Invalid budget_stage", status_code=400)

    db = SessionLocal()
    try:
        records, _ = budget_service.get_filtered_records(
            db, skip=0, limit=1000000, budget_stage=stage, financial_year=year, department_id=dept_id
        )
        summary = budget_service.summarize_by_scheme(records)
        return success_response(data=summary)
    finally:
        db.close()

@budget_bp.route('/analysis/trend', methods=['GET'])
def get_trend():
    """Calculates year-wise totals and year-over-year percentage changes."""
    stage_str = request.args.get('budget_stage')
    dept_id = request.args.get('department_id', type=int)
    scheme_id = request.args.get('scheme_id', type=int)
    
    if not stage_str:
        return error_response("budget_stage is required for trend analysis.", status_code=400)
    
    try:
        stage = BudgetStage(stage_str)
    except ValueError:
        return error_response("Invalid budget_stage", status_code=400)

    db = SessionLocal()
    try:
        records, _ = budget_service.get_filtered_records(
            db, skip=0, limit=1000000, budget_stage=stage, 
            department_id=dept_id, scheme_id=scheme_id
        )
        trend = budget_service.calculate_year_trend(records)
        return success_response(data=trend)
    finally:
        db.close()

@budget_bp.route('/analysis/scheme-trends', methods=['GET'])
def get_scheme_trends():
    """Calculates year-wise totals and trends grouped by scheme."""
    stage_str = request.args.get('budget_stage')
    dept_id = request.args.get('department_id', type=int)
    
    if not stage_str:
        return error_response("budget_stage is required for trend analysis.", status_code=400)
    
    try:
        stage = BudgetStage(stage_str)
    except ValueError:
        return error_response("Invalid budget_stage", status_code=400)

    db = SessionLocal()
    try:
        records, _ = budget_service.get_filtered_records(
            db, skip=0, limit=1000000, budget_stage=stage, 
            department_id=dept_id
        )
        trends = budget_service.calculate_scheme_trends(records)
        return success_response(data=trends)
    finally:
        db.close()
