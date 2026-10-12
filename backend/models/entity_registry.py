"""
Phase 9.2 — Cross-Phase Entity Registry and Identity Resolution Models.
========================================================================

Defines canonical SQLAlchemy ORM entities for the shared entity registry
enabling records across Phases 1 through 8 to reference verified real-world entities:

1. CanonicalEntity: Canonical authority record representing a real-world entity
   across 10 supported domains (departments, schemes, parties, representatives,
   constituencies, administrative areas, claims, civic issues, source documents, works).
2. SourceIdentifierMapping: Preserves original source-specific identifiers and original
   reported source names (never overwritten).
3. EntityAlias: Manages alternate names, historical names, acronyms, transliterations,
   and bilingual Tamil/English variants with validity time-bounds.
4. EntityAuditRecord: Comprehensive audit history for merges, splits, and state changes.
5. DuplicateCandidateReview: Tracks potential duplicates, uncertain matches, divergence
   reasons, and human review decisions.

Core Directives:
- Strict non-merging safeguard: Do NOT merge distinct entities merely because names are similar.
- Preservation of original source names.
- Explicit matching method, confidence, and review status on all linkages.
"""

from __future__ import annotations

import enum
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from sqlalchemy import (
    Column, Integer, String, Text, DateTime, ForeignKey, Float, Boolean, Enum, JSON, UniqueConstraint
)
from sqlalchemy.orm import relationship
from backend.database.base_class import Base


class RegistryEntityType(str, enum.Enum):
    """
    10 Supported canonical entity types across CIVICLENS TN.
    """
    GOVERNMENT_DEPARTMENT = "government_department"
    SCHEME = "scheme"
    POLITICAL_PARTY = "political_party"
    REPRESENTATIVE = "representative"
    CONSTITUENCY = "constituency"
    ADMINISTRATIVE_AREA = "administrative_area"
    PUBLIC_CLAIM = "public_claim"
    CIVIC_ISSUE = "civic_issue"
    SOURCE_DOCUMENT = "source_document"
    PUBLIC_WORK = "public_work"

    @classmethod
    def from_string(cls, val: Any) -> "RegistryEntityType":
        if isinstance(val, cls):
            return val
        clean = str(val).strip().lower()
        for item in cls:
            if item.value == clean or item.name.lower() == clean:
                return item
        raise ValueError(f"Unknown RegistryEntityType: {val}")


class EntityLifecycleStatus(str, enum.Enum):
    """
    Lifecycle status of a canonical entity.
    """
    ACTIVE = "ACTIVE"
    MERGED = "MERGED"
    SPLIT = "SPLIT"
    DEPRECATED = "DEPRECATED"


class ResolutionMethod(str, enum.Enum):
    """
    Methodology used to resolve or map an identifier to the canonical entity.
    """
    DETERMINISTIC_ID = "DETERMINISTIC_ID"
    EXACT_NAME = "EXACT_NAME"
    ALIAS_MATCH = "ALIAS_MATCH"
    TRANSLITERATION_MATCH = "TRANSLITERATION_MATCH"
    HISTORICAL_NAME_MATCH = "HISTORICAL_NAME_MATCH"
    FUZZY_MATCH = "FUZZY_MATCH"
    HUMAN_REVIEWED = "HUMAN_REVIEWED"


class ReviewStatusEnum(str, enum.Enum):
    """
    Human review status for mappings and candidate links.
    """
    VERIFIED = "VERIFIED"
    PENDING_REVIEW = "PENDING_REVIEW"
    DISPUTED = "DISPUTED"
    REJECTED = "REJECTED"


class AliasTypeEnum(str, enum.Enum):
    """
    Taxonomy of alias relationships.
    """
    OFFICIAL_ALIAS = "OFFICIAL_ALIAS"
    HISTORICAL_NAME = "HISTORICAL_NAME"
    ACRONYM = "ACRONYM"
    TRANSLITERATION = "TRANSLITERATION"
    SPELLING_VARIANT = "SPELLING_VARIANT"
    HONORIFIC_VARIANT = "HONORIFIC_VARIANT"


