"""
Phase 10.2 — Public Policy Evaluation Data Acquisition Pipeline.
================================================================

Provides an enterprise-grade, respectful, multi-format acquisition pipeline for:
- Government Orders (GOs) and Policy Notes
- Budget Documents and Detailed Demands for Grants (DDG)
- Comptroller & Auditor General (CAG) Audit Reports
- Structured Survey & Administrative Datasets (CSV, Excel, JSON)
- Web Pages and HTML Tabular Records
- Independent Evaluation Studies and Academic Reports

Key Architectural Features:
1. Source Registry Integration with domain whitelists and politeness limits.
2. Download & Manual-Import Interfaces (handling OTP/CAPTCHA gated resources).
3. File Type Detection via magic byte signatures and MIME inspection.
4. Layout-aware PDF text extraction and tabular extraction using pdfplumber.
5. OCR Fallback for scanned/raster PDFs and document images.
6. Structured dataset ingestion (CSV, JSON, Excel, HTML tables).
7. SHA-256 cryptographic checksums and duplicate prevention.
8. ISO-8601 UTC retrieval timestamps and provenance metadata tracking.
9. Publication-date extraction heuristics (GO dates, CAG report years, fiscal years).
10. Structured failure and processing audit logging.
11. Automatic citizen privacy protection via DPDPA 2023 PII scrubbing.
12. Zero-fabrication compliance: strictly preserves raw files and records source reality.
"""

from __future__ import annotations

import os
import re
import io
import csv
import json
import time
import zipfile
import hashlib
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from dataclasses import dataclass, field
from html.parser import HTMLParser
from typing import List, Dict, Any, Optional, Tuple, Set, Union

from backend.models.civic_issue import sanitize_pii
from backend.core.logger import setup_logger

logger = setup_logger("civiclens.phase10.acquisition")


# ===========================================================================
# 1. Source Configuration & Registry
# ===========================================================================

@dataclass
class PolicySourceConfig:
    """Source-specific configuration and compliance profile."""
    source_id: str
    source_name: str
    publisher: str
    base_url: str
    source_tier: int  # Tier 1 (Statutory) to Tier 5 (Unverified)
    rate_limit_seconds: float = 2.0
    allowed_domains: List[str] = field(default_factory=list)
    disallowed_paths: List[str] = field(default_factory=list)
    supported_formats: List[str] = field(default_factory=lambda: ["PDF", "CSV", "JSON", "HTML", "XLSX"])
    requires_manual_import: bool = False
    custom_headers: Dict[str, str] = field(default_factory=dict)
    timeout_seconds: float = 15.0
    max_retries: int = 3
    is_active: bool = True


DEFAULT_POLICY_EVALUATION_SOURCES: Dict[str, PolicySourceConfig] = {
    "TN_BUDGET": PolicySourceConfig(
        source_id="TN_BUDGET",
        source_name="Tamil Nadu State Budget Portal",
        publisher="Finance Department, Government of Tamil Nadu",
        base_url="https://tnbudget.tn.gov.in/",
        source_tier=1,
        rate_limit_seconds=2.0,
        allowed_domains=["tnbudget.tn.gov.in", "www.tnbudget.tn.gov.in"],
        disallowed_paths=["/admin", "/login"],
        supported_formats=["PDF", "HTML"],
    ),
    "TN_GOV_POLICY": PolicySourceConfig(
        source_id="TN_GOV_POLICY",
        source_name="Government of Tamil Nadu Department Policy Notes & GOs",
        publisher="Government of Tamil Nadu",
        base_url="https://www.tn.gov.in/",
        source_tier=1,
        rate_limit_seconds=2.0,
        allowed_domains=["tn.gov.in", "www.tn.gov.in"],
        disallowed_paths=["/admin", "/login", "/restricted"],
        supported_formats=["PDF", "HTML"],
    ),
    "CAG_AUDIT": PolicySourceConfig(
        source_id="CAG_AUDIT",
        source_name="Comptroller and Auditor General of India — Tamil Nadu Audits",
        publisher="Office of the CAG of India",
        base_url="https://cag.gov.in/",
        source_tier=1,
        rate_limit_seconds=2.5,
        allowed_domains=["cag.gov.in", "www.cag.gov.in"],
        disallowed_paths=["/admin", "/user"],
        supported_formats=["PDF", "HTML"],
    ),
    "DATA_GOV_IN": PolicySourceConfig(
        source_id="DATA_GOV_IN",
        source_name="Open Government Data Platform India (OGD)",
        publisher="National Informatics Centre (NIC)",
        base_url="https://www.data.gov.in/",
        source_tier=2,
        rate_limit_seconds=2.0,
        allowed_domains=["data.gov.in", "www.data.gov.in"],
        disallowed_paths=["/user/login", "/admin"],
        supported_formats=["CSV", "JSON", "XLSX"],
    ),
    "CENSUS_SRS": PolicySourceConfig(
        source_id="CENSUS_SRS",
        source_name="Office of the Registrar General & Census Commissioner / NFHS",
        publisher="Ministry of Home Affairs / MoHFW, Government of India",
        base_url="https://censusindia.gov.in/",
        source_tier=2,
        rate_limit_seconds=2.0,
        allowed_domains=["censusindia.gov.in", "www.censusindia.gov.in", "rchiips.org"],
        disallowed_paths=["/admin"],
        supported_formats=["PDF", "XLSX", "CSV"],
    ),
    "SANSAD_PARLIAMENT": PolicySourceConfig(
        source_id="SANSAD_PARLIAMENT",
        source_name="Digital Sansad (Parliament of India Q&A on Tamil Nadu CSS)",
        publisher="Lok Sabha and Rajya Sabha Secretariats",
        base_url="https://sansad.in/",
        source_tier=1,
        rate_limit_seconds=2.0,
        allowed_domains=["sansad.in", "www.sansad.in"],
        disallowed_paths=["/admin", "/login"],
        supported_formats=["HTML", "PDF"],
    ),
    "TN_SPC": PolicySourceConfig(
        source_id="TN_SPC",
        source_name="Tamil Nadu State Planning Commission Evaluation Reports",
        publisher="State Planning Commission, Government of Tamil Nadu",
        base_url="https://spc.tn.gov.in/",
        source_tier=2,
        rate_limit_seconds=2.0,
        allowed_domains=["spc.tn.gov.in", "www.spc.tn.gov.in"],
        disallowed_paths=["/admin", "/wp-admin"],
        supported_formats=["PDF", "HTML"],
    ),
    "LOCAL_FIXTURE": PolicySourceConfig(
        source_id="LOCAL_FIXTURE",
        source_name="CIVICLENS TN Test Fixture Environment",
        publisher="CIVICLENS TN Internal Test Suite",
        base_url="http://test-fixture.civiclens.internal/",
        source_tier=1,
        rate_limit_seconds=0.0,
        allowed_domains=["test-fixture.civiclens.internal", "localhost", "127.0.0.1"],
        disallowed_paths=["/restricted"],
        supported_formats=["PDF", "CSV", "JSON", "HTML", "XLSX"],
    ),
}


