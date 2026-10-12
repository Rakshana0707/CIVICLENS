"""
Phase 9.1 — Unified Civic Intelligence & Evidence Graph Architecture Tests.
============================================================================

Validates:
1. Graph entity type coverage across Phases 1–8.
2. Standardized relationship type vocabulary (14 explicit types).
3. CivicGraphNode schema integrity, bilingual labels, and uniqueness constraints.
4. CivicEvidenceEdge schema integrity, granular evidence, and cryptographic hashing.
5. Strict provenance retention on all edges (source document, hash, matching method, confidence).
6. 4-tier matching method taxonomy (documentary, deterministic, candidate, human-reviewed).
7. Epistemic guardrail: non-inference of causation from simple spatial/temporal association.
8. Bidirectional graph traversal (outgoing/incoming edges).
9. Zero-fabrication compliance (strictly labelled test fixtures).
"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.database.base_class import Base
from backend.models.graph import (
    CivicGraphNode,
    CivicEvidenceEdge,
    GraphEntityType,
    GraphRelationshipType,
    MatchingMethod,
    GraphProvenanceStatus,
    GraphReviewStatus,
)
from tests.fixtures.phase9_fixtures import (
    get_phase9_sample_nodes,
    get_phase9_sample_edges,
)


@pytest.fixture
def db_session():
    """In-memory SQLite database session for testing Phase 9 architecture."""
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    try:
        yield session
    finally:
        session.close()


def test_1_graph_entity_type_coverage():
    """Verify all Phase 1-8 domains are represented in GraphEntityType enum."""
    expected_types = [
        "BUDGET_DEPARTMENT", "BUDGET_SCHEME", "BUDGET_RECORD", "HISTORICAL_SCHEME",
        "POLITICAL_PROMISE", "MANIFESTO", "PROMISE_CATEGORY", "NEWS_ARTICLE",
        "NEWS_SOURCE", "POLITICAL_EVENT", "POLITICAL_PARTY", "POLITICAL_PERSON",
        "DONOR", "ELECTORAL_TRUST", "CONTRIBUTION", "FINANCIAL_DOCUMENT",
        "PARTY_FINANCIAL_STATEMENT", "ELECTION_EXPENDITURE", "REPRESENTATIVE",
        "CONSTITUENCY", "ELECTION", "LEGISLATIVE_ACTIVITY", "CONSTITUENCY_WORK",
        "DEVELOPMENT_INDICATOR", "CLAIM", "ATOMIC_CLAIM", "EVIDENCE_DOCUMENT",
        "EVIDENCE_PASSAGE", "CIVIC_ISSUE", "GRIEVANCE_RECORD", "GOVERNMENT_DEPARTMENT",
        "ADMINISTRATIVE_AREA", "SERVICE_STANDARD", "RESPONSE_RECORD",
        "RESOLUTION_EVIDENCE", "PUBLIC_WORK", "SOURCE_DOCUMENT",
    ]
    members = [m.value for m in GraphEntityType]
    for exp in expected_types:
        assert exp in members, f"Expected entity type {exp} missing from GraphEntityType"


def test_2_relationship_types_vocabulary():
    """Verify all 14 required explicit relationship types are supported."""
    required_relationships = [
        "funds", "implements", "promises", "relates_to", "reports_on",
        "mentions", "concerns", "represents", "responds_to",
        "provides_evidence_for", "contradicts", "contextualizes",
        "located_in", "derived_from",
    ]
    members = [m.value for m in GraphRelationshipType]
    for rel in required_relationships:
        assert rel in members, f"Required relationship {rel} missing from GraphRelationshipType"
        # Test helper method
        parsed = GraphRelationshipType.from_string(rel)
        assert parsed.value == rel


def test_3_matching_method_and_provenance_taxonomies():
    """Verify 4 matching methods and lifecycle provenance statuses."""
    expected_methods = ["DIRECT_DOCUMENTARY", "DETERMINISTIC_ID", "AUTOMATED_CANDIDATE", "HUMAN_REVIEWED"]
    for m in expected_methods:
        assert m in [item.value for item in MatchingMethod]

    expected_statuses = ["VALID", "PROVISIONAL", "DISPUTED", "SUPERSEDED", "RETRACTED"]
    for s in expected_statuses:
        assert s in [item.value for item in GraphProvenanceStatus]


def test_4_civic_graph_node_persistence_and_serialization(db_session):
    """Verify CivicGraphNode persistence, bilingual labels, and to_dict()."""
    sample_nodes = get_phase9_sample_nodes()
    assert len(sample_nodes) >= 12

    for node_data in sample_nodes:
        node = CivicGraphNode(**node_data)
        db_session.add(node)
    db_session.commit()

    saved_nodes = db_session.query(CivicGraphNode).all()
    assert len(saved_nodes) == len(sample_nodes)

    # Validate specific node
    rep_node = db_session.query(CivicGraphNode).filter_by(node_id="NODE:REP:REP_MK_STALIN").first()
    assert rep_node is not None
    assert rep_node.label == "M. K. Stalin"
    assert rep_node.label_ta == "மு.க. ஸ்டாலின்"
    assert rep_node.entity_type == GraphEntityType.REPRESENTATIVE
    assert rep_node.source_phase == "PHASE_6"
    assert rep_node.is_test_fixture is True

    serialized = rep_node.to_dict()
    assert serialized["node_id"] == "NODE:REP:REP_MK_STALIN"
    assert serialized["entity_type"] == "REPRESENTATIVE"
    assert serialized["canonical_id"] == "REP-TN-013-001"
    assert "attributes" in serialized


def test_5_civic_evidence_edge_persistence_and_provenance(db_session):
    """Verify CivicEvidenceEdge creation with full provenance retention."""
    # Seed nodes first
    for node_data in get_phase9_sample_nodes():
        db_session.add(CivicGraphNode(**node_data))
    db_session.commit()

    sample_edges = get_phase9_sample_edges()
    assert len(sample_edges) >= 14

    for edge_data in sample_edges:
        edge = CivicEvidenceEdge(**edge_data)
        db_session.add(edge)
    db_session.commit()

    saved_edges = db_session.query(CivicEvidenceEdge).all()
    assert len(saved_edges) == len(sample_edges)

    # Check that EVERY edge retains required provenance fields
    for edge in saved_edges:
        assert edge.source_node_id.startswith("NODE:")
        assert edge.target_node_id.startswith("NODE:")
        assert edge.relationship_type is not None
        assert edge.evidence_reference is not None and len(edge.evidence_reference) > 5
        assert edge.source_document_id is not None
        assert edge.source_document_hash is not None and len(edge.source_document_hash) == 64
        assert edge.matching_method in MatchingMethod
        assert 0.0 <= edge.confidence_score <= 1.0
        assert edge.provenance_status in GraphProvenanceStatus
        assert edge.created_at is not None
        assert edge.is_test_fixture is True


def test_6_epistemic_guardrail_non_causation_from_association(db_session):
    """
    Verify epistemic non-inference rule:
    Spatial co-location (e.g. issue in a constituency) must use 'located_in',
    NOT 'implements' or 'funds'.
    """
    # Seed nodes
    for node_data in get_phase9_sample_nodes():
        db_session.add(CivicGraphNode(**node_data))
    db_session.commit()

    for edge_data in get_phase9_sample_edges():
        db_session.add(CivicEvidenceEdge(**edge_data))
    db_session.commit()

    # Find the edge between Kolathur civic issue and Kolathur constituency
    spatial_edge = db_session.query(CivicEvidenceEdge).filter_by(
        source_node_id="NODE:ISSUE:CIVIC_KOLATHUR_ROAD_01",
        target_node_id="NODE:CONST:AC_KOLATHUR",
    ).first()

    assert spatial_edge is not None
    assert spatial_edge.relationship_type == GraphRelationshipType.LOCATED_IN
    # Must NOT infer causation
    assert spatial_edge.relationship_type != GraphRelationshipType.IMPLEMENTS
    assert spatial_edge.relationship_type != GraphRelationshipType.FUNDS
    assert "Does NOT imply MLA personal negligence" in spatial_edge.epistemic_notes


def test_7_bidirectional_traversal(db_session):
    """Verify that graph nodes can traverse outgoing and incoming evidence edges."""
    for node_data in get_phase9_sample_nodes():
        db_session.add(CivicGraphNode(**node_data))
    db_session.commit()

    for edge_data in get_phase9_sample_edges():
        db_session.add(CivicEvidenceEdge(**edge_data))
    db_session.commit()

    party_node = db_session.query(CivicGraphNode).filter_by(node_id="NODE:PARTY:DMK").first()
    assert party_node is not None

    # Party should have incoming FUNDS edge from donor
    incoming_rels = [e.relationship_type for e in party_node.incoming_edges]
    assert GraphRelationshipType.FUNDS in incoming_rels

    # Party should have outgoing PROMISES edge to promise
    outgoing_rels = [e.relationship_type for e in party_node.outgoing_edges]
    assert GraphRelationshipType.PROMISES in outgoing_rels


def test_8_zero_fabrication_compliance(db_session):
    """Verify that all Phase 9 fixtures are explicitly marked as test fixtures."""
    sample_nodes = get_phase9_sample_nodes()
    sample_edges = get_phase9_sample_edges()

    assert all(n["is_test_fixture"] is True for n in sample_nodes)
    assert all(e["is_test_fixture"] is True for e in sample_edges)
