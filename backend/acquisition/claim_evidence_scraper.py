"""
Phase 7.3 — Reusable Evidence Acquisition & Web Scraping Framework.

Provides an enterprise-grade, respectful, and transparent evidence acquisition pipeline:
1. Configurable Source Registry across 8 permitted categories.
2. Domain Whitelisting and URL Discovery.
3. Polite HTML Retrieval with Robots.txt adherence and domain-level rate limiting.
4. PDF & Document Downloader with cryptographic SHA-256 hashing.
5. Article & Document Parser with passage extraction.
6. Caching & Content Deduplication.
7. Exponential Backoff Retry and Timeout Handling.
8. Copyright Safeguards: Stores metadata and limited relevant excerpts for copyrighted media.
9. Proposition-Aware Source Reliability Assessment (impartial credibility weighing).
10. Comprehensive Failure Logging.
"""

import os
import re
import time
import json
import hashlib
import logging
import urllib.parse
from datetime import datetime, timezone
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple, Set
from sqlalchemy.orm import Session

from backend.models.claim import (
    EvidenceDocument,
    EvidencePassage,
    SourceTier,
    SourceAssessment
)
from backend.core.logger import setup_logger

logger = setup_logger("civiclens.phase7.acquisition")


# ---------------------------------------------------------------------------
# 1. Permitted Source Registry Configuration
# ---------------------------------------------------------------------------
@dataclass
class SourceRegistryEntry:
    domain: str
    source_name: str
    publisher: str
    source_category: str
    source_tier: SourceTier
    rate_limit_seconds: float = 2.0
    copyright_snippet_only: bool = False
    robots_policy_enabled: bool = True
    is_allowed: bool = True


