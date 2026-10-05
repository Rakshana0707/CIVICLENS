"""
Government Implementation Evidence Acquisition Pipeline (Phase 3.9).

Acquires candidate government implementation evidence documents (GOs, Policy Notes,
Budget documents, Press Releases, Department pages) from strict allowed domains.

Pipeline:
Promise / Search Query -> Allowed Source Domains -> Web Acquisition -> Candidate Documents -> Document Extraction -> Evidence Records

Security & Politeness Rules:
- Enforces strict domain whitelisting (config/evidence_sources.json). Arbitrary websites are blocked.
- Uses PoliteHTTPClient (robots.txt, rate limits, politeness delays, User-Agent).
- Never circumvents access controls, CAPTCHAs, or paywalls.
- Does NOT perform implementation status assessment (ingestion pipeline only).
"""

import os
import json
import logging
import urllib.parse
import hashlib
import re
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy.orm import Session

from backend.acquisition.http_client import PoliteHTTPClient
from backend.models.common import Evidence

logger = logging.getLogger(__name__)

DEFAULT_EVIDENCE_CONFIG_PATH = os.path.join("config", "evidence_sources.json")


class EvidenceAcquisitionPipeline:
    """
    Pipeline orchestrating domain-restricted evidence document acquisition,
    content extraction, and evidence record creation.
    """

    def __init__(
        self,
        db_session: Optional[Session] = None,
        config_path: str = DEFAULT_EVIDENCE_CONFIG_PATH,
        cache_dir: str = "data/cache/evidence"
    ):
        self.db = db_session
        self.config_path = config_path
        self.cache_dir = cache_dir
        self.http_client = PoliteHTTPClient(cache_dir=self.cache_dir)

        self.allowed_domains: List[str] = []
        self.source_metadata: Dict[str, Dict[str, Any]] = {}
        self._load_config()

    def _load_config(self):
        if not os.path.exists(self.config_path):
            logger.warning(f"Evidence sources config not found at {self.config_path}. Using default government domains.")
            self.allowed_domains = ["tn.gov.in", "cms.tn.gov.in", "budget.tn.gov.in"]
            return

        with open(self.config_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            self.allowed_domains = data.get("allowed_domains", [])
            for src in data.get("sources", []):
                domain = src.get("domain")
                if domain:
                    self.source_metadata[domain] = src

    def is_domain_allowed(self, url: str) -> bool:
        """
        Validates that the target URL belongs to an explicitly allowed domain.
        """
        parsed = urllib.parse.urlparse(url)
        netloc = parsed.netloc.lower().split(":")[0]  # Remove port if present

        for allowed in self.allowed_domains:
            allowed_lower = allowed.lower()
            if netloc == allowed_lower or netloc.endswith("." + allowed_lower):
                return True
        return False

    def get_source_info(self, url: str) -> Dict[str, Any]:
        """Returns source metadata (source_type, source_tier) for a URL."""
        parsed = urllib.parse.urlparse(url)
        netloc = parsed.netloc.lower().split(":")[0]

        # 1. Check exact domain match first
        if netloc in self.source_metadata:
            return self.source_metadata[netloc]

        # 2. Check suffix match by longest domain first
        sorted_domains = sorted(self.source_metadata.keys(), key=len, reverse=True)
        for domain in sorted_domains:
            if netloc.endswith("." + domain):
                return self.source_metadata[domain]

        return {
            "domain": netloc,
            "source_name": "Government Source",
            "source_type": "Government website",
            "source_tier": 1
        }

    def _extract_publication_date(self, text: str) -> Optional[str]:
        """Infers publication date from document text if present."""
        date_match = re.search(
            r'(\b\d{1,2}[./-]\d{1,2}[./-]\d{4}\b|\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]* \d{1,2},? \d{4}\b|\bG\.O\.\s*Ms\.\s*No\.?\s*\d+,\s*dated\s*\d{1,2}[./-]\d{1,2}[./-]\d{4}\b)',
            text, re.IGNORECASE
        )
        return date_match.group(0) if date_match else None

    def _extract_text_chunks(self, content: bytes, doc_format: str) -> List[Tuple[int, str]]:
        """
        Extracts page-aware or paragraph-aware text chunks from bytes.
        Returns list of (page_number, text_chunk).
        """
        chunks = []
        if doc_format.upper() == "PDF":
            try:
                import io, pdfplumber
                with pdfplumber.open(io.BytesIO(content)) as pdf:
                    for i, page in enumerate(pdf.pages):
                        text = page.extract_text()
                        if text and text.strip():
                            chunks.append((i + 1, text.strip()))
            except Exception as e:
                logger.warning(f"PDF extraction fallback: {e}")
                text_str = content.decode("utf-8", errors="ignore")
                paras = [p.strip() for p in text_str.split("\n\n") if p.strip()]
                for i, p in enumerate(paras):
                    chunks.append((1, p))
        else:
            try:
                from html.parser import HTMLParser

                class SimpleHTMLParser(HTMLParser):
                    def __init__(self):
                        super().__init__()
                        self.text_blocks = []
                        self.current = []

                    def handle_data(self, data):
                        if data.strip():
                            self.current.append(data.strip())

                    def handle_endtag(self, tag):
                        if tag in ('p', 'div', 'h1', 'h2', 'h3', 'li') and self.current:
                            self.text_blocks.append(" ".join(self.current))
                            self.current = []

                parser = SimpleHTMLParser()
                parser.feed(content.decode("utf-8", errors="ignore"))
                if parser.current:
                    parser.text_blocks.append(" ".join(parser.current))
                for block in parser.text_blocks:
                    chunks.append((1, block))
            except Exception:
                text_str = content.decode("utf-8", errors="ignore")
                chunks.append((1, text_str.strip()))

        return chunks

    def fetch_and_extract_evidence(
        self,
        url: str,
        result_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Executes the acquisition pipeline for a single target URL.
        Verifies domain safety, downloads document, extracts evidence chunks, and persists.
        """
        if not self.is_domain_allowed(url):
            logger.error(f"Domain Security Rejection: URL {url} is not in the allowed domain list.")
            return []

        src_info = self.get_source_info(url)
        content, metadata = self.http_client.fetch(url)

        if not content or metadata.retrieval_status != "success":
            logger.error(f"Evidence fetch failed for {url}: {metadata.retrieval_status}")
            return []

        content_hash = metadata.content_hash or hashlib.sha256(content).hexdigest()
        doc_format = metadata.document_format or ("PDF" if url.lower().endswith(".pdf") else "HTML")

        chunks = self._extract_text_chunks(content, doc_format)
        evidence_records: List[Dict[str, Any]] = []

        now_iso = datetime.now(timezone.utc).isoformat()

        for page_num, text_chunk in chunks:
            pub_date = self._extract_publication_date(text_chunk)

            supporting_values = {
                "source_url": url,
                "source_domain": src_info.get("domain"),
                "source_name": src_info.get("source_name"),
                "source_type": src_info.get("source_type"),
                "source_tier": src_info.get("source_tier", 1),
                "publication_date": pub_date,
                "content_hash": content_hash,
                "acquisition_timestamp": now_iso
            }

            rec_dict = {
                "content": text_chunk,
                "page_number": page_num,
                "context": text_chunk[:200] + "..." if len(text_chunk) > 200 else text_chunk,
                "explanation": f"Acquired evidence from {src_info.get('source_type')} ({url})",
                "supporting_values": supporting_values,
                "result_type": "GovernmentEvidence",
                "result_id": result_id
            }

            if self.db is not None:
                ev = Evidence(
                    content=text_chunk,
                    page_number=page_num,
                    context=rec_dict["context"],
                    explanation=rec_dict["explanation"],
                    supporting_values=supporting_values,
                    result_type="GovernmentEvidence",
                    result_id=result_id
                )
                self.db.add(ev)
                self.db.commit()
                rec_dict["id"] = ev.id

            evidence_records.append(rec_dict)

        logger.info(f"Acquired {len(evidence_records)} evidence records from {url}")
        return evidence_records
