"""
Phase 7 — Political Claim Verification & Evidence Intelligence Database Models.

Defines canonical SQLAlchemy ORM entities for:
1. Claim
2. ClaimVersion
3. ClaimSubject
4. ClaimSource
5. EvidenceDocument
6. EvidencePassage
7. ClaimEvidenceRelationship
8. VerificationRun
9. VerificationResult
10. VerificationHistory
11. SourceAssessment
12. ReviewRecord

Adheres strictly to core verification principles:
- Original claim preservation
- Atomic propositions separation
- Distinguishing empirical evidence from interpretation
- Recording supporting and contradicting signals
- Explicit uncertainty exposure and source-level provenance
- Human review tracking
- Strictly NO automated political truthfulness rankings or leaderboards
"""

import enum
from datetime import datetime, timezone
from typing import List, Optional
from sqlalchemy import (
    Column, Integer, String, Text, DateTime, ForeignKey, Float, Boolean, Enum, JSON, UniqueConstraint
)
from sqlalchemy.orm import relationship
from backend.database.base_class import Base


class ClaimCategory(str, enum.Enum):
    """
    Standardized classification for public political and civic claims in Tamil Nadu.
    """
    GOVERNMENT_SCHEMES = "GOVERNMENT_SCHEMES"
    BUDGET_EXPENDITURE = "BUDGET_EXPENDITURE"
    ELECTION_RESULTS = "ELECTION_RESULTS"
    POLITICAL_PROMISES = "POLITICAL_PROMISES"
    REPRESENTATIVE_ACTIVITY = "REPRESENTATIVE_ACTIVITY"
    PUBLIC_FUNDING = "PUBLIC_FUNDING"
    DEMOGRAPHIC_STATISTICS = "DEMOGRAPHIC_STATISTICS"
    PUBLIC_INFRASTRUCTURE = "PUBLIC_INFRASTRUCTURE"
    HEALTHCARE_EDUCATION = "HEALTHCARE_EDUCATION"
    EMPLOYMENT_ECONOMIC = "EMPLOYMENT_ECONOMIC"
    OTHER_PUBLIC_INTEREST = "OTHER_PUBLIC_INTEREST"


class ClaimStatus(str, enum.Enum):
    PENDING = "PENDING"
    DECOMPOSED = "DECOMPOSED"
    EVIDENCE_LINKED = "EVIDENCE_LINKED"
    VERIFIED = "VERIFIED"
    UNDER_REVIEW = "UNDER_REVIEW"
    ARCHIVED = "ARCHIVED"


class SourceTier(str, enum.Enum):
    """
    Objective credibility hierarchy for evidence sources.
    """
    TIER_1_STATUTORY = "TIER_1_STATUTORY"                # Gazettes, ECI returns, Hansard, CAG audits
    TIER_2_OFFICIAL_AGENCY = "TIER_2_OFFICIAL_AGENCY"    # PIB, TN DIPR releases, RBI, MoSPI, NFHS
    TIER_3_ACCREDITED_FACTCHECK = "TIER_3_ACCREDITED_FACTCHECK"  # IFCN factcheckers, primary news of record
    TIER_4_SECONDARY_CIVIC = "TIER_4_SECONDARY_CIVIC"    # Academic papers, civil society dashboards
    TIER_5_UNVERIFIED = "TIER_5_UNVERIFIED"              # Social media, uncorroborated blogs


class EvidenceRelationshipType(str, enum.Enum):
    """
    Explicit bidirectional relationship between evidence passage and claim proposition.
    """
    SUPPORTS = "SUPPORTS"
    CONTRADICTS = "CONTRADICTS"
    PARTIALLY_SUPPORTS = "PARTIALLY_SUPPORTS"
    CONTEXTUALIZES = "CONTEXTUALIZES"
    NEUTRAL = "NEUTRAL"


class VerificationVerdict(str, enum.Enum):
    """
    Exhaustive standardized verdict taxonomy.
    """
    SUPPORTED = "SUPPORTED"
    CONTRADICTED = "CONTRADICTED"
    PARTIALLY_SUPPORTED = "PARTIALLY_SUPPORTED"
    MISLEADING_CONTEXT = "MISLEADING_CONTEXT"
    UNVERIFIABLE_INSUFFICIENT_EVIDENCE = "UNVERIFIABLE_INSUFFICIENT_EVIDENCE"
    DISPUTED_METHODOLOGY = "DISPUTED_METHODOLOGY"


