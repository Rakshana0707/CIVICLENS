import logging
import re
from typing import List, Dict, Tuple, Any
from dataclasses import asdict
from backend.ingestion.models import RawSchemeRecord

logger = logging.getLogger(__name__)

class SchemeNormalizer:
    def __init__(self):
        self.report = {
            "total_processed": 0,
            "valid_records": 0,
            "unresolved_records": 0,
            "formatting_artifacts_removed": 0,
            "duplicates_detected": 0,
            "obvious_extraction_duplicates": 0,
            "missing_required_fields": 0
        }

    def _normalize_text_encoding(self, text: str) -> str:
        if not text:
            return text
        # Remove common PDF parsing artifacts (like unmapped cid characters)
        original_length = len(text)
        cleaned = re.sub(r'\(cid:\d+\)', '', text)
        # Remove gibberish markers or null bytes
        cleaned = cleaned.replace('\x00', '')
        if len(cleaned) < original_length:
            self.report["formatting_artifacts_removed"] += 1
        return cleaned.strip()

    def _normalize_financial_year(self, fy: str) -> str:
        if not fy:
            return ""
        fy = self._normalize_text_encoding(fy)
        # Match variations like 2023-2024, 23-24, 2023-24
        match = re.search(r'(\d{4})\s*[-/]\s*(\d{2,4})', fy)
        if match:
            start_yr = match.group(1)
            end_yr = match.group(2)
            if len(end_yr) == 4:
                end_yr = end_yr[2:]
            return f"{start_yr}-{end_yr}"
        return fy

    def _normalize_monetary_values(self, val_str: str) -> float:
        if not val_str:
            return None
        # Extract numbers allowing commas and decimals
        matches = re.findall(r'[\d,]+\.?\d*', str(val_str))
        if matches:
            try:
                return float(matches[0].replace(',', ''))
            except ValueError:
                return None
        return None

    def _is_valid(self, record: RawSchemeRecord) -> bool:
        # Minimum required: Name, Dept, Source
        if not record.scheme_name or not record.department_name or not record.source_document_id:
            return False
        return True

    def process_records(self, raw_records: List[RawSchemeRecord]) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], Dict[str, Any]]:
        valid_records = []
        unresolved_records = []
        
        # To track duplicates
        seen_exact_hashes = set()
        seen_conceptual_keys = set() # (dept, scheme_name, year)

        for record in raw_records:
            self.report["total_processed"] += 1
            
            # Create a working copy for normalization
            normalized = asdict(record)
            
            # 1. Normalize Encoding and Clean Text
            # We explicitly PRESERVE original strings but clean structural artifacts
            normalized["original_scheme_name"] = record.scheme_name
            normalized["original_description"] = record.description
            
            normalized["scheme_name"] = self._normalize_text_encoding(record.scheme_name)
            normalized["department_name"] = self._normalize_text_encoding(record.department_name)
            normalized["financial_year"] = self._normalize_financial_year(record.financial_year)
            normalized["description"] = self._normalize_text_encoding(record.description)
            normalized["objectives"] = self._normalize_text_encoding(record.objectives)
            normalized["target_beneficiaries"] = self._normalize_text_encoding(record.target_beneficiaries)
            normalized["sector_category"] = self._normalize_text_encoding(record.sector_category)
            
            if record.allocation_amount:
                normalized["allocation_numeric"] = self._normalize_monetary_values(record.allocation_amount)

            # 2. Duplicate Detection
            # Obvious extraction duplicate: Exact match on all fields
            exact_hash = hash(frozenset(normalized.items()))
            if exact_hash in seen_exact_hashes:
                self.report["obvious_extraction_duplicates"] += 1
                continue # Discard pure extraction artifacts
            seen_exact_hashes.add(exact_hash)

            # Conceptual duplicate: Same dept, scheme, and year. 
            # Note: We DO NOT merge them automatically per requirements ("Do not merge schemes merely because their names are similar")
            # We just flag them as potential duplicates in the record.
            concept_key = (normalized.get("department_name"), normalized.get("scheme_name"), normalized.get("financial_year"))
            if concept_key in seen_conceptual_keys:
                self.report["duplicates_detected"] += 1
                normalized["is_potential_duplicate"] = True
            else:
                normalized["is_potential_duplicate"] = False
                if all(concept_key): # only add if valid
                    seen_conceptual_keys.add(concept_key)

            # 3. Validation
            # Required fields: scheme_name, department_name, source_document_id
            if not normalized["scheme_name"] or not normalized["department_name"] or not normalized["source_document_id"]:
                self.report["missing_required_fields"] += 1
                self.report["unresolved_records"] += 1
                
                # Do NOT generate descriptions if missing
                if not normalized["description"]:
                    normalized["description"] = None 
                    
                unresolved_records.append(normalized)
            else:
                self.report["valid_records"] += 1
                valid_records.append(normalized)

        return valid_records, unresolved_records, self.report
