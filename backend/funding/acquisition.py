"""
Phase 5 — Financial Document Acquisition Engine.

Provides reusable, configurable acquisition for statutory political funding documents
including PDF reports, HTML web pages, CSV/XLSX spreadsheets, and JSON feeds.
"""

import os
import json
import time
import logging
import hashlib
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple, Set
import urllib.request
import urllib.parse
import urllib.error

# Configure logger
logger = logging.getLogger("civiclens.funding.acquisition")
logging.basicConfig(level=logging.INFO)


class DocumentFormat:
    PDF = "PDF"
    HTML = "HTML"
    CSV = "CSV"
    XLSX = "XLSX"
    JSON = "JSON"
    UNKNOWN = "UNKNOWN"


class FileTypeDetector:
    """Detects document format using magic headers, content inspection, and file extension fallback."""

    @staticmethod
    def detect_format(content_bytes: bytes, filename_or_url: str = "", content_type_header: str = "") -> str:
        if not content_bytes:
            return DocumentFormat.UNKNOWN

        # 1. Magic Bytes Check
        if content_bytes.startswith(b"%PDF"):
            return DocumentFormat.PDF

        if content_bytes.startswith(b"PK\x03\x04"):
            # Could be XLSX or ZIP
            if filename_or_url.lower().endswith(".xlsx") or "spreadsheet" in content_type_header.lower():
                return DocumentFormat.XLSX
            return DocumentFormat.XLSX

        # 2. JSON check
        trimmed = content_bytes.strip()
        if (trimmed.startswith(b"{") and trimmed.endswith(b"}")) or (trimmed.startswith(b"[") and trimmed.endswith(b"]")):
            try:
                json.loads(trimmed.decode('utf-8', errors='ignore'))
                return DocumentFormat.JSON
            except Exception:
                pass

        # 3. HTML check
        lowered_head = content_bytes[:1024].lower()
        if b"<html" in lowered_head or b"<!doctype html" in lowered_head or b"<head" in lowered_head:
            return DocumentFormat.HTML

        # 4. Content-Type Header fallback
        ct = content_type_header.lower()
        if "application/pdf" in ct:
            return DocumentFormat.PDF
        if "text/html" in ct:
            return DocumentFormat.HTML
        if "text/csv" in ct or "application/csv" in ct:
            return DocumentFormat.CSV
        if "application/json" in ct:
            return DocumentFormat.JSON

        # 5. Extension fallback
        ext = os.path.splitext(filename_or_url.split("?")[0])[1].lower()
        if ext == ".pdf":
            return DocumentFormat.PDF
        if ext in (".html", ".htm"):
            return DocumentFormat.HTML
        if ext == ".csv":
            return DocumentFormat.CSV
        if ext in (".xlsx", ".xls"):
            return DocumentFormat.XLSX
        if ext == ".json":
            return DocumentFormat.JSON

        # 6. CSV heuristics (text lines with comma separators)
        try:
            sample_text = content_bytes[:2048].decode('utf-8', errors='ignore')
            lines = [line for line in sample_text.splitlines() if line.strip()]
            if len(lines) >= 2 and all(',' in line for line in lines[:5]):
                return DocumentFormat.CSV
        except Exception:
            pass

        return DocumentFormat.UNKNOWN


class AcquisitionConfig:
    """Configuration settings for the acquisition pipeline."""

    def __init__(
        self,
        raw_storage_dir: str = "data/raw/political_funding",
        manifest_filename: str = "manifest.json",
        rate_limit_seconds: float = 1.0,
        timeout_seconds: float = 15.0,
        max_retries: int = 3,
        backoff_factor: float = 1.5,
        allowed_parties: Optional[List[str]] = None,
        allowed_years: Optional[List[str]] = None,
        allowed_sources: Optional[List[str]] = None,
        user_agent: str = "CIVICLENS-TN-Bot/1.0 (+https://civiclens.tn.gov.in/bot)"
    ):
        self.raw_storage_dir = raw_storage_dir
        self.manifest_path = os.path.join(raw_storage_dir, manifest_filename)
        self.rate_limit_seconds = rate_limit_seconds
        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor
        self.allowed_parties = allowed_parties or [
            "DMK", "AIADMK", "INC", "BJP", "PMK", "VCK", "NTK", "DMDK"
        ]
        self.allowed_years = allowed_years or [
            "FY2016-17", "FY2017-18", "FY2018-19", "FY2019-20",
            "FY2020-21", "FY2021-22", "FY2022-23", "FY2023-24", "FY2024-25"
        ]
        self.allowed_sources = allowed_sources
        self.user_agent = user_agent


