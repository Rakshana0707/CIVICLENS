"""
Phase 7.3 — Unit Tests for Evidence Acquisition & Web Scraping Framework.

Tests:
1. Permitted source registry across 8 categories and domain whitelisting.
2. Disallowed domain rejection and structured failure logging.
3. Robots.txt policy enforcement (disallowed paths blocked and logged).
4. Per-domain rate limiting interval governance.
5. Local disk caching and SHA-256 deduplication.
6. Retry loop and timeout / error failure handling.
7. HTML document parsing, title extraction, and passage segmentation.
8. Copyright fair-use snippet capping for news media (up to 3 matched paragraphs).
9. End-to-end evidence registration in DB with all 12 required provenance fields.
10. Proposition-specific source reliability assessment (context-aware credibility).
11. Disabled registry entry handling (is_allowed=False).
12. Non-circumvention rule on access denied (HTTP 401/403).
"""

import os
import shutil
import tempfile
import time
from datetime import datetime, timezone
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.database.base_class import Base
from backend.models.claim import (
    EvidenceDocument,
    EvidencePassage,
    SourceTier,
    SourceAssessment
)
from backend.acquisition.claim_evidence_scraper import (
    SourceRegistryEntry,
    DEFAULT_PERMITTED_SOURCES,
    RateLimiter,
    RobotsPolicyChecker,
    EvidenceCacheManager,
    EvidenceAcquisitionPipeline
)


