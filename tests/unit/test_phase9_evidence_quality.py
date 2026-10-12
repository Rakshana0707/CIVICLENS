"""
Phase 9.6 — Evidence Quality and Contradiction Analysis Tests.
==============================================================

Validates:
1. Multi-factor evidence quality scorecard (9 documented factors with inputs, interpretation, and limitations).
2. Source reliability tier mapping (Statutory vs Executive vs Journalistic vs Citizen).
3. Conflicting dates detection across records.
4. Incompatible status reports detection (COMPLETED vs STALLED).
5. Contradictory claim evidence with documented evidentiary weight comparison (newer is NOT automatically correct).
6. Stale and outdated documents detection.
7. Missing source documents and incomplete provenance detection.
8. Evidence completeness assessment (coverage of required statutory elements).
9. Persistent conflict preservation in CivicConflictRecord without data suppression.
10. REST API endpoints: /api/graph/conflicts, /api/graph/edges/<id>/quality, /api/graph/nodes/<id>/completeness.
"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.api.app import create_app
from backend.database.base_class import Base
from backend.models.entity_registry import (
    CanonicalEntity,
    RegistryEntityType,
    EntityLifecycleStatus,
)
from backend.models.graph import (
    CivicGraphNode,
    CivicEvidenceEdge,
    CivicConflictRecord,
    ConflictTypeEnum,
    ConflictSeverityEnum,
    ConflictResolutionStatus,
    GraphEntityType,
    GraphRelationshipType,
    MatchingMethod,
    GraphProvenanceStatus,
    GraphReviewStatus,
)
from backend.services.graph_storage_service import GraphStorageService
from backend.services.evidence_quality_service import (
    EvidenceQualityService,
    SOURCE_TIER_WEIGHTS,
)


@pytest.fixture
def db_session():
    """In-memory SQLite database session for Phase 9.6 quality tests."""
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine, expire_on_commit=False)
    session = Session()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def quality_fixture_graph(db_session):
    """Seed graph nodes and edges covering various quality tiers and conflicts."""
    # 1. Scheme node
    node_scheme = GraphStorageService.create_or_get_node(
        db_session,
        node_id="NODE:SCHEME:DESAL_NEMMELI",
        entity_type=GraphEntityType.BUDGET_SCHEME,
        canonical_id="SCH-NEMMELI-150MLD",
        label="Nemmeli 150 MLD Desalination Plant Augmentation",
        source_phase="PHASE_2",
        is_test_fixture=True,
    )

    # 2. Budget record node
    node_budget = GraphStorageService.create_or_get_node(
        db_session,
        node_id="NODE:BUDGET:DEMAND_34_2022",
        entity_type=GraphEntityType.BUDGET_RECORD,
        canonical_id="BUD-DEM34-2022",
        label="Demand 34 Capital Outlay on Water Supply",
        source_phase="PHASE_1",
        is_test_fixture=True,
    )

    # 3. High quality statutory edge
    edge_statutory = GraphStorageService.add_evidence_edge(
        db_session,
        source_node_id=node_budget.node_id,
        target_node_id=node_scheme.node_id,
        relationship_type=GraphRelationshipType.FUNDS,
        evidence_reference="Demand 34 Detailed Budget Estimates 2022-23 Page 104 Table 4",
        source_document_id="DOC-CAG-AUDIT-REPORT-2022-34",
        source_document_url="https://cag.gov.in/en/audit-report/details/1124",
        source_document_hash="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        matching_method=MatchingMethod.DIRECT_DOCUMENTARY,
        confidence_score=1.0,
        review_status=GraphReviewStatus.VERIFIED,
        valid_from="2022-04-01",
        valid_to="2023-03-31",
        properties={"status": "SANCTIONED", "completion_year": 2023},
        is_test_fixture=True,
    )

    # 4. Conflicting edge with incompatible status and conflicting date
    edge_news_conflicting = GraphStorageService.add_evidence_edge(
        db_session,
        source_node_id=node_scheme.node_id,
        target_node_id=node_budget.node_id,
        relationship_type=GraphRelationshipType.CONTEXTUALIZES,
        evidence_reference="Local media investigative report cites contractor disputes",
        source_document_id="DOC-NEWS-ARTICLE-CHENNAI-2025",
        source_document_url="https://news.civiclens.test/article/4412",
        source_document_hash="9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08",
        matching_method=MatchingMethod.DIRECT_DOCUMENTARY,
        confidence_score=0.85,
        review_status=GraphReviewStatus.PENDING_REVIEW,
        valid_from="2025-01-01",
        properties={"status": "STALLED", "completion_year": 2026},
        is_test_fixture=True,
    )

    # 5. Stale edge from an outdated document prior to 2018
    edge_stale = GraphStorageService.add_evidence_edge(
        db_session,
        source_node_id=node_scheme.node_id,
        target_node_id=node_budget.node_id,
        relationship_type=GraphRelationshipType.RELATES_TO,
        evidence_reference="Preliminary feasibility draft 2015",
        source_document_id="DOC-DRAFT-FEASIBILITY-2015",
        valid_from="2015-01-01",
        properties={"is_stale_source": True},
        is_test_fixture=True,
    )

    # 6. Edge with incomplete provenance (missing hash and missing excerpt)
    edge_incomplete = GraphStorageService.add_evidence_edge(
        db_session,
        source_node_id=node_budget.node_id,
        target_node_id=node_scheme.node_id,
        relationship_type=GraphRelationshipType.MENTIONS,
        evidence_reference=None,  # Missing excerpt!
        source_document_id="DOC-GENERIC-REFERENCE",
        source_document_hash=None,  # Missing hash!
        is_test_fixture=True,
    )

    # 7. Claim node with conflicting dialectical evidence
    node_claim = GraphStorageService.create_or_get_node(
        db_session,
        node_id="NODE:CLAIM:DESAL_OUTPUT_MET",
        entity_type=GraphEntityType.CLAIM,
        canonical_id="CLAIM-DESAL-150",
        label="Nemmeli plant operating consistently at full 150 MLD capacity",
        source_phase="PHASE_6",
        is_test_fixture=True,
    )
    node_doc_cag = GraphStorageService.create_or_get_node(
        db_session,
        node_id="NODE:DOC:CAG_WATER_AUDIT",
        entity_type=GraphEntityType.EVIDENCE_DOCUMENT,
        canonical_id="DOC-CAG-2023-WATER",
        label="CAG Statutory Audit on Chennai Water Infrastructure 2023",
        source_phase="PHASE_6",
        is_test_fixture=True,
    )
    node_doc_pr = GraphStorageService.create_or_get_node(
        db_session,
        node_id="NODE:DOC:DEPT_PRESS_RELEASE",
        entity_type=GraphEntityType.EVIDENCE_DOCUMENT,
        canonical_id="DOC-NEWS-DAILY-MEDIA-2024",
        label="Daily News Media Report: Capacity Target Achieved",
        source_phase="PHASE_4",
        is_test_fixture=True,
    )

    # CAG Audit contradicts claim
    edge_cag_contra = GraphStorageService.add_evidence_edge(
        db_session,
        source_node_id=node_doc_cag.node_id,
        target_node_id=node_claim.node_id,
        relationship_type=GraphRelationshipType.CONTRADICTS,
        evidence_reference="CAG Audit Para 3.8: Average daily output measured at 92 MLD due to power trips",
        source_document_id="DOC-CAG-2023-WATER",
        source_document_hash="11223344556677889900aabbccddeeff11223344556677889900aabbccddeeff",
        matching_method=MatchingMethod.DIRECT_DOCUMENTARY,
        review_status=GraphReviewStatus.VERIFIED,
        valid_from="2023-01-01",
        is_test_fixture=True,
    )

    # Press release supports claim
    edge_pr_support = GraphStorageService.add_evidence_edge(
        db_session,
        source_node_id=node_doc_pr.node_id,
        target_node_id=node_claim.node_id,
        relationship_type=GraphRelationshipType.PROVIDES_EVIDENCE_FOR,
        evidence_reference="Press release claims full 150 MLD output reached on trial runs",
        source_document_id="DOC-NEWS-DAILY-MEDIA-2024",
        source_document_hash="99887766554433221100ffeeddccbbaa99887766554433221100ffeeddccbbaa",
        matching_method=MatchingMethod.DIRECT_DOCUMENTARY,
        review_status=GraphReviewStatus.PENDING_REVIEW,
        valid_from="2024-06-01",
        is_test_fixture=True,
    )

    db_session.commit()
    return {
        "scheme": node_scheme,
        "budget": node_budget,
        "claim": node_claim,
        "edge_statutory": edge_statutory,
        "edge_news_conflicting": edge_news_conflicting,
        "edge_stale": edge_stale,
        "edge_incomplete": edge_incomplete,
        "edge_cag_contra": edge_cag_contra,
        "edge_pr_support": edge_pr_support,
    }


def test_1_multi_factor_evidence_quality_scorecard(db_session, quality_fixture_graph):
    """
    Validates that assess_edge_evidence_quality evaluates all 9 documented factors,
    computes composite score, and includes documented inputs, interpretation, and limitations.
    """
    edge = quality_fixture_graph["edge_statutory"]
    scorecard = EvidenceQualityService.assess_edge_evidence_quality(edge)

    assert scorecard["edge_id"] == edge.edge_id
    assert scorecard["composite_score"] >= 0.85
    assert "HIGH_CREDIBILITY" in scorecard["interpretation"]

    # Verify all 9 documented factors exist in the breakdown
    factors = scorecard["factor_breakdown"]
    expected_factors = [
        "source_authenticity",
        "directness",
        "document_availability",
        "date_relevance",
        "geographic_relevance",
        "entity_match_quality",
        "source_completeness",
        "consistency",
        "review_status",
    ]
    for ef in expected_factors:
        assert ef in factors
        assert 0.0 <= factors[ef] <= 1.0

    # Verify documented inputs and limitations disclaimer
    assert "source_tier" in scorecard["documented_inputs"]
    assert "limitations" in scorecard
    assert "documentary provenance rigor" in scorecard["limitations"]


def test_2_source_reliability_tier_mapping():
    """
    Validates documented publisher tier taxonomy:
    Statutory audits vs executive filings vs journalistic media vs citizen reports.
    """
    # 1. Statutory audit (CAG)
    eval_cag = EvidenceQualityService.assess_source_reliability("DOC-CAG-PERFORMANCE-2022")
    assert eval_cag["source_tier"] == "STATUTORY_AUDIT_GAZETTE"
    assert eval_cag["authority_weight"] == 0.95

    # 2. Executive Departmental Record (G.O.)
    eval_go = EvidenceQualityService.assess_source_reliability("DOC-GO-MS-43-MAWS")
    assert eval_go["source_tier"] == "EXECUTIVE_DEPARTMENTAL_RECORD"
    assert eval_go["authority_weight"] == 0.85

    # 3. Journalistic Media (The Hindu / Dinamalar)
    eval_news = EvidenceQualityService.assess_source_reliability("DOC-NEWS-ARTICLE-DINAMALAR-2023")
    assert eval_news["source_tier"] == "VERIFIED_JOURNALISTIC_MEDIA"
    assert eval_news["authority_weight"] == 0.65

    # 4. Uncited / Informal Source
    eval_none = EvidenceQualityService.assess_source_reliability(None)
    assert eval_none["source_tier"] == "PROVISIONAL_CITIZEN_CLAIM"
    assert eval_none["authority_weight"] == 0.40


def test_3_conflicting_dates_detection(db_session, quality_fixture_graph):
    """
    Detects conflicting date timelines across records (2023 completion vs 2026 completion).
    """
    conflicts = EvidenceQualityService.detect_conflicts(
        session=db_session,
        node_id="NODE:SCHEME:DESAL_NEMMELI",
        persist_records=False,
    )
    date_conflicts = [c for c in conflicts if c.conflict_type == ConflictTypeEnum.CONFLICTING_DATES]
    assert len(date_conflicts) >= 1
    assert "divergence > 2 years" in date_conflicts[0].description


def test_4_incompatible_status_reports(db_session, quality_fixture_graph):
    """
    Detects incompatible status reports (SANCTIONED vs STALLED) for the same scheme.
    """
    conflicts = EvidenceQualityService.detect_conflicts(
        session=db_session,
        node_id="NODE:SCHEME:DESAL_NEMMELI",
        persist_records=False,
    )
    status_conflicts = [c for c in conflicts if c.conflict_type == ConflictTypeEnum.INCOMPATIBLE_STATUS]
    assert len(status_conflicts) >= 1
    assert status_conflicts[0].severity == ConflictSeverityEnum.CRITICAL
    assert "Incompatible status reports" in status_conflicts[0].description


def test_5_contradictory_claim_evidence_and_weight_comparison(db_session, quality_fixture_graph):
    """
    Validates detection of contradictory claim evidence:
    - CAG audit (contradicts) vs Press release (supports).
    - Evidentiary weight comparison properly ranks CAG audit higher despite the press release being newer!
    - Rule: Newer is NOT automatically correct.
    """
    conflicts = EvidenceQualityService.detect_conflicts(
        session=db_session,
        node_id="NODE:CLAIM:DESAL_OUTPUT_MET",
        persist_records=True,
    )
    claim_conflicts = [c for c in conflicts if c.conflict_type == ConflictTypeEnum.CONTRADICTORY_CLAIM_EVIDENCE]
    assert len(claim_conflicts) >= 1

    c = claim_conflicts[0]
    comparison = c.epistemic_weight_comparison
    assert "supporting_edge" in comparison
    assert "contradicting_edge" in comparison

    # Verify that CAG audit carries higher weight (0.95 tier)
    assert comparison["contradicting_edge"]["source_tier"] == "STATUTORY_AUDIT_GAZETTE"
    assert comparison["supporting_edge"]["source_tier"] == "VERIFIED_JOURNALISTIC_MEDIA"
    assert comparison["contradicting_edge"]["composite_score"] > comparison["supporting_edge"]["composite_score"]

    # Verify non-automatic "newest is correct" rule
    assert "Newer publication date does not automatically override statutory audit" in comparison["methodological_note"]


def test_6_stale_and_outdated_sources_detection(db_session, quality_fixture_graph):
    """
    Detects stale sources (e.g. 2015 feasibility report) and flags OUTDATED_DOCUMENT.
    """
    conflicts = EvidenceQualityService.detect_conflicts(
        session=db_session,
        node_id="NODE:SCHEME:DESAL_NEMMELI",
        persist_records=False,
    )
    stale_conflicts = [c for c in conflicts if c.conflict_type == ConflictTypeEnum.OUTDATED_DOCUMENT]
    assert len(stale_conflicts) >= 1
    assert "cites stale or outdated document" in stale_conflicts[0].description


def test_7_missing_source_documents_and_incomplete_provenance(db_session, quality_fixture_graph):
    """
    Detects edges with missing hashes and missing verbatim excerpts.
    """
    conflicts = EvidenceQualityService.detect_conflicts(
        session=db_session,
        node_id="NODE:SCHEME:DESAL_NEMMELI",
        persist_records=False,
    )
    incomplete_conflicts = [c for c in conflicts if c.conflict_type == ConflictTypeEnum.INCOMPLETE_PROVENANCE]
    assert len(incomplete_conflicts) >= 1
    assert any("missing SHA-256 hash" in ic.description for ic in incomplete_conflicts)


def test_8_evidence_completeness_assessment(db_session, quality_fixture_graph):
    """
    Assesses completeness of statutory evidence chain for an entity:
    Distinguishes completeness from quality scores or verification outcomes.
    """
    # 1. Scheme with funding edge
    comp_scheme = EvidenceQualityService.assess_evidence_completeness(
        db_session, "NODE:SCHEME:DESAL_NEMMELI"
    )
    assert comp_scheme["entity_type"] == "BUDGET_SCHEME"
    assert "BUDGET_FUNDING_RECORD" in comp_scheme["present_elements"]
    assert "MISSING_IMPLEMENTATION_RECORD" in comp_scheme["missing_elements"][0]
    assert comp_scheme["is_complete"] is False

    # 2. Incomplete civic issue without response
    node_isolated_issue = GraphStorageService.create_or_get_node(
        db_session,
        node_id="NODE:ISSUE:ISOLATED_DRAIN",
        entity_type=GraphEntityType.CIVIC_ISSUE,
        canonical_id="ISSUE-ISO-01",
        label="Isolated drain overflow complaint",
        source_phase="PHASE_7",
        is_test_fixture=True,
    )
    db_session.commit()

    comp_issue = EvidenceQualityService.assess_evidence_completeness(
        db_session, node_isolated_issue.node_id
    )
    assert comp_issue["is_complete"] is False
    assert len(comp_issue["missing_elements"]) == 2


def test_9_conflict_persistence_and_preservation(db_session, quality_fixture_graph):
    """
    Validates that detected conflicts are persistently recorded in CivicConflictRecord
    without deleting or suppressing the underlying conflicting evidence.
    """
    conflicts = EvidenceQualityService.detect_conflicts(
        db_session, node_id="NODE:CLAIM:DESAL_OUTPUT_MET", persist_records=True
    )
    db_session.commit()

    records_in_db = (
        db_session.query(CivicConflictRecord)
        .filter(CivicConflictRecord.primary_node_id == "NODE:CLAIM:DESAL_OUTPUT_MET")
        .all()
    )
    assert len(records_in_db) >= 1
    rec = records_in_db[0]
    assert rec.resolution_status == ConflictResolutionStatus.EXPLAINED_DIALECTIC
    assert rec.edge_a_id is not None
    assert rec.edge_b_id is not None

    # Underlying conflicting edges MUST remain in the database (never suppressed!)
    edge_a = db_session.query(CivicEvidenceEdge).filter(CivicEvidenceEdge.edge_id == rec.edge_a_id).first()
    edge_b = db_session.query(CivicEvidenceEdge).filter(CivicEvidenceEdge.edge_id == rec.edge_b_id).first()
    assert edge_a is not None
    assert edge_b is not None


def test_10_rest_api_quality_and_conflict_endpoints(db_session, quality_fixture_graph, monkeypatch):
    """
    Validates REST API endpoints:
    - GET /api/graph/conflicts
    - GET /api/graph/edges/<edge_id>/quality
    - GET /api/graph/nodes/<node_id>/completeness
    """
    import backend.api.graph as api_graph_module

    # Pre-extract primitive ID before client calls
    edge_id = quality_fixture_graph["edge_statutory"].edge_id

    # Prevent db.close() inside endpoints from closing db_session
    monkeypatch.setattr(db_session, "close", lambda: None)
    monkeypatch.setattr(api_graph_module, "SessionLocal", lambda: db_session)

    app = create_app()
    client = app.test_client()

    # 1. GET /api/graph/conflicts
    resp_conf = client.get("/api/graph/conflicts?node_id=NODE:CLAIM:DESAL_OUTPUT_MET")
    assert resp_conf.status_code == 200
    data_c = resp_conf.get_json()
    assert data_c["status"] == "success"
    assert "conflicts" in data_c["data"]
    assert len(data_c["data"]["conflicts"]) >= 1

    # 2. GET /api/graph/edges/<edge_id>/quality
    resp_q = client.get(f"/api/graph/edges/{edge_id}/quality")
    assert resp_q.status_code == 200
    data_q = resp_q.get_json()
    assert data_q["status"] == "success"
    assert "scorecard" in data_q["data"]
    assert data_q["data"]["scorecard"]["composite_score"] >= 0.85

    # 3. GET /api/graph/nodes/<node_id>/completeness
    resp_comp = client.get("/api/graph/nodes/NODE:SCHEME:DESAL_NEMMELI/completeness")
    assert resp_comp.status_code == 200
    data_comp = resp_comp.get_json()
    assert data_comp["status"] == "success"
    assert "completeness" in data_comp["data"]
    assert "present_elements" in data_comp["data"]["completeness"]