class SourceRegistry:
    """Official source registry for statutory political finance document endpoints."""

    DEFAULT_SOURCES: Dict[str, Dict[str, Any]] = {
        "SRC-ECI-24A": {
            "source_name": "ECI Form 24A Contribution Disclosures",
            "base_url": "https://www.eci.gov.in/contribution-reports",
            "allowed_domain": "eci.gov.in",
            "supported_formats": [DocumentFormat.PDF, DocumentFormat.HTML],
            "statutory_tier": 1,
            "requires_auth": False
        },
        "SRC-ECI-AUDIT": {
            "source_name": "ECI Annual Audited Accounts",
            "base_url": "https://www.eci.gov.in/annual-audit-reports",
            "allowed_domain": "eci.gov.in",
            "supported_formats": [DocumentFormat.PDF, DocumentFormat.HTML],
            "statutory_tier": 1,
            "requires_auth": False
        },
        "SRC-ECI-TRUSTS": {
            "source_name": "Electoral Trust Contribution Reports",
            "base_url": "https://www.eci.gov.in/electoral-trusts-reports",
            "allowed_domain": "eci.gov.in",
            "supported_formats": [DocumentFormat.PDF, DocumentFormat.HTML],
            "statutory_tier": 1,
            "requires_auth": False
        },
        "SRC-ADR-DONATIONS": {
            "source_name": "ADR Political Party Watch Donation Reports",
            "base_url": "https://www.adrindia.org/content/donation-report",
            "allowed_domain": "adrindia.org",
            "supported_formats": [DocumentFormat.HTML, DocumentFormat.PDF, DocumentFormat.CSV],
            "statutory_tier": 2,
            "requires_auth": False
        },
        "SRC-SBI-BONDS": {
            "source_name": "Electoral Bond Disclosures SBI/ECI",
            "base_url": "https://www.eci.gov.in/electoral-bonds",
            "allowed_domain": "eci.gov.in",
            "supported_formats": [DocumentFormat.CSV, DocumentFormat.PDF, DocumentFormat.XLSX],
            "statutory_tier": 1,
            "requires_auth": False
        },
        "SRC-ECI-EXPENSE": {
            "source_name": "Political Party Election Expenditure Statements",
            "base_url": "https://www.eci.gov.in/candidate-politicalparty",
            "allowed_domain": "eci.gov.in",
            "supported_formats": [DocumentFormat.PDF, DocumentFormat.HTML],
            "statutory_tier": 1,
            "requires_auth": False
        }
    }

    def __init__(self, sources: Optional[Dict[str, Dict[str, Any]]] = None):
        self.sources = sources or self.DEFAULT_SOURCES

    def get_source(self, source_id: str) -> Optional[Dict[str, Any]]:
        return self.sources.get(source_id)

    def is_domain_allowed(self, source_id: str, url: str) -> bool:
        src = self.get_source(source_id)
        if not src:
            return False
        parsed = urllib.parse.urlparse(url)
        return src["allowed_domain"].lower() in parsed.netloc.lower()