class EntityOperationType(str, enum.Enum):
    """
    Audit ledger operation categories.
    """
    CREATE = "CREATE"
    MERGE = "MERGE"
    SPLIT = "SPLIT"
    ALIAS_ADDED = "ALIAS_ADDED"
    STATUS_CHANGED = "STATUS_CHANGED"
    UNCERTAIN_MATCH_REVIEW = "UNCERTAIN_MATCH_REVIEW"


class DuplicateReviewStatus(str, enum.Enum):
    """
    Review disposition for candidate duplicate pairs.
    """
    PENDING_REVIEW = "PENDING_REVIEW"
    CONFIRMED_DUPLICATE = "CONFIRMED_DUPLICATE"
    CONFIRMED_DISTINCT = "CONFIRMED_DISTINCT"
    REJECTED = "REJECTED"


# ---------------------------------------------------------------------------
# 1. CanonicalEntity Model
# ---------------------------------------------------------------------------
class CanonicalEntity(Base):
    """
    Canonical authority record representing a real-world civic entity.
    Reuses existing IDs (e.g. DEPT-MAWS, AC-013, SCH-042) wherever possible.
    """
    __tablename__ = "canonical_entities"

    entity_id = Column(String(120), primary_key=True, index=True)
    entity_type = Column(Enum(RegistryEntityType), nullable=False, index=True)
    
    canonical_name_en = Column(String(300), nullable=False, index=True)
    canonical_name_ta = Column(String(400), nullable=True, index=True)
    normalized_name = Column(String(300), nullable=False, index=True)
    category_or_subtype = Column(String(100), nullable=True, index=True)

    # Time-bounded validity
    valid_from = Column(String(50), nullable=True)  # YYYY or YYYY-MM-DD
    valid_to = Column(String(50), nullable=True)    # NULL if currently active

    status = Column(Enum(EntityLifecycleStatus), default=EntityLifecycleStatus.ACTIVE, nullable=False, index=True)
    merged_into_id = Column(String(120), ForeignKey("canonical_entities.entity_id", ondelete="SET NULL"), nullable=True, index=True)

    metadata_json = Column(JSON, nullable=True)
    is_test_fixture = Column(Boolean, default=False, nullable=False, index=True)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    aliases = relationship("EntityAlias", back_populates="entity", cascade="all, delete-orphan")
    source_mappings = relationship("SourceIdentifierMapping", back_populates="entity", cascade="all, delete-orphan")
    audit_records = relationship(
        "EntityAuditRecord",
        foreign_keys="[EntityAuditRecord.primary_entity_id]",
        back_populates="primary_entity",
        cascade="all, delete-orphan",
    )
    merged_into = relationship("CanonicalEntity", remote_side=[entity_id], backref="merged_entities")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "entity_id": self.entity_id,
            "entity_type": self.entity_type.value if hasattr(self.entity_type, "value") else str(self.entity_type),
            "canonical_name_en": self.canonical_name_en,
            "canonical_name_ta": self.canonical_name_ta,
            "normalized_name": self.normalized_name,
            "category_or_subtype": self.category_or_subtype,
            "valid_from": self.valid_from,
            "valid_to": self.valid_to,
            "status": self.status.value if hasattr(self.status, "value") else str(self.status),
            "merged_into_id": self.merged_into_id,
            "metadata": self.metadata_json or {},
            "is_test_fixture": self.is_test_fixture,
            "aliases_count": len(self.aliases) if self.aliases else 0,
            "mappings_count": len(self.source_mappings) if self.source_mappings else 0,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


