"""
Phase 9.7 — Unified Civic Search and Evidence Graph API Tests.
==============================================================

Validates:
1.  Operation 1:  Searching canonical entities across Phases 1–8 with pagination & filtering.
2.  Operation 2:  Retrieving an entity node, canonical registry profile, and source mappings.
3.  Operation 3:  Retrieving directly connected neighbor entities and evidence relationships.
4.  Operation 4:  Traversing evidence paths and structured investigation walk templates.
5.  Operation 5:  Filtering evidence edges by relationship type, source document, and review status.
6.  Operation 6:  Retrieving evidence and 9-factor scorecard for an individual edge.
7.  Operation 7:  Listing unresolved relationship candidates discovered by discovery engine.
8.  Operation 8:  Retrieving contradictory, disputed, and dialectical tension records.
9.  Operation 9:  Retrieving graph provenance, review decisions, and immutable audit history.
10. Operation 10: Viewing relevant records from original phase modules without data duplication.
11. Security & Privacy: Automated PII scrubbing and internal server path sanitization.
12. Authorization: RBAC enforcement on review mutation actions (confirm, reject, defer).
"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.api.app import create_app
from backend.database.base_class import Base
from backend.models.entity_registry import (
    CanonicalEntity,
    EntityAlias,
    EntityAuditRecord,
    SourceIdentifierMapping,
    RegistryEntityType,
    EntityLifecycleStatus,
    AliasTypeEnum,
    EntityOperationType,
)
from backend.models.graph import (
    CivicGraphNode,
    CivicEvidenceEdge,
    CandidateRelationshipProposal,
    CandidateReviewDisposition,
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
from datetime import datetime, timezone
from backend.models.civic_issue import CivicIssue, CivicIssueStatus, IssueCategory, IssueCategoryEnum
from backend.models.claim import Claim, ClaimCategory, ClaimStatus, VerificationVerdict
from backend.models.promise import PoliticalPromise
from backend.models.manifesto import Manifesto
from backend.services.graph_storage_service import GraphStorageService
from backend.services.relationship_discovery_engine import RelationshipDiscoveryEngine
import backend.api.graph as api_graph_module


@pytest.fixture
def api_test_db():
    """In-memory SQLite database session for Phase 9.7 API testing."""
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine, expire_on_commit=False)
    session = Session()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def seed_graph_dataset(api_test_db):
    """Seed comprehensive cross-phase nodes, edges, proposals, conflicts, and records."""
    # 1. Canonical Entity & Mappings
    canonical_dept = CanonicalEntity(
        entity_id="DEPT-MAWS-TN",
        canonical_name_en="Municipal Administration and Water Supply Department",
        canonical_name_ta="நகராட்சி நிர்வாகம் மற்றும் குடிநீர் வழங்கல் துறை",
        normalized_name="municipal administration and water supply department",
        entity_type=RegistryEntityType.GOVERNMENT_DEPARTMENT,
        status=EntityLifecycleStatus.ACTIVE,
    )
    api_test_db.add(canonical_dept)

    alias_maws = EntityAlias(
        alias_id="ALIAS-MAWS-01",
        entity_id="DEPT-MAWS-TN",
        alias_name="MAWS",
        normalized_alias="maws",
        alias_type=AliasTypeEnum.ACRONYM,
        language="en",
        source_reference="official_portal",
    )
    api_test_db.add(alias_maws)

    src_map = SourceIdentifierMapping(
        mapping_id="MAP-MAWS-01",
        entity_id="DEPT-MAWS-TN",
        source_system="TNBudgetPortal",
        source_record_id="DEMAND_34",
        source_record_name="Municipal Administration & Water Supply",
    )
    api_test_db.add(src_map)

    # 2. Graph Nodes across Phases
    node_dept = GraphStorageService.create_or_get_node(
        api_test_db,
        node_id="NODE:DEPT:MAWS",
        entity_type=GraphEntityType.GOVERNMENT_DEPARTMENT,
        canonical_id="DEPT-MAWS-TN",
        label="Municipal Administration and Water Supply Department",
        source_phase="PHASE_1",
        is_test_fixture=True,
    )

    node_scheme = GraphStorageService.create_or_get_node(
        api_test_db,
        node_id="NODE:SCHEME:NEMMELI",
        entity_type=GraphEntityType.BUDGET_SCHEME,
        canonical_id="SCHEME-NEMMELI-150MLD",
        label="Nemmeli 150 MLD Desalination Augmentation Scheme",
        source_phase="PHASE_2",
        attributes={"scheme_id": 101, "budget_crores": 1516.0},
        is_test_fixture=True,
    )

    node_promise = GraphStorageService.create_or_get_node(
        api_test_db,
        node_id="NODE:PROMISE:WATER_SUPPLY",
        entity_type=GraphEntityType.POLITICAL_PROMISE,
        canonical_id="PROM-DMK-2021-WATER",
        label="Ensure 24x7 treated water supply to South Chennai through modern desalination",
        source_phase="PHASE_3",
        is_test_fixture=True,
    )

    node_claim = GraphStorageService.create_or_get_node(
        api_test_db,
        node_id="NODE:CLAIM:DESAL_OUTPUT",
        entity_type=GraphEntityType.CLAIM,
        canonical_id="CLAIM-DESAL-OUTPUT-2024",
        label="Nemmeli desalination plant achieves steady 150 MLD production output",
        source_phase="PHASE_6",
        is_test_fixture=True,
    )

    node_issue = GraphStorageService.create_or_get_node(
        api_test_db,
        node_id="NODE:ISSUE:DRAIN_OVERFLOW",
        entity_type=GraphEntityType.CIVIC_ISSUE,
        canonical_id="ISSUE-GCC-2024-4401",
        label="Stormwater drain overflow in Velachery Ward 177",
        source_phase="PHASE_7",
        attributes={"zone": "Adyar", "reporter_phone": "+91-9840123456", "file_path": "C:\\CIVCLENS\\logs\\issue_4401.jsonl"},
        is_test_fixture=True,
    )

    # 3. Evidence Edges
    edge_implements = GraphStorageService.add_evidence_edge(
        api_test_db,
        source_node_id=node_dept.node_id,
        target_node_id=node_scheme.node_id,
        relationship_type=GraphRelationshipType.IMPLEMENTS,
        evidence_reference="MAWS Policy Note 2023-24 Page 42 Section 3.2 lists Nemmeli plant augmentation",
        source_document_id="DOC-GO-TN-MAWS-2023-42",
        source_document_url="https://tn.gov.in/maws/policy-note-2023",
        source_document_hash="aa11bb22cc33dd44ee55ff66aa11bb22cc33dd44ee55ff66aa11bb22cc33dd44",
        matching_method=MatchingMethod.DIRECT_DOCUMENTARY,
        confidence_score=0.96,
        review_status=GraphReviewStatus.VERIFIED,
        valid_from="2023-04-01",
        is_test_fixture=True,
    )

    edge_relates = GraphStorageService.add_evidence_edge(
        api_test_db,
        source_node_id=node_promise.node_id,
        target_node_id=node_scheme.node_id,
        relationship_type=GraphRelationshipType.RELATES_TO,
        evidence_reference="Manifesto Promise 144 relates to drinking water infrastructure in Chennai",
        source_document_id="DOC-MANIFESTO-DMK-2021",
        matching_method=MatchingMethod.AUTOMATED_CANDIDATE,
        confidence_score=0.82,
        review_status=GraphReviewStatus.PENDING_REVIEW,
        valid_from="2021-05-01",
        is_test_fixture=True,
    )

    # Disputed Edge
    edge_disputed = GraphStorageService.add_evidence_edge(
        api_test_db,
        source_node_id=node_claim.node_id,
        target_node_id=node_scheme.node_id,
        relationship_type=GraphRelationshipType.PROVIDES_EVIDENCE_FOR,
        evidence_reference="Preliminary contractor statement disputed by independent scrutiny",
        source_document_id="DOC-CONTRACTOR-NOTE-2024",
        matching_method=MatchingMethod.AUTOMATED_CANDIDATE,
        confidence_score=0.55,
        review_status=GraphReviewStatus.PENDING_REVIEW,
        is_test_fixture=True,
    )
    edge_disputed.provenance_status = GraphProvenanceStatus.DISPUTED

    # 4. Candidate Proposal (Unresolved)
    proposal_unresolved = CandidateRelationshipProposal(
        proposal_id="PROP-CANDIDATE-001",
        source_node_id=node_scheme.node_id,
        target_node_id=node_issue.node_id,
        relationship_type=GraphRelationshipType.RESPONDS_TO,
        evidence_supporting_candidate="Scheme augmentation addresses localized distribution complaints",
        matching_method=MatchingMethod.AUTOMATED_CANDIDATE,
        confidence_score=0.74,
        source_document_id="DOC-SURVEY-2024",
        review_status=CandidateReviewDisposition.PENDING_REVIEW,
        is_test_fixture=True,
    )
    api_test_db.add(proposal_unresolved)

    # 5. Persistent Civic Conflict Record
    conflict_rec = CivicConflictRecord(
        conflict_id="CONF-DESAL-OUTPUT-01",
        conflict_type=ConflictTypeEnum.CONTRADICTORY_CLAIM_EVIDENCE,
        severity=ConflictSeverityEnum.HIGH,
        primary_node_id=node_claim.node_id,
        description="CAG audit para 3.8 contradicts departmental press release on effective daily output",
        epistemic_weight_comparison={
            "statutory_weight": 0.95,
            "media_weight": 0.65,
            "rule": "Newer press release does not automatically invalidate statutory audit",
        },
        resolution_status=ConflictResolutionStatus.EXPLAINED_DIALECTIC,
        is_test_fixture=True,
    )
    api_test_db.add(conflict_rec)

    # 6. Original Phase Records for Cross-Phase Resolution
    manifesto = Manifesto(
        manifesto_id="MAN-DMK-2021",
        party="DMK",
        election_year=2021,
    )
    api_test_db.add(manifesto)
    api_test_db.flush()

    promise_rec = PoliticalPromise(
        promise_id="PROM-DMK-2021-WATER",
        manifesto_id="MAN-DMK-2021",
        original_text="Ensure 24x7 treated water supply to South Chennai through modern desalination",
        normalized_text="ensure 24x7 treated water supply to south chennai through modern desalination",
        classification="water_infrastructure",
        metadata_json={"status": "IN_PROGRESS"},
    )
    api_test_db.add(promise_rec)

    cat = IssueCategory(
        code=IssueCategoryEnum.DRAINAGE,
        name_en="Drainage and Storm Water",
        name_ta="வடிகால்",
    )
    api_test_db.add(cat)
    api_test_db.flush()

    issue_rec = CivicIssue(
        issue_code="ISSUE-GCC-2024-4401",
        title="Stormwater drain overflow in Velachery Ward 177",
        description="Drain blockage near Door No. 14, contact Thiru K. Murugesan at +91-9840123456 or citizen@example.com for access.",
        category_id=cat.id,
        status=CivicIssueStatus.OPEN,
        reported_date=datetime.now(timezone.utc),
    )
    api_test_db.add(issue_rec)

    claim_rec = Claim(
        claim_id="CLAIM-DESAL-OUTPUT-2024",
        original_text="Nemmeli desalination plant achieves steady 150 MLD production output",
        normalized_text="nemmeli desalination plant achieves steady 150 mld production output",
        claim_category=ClaimCategory.PUBLIC_INFRASTRUCTURE,
        status=ClaimStatus.VERIFIED,
        speaker_name="Department Press Briefing",
    )
    api_test_db.add(claim_rec)

    api_test_db.commit()

    return {
        "dept_node": node_dept,
        "scheme_node": node_scheme,
        "promise_node": node_promise,
        "claim_node": node_claim,
        "issue_node": node_issue,
        "edge_implements": edge_implements,
        "edge_relates": edge_relates,
        "edge_disputed": edge_disputed,
        "proposal_unresolved": proposal_unresolved,
        "conflict": conflict_rec,
    }


@pytest.fixture
def test_client(api_test_db, monkeypatch):
    """Configures Flask test client with SessionLocal pointing to our in-memory SQLite DB."""
    # Prevent db.close() in request handler from closing the shared api_test_db
    monkeypatch.setattr(api_test_db, "close", lambda: None)
    monkeypatch.setattr(api_graph_module, "SessionLocal", lambda: api_test_db)

    app = create_app()
    return app.test_client()


# ===========================================================================
# 1. Searching Canonical Entities across Phases 1–8
# ===========================================================================
def test_1_search_canonical_entities_with_filters_and_pagination(test_client, seed_graph_dataset):
    """Validates Operation 1: Search canonical entities by query, type, phase, with pagination."""
    # 1. Search by text query
    resp = test_client.get("/api/graph/entities/search?q=Nemmeli&limit=10&offset=0")
    assert resp.status_code == 200
    data = resp.get_json()["data"]
    assert data["total"] >= 1
    assert any("Nemmeli" in item["label"] for item in data["items"])
    assert data["limit"] == 10
    assert data["offset"] == 0

    # 2. Filter by entity_type
    resp_type = test_client.get("/api/graph/entities/search?entity_type=GOVERNMENT_DEPARTMENT")
    assert resp_type.status_code == 200
    data_t = resp_type.get_json()["data"]
    assert any(item["entity_type"] == "GOVERNMENT_DEPARTMENT" for item in data_t["items"])

    # 3. Filter by source_phase
    resp_phase = test_client.get("/api/graph/entities/search?source_phase=PHASE_3")
    assert resp_phase.status_code == 200
    data_p = resp_phase.get_json()["data"]
    assert any(item["source_phase"] == "PHASE_3" for item in data_p["items"])


# ===========================================================================
# 2. Retrieving an Entity and its Source Records
# ===========================================================================
def test_2_retrieve_entity_profile_and_source_mappings(test_client, seed_graph_dataset):
    """Validates Operation 2: Retrieve entity node, canonical profile, aliases, and source mappings."""
    resp = test_client.get("/api/graph/nodes/NODE:DEPT:MAWS")
    assert resp.status_code == 200
    data = resp.get_json()["data"]

    # Verify node details
    assert data["node"]["node_id"] == "NODE:DEPT:MAWS"
    assert data["node"]["canonical_id"] == "DEPT-MAWS-TN"

    # Verify canonical registry profile
    assert data["canonical_profile"] is not None
    assert data["canonical_profile"]["canonical_name"] == "Municipal Administration and Water Supply Department"
    assert "நகராட்சி" in data["canonical_profile"]["tamil_name"]

    # Verify aliases and source mappings
    assert any(a["alias_name"] == "MAWS" for a in data["aliases"])
    assert any(sm["source_system"] == "TNBudgetPortal" for sm in data["source_mappings"])

    # Verify edge statistics
    assert "edge_statistics" in data
    assert data["edge_statistics"]["outbound_count"] >= 1

    # Verify 404 for nonexistent node
    resp_404 = test_client.get("/api/graph/nodes/NODE:NONEXISTENT:999")
    assert resp_404.status_code == 404


# ===========================================================================
# 3. Retrieving Directly Connected Entities
# ===========================================================================
def test_3_retrieve_directly_connected_neighbor_entities(test_client, seed_graph_dataset):
    """Validates Operation 3: Retrieve connected entities with relationship metadata."""
    resp = test_client.get("/api/graph/nodes/NODE:DEPT:MAWS/neighbors?direction=outgoing")
    assert resp.status_code == 200
    data = resp.get_json()["data"]

    assert data["node_id"] == "NODE:DEPT:MAWS"
    assert data["direction"] == "outgoing"
    assert len(data["connected_entities"]) >= 1

    conn = data["connected_entities"][0]
    assert conn["relationship_type"] == "implements"
    assert conn["matching_method"] == "DIRECT_DOCUMENTARY"
    assert conn["review_status"] == "VERIFIED"
    assert "MAWS Policy Note" in conn["evidence_reference"]
    assert conn["neighbor_node"]["node_id"] == "NODE:SCHEME:NEMMELI"
    assert conn["neighbor_node"]["entity_type"] == "BUDGET_SCHEME"


# ===========================================================================
# 4. Traversing Evidence Paths
# ===========================================================================
def test_4_traverse_evidence_paths_and_investigation_walks(test_client, seed_graph_dataset):
    """Validates Operation 4: Depth-bounded traversal and structured investigation walks."""
    # 1. POST /api/graph/traverse
    payload = {
        "start_node_id": "NODE:DEPT:MAWS",
        "direction": "outgoing",
        "max_depth": 3,
        "max_paths": 10,
    }
    resp_trav = test_client.post("/api/graph/traverse", json=payload)
    assert resp_trav.status_code == 200
    data_trav = resp_trav.get_json()["data"]
    assert "paths" in data_trav
    assert len(data_trav["paths"]) >= 1

    # Input validation: start_node_id required
    bad_resp = test_client.post("/api/graph/traverse", json={})
    assert bad_resp.status_code == 400

    # 2. GET /api/graph/investigate/<mode>
    resp_inv = test_client.get("/api/graph/investigate/promise?node_id=NODE:PROMISE:WATER_SUPPLY")
    assert resp_inv.status_code == 200
    data_inv = resp_inv.get_json()["data"]
    assert data_inv["mode"] == "promise"
    assert "paths" in data_inv


# ===========================================================================
# 5. Filtering by Relationship Type and Source
# ===========================================================================
def test_5_filter_edges_by_relationship_and_source_document(test_client, seed_graph_dataset):
    """Validates Operation 5: Edge filtering by relationship_type, source document, and review status."""
    resp = test_client.get("/api/graph/edges?relationship_type=implements&limit=10")
    assert resp.status_code == 200
    data = resp.get_json()["data"]
    assert data["total"] >= 1
    assert all(e["relationship_type"] == "implements" for e in data["edges"])

    resp_doc = test_client.get("/api/graph/edges?source_document_id=DOC-GO-TN-MAWS-2023-42")
    assert resp_doc.status_code == 200
    data_doc = resp_doc.get_json()["data"]
    assert len(data_doc["edges"]) >= 1
    assert data_doc["edges"][0]["source_document_id"] == "DOC-GO-TN-MAWS-2023-42"


# ===========================================================================
# 6. Retrieving Evidence for an Individual Relationship
# ===========================================================================
def test_6_retrieve_individual_edge_evidence_and_scorecard(test_client, seed_graph_dataset):
    """Validates Operation 6: Complete edge details, source/target, and 9-factor scorecard."""
    edge_id = seed_graph_dataset["edge_implements"].edge_id
    resp = test_client.get(f"/api/graph/edges/{edge_id}")
    assert resp.status_code == 200
    data = resp.get_json()["data"]

    assert data["edge_id"] == edge_id
    assert data["relationship_type"] == "implements"
    assert data["source_document_id"] == "DOC-GO-TN-MAWS-2023-42"
    assert data["source_document_hash"] is not None
    assert "quality_scorecard" in data
    assert data["quality_scorecard"]["composite_score"] >= 0.80
    assert "source_authenticity" in data["quality_scorecard"]["factor_breakdown"]

    # Verify 404 for nonexistent edge
    resp_404 = test_client.get("/api/graph/edges/EDGE:NONEXISTENT:999")
    assert resp_404.status_code == 404


# ===========================================================================
# 7. Listing Unresolved Relationship Candidates
# ===========================================================================
def test_7_list_unresolved_relationship_candidates(test_client, seed_graph_dataset):
    """Validates Operation 7: Listing unreviewed relationship candidate proposals."""
    resp = test_client.get("/api/graph/proposals/unresolved")
    assert resp.status_code == 200
    data = resp.get_json()["data"]

    assert data["total"] >= 1
    assert len(data["unresolved_proposals"]) >= 1
    prop = data["unresolved_proposals"][0]
    assert prop["proposal_id"] == "PROP-CANDIDATE-001"
    assert prop["review_status"] == "PENDING_REVIEW"
    assert prop["relationship_type"] == "responds_to"
    assert prop["confidence_score"] == 0.74


# ===========================================================================
# 8. Retrieving Contradictory or Disputed Evidence
# ===========================================================================
def test_8_retrieve_contradictory_and_disputed_evidence(test_client, seed_graph_dataset):
    """Validates Operation 8: Retrieving persistent conflicts and disputed evidence edges."""
    resp = test_client.get("/api/graph/conflicts?node_id=NODE:CLAIM:DESAL_OUTPUT&conflict_type=CONTRADICTORY_CLAIM_EVIDENCE")
    assert resp.status_code == 200
    data = resp.get_json()["data"]

    assert "conflicts" in data
    assert len(data["conflicts"]) >= 1
    conf = data["conflicts"][0]
    assert conf["conflict_type"] == "CONTRADICTORY_CLAIM_EVIDENCE"
    assert conf["severity"] == "HIGH"
    assert "epistemic_weight_comparison" in conf
    assert "statutory_weight" in conf["epistemic_weight_comparison"]

    # Verify disputed edges returned
    resp_disp = test_client.get("/api/graph/disputes")
    assert resp_disp.status_code == 200
    data_disp = resp_disp.get_json()["data"]
    assert "disputed_edges" in data_disp
    assert len(data_disp["disputed_edges"]) >= 1
    assert data_disp["disputed_edges"][0]["provenance_status"] == "DISPUTED"


# ===========================================================================
# 9. Retrieving Graph Provenance and Review History
# ===========================================================================
def test_9_retrieve_graph_provenance_and_review_history(test_client, seed_graph_dataset, api_test_db):
    """Validates Operation 9: Immutable review ledger across proposals and entity mutations."""
    # Create an entity audit record to simulate merge/split audit history
    audit_rec = EntityAuditRecord(
        audit_id="AUDIT-DEPT-001",
        primary_entity_id="DEPT-MAWS-TN",
        operation_type=EntityOperationType.STATUS_CHANGED,
        performed_by="REVIEWER_OFFICIAL_42",
        rationale="Added verified Tamil department title from Gazette No. 104",
        previous_state_json={"tamil_name": None},
        new_state_json={"tamil_name": "நகராட்சி நிர்வாகம் மற்றும் குடிநீர் வழங்கல் துறை"},
    )
    api_test_db.add(audit_rec)
    api_test_db.commit()

    resp = test_client.get("/api/graph/history?reviewer_id=REVIEWER_OFFICIAL_42")
    assert resp.status_code == 200
    data = resp.get_json()["data"]

    assert data["total"] >= 1
    item = data["history"][0]
    assert item["audit_type"] == "ENTITY_REGISTRY_MUTATION"
    assert item["reviewer_id"] == "REVIEWER_OFFICIAL_42"
    assert "Gazette No. 104" in item["notes"]


# ===========================================================================
# 10. Viewing Relevant Records from the Original Phase Modules
# ===========================================================================
def test_10_view_original_phase_records_without_data_duplication(test_client, seed_graph_dataset):
    """Validates Operation 10: Dynamic cross-phase record resolution across Phase 1–8 tables."""
    # 1. Phase 3: Political Promise
    resp_prom = test_client.get("/api/graph/nodes/NODE:PROMISE:WATER_SUPPLY/original-record")
    assert resp_prom.status_code == 200
    data_prom = resp_prom.get_json()["data"]
    assert data_prom["source_phase"] == "PHASE_3"
    assert data_prom["module_data"]["promise_id"] == "PROM-DMK-2021-WATER"
    assert data_prom["module_data"]["classification"] == "water_infrastructure"

    # 2. Phase 6: Public Claim
    resp_claim = test_client.get("/api/graph/nodes/NODE:CLAIM:DESAL_OUTPUT/original-record")
    assert resp_claim.status_code == 200
    data_claim = resp_claim.get_json()["data"]
    assert data_claim["source_phase"] == "PHASE_6"
    assert data_claim["module_data"]["claim_id"] == "CLAIM-DESAL-OUTPUT-2024"
    assert data_claim["module_data"]["status"] == "VERIFIED"

    # 3. Phase 7: Civic Issue
    resp_issue = test_client.get("/api/graph/nodes/NODE:ISSUE:DRAIN_OVERFLOW/original-record")
    assert resp_issue.status_code == 200
    data_issue = resp_issue.get_json()["data"]
    assert data_issue["source_phase"] == "PHASE_7"
    assert data_issue["module_data"]["issue_code"] == "ISSUE-GCC-2024-4401"


# ===========================================================================
# 11. Security & Privacy: Automated PII Scrubbing and Internal Path Sanitization
# ===========================================================================
def test_11_privacy_and_security_sanitization(test_client, seed_graph_dataset):
    """
    Validates that:
    1. Phone numbers, emails, and citizen salutations are redacted from grievance text.
    2. Local server filesystem paths (e.g. C:\\CIVCLENS\\logs\\...) are redacted.
    """
    # 1. Public retrieval of civic issue record
    resp = test_client.get("/api/graph/nodes/NODE:ISSUE:DRAIN_OVERFLOW/original-record")
    assert resp.status_code == 200
    mod_data = resp.get_json()["data"]["module_data"]

    desc = mod_data["description"]
    # Phone number must be redacted
    assert "+91-9840123456" not in desc
    assert "[PHONE REDACTED]" in desc

    # Email must be redacted
    assert "citizen@example.com" not in desc
    assert "[EMAIL REDACTED]" in desc

    # Citizen name with salutation must be scrubbed
    assert "Thiru K. Murugesan" not in desc

    # 2. Node properties path scrubbing
    resp_node = test_client.get("/api/graph/nodes/NODE:ISSUE:DRAIN_OVERFLOW")
    assert resp_node.status_code == 200
    props = resp_node.get_json()["data"]["node"]["properties"]
    assert "C:\\CIVCLENS" not in str(props)
    assert "[INTERNAL_PATH_REDACTED]" in props.get("file_path", "")


# ===========================================================================
# 12. Authorization: RBAC Enforcement on Review Mutations
# ===========================================================================
def test_12_role_based_authorization_for_review_mutations(test_client, seed_graph_dataset):
    """
    Validates RBAC enforcement:
    - Mutation endpoints reject requests without authorized role (403 Forbidden).
    - Requests with authorized role (e.g. LEAD_REVIEWER or DOMAIN_EXPERT) succeed.
    """
    prop_id = seed_graph_dataset["proposal_unresolved"].proposal_id

    # 1. Reject without authorization header
    resp_no_auth = test_client.post(f"/api/graph/proposals/{prop_id}/confirm", json={"reviewer_id": "ANON"})
    assert resp_no_auth.status_code == 403
    assert "Access Denied" in resp_no_auth.get_json()["message"]

    # 2. Reject with unauthorized role
    resp_bad_role = test_client.post(
        f"/api/graph/proposals/{prop_id}/confirm",
        headers={"X-Reviewer-Role": "CITIZEN_GUEST"},
        json={"reviewer_id": "GUEST_USER"},
    )
    assert resp_bad_role.status_code == 403
    assert "Access Denied" in resp_bad_role.get_json()["message"]

    # 3. Succeed with authorized reviewer role: LEAD_REVIEWER
    resp_auth = test_client.post(
        f"/api/graph/proposals/{prop_id}/confirm",
        headers={"X-Reviewer-Role": "LEAD_REVIEWER"},
        json={
            "reviewer_id": "LEAD_AUDITOR_42",
            "reviewer_notes": "Corroborated via municipal division register.",
        },
    )
    assert resp_auth.status_code == 200
    data_auth = resp_auth.get_json()["data"]
    assert data_auth["proposal"]["review_status"] == "CONFIRMED"
    assert data_auth["confirmed_edge"] is not None
    assert data_auth["confirmed_edge"]["relationship_type"] == "responds_to"
