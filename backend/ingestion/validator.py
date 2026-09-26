import re
import logging
from typing import List, Dict, Tuple, Any
from backend.models.budget import BudgetRecord

logger = logging.getLogger(__name__)

class InvalidRecordError(Exception):
    pass

class BudgetValidator:
    """
    Validates budget records before they are stored.
    Rules are configurable via the rules dictionary.
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        # Configurable rules
        self.config = config or {
            "require_department": True,
            "require_scheme": True,
            "require_financial_year": True,
            "require_budget_stage": True,
            "require_source_reference": True,
            "financial_year_pattern": r"^\d{4}-\d{2}$",
            "allow_null_amounts": True,  # Missing values should not be treated as 0
            "strict_numeric_amounts": True
        }

    def validate_batch(self, records: List[BudgetRecord]) -> Tuple[List[BudgetRecord], List[Dict], Dict]:
        """
        Validates a batch of records.
        Returns: (valid_records, invalid_records_with_reasons, report_summary)
        """
        valid = []
        invalid = []
        
        # For duplicate detection within the batch
        seen_keys = set()
        
        for record in records:
            errors = []
            
            # 1. Traceability checks
            if self.config.get("require_source_reference"):
                if not record.source_document_id:
                    errors.append("Missing source_document_id.")
            
            # 2. Required fields
            if self.config.get("require_department") and not record.department_name:
                errors.append("Missing department_name.")
                
            if self.config.get("require_scheme") and not record.scheme_name:
                errors.append("Missing scheme_name.")
                
            if self.config.get("require_financial_year"):
                if not record.financial_year:
                    errors.append("Missing financial_year.")
                elif self.config.get("financial_year_pattern"):
                    if not re.match(self.config["financial_year_pattern"], record.financial_year):
                        errors.append(f"Malformed financial_year: {record.financial_year}")
            
            if self.config.get("require_budget_stage") and not record.budget_stage:
                errors.append("Missing budget_stage.")
                
            # 3. Amount checks (Do not treat missing as zero)
            if record.amount is None:
                if not self.config.get("allow_null_amounts"):
                    errors.append("amount is null and allow_null_amounts is False.")
            else:
                if self.config.get("strict_numeric_amounts"):
                    if not isinstance(record.amount, (int, float)):
                        errors.append(f"Invalid numeric amount type: {type(record.amount)}")

            # 4. Duplicate detection
            # Source-aware key: document, department, scheme, head_of_account, year, stage
            dup_key = (
                record.source_document_id,
                record.department_name,
                record.scheme_name,
                record.head_of_account,
                record.financial_year,
                record.budget_stage
            )
            
            if dup_key in seen_keys:
                errors.append("Likely duplicate record in batch.")
            else:
                # We only add to seen keys if there are no other errors that would invalidate the key parts
                # Actually, add it anyway to catch multiple identical malformed rows
                seen_keys.add(dup_key)

            if errors:
                invalid.append({
                    "record_id": record.record_id,
                    "raw_payload": record.original_category,
                    "source": record.source_document_id,
                    "errors": errors
                })
            else:
                valid.append(record)

        # 8. Produce a validation report
        report = self._generate_report(len(records), len(valid), invalid)
        return valid, invalid, report

    def _generate_report(self, total: int, valid_count: int, invalid_records: List[Dict]) -> Dict:
        error_counts = {}
        for inv in invalid_records:
            for err in inv['errors']:
                error_counts[err] = error_counts.get(err, 0) + 1
                
        return {
            "total_processed": total,
            "total_valid": valid_count,
            "total_invalid": len(invalid_records),
            "rejection_reasons": error_counts
        }