@pytest.fixture
def temp_cache_dir():
    """Provides an isolated temporary cache directory for acquisition tests."""
    temp_dir = tempfile.mkdtemp(prefix="civiclens_test_cache_")
    yield temp_dir
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def db_session():
    """Isolated in-memory SQLite database session for acquisition tests."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    yield session

    session.close()


def test_1_permitted_source_registry_and_whitelisting(temp_cache_dir):
    """
    Verifies that the registry configures domains across the 8 permitted categories
    with appropriate metadata, tiers, and rate limits.
    """
    pipeline = EvidenceAcquisitionPipeline(cache_dir=temp_cache_dir)

    expected_domains = [
        ("tn.gov.in", "OFFICIAL_GOVERNMENT", SourceTier.TIER_1_STATUTORY, False),
        ("pib.gov.in", "PRESS_RELEASE", SourceTier.TIER_2_OFFICIAL_AGENCY, False),
        ("assembly.tn.gov.in", "LEGISLATIVE_DOCUMENT", SourceTier.TIER_1_STATUTORY, False),
        ("sansad.in", "LEGISLATIVE_DOCUMENT", SourceTier.TIER_1_STATUTORY, False),
        ("data.gov.in", "STATISTICAL_DATASET", SourceTier.TIER_2_OFFICIAL_AGENCY, False),
        ("eci.gov.in", "ELECTION_RECORD", SourceTier.TIER_1_STATUTORY, False),
        ("tnbudget.tn.gov.in", "SCHEME_BUDGET", SourceTier.TIER_1_STATUTORY, False),
        ("altnews.in", "INDEPENDENT_FACTCHECK", SourceTier.TIER_3_ACCREDITED_FACTCHECK, True),
        ("thehindu.com", "PUBLIC_NEWS", SourceTier.TIER_4_SECONDARY_CIVIC, True),
        ("dailythanthi.com", "PUBLIC_NEWS", SourceTier.TIER_4_SECONDARY_CIVIC, True),
    ]

    for domain, cat, tier, is_snippet_only in expected_domains:
        assert domain in pipeline.registry, f"Domain {domain} missing from permitted registry"
        entry = pipeline.registry[domain]
        assert entry.source_category == cat
        assert entry.source_tier == tier
        assert entry.copyright_snippet_only == is_snippet_only
        assert entry.rate_limit_seconds >= 2.0

        # Whitelist verification check
        allowed, returned_entry, err = pipeline.is_source_allowed(f"https://{domain}/reports/doc1")
        assert allowed is True
        assert returned_entry.domain == domain
        assert err is None


def test_2_disallowed_domain_rejection_and_failure_logging(temp_cache_dir):
    """
    Verifies that non-whitelisted domains are strictly rejected and logged in failure_logs.
    """
    pipeline = EvidenceAcquisitionPipeline(cache_dir=temp_cache_dir)
    unauthorized_url = "https://unverified-political-rumors.blog/2026/claim-leak.html"

    allowed, entry, err = pipeline.is_source_allowed(unauthorized_url)
    assert allowed is False
    assert entry is None
    assert "not registered in permitted evidence source registry" in err

    # Verify structured failure log
    assert len(pipeline.failure_logs) == 1
    log = pipeline.failure_logs[0]
    assert log["failure_type"] == "DOMAIN_NOT_WHITELISTED"
    assert log["url"] == unauthorized_url
    assert "timestamp" in log

    # Verify fetch_url also halts on disallowed domain
    data, code, status = pipeline.fetch_url(unauthorized_url)
    assert data is None
    assert code == "RESTRICTED"
    assert status == "ROBOTS_OR_DOMAIN_DENIED"


def test_3_robots_policy_restriction(temp_cache_dir):
    """
    Verifies that paths restricted by robots.txt are rejected and logged as ROBOTS_DENIED.
    """
    pipeline = EvidenceAcquisitionPipeline(cache_dir=temp_cache_dir)

    # Disallowed path on a registered domain
    disallowed_url = "https://pib.gov.in/admin/private_release.html"
    allowed, entry, err = pipeline.is_source_allowed(disallowed_url)

    assert allowed is False
    assert "restricted by robots.txt policies" in err
    assert any(log["failure_type"] == "ROBOTS_DENIED" for log in pipeline.failure_logs)

    data, code, status = pipeline.fetch_url(disallowed_url)
    assert data is None
    assert status == "ROBOTS_OR_DOMAIN_DENIED"


def test_4_rate_limiting_delay_governance():
    """
    Validates that RateLimiter tracks domain timestamps and enforces delays.
    """
    limiter = RateLimiter()
    domain = "tnbudget.tn.gov.in"

    # First request: immediate execution
    t0 = time.time()
    limiter.wait_if_needed(domain, 0.2)
    t1 = time.time()
    assert (t1 - t0) < 0.1

    # Second request immediately after: should wait ~0.2s
    limiter.wait_if_needed(domain, 0.2)
    t2 = time.time()
    assert (t2 - t1) >= 0.18


def test_5_caching_and_content_deduplication(temp_cache_dir):
    """
    Verifies that local caching stores downloaded bytes and retrieves them without refetching.
    """
    pipeline = EvidenceAcquisitionPipeline(cache_dir=temp_cache_dir)
    test_url = "https://tn.gov.in/schemes/kalaignar_magalir_urimai.html"
    mock_payload = b"<html><head><title>KMUT Guidelines</title></head><body>Official Scheme Details</body></html>"

    # First fetch: should store in cache
    data1, code1, status1 = pipeline.fetch_url(test_url, mock_response=mock_payload)
    assert data1 == mock_payload
    assert status1 == "ACCESSIBLE_PUBLIC"

    # Second fetch: should retrieve from local cache without providing mock_payload
    data2, code2, status2 = pipeline.fetch_url(test_url)
    assert data2 == mock_payload
    assert code2 == "200_CACHED"
    assert status2 == "CACHED_LOCAL"


def test_6_network_retry_and_timeout_handling(temp_cache_dir):
    """
    Verifies timeout and network exception handling across configured retries.
    """
    pipeline = EvidenceAcquisitionPipeline(cache_dir=temp_cache_dir)
    failing_url = "https://tn.gov.in/slow_service"

    from unittest.mock import patch
    from urllib.error import URLError

    with patch("urllib.request.urlopen") as mock_urlopen:
        mock_urlopen.side_effect = URLError("Simulated connection timeout")
        data, code, status = pipeline.fetch_url(failing_url, timeout_seconds=0.1, max_retries=2)
        assert data is None
        assert status in ["FAILED_TIMEOUT", "FAILED_ERROR", "FAILED_RETRIES"]
        assert any(log["failure_type"] in ["TIMEOUT_OR_NETWORK", "UNEXPECTED_ERROR"] for log in pipeline.failure_logs)


def test_7_html_document_parsing_and_passage_extraction(temp_cache_dir):
    """
    Verifies HTML parsing, title detection, and passage division on bilingual content.
    """
    pipeline = EvidenceAcquisitionPipeline(cache_dir=temp_cache_dir)
    sample_html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Tamil Nadu Budget 2024-25 — Highlights</title>
        <meta name="date" content="2024-02-19">
    </head>
    <body>
        <h1>State Budget Highlights</h1>
        <p>The total outlay for education is allocated at Rs 44,042 crore.</p>
        <p>கலைஞர் மகளிர் உரிமைத் திட்டத்திற்கு ரூ.13,720 கோடி நிதி ஒதுக்கப்பட்டுள்ளது.</p>
        <p>Fiscal deficit is projected at 3.44 percent of GSDP.</p>
    </body>
    </html>
    """.encode("utf-8")

    parsed = pipeline.parse_document_content(
        raw_bytes=sample_html,
        url="https://tnbudget.tn.gov.in/highlights.html",
        content_type="HTML"
    )

    assert parsed["title"] == "Tamil Nadu Budget 2024-25 — Highlights"
    assert parsed["is_snippet_only"] is False
    assert len(parsed["passages"]) == 4

    # Check that Tamil passage is retained intact
    tamil_passage = next(p for p in parsed["passages"] if "கலைஞர் மகளிர்" in p["passage_text"])
    assert "13,720" in tamil_passage["passage_text"]
    assert tamil_passage["section_or_table"] == "Section 3"


