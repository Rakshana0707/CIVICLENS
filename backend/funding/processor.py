"""
Phase 5 — Financial Document Parsing & Table Extraction Engine.

Parses statutory political funding documents (Form 24A contribution disclosures,
annual audited accounts, election expenditure statements) across varying layouts.
Extracts structured financial tables, normalizes monetary amounts, tracks page-level
provenance, and assigns extraction confidence scores.
"""

import re
import os
import json
import logging
from enum import Enum
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timezone

logger = logging.getLogger("civiclens.funding.processor")
logging.basicConfig(level=logging.INFO)


class AmountStatus(str, Enum):
    VALID_NUMERIC = "VALID_NUMERIC"
    ZERO = "ZERO"
    MISSING = "MISSING"
    NOT_DISCLOSED = "NOT_DISCLOSED"
    NOT_APPLICABLE = "NOT_APPLICABLE"
    EXTRACTION_FAILURE = "EXTRACTION_FAILURE"


class ExtractionMethod(str, Enum):
    PDF_NATIVE_TABLE = "PDF_NATIVE_TABLE"
    OCR_FALLBACK_TABLE = "OCR_FALLBACK_TABLE"
    LAYOUT_TEXT_PARSER = "LAYOUT_TEXT_PARSER"
    STRUCTURED_HTML_PARSER = "STRUCTURED_HTML_PARSER"


class AmountNormalizer:
    """Normalizes monetary strings to float INR values while preserving value status distinctions."""

    ZERO_STRINGS = {"0", "0.0", "0.00", "nil", "zero", "rs.0", "rs 0", "inr 0", "none"}
    NOT_DISCLOSED_STRINGS = {"undisclosed", "redacted", "***", "[not disclosed]", "not disclosed", "confidential"}
    NOT_APPLICABLE_STRINGS = {"n/a", "na", "not applicable", "-", "--", "---"}

    @classmethod
    def normalize(cls, raw_str: Optional[str]) -> Tuple[Optional[float], AmountStatus, str]:
        if raw_str is None:
            return None, AmountStatus.MISSING, ""

        clean = str(raw_str).strip()
        if not clean:
            return None, AmountStatus.MISSING, clean

        lowered = clean.lower()

        # 1. Explicit Zero Check
        if lowered in cls.ZERO_STRINGS or re.match(r"^₹?\s*0+(\.0+)?\s*/?-?$", lowered):
            return 0.0, AmountStatus.ZERO, clean

        # 2. Not Disclosed Check
        if lowered in cls.NOT_DISCLOSED_STRINGS or "not disclosed" in lowered:
            return None, AmountStatus.NOT_DISCLOSED, clean

        # 3. Not Applicable Check
        if lowered in cls.NOT_APPLICABLE_STRINGS:
            return None, AmountStatus.NOT_APPLICABLE, clean

        # 4. Numeric Parsing Heuristics
        # Check for Lakhs / Crores multiplier first
        multiplier = 1.0
        work_str = lowered
        if re.search(r"\b(crores?|cr)\b", work_str):
            multiplier = 10000000.0
            work_str = re.sub(r"\b(crores?|cr)\b", "", work_str).strip()
        elif re.search(r"\b(lakhs?|lacs?|lac)\b", work_str):
            multiplier = 100000.0
            work_str = re.sub(r"\b(lakhs?|lacs?|lac)\b", "", work_str).strip()

        # Remove currency symbols (₹, rs, inr, /-), commas, and spaces
        num_str = re.sub(r"^(₹|rs\.?|inr)\s*", "", work_str, flags=re.IGNORECASE)
        num_str = re.sub(r"[/\-]+$", "", num_str).strip()
        num_str = num_str.replace(",", "").strip()

        # Handle parentheses indicating negative amounts
        is_negative = False
        if num_str.startswith("(") and num_str.endswith(")"):
            is_negative = True
            num_str = num_str[1:-1].strip()

        try:
            val = float(num_str) * multiplier
            if is_negative:
                val = -val

            if val == 0.0:
                return 0.0, AmountStatus.ZERO, clean

            return val, AmountStatus.VALID_NUMERIC, clean
        except Exception:
            # Unparseable string
            return None, AmountStatus.EXTRACTION_FAILURE, clean


class ScannedPdfDetector:
    """Detects whether a PDF page relies on scanned raster images based on text density."""

    @staticmethod
    def inspect_page_text_density(page_text: str, char_threshold: int = 50) -> bool:
        """Returns True if the page appears to be a scanned image with minimal/no extracted text."""
        if not page_text:
            return True
        clean_text = page_text.strip()
        return len(clean_text) < char_threshold