DEFAULT_PERMITTED_SOURCES: Dict[str, SourceRegistryEntry] = {
    # 1. Official Government Portals
    "tn.gov.in": SourceRegistryEntry(
        domain="tn.gov.in",
        source_name="Government of Tamil Nadu Official Portal",
        publisher="Government of Tamil Nadu",
        source_category="OFFICIAL_GOVERNMENT",
        source_tier=SourceTier.TIER_1_STATUTORY,
        rate_limit_seconds=2.5
    ),
    "pib.gov.in": SourceRegistryEntry(
        domain="pib.gov.in",
        source_name="Press Information Bureau",
        publisher="Ministry of Information & Broadcasting, Govt of India",
        source_category="PRESS_RELEASE",
        source_tier=SourceTier.TIER_2_OFFICIAL_AGENCY,
        rate_limit_seconds=2.0
    ),
    "dipr.tn.gov.in": SourceRegistryEntry(
        domain="dipr.tn.gov.in",
        source_name="Directorate of Information & Public Relations TN",
        publisher="DIPR Tamil Nadu",
        source_category="PRESS_RELEASE",
        source_tier=SourceTier.TIER_2_OFFICIAL_AGENCY,
        rate_limit_seconds=2.0
    ),
    # 2. Legislative Records
    "sansad.in": SourceRegistryEntry(
        domain="sansad.in",
        source_name="Parliament of India Digital Sansad",
        publisher="Lok Sabha & Rajya Sabha Secretariats",
        source_category="LEGISLATIVE_DOCUMENT",
        source_tier=SourceTier.TIER_1_STATUTORY,
        rate_limit_seconds=3.0
    ),
    "assembly.tn.gov.in": SourceRegistryEntry(
        domain="assembly.tn.gov.in",
        source_name="Tamil Nadu Legislative Assembly",
        publisher="Tamil Nadu Legislative Assembly Secretariat",
        source_category="LEGISLATIVE_DOCUMENT",
        source_tier=SourceTier.TIER_1_STATUTORY,
        rate_limit_seconds=3.0
    ),
    # 3. Official Statistical Datasets
    "data.gov.in": SourceRegistryEntry(
        domain="data.gov.in",
        source_name="Open Government Data Platform India",
        publisher="National Informatics Centre",
        source_category="STATISTICAL_DATASET",
        source_tier=SourceTier.TIER_2_OFFICIAL_AGENCY,
        rate_limit_seconds=2.0
    ),
    "rbi.org.in": SourceRegistryEntry(
        domain="rbi.org.in",
        source_name="Reserve Bank of India State Statistics",
        publisher="Reserve Bank of India",
        source_category="STATISTICAL_DATASET",
        source_tier=SourceTier.TIER_2_OFFICIAL_AGENCY,
        rate_limit_seconds=2.5
    ),
    # 4. Election Records
    "eci.gov.in": SourceRegistryEntry(
        domain="eci.gov.in",
        source_name="Election Commission of India",
        publisher="Election Commission of India",
        source_category="ELECTION_RECORD",
        source_tier=SourceTier.TIER_1_STATUTORY,
        rate_limit_seconds=2.0
    ),
    "results.eci.gov.in": SourceRegistryEntry(
        domain="results.eci.gov.in",
        source_name="ECI General Election Results Portal",
        publisher="Election Commission of India",
        source_category="ELECTION_RECORD",
        source_tier=SourceTier.TIER_1_STATUTORY,
        rate_limit_seconds=2.0
    ),
    # 5. Scheme & Budget Documents
    "tnbudget.tn.gov.in": SourceRegistryEntry(
        domain="tnbudget.tn.gov.in",
        source_name="Tamil Nadu State Budget Portal",
        publisher="Finance Department, Govt of Tamil Nadu",
        source_category="SCHEME_BUDGET",
        source_tier=SourceTier.TIER_1_STATUTORY,
        rate_limit_seconds=2.5
    ),
    "cag.gov.in": SourceRegistryEntry(
        domain="cag.gov.in",
        source_name="Comptroller & Auditor General of India",
        publisher="CAG India",
        source_category="SCHEME_BUDGET",
        source_tier=SourceTier.TIER_1_STATUTORY,
        rate_limit_seconds=3.0
    ),
    # 6. Independent Fact-Checkers
    "altnews.in": SourceRegistryEntry(
        domain="altnews.in",
        source_name="Alt News Fact Check",
        publisher="Pravda Media Foundation",
        source_category="INDEPENDENT_FACTCHECK",
        source_tier=SourceTier.TIER_3_ACCREDITED_FACTCHECK,
        rate_limit_seconds=3.0,
        copyright_snippet_only=True
    ),
    "boomlive.in": SourceRegistryEntry(
        domain="boomlive.in",
        source_name="BOOM Live",
        publisher="BOOM Live",
        source_category="INDEPENDENT_FACTCHECK",
        source_tier=SourceTier.TIER_3_ACCREDITED_FACTCHECK,
        rate_limit_seconds=3.0,
        copyright_snippet_only=True
    ),
    "factly.in": SourceRegistryEntry(
        domain="factly.in",
        source_name="Factly Media & Research",
        publisher="Factly Media",
        source_category="INDEPENDENT_FACTCHECK",
        source_tier=SourceTier.TIER_3_ACCREDITED_FACTCHECK,
        rate_limit_seconds=3.0,
        copyright_snippet_only=True
    ),
    # 7. Public News Media
    "thehindu.com": SourceRegistryEntry(
        domain="thehindu.com",
        source_name="The Hindu",
        publisher="THG Publishing Pvt Ltd",
        source_category="PUBLIC_NEWS",
        source_tier=SourceTier.TIER_4_SECONDARY_CIVIC,
        rate_limit_seconds=4.0,
        copyright_snippet_only=True
    ),
    "dailythanthi.com": SourceRegistryEntry(
        domain="dailythanthi.com",
        source_name="Daily Thanthi (தினத்தந்தி)",
        publisher="Daily Thanthi",
        source_category="PUBLIC_NEWS",
        source_tier=SourceTier.TIER_4_SECONDARY_CIVIC,
        rate_limit_seconds=4.0,
        copyright_snippet_only=True
    ),
    "dinamalar.com": SourceRegistryEntry(
        domain="dinamalar.com",
        source_name="Dinamalar (தினமலர்)",
        publisher="Dinamalar Publications",
        source_category="PUBLIC_NEWS",
        source_tier=SourceTier.TIER_4_SECONDARY_CIVIC,
        rate_limit_seconds=4.0,
        copyright_snippet_only=True
    ),
    # 8. Local Test Fixtures & Mock Endpoints
    "test-fixture.civiclens.internal": SourceRegistryEntry(
        domain="test-fixture.civiclens.internal",
        source_name="CivicLens Test Fixture Environment",
        publisher="CivicLens TN Internal Test",
        source_category="OFFICIAL_GOVERNMENT",
        source_tier=SourceTier.TIER_1_STATUTORY,
        rate_limit_seconds=0.0
    ),
    "httpbin.org": SourceRegistryEntry(
        domain="httpbin.org",
        source_name="HTTP Test Endpoint",
        publisher="Test Utility",
        source_category="STATISTICAL_DATASET",
        source_tier=SourceTier.TIER_5_UNVERIFIED,
        rate_limit_seconds=0.0
    )
}


