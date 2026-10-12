"""
Phase 9.1 — Unified Civic Intelligence and Evidence Graph Database Models.
===========================================================================

Defines canonical SQLAlchemy ORM entities for the generic graph layer connecting
Phases 1 through 8 via evidence-backed, auditable relationships:

1. CivicGraphNode: Uniform abstraction of all civic entities (budgets, schemes,
   promises, news, parties, funding, representatives, constituencies, claims,
   civic issues, departments, responses, source documents).
2. CivicEvidenceEdge: First-class graph edge linking two civic entities with
   strictly retained provenance, evidence references, matching method, confidence,
   review status, and epistemic guardrails.

Guiding Principles:
- Reuses existing models from Phases 1–8 rather than duplicating underlying records.
- Explicit relationship types with semantic constraints.
- Epistemic integrity: Strict prohibition against inferring causation from simple association.
- Provenance retention on every single edge (source document, page/section, hash, matching method).
- Support for labelled test fixtures only prior to real Phase 9 collection.
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


class GraphEntityType(str, enum.Enum):
    """
    Standardized entity types spanning Phases 1–8 in CIVICLENS TN.
    """
    BUDGET_DEPARTMENT = "BUDGET_DEPARTMENT"
    BUDGET_SCHEME = "BUDGET_SCHEME"
    BUDGET_RECORD = "BUDGET_RECORD"
    HISTORICAL_SCHEME = "HISTORICAL_SCHEME"
    POLITICAL_PROMISE = "POLITICAL_PROMISE"
    MANIFESTO = "MANIFESTO"
    PROMISE_CATEGORY = "PROMISE_CATEGORY"
    NEWS_ARTICLE = "NEWS_ARTICLE"
    NEWS_SOURCE = "NEWS_SOURCE"
    POLITICAL_EVENT = "POLITICAL_EVENT"
    POLITICAL_PARTY = "POLITICAL_PARTY"
    POLITICAL_PERSON = "POLITICAL_PERSON"
    DONOR = "DONOR"
    ELECTORAL_TRUST = "ELECTORAL_TRUST"
    CONTRIBUTION = "CONTRIBUTION"
    FINANCIAL_DOCUMENT = "FINANCIAL_DOCUMENT"
    PARTY_FINANCIAL_STATEMENT = "PARTY_FINANCIAL_STATEMENT"
    ELECTION_EXPENDITURE = "ELECTION_EXPENDITURE"
    REPRESENTATIVE = "REPRESENTATIVE"
    CONSTITUENCY = "CONSTITUENCY"
    ELECTION = "ELECTION"
    LEGISLATIVE_ACTIVITY = "LEGISLATIVE_ACTIVITY"
    CONSTITUENCY_WORK = "CONSTITUENCY_WORK"
    DEVELOPMENT_INDICATOR = "DEVELOPMENT_INDICATOR"
    CLAIM = "CLAIM"
    ATOMIC_CLAIM = "ATOMIC_CLAIM"
    EVIDENCE_DOCUMENT = "EVIDENCE_DOCUMENT"
    EVIDENCE_PASSAGE = "EVIDENCE_PASSAGE"
    CIVIC_ISSUE = "CIVIC_ISSUE"
    GRIEVANCE_RECORD = "GRIEVANCE_RECORD"
    GOVERNMENT_DEPARTMENT = "GOVERNMENT_DEPARTMENT"
    ADMINISTRATIVE_AREA = "ADMINISTRATIVE_AREA"
    SERVICE_STANDARD = "SERVICE_STANDARD"
    RESPONSE_RECORD = "RESPONSE_RECORD"
    RESOLUTION_EVIDENCE = "RESOLUTION_EVIDENCE"
    PUBLIC_WORK = "PUBLIC_WORK"
    SOURCE_DOCUMENT = "SOURCE_DOCUMENT"


class GraphRelationshipType(str, enum.Enum):
    """
    Standardized explicit relationship types in the evidence graph.
    Do not infer causation from simple association.
    """
    FUNDS = "funds"
    IMPLEMENTS = "implements"
    PROMISES = "promises"
    RELATES_TO = "relates_to"
    REPORTS_ON = "reports_on"
    MENTIONS = "mentions"
    CONCERNS = "concerns"
    REPRESENTS = "represents"
    RESPONDS_TO = "responds_to"
    PROVIDES_EVIDENCE_FOR = "provides_evidence_for"
    CONTRADICTS = "contradicts"
    CONTEXTUALIZES = "contextualizes"
    LOCATED_IN = "located_in"
    DERIVED_FROM = "derived_from"

    @classmethod
    def from_string(cls, val: Any) -> "GraphRelationshipType":
        if isinstance(val, cls):
            return val
        clean = str(val).strip().lower()
        for item in cls:
            if item.value == clean or item.name.lower() == clean:
                return item
        raise ValueError(f"Unknown GraphRelationshipType: {val}")


class MatchingMethod(str, enum.Enum):
    """
    Methodology through which an edge was established.
    Distinguishes direct documentary evidence from heuristic candidates.
    """
    DIRECT_DOCUMENTARY = "DIRECT_DOCUMENTARY"      # Explicitly stated in gazette, Hansard, or primary source
    DETERMINISTIC_ID = "DETERMINISTIC_ID"          # Exact primary key, demand number, portal token match
    AUTOMATED_CANDIDATE = "AUTOMATED_CANDIDATE"    # Multi-signal NLP, entity overlap, vector similarity
    HUMAN_REVIEWED = "HUMAN_REVIEWED"              # Verified by human domain auditor


class GraphProvenanceStatus(str, enum.Enum):
    """
    Lifecycle provenance status of an edge in the graph.
    """
    VALID = "VALID"
    PROVISIONAL = "PROVISIONAL"
    DISPUTED = "DISPUTED"
    SUPERSEDED = "SUPERSEDED"
    RETRACTED = "RETRACTED"


class GraphReviewStatus(str, enum.Enum):
    """
    Human-in-the-loop audit review status.
    """
    PENDING_REVIEW = "PENDING_REVIEW"
    VERIFIED = "VERIFIED"
    REJECTED = "REJECTED"
    OVERRIDDEN = "OVERRIDDEN"


# ---------------------------------------------------------------------------
# 1. CivicGraphNode Entity
# ---------------------------------------------------------------------------
class CivicGraphNode(Base):
    """
    Canonical node representing any civic intelligence entity in Tamil Nadu.
    Provides uniform addressing across heterogeneous Phase 1–8 tables.
    """
    __tablename__ = "civic_graph_nodes"

    node_id = Column(String(120), primary_key=True, index=True)  # e.g., "NODE:REP:REP-MK-STALIN", "NODE:SCHEME:SCH-042"
    entity_type = Column(Enum(GraphEntityType), nullable=False, index=True)
    canonical_id = Column(String(100), nullable=False, index=True)  # ID in underlying Phase 1-8 table
    label = Column(String(300), nullable=False, index=True)
    label_ta = Column(String(400), nullable=True)
    source_phase = Column(String(50), nullable=False, index=True)  # "PHASE_1", "PHASE_2", ..., "PHASE_8"

    attributes_json = Column(JSON, nullable=True)  # Lightweight entity summary for fast graph rendering
    is_test_fixture = Column(Boolean, default=False, nullable=False, index=True)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Outgoing and incoming edges
    outgoing_edges = relationship(
        "CivicEvidenceEdge",
        foreign_keys="[CivicEvidenceEdge.source_node_id]",
        back_populates="source_node",
        cascade="all, delete-orphan",
    )
    incoming_edges = relationship(
        "CivicEvidenceEdge",
        foreign_keys="[CivicEvidenceEdge.target_node_id]",
        back_populates="target_node",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        UniqueConstraint('entity_type', 'canonical_id', name='uq_graph_node_entity'),
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "node_id": self.node_id,
            "entity_type": self.entity_type.value if hasattr(self.entity_type, "value") else str(self.entity_type),
            "canonical_id": self.canonical_id,
            "label": self.label,
            "label_ta": self.label_ta,
            "source_phase": self.source_phase,
            "attributes": self.attributes_json or {},
            "is_test_fixture": self.is_test_fixture,
            "outgoing_edges_count": len(self.outgoing_edges) if self.outgoing_edges else 0,
            "incoming_edges_count": len(self.incoming_edges) if self.incoming_edges else 0,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


# ---------------------------------------------------------------------------
# 2. CivicEvidenceEdge Entity
# ---------------------------------------------------------------------------
class CivicEvidenceEdge(Base):
    """
    First-class directed graph edge connecting two civic entities with evidence-backed provenance.
    
    Guarantees:
    - Retains source and target entity references.
    - Retains relationship type from explicit semantic vocabulary.
    - Retains evidence reference (excerpt, quote, table number, page number).
    - Retains source document reference (document ID, official URL, SHA-256 hash).
    - Retains matching method (documentary, deterministic, candidate, human-reviewed).
    - Retains confidence score and human review status.
    - Retains creation timestamp and provenance status.
    """
    __tablename__ = "civic_evidence_edges"

    edge_id = Column(String(120), primary_key=True, index=True)  # e.g., "EDGE:FUNDS:DOC-001:BUD-01:SCH-02"
    source_node_id = Column(String(120), ForeignKey("civic_graph_nodes.node_id", ondelete="CASCADE"), nullable=False, index=True)
    target_node_id = Column(String(120), ForeignKey("civic_graph_nodes.node_id", ondelete="CASCADE"), nullable=False, index=True)

    relationship_type = Column(Enum(GraphRelationshipType), nullable=False, index=True)

    # Granular Evidence Provenance
    evidence_reference = Column(Text, nullable=True)        # Exact quote, table cell, or paragraph excerpt
    source_document_id = Column(String(120), nullable=True, index=True)  # Cross-phase source document identifier
    source_document_url = Column(String(500), nullable=True)
    source_document_hash = Column(String(64), nullable=True)             # SHA-256 hash of originating artifact

    # Methodology & Epistemic Audit
    matching_method = Column(Enum(MatchingMethod), nullable=False, default=MatchingMethod.DIRECT_DOCUMENTARY, index=True)
    confidence_score = Column(Float, nullable=False, default=1.0)
    review_status = Column(Enum(GraphReviewStatus), default=GraphReviewStatus.PENDING_REVIEW, index=True)
    provenance_status = Column(Enum(GraphProvenanceStatus), default=GraphProvenanceStatus.VALID, index=True)

    epistemic_notes = Column(Text, nullable=True)           # Causal caveat or justification
    properties_json = Column(JSON, nullable=True)           # Domain attributes (e.g. amount_inr, fiscal_year, vote_count)
    is_test_fixture = Column(Boolean, default=False, nullable=False, index=True)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    source_node = relationship(
        "CivicGraphNode",
        foreign_keys=[source_node_id],
        back_populates="outgoing_edges",
    )
    target_node = relationship(
        "CivicGraphNode",
        foreign_keys=[target_node_id],
        back_populates="incoming_edges",
    )

    __table_args__ = (
        UniqueConstraint('source_node_id', 'target_node_id', 'relationship_type', 'source_document_id', name='uq_evidence_edge'),
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "edge_id": self.edge_id,
            "source_node_id": self.source_node_id,
            "target_node_id": self.target_node_id,
            "relationship_type": self.relationship_type.value if hasattr(self.relationship_type, "value") else str(self.relationship_type),
            "evidence_reference": self.evidence_reference,
            "source_document_id": self.source_document_id,
            "source_document_url": self.source_document_url,
            "source_document_hash": self.source_document_hash,
            "matching_method": self.matching_method.value if hasattr(self.matching_method, "value") else str(self.matching_method),
            "confidence_score": self.confidence_score,
            "review_status": self.review_status.value if hasattr(self.review_status, "value") else str(self.review_status),
            "provenance_status": self.provenance_status.value if hasattr(self.provenance_status, "value") else str(self.provenance_status),
            "epistemic_notes": self.epistemic_notes,
            "properties": self.properties_json or {},
            "is_test_fixture": self.is_test_fixture,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