class PolicyEvaluationSourceRegistry:
    """Registry managing authorized public policy evaluation data sources."""

    def __init__(self, custom_sources: Optional[Dict[str, PolicySourceConfig]] = None):
        self._sources: Dict[str, PolicySourceConfig] = dict(DEFAULT_POLICY_EVALUATION_SOURCES)
        if custom_sources:
            self._sources.update(custom_sources)

    def register(self, config: PolicySourceConfig):
        self._sources[config.source_id] = config
        logger.info(f"Registered policy evaluation source: {config.source_id} ({config.source_name})")

    def get(self, source_id: str) -> Optional[PolicySourceConfig]:
        return self._sources.get(source_id)

    def list_sources(self) -> List[PolicySourceConfig]:
        return list(self._sources.values())

    def get_by_url(self, url: str) -> Optional[PolicySourceConfig]:
        parsed = urllib.parse.urlparse(url)
        domain = parsed.netloc.lower()
        for config in self._sources.values():
            for allowed in config.allowed_domains:
                if domain == allowed or domain.endswith("." + allowed):
                    return config
        return None


# ===========================================================================
# 2. File Type Detection
# ===========================================================================

class FileTypeDetector:
    """
    Detects file types using magic byte signatures, content sniffing, and extensions.
    """

    MAGIC_SIGNATURES = [
        (b"%PDF-", "PDF", "application/pdf"),
        (b"PK\x03\x04", "XLSX", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"),
        (b"\xD0\xCF\x11\xE0\xA1\xB1\x1A\xE1", "XLS", "application/vnd.ms-excel"),
    ]

    EXTENSION_MAP = {
        ".pdf": ("PDF", "application/pdf"),
        ".csv": ("CSV", "text/csv"),
        ".tsv": ("CSV", "text/tab-separated-values"),
        ".json": ("JSON", "application/json"),
        ".xlsx": ("XLSX", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"),
        ".xls": ("XLS", "application/vnd.ms-excel"),
        ".html": ("HTML", "text/html"),
        ".htm": ("HTML", "text/html"),
        ".txt": ("TXT", "text/plain"),
    }

    @classmethod
    def detect_type(
        cls,
        raw_bytes: bytes,
        url_or_filename: Optional[str] = None,
        header_content_type: Optional[str] = None
    ) -> Tuple[str, str]:
        """
        Returns (format_code, mime_type). Format code is one of: PDF, CSV, JSON, XLSX, XLS, HTML, TXT, UNKNOWN.
        """
        if not raw_bytes:
            return "EMPTY", "application/x-empty"

        # 1. Check Magic Byte Signatures
        for signature, fmt, mime in cls.MAGIC_SIGNATURES:
            if raw_bytes.startswith(signature):
                return fmt, mime

        # 2. Check Text Signatures (HTML, JSON, CSV)
        sample = raw_bytes[:1024].strip()
        sample_lower = sample.lower()

        # HTML Detection
        if (
            sample_lower.startswith(b"<!doctype html")
            or sample_lower.startswith(b"<html")
            or b"<body" in sample_lower
            or b"<div" in sample_lower
        ):
            return "HTML", "text/html"

        # JSON Detection
        if sample.startswith(b"{") or sample.startswith(b"["):
            try:
                json.loads(raw_bytes.decode("utf-8", errors="ignore"))
                return "JSON", "application/json"
            except Exception:
                pass

        # 3. Filename Extension fallback
        if url_or_filename:
            parsed_path = urllib.parse.urlparse(url_or_filename).path
            _, ext = os.path.splitext(parsed_path.lower())
            if ext in cls.EXTENSION_MAP:
                return cls.EXTENSION_MAP[ext]

        # 4. Content-Type Header fallback
        if header_content_type:
            clean_ct = header_content_type.split(";")[0].strip().lower()
            if "pdf" in clean_ct:
                return "PDF", "application/pdf"
            if "csv" in clean_ct:
                return "CSV", "text/csv"
            if "json" in clean_ct:
                return "JSON", "application/json"
            if "html" in clean_ct:
                return "HTML", "text/html"
            if "sheet" in clean_ct or "excel" in clean_ct:
                return "XLSX", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

        # 5. Fallback CSV detection (comma or tab delimited rows)
        try:
            sample_str = raw_bytes[:2048].decode("utf-8", errors="ignore")
            lines = [line.strip() for line in sample_str.splitlines() if line.strip()]
            if len(lines) >= 2:
                sniffer = csv.Sniffer()
                dialect = sniffer.sniff(sample_str[:1024])
                if dialect.delimiter in (",", "\t", ";"):
                    return "CSV", "text/csv"
        except Exception:
            pass

        return "UNKNOWN", "application/octet-stream"


# ===========================================================================
# 3. Publication Date Extractor
# ===========================================================================

class PublicationDateExtractor:
    """
    Extracts published dates or reference fiscal years from document text and titles.
    """

    MONTH_MAP = {
        "january": 1, "jan": 1, "february": 2, "feb": 2, "march": 3, "mar": 3,
        "april": 4, "apr": 4, "may": 5, "june": 6, "jun": 6, "july": 7, "jul": 7,
        "august": 8, "aug": 8, "september": 9, "sep": 9, "sept": 9,
        "october": 10, "oct": 10, "november": 11, "nov": 11, "december": 12, "dec": 12
    }

    @classmethod
    def extract_date(cls, text: str, title: Optional[str] = None) -> Optional[str]:
        """
        Attempts to extract a standardized publication date string (YYYY-MM-DD or FY YYYY-YYYY).
        """
        search_corpus = f"{title or ''}\n{text[:4000]}"

        # Pattern 1: Government Order format: G.O. (Ms.) No. 123 Dated: 15.09.2023 or 15/09/2023
        go_match = re.search(
            r'Dated\s*[:.-]?\s*(\d{1,2})[./-](\d{1,2})[./-](\d{4})',
            search_corpus,
            re.IGNORECASE
        )
        if go_match:
            d, m, y = int(go_match.group(1)), int(go_match.group(2)), int(go_match.group(3))
            if 1 <= d <= 31 and 1 <= m <= 12 and 1990 <= y <= 2035:
                return f"{y:04d}-{m:02d}-{d:02d}"

        # Pattern 2: CAG Report Year: Report No. 3 of 2024
        cag_match = re.search(r'Report\s+No\.?\s*\d+\s+of\s+(20\d{2})', search_corpus, re.IGNORECASE)
        if cag_match:
            y = int(cag_match.group(1))
            return f"{y}-03-31"  # Default to end of audit reporting cycle

        # Pattern 3: DD Month YYYY (e.g., 20 March 2024 or 20th March, 2024)
        date_word_match = re.search(
            r'\b(\d{1,2})(?:st|nd|rd|th)?\s+([A-Za-z]+),?\s+(\d{4})\b',
            search_corpus,
            re.IGNORECASE
        )
        if date_word_match:
            d = int(date_word_match.group(1))
            m_str = date_word_match.group(2).lower()
            y = int(date_word_match.group(3))
            if m_str in cls.MONTH_MAP and 1 <= d <= 31 and 1990 <= y <= 2035:
                m = cls.MONTH_MAP[m_str]
                return f"{y:04d}-{m:02d}-{d:02d}"

        # Pattern 4: Standard ISO date: YYYY-MM-DD
        iso_match = re.search(r'\b(20\d{2})-(0[1-9]|1[0-2])-(0[1-9]|[12]\d|3[01])\b', search_corpus)
        if iso_match:
            return iso_match.group(0)

        # Pattern 5: Fiscal Year: 2023-2024 or 2023-24
        fy_match = re.search(r'\b(20\d{2})[-–](20\d{2}|\d{2})\b', search_corpus)
        if fy_match:
            start_yr = fy_match.group(1)
            end_yr = fy_match.group(2)
            if len(end_yr) == 2:
                end_yr = f"20{end_yr}"
            return f"{start_yr}-{end_yr}"

        return None


# ===========================================================================
# 4. PDF Layout & Table Extractor with OCR Fallback
# ===========================================================================

class PolicyOCRFallbackHandler:
    """Detects scanned pages and invokes Tesseract OCR or records structured fallback."""

    @staticmethod
    def is_tesseract_available() -> bool:
        try:
            import pytesseract  # type: ignore
            pytesseract.get_tesseract_version()
            return True
        except Exception:
            return False

    @classmethod
    def process_scanned_page(
        cls,
        page_index: int,
        image_bytes: Optional[bytes] = None
    ) -> Dict[str, Any]:
        """Performs OCR if available; otherwise returns structured fallback marker."""
        if cls.is_tesseract_available() and image_bytes:
            try:
                import pytesseract  # type: ignore
                from PIL import Image  # type: ignore
                img = Image.open(io.BytesIO(image_bytes))
                text = pytesseract.image_to_string(img, lang="eng+tam")
                return {
                    "ocr_used": True,
                    "ocr_status": "OCR_SUCCESS",
                    "text": sanitize_pii(text),
                    "page_index": page_index
                }
            except Exception as e:
                logger.warning(f"OCR processing failed for page {page_index}: {e}")

        # Graceful fallback metadata when OCR engine is absent or fails
        return {
            "ocr_used": False,
            "ocr_status": "OCR_REQUIRED_FALLBACK",
            "text": f"[SCANNED DOCUMENT PAGE {page_index + 1} — OCR REQUIRED: Raster page detected; manual transcription or Tesseract engine needed]",
            "page_index": page_index
        }


class PolicyPDFExtractor:
    """Extracts text, structured tables, and handles raster pages using pdfplumber."""

    @staticmethod
    def parse_pdf(file_bytes: bytes) -> Dict[str, Any]:
        result = {
            "text": "",
            "tables": [],
            "page_count": 0,
            "ocr_used": False,
            "ocr_status": "NO_OCR_NEEDED",
            "scanned_pages": 0,
            "metadata": {}
        }

        try:
            import pdfplumber  # type: ignore
            with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
                result["page_count"] = len(pdf.pages)
                result["metadata"] = dict(pdf.metadata or {})
                full_text_pages = []
                all_tables = []
                scanned_pages_count = 0

                for idx, page in enumerate(pdf.pages):
                    page_text = page.extract_text() or ""
                    
                    # Extract tables from page
                    page_tables = page.extract_tables()
                    if page_tables:
                        for table in page_tables:
                            if len(table) >= 2:
                                headers = [
                                    str(c).strip().replace("\n", " ") if c else f"col_{i}"
                                    for i, c in enumerate(table[0])
                                ]
                                dict_rows = []
                                for row in table[1:]:
                                    row_dict = {}
                                    for i, cell in enumerate(row):
                                        h = headers[i] if i < len(headers) else f"col_{i}"
                                        clean_cell = str(cell).strip() if cell is not None else ""
                                        row_dict[h] = sanitize_pii(clean_cell)
                                    dict_rows.append(row_dict)
                                if dict_rows:
                                    all_tables.append(dict_rows)

                    # Check for raster/scanned page (< 30 characters of extracted text)
                    if len(page_text.strip()) < 30:
                        scanned_pages_count += 1
                        ocr_res = PolicyOCRFallbackHandler.process_scanned_page(page_index=idx)
                        page_text = ocr_res["text"]
                        if ocr_res.get("ocr_used"):
                            result["ocr_used"] = True
                            result["ocr_status"] = ocr_res["ocr_status"]
                        elif result["ocr_status"] == "NO_OCR_NEEDED":
                            result["ocr_status"] = ocr_res["ocr_status"]

                    full_text_pages.append(page_text)

                result["text"] = sanitize_pii("\n\n".join(full_text_pages))
                result["tables"] = all_tables
                result["scanned_pages"] = scanned_pages_count

        except Exception as e:
            logger.error(f"Policy PDF extraction error: {e}")
            result["text"] = f"[PDF PARSE ERROR: {str(e)}]"
            result["ocr_status"] = "PDF_CORRUPT_OR_UNREADABLE"

        return result


# ===========================================================================
# 5. HTML Table Parser & Extractor
# ===========================================================================

class PolicyHTMLTableParser(HTMLParser):
    """Zero-dependency HTML table parser converting tables into row matrices."""

    def __init__(self):
        super().__init__()
        self.tables: List[List[List[str]]] = []
        self._current_table: Optional[List[List[str]]] = None
        self._current_row: Optional[List[str]] = None
        self._current_cell: Optional[str] = None
        self._in_table = False
        self._in_row = False
        self._in_cell = False

    def handle_starttag(self, tag: str, attrs: List[Tuple[str, Optional[str]]]):
        tag = tag.lower()
        if tag == "table":
            self._in_table = True
            self._current_table = []
        elif self._in_table and tag == "tr":
            self._in_row = True
            self._current_row = []
        elif self._in_row and tag in ("td", "th"):
            self._in_cell = True
            self._current_cell = ""

    def handle_endtag(self, tag: str):
        tag = tag.lower()
        if tag in ("td", "th") and self._in_cell:
            if self._current_row is not None and self._current_cell is not None:
                self._current_row.append(self._current_cell.strip())
            self._in_cell = False
            self._current_cell = None
        elif tag == "tr" and self._in_row:
            if self._current_table is not None and self._current_row is not None:
                self._current_table.append(self._current_row)
            self._in_row = False
            self._current_row = None
        elif tag == "table" and self._in_table:
            if self._current_table:
                self.tables.append(self._current_table)
            self._in_table = False
            self._current_table = None

    def handle_data(self, data: str):
        if self._in_cell and self._current_cell is not None:
            self._current_cell += data


class PolicyHTMLExtractor:
    """Extracts clean text and structured tables from HTML policy pages."""

    @staticmethod
    def extract(html_content: str) -> Dict[str, Any]:
        # Extract tables
        parser = PolicyHTMLTableParser()
        parser.feed(html_content)
        extracted_tables: List[List[Dict[str, Any]]] = []

        for raw_table in parser.tables:
            if not raw_table or len(raw_table) < 2:
                continue
            headers = [h if h else f"col_{i}" for i, h in enumerate(raw_table[0])]
            table_rows: List[Dict[str, Any]] = []
            for row in raw_table[1:]:
                row_dict = {}
                for i, val in enumerate(row):
                    header = headers[i] if i < len(headers) else f"col_{i}"
                    row_dict[header] = sanitize_pii(val)
                table_rows.append(row_dict)
            if table_rows:
                extracted_tables.append(table_rows)

        # Extract plain text removing tags and scripts
        clean_text = re.sub(r'<script.*?</script>', '', html_content, flags=re.DOTALL | re.IGNORECASE)
        clean_text = re.sub(r'<style.*?</style>', '', clean_text, flags=re.DOTALL | re.IGNORECASE)
        clean_text = re.sub(r'<[^>]+>', ' ', clean_text)
        clean_text = re.sub(r'\s+', ' ', clean_text).strip()

        return {
            "text": sanitize_pii(clean_text),
            "tables": extracted_tables
        }


# ===========================================================================
# 6. Structured Tabular Ingestion (CSV, JSON, Excel)
# ===========================================================================

class StructuredDatasetIngestor:
    """Ingests structured datasets (CSV, JSON, Excel) into normalized records."""

    @staticmethod
    def ingest_csv(csv_bytes_or_str: Union[bytes, str]) -> List[Dict[str, Any]]:
        text = csv_bytes_or_str.decode("utf-8", errors="replace") if isinstance(csv_bytes_or_str, bytes) else csv_bytes_or_str
        reader = csv.DictReader(io.StringIO(text))
        rows = []
        for r in reader:
            sanitized = {k.strip(): sanitize_pii(str(v).strip()) for k, v in r.items() if k is not None}
            rows.append(sanitized)
        return rows

    @staticmethod
    def ingest_json(json_bytes_or_str: Union[bytes, str]) -> Union[List[Dict[str, Any]], Dict[str, Any]]:
        text = json_bytes_or_str.decode("utf-8", errors="replace") if isinstance(json_bytes_or_str, bytes) else json_bytes_or_str
        data = json.loads(text)
        if isinstance(data, list):
            return [
                {k: sanitize_pii(str(v)) if isinstance(v, str) else v for k, v in item.items()}
                if isinstance(item, dict) else item
                for item in data
            ]
        elif isinstance(data, dict):
            return {k: sanitize_pii(str(v)) if isinstance(v, str) else v for k, v in data.items()}
        return data

    @staticmethod
    def ingest_xlsx(xlsx_bytes: bytes) -> List[List[Dict[str, Any]]]:
        """Extracts sheets from XLSX using standard zipfile XML parsing."""
        tables = []
        try:
            with zipfile.ZipFile(io.BytesIO(xlsx_bytes), "r") as zf:
                # Read shared strings if present
                shared_strings = []
                if "xl/sharedStrings.xml" in zf.namelist():
                    ss_xml = zf.read("xl/sharedStrings.xml").decode("utf-8", errors="ignore")
                    shared_strings = re.findall(r'<t[^>]*>(.*?)</t>', ss_xml)

                # Process sheet1
                sheet_files = [f for f in zf.namelist() if f.startswith("xl/worksheets/sheet")]
                for sheet_file in sheet_files[:3]:  # Process up to 3 sheets
                    sheet_xml = zf.read(sheet_file).decode("utf-8", errors="ignore")
                    rows_xml = re.findall(r'<row[^>]*>(.*?)</row>', sheet_xml)
                    sheet_rows: List[List[str]] = []
                    for row_str in rows_xml:
                        cells = re.findall(r'<c[^>]*?(?:t="([^"]*)")?[^>]*>(?:<v>([^<]*)</v>)?', row_str)
                        row_vals = []
                        for cell_type, val in cells:
                            if cell_type == "s" and val.isdigit() and int(val) < len(shared_strings):
                                row_vals.append(shared_strings[int(val)])
                            else:
                                row_vals.append(val)
                        if any(row_vals):
                            sheet_rows.append(row_vals)

                    if len(sheet_rows) >= 2:
                        headers = [h if h else f"col_{i}" for i, h in enumerate(sheet_rows[0])]
                        dict_rows = []
                        for row in sheet_rows[1:]:
                            r_dict = {}
                            for i, cell in enumerate(row):
                                h = headers[i] if i < len(headers) else f"col_{i}"
                                r_dict[h] = sanitize_pii(cell)
                            dict_rows.append(r_dict)
                        if dict_rows:
                            tables.append(dict_rows)
        except Exception as e:
            logger.warning(f"XLSX parsing note: {e}")

        return tables


# ===========================================================================
# 7. Checksums, Storage, and Duplicate Detection
# ===========================================================================

@dataclass
class PolicyAcquisitionResult:
    """Comprehensive acquisition outcome and provenance record."""
    source_id: str
    url: str
    status: str  # SUCCESS, CACHED, DUPLICATE, FAILED, OCR_FALLBACK, MANUAL_IMPORT_REQUIRED
    file_format: str
    mime_type: str
    retrieved_at: datetime
    sha256_hash: str
    file_size_bytes: int
    storage_path: Optional[str] = None
    document_title: Optional[str] = None
    publication_date: Optional[str] = None
    parsed_text: str = ""
    extracted_tables: List[List[Dict[str, Any]]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    ocr_used: bool = False
    ocr_status: str = "NO_OCR_NEEDED"
    error_message: Optional[str] = None
    http_status: Optional[int] = None
    retry_count: int = 0
    is_cached: bool = False
    is_duplicate: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source_id": self.source_id,
            "url": self.url,
            "status": self.status,
            "file_format": self.file_format,
            "mime_type": self.mime_type,
            "retrieved_at": self.retrieved_at.isoformat(),
            "sha256_hash": self.sha256_hash,
            "file_size_bytes": self.file_size_bytes,
            "storage_path": self.storage_path,
            "document_title": self.document_title,
            "publication_date": self.publication_date,
            "ocr_used": self.ocr_used,
            "ocr_status": self.ocr_status,
            "table_count": len(self.extracted_tables),
            "text_length": len(self.parsed_text),
            "is_duplicate": self.is_duplicate,
            "error_message": self.error_message,
        }


class PolicyStorageManager:
    """Manages raw payload storage, sidecar metadata, and deduplication."""

    def __init__(self, base_storage_dir: str = "data/raw/policy_evaluation"):
        self.base_storage_dir = base_storage_dir
        os.makedirs(self.base_storage_dir, exist_ok=True)
        self._seen_hashes: Set[str] = set()

    @staticmethod
    def compute_sha256(content: Union[bytes, str]) -> str:
        if isinstance(content, str):
            content = content.encode("utf-8")
        return hashlib.sha256(content).hexdigest()

    def is_duplicate(self, sha256_hash: str) -> bool:
        if sha256_hash in self._seen_hashes:
            return True
        # Check if file exists on disk
        sidecar_path = os.path.join(self.base_storage_dir, f"{sha256_hash}.meta.json")
        return os.path.exists(sidecar_path)

    def mark_seen(self, sha256_hash: str):
        self._seen_hashes.add(sha256_hash)

    def save_payload(
        self,
        raw_bytes: bytes,
        sha256_hash: str,
        file_format: str,
        metadata: Dict[str, Any]
    ) -> str:
        ext = file_format.lower()
        file_path = os.path.join(self.base_storage_dir, f"{sha256_hash}.{ext}")
        meta_path = os.path.join(self.base_storage_dir, f"{sha256_hash}.meta.json")

        with open(file_path, "wb") as f:
            f.write(raw_bytes)

        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2)

        self._seen_hashes.add(sha256_hash)
        return file_path


# ===========================================================================
# 8. Processing & Error Logging
# ===========================================================================

@dataclass
class ProcessingErrorLog:
    source_id: str
    url: str
    timestamp: datetime
    error_type: str
    error_message: str
    http_status: Optional[int] = None
    retry_count: int = 0


class PolicyAcquisitionLogger:
    """Structured audit and failure logger for policy acquisition."""

    def __init__(self):
        self._logs: List[ProcessingErrorLog] = []

    def record_error(
        self,
        source_id: str,
        url: str,
        error_type: str,
        error_message: str,
        http_status: Optional[int] = None,
        retry_count: int = 0
    ):
        log_entry = ProcessingErrorLog(
            source_id=source_id,
            url=url,
            timestamp=datetime.now(timezone.utc),
            error_type=error_type,
            error_message=error_message,
            http_status=http_status,
            retry_count=retry_count
        )
        self._logs.append(log_entry)
        logger.warning(
            f"Policy Acquisition Error [{source_id}] {url} -> {error_type} "
            f"(HTTP {http_status}, Retries {retry_count}): {error_message}"
        )

    def get_logs(self) -> List[ProcessingErrorLog]:
        return list(self._logs)

    def clear(self):
        self._logs.clear()


# ===========================================================================
# 9. Unified Policy Evaluation Acquisition Pipeline
# ===========================================================================

class PolicyEvaluationAcquisitionPipeline:
    """
    Main reusable pipeline orchestrating downloads, manual imports, parsing,
    deduplication, date extraction, and provenance recording.
    """

    def __init__(
        self,
        registry: Optional[PolicyEvaluationSourceRegistry] = None,
        storage_manager: Optional[PolicyStorageManager] = None
    ):
        self.registry = registry or PolicyEvaluationSourceRegistry()
        self.storage = storage_manager or PolicyStorageManager()
        self.logger = PolicyAcquisitionLogger()
        self._last_domain_request: Dict[str, float] = {}

    def _enforce_rate_limit(self, domain: str, delay_seconds: float):
        if delay_seconds <= 0:
            return
        last_req = self._last_domain_request.get(domain, 0.0)
        elapsed = time.time() - last_req
        if elapsed < delay_seconds:
            time.sleep(delay_seconds - elapsed)
        self._last_domain_request[domain] = time.time()

    def acquire_document(
        self,
        url_or_path: str,
        source_id: Optional[str] = None,
        document_title: Optional[str] = None,
        is_manual_import: bool = False,
        file_bytes: Optional[bytes] = None
    ) -> PolicyAcquisitionResult:
        """
        Acquires and processes a policy document from a URL, local path, or byte buffer.
        """
        retrieved_at = datetime.now(timezone.utc)

        # 1. Resolve Source Configuration
        config = self.registry.get(source_id) if source_id else self.registry.get_by_url(url_or_path)
        if not config:
            config = self.registry.get("LOCAL_FIXTURE") or PolicySourceConfig(
                source_id="UNKNOWN",
                source_name="Unknown Source",
                publisher="Unspecified",
                base_url=url_or_path,
                source_tier=4
            )

        # 2. Acquire Raw Bytes
        raw_bytes: bytes = b""
        http_status: Optional[int] = None
        retry_count = 0

        if file_bytes is not None:
            raw_bytes = file_bytes
        elif is_manual_import or os.path.exists(url_or_path):
            try:
                with open(url_or_path, "rb") as f:
                    raw_bytes = f.read()
            except Exception as e:
                self.logger.record_error(config.source_id, url_or_path, "FILE_READ_ERROR", str(e))
                return PolicyAcquisitionResult(
                    source_id=config.source_id,
                    url=url_or_path,
                    status="FAILED",
                    file_format="UNKNOWN",
                    mime_type="application/octet-stream",
                    retrieved_at=retrieved_at,
                    sha256_hash="",
                    file_size_bytes=0,
                    error_message=f"File read failed: {str(e)}"
                )
        else:
            # Check domain whitelist and robots policy
            parsed_url = urllib.parse.urlparse(url_or_path)
            domain = parsed_url.netloc.lower()

            domain_allowed = any(domain == a or domain.endswith("." + a) for a in config.allowed_domains)
            if not domain_allowed:
                self.logger.record_error(config.source_id, url_or_path, "DOMAIN_NOT_WHITELISTED", f"Domain {domain} not in allowed domains")
                return PolicyAcquisitionResult(
                    source_id=config.source_id,
                    url=url_or_path,
                    status="FAILED",
                    file_format="UNKNOWN",
                    mime_type="application/octet-stream",
                    retrieved_at=retrieved_at,
                    sha256_hash="",
                    file_size_bytes=0,
                    error_message=f"Domain {domain} is not whitelisted for source {config.source_id}"
                )

            # Check disallowed paths
            for disallowed in config.disallowed_paths:
                if disallowed and disallowed.lower() in parsed_url.path.lower():
                    self.logger.record_error(config.source_id, url_or_path, "DISALLOWED_PATH", f"Path {parsed_url.path} is restricted by policy")
                    return PolicyAcquisitionResult(
                        source_id=config.source_id,
                        url=url_or_path,
                        status="FAILED",
                        file_format="UNKNOWN",
                        mime_type="application/octet-stream",
                        retrieved_at=retrieved_at,
                        sha256_hash="",
                        file_size_bytes=0,
                        error_message="Access restricted: path is disallowed"
                    )

            # Polite download with retries
            self._enforce_rate_limit(domain, config.rate_limit_seconds)
            headers = {"User-Agent": "CIVICLENS-TN-PolicyEvaluation/1.0 (Civic Research; +https://civiclens-tn.internal/bot)"}
            headers.update(config.custom_headers)

            req = urllib.request.Request(url_or_path, headers=headers)
            for attempt in range(config.max_retries):
                retry_count = attempt
                try:
                    with urllib.request.urlopen(req, timeout=config.timeout_seconds) as resp:
                        http_status = resp.status
                        raw_bytes = resp.read()
                        break
                except Exception as e:
                    if attempt == config.max_retries - 1:
                        self.logger.record_error(config.source_id, url_or_path, "DOWNLOAD_ERROR", str(e), http_status=http_status, retry_count=attempt)
                        return PolicyAcquisitionResult(
                            source_id=config.source_id,
                            url=url_or_path,
                            status="FAILED",
                            file_format="UNKNOWN",
                            mime_type="application/octet-stream",
                            retrieved_at=retrieved_at,
                            sha256_hash="",
                            file_size_bytes=0,
                            error_message=f"Download failed after {config.max_retries} retries: {str(e)}",
                            http_status=http_status,
                            retry_count=attempt
                        )
                    time.sleep(1.0 * (2 ** attempt))

        # 3. Checksums and Deduplication
        sha256_hash = self.storage.compute_sha256(raw_bytes)
        is_dup = self.storage.is_duplicate(sha256_hash)

        # 4. Detect File Type
        file_format, mime_type = FileTypeDetector.detect_type(raw_bytes, url_or_filename=url_or_path)

        # 5. Extract Content & Tables Based on Format
        parsed_text = ""
        extracted_tables = []
        ocr_used = False
        ocr_status = "NO_OCR_NEEDED"
        metadata: Dict[str, Any] = {"source_tier": config.source_tier, "publisher": config.publisher}

        if file_format == "PDF":
            pdf_res = PolicyPDFExtractor.parse_pdf(raw_bytes)
            parsed_text = pdf_res["text"]
            extracted_tables = pdf_res["tables"]
            ocr_used = pdf_res["ocr_used"]
            ocr_status = pdf_res["ocr_status"]
            metadata["page_count"] = pdf_res["page_count"]
            metadata["scanned_pages"] = pdf_res["scanned_pages"]
        elif file_format == "CSV":
            csv_rows = StructuredDatasetIngestor.ingest_csv(raw_bytes)
            extracted_tables = [csv_rows]
            parsed_text = sanitize_pii(raw_bytes[:2000].decode("utf-8", errors="replace"))
        elif file_format == "JSON":
            json_res = StructuredDatasetIngestor.ingest_json(raw_bytes)
            if isinstance(json_res, list):
                extracted_tables = [json_res]
            parsed_text = sanitize_pii(json.dumps(json_res, indent=2)[:2000])
        elif file_format == "HTML":
            html_res = PolicyHTMLExtractor.extract(raw_bytes.decode("utf-8", errors="replace"))
            parsed_text = html_res["text"]
            extracted_tables = html_res["tables"]
        elif file_format == "XLSX":
            xlsx_tables = StructuredDatasetIngestor.ingest_xlsx(raw_bytes)
            extracted_tables = xlsx_tables
            parsed_text = f"[EXCEL WORKBOOK: {len(xlsx_tables)} tables extracted]"
        else:
            parsed_text = sanitize_pii(raw_bytes.decode("utf-8", errors="replace"))

        # 6. Extract Publication Date
        effective_title = document_title or os.path.basename(url_or_path)
        pub_date = PublicationDateExtractor.extract_date(parsed_text, title=effective_title)

        # 7. Preserve Raw Payload & Provenance
        sidecar_meta = {
            "source_id": config.source_id,
            "url": url_or_path,
            "sha256_hash": sha256_hash,
            "file_format": file_format,
            "mime_type": mime_type,
            "retrieved_at": retrieved_at.isoformat(),
            "publication_date": pub_date,
            "document_title": effective_title,
            "file_size_bytes": len(raw_bytes),
            "source_tier": config.source_tier,
            "ocr_status": ocr_status,
        }
        storage_path = self.storage.save_payload(raw_bytes, sha256_hash, file_format, sidecar_meta)

        status_str = "DUPLICATE" if is_dup else ("OCR_FALLBACK" if ocr_status == "OCR_REQUIRED_FALLBACK" else "SUCCESS")

        return PolicyAcquisitionResult(
            source_id=config.source_id,
            url=url_or_path,
            status=status_str,
            file_format=file_format,
            mime_type=mime_type,
            retrieved_at=retrieved_at,
            sha256_hash=sha256_hash,
            file_size_bytes=len(raw_bytes),
            storage_path=storage_path,
            document_title=effective_title,
            publication_date=pub_date,
            parsed_text=parsed_text,
            extracted_tables=extracted_tables,
            metadata=metadata,
            ocr_used=ocr_used,
            ocr_status=ocr_status,
            http_status=http_status,
            retry_count=retry_count,
            is_duplicate=is_dup
        )
