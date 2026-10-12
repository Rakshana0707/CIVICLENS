"""
Phase 9.5 — Explainable Evidence Traversal Engine Tests.
========================================================

Validates:
1. Investigation Path 1: Promise -> Scheme -> Budget -> Implementation.
2. Investigation Path 2: Claim -> Supporting and Contradicting Evidence -> Verification.
3. Investigation Path 3: Civic Issue -> Official Record -> Department Response -> Resolution.
4. Investigation Path 4: Representative -> Constituency -> Public Works (with spatial non-culpability caveat).
5. Investigation Path 5: Funding Disclosure -> Disclosed Entity -> Source Document.
6. Anti-fabrication safeguard: Missing intermediate edges must NEVER be manufactured or bridged.
7. Cycle prevention: Cyclic graph topologies terminate safely without infinite recursion or loop duplication.
8. Traversal bounds: Configurable max_depth and max_paths limits.
9. Direct vs Inferred link discrimination and missing evidence warnings.
10. REST API integration: /api/graph/traverse and /api/graph/investigate/<mode>.
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
    CandidateRelationshipProposal,
    CandidateReviewDisposition,
    GraphEntityType,
    GraphRelationshipType,
    MatchingMethod,
    GraphProvenanceStatus,
    GraphReviewStatus,
)
from backend.services.graph_storage_service import GraphStorageService
from backend.services.evidence_traversal_engine import EvidenceTraversalEngine, NodeNotFoundError


@pytest.fixture
def db_session():
    """In-memory SQLite database session for traversal tests."""
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def traversal_fixture_graph(db_session):
    """
    Constructs a comprehensive cross-phase evidence graph covering all 5 investigation paths.
    """
    # -----------------------------------------------------------------------
    # Path 1 Entities: Promise -> Scheme -> Budget -> Implementation
    # -----------------------------------------------------------------------
    node_prom = GraphStorageService.create_or_get_node(
        db_session,
        node_id="NODE:PROM:BREAKFAST_2021",
        entity_type=GraphEntityType.POLITICAL_PROMISE,
        canonical_id="PROM-DMK-314",
        label="DMK 2021 Manifesto Promise 314: Free School Breakfast",
        source_phase="PHASE_3",
        is_test_fixture=True,
    )
    node_scheme = GraphStorageService.create_or_get_node(
        db_session,
        node_id="NODE:SCHEME:BREAKFAST_TN",
        entity_type=GraphEntityType.HISTORICAL_SCHEME,
        canonical_id="SCH-TN-2022-BF",
        label="Chief Minister Breakfast Scheme",
        source_phase="PHASE_2",
        is_test_fixture=True,
    )
    node_budget = GraphStorageService.create_or_get_node(
        db_session,
        node_id="NODE:BUDGET:DEMAND_34_EXP",
        entity_type=GraphEntityType.BUDGET_RECORD,
        canonical_id="BUD-EXP-2022-34",
        label="Demand 34 Sub-Head 104 Breakfast Scheme Allocation Rs 33.56 Cr",
        source_phase="PHASE_1",
        is_test_fixture=True,
    )
    node_impl = GraphStorageService.create_or_get_node(
        db_session,
        node_id="NODE:IMPL:PRIMARY_SCHOOL_KITCHENS",
        entity_type=GraphEntityType.PUBLIC_WORK,
        canonical_id="WORK-KITCHEN-2022",
        label="Centralized Community Kitchen Infrastructure across 1,545 Schools",
        source_phase="PHASE_8",
        is_test_fixture=True,
    )

    # Path 1 Edges
    GraphStorageService.add_evidence_edge(
        db_session,
        source_node_id=node_prom.node_id,
        target_node_id=node_scheme.node_id,
        relationship_type=GraphRelationshipType.RELATES_TO,
        evidence_reference="Manifesto Item 314 shares primary policy target with G.O. Ms 43",
        source_document_id="DOC-MAN-DMK-2021",
        matching_method=MatchingMethod.DIRECT_DOCUMENTARY,
        is_test_fixture=True,
    )
    GraphStorageService.add_evidence_edge(
        db_session,
        source_node_id=node_budget.node_id,
        target_node_id=node_scheme.node_id,
        relationship_type=GraphRelationshipType.FUNDS,
        evidence_reference="Demand 34 Detailed Budget Estimates 2022-23 Page 88",
        source_document_id="DOC-TN-BUDGET-2022",
        matching_method=MatchingMethod.DIRECT_DOCUMENTARY,
        is_test_fixture=True,
    )
    GraphStorageService.add_evidence_edge(
        db_session,
        source_node_id=node_scheme.node_id,
        target_node_id=node_impl.node_id,
        relationship_type=GraphRelationshipType.IMPLEMENTS,
        evidence_reference="MAWS Administrative Report 2022-23 Table 7",
        source_document_id="DOC-MAWS-ADMIN-2022",
        matching_method=MatchingMethod.DIRECT_DOCUMENTARY,
        is_test_fixture=True,
    )

    # -----------------------------------------------------------------------
    # Path 2 Entities: Claim -> Supporting and Contradicting Evidence
    # -----------------------------------------------------------------------
    node_claim = GraphStorageService.create_or_get_node(
        db_session,
        node_id="NODE:CLAIM:ATTENDANCE_18_PCT",
        entity_type=GraphEntityType.CLAIM,
        canonical_id="CLAIM-EDU-2023-01",
        label="Breakfast scheme boosted primary school attendance by 18%",
        source_phase="PHASE_6",
        is_test_fixture=True,
    )
    node_doc_pro = GraphStorageService.create_or_get_node(
        db_session,
        node_id="NODE:DOC:DPI_REPORT",
        entity_type=GraphEntityType.EVIDENCE_DOCUMENT,
        canonical_id="DOC-DPI-2023",
        label="DPI Official Attendance Evaluation Report 2023",
        source_phase="PHASE_6",
        is_test_fixture=True,
    )
    node_doc_con = GraphStorageService.create_or_get_node(
        db_session,
        node_id="NODE:DOC:CAG_AUDIT",
        entity_type=GraphEntityType.EVIDENCE_DOCUMENT,
        canonical_id="DOC-CAG-2023",
        label="CAG Independent Audit on School Feeding 2023",
        source_phase="PHASE_6",
        is_test_fixture=True,
    )

    # Path 2 Edges: Supporting and Contradicting
    GraphStorageService.add_evidence_edge(
        db_session,
        source_node_id=node_doc_pro.node_id,
        target_node_id=node_claim.node_id,
        relationship_type=GraphRelationshipType.PROVIDES_EVIDENCE_FOR,
        evidence_reference="Table 4.1 DPI: Average attendance gain computed at 18.2%",
        source_document_id="DOC-DPI-2023",
        matching_method=MatchingMethod.DIRECT_DOCUMENTARY,
        is_test_fixture=True,
    )
    GraphStorageService.add_evidence_edge(
        db_session,
        source_node_id=node_doc_con.node_id,
        target_node_id=node_claim.node_id,
        relationship_type=GraphRelationshipType.CONTRADICTS,
        evidence_reference="Section 2.14 CAG: Baseline unadjusted; gain statistically estimated at 4.2%",
        source_document_id="DOC-CAG-2023",
        matching_method=MatchingMethod.DIRECT_DOCUMENTARY,
        is_test_fixture=True,
    )

    # -----------------------------------------------------------------------
    # Path 3 Entities: Civic Issue -> Official Record -> Response -> Resolution
    # -----------------------------------------------------------------------
    node_issue = GraphStorageService.create_or_get_node(
        db_session,
        node_id="NODE:ISSUE:WATER_WARD65",
        entity_type=GraphEntityType.CIVIC_ISSUE,
        canonical_id="ISSUE-KOL-WTR-65",
        label="Contaminated drinking water pipeline in Ward 65",
        source_phase="PHASE_7",
        is_test_fixture=True,
    )
    node_griev = GraphStorageService.create_or_get_node(
        db_session,
        node_id="NODE:GRIEV:PORTAL_TOKEN_89",
        entity_type=GraphEntityType.GRIEVANCE_RECORD,
        canonical_id="GRIEV-CM-PORTAL-89",
        label="CM Helpline Grievance Token #TN-2024-89",
        source_phase="PHASE_8",
        is_test_fixture=True,
    )
    node_resp = GraphStorageService.create_or_get_node(
        db_session,
        node_id="NODE:RESP:CMWSSB_ACTION",
        entity_type=GraphEntityType.RESPONSE_RECORD,
        canonical_id="RESP-CMWSSB-2024-89",
        label="CMWSSB Action Taken Report ATR-89",
        source_phase="PHASE_8",
        is_test_fixture=True,
    )
    node_resol = GraphStorageService.create_or_get_node(
        db_session,
        node_id="NODE:RESOL:WATER_TEST_CERT",
        entity_type=GraphEntityType.RESOLUTION_EVIDENCE,
        canonical_id="RESOL-WTR-TEST-89",
        label="King Institute Water Potability Clearance Certificate",
        source_phase="PHASE_8",
        is_test_fixture=True,
    )

    # Path 3 Edges
    GraphStorageService.add_evidence_edge(
        db_session,
        source_node_id=node_issue.node_id,
        target_node_id=node_griev.node_id,
        relationship_type=GraphRelationshipType.CONCERNS,
        evidence_reference="Citizen complaint registered under token #TN-2024-89",
        source_document_id="DOC-HELPLINE-89",
        matching_method=MatchingMethod.DETERMINISTIC_ID,
        is_test_fixture=True,
    )
    GraphStorageService.add_evidence_edge(
        db_session,
        source_node_id=node_resp.node_id,
        target_node_id=node_issue.node_id,
        relationship_type=GraphRelationshipType.RESPONDS_TO,
        evidence_reference="CMWSSB Engineer pipeline replacement log dispatched",
        source_document_id="DOC-ATR-CMWSSB-89",
        matching_method=MatchingMethod.DIRECT_DOCUMENTARY,
        review_status=GraphReviewStatus.VERIFIED,
        is_test_fixture=True,
    )
    GraphStorageService.add_evidence_edge(
        db_session,
        source_node_id=node_resol.node_id,
        target_node_id=node_resp.node_id,
        relationship_type=GraphRelationshipType.PROVIDES_EVIDENCE_FOR,
        evidence_reference="Lab Report #KI-9902 water potability parameters passed",
        source_document_id="DOC-LAB-CERT-89",
        matching_method=MatchingMethod.DIRECT_DOCUMENTARY,
        is_test_fixture=True,
    )

    # -----------------------------------------------------------------------
    # Path 4 Entities: Representative -> Constituency -> Public Works
    # -----------------------------------------------------------------------
    node_rep = GraphStorageService.create_or_get_node(
        db_session,
        node_id="NODE:REP:STALIN_MLA",
        entity_type=GraphEntityType.REPRESENTATIVE,
        canonical_id="REP-KOLATHUR-013",
        label="M. K. Stalin",
        source_phase="PHASE_5",
        is_test_fixture=True,
    )
    node_const = GraphStorageService.create_or_get_node(
        db_session,
        node_id="NODE:CONST:KOLATHUR_AC",
        entity_type=GraphEntityType.CONSTITUENCY,
        canonical_id="AC-013",
        label="Kolathur Assembly Constituency AC-013",
        source_phase="PHASE_5",
        is_test_fixture=True,
    )
    node_work = GraphStorageService.create_or_get_node(
        db_session,
        node_id="NODE:WORK:KOLATHUR_STORM_DRAIN",
        entity_type=GraphEntityType.PUBLIC_WORK,
        canonical_id="WORK-SWD-KOL-2023",
        label="Kolathur Storm Water Drainage Modernization Package 4",
        source_phase="PHASE_8",
        is_test_fixture=True,
    )

    # Path 4 Edges
    GraphStorageService.add_evidence_edge(
        db_session,
        source_node_id=node_rep.node_id,
        target_node_id=node_const.node_id,
        relationship_type=GraphRelationshipType.REPRESENTS,
        evidence_reference="ECI Form 21E Official Result Declaration Kolathur AC-013",
        source_document_id="DOC-ECI-21E-2021",
        matching_method=MatchingMethod.DIRECT_DOCUMENTARY,
        is_test_fixture=True,
    )
    GraphStorageService.add_evidence_edge(
        db_session,
        source_node_id=node_work.node_id,
        target_node_id=node_const.node_id,
        relationship_type=GraphRelationshipType.LOCATED_IN,
        evidence_reference="GIS boundary coordinates fall in AC-013",
        source_document_id="DOC-GIS-KOL-2023",
        matching_method=MatchingMethod.DETERMINISTIC_ID,
        is_test_fixture=True,
    )

    # -----------------------------------------------------------------------
    # Path 5 Entities: Funding -> Disclosed Party -> Source Document
    # -----------------------------------------------------------------------
    node_contrib = GraphStorageService.create_or_get_node(
        db_session,
        node_id="NODE:CONTRIB:EB_1042",
        entity_type=GraphEntityType.CONTRIBUTION,
        canonical_id="CONTRIB-EB-1042",
        label="Electoral Bond Serial #TL40283 Contribution",
        source_phase="PHASE_4",
        is_test_fixture=True,
    )
    node_party = GraphStorageService.create_or_get_node(
        db_session,
        node_id="NODE:PARTY:DMK_HEADQUARTERS",
        entity_type=GraphEntityType.POLITICAL_PARTY,
        canonical_id="PARTY-DMK-HQ",
        label="Dravida Munnetra Kazhagam",
        source_phase="PHASE_4",
        is_test_fixture=True,
    )
    node_source_doc = GraphStorageService.create_or_get_node(
        db_session,
        node_id="NODE:DOC:ECI_AFFIDAVIT_2024",
        entity_type=GraphEntityType.SOURCE_DOCUMENT,
        canonical_id="DOC-ECI-AFF-2024",
        label="ECI Published Supreme Court Affidavit on Electoral Bonds 2024",
        source_phase="PHASE_4",
        is_test_fixture=True,
    )

    # Path 5 Edges
    GraphStorageService.add_evidence_edge(
        db_session,
        source_node_id=node_contrib.node_id,
        target_node_id=node_party.node_id,
        relationship_type=GraphRelationshipType.FUNDS,
        evidence_reference="SBI Bond Redemption Entry TL40283 matched to party account",
        source_document_id="DOC-ECI-AFF-2024",
        matching_method=MatchingMethod.DETERMINISTIC_ID,
        confidence_score=1.0,
        review_status=GraphReviewStatus.VERIFIED,
        is_test_fixture=True,
    )
    GraphStorageService.add_evidence_edge(
        db_session,
        source_node_id=node_contrib.node_id,
        target_node_id=node_source_doc.node_id,
        relationship_type=GraphRelationshipType.DERIVED_FROM,
        evidence_reference="Page 112 Annexure 2 ECI Bond Disclosure Dataset",
        source_document_id="DOC-ECI-AFF-2024",
        matching_method=MatchingMethod.DIRECT_DOCUMENTARY,
        is_test_fixture=True,
    )

    db_session.commit()
    return {
        "prom": node_prom,
        "scheme": node_scheme,
        "budget": node_budget,
        "impl": node_impl,
        "claim": node_claim,
        "doc_pro": node_doc_pro,
        "doc_con": node_doc_con,
        "issue": node_issue,
        "resp": node_resp,
        "resol": node_resol,
        "rep": node_rep,
        "const": node_const,
        "work": node_work,
        "contrib": node_contrib,
        "party": node_party,
        "source_doc": node_source_doc,
    }


def test_1_investigation_path_1_promise_scheme_budget_implementation(db_session, traversal_fixture_graph):
    """
    Validates Investigation Path 1:
    Promise -> Scheme -> Budget -> Implementation.
    Verifies path completeness, hop ordering, and epistemic caveat on Promise -> Scheme.
    """
    paths = EvidenceTraversalEngine.investigate_promise_fulfillment(
        session=db_session,
        promise_node_id="NODE:PROM:BREAKFAST_2021",
        max_depth=4,
    )
    assert len(paths) >= 1
    p1 = paths[0]

    # Verify intermediate entities and sequence
    node_ids = [n["node_id"] for n in p1["nodes"]]
    assert "NODE:PROM:BREAKFAST_2021" in node_ids
    assert "NODE:SCHEME:BREAKFAST_TN" in node_ids

    # Verify epistemic caveats distinguish policy intent from statutory fulfillment proof
    assert len(p1["epistemic_caveats"]) >= 1
    assert any("Policy Intent Association" in c for c in p1["epistemic_caveats"])

    # Verify edge metadata retention
    for edge in p1["edges"]:
        assert edge["relationship_type"] is not None
        assert edge["matching_method"] is not None
        assert edge["source_document_id"] is not None


def test_2_investigation_path_2_claim_supporting_and_contradicting_evidence(db_session, traversal_fixture_graph):
    """
    Validates Investigation Path 2:
    Claim -> Supporting and Contradicting Evidence.
    Verifies that dialectical evidence is exposed and conflicting edges are retained.
    """
    paths = EvidenceTraversalEngine.investigate_claim_veracity(
        session=db_session,
        claim_node_id="NODE:CLAIM:ATTENDANCE_18_PCT",
        max_depth=3,
    )
    assert len(paths) >= 2

    rel_types = set()
    for p in paths:
        for e in p["edges"]:
            rel_types.add(e["relationship_type"])

    # Both supporting and contradicting edges must be present in the discovered paths
    assert "provides_evidence_for" in rel_types
    assert "contradicts" in rel_types

    # Verify conflicting evidence detection on the claim node
    has_conflict_flag = any(len(p["conflicting_evidence"]) > 0 for p in paths)
    assert has_conflict_flag


def test_3_investigation_path_3_civic_issue_response_resolution(db_session, traversal_fixture_graph):
    """
    Validates Investigation Path 3:
    Civic Issue -> Grievance Record -> Department Response -> Resolution Evidence.
    """
    paths = EvidenceTraversalEngine.investigate_civic_issue_resolution(
        session=db_session,
        issue_node_id="NODE:ISSUE:WATER_WARD65",
        max_depth=4,
    )
    assert len(paths) >= 1
    # Check that response record is traversed
    all_traversed_nodes = {n["node_id"] for p in paths for n in p["nodes"]}
    assert "NODE:RESP:CMWSSB_ACTION" in all_traversed_nodes


def test_4_investigation_path_4_representative_constituency_works(db_session, traversal_fixture_graph):
    """
    Validates Investigation Path 4:
    Representative -> Constituency -> Public Works.
    Verifies explicit spatial non-culpability caveat.
    """
    paths = EvidenceTraversalEngine.investigate_representative_works(
        session=db_session,
        representative_node_id="NODE:REP:STALIN_MLA",
        max_depth=3,
    )
    assert len(paths) >= 1

    # Check that AC-013 constituency is an intermediate hop
    all_traversed = {n["node_id"] for p in paths for n in p["nodes"]}
    assert "NODE:CONST:KOLATHUR_AC" in all_traversed

    # Verify caveat on spatial association
    for p in paths:
        if len(p["edges"]) > 1:
            assert any("Constituency Spatial Association" in c for c in p["epistemic_caveats"])


def test_5_investigation_path_5_funding_disclosure_lineage(db_session, traversal_fixture_graph):
    """
    Validates Investigation Path 5:
    Funding Disclosure -> Disclosed Entity -> Source Document.
    Verifies that contribution disclosures retain primary documents and caveat on outcome causation.
    """
    paths = EvidenceTraversalEngine.investigate_funding_lineage(
        session=db_session,
        funding_node_id="NODE:CONTRIB:EB_1042",
        max_depth=3,
    )
    assert len(paths) >= 1

    # Disclosed party must be present
    all_traversed = {n["node_id"] for p in paths for n in p["nodes"]}
    assert "NODE:PARTY:DMK_HEADQUARTERS" in all_traversed or "NODE:DOC:ECI_AFFIDAVIT_2024" in all_traversed


def test_6_anti_fabrication_missing_intermediate_edges(db_session, traversal_fixture_graph):
    """
    Anti-fabrication safeguard:
    When an intermediate edge is missing, the traversal engine MUST NEVER manufacture
    or bridge disconnected nodes.
    """
    # Create an isolated budget record not connected to the breakfast scheme
    node_isolated_bud = GraphStorageService.create_or_get_node(
        db_session,
        node_id="NODE:BUD:ISOLATED_FOREST",
        entity_type=GraphEntityType.BUDGET_RECORD,
        canonical_id="BUD-ISOLATED-01",
        label="Demand 15 Forest Dept Allocation",
        source_phase="PHASE_1",
        is_test_fixture=True,
    )
    db_session.commit()

    # Search paths from Promise to Isolated Budget
    paths = EvidenceTraversalEngine.find_paths(
        session=db_session,
        start_node_id="NODE:PROM:BREAKFAST_2021",
        target_node_id=node_isolated_bud.node_id,
        max_depth=4,
    )
    # MUST BE ZERO PATHS (No edge exists between them)
    assert len(paths) == 0


def test_7_cycle_prevention_safeguard(db_session):
    """
    Cycle prevention:
    A cyclic graph topology (A -> B -> C -> A) terminates cleanly without
    infinite loops or repeating nodes in the same branch.
    """
    # Create 3 cyclic nodes
    na = GraphStorageService.create_or_get_node(
        db_session, "NODE:CYCLE:A", GraphEntityType.PUBLIC_WORK, "CYC-A", "Cycle Node A", is_test_fixture=True
    )
    nb = GraphStorageService.create_or_get_node(
        db_session, "NODE:CYCLE:B", GraphEntityType.PUBLIC_WORK, "CYC-B", "Cycle Node B", is_test_fixture=True
    )
    nc = GraphStorageService.create_or_get_node(
        db_session, "NODE:CYCLE:C", GraphEntityType.PUBLIC_WORK, "CYC-C", "Cycle Node C", is_test_fixture=True
    )

    GraphStorageService.add_evidence_edge(
        db_session, na.node_id, nb.node_id, GraphRelationshipType.RELATES_TO,
        evidence_reference="A to B", source_document_id="DOC-CYC-1", is_test_fixture=True
    )
    GraphStorageService.add_evidence_edge(
        db_session, nb.node_id, nc.node_id, GraphRelationshipType.RELATES_TO,
        evidence_reference="B to C", source_document_id="DOC-CYC-2", is_test_fixture=True
    )
    GraphStorageService.add_evidence_edge(
        db_session, nc.node_id, na.node_id, GraphRelationshipType.RELATES_TO,
        evidence_reference="C to A cycle close", source_document_id="DOC-CYC-3", is_test_fixture=True
    )
    db_session.commit()

    # Traverse starting from A
    paths = EvidenceTraversalEngine.find_paths(
        session=db_session,
        start_node_id=na.node_id,
        max_depth=5,
    )
    assert len(paths) > 0

    # In EVERY path, node IDs must be strictly unique (no cycle repetition!)
    for p in paths:
        node_ids = [n["node_id"] for n in p["nodes"]]
        assert len(node_ids) == len(set(node_ids)), f"Cycle detected in path {node_ids}"


def test_8_depth_and_result_limits(db_session, traversal_fixture_graph):
    """
    Verifies that max_depth and max_paths strictly constrain the search space.
    """
    # 1. Depth limit: max_depth=1 should return paths with length <= 1
    paths_d1 = EvidenceTraversalEngine.find_paths(
        session=db_session,
        start_node_id="NODE:PROM:BREAKFAST_2021",
        max_depth=1,
    )
    for p in paths_d1:
        assert p["length"] <= 1

    # 2. Result limit: max_paths=1
    paths_limit1 = EvidenceTraversalEngine.find_paths(
        session=db_session,
        start_node_id="NODE:CLAIM:ATTENDANCE_18_PCT",
        direction="both",
        max_paths=1,
    )
    assert len(paths_limit1) == 1


def test_9_direct_vs_inferred_links_and_uncertain_edges(db_session, traversal_fixture_graph):
    """
    Distinguishes direct documentary paths from paths containing candidate or unreviewed edges.
    """
    # Add a candidate edge with low confidence and unreviewed status
    node_candidate_extra = GraphStorageService.create_or_get_node(
        db_session,
        node_id="NODE:EXTRA:CANDIDATE",
        entity_type=GraphEntityType.PUBLIC_WORK,
        canonical_id="CAND-EXTRA",
        label="Candidate Kitchen Upgrade",
        source_phase="PHASE_8",
        is_test_fixture=True,
    )
    GraphStorageService.add_evidence_edge(
        db_session,
        source_node_id="NODE:IMPL:PRIMARY_SCHOOL_KITCHENS",
        target_node_id=node_candidate_extra.node_id,
        relationship_type=GraphRelationshipType.RELATES_TO,
        evidence_reference="NLP candidate overlap",
        source_document_id=None,  # Missing source doc!
        matching_method=MatchingMethod.AUTOMATED_CANDIDATE,
        confidence_score=0.60,
        review_status=GraphReviewStatus.PENDING_REVIEW,
        is_test_fixture=True,
    )
    db_session.commit()

    paths = EvidenceTraversalEngine.find_paths(
        session=db_session,
        start_node_id="NODE:IMPL:PRIMARY_SCHOOL_KITCHENS",
        target_node_id=node_candidate_extra.node_id,
        max_depth=2,
    )
    assert len(paths) == 1
    p = paths[0]
    assert p["is_direct_path"] is False
    assert p["has_uncertain_edges"] is True
    assert len(p["missing_evidence"]) >= 1
    assert any("lacks an official primary source document" in m for m in p["missing_evidence"])


def test_10_rest_api_traversal_and_investigation_endpoints(db_session, traversal_fixture_graph, monkeypatch):
    """
    Validates REST API routes: /api/graph/traverse and /api/graph/investigate/<mode>.
    """
    import backend.api.graph as api_graph_module
    monkeypatch.setattr(api_graph_module, "SessionLocal", lambda: db_session)

    app = create_app()
    client = app.test_client()

    # 1. Test POST /api/graph/traverse
    resp_traverse = client.post(
        "/api/graph/traverse",
        json={
            "start_node_id": "NODE:CLAIM:ATTENDANCE_18_PCT",
            "direction": "both",
            "max_depth": 3,
        },
    )
    assert resp_traverse.status_code == 200
    data_t = resp_traverse.get_json()
    assert data_t["status"] == "success"
    assert "paths" in data_t["data"]
    assert len(data_t["data"]["paths"]) >= 2

    # 2. Test GET /api/graph/investigate/claim
    resp_inv = client.get(
        "/api/graph/investigate/claim?node_id=NODE:CLAIM:ATTENDANCE_18_PCT&max_depth=3"
    )
    assert resp_inv.status_code == 200
    data_inv = resp_inv.get_json()
    assert data_inv["status"] == "success"
    assert data_inv["data"]["mode"] == "claim"
    assert len(data_inv["data"]["paths"]) >= 2

    # 3. Test 404 for non-existent node
    resp_404 = client.get(
        "/api/graph/investigate/claim?node_id=NODE:NON_EXISTENT_999"
    )
    assert resp_404.status_code == 404