class ReviewStatus(str, enum.Enum):
    PENDING_REVIEW = "PENDING_REVIEW"
    IN_REVIEW = "IN_REVIEW"
    ACCEPTED = "ACCEPTED"
    OVERRIDDEN = "OVERRIDDEN"
    REJECTED = "REJECTED"


class SubjectType(str, enum.Enum):
    POLITICIAN = "POLITICIAN"
    POLITICAL_PARTY = "POLITICAL_PARTY"
    GOVERNMENT_DEPARTMENT = "GOVERNMENT_DEPARTMENT"
    SCHEME = "SCHEME"
    CONSTITUENCY = "CONSTITUENCY"
    STATISTICAL_INDICATOR = "STATISTICAL_INDICATOR"
    INSTITUTION = "INSTITUTION"


class AttributionType(str, enum.Enum):
    """
    Distinguishes the quotation or attribution modality of the statement.
    """
    DIRECT_QUOTE = "DIRECT_QUOTE"
    PARAPHRASE = "PARAPHRASE"
    JOURNALIST_DESCRIPTION = "JOURNALIST_DESCRIPTION"
    USER_SUBMITTED = "USER_SUBMITTED"
    AUTOMATED_EXTRACTION = "AUTOMATED_EXTRACTION"


class CandidateSourceType(str, enum.Enum):
    """
    Originating intake channel for the claim candidate.
    """
    PUBLIC_SPEECH = "PUBLIC_SPEECH"
    OFFICIAL_STATEMENT = "OFFICIAL_STATEMENT"
    PRESS_RELEASE = "PRESS_RELEASE"
    LEGISLATIVE_RECORD = "LEGISLATIVE_RECORD"
    MANIFESTO = "MANIFESTO"
    NEWS_ARTICLE = "NEWS_ARTICLE"
    FACT_CHECK_ARTICLE = "FACT_CHECK_ARTICLE"
    MANUAL_SUBMISSION = "MANUAL_SUBMISSION"


class VerifiabilityStatus(str, enum.Enum):
    """
    Distinguishes verifiable factual claims from subjective or non-factual statements.
    """
    VERIFIABLE_FACTUAL = "VERIFIABLE_FACTUAL"
    OPINION = "OPINION"
    PREDICTION = "PREDICTION"
    VALUE_JUDGMENT = "VALUE_JUDGMENT"
    RHETORICAL_QUESTION = "RHETORICAL_QUESTION"
    SLOGAN = "SLOGAN"
    AMBIGUOUS_UNVERIFIABLE = "AMBIGUOUS_UNVERIFIABLE"


class AtomicClaimType(str, enum.Enum):
    """
    Taxonomy of verifiable and non-verifiable proposition types.
    """
    NUMERICAL_STATISTIC = "NUMERICAL_STATISTIC"
    SCHEME_BENEFIT = "SCHEME_BENEFIT"
    BUDGET_ALLOCATION = "BUDGET_ALLOCATION"
    POLICY_DECISION = "POLICY_DECISION"
    ELECTION_OUTCOME = "ELECTION_OUTCOME"
    HISTORICAL_RECORD = "HISTORICAL_RECORD"
    INFRASTRUCTURE_DELIVERY = "INFRASTRUCTURE_DELIVERY"
    EMPLOYMENT_METRIC = "EMPLOYMENT_METRIC"
    NON_FACTUAL = "NON_FACTUAL"


# ---------------------------------------------------------------------------
# 1. ClaimSource Entity
# ---------------------------------------------------------------------------
class ClaimSource(Base):
    """
    Captures provenance details of where, when, and how a claim was voiced or published.
    """
    __tablename__ = "claim_sources"

    source_id = Column(String, primary_key=True, index=True)
    source_type = Column(String, nullable=False, index=True)  # PRESS_MEET, CAMPAIGN_RALLY, SOCIAL_POST, MANIFESTO, DEBATE
    organization_or_party = Column(String, nullable=True, index=True)
    speaker_name = Column(String, nullable=True, index=True)
    speaker_party = Column(String, nullable=True, index=True)
    venue = Column(String, nullable=True)
    source_url = Column(String, nullable=True)
    archive_url = Column(String, nullable=True)
    publication_date = Column(DateTime, nullable=True)
    collection_date = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    collection_method = Column(String, default="manual_intake")
    checksum = Column(String, nullable=True)
    notes = Column(Text, nullable=True)

    # Relationships
    claims = relationship("Claim", back_populates="source", cascade="all, delete-orphan")