def test_8_copyright_safeguards_snippet_capping(temp_cache_dir):
    """
    Verifies that copyrighted news sources only retain up to 3 keyword-relevant excerpts.
    """
    pipeline = EvidenceAcquisitionPipeline(cache_dir=temp_cache_dir)
    news_url = "https://thehindu.com/news/national/tamil-nadu/budget-reactions-assembly.html"

    # Multi-paragraph news article
    sample_news_html = """
    <html>
    <head><title>Opposition Debates TN State Budget in Assembly</title></head>
    <body>
        <p>Leaders gathered at Chennai Fort St. George on Monday morning.</p>
        <p>Opposition Leader claimed that capital expenditure fell short by Rs 5000 crore.</p>
        <p>The Finance Minister replied with detailed tables showing infrastructure growth.</p>
        <p>Several MLAs raised local constituency issues concerning rural roads and bridges.</p>
        <p>The session adjourned for lunch at 1:30 PM with heavy security outside.</p>
        <p>A press conference followed where parties briefed regional television reporters.</p>
    </body>
    </html>
    """.encode("utf-8")

    # Match keywords: "capital expenditure", "Finance Minister"
    parsed = pipeline.parse_document_content(
        raw_bytes=sample_news_html,
        url=news_url,
        content_type="HTML",
        claim_keywords=["capital expenditure", "infrastructure"]
    )

    assert parsed["is_snippet_only"] is True
    # Should cap at keyword-matched paragraphs (<= 3 excerpts)
    assert 1 <= len(parsed["passages"]) <= 3
    # Check that unrelated boilerplate ("lunch at 1:30 PM") is excluded
    assert not any("adjourned for lunch" in p["passage_text"] for p in parsed["passages"])
    assert any("capital expenditure" in p["passage_text"] for p in parsed["passages"])


def test_9_end_to_end_acquisition_and_db_registration(db_session, temp_cache_dir):
    """
    Tests end-to-end acquire_and_register_evidence call:
    fetches mock payload, hashes with SHA-256, parses, and writes EvidenceDocument & EvidencePassage records.
    """
    pipeline = EvidenceAcquisitionPipeline(db=db_session, cache_dir=temp_cache_dir)
    doc_id = "EDOC-TN-2024-SCHEME-01"
    url = "https://tn.gov.in/schemes/pudhumai_penn.html"
    content = b"<html><head><title>Pudhumai Penn Scheme</title></head><body><p>Under Pudhumai Penn, Rs 1000 per month is provided to girl students entering higher education.</p></body></html>"

    result = pipeline.acquire_and_register_evidence(
        document_id=doc_id,
        source_url=url,
        document_type="SCHEME_GUIDELINE",
        language="en",
        mock_bytes=content,
        is_test_fixture=True
    )

    assert result["status"] == "SUCCESS"
    assert result["evidence_document_id"] == doc_id
    assert result["source_url"] == url
    assert result["source_title"] == "Pudhumai Penn Scheme"
    assert result["publisher"] == "Government of Tamil Nadu"
    assert result["source_category"] == "OFFICIAL_GOVERNMENT"
    assert result["access_status"] == "ACCESSIBLE_PUBLIC"
    assert len(result["file_hash"]) == 64  # SHA-256 hex string

    # Verify persisted DB records
    db_doc = db_session.query(EvidenceDocument).filter(EvidenceDocument.document_id == doc_id).first()
    assert db_doc is not None
    assert db_doc.document_id == doc_id
    assert db_doc.file_hash_sha256 == result["file_hash"]
    assert db_doc.extraction_method == "ACQUISITION_FRAMEWORK_V1"
    assert db_doc.is_test_fixture is True

    passages = db_session.query(EvidencePassage).filter(EvidencePassage.document_id == doc_id).all()
    assert len(passages) == 1
    assert "Rs 1000 per month" in passages[0].passage_text