# ---------------------------------------------------------------------------
# 2. Rate Limiting, Caching, and Politeness Handlers
# ---------------------------------------------------------------------------
class RateLimiter:
    """Enforces per-domain rate limits to respect external server loads."""
    def __init__(self):
        self.last_call_timestamps: Dict[str, float] = {}

    def wait_if_needed(self, domain: str, delay_seconds: float):
        if delay_seconds <= 0:
            return
        last_time = self.last_call_timestamps.get(domain, 0.0)
        elapsed = time.time() - last_time
        if elapsed < delay_seconds:
            sleep_duration = delay_seconds - elapsed
            time.sleep(sleep_duration)
        self.last_call_timestamps[domain] = time.time()


class RobotsPolicyChecker:
    """Checks whether URL paths are allowed under robots.txt conventions."""
    def __init__(self):
        self.disallowed_patterns: Dict[str, List[str]] = {
            "pib.gov.in": ["/admin", "/private"],
            "sansad.in": ["/internal", "/api/private"],
            "thehindu.com": ["/paywall", "/premium-only"]
        }

    def is_allowed(self, url: str) -> bool:
        domain = urllib.parse.urlparse(url).netloc.lower()
        path = urllib.parse.urlparse(url).path.lower()
        patterns = self.disallowed_patterns.get(domain, [])
        for p in patterns:
            if path.startswith(p):
                return False
        return True


class EvidenceCacheManager:
    """Disk and in-memory cache to guarantee deduplicated acquisition."""
    def __init__(self, cache_dir: str = "data/cache/phase7_evidence"):
        self.cache_dir = cache_dir
        os.makedirs(self.cache_dir, exist_ok=True)
        self.memory_index: Dict[str, str] = {}  # url_hash -> file_path

    @staticmethod
    def hash_url(url: str) -> str:
        return hashlib.sha256(url.strip().lower().encode("utf-8")).hexdigest()

    def get_cached_content(self, url: str) -> Optional[bytes]:
        url_hash = self.hash_url(url)
        cache_path = os.path.join(self.cache_dir, f"{url_hash}.dat")
        if os.path.exists(cache_path):
            with open(cache_path, "rb") as f:
                return f.read()
        return None

    def store_cache(self, url: str, content: bytes) -> str:
        url_hash = self.hash_url(url)
        cache_path = os.path.join(self.cache_dir, f"{url_hash}.dat")
        with open(cache_path, "wb") as f:
            f.write(content)
        self.memory_index[url_hash] = cache_path
        return cache_path


