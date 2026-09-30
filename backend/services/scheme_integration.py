import logging
from typing import List, Dict, Any, Tuple
from sqlalchemy.orm import Session
from backend.models.budget import BudgetScheme, BudgetDepartment, HistoricalScheme

logger = logging.getLogger(__name__)

class SchemeIntegrator:
    def __init__(self, db_session: Session):
        self.db = db_session

    def integrate(self, normalized_records: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Integrates historical Phase 2 scheme records with Phase 1 quantitative tables.
        Returns a match-quality report.
        """
        report = {
            "total_records": len(normalized_records),
            "exact_matches": 0,
            "uncertain_matches": 0,
            "unmatched_new_schemes": 0,
            "failed_department_lookup": 0
        }
        
        mapping_table = []

        for record in normalized_records:
            dept_name = record.get("department_name")
            scheme_name = record.get("scheme_name")
            
            # 1. Lookup Department
            dept = self.db.query(BudgetDepartment).filter(BudgetDepartment.name == dept_name).first()
            if not dept:
                report["failed_department_lookup"] += 1
                mapping_table.append({"record": record, "status": "FAILED_DEPT", "matched_id": None})
                continue
                
            # 2. Strict Exact Matching to Phase 1 BudgetScheme
            # We enforce strict lowercase exact string match to avoid false positive merges
            existing_schemes = self.db.query(BudgetScheme).filter(BudgetScheme.department_id == dept.id).all()
            
            exact_match_id = None
            uncertain_match_id = None
            
            for bs in existing_schemes:
                if bs.name.lower().strip() == scheme_name.lower().strip():
                    exact_match_id = bs.id
                    break
                    
            if not exact_match_id:
                # Naive uncertain match rule: one name is a subset of another and > 10 chars
                # Or fuzzy ratio > 80% (simulated here via basic substring)
                for bs in existing_schemes:
                    if len(scheme_name) > 10 and (scheme_name.lower() in bs.name.lower() or bs.name.lower() in scheme_name.lower()):
                        uncertain_match_id = bs.id
                        break
            
            # 3. Determine Integration Status
            budget_scheme_id = None
            is_uncertain = 0
            
            if exact_match_id:
                budget_scheme_id = exact_match_id
                report["exact_matches"] += 1
                status = "EXACT_MATCH"
            elif uncertain_match_id:
                budget_scheme_id = uncertain_match_id
                is_uncertain = 1
                report["uncertain_matches"] += 1
                status = "UNCERTAIN_MATCH"
            else:
                report["unmatched_new_schemes"] += 1
                status = "NEW_UNMATCHED"
                
            mapping_table.append({
                "historical_name": scheme_name,
                "department": dept_name,
                "status": status,
                "budget_scheme_id": budget_scheme_id
            })
            
            # 4. Construct DB Model (If we were inserting)
            # original_source_identifier is preserved via record_id
            # This logic just evaluates the match and prepares the integration.
            # In a real run, we'd add to session.
            
            hist_scheme = HistoricalScheme(
                original_source_identifier=record.get("record_id"),
                budget_scheme_id=budget_scheme_id,
                department_id=dept.id,
                source_document_id=record.get("source_document_id"),
                financial_year=record.get("financial_year"),
                scheme_name=scheme_name,
                description=record.get("description"),
                objectives=record.get("objectives"),
                target_beneficiaries=record.get("target_beneficiaries"),
                sector_category=record.get("sector_category"),
                is_uncertain_match=is_uncertain,
                match_confidence=1.0 if status == "EXACT_MATCH" else (0.7 if status == "UNCERTAIN_MATCH" else 0.0)
            )
            # self.db.add(hist_scheme) # Omitted explicit commit to allow purely returning the mapping
            
        return {
            "report": report,
            "mapping_table": mapping_table
        }