# ---------------------------------------------------------------------------
# 2. SourceIdentifierMapping Model
# ---------------------------------------------------------------------------
class SourceIdentifierMapping(Base):
    """
    Connects an upstream phase/source record ID and reported name to the canonical entity.
    Preserves original source name even after normalization.
    """
    __tablename__ = "source_identifier_mappings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    mapping_id = Column(String(120), unique=True, nullable=False, index=True)
    entity_id = Column(String(120), ForeignKey("canonical_entities.entity_id", ondelete="CASCADE"), nullable=False, index=True)

    source_system = Column(String(100), nullable=False, index=True)      # e.g., "TN_BUDGET_DDG", "ECI", "TNEGA_1100"
    source_record_id = Column(String(150), nullable=False, index=True)   # Original key in upstream system
    source_record_name = Column(String(400), nullable=False)             # Verbatim original name as reported

    matching_method = Column(Enum(ResolutionMethod), default=ResolutionMethod.DETERMINISTIC_ID, nullable=False, index=True)
    confidence_score = Column(Float, default=1.0, nullable=False)
    review_status = Column(Enum(ReviewStatusEnum), default=ReviewStatusEnum.VERIFIED, nullable=False, index=True)
    notes = Column(Text, nullable=True)
    is_test_fixture = Column(Boolean, default=False, nullable=False, index=True)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    entity = relationship("CanonicalEntity", back_populates="source_mappings")

    __table_args__ = (
        UniqueConstraint('source_system', 'source_record_id', name='uq_source_sys_record'),
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "mapping_id": self.mapping_id,
            "entity_id": self.entity_id,
            "source_system": self.source_system,
            "source_record_id": self.source_record_id,
            "source_record_name": self.source_record_name,
            "matching_method": self.matching_method.value if hasattr(self.matching_method, "value") else str(self.matching_method),
            "confidence_score": self.confidence_score,
            "review_status": self.review_status.value if hasattr(self.review_status, "value") else str(self.review_status),
            "notes": self.notes,
            "is_test_fixture": self.is_test_fixture,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


# ---------------------------------------------------------------------------
# 3. EntityAlias Model
# ---------------------------------------------------------------------------
class EntityAlias(Base):
    """
    Alternate names, acronyms, historical names, and transliterated representations.
    Supports time-bounded validity (e.g. historical place or department names).
    """
    __tablename__ = "entity_aliases"

    id = Column(Integer, primary_key=True, autoincrement=True)
    alias_id = Column(String(120), unique=True, nullable=False, index=True)
    entity_id = Column(String(120), ForeignKey("canonical_entities.entity_id", ondelete="CASCADE"), nullable=False, index=True)

    alias_name = Column(String(400), nullable=False, index=True)
    normalized_alias = Column(String(400), nullable=False, index=True)
    language = Column(String(20), default="en", index=True)             # en, ta, translit, bilingual
    alias_type = Column(Enum(AliasTypeEnum), default=AliasTypeEnum.OFFICIAL_ALIAS, nullable=False, index=True)

    valid_from = Column(String(50), nullable=True)                      # Historical validity start
    valid_to = Column(String(50), nullable=True)                        # Historical validity end
    source_reference = Column(String(300), nullable=True)
    is_test_fixture = Column(Boolean, default=False, nullable=False, index=True)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    entity = relationship("CanonicalEntity", back_populates="aliases")

    __table_args__ = (
        UniqueConstraint('entity_id', 'alias_name', 'alias_type', name='uq_entity_alias_type'),
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "alias_id": self.alias_id,
            "entity_id": self.entity_id,
            "alias_name": self.alias_name,
            "normalized_alias": self.normalized_alias,
            "language": self.language,
            "alias_type": self.alias_type.value if hasattr(self.alias_type, "value") else str(self.alias_type),
            "valid_from": self.valid_from,
            "valid_to": self.valid_to,
            "source_reference": self.source_reference,
            "is_test_fixture": self.is_test_fixture,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


# ---------------------------------------------------------------------------
# 4. EntityAuditRecord Model
# ---------------------------------------------------------------------------
class EntityAuditRecord(Base):
    """
    Immutable audit history recording all entity merges, splits, and updates.
    """
    __tablename__ = "entity_audit_records"

    id = Column(Integer, primary_key=True, autoincrement=True)
    audit_id = Column(String(120), unique=True, nullable=False, index=True)
    operation_type = Column(Enum(EntityOperationType), nullable=False, index=True)

    primary_entity_id = Column(String(120), ForeignKey("canonical_entities.entity_id", ondelete="CASCADE"), nullable=False, index=True)
    secondary_entity_id = Column(String(120), nullable=True, index=True)

    rationale = Column(Text, nullable=False)                            # Mandatory justification
    performed_by = Column(String(100), nullable=False, default="SYSTEM_NORMALIZER")
    previous_state_json = Column(JSON, nullable=True)
    new_state_json = Column(JSON, nullable=True)

    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)

    # Relationships
    primary_entity = relationship("CanonicalEntity", foreign_keys=[primary_entity_id], back_populates="audit_records")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "audit_id": self.audit_id,
            "operation_type": self.operation_type.value if hasattr(self.operation_type, "value") else str(self.operation_type),
            "primary_entity_id": self.primary_entity_id,
            "secondary_entity_id": self.secondary_entity_id,
            "rationale": self.rationale,
            "performed_by": self.performed_by,
            "previous_state": self.previous_state_json or {},
            "new_state": self.new_state_json or {},
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
        }


