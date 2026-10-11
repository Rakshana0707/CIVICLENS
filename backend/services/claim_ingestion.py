"""
Phase 7.2 — Political Claim Registry and Claim Ingestion Service.

Handles multi-channel intake of claim candidates across:
1. Public Speeches
2. Official Statements
3. Press Releases
4. Legislative Records
5. Manifestos
6. News Articles
7. Existing Fact-Check Articles
8. Manually Submitted Public-Interest Claims

Enforces core project standards:
- Exact original wording preservation
- Attribution distinction (Direct Quote, Paraphrase, Journalist Description, User Submitted, Automated Extraction)
- Strictly NO hallucinated or guessed speaker, date, party, or context when unverified
- Deduplication without merging materially distinct claims (different speaker, date, or context)
- Version tracking for corrections and supplemental context
- Multilingual support (Tamil, English, code-switched)
"""

import re
import hashlib
import unicodedata
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import desc

from backend.models.claim import (
    Claim,
    ClaimVersion,
    ClaimSource,
    ClaimCategory,
    ClaimStatus,
    ReviewStatus,
    AttributionType,
    CandidateSourceType
)
from backend.services.claim_verification import ClaimVerificationService
from backend.core.logger import setup_logger

logger = setup_logger("civiclens.phase7.ingestion")


class IngestionStatus:
    CREATED = "CREATED"
    DUPLICATE_EXACT = "DUPLICATE_EXACT"
    VERSION_ADDED = "VERSION_ADDED"
    DISTINCT_REITERATION = "DISTINCT_REITERATION"
    REJECTED_INVALID = "REJECTED_INVALID"