# ---------------------------------------------------------------------------
# 2. Claim Entity
# ---------------------------------------------------------------------------
class Claim(Base):
    """
    Canonical Claim entity. Preserves original unaltered wording and links to
    decomposed subjects, evidence relationships, and verification results.
    """
    __tablename__ = "political_claims"

    claim_id = Column(String, primary_key=True, index=True)
    source_id = Column(String, ForeignKey("claim_sources.source_id", ondelete="SET NULL"), nullable=True, index=True)

    # Utterance Text & Context Preservation
    original_text = Column(Text, nullable=False)  # Immutable verbatim claim text
    normalized_text = Column(Text, nullable=False)  # Stemmed, whitespace cleaned
    context_text = Column(Text, nullable=True)      # Surrounding speech or dialogue
    language = Column(String, default="ta")         # ta, en, bilingual

    # Categorization & Scope
    claim_category = Column(Enum(ClaimCategory), nullable=False, index=True)
    speaker_name = Column(String, nullable=True, index=True)
    speaker_role = Column(String, nullable=True)  # where supported (e.g. Chief Minister, MLA, MP)
    speaker_party = Column(String, nullable=True, index=True)
    party = Column(String, nullable=True, index=True)  # canonical alias for party where supported
    claim_date = Column(DateTime, nullable=True, index=True)
    publication_date = Column(DateTime, nullable=True, index=True)  # where applicable
    claim_source_url = Column(String, nullable=True)
    source_document_id = Column(String, nullable=True, index=True)
    temporal_scope = Column(String, nullable=True)  # e.g. "2021-2022", "Last 3 years"
    geographic_scope = Column(String, nullable=True, default="Tamil Nadu")  # e.g. "Tamil Nadu", "Chennai"
    extraction_method = Column(String, default="MANUAL")

    # Ingestion Attribution & Source Channel
    attribution_type = Column(Enum(AttributionType), default=AttributionType.DIRECT_QUOTE, index=True)
    candidate_source_type = Column(Enum(CandidateSourceType), default=CandidateSourceType.PUBLIC_SPEECH, index=True)
    content_fingerprint = Column(String, nullable=True, index=True)

    # Status & Audit
    status = Column(Enum(ClaimStatus), default=ClaimStatus.PENDING, index=True)
    review_status = Column(Enum(ReviewStatus), default=ReviewStatus.PENDING_REVIEW, index=True)
    is_test_fixture = Column(Boolean, default=False)
    metadata_json = Column(JSON, nullable=True)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    source = relationship("ClaimSource", back_populates="claims")
    versions = relationship("ClaimVersion", back_populates="claim", cascade="all, delete-orphan")
    subjects = relationship("ClaimSubject", back_populates="claim", cascade="all, delete-orphan")
    atomic_claims = relationship("AtomicClaim", back_populates="claim", cascade="all, delete-orphan")
    evidence_relationships = relationship("ClaimEvidenceRelationship", back_populates="claim", cascade="all, delete-orphan")
    verification_runs = relationship("VerificationRun", back_populates="claim", cascade="all, delete-orphan")
    verification_results = relationship("VerificationResult", back_populates="claim", cascade="all, delete-orphan")
    verification_history = relationship("VerificationHistory", back_populates="claim", cascade="all, delete-orphan")
    reviews = relationship("ReviewRecord", back_populates="claim", cascade="all, delete-orphan")