# ---------------------------------------------------------------------------
# 5. DuplicateCandidateReview Model
# ---------------------------------------------------------------------------
class DuplicateCandidateReview(Base):
    """
    Tracks potential duplicate entities, similarity scores, divergence rationale,
    and expert review outcomes.
    """
    __tablename__ = "duplicate_candidate_reviews"

    id = Column(Integer, primary_key=True, autoincrement=True)
    candidate_id = Column(String(120), unique=True, nullable=False, index=True)
    entity_type = Column(Enum(RegistryEntityType), nullable=False, index=True)

    entity_a_id = Column(String(120), ForeignKey("canonical_entities.entity_id", ondelete="CASCADE"), nullable=False, index=True)
    entity_b_id = Column(String(120), ForeignKey("canonical_entities.entity_id", ondelete="CASCADE"), nullable=False, index=True)

    similarity_score = Column(Float, nullable=False)
    matching_method = Column(String(50), nullable=False)
    divergence_reasons = Column(JSON, nullable=True)                   # Why not automatically merged (e.g. DIFFERENT_DISTRICT)

    review_status = Column(Enum(DuplicateReviewStatus), default=DuplicateReviewStatus.PENDING_REVIEW, nullable=False, index=True)
    reviewer_notes = Column(Text, nullable=True)
    reviewed_by = Column(String(100), nullable=True)
    reviewed_at = Column(DateTime, nullable=True)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    entity_a = relationship("CanonicalEntity", foreign_keys=[entity_a_id])
    entity_b = relationship("CanonicalEntity", foreign_keys=[entity_b_id])

    __table_args__ = (
        UniqueConstraint('entity_a_id', 'entity_b_id', name='uq_duplicate_pair'),
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "candidate_id": self.candidate_id,
            "entity_type": self.entity_type.value if hasattr(self.entity_type, "value") else str(self.entity_type),
            "entity_a_id": self.entity_a_id,
            "entity_b_id": self.entity_b_id,
            "similarity_score": self.similarity_score,
            "matching_method": self.matching_method,
            "divergence_reasons": self.divergence_reasons or [],
            "review_status": self.review_status.value if hasattr(self.review_status, "value") else str(self.review_status),
            "reviewer_notes": self.reviewer_notes,
            "reviewed_by": self.reviewed_by,
            "reviewed_at": self.reviewed_at.isoformat() if self.reviewed_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