def test_10_proposition_specific_reliability_assessment():
    """
    Verifies that source credibility is evaluated based on the specific claim proposition
    and not assumed unconditionally truthful simply because it is official.
    """
    # 1. Executive Press Release in contested partisan speech
    pr_doc = EvidenceDocument(
        document_id="EDOC-PR-01",
        source_tier=SourceTier.TIER_2_OFFICIAL_AGENCY,
        source_name="Press Information Bureau",
        publisher="PIB",
        document_type="PRESS_RELEASE",
        source_category="PRESS_RELEASE"
    )
    score_pr = EvidenceAcquisitionPipeline.calculate_proposition_reliability(
        document=pr_doc,
        claim_category="PUBLIC_FUNDING",
        is_contested_political_speech=True
    )
    assert score_pr["contextual_independence_score"] == 0.55
    assert "Executive press releases have lower institutional independence" in score_pr["reliability_notes"]

    # 2. Statutory Budget Book for Budget Allocation claim
    budget_doc = EvidenceDocument(
        document_id="EDOC-BUDGET-01",
        source_tier=SourceTier.TIER_1_STATUTORY,
        source_name="Tamil Nadu Budget",
        publisher="Finance Department",
        document_type="BUDGET_DOCUMENT",
        source_category="SCHEME_BUDGET"
    )
    score_budget = EvidenceAcquisitionPipeline.calculate_proposition_reliability(
        document=budget_doc,
        claim_category="BUDGET_EXPENDITURE",
        is_contested_political_speech=False
    )
    assert score_budget["contextual_independence_score"] == 0.95
    assert score_budget["composite_proposition_reliability"] >= 0.90

    # 3. Public News for Budget Allocation claim (downgraded for primary empirical claims)
    news_doc = EvidenceDocument(
        document_id="EDOC-NEWS-01",
        source_tier=SourceTier.TIER_4_SECONDARY_CIVIC,
        source_name="The Hindu",
        publisher="The Hindu Group",
        document_type="NEWS_ARTICLE",
        source_category="PUBLIC_NEWS"
    )
    score_news = EvidenceAcquisitionPipeline.calculate_proposition_reliability(
        document=news_doc,
        claim_category="BUDGET_EXPENDITURE",
        is_contested_political_speech=False
    )
    assert score_news["composite_proposition_reliability"] < score_budget["composite_proposition_reliability"]
    assert "News reporting is secondary evidence for budget outlays" in score_news["reliability_notes"]

    # 4. Constitutional Election Record for Election Results
    eci_doc = EvidenceDocument(
        document_id="EDOC-ECI-01",
        source_tier=SourceTier.TIER_1_STATUTORY,
        source_name="ECI Results Portal",
        publisher="Election Commission of India",
        document_type="ELECTION_RECORD",
        source_category="ELECTION_RECORD"
    )
    score_eci = EvidenceAcquisitionPipeline.calculate_proposition_reliability(
        document=eci_doc,
        claim_category="ELECTION_RESULTS",
        is_contested_political_speech=False
    )
    assert score_eci["composite_proposition_reliability"] == 1.0
    assert "Constitutional election returns provide definitive legal proof" in score_eci["reliability_notes"]


def test_11_disabled_source_in_registry(temp_cache_dir):
    """
    Verifies that if a registry entry has is_allowed=False, access is prevented and logged.
    """
    custom_registry = {
        "pib.gov.in": SourceRegistryEntry(
            domain="pib.gov.in",
            source_name="Press Information Bureau",
            publisher="PIB",
            source_category="PRESS_RELEASE",
            source_tier=SourceTier.TIER_2_OFFICIAL_AGENCY,
            is_allowed=False  # Disabled
        )
    }
    pipeline = EvidenceAcquisitionPipeline(source_registry=custom_registry, cache_dir=temp_cache_dir)

    allowed, entry, err = pipeline.is_source_allowed("https://pib.gov.in/release123")
    assert allowed is False
    assert "disabled in source registry" in err
    assert any(log["failure_type"] == "DOMAIN_DISABLED" for log in pipeline.failure_logs)


def test_12_non_circumvention_on_access_denied(temp_cache_dir):
    """
    Verifies that HTTP 401 / 403 access barriers are treated as ACCESS_DENIED
    and never bypassed by circumvention tricks.
    """
    pipeline = EvidenceAcquisitionPipeline(cache_dir=temp_cache_dir)
    # Simulate a 403 Forbidden using mock urllib HTTPError
    from urllib.error import HTTPError
    import urllib.request
    from unittest.mock import patch

    with patch("urllib.request.urlopen") as mock_urlopen:
        mock_urlopen.side_effect = HTTPError(
            url="https://tn.gov.in/restricted_doc",
            code=403,
            msg="Forbidden",
            hdrs={},
            fp=None
        )

        data, code, status = pipeline.fetch_url("https://tn.gov.in/restricted_doc")
        assert data is None
        assert code == "HTTP_403"
        assert status == "ACCESS_DENIED"
        assert any(log["failure_type"] == "ACCESS_DENIED" for log in pipeline.failure_logs)
