import json
import logging
import re
from typing import List, Dict, Tuple
from backend.models.budget import BudgetRecord

logger = logging.getLogger(__name__)

class BudgetCleaner:
    def __init__(self, mappings_file: str = "config/budget_mappings.json"):
        self.mappings_file = mappings_file
        self.department_mappings = {}
        self.scheme_mappings = {}
        self._load_mappings()

    def _load_mappings(self):
        try:
            with open(self.mappings_file, 'r') as f:
                data = json.load(f)
                self.department_mappings = data.get("departments", {})
                self.scheme_mappings = data.get("schemes", {})
        except FileNotFoundError:
            logger.warning(f"Mappings file {self.mappings_file} not found. Normalization will rely on raw text.")

    def _normalize_text(self, text: str) -> str:
        if not text:
            return ""
        # Normalize whitespace
        text = re.sub(r'\s+', ' ', text)
        # Strip leading/trailing
        return text.strip()

    def clean_batch(self, records: List[BudgetRecord]) -> Tuple[List[BudgetRecord], List[Dict], Dict]:
        """
        Cleans a batch of validated records.
        Returns: (cleaned_records, unresolved_records, cleaning_report)
        """
        cleaned = []
        unresolved = []
        
        # Report tracking
        report = {
            "total_processed": len(records),
            "total_cleaned": 0,
            "total_unresolved": 0,
            "transformations": []
        }

        for record in records:
            transformations_applied = []
            
            # 1. Normalize Text and Encoding
            orig_dept = record.department_name
            orig_scheme = record.scheme_name
            
            record.department_name = self._normalize_text(record.department_name)
            record.scheme_name = self._normalize_text(record.scheme_name)
            
            if orig_dept != record.department_name:
                transformations_applied.append(f"Normalized whitespace in department name '{orig_dept}'")
            if orig_scheme != record.scheme_name:
                transformations_applied.append(f"Normalized whitespace in scheme name '{orig_scheme}'")

            # 2. Apply explicit mappings (No fuzzy matching to prevent unwanted merges)
            mapped_dept = self.department_mappings.get(record.department_name)
            if mapped_dept:
                record.department_name = mapped_dept
                transformations_applied.append(f"Mapped department '{orig_dept}' to '{mapped_dept}'")

            mapped_scheme = self.scheme_mappings.get(record.scheme_name)
            if mapped_scheme:
                record.scheme_name = mapped_scheme
                transformations_applied.append(f"Mapped scheme '{orig_scheme}' to '{mapped_scheme}'")

            # 3. Standardize Financial Year
            # Ensure YYYY-YY format. Assume validation already enforced this mostly.
            if record.financial_year:
                orig_fy = record.financial_year
                record.financial_year = record.financial_year.replace("/", "-")
                if orig_fy != record.financial_year:
                    transformations_applied.append(f"Standardized FY from {orig_fy} to {record.financial_year}")

            # 4. Monetary values are already numeric due to ingestor mapping, but we ensure missing stays null.
            # 5. Budget stage is Enum, so it's standardized by definition.
            
            # 6. Unresolved logic
            # If after normalization, the department or scheme is empty, it's unresolved
            if not record.department_name or not record.scheme_name:
                unresolved.append({
                    "record_id": record.record_id,
                    "reason": "Missing or emptied department/scheme after cleaning",
                    "original_payload": record.original_category
                })
                continue
            
            # Record transformations for report
            if transformations_applied:
                report["transformations"].append({
                    "record_id": record.record_id,
                    "changes": transformations_applied
                })
            
            cleaned.append(record)

        report["total_cleaned"] = len(cleaned)
        report["total_unresolved"] = len(unresolved)
        return cleaned, unresolved, report
