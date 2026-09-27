from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy.orm import Session
from backend.repositories.budget import budget_repo
from backend.models.budget import BudgetRecord, BudgetStage

class BudgetAnalysisService:
    """
    Service layer for budget data retrieval and analysis.
    Calculations are strictly performed in-memory, separated from DB queries.
    """

    @staticmethod
    def get_filtered_records(
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
        return budget_repo.get_records(
            db,
            skip=skip,
            limit=limit,
            financial_year=financial_year,
            department_name=department_name,
            department_id=department_id,
            scheme_name=scheme_name,
            scheme_id=scheme_id,
            budget_stage=budget_stage
        )
        
    @staticmethod
    def summarize_by_year(records: List[BudgetRecord]) -> Dict[str, float]:
        """
        Summarizes budget amounts grouped by financial year.
        Records with missing amounts (None) are excluded, NOT treated as 0.
        Note: Assumes all records are of the same BudgetStage. Mixing stages in a simple sum is invalid.
        """
        summary = {}
        for record in records:
            if record.amount is None:
                continue
            year = record.financial_year
            summary[year] = summary.get(year, 0.0) + record.amount
        return summary

    @staticmethod
    def summarize_by_department(records: List[BudgetRecord]) -> Dict[str, float]:
        """
        Summarizes budget amounts grouped by department name.
        """
        summary = {}
        for record in records:
            if record.amount is None or not record.scheme or not record.scheme.department:
                continue
            dept = record.scheme.department.name
            summary[dept] = summary.get(dept, 0.0) + record.amount
        return summary

    @staticmethod
    def summarize_by_scheme(records: List[BudgetRecord]) -> Dict[str, float]:
        """
        Summarizes budget amounts grouped by scheme name.
        """
        summary = {}
        for record in records:
            if record.amount is None or not record.scheme:
                continue
            scheme = record.scheme.name
            summary[scheme] = summary.get(scheme, 0.0) + record.amount
        return summary

    @staticmethod
    def compare_stages(
        records: List[BudgetRecord], 
        stage_a: BudgetStage, 
        stage_b: BudgetStage
    ) -> Dict[str, Any]:
        """
        Compares two budget stages (e.g. Budget Estimate vs Actual Expenditure) 
        for comparable entities.
        
        Returns a dictionary mapping a unique identifier (e.g. scheme + year) 
        to the comparison metrics (absolute difference, percentage difference).
        """
        if stage_a == stage_b:
            raise ValueError("Cannot compare identical budget stages.")
            
        # Group amounts by unique entity (scheme_id + financial_year) and stage
        grouped_data = {}
        
        for record in records:
            if record.amount is None or not record.scheme:
                continue
                
            # We group by scheme and year. We could expand this to include head_of_account.
            entity_key = f"{record.scheme.name} ({record.financial_year})"
            
            if entity_key not in grouped_data:
                grouped_data[entity_key] = {}
                
            if record.budget_stage in [stage_a, stage_b]:
                # Assume single record per stage/scheme/year in this context, 
                # or sum them if multiple entries exist (e.g. sub-schemes).
                grouped_data[entity_key][record.budget_stage] = grouped_data[entity_key].get(record.budget_stage, 0.0) + record.amount
                
        # Perform comparison only where BOTH stages exist
        comparisons = {}
        for entity_key, stages_data in grouped_data.items():
            if stage_a in stages_data and stage_b in stages_data:
                val_a = stages_data[stage_a]
                val_b = stages_data[stage_b]
                diff = val_b - val_a
                
                percent_diff = None
                if val_a != 0:
                    percent_diff = (diff / val_a) * 100
                    
                comparisons[entity_key] = {
                    "value_a": val_a,
                    "value_b": val_b,
                    "absolute_difference": diff,
                    "percentage_difference": percent_diff
                }
                
        return comparisons

budget_service = BudgetAnalysisService()