# ---------------------------------------------------------------------------
# 3. ClaimVersion Entity
# ---------------------------------------------------------------------------
class ClaimVersion(Base):
    """
    Captures revisions, transcript corrections, or bilingual translations 
    without overwriting the canonical original utterance text.
    """
    __tablename__ = "claim_versions"

    version_id = Column(String, primary_key=True, index=True)
    claim_id = Column(String, ForeignKey("political_claims.claim_id", ondelete="CASCADE"), nullable=False, index=True)
    version_number = Column(Integer, default=1)
    edited_text = Column(Text, nullable=False)
    transliterated_text = Column(Text, nullable=True)
    additional_context = Column(Text, nullable=True)
    change_rationale = Column(Text, nullable=False)
    edited_by = Column(String, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    claim = relationship("Claim", back_populates="versions")


# ---------------------------------------------------------------------------
# 4. ClaimSubject Entity
# ---------------------------------------------------------------------------
class ClaimSubject(Base):
    """
    Atomic subject or entity decomposed from a claim (e.g. MLA, scheme, department).
    """
    __tablename__ = "claim_subjects"

    subject_id = Column(String, primary_key=True, index=True)
    claim_id = Column(String, ForeignKey("political_claims.claim_id", ondelete="CASCADE"), nullable=False, index=True)
    subject_type = Column(Enum(SubjectType), nullable=False, index=True)
    entity_id = Column(String, nullable=True, index=True)  # Links to representative_id, scheme_id, party_id
    canonical_name = Column(String, nullable=False, index=True)
    confidence = Column(Float, default=1.0)

    # Relationships
    claim = relationship("Claim", back_populates="subjects")


# ---------------------------------------------------------------------------
# 4b. AtomicClaim Entity
# ---------------------------------------------------------------------------
class AtomicClaim(Base):
    """
    Decomposed atomic verifiable proposition extracted from a compound political claim.
    Preserves exact sub-proposition text, linguistic context, and structured SPO fields.
    """
    __tablename__ = "atomic_claims"

    atomic_claim_id = Column(String, primary_key=True, index=True)
    claim_id = Column(String, ForeignKey("political_claims.claim_id", ondelete="CASCADE"), nullable=False, index=True)
    atomic_claim_text = Column(Text, nullable=False)
    language = Column(String, default="en", index=True)

    # Structured Semantic Frame (SPO)
    subject = Column(String, nullable=True, index=True)
    predicate = Column(String, nullable=True)
    action = Column(String, nullable=True)
    object = Column(String, nullable=True)

    # Temporal & Spatial Scope
    time_period = Column(String, nullable=True)
    geographic_scope = Column(String, nullable=True, default="Tamil Nadu")

    # Quantitative Attributes
    numeric_value = Column(Float, nullable=True)
    unit = Column(String, nullable=True)
    denominator = Column(String, nullable=True)
    comparison_operator = Column(String, nullable=True)
    baseline_value = Column(Float, nullable=True)

    # Taxonomy & Verifiability
    claim_type = Column(String, nullable=False, default="NUMERICAL_STATISTIC", index=True)
    verifiability_status = Column(String, nullable=False, default="VERIFIABLE_FACTUAL", index=True)
    is_verifiable = Column(Boolean, default=True, index=True)
    is_negated = Column(Boolean, default=False)

    # Processing Provenance
    decomposition_method = Column(String, default="MULTILINGUAL_NLP_V1")
    confidence = Column(Float, default=1.0)
    translation_text = Column(Text, nullable=True)
    metadata_json = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    claim = relationship("Claim", back_populates="atomic_claims")


# ---------------------------------------------------------------------------
# 5. EvidenceDocument Entity
# ---------------------------------------------------------------------------
class EvidenceDocument(Base):
    """
    Represents an ingested statutory record, budget book, Hansard transcript,
    government order, or independent fact-check document.
    """
    __tablename__ = "evidence_documents"

    document_id = Column(String, primary_key=True, index=True)
    source_tier = Column(Enum(SourceTier), default=SourceTier.TIER_1_STATUTORY, index=True)
    source_name = Column(String, nullable=False, index=True)  # e.g., "Finance Department TN"
    publisher = Column(String, nullable=True, index=True)      # Publisher / issuing authority
    document_type = Column(String, nullable=False, index=True)  # e.g., "GOVERNMENT_ORDER", "BUDGET_DDG", "PRESS_RELEASE"
    source_category = Column(String, nullable=True, index=True) # e.g. "OFFICIAL_GOVERNMENT", "LEGISLATIVE_RECORD", "FACT_CHECK"
    title = Column(String, nullable=False)
    publication_date = Column(DateTime, nullable=True, index=True)
    retrieval_date = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    source_url = Column(String, nullable=True)
    file_path = Column(String, nullable=True)
    file_hash_sha256 = Column(String, nullable=False, unique=True, index=True)
    extraction_method = Column(String, default="DIRECT_PARSE")
    access_status = Column(String, default="ACCESSIBLE_PUBLIC")  # ACCESSIBLE_PUBLIC, RESTRICTED_SNIPPET_ONLY, CACHED_LOCAL, ROBOTS_DENIED
    language = Column(String, default="en")
    is_official = Column(Boolean, default=True)
    is_test_fixture = Column(Boolean, default=False)
    metadata_json = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    @property
    def evidence_document_id(self) -> str:
        return self.document_id

    @property
    def file_hash(self) -> str:
        return self.file_hash_sha256

    @property
    def source_title(self) -> str:
        return self.title

    # Relationships
    passages = relationship("EvidencePassage", back_populates="document", cascade="all, delete-orphan")
    source_assessments = relationship("SourceAssessment", back_populates="document", cascade="all, delete-orphan")


# ---------------------------------------------------------------------------
# 6. EvidencePassage Entity
# ---------------------------------------------------------------------------
class EvidencePassage(Base):
    """
    Granular text excerpt, tabular cell, or speech passage providing precise proof.
    """
    __tablename__ = "evidence_passages"

    passage_id = Column(String, primary_key=True, index=True)
    document_id = Column(String, ForeignKey("evidence_documents.document_id", ondelete="CASCADE"), nullable=False, index=True)
    passage_text = Column(Text, nullable=False)
    page_number = Column(Integer, nullable=True)
    section_or_table = Column(String, nullable=True)
    context_text = Column(Text, nullable=True)
    extracted_entities = Column(JSON, nullable=True)
    numerical_values = Column(JSON, nullable=True)  # e.g., {"amount_crores": 5000.0, "year": 2022}
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    document = relationship("EvidenceDocument", back_populates="passages")
    claim_relationships = relationship("ClaimEvidenceRelationship", back_populates="passage", cascade="all, delete-orphan")


# ---------------------------------------------------------------------------
# 7. ClaimEvidenceRelationship Entity
# ---------------------------------------------------------------------------
class ClaimEvidenceRelationship(Base):
    """
    Explicit junction linking a claim proposition to an evidence passage with
    support vs. contradiction signals and multi-signal scores.
    """
    __tablename__ = "claim_evidence_relationships"

    relationship_id = Column(String, primary_key=True, index=True)
    claim_id = Column(String, ForeignKey("political_claims.claim_id", ondelete="CASCADE"), nullable=False, index=True)
    passage_id = Column(String, ForeignKey("evidence_passages.passage_id", ondelete="CASCADE"), nullable=False, index=True)

    relationship_type = Column(Enum(EvidenceRelationshipType), nullable=False, index=True)
    relevance_score = Column(Float, default=0.0)        # 0.0 to 1.0
    confidence_score = Column(Float, default=0.0)       # 0.0 to 1.0
    contradiction_score = Column(Float, default=0.0)    # 0.0 to 1.0
    matching_method = Column(String, nullable=True)     # e.g. "hybrid_multi_signal"
    reconciliation_notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    claim = relationship("Claim", back_populates="evidence_relationships")
    passage = relationship("EvidencePassage", back_populates="claim_relationships")


# ---------------------------------------------------------------------------
# 8. VerificationRun Entity
# ---------------------------------------------------------------------------
class VerificationRun(Base):
    """
    Execution trace for an automated verification pass.
    """
    __tablename__ = "verification_runs"

    run_id = Column(String, primary_key=True, index=True)
    claim_id = Column(String, ForeignKey("political_claims.claim_id", ondelete="CASCADE"), nullable=False, index=True)
    engine_version = Column(String, default="v1.0")
    model_names = Column(JSON, nullable=True)
    started_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    completed_at = Column(DateTime, nullable=True)
    execution_status = Column(String, default="SUCCESS")
    configuration_json = Column(JSON, nullable=True)

    # Relationships
    claim = relationship("Claim", back_populates="verification_runs")
    result = relationship("VerificationResult", back_populates="run", uselist=False, cascade="all, delete-orphan")


# ---------------------------------------------------------------------------
# 9. VerificationResult Entity
# ---------------------------------------------------------------------------
class VerificationResult(Base):
    """
    Synthesized verdict containing confidence, empirical findings, and caveats.
    """
    __tablename__ = "verification_results"

    result_id = Column(String, primary_key=True, index=True)
    claim_id = Column(String, ForeignKey("political_claims.claim_id", ondelete="CASCADE"), nullable=False, index=True)
    run_id = Column(String, ForeignKey("verification_runs.run_id", ondelete="SET NULL"), nullable=True, index=True)

    verdict = Column(Enum(VerificationVerdict), nullable=False, index=True)
    confidence_score = Column(Float, default=0.0)
    support_score = Column(Float, default=0.0)
    contradiction_score = Column(Float, default=0.0)
    uncertainty_score = Column(Float, default=0.0)

    rationale = Column(Text, nullable=False)
    empirical_findings = Column(JSON, nullable=True)  # {"official_value": 6200.0, "claimed_value": 10000.0, "variance_pct": -38.0}
    limitations_and_caveats = Column(Text, nullable=True)
    is_current = Column(Boolean, default=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    claim = relationship("Claim", back_populates="verification_results")
    run = relationship("VerificationRun", back_populates="result")


# ---------------------------------------------------------------------------
# 10. VerificationHistory Entity
# ---------------------------------------------------------------------------
class VerificationHistory(Base):
    """
    Audit log tracking verdict transitions, rationale updates, or human overrides.
    """
    __tablename__ = "verification_history"

    history_id = Column(String, primary_key=True, index=True)
    claim_id = Column(String, ForeignKey("political_claims.claim_id", ondelete="CASCADE"), nullable=False, index=True)
    result_id = Column(String, ForeignKey("verification_results.result_id", ondelete="SET NULL"), nullable=True, index=True)

    previous_verdict = Column(String, nullable=True)
    new_verdict = Column(String, nullable=False)
    change_reason = Column(Text, nullable=True)
    triggered_by = Column(String, default="AUTOMATED_PIPELINE")  # AUTOMATED_PIPELINE, HUMAN_REVIEWER, NEW_EVIDENCE
    changed_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    claim = relationship("Claim", back_populates="verification_history")


# ---------------------------------------------------------------------------
# 11. SourceAssessment Entity
# ---------------------------------------------------------------------------
class SourceAssessment(Base):
    """
    Objective credibility evaluation for an evidence document.
    """
    __tablename__ = "source_assessments"

    assessment_id = Column(String, primary_key=True, index=True)
    document_id = Column(String, ForeignKey("evidence_documents.document_id", ondelete="CASCADE"), nullable=False, index=True)

    source_tier = Column(Enum(SourceTier), nullable=False, index=True)
    tier_weight = Column(Float, default=1.0)
    primary_source_score = Column(Float, default=1.0)
    institutional_independence_score = Column(Float, default=1.0)
    verifiability_score = Column(Float, default=1.0)
    composite_quality_score = Column(Float, default=1.0)
    assessment_notes = Column(Text, nullable=True)
    assessed_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    document = relationship("EvidenceDocument", back_populates="source_assessments")


# ---------------------------------------------------------------------------
# 12. ReviewRecord Entity
# ---------------------------------------------------------------------------
class ReviewRecord(Base):
    """
    Human-in-the-loop audit trail capturing expert analyst validation or overrides.
    """
    __tablename__ = "review_records"

    review_id = Column(String, primary_key=True, index=True)
    claim_id = Column(String, ForeignKey("political_claims.claim_id", ondelete="CASCADE"), nullable=False, index=True)
    reviewer_id = Column(String, nullable=False, index=True)
    reviewer_role = Column(String, default="DOMAIN_EXPERT")
    review_status = Column(Enum(ReviewStatus), default=ReviewStatus.PENDING_REVIEW, index=True)

    original_verdict = Column(String, nullable=True)
    reviewed_verdict = Column(String, nullable=False)
    review_notes = Column(Text, nullable=False)
    override_applied = Column(Boolean, default=False)
    reviewed_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    claim = relationship("Claim", back_populates="reviews")