class ClaimIngestionService:
    """
    Intake and registry engine for political and civic claims in Tamil Nadu.
    """

    def __init__(self, db: Session):
        self.db = db
        self.verification_service = ClaimVerificationService(db=db)

    # -----------------------------------------------------------------------
    # 1. Content Fingerprinting & Text Normalization
    # -----------------------------------------------------------------------
    @staticmethod
    def generate_content_fingerprint(text: str, language: str = "ta") -> str:
        """
        Computes a deterministic cryptographic hash of normalized text for deduplication.
        Preserves Unicode Tamil characters while standardizing whitespace and case.
        """
        if not text:
            return ""
        # Unicode normalization (NFC standardizes Tamil combining characters)
        normalized = unicodedata.normalize("NFC", text.strip())
        # Lowercase for Latin characters
        normalized = normalized.lower()
        # Remove common punctuation but preserve alphanumeric + Tamil unicode range
        # Tamil unicode block: \u0B80-\u0BFF
        cleaned = re.sub(r"[^\w\s\u0B80-\u0BFF]", "", normalized)
        # Collapse multiple spaces
        cleaned = re.sub(r"\s+", " ", cleaned).strip()
        return hashlib.sha256(cleaned.encode("utf-8")).hexdigest()

    # -----------------------------------------------------------------------
    # 2. Candidate Deduplication & Material Distinction Check
    # -----------------------------------------------------------------------
    def check_duplicate(
        self,
        original_text: str,
        speaker_name: Optional[str] = None,
        claim_date: Optional[datetime] = None,
        language: str = "ta"
    ) -> Dict[str, Any]:
        """
        Evaluates an incoming candidate against the registry.
        Distinguishes between exact duplicates, materially distinct reiterations, and new claims.
        """
        fingerprint = self.generate_content_fingerprint(original_text, language=language)
        matching_claims = self.db.query(Claim).filter(
            Claim.content_fingerprint == fingerprint
        ).all()

        if not matching_claims:
            return {
                "is_duplicate": False,
                "is_reiteration": False,
                "fingerprint": fingerprint,
                "matching_claim_id": None
            }

        # Check for exact duplicate vs distinct reiteration
        for c in matching_claims:
            same_speaker = (c.speaker_name == speaker_name)
            # Date matching: compare YYYY-MM-DD if both exist
            same_date = False
            if c.claim_date is None and claim_date is None:
                same_date = True
            elif c.claim_date is not None and claim_date is not None:
                same_date = (c.claim_date.date() == claim_date.date())

            if same_speaker and same_date:
                return {
                    "is_duplicate": True,
                    "is_reiteration": False,
                    "fingerprint": fingerprint,
                    "matching_claim_id": c.claim_id
                }

        # Same wording, but materially different date or speaker (distinct reiteration)
        return {
            "is_duplicate": False,
            "is_reiteration": True,
            "fingerprint": fingerprint,
            "related_claim_ids": [c.claim_id for c in matching_claims]
        }

    # -----------------------------------------------------------------------
    # 3. Core Generic Ingestion Method
    # -----------------------------------------------------------------------
    def ingest_claim(
        self,
        claim_id: str,
        original_text: str,
        claim_category: ClaimCategory,
        candidate_source_type: CandidateSourceType,
        attribution_type: AttributionType,
        language: str = "ta",
        speaker_name: Optional[str] = None,
        speaker_role: Optional[str] = None,
        party: Optional[str] = None,
        claim_date: Optional[datetime] = None,
        publication_date: Optional[datetime] = None,
        claim_source_url: Optional[str] = None,
        source_document_id: Optional[str] = None,
        geographic_scope: Optional[str] = "Tamil Nadu",
        extraction_method: str = "MANUAL",
        context_text: Optional[str] = None,
        temporal_scope: Optional[str] = None,
        is_correction_for_claim_id: Optional[str] = None,
        correction_rationale: Optional[str] = None,
        transliteration: Optional[str] = None,
        is_test_fixture: bool = False,
        metadata_json: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Generic ingestion processor.
        Stores exact original wording, enforces non-inference of missing metadata,
        detects exact duplicates, and records versions when corrections are provided.
        """
        if not original_text or not original_text.strip():
            return {
                "status": IngestionStatus.REJECTED_INVALID,
                "error": "original_text cannot be empty."
            }

        cleaned_original = original_text.strip()
        fingerprint = self.generate_content_fingerprint(cleaned_original, language=language)

        # Case A: Explicit correction or additional context for an existing claim
        if is_correction_for_claim_id:
            target_claim = self.db.query(Claim).filter(Claim.claim_id == is_correction_for_claim_id).first()
            if not target_claim:
                return {
                    "status": IngestionStatus.REJECTED_INVALID,
                    "error": f"Target claim '{is_correction_for_claim_id}' not found for version update."
                }
            version = self.verification_service.add_claim_version(
                claim_id=is_correction_for_claim_id,
                edited_text=cleaned_original,
                change_rationale=correction_rationale or "Ingested correction/context update.",
                transliterated_text=transliteration,
                additional_context=context_text,
                edited_by="ingestion_pipeline"
            )
            return {
                "status": IngestionStatus.VERSION_ADDED,
                "claim_id": target_claim.claim_id,
                "version_number": version.version_number,
                "message": f"Added version {version.version_number} to existing claim {target_claim.claim_id}."
            }

        # Case B: Deduplication check
        dup_check = self.check_duplicate(
            original_text=cleaned_original,
            speaker_name=speaker_name,
            claim_date=claim_date,
            language=language
        )

        if dup_check["is_duplicate"]:
            logger.info(f"Duplicate claim detected for fingerprint {fingerprint}: existing ID {dup_check['matching_claim_id']}")
            return {
                "status": IngestionStatus.DUPLICATE_EXACT,
                "claim_id": dup_check["matching_claim_id"],
                "message": "Exact duplicate claim already registered. Preserving existing record without duplicate creation."
            }

        # Case C: Materially distinct reiteration or brand new claim
        meta = metadata_json or {}
        if dup_check.get("is_reiteration"):
            meta["related_reiteration_claim_ids"] = dup_check.get("related_claim_ids", [])
            logger.info(f"Ingesting distinct reiteration for existing claim(s) {meta['related_reiteration_claim_ids']}")

        # Register the new claim strictly without guessing unverified fields
        claim = self.verification_service.register_claim(
            claim_id=claim_id,
            original_text=cleaned_original,
            claim_category=claim_category,
            speaker_name=speaker_name,        # None if unverified
            speaker_role=speaker_role,        # None if unverified
            speaker_party=party,              # None if unverified
            party=party,
            claim_date=claim_date,            # None if unverified (never guessed)
            publication_date=publication_date,
            claim_source_url=claim_source_url,
            source_document_id=source_document_id,
            temporal_scope=temporal_scope,
            geographic_scope=geographic_scope,
            context_text=context_text,
            language=language,
            extraction_method=extraction_method,
            attribution_type=attribution_type,
            candidate_source_type=candidate_source_type,
            content_fingerprint=fingerprint,
            is_test_fixture=is_test_fixture,
            metadata_json=meta
        )

        ingestion_status = (
            IngestionStatus.DISTINCT_REITERATION if dup_check.get("is_reiteration")
            else IngestionStatus.CREATED
        )

        return {
            "status": ingestion_status,
            "claim_id": claim.claim_id,
            "original_text": claim.original_text,
            "language": claim.language,
            "attribution_type": claim.attribution_type.value,
            "candidate_source_type": claim.candidate_source_type.value,
            "speaker_name": claim.speaker_name,
            "party": claim.party,
            "claim_date": claim.claim_date.isoformat() if claim.claim_date else None,
            "review_status": claim.review_status.value,
            "created_at": claim.created_at.isoformat()
        }

    # -----------------------------------------------------------------------
    # 4. Specialized Channel Ingestion Methods
    # -----------------------------------------------------------------------
    def ingest_public_speech(
        self,
        claim_id: str,
        transcript_text: str,
        claim_category: ClaimCategory,
        speaker_name: Optional[str] = None,
        speaker_role: Optional[str] = None,
        party: Optional[str] = None,
        speech_date: Optional[datetime] = None,
        venue: Optional[str] = None,
        video_or_audio_url: Optional[str] = None,
        is_direct_quote: bool = True,
        language: str = "ta",
        is_test_fixture: bool = False
    ) -> Dict[str, Any]:
        """
        Ingests a claim candidate delivered during a public speech, rally, or press meet.
        """
        attr_type = AttributionType.DIRECT_QUOTE if is_direct_quote else AttributionType.PARAPHRASE
        context = f"Public speech at {venue} on {speech_date.strftime('%Y-%m-%d')}" if (venue and speech_date) else None

        return self.ingest_claim(
            claim_id=claim_id,
            original_text=transcript_text,
            claim_category=claim_category,
            candidate_source_type=CandidateSourceType.PUBLIC_SPEECH,
            attribution_type=attr_type,
            language=language,
            speaker_name=speaker_name,
            speaker_role=speaker_role,
            party=party,
            claim_date=speech_date,
            publication_date=speech_date,
            claim_source_url=video_or_audio_url,
            context_text=context,
            extraction_method="SPEECH_TRANSCRIPT_INGESTION",
            is_test_fixture=is_test_fixture
        )

    def ingest_official_statement(
        self,
        claim_id: str,
        statement_text: str,
        claim_category: ClaimCategory,
        issuing_agency: Optional[str] = None,
        official_name: Optional[str] = None,
        official_role: Optional[str] = None,
        statement_date: Optional[datetime] = None,
        source_url: Optional[str] = None,
        source_document_id: Optional[str] = None,
        language: str = "en",
        is_test_fixture: bool = False
    ) -> Dict[str, Any]:
        """
        Ingests a claim candidate from an official government communique or departmental announcement.
        """
        return self.ingest_claim(
            claim_id=claim_id,
            original_text=statement_text,
            claim_category=claim_category,
            candidate_source_type=CandidateSourceType.OFFICIAL_STATEMENT,
            attribution_type=AttributionType.DIRECT_QUOTE,
            language=language,
            speaker_name=official_name,
            speaker_role=official_role,
            party=None,  # Government executive communique has no partisan attribution
            claim_date=statement_date,
            publication_date=statement_date,
            claim_source_url=source_url,
            source_document_id=source_document_id,
            context_text=f"Official statement issued by {issuing_agency}" if issuing_agency else None,
            extraction_method="OFFICIAL_PORTAL_CRAWL",
            is_test_fixture=is_test_fixture
        )

    def ingest_press_release(
        self,
        claim_id: str,
        release_text: str,
        claim_category: ClaimCategory,
        issuing_party_or_org: Optional[str] = None,
        spokesperson_name: Optional[str] = None,
        release_date: Optional[datetime] = None,
        source_url: Optional[str] = None,
        source_document_id: Optional[str] = None,
        language: str = "ta",
        is_test_fixture: bool = False
    ) -> Dict[str, Any]:
        """
        Ingests a political party press release or DIPR bulletin.
        """
        return self.ingest_claim(
            claim_id=claim_id,
            original_text=release_text,
            claim_category=claim_category,
            candidate_source_type=CandidateSourceType.PRESS_RELEASE,
            attribution_type=AttributionType.DIRECT_QUOTE,
            language=language,
            speaker_name=spokesperson_name,
            party=issuing_party_or_org,
            claim_date=release_date,
            publication_date=release_date,
            claim_source_url=source_url,
            source_document_id=source_document_id,
            extraction_method="PRESS_RELEASE_INTAKE",
            is_test_fixture=is_test_fixture
        )

    def ingest_legislative_record(
        self,
        claim_id: str,
        proceeding_text: str,
        claim_category: ClaimCategory,
        legislative_body: str,  # TN_ASSEMBLY, LOK_SABHA, RAJYA_SABHA
        member_name: Optional[str] = None,
        member_role: Optional[str] = None,
        party: Optional[str] = None,
        session_date: Optional[datetime] = None,
        question_or_debate_id: Optional[str] = None,
        source_url: Optional[str] = None,
        language: str = "ta",
        is_test_fixture: bool = False
    ) -> Dict[str, Any]:
        """
        Ingests a statement made on the floor of the Tamil Nadu Legislative Assembly or Parliament.
        """
        return self.ingest_claim(
            claim_id=claim_id,
            original_text=proceeding_text,
            claim_category=claim_category,
            candidate_source_type=CandidateSourceType.LEGISLATIVE_RECORD,
            attribution_type=AttributionType.DIRECT_QUOTE,
            language=language,
            speaker_name=member_name,
            speaker_role=member_role,
            party=party,
            claim_date=session_date,
            publication_date=session_date,
            claim_source_url=source_url,
            source_document_id=question_or_debate_id,
            context_text=f"Floor proceeding in {legislative_body} ({question_or_debate_id or ''})",
            extraction_method="HANSARD_PARSER",
            is_test_fixture=is_test_fixture
        )

    def ingest_manifesto(
        self,
        claim_id: str,
        manifesto_clause_text: str,
        claim_category: ClaimCategory,
        party: str,
        election_year: int,
        manifesto_document_id: Optional[str] = None,
        page_number: Optional[int] = None,
        language: str = "ta",
        is_test_fixture: bool = False
    ) -> Dict[str, Any]:
        """
        Ingests a specific political manifesto pledge or policy assertion.
        """
        return self.ingest_claim(
            claim_id=claim_id,
            original_text=manifesto_clause_text,
            claim_category=claim_category,
            candidate_source_type=CandidateSourceType.MANIFESTO,
            attribution_type=AttributionType.DIRECT_QUOTE,
            language=language,
            speaker_name=f"{party} Election Committee",
            speaker_role="Political Party Manifesto",
            party=party,
            claim_date=datetime(election_year, 1, 1, tzinfo=timezone.utc),
            temporal_scope=str(election_year),
            source_document_id=manifesto_document_id,
            context_text=f"Official {election_year} Election Manifesto (Page {page_number or 'N/A'})",
            extraction_method="MANIFESTO_PARSER",
            is_test_fixture=is_test_fixture
        )

    def ingest_news_article(
        self,
        claim_id: str,
        extracted_text: str,
        claim_category: ClaimCategory,
        article_source_name: str,
        attribution_type: AttributionType,
        speaker_name: Optional[str] = None,
        speaker_role: Optional[str] = None,
        party: Optional[str] = None,
        publication_date: Optional[datetime] = None,
        article_url: Optional[str] = None,
        source_document_id: Optional[str] = None,
        language: str = "ta",
        is_test_fixture: bool = False
    ) -> Dict[str, Any]:
        """
        Ingests a claim extracted from a news article.
        Explicitly distinguishes between direct quotes, paraphrased speech, and journalist descriptions.
        """
        return self.ingest_claim(
            claim_id=claim_id,
            original_text=extracted_text,
            claim_category=claim_category,
            candidate_source_type=CandidateSourceType.NEWS_ARTICLE,
            attribution_type=attribution_type,
            language=language,
            speaker_name=speaker_name,
            speaker_role=speaker_role,
            party=party,
            claim_date=None,  # Do not infer exact speech date from publication date unless verified
            publication_date=publication_date,
            claim_source_url=article_url,
            source_document_id=source_document_id,
            context_text=f"Reported in {article_source_name}",
            extraction_method="NEWS_TEXT_EXTRACTOR",
            is_test_fixture=is_test_fixture
        )

    def ingest_fact_check(
        self,
        claim_id: str,
        reviewed_claim_text: str,
        claim_category: ClaimCategory,
        factcheck_publisher: str,
        reviewed_speaker: Optional[str] = None,
        reviewed_party: Optional[str] = None,
        claim_date: Optional[datetime] = None,
        publication_date: Optional[datetime] = None,
        factcheck_url: Optional[str] = None,
        source_document_id: Optional[str] = None,
        language: str = "en",
        is_test_fixture: bool = False
    ) -> Dict[str, Any]:
        """
        Ingests a viral or public claim recorded in an independent fact-check article.
        """
        return self.ingest_claim(
            claim_id=claim_id,
            original_text=reviewed_claim_text,
            claim_category=claim_category,
            candidate_source_type=CandidateSourceType.FACT_CHECK_ARTICLE,
            attribution_type=AttributionType.AUTOMATED_EXTRACTION,
            language=language,
            speaker_name=reviewed_speaker,
            party=reviewed_party,
            claim_date=claim_date,
            publication_date=publication_date,
            claim_source_url=factcheck_url,
            source_document_id=source_document_id,
            context_text=f"Claim reviewed by independent fact-checker {factcheck_publisher}",
            extraction_method="CLAIMREVIEW_JSONLD_INGESTION",
            is_test_fixture=is_test_fixture
        )

    def ingest_user_submission(
        self,
        claim_id: str,
        submitted_text: str,
        claim_category: ClaimCategory,
        alleged_speaker: Optional[str] = None,
        alleged_party: Optional[str] = None,
        claim_source_url: Optional[str] = None,
        user_notes: Optional[str] = None,
        language: str = "ta",
        is_test_fixture: bool = False
    ) -> Dict[str, Any]:
        """
        Ingests a user-submitted claim candidate.
        Marked as USER_SUBMITTED with unverified metadata preserved as unverified.
        """
        return self.ingest_claim(
            claim_id=claim_id,
            original_text=submitted_text,
            claim_category=claim_category,
            candidate_source_type=CandidateSourceType.MANUAL_SUBMISSION,
            attribution_type=AttributionType.USER_SUBMITTED,
            language=language,
            speaker_name=alleged_speaker,
            party=alleged_party,
            claim_date=None,  # User submitted dates are not verified as factual until reviewed
            claim_source_url=claim_source_url,
            context_text=f"User submission notes: {user_notes}" if user_notes else "Public user submission",
            extraction_method="CITIZEN_SUBMISSION_PORTAL",
            is_test_fixture=is_test_fixture
        )
