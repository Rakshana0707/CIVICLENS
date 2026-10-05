import enum
from datetime import datetime, timezone
from sqlalchemy import (
    Column, Integer, String, Text, DateTime, ForeignKey, Float, Boolean, Enum, JSON
)
from sqlalchemy.orm import relationship
from backend.database.base_class import Base

class PromiseStatus(str, enum.Enum):
    NOT_ASSESSED = "not_assessed"
    NO_EVIDENCE_FOUND = "no_evidence_found"
    ANNOUNCED = "announced"
    POLICY_ACTION = "policy_action"
    PARTIALLY_IMPLEMENTED = "partially_implemented"
    IMPLEMENTED = "implemented"
    UNCLEAR = "unclear"
    DISPUTED = "disputed"


class PoliticalPromise(Base):
    """
    Core Promise entity representing an extracted political manifesto promise.
    Keeps promise data, evidence links, scheme links, and assessments completely separated.
    """
    __tablename__ = "political_promises"

    promise_id = Column(String, primary_key=True, index=True)
    manifesto_id = Column(String, ForeignKey("manifestos.manifesto_id", ondelete="CASCADE"), nullable=False, index=True)

    original_text = Column(Text, nullable=False)  # Exact original wording preserved
    normalized_text = Column(Text, nullable=False)
    page_number = Column(Integer, nullable=True)
    section = Column(String, nullable=True)
    language = Column(String, default="Unknown")
    classification = Column(String, default="general_policy")
    extraction_method = Column(String, nullable=True)
    extraction_confidence = Column(Float, default=1.0)
    is_ambiguous = Column(Boolean, default=False)
    is_test_fixture = Column(Boolean, default=False)

    metadata_json = Column(JSON, nullable=True)  # Target pop, sector, dept, geography, targets, etc.

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    manifesto = relationship("Manifesto", back_populates="promises")
    categories = relationship("PromiseCategoryMapping", back_populates="promise", cascade="all, delete-orphan")
    evidence_links = relationship("PromiseEvidenceLink", back_populates="promise", cascade="all, delete-orphan")
    scheme_links = relationship("PromiseSchemeLink", back_populates="promise", cascade="all, delete-orphan")
    assessments = relationship("PromiseAssessment", back_populates="promise", cascade="all, delete-orphan")
    assessment_history = relationship("PromiseAssessmentHistory", back_populates="promise", cascade="all, delete-orphan")


class PromiseCategory(Base):
    """
    Configurable category taxonomy entity for political promises.
    """
    __tablename__ = "promise_categories"

    id = Column(Integer, primary_key=True, index=True)
    category_code = Column(String, nullable=False, unique=True, index=True)  # e.g. "Education", "Healthcare"
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)

    mappings = relationship("PromiseCategoryMapping", back_populates="category", cascade="all, delete-orphan")


class PromiseCategoryMapping(Base):
    """
    Junction table mapping Promises to Categories (supports multi-category mapping).
    """
    __tablename__ = "promise_category_mappings"

    id = Column(Integer, primary_key=True, index=True)
    promise_id = Column(String, ForeignKey("political_promises.promise_id", ondelete="CASCADE"), nullable=False, index=True)
    category_id = Column(Integer, ForeignKey("promise_categories.id", ondelete="CASCADE"), nullable=False, index=True)
    is_primary = Column(Boolean, default=False)
    confidence = Column(Float, default=1.0)

    promise = relationship("PoliticalPromise", back_populates="categories")
    category = relationship("PromiseCategory", back_populates="mappings")


class PromiseEvidenceLink(Base):
    """
    Explicit junction linking a Promise to Evidence (separate from promise and assessment records).
    Supports multiple evidence records per promise.
    """
    __tablename__ = "promise_evidence_links"

    id = Column(Integer, primary_key=True, index=True)
    promise_id = Column(String, ForeignKey("political_promises.promise_id", ondelete="CASCADE"), nullable=False, index=True)
    evidence_id = Column(Integer, ForeignKey("evidence.id", ondelete="CASCADE"), nullable=False, index=True)

    similarity_score = Column(Float, nullable=True)
    matching_method = Column(String, nullable=True)  # e.g. "vector_similarity", "keyword_exact"
    relevance_notes = Column(Text, nullable=True)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    promise = relationship("PoliticalPromise", back_populates="evidence_links")
    evidence = relationship("Evidence")


class PromiseSchemeLink(Base):
    """
    Explicit junction linking a Promise to Historical Schemes / Budget Schemes.
    Supports multiple historical schemes per promise.
    """
    __tablename__ = "promise_scheme_links"

    id = Column(Integer, primary_key=True, index=True)
    promise_id = Column(String, ForeignKey("political_promises.promise_id", ondelete="CASCADE"), nullable=False, index=True)
    historical_scheme_id = Column(Integer, ForeignKey("historical_schemes.id", ondelete="SET NULL"), nullable=True, index=True)
    budget_scheme_id = Column(Integer, ForeignKey("budget_schemes.id", ondelete="SET NULL"), nullable=True, index=True)

    similarity_score = Column(Float, nullable=True)
    matching_method = Column(String, nullable=True)
    match_type = Column(String, nullable=True)  # e.g. "pre_existing_scheme", "new_scheme_instance"
    notes = Column(Text, nullable=True)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    promise = relationship("PoliticalPromise", back_populates="scheme_links")
    historical_scheme = relationship("HistoricalScheme")
    budget_scheme = relationship("BudgetScheme")


class PromiseAssessment(Base):
    """
    Assessment entity evaluating implementation status of a Promise.
    Separated from Promise, Evidence, and Similarity.
    """
    __tablename__ = "promise_assessments"

    id = Column(Integer, primary_key=True, index=True)
    promise_id = Column(String, ForeignKey("political_promises.promise_id", ondelete="CASCADE"), nullable=False, index=True)

    status = Column(Enum(PromiseStatus), nullable=False, default=PromiseStatus.NOT_ASSESSED, index=True)
    confidence_score = Column(Float, default=0.0)
    rationale = Column(Text, nullable=True)
    assessed_by = Column(String, nullable=True)  # e.g. "rule_engine_v1", "human_expert"
    assessment_date = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    is_current = Column(Boolean, default=True)

    promise = relationship("PoliticalPromise", back_populates="assessments")
    history_entries = relationship("PromiseAssessmentHistory", back_populates="assessment", cascade="all, delete-orphan")


class PromiseAssessmentHistory(Base):
    """
    Audit trail entity tracking status changes of promise assessments over time.
    """
    __tablename__ = "promise_assessment_history"

    id = Column(Integer, primary_key=True, index=True)
    promise_id = Column(String, ForeignKey("political_promises.promise_id", ondelete="CASCADE"), nullable=False, index=True)
    assessment_id = Column(Integer, ForeignKey("promise_assessments.id", ondelete="SET NULL"), nullable=True, index=True)

    previous_status = Column(String, nullable=True)
    new_status = Column(String, nullable=False)
    change_reason = Column(Text, nullable=True)
    changed_by = Column(String, nullable=True)
    changed_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    promise = relationship("PoliticalPromise", back_populates="assessment_history")
    assessment = relationship("PromiseAssessment", back_populates="history_entries")
