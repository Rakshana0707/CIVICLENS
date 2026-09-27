from typing import List, Optional, Tuple, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_, desc
from backend.repositories.base import CRUDBase
from backend.models.budget import BudgetRecord, BudgetDepartment, BudgetScheme, BudgetStage

class BudgetRecordRepository(CRUDBase[BudgetRecord]):
    def __init__(self):
        super().__init__(BudgetRecord)
        
    def get_records(
        self,
        db: Session,
        *,
        skip: int = 0,
        limit: int = 100,
        financial_year: Optional[str] = None,
        department_name: Optional[str] = None,
        department_id: Optional[int] = None,
        scheme_name: Optional[str] = None,
        scheme_id: Optional[int] = None,
        budget_stage: Optional[BudgetStage] = None
    ) -> Tuple[List[BudgetRecord], int]:
        """
        Retrieve budget records with filtering and pagination.
        Returns a tuple: (list of records, total count).
        """
        query = db.query(self.model).join(BudgetScheme).join(BudgetDepartment)
        
        if financial_year:
            query = query.filter(self.model.financial_year == financial_year)
            
        if budget_stage:
            query = query.filter(self.model.budget_stage == budget_stage)
            
        if department_id is not None:
            query = query.filter(BudgetScheme.department_id == department_id)
        elif department_name:
            query = query.filter(BudgetDepartment.name.ilike(f"%{department_name}%"))
            
        if scheme_id is not None:
            query = query.filter(self.model.scheme_id == scheme_id)
        elif scheme_name:
            query = query.filter(BudgetScheme.name.ilike(f"%{scheme_name}%"))
            
        # Get total count before pagination
        total_count = query.count()
        
        # Apply pagination and ordering
        records = query.order_by(
            BudgetDepartment.name, 
            BudgetScheme.name, 
            desc(self.model.financial_year)
        ).offset(skip).limit(limit).all()
        
        return records, total_count

    def get_available_years(self, db: Session) -> List[str]:
        """Returns a list of distinct financial years present in the database."""
        results = db.query(self.model.financial_year).distinct().order_by(desc(self.model.financial_year)).all()
        return [r[0] for r in results]

    def get_departments(self, db: Session, *, search_term: Optional[str] = None) -> List[BudgetDepartment]:
        """Returns available departments, optionally filtered by name."""
        query = db.query(BudgetDepartment)
        if search_term:
            query = query.filter(BudgetDepartment.name.ilike(f"%{search_term}%"))
        return query.order_by(BudgetDepartment.name).all()

    def get_schemes(
        self, 
        db: Session, 
        *, 
        department_id: Optional[int] = None,
        search_term: Optional[str] = None
    ) -> List[BudgetScheme]:
        """Returns available schemes, optionally filtered by department and name."""
        query = db.query(BudgetScheme)
        if department_id is not None:
            query = query.filter(BudgetScheme.department_id == department_id)
        if search_term:
            query = query.filter(BudgetScheme.name.ilike(f"%{search_term}%"))
        return query.order_by(BudgetScheme.name).all()

budget_repo = BudgetRecordRepository()