class DownloadManifest:
    """Manages raw document inventory manifest (data/raw/political_funding/manifest.json)."""

    def __init__(self, manifest_path: str):
        self.manifest_path = manifest_path
        self.data: Dict[str, Any] = self._load()

    def _load(self) -> Dict[str, Any]:
        if os.path.exists(self.manifest_path):
            try:
                with open(self.manifest_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Error reading manifest file at {self.manifest_path}: {e}")

        return {
            "manifest_version": "1.0",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "summary": {
                "total_documents": 0,
                "total_bytes": 0,
                "unique_sha256_hashes": 0,
                "duplicates_count": 0,
                "failed_downloads_count": 0
            },
            "documents": {},
            "failed_downloads": []
        }

    def save(self) -> None:
        os.makedirs(os.path.dirname(self.manifest_path), exist_ok=True)
        self.data["updated_at"] = datetime.now(timezone.utc).isoformat()
        
        # Recalculate summary metrics
        docs = self.data["documents"]
        unique_hashes = set(d["sha256_hash"] for d in docs.values() if d.get("sha256_hash"))
        duplicates = sum(1 for d in docs.values() if d.get("is_duplicate"))
        total_bytes = sum(d.get("file_size_bytes", 0) for d in docs.values())

        self.data["summary"] = {
            "total_documents": len(docs),
            "total_bytes": total_bytes,
            "unique_sha256_hashes": len(unique_hashes),
            "duplicates_count": duplicates,
            "failed_downloads_count": len(self.data.get("failed_downloads", []))
        }

        with open(self.manifest_path, "w", encoding="utf-8") as f:
            json.dump(self.data, f, indent=2, ensure_ascii=False)

    def is_cached_url(self, url: str) -> Optional[Dict[str, Any]]:
        for doc in self.data["documents"].values():
            if doc.get("source_url") == url and doc.get("status") in ("SUCCESS", "CACHED"):
                if os.path.exists(doc.get("file_path", "")):
                    return doc
        return None

    def find_by_hash(self, sha256_hash: str) -> Optional[Dict[str, Any]]:
        for doc in self.data["documents"].values():
            if doc.get("sha256_hash") == sha256_hash and doc.get("status") in ("SUCCESS", "CACHED"):
                return doc
        return None

    def add_document(self, doc_entry: Dict[str, Any]) -> None:
        doc_id = doc_entry["document_id"]
        self.data["documents"][doc_id] = doc_entry
        self.save()

    def add_failure(self, failure_entry: Dict[str, Any]) -> None:
        self.data["failed_downloads"].append(failure_entry)
        self.save()


class DocumentAcquisitionEngine:
    """Core engine for acquiring statutory political funding documents."""

    def __init__(self, config: Optional[AcquisitionConfig] = None, registry: Optional[SourceRegistry] = None):
        self.config = config or AcquisitionConfig()
        self.registry = registry or SourceRegistry()
        self.manifest = DownloadManifest(self.config.manifest_path)
        self.last_request_time: Dict[str, float] = {}

        os.makedirs(self.config.raw_storage_dir, exist_ok=True)

    def _enforce_rate_limit(self, domain: str) -> None:
        last = self.last_request_time.get(domain, 0.0)
        elapsed = time.time() - last
        if elapsed < self.config.rate_limit_seconds:
            time.sleep(self.config.rate_limit_seconds - elapsed)
        self.last_request_time[domain] = time.time()

    def compute_sha256(self, content_bytes: bytes) -> str:
        return hashlib.sha256(content_bytes).hexdigest()

    def matches_filters(self, party_code: Optional[str] = None, year: Optional[str] = None, source_id: Optional[str] = None) -> bool:
        if source_id and self.config.allowed_sources and source_id not in self.config.allowed_sources:
            return False
        if party_code and self.config.allowed_parties and party_code.upper() not in self.config.allowed_parties:
            return False
        if year and self.config.allowed_years and year not in self.config.allowed_years:
            return False
        return True

    def acquire_document(
        self,
        url: str,
        source_id: str,
        party_code: Optional[str] = None,
        financial_year: Optional[str] = None,
        custom_filename: Optional[str] = None,
        mock_content: Optional[bytes] = None,
        force_redownload: bool = False
    ) -> Dict[str, Any]:
        """
        Acquires a single financial document from URL (or local mock stream in test mode).
        Handles caching, file type detection, SHA-256 checksums, duplicate detection,
        retries, and manifest updates.
        """
        if not self.matches_filters(party_code=party_code, year=financial_year, source_id=source_id):
            logger.info(f"Skipping acquisition for {url} (Filters: party={party_code}, year={financial_year}, source={source_id})")
            return {"status": "SKIPPED", "reason": "Filtered by user rules"}

        src_info = self.registry.get_source(source_id)
        if not src_info:
            raise ValueError(f"Unregistered source ID: {source_id}")

        # Check Cache
        cached = self.manifest.is_cached_url(url)
        if cached and not force_redownload:
            logger.info(f"Cache hit for URL {url} -> {cached['file_path']}")
            return {**cached, "status": "CACHED"}

        parsed_url = urllib.parse.urlparse(url)
        domain = parsed_url.netloc

        content_bytes = b""
        content_type_hdr = ""
        fetch_error = None

        if mock_content is not None:
            # Test fixture / mock mode
            content_bytes = mock_content
            content_type_hdr = "application/pdf" if mock_content.startswith(b"%PDF") else "text/html"
        else:
            # Domain check
            if not self.registry.is_domain_allowed(source_id, url):
                err_msg = f"URL domain '{domain}' not permitted for source '{source_id}'"
                logger.error(err_msg)
                self.manifest.add_failure({
                    "url": url,
                    "source_id": source_id,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "error": err_msg
                })
                return {"status": "FAILED", "reason": err_msg}

            # Download with Retry & Rate Limiting
            req = urllib.request.Request(url, headers={"User-Agent": self.config.user_agent})
            for attempt in range(1, self.config.max_retries + 1):
                try:
                    self._enforce_rate_limit(domain)
                    with urllib.request.urlopen(req, timeout=self.config.timeout_seconds) as resp:
                        content_bytes = resp.read()
                        content_type_hdr = resp.headers.get("Content-Type", "")
                        fetch_error = None
                        break
                except Exception as e:
                    fetch_error = str(e)
                    logger.warning(f"Download attempt {attempt}/{self.config.max_retries} failed for {url}: {e}")
                    if attempt < self.config.max_retries:
                        time.sleep(self.config.rate_limit_seconds * (self.config.backoff_factor ** attempt))

        if fetch_error or not content_bytes:
            err_msg = fetch_error or "Empty payload received"
            self.manifest.add_failure({
                "url": url,
                "source_id": source_id,
                "party_code": party_code,
                "financial_year": financial_year,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "error": err_msg
            })
            return {"status": "FAILED", "reason": err_msg}

        # Checksum & File Type Detection
        sha256_hash = self.compute_sha256(content_bytes)
        detected_format = FileTypeDetector.detect_format(content_bytes, url, content_type_hdr)

        # Duplicate Detection
        existing_doc = self.manifest.find_by_hash(sha256_hash)
        is_duplicate = existing_doc is not None
        duplicate_of = existing_doc["document_id"] if existing_doc else None

        # Storage Path Strategy
        party_str = (party_code or "COMMON").upper()
        year_str = financial_year or "GENERAL"
        dest_dir = os.path.join(self.config.raw_storage_dir, source_id, year_str)
        os.makedirs(dest_dir, exist_ok=True)

        ext = detected_format.lower() if detected_format != DocumentFormat.UNKNOWN else "bin"
        if custom_filename:
            file_name = custom_filename
        else:
            file_name = f"{party_str}_{year_str}_{sha256_hash[:8]}.{ext}"

        file_path = os.path.join(dest_dir, file_name)

        # Write Raw File
        with open(file_path, "wb") as f:
            f.write(content_bytes)

        # Create Manifest Entry
        doc_id = f"DOC_{source_id}_{party_str}_{year_str}_{sha256_hash[:8]}"
        doc_entry = {
            "document_id": doc_id,
            "source_id": source_id,
            "source_name": src_info["source_name"],
            "source_url": url,
            "party_code": party_code,
            "financial_year": financial_year,
            "retrieval_timestamp": datetime.now(timezone.utc).isoformat(),
            "file_path": file_path,
            "file_size_bytes": len(content_bytes),
            "sha256_hash": sha256_hash,
            "detected_format": detected_format,
            "is_duplicate": is_duplicate,
            "duplicate_of": duplicate_of,
            "status": "SUCCESS"
        }

        self.manifest.add_document(doc_entry)
        logger.info(f"Acquired document {doc_id} -> {file_path} (Format: {detected_format}, Bytes: {len(content_bytes)})")
        return doc_entry

    def discover_and_acquire(
        self,
        discovery_targets: List[Dict[str, Any]],
        mock_payload_map: Optional[Dict[str, bytes]] = None
    ) -> List[Dict[str, Any]]:
        """
        Batch acquires discovery target dicts containing url, source_id, party_code, financial_year.
        """
        results = []
        for target in discovery_targets:
            url = target["url"]
            source_id = target["source_id"]
            party = target.get("party_code")
            fy = target.get("financial_year")
            mock_data = mock_payload_map.get(url) if mock_payload_map else None

            res = self.acquire_document(
                url=url,
                source_id=source_id,
                party_code=party,
                financial_year=fy,
                mock_content=mock_data
            )
            results.append(res)
        return results