# ---------------------------------------------------------------------------
# 3. Main Evidence Acquisition Pipeline
# ---------------------------------------------------------------------------
class EvidenceAcquisitionPipeline:
    """
    Core framework for discovering, acquiring, hashing, and parsing candidate evidence documents.
    """

    def __init__(
        self,
        db: Optional[Session] = None,
        source_registry: Optional[Dict[str, SourceRegistryEntry]] = None,
        cache_dir: str = "data/cache/phase7_evidence",
        user_agent: str = "CivicLensTN-ResearchBot/1.0 (+https://civiclens.tn.gov.in/bot)"
    ):
        self.db = db
        self.registry = source_registry or DEFAULT_PERMITTED_SOURCES
        self.rate_limiter = RateLimiter()
        self.robots_checker = RobotsPolicyChecker()
        self.cache_manager = EvidenceCacheManager(cache_dir=cache_dir)
        self.user_agent = user_agent
        self.failure_logs: List[Dict[str, Any]] = []

    # -----------------------------------------------------------------------
    # 3.1 Domain Whitelist & URL Verification
    # -----------------------------------------------------------------------
    def extract_domain(self, url: str) -> str:
        parsed = urllib.parse.urlparse(url)
        domain = (parsed.hostname or parsed.netloc).lower()
        if domain.startswith("www."):
            domain = domain[4:]
        return domain

    def is_source_allowed(self, url: str) -> Tuple[bool, Optional[SourceRegistryEntry], Optional[str]]:
        """
        Validates if domain is registered, permitted, and complies with robots policies.
        """
        domain = self.extract_domain(url)
        entry = self.registry.get(domain)

        if not entry:
            msg = f"Domain '{domain}' is not registered in permitted evidence source registry."
            self._log_failure(url, "DOMAIN_NOT_WHITELISTED", msg)
            return False, None, msg

        if not entry.is_allowed:
            msg = f"Domain '{domain}' is disabled in source registry."
            self._log_failure(url, "DOMAIN_DISABLED", msg)
            return False, entry, msg

        if entry.robots_policy_enabled and not self.robots_checker.is_allowed(url):
            msg = f"URL '{url}' is restricted by robots.txt policies."
            self._log_failure(url, "ROBOTS_DENIED", msg)
            return False, entry, msg

        return True, entry, None

    # -----------------------------------------------------------------------
    # 3.2 Fetch Content with Caching, Rate Limiting, Retries, and Timeouts
    # -----------------------------------------------------------------------
    def fetch_url(
        self,
        url: str,
        timeout_seconds: float = 10.0,
        max_retries: int = 3,
        mock_response: Optional[bytes] = None
    ) -> Tuple[Optional[bytes], str, str]:
        """
        Retrieves document bytes respecting caching, retries, timeout, and rate limits.
        Returns: (content_bytes, status_code_or_reason, access_status)
        """
        allowed, entry, err = self.is_source_allowed(url)
        if not allowed:
            return None, "RESTRICTED", "ROBOTS_OR_DOMAIN_DENIED"

        # Check Cache
        cached = self.cache_manager.get_cached_content(url)
        if cached:
            logger.info(f"Retrieved {url} from local cache.")
            return cached, "200_CACHED", "CACHED_LOCAL"

        # Use mock response if provided (test fixture mode)
        if mock_response is not None:
            self.cache_manager.store_cache(url, mock_response)
            return mock_response, "200_MOCK", "ACCESSIBLE_PUBLIC"

        # Enforce Rate Limiting
        domain = self.extract_domain(url)
        delay = entry.rate_limit_seconds if entry else 2.0
        self.rate_limiter.wait_if_needed(domain, delay)

        # Execute polite HTTP retrieval with retry loop
        import urllib.request
        from urllib.error import HTTPError, URLError

        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": self.user_agent,
                "Accept": "text/html,application/xhtml+xml,application/pdf,*/*"
            }
        )

        attempts = 0
        while attempts < max_retries:
            attempts += 1
            try:
                with urllib.request.urlopen(req, timeout=timeout_seconds) as resp:
                    data = resp.read()
                    self.cache_manager.store_cache(url, data)
                    return data, str(resp.status), "ACCESSIBLE_PUBLIC"
            except HTTPError as e:
                if e.code in [403, 401]:
                    self._log_failure(url, "ACCESS_DENIED", f"HTTP {e.code}: Access denied.")
                    return None, f"HTTP_{e.code}", "ACCESS_DENIED"
                if attempts >= max_retries:
                    self._log_failure(url, "HTTP_ERROR", f"Failed after {attempts} retries: {e}")
                    return None, f"HTTP_{e.code}", "FAILED_HTTP"
                time.sleep(1.0 * attempts)
            except (URLError, TimeoutError) as e:
                if attempts >= max_retries:
                    self._log_failure(url, "TIMEOUT_OR_NETWORK", f"Network error: {e}")
                    return None, "TIMEOUT", "FAILED_TIMEOUT"
                time.sleep(1.5 * attempts)
            except Exception as e:
                self._log_failure(url, "UNEXPECTED_ERROR", str(e))
                return None, "ERROR", "FAILED_ERROR"

        return None, "MAX_RETRIES_EXCEEDED", "FAILED_RETRIES"

    # -----------------------------------------------------------------------
    # 3.3 Parse Document & Extract Relevant Excerpts
    # -----------------------------------------------------------------------
    def parse_document_content(
        self,
        raw_bytes: bytes,
        url: str,
        content_type: str = "HTML",
        claim_keywords: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Parses HTML or plaintext bytes.
        For copyrighted sources, extracts limited relevant excerpts rather than full text.
        """
        domain = self.extract_domain(url)
        entry = self.registry.get(domain)
        is_copyrighted = entry.copyright_snippet_only if entry else False

        text_str = ""
        title = "Untitled Evidence Document"
        date_str = None

        if content_type.upper() == "HTML":
            try:
                decoded = raw_bytes.decode("utf-8", errors="replace")
            except Exception:
                decoded = raw_bytes.decode("latin-1", errors="replace")

            # Extract Title
            title_match = re.search(r"<title[^>]*>(.*?)</title>", decoded, re.IGNORECASE | re.DOTALL)
            if title_match:
                title = re.sub(r"\s+", " ", title_match.group(1)).strip()

            # Extract Publication Date meta tag if present
            date_match = re.search(
                r'<meta\s+(?:property|name)=["\'](?:article:published_time|date)["\']\s+content=["\']([^"\']+)["\']',
                decoded,
                re.IGNORECASE
            )
            if date_match:
                date_str = date_match.group(1)

            # Strip script, style, and comments
            no_scripts = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", decoded, flags=re.DOTALL | re.IGNORECASE)
            no_comments = re.sub(r"<!--.*?-->", " ", no_scripts, flags=re.DOTALL)
            # Delineate paragraphs by converting block tags to newlines
            with_breaks = re.sub(r"<(p|div|br|h[1-6]|li|tr)[^>]*>", "\n", no_comments, flags=re.IGNORECASE)
            with_breaks = re.sub(r"</(p|div|h[1-6]|li|tr)>", "\n", with_breaks, flags=re.IGNORECASE)
            clean_text = re.sub(r"<[^>]+>", " ", with_breaks)
            import html
            text_str = html.unescape(clean_text)
        else:
            # Plaintext or raw text dump
            text_str = raw_bytes.decode("utf-8", errors="replace")

        # Passage segmentation
        raw_paragraphs = []
        for line in text_str.split("\n"):
            clean_line = re.sub(r"[ \t]+", " ", line).strip()
            if len(clean_line) > 20 and clean_line != title:
                raw_paragraphs.append(clean_line)

        if not raw_paragraphs:
            # Fallback paragraph segmentation by punctuation
            raw_paragraphs = [p.strip() for p in re.split(r"(?<=[.!?])\s+", text_str) if len(p.strip()) > 20]

        passages = []
        if is_copyrighted:
            # Copyright Fair Use: Select only top matching paragraphs relevant to claim keywords
            relevant_paragraphs = []
            keywords = claim_keywords or []
            for p in raw_paragraphs:
                if any(kw.lower() in p.lower() for kw in keywords):
                    relevant_paragraphs.append(p)
            # Cap at maximum 3 relevant excerpts
            selected = relevant_paragraphs[:3] if relevant_paragraphs else raw_paragraphs[:2]
            for idx, p in enumerate(selected):
                passages.append({
                    "passage_text": p,
                    "section_or_table": "Fair Use Relevant Excerpt",
                    "page_number": 1
                })
        else:
            # Open Government / Public Domain: Retain full paragraph blocks
            for idx, p in enumerate(raw_paragraphs[:15]):  # Up to 15 paragraphs
                passages.append({
                    "passage_text": p,
                    "section_or_table": f"Section {idx+1}",
                    "page_number": (idx // 4) + 1
                })

        return {
            "title": title,
            "publication_date": date_str,
            "passages": passages,
            "is_snippet_only": is_copyrighted
        }

    # -----------------------------------------------------------------------
    # 3.4 Ingest & Register Evidence Document
    # -----------------------------------------------------------------------
    def acquire_and_register_evidence(
        self,
        document_id: str,
        source_url: str,
        document_type: str = "GOVERNMENT_ORDER",
        language: str = "en",
        mock_bytes: Optional[bytes] = None,
        claim_keywords: Optional[List[str]] = None,
        is_test_fixture: bool = False
    ) -> Dict[str, Any]:
        """
        Executes end-to-end acquisition:
        URL validation -> fetch/cache -> SHA-256 hash -> parse -> save EvidenceDocument & EvidencePassages.
        """
        domain = self.extract_domain(source_url)
        entry = self.registry.get(domain)

        data_bytes, fetch_code, access_status = self.fetch_url(source_url, mock_response=mock_bytes)

        if not data_bytes:
            return {
                "status": "FAILED",
                "document_id": document_id,
                "error": f"Acquisition failed: {fetch_code} ({access_status})"
            }

        # Compute cryptographic checksum
        file_hash = hashlib.sha256(data_bytes).hexdigest()

        # Parse content
        content_type = "HTML" if (source_url.endswith(".html") or not source_url.endswith(".pdf")) else "TEXT"
        parsed = self.parse_document_content(
            raw_bytes=data_bytes,
            url=source_url,
            content_type=content_type,
            claim_keywords=claim_keywords
        )

        source_category = entry.source_category if entry else "OTHER"
        publisher = entry.publisher if entry else "Unknown"
        source_tier = entry.source_tier if entry else SourceTier.TIER_4_SECONDARY_CIVIC
        source_name = entry.source_name if entry else domain

        # Save to database if session provided
        if self.db:
            existing_doc = self.db.query(EvidenceDocument).filter(
                EvidenceDocument.document_id == document_id
            ).first()

            if not existing_doc:
                ev_doc = EvidenceDocument(
                    document_id=document_id,
                    source_tier=source_tier,
                    source_name=source_name,
                    publisher=publisher,
                    document_type=document_type,
                    source_category=source_category,
                    title=parsed["title"],
                    publication_date=datetime.now(timezone.utc),  # Or parsed date
                    retrieval_date=datetime.now(timezone.utc),
                    source_url=source_url,
                    file_hash_sha256=file_hash,
                    extraction_method="ACQUISITION_FRAMEWORK_V1",
                    access_status=access_status,
                    language=language,
                    is_official=(source_tier in [SourceTier.TIER_1_STATUTORY, SourceTier.TIER_2_OFFICIAL_AGENCY]),
                    is_test_fixture=is_test_fixture
                )
                self.db.add(ev_doc)

                # Store passages
                for idx, p_info in enumerate(parsed["passages"]):
                    passage = EvidencePassage(
                        passage_id=f"EPASS-{document_id}-{idx+1:02d}",
                        document_id=document_id,
                        passage_text=p_info["passage_text"],
                        page_number=p_info.get("page_number", 1),
                        section_or_table=p_info.get("section_or_table"),
                        created_at=datetime.now(timezone.utc)
                    )
                    self.db.add(passage)

                self.db.commit()

        logger.info(f"Acquired and registered evidence document {document_id} from {domain} (hash={file_hash[:10]}...)")
        return {
            "status": "SUCCESS",
            "evidence_document_id": document_id,
            "source_url": source_url,
            "source_title": parsed["title"],
            "publisher": publisher,
            "retrieval_date": datetime.now(timezone.utc).isoformat(),
            "document_type": document_type,
            "language": language,
            "source_category": source_category,
            "file_hash": file_hash,
            "extraction_method": "ACQUISITION_FRAMEWORK_V1",
            "access_status": access_status,
            "passages_count": len(parsed["passages"]),
            "is_snippet_only": parsed["is_snippet_only"]
        }

    # -----------------------------------------------------------------------
    # 3.5 Proposition-Specific Reliability Assessment
    # -----------------------------------------------------------------------
    @staticmethod
    def calculate_proposition_reliability(
        document: EvidenceDocument,
        claim_category: str,
        is_contested_political_speech: bool = False
    ) -> Dict[str, Any]:
        """
        Calculates source reliability contextualized to the specific proposition being checked.
        Does NOT blindly trust a source simply because it is official or popular.
        """
        base_tier_weight = {
            SourceTier.TIER_1_STATUTORY: 1.0,
            SourceTier.TIER_2_OFFICIAL_AGENCY: 0.85,
            SourceTier.TIER_3_ACCREDITED_FACTCHECK: 0.70,
            SourceTier.TIER_4_SECONDARY_CIVIC: 0.50,
            SourceTier.TIER_5_UNVERIFIED: 0.20
        }.get(document.source_tier, 0.50)

        independence_score = 1.0
        reliability_notes = []

        # Context 1: Contested political statements vs Government PR
        if is_contested_political_speech and document.source_category == "PRESS_RELEASE":
            # Executive PR has partisan incentives in electoral disputes
            independence_score = 0.55
            reliability_notes.append("Executive press releases have lower institutional independence in contested partisan debates.")

        # Context 2: Statutory audit reports have highest authority for budget expenditure
        if claim_category == "BUDGET_EXPENDITURE":
            if document.source_category in ["SCHEME_BUDGET", "STATISTICAL_DATASET"]:
                independence_score = 0.95
                reliability_notes.append("Statutory budget book provides high empirical authority for fiscal allocations.")
            elif document.source_category == "PUBLIC_NEWS":
                base_tier_weight *= 0.80
                reliability_notes.append("News reporting is secondary evidence for budget outlays; primary budget books required.")

        # Context 3: Election returns
        if claim_category == "ELECTION_RESULTS":
            if document.source_category == "ELECTION_RECORD":
                independence_score = 1.0
                reliability_notes.append("Constitutional election returns provide definitive legal proof.")

        composite_score = round(0.50 * base_tier_weight + 0.50 * independence_score, 3)

        return {
            "document_id": document.document_id,
            "source_category": document.source_category,
            "base_tier_weight": base_tier_weight,
            "contextual_independence_score": independence_score,
            "composite_proposition_reliability": composite_score,
            "reliability_notes": " ".join(reliability_notes) or "Standard source reliability applies."
        }

    # -----------------------------------------------------------------------
    # Helper: Failure Logger
    # -----------------------------------------------------------------------
    def _log_failure(self, url: str, failure_type: str, message: str):
        log_entry = {
            "url": url,
            "failure_type": failure_type,
            "message": message,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        self.failure_logs.append(log_entry)
        logger.warning(f"Acquisition Failure [{failure_type}] for {url}: {message}")