class HeaderColumnDetector:
    """Identifies standard table column types from raw header strings."""

    COLUMN_PATTERNS = {
        "donor_name": [r"name of donor", r"name of person", r"contributor", r"donor", r"name of company", r"particulars"],
        "donor_address": [r"address", r"location", r"residence", r"registered office"],
        "amount": [r"amount", r"sum", r"contribution", r"inr", r"rupees", r"value"],
        "payment_mode": [r"mode", r"cheque", r"demand draft", r"eft", r"instrument", r"method"],
        "date": [r"date", r"payment date", r"receipt date", r"dt"],
        "remarks": [r"remarks", r"pan", r"cin", r"reference", r"notes"]
    }

    @classmethod
    def detect_column_type(cls, header_str: str) -> Optional[str]:
        if not header_str:
            return None
        lowered = header_str.lower()
        for col_type, patterns in cls.COLUMN_PATTERNS.items():
            for pat in patterns:
                if re.search(pat, lowered):
                    return col_type
        return None


class FinancialDocumentProcessor:
    """
    Main document processing pipeline for Phase 5.
    Parses native/scanned PDF filings or HTML documents into clean financial records.
    """

    PROCESSING_VERSION = "v1.0"

    @classmethod
    def extract_financial_year(cls, text: str) -> Optional[str]:
        """Extracts financial year string (e.g. FY2021-22) from text."""
        if not text:
            return None
        # Pattern matching: 2021-2022, 2021-22, FY 2021-22
        match = re.search(r"\b(?:FY\s*)?(20\d{2})[-/](\d{4}|\d{2})\b", text, re.IGNORECASE)
        if match:
            start_yr = match.group(1)
            end_yr = match.group(2)
            if len(end_yr) == 4:
                end_yr = end_yr[2:]
            return f"FY{start_yr}-{end_yr}"
        return None

    @classmethod
    def extract_party_code(cls, text: str) -> Optional[str]:
        """Extracts political party code from text."""
        if not text:
            return None
        known_parties = {
            "DMK": ["dravida munnetra kazhagam", "dmk"],
            "AIADMK": ["all india anna dravida munnetra kazhagam", "aiadmk"],
            "INC": ["indian national congress", "congress", "inc"],
            "BJP": ["bharatiya janata party", "bjp"],
            "PMK": ["pattali makkal katchi", "pmk"],
            "VCK": ["viduthalai meuthaigal katchi", "vck"],
            "NTK": ["naam tamilar katchi", "ntk"],
            "DMDK": ["desiya murpokku dravida kazhagam", "dmdk"]
        }
        text_lowered = text.lower()
        for code, synonyms in known_parties.items():
            for syn in synonyms:
                if syn in text_lowered:
                    return code
        return None

    @classmethod
    def parse_raw_table_row(
        cls,
        row_cells: List[str],
        column_map: Dict[int, str],
        document_id: str,
        source_url: str,
        page_number: int,
        table_number: int,
        row_index: int,
        party_code: str,
        financial_year: str,
        method: str = ExtractionMethod.PDF_NATIVE_TABLE
    ) -> Dict[str, Any]:
        """
        Parses a single tabular row into a structured ExtractedFinancialRecord dict.
        """
        raw_row_str = " | ".join([c.strip() for c in row_cells if c])

        donor_name = None
        donor_address = None
        raw_amount_str = None
        payment_mode = None
        payment_date = None
        remarks = None

        for idx, cell_text in enumerate(row_cells):
            col_type = column_map.get(idx)
            cell_clean = cell_text.strip()
            if not cell_clean:
                continue

            if col_type == "donor_name":
                donor_name = cell_clean
            elif col_type == "donor_address":
                donor_address = cell_clean
            elif col_type == "amount":
                raw_amount_str = cell_clean
            elif col_type == "payment_mode":
                payment_mode = cell_clean
            elif col_type == "date":
                payment_date = cell_clean
            elif col_type == "remarks":
                remarks = cell_clean

        # Fallback cell indexing if header mapping was partial
        if not raw_amount_str and len(row_cells) >= 3:
            # Look for cell containing digits/currency
            for cell in row_cells:
                if re.search(r"\d", cell) and not re.search(r"^[0-9]{1,2}[/-][0-9]{1,2}[/-][0-9]{2,4}$", cell.strip()):
                    raw_amount_str = cell.strip()
                    break

        norm_amount, amount_status, _ = AmountNormalizer.normalize(raw_amount_str)

        # Confidence calculation
        confidence = 0.50
        if norm_amount is not None or amount_status in (AmountStatus.ZERO, AmountStatus.NOT_DISCLOSED):
            confidence += 0.30
        if donor_name:
            confidence += 0.15
        if payment_mode or payment_date:
            confidence += 0.05
        confidence = min(1.0, round(confidence, 2))

        record_id = f"REC_{document_id}_P{page_number}_T{table_number}_R{row_index}"

        return {
            "record_id": record_id,
            "document_id": document_id,
            "source_url": source_url,
            "page_number": page_number,
            "table_number": table_number,
            "row_index": row_index,
            "raw_row": raw_row_str,
            "party_code": party_code,
            "financial_year": financial_year,
            "donor_name": donor_name,
            "donor_address": donor_address,
            "raw_amount_str": raw_amount_str,
            "normalized_amount_inr": norm_amount,
            "amount_status": amount_status.value,
            "payment_mode": payment_mode,
            "payment_date": payment_date,
            "remarks": remarks,
            "extraction_method": method,
            "extraction_confidence": confidence,
            "processing_version": cls.PROCESSING_VERSION,
            "processed_at": datetime.now(timezone.utc).isoformat()
        }

    @classmethod
    def process_raw_document_payload(
        cls,
        document_id: str,
        source_url: str,
        raw_text_pages: List[Dict[str, Any]],
        default_party_code: Optional[str] = None,
        default_financial_year: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Main pipeline entry point. Processes page-level text/table payloads into structured records.
        """
        all_full_text = "\n".join([p.get("text", "") for p in raw_text_pages])
        detected_fy = cls.extract_financial_year(all_full_text) or default_financial_year or "FY2021-22"
        detected_party = cls.extract_party_code(all_full_text) or default_party_code or "COMMON"

        scanned_pages = []
        extracted_records = []
        extraction_logs = []

        total_pages = len(raw_text_pages)

        for page_obj in raw_text_pages:
            page_num = page_obj.get("page_number", 1)
            page_text = page_obj.get("text", "")
            tables = page_obj.get("tables", [])

            is_scanned = ScannedPdfDetector.inspect_page_text_density(page_text)
            if is_scanned:
                scanned_pages.append(page_num)

            method = ExtractionMethod.OCR_FALLBACK_TABLE if is_scanned else ExtractionMethod.PDF_NATIVE_TABLE

            for table_idx, table_matrix in enumerate(tables, start=1):
                if not table_matrix or len(table_matrix) < 2:
                    continue

                # Header detection
                header_row = table_matrix[0]
                column_map = {}
                for idx, col_header in enumerate(header_row):
                    detected_col = HeaderColumnDetector.detect_column_type(str(col_header))
                    if detected_col:
                        column_map[idx] = detected_col

                # Default fallback mappings for standard Form 24A (SlNo, Donor, Address, Amount, Mode, Date, Remarks)
                if "donor_name" not in column_map.values() and len(header_row) >= 4:
                    column_map[1] = "donor_name"
                    column_map[2] = "donor_address"
                    column_map[3] = "amount"
                    if len(header_row) >= 5:
                        column_map[4] = "payment_mode"
                    if len(header_row) >= 6:
                        column_map[5] = "date"

                # Process data rows
                for row_idx, row_cells in enumerate(table_matrix[1:], start=1):
                    rec = cls.parse_raw_table_row(
                        row_cells=[str(cell or "") for cell in row_cells],
                        column_map=column_map,
                        document_id=document_id,
                        source_url=source_url,
                        page_number=page_num,
                        table_number=table_idx,
                        row_index=row_idx,
                        party_code=detected_party,
                        financial_year=detected_fy,
                        method=method
                    )
                    extracted_records.append(rec)

        overall_confidence = (
            sum(r["extraction_confidence"] for r in extracted_records) / len(extracted_records)
            if extracted_records else 0.0
        )

        return {
            "document_id": document_id,
            "source_url": source_url,
            "party_code": detected_party,
            "financial_year": detected_fy,
            "total_pages": total_pages,
            "scanned_pages_count": len(scanned_pages),
            "is_scanned_pdf": len(scanned_pages) > 0 and (len(scanned_pages) / total_pages) > 0.5,
            "total_records_extracted": len(extracted_records),
            "average_extraction_confidence": round(overall_confidence, 2),
            "records": extracted_records,
            "processing_version": cls.PROCESSING_VERSION
        }
