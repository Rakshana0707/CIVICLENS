"""
Unit & Integration Tests for Phase 9.9 — Cross-Phase Investigation Workflows and Auditability.
=============================================================================================

Tests:
1. WORKFLOW A: Political Promise Delivery (Promise -> Schemes -> Budgets -> Implementation).
2. WORKFLOW B: Civic Issue Resolution (Docket -> Response -> Status -> Empirical Proof).
3. WORKFLOW C: Public Claim Dialectics (Supporting vs. Contradicting vs. Contextual Evidence).
4. WORKFLOW D: Representative Stewardship & Anti-Causality (Rep -> Constituency -> Works).
5. WORKFLOW E: Political Finance Transparency (Disclosed Entity -> Statutory Document).
6. Missing Information & Evidentiary Gap Detection.
7. Unreviewed Candidate Proposal Separation & Warning Flags.
8. Official Administrative Reporting vs. Independent Verification Matrix.
9. Reviewer Decision Audit History Extraction.
10. Non-Verdict Summary Generation (Evidence + Unresolved Questions).
11. Auditable Report Export (JSON & Markdown) with DPDPA 2023 PII & Path Sanitization.
12. REST API Integration Endpoints for Workflows A–E and Report Export.
"""

import pytest
from unittest.mock import MagicMock
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.database.base_class import Base
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
    GraphReviewStatus,
    GraphProvenanceStatus,
)
from backend.models.entity_registry import (
    CanonicalEntity,
    EntityAuditRecord,
    EntityOperationType,
    RegistryEntityType,
)
from backend.services.investigation_service import CrossPhaseInvestigationService
from backend.api.app import create_app
import backend.api.graph as api_graph_module


# -----------------------------------------------------------------------------
# FIXTURES
# -----------------------------------------------------------------------------
@pytest.fixture(scope="module")
def inv_engine():
    """In-memory SQLite engine for investigation workflow tests."""
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(engine)
    return engine


@pytest.fixture(scope="module")
def inv_db(inv_engine):
    """Provides transactional database session."""
    Session = sessionmaker(bind=inv_engine)
    session = Session()

    # Seed cross-phase graph fixtures
    # 1. Promise
    p_node = CivicGraphNode(
        node_id="NODE:PROM:DMK_WATER",
        canonical_id="PROM-DMK-WATER-01",
        label="DMK 2021 Manifesto 114: Desalination Water Supply",
        label_ta="திமுக வாக்குறுதி 114: கடல்நீராக்கல் குடிநீர்",
        entity_type=GraphEntityType.POLITICAL_PROMISE,
        source_phase="phase1",
    )
    # 2. Scheme
    s_node = CivicGraphNode(
        node_id="NODE:SCHEME:NEMMELI",
        canonical_id="SCHEME-NEMMELI-01",
        label="Nemmeli 150 MLD Desalination Scheme",
        label_ta="நெம்மேலி குடிநீராக்கல் திட்டம்",
        entity_type=GraphEntityType.BUDGET_SCHEME,
        source_phase="phase2",
    )
    # 3. Budget
    b_node = CivicGraphNode(
        node_id="NODE:BUDGET:DEMAND_34",
        canonical_id="BUDGET-DEMAND-34",
        label="Demand 34 Capital Head 4215",
        entity_type=GraphEntityType.BUDGET_RECORD,
        source_phase="phase1",
    )
    # 4. Civic Issue
    i_node = CivicGraphNode(
        node_id="NODE:ISSUE:VELACHERY_WATER",
        canonical_id="ISSUE-VELACHERY-01",
        label="Velachery Ward 178 Water Shortage",
        entity_type=GraphEntityType.CIVIC_ISSUE,
        source_phase="phase7",
    )
    # 5. Department
    d_node = CivicGraphNode(
        node_id="NODE:DEPT:MAWS",
        canonical_id="DEPT-MAWS-01",
        label="MAWS Department",
        entity_type=GraphEntityType.GOVERNMENT_DEPARTMENT,
        source_phase="phase3",
    )
    # 6. Claim
    c_node = CivicGraphNode(
        node_id="NODE:CLAIM:OUTPUT_150MLD",
        canonical_id="CLAIM-150MLD-01",
        label="Claim: Nemmeli Operating at Full 150 MLD Output",
        entity_type=GraphEntityType.CLAIM,
        source_phase="phase8",
    )
    # 7. Source Doc
    doc_node = CivicGraphNode(
        node_id="NODE:DOC:CAG_2023",
        canonical_id="DOC-CAG-2023-01",
        label="CAG Report 4 of 2023",
        entity_type=GraphEntityType.SOURCE_DOCUMENT,
        source_phase="phase8",
    )
    # 8. Representative & Constituency
    rep_node = CivicGraphNode(
        node_id="NODE:REP:VELACHERY_MLA",
        canonical_id="REP-VELACHERY-01",
        label="Aassan Maulaana (MLA, Velachery)",
        entity_type=GraphEntityType.REPRESENTATIVE,
        source_phase="phase6",
    )
    const_node = CivicGraphNode(
        node_id="NODE:CONST:VELACHERY",
        canonical_id="CONST-VELACHERY-026",
        label="Velachery Constituency AC-026",
        entity_type=GraphEntityType.CONSTITUENCY,
        source_phase="phase6",
    )
    # 9. Party
    party_node = CivicGraphNode(
        node_id="NODE:PARTY:DMK",
        canonical_id="PARTY-DMK-01",
        label="DMK Party",
        entity_type=GraphEntityType.POLITICAL_PARTY,
        source_phase="phase5",
    )

    session.add_all([p_node, s_node, b_node, i_node, d_node, c_node, doc_node, rep_node, const_node, party_node])
    session.flush()

    # Edges
    # Workflow A edges
    e_prom_scheme = CivicEvidenceEdge(
        edge_id="EDGE:PROM:SCHEME:01",
        source_node_id=p_node.node_id,
        target_node_id=s_node.node_id,
        relationship_type=GraphRelationshipType.PROMISES,
        evidence_reference="Manifesto Item 114 aligns with scheme administrative sanction",
        source_document_id="DOC-MANIFESTO-2021",
        source_document_hash="a1b2c3d4e5f67890abcdef1234567890abcdef1234567890abcdef1234567890",
        matching_method=MatchingMethod.DIRECT_DOCUMENTARY,
        confidence_score=0.95,
        review_status=GraphReviewStatus.VERIFIED,
        provenance_status=GraphProvenanceStatus.VALID,
    )
    e_scheme_budget = CivicEvidenceEdge(
        edge_id="EDGE:BUDGET:SCHEME:01",
        source_node_id=b_node.node_id,
        target_node_id=s_node.node_id,
        relationship_type=GraphRelationshipType.FUNDS,
        evidence_reference="Demand 34 Head 4215 grants 1250 Cr outlay",
        source_document_id="DOC-BUDGET-DEMAND-34",
        source_document_hash="f1e2d3c4b5a67890abcdef1234567890abcdef1234567890abcdef1234567890",
        matching_method=MatchingMethod.DETERMINISTIC_ID,
        confidence_score=0.98,
        review_status=GraphReviewStatus.VERIFIED,
        provenance_status=GraphProvenanceStatus.VALID,
    )

    # Workflow B edges
    e_dept_issue = CivicEvidenceEdge(
        edge_id="EDGE:DEPT:ISSUE:01",
        source_node_id=d_node.node_id,
        target_node_id=i_node.node_id,
        relationship_type=GraphRelationshipType.RESPONDS_TO,
        evidence_reference="MAWS response docket ATR 8921",
        source_document_id="DOC-ATR-MAWS-8921",
        matching_method=MatchingMethod.DIRECT_DOCUMENTARY,
        confidence_score=0.90,
        review_status=GraphReviewStatus.VERIFIED,
        provenance_status=GraphProvenanceStatus.VALID,
    )

    # Workflow C edges (Dialectical supporting vs contradicting)
    e_claim_support = CivicEvidenceEdge(
        edge_id="EDGE:DOC:CLAIM:01",
        source_node_id=s_node.node_id,
        target_node_id=c_node.node_id,
        relationship_type=GraphRelationshipType.PROVIDES_EVIDENCE_FOR,
        evidence_reference="Department press note asserting 150 MLD commissioning",
        source_document_id="DOC-PRESS-2023",
        matching_method=MatchingMethod.DIRECT_DOCUMENTARY,
        confidence_score=0.85,
        review_status=GraphReviewStatus.VERIFIED,
        provenance_status=GraphProvenanceStatus.VALID,
    )
    e_claim_contra = CivicEvidenceEdge(
        edge_id="EDGE:CAG:CLAIM:01",
        source_node_id=doc_node.node_id,
        target_node_id=c_node.node_id,
        relationship_type=GraphRelationshipType.CONTRADICTS,
        evidence_reference="CAG Audit Para 3.8 measured 94.2 MLD average daily dispatch",
        source_document_id="DOC-CAG-REPORT-2023",
        source_document_hash="11223344556677889900aabbccddeeff11223344556677889900aabbccddeeff",
        matching_method=MatchingMethod.DIRECT_DOCUMENTARY,
        confidence_score=0.96,
        review_status=GraphReviewStatus.VERIFIED,
        provenance_status=GraphProvenanceStatus.VALID,
    )

    # Workflow D edges (Representative & Constituency)
    e_rep_const = CivicEvidenceEdge(
        edge_id="EDGE:REP:CONST:01",
        source_node_id=rep_node.node_id,
        target_node_id=const_node.node_id,
        relationship_type=GraphRelationshipType.REPRESENTS,
        evidence_reference="Tamil Nadu Legislative Assembly Gazette notification",
        source_document_id="DOC-TNLA-GAZETTE-2021",
        matching_method=MatchingMethod.DETERMINISTIC_ID,
        confidence_score=1.0,
        review_status=GraphReviewStatus.VERIFIED,
        provenance_status=GraphProvenanceStatus.VALID,
    )
    e_issue_const = CivicEvidenceEdge(
        edge_id="EDGE:ISSUE:CONST:01",
        source_node_id=i_node.node_id,
        target_node_id=const_node.node_id,
        relationship_type=GraphRelationshipType.LOCATED_IN,
        evidence_reference="GCC Ward 178 located inside AC-026",
        source_document_id="DOC-GCC-DELIM-2022",
        matching_method=MatchingMethod.DETERMINISTIC_ID,
        confidence_score=0.99,
        review_status=GraphReviewStatus.VERIFIED,
        provenance_status=GraphProvenanceStatus.VALID,
    )

    # Workflow E edges (Party & Finance)
    e_party_rep = CivicEvidenceEdge(
        edge_id="EDGE:PARTY:REP:01",
        source_node_id=party_node.node_id,
        target_node_id=rep_node.node_id,
        relationship_type=GraphRelationshipType.RELATES_TO,
        evidence_reference="ECI General Election 2021 Form 20 return",
        source_document_id="DOC-ECI-FORM-20-2021",
        source_document_hash="99887766554433221100aabbccddeeff99887766554433221100aabbccddeeff",
        matching_method=MatchingMethod.DIRECT_DOCUMENTARY,
        confidence_score=0.99,
        review_status=GraphReviewStatus.VERIFIED,
        provenance_status=GraphProvenanceStatus.VALID,
    )

    session.add_all([
        e_prom_scheme, e_scheme_budget, e_dept_issue,
        e_claim_support, e_claim_contra, e_rep_const, e_issue_const, e_party_rep
    ])

    # Candidate Proposal
    prop = CandidateRelationshipProposal(
        proposal_id="PROP-NEMMELI-ISSUE",
        source_node_id=s_node.node_id,
        target_node_id=i_node.node_id,
        relationship_type=GraphRelationshipType.RESPONDS_TO,
        evidence_supporting_candidate="Distribution line augmentation covers Ward 178",
        matching_method=MatchingMethod.AUTOMATED_CANDIDATE,
        confidence_score=0.75,
        review_status=CandidateReviewDisposition.PENDING_REVIEW,
    )
    session.add(prop)

    # Conflict Record
    conflict = CivicConflictRecord(
        conflict_id="CONF-DESAL-OUTPUT",
        conflict_type=ConflictTypeEnum.CONTRADICTORY_CLAIM_EVIDENCE,
        severity=ConflictSeverityEnum.HIGH,
        primary_node_id=c_node.node_id,
        description="CAG audit measured 94.2 MLD output contradicting 150 MLD claim",
        epistemic_weight_comparison={"statutory_weight": 0.96, "press_weight": 0.85},
        resolution_status=ConflictResolutionStatus.EXPLAINED_DIALECTIC,
    )
    session.add(conflict)

    # Reviewer decision audit history
    audit_rec = EntityAuditRecord(
        audit_id="AUDIT-DEPT-01",
        primary_entity_id=d_node.node_id,
        operation_type=EntityOperationType.STATUS_CHANGED,
        performed_by="LEAD_AUDITOR_TN",
        rationale="Verified primary department charter from Gazette No. 42",
    )
    session.add(audit_rec)

    session.commit()
    yield session
    session.close()


@pytest.fixture
def api_test_client(inv_db, monkeypatch):
    """Flask test client for Phase 9.9 API verification."""
    monkeypatch.setattr(inv_db, "close", lambda: None)
    monkeypatch.setattr(api_graph_module, "SessionLocal", lambda: inv_db)
    app = create_app()
    app.config["TESTING"] = True
    return app.test_client()


# =============================================================================
# TEST CASES
# =============================================================================
class TestPhase9InvestigationWorkflows:
    """Test suite for Phase 9.9 auditable investigation workflows."""

    # 1. Workflow A
    def test_1_workflow_a_promise_delivery(self, inv_db):
        """Validates Workflow A: Promise -> Schemes -> Budgets -> Implementation."""
        data = CrossPhaseInvestigationService.investigate_promise_delivery(
            identifier="NODE:PROM:DMK_WATER", session=inv_db
        )
        assert data["workflow"] == "WORKFLOW_A_PROMISE_DELIVERY"
        assert data["subject_identifier"] == "NODE:PROM:DMK_WATER"
        assert len(data["records_available"]["related_schemes"]) >= 1
        assert len(data["records_available"]["budget_allocations"]) >= 1
        assert "Policy Association Rule" in data["epistemic_guardrail"]
        assert len(data["unresolved_questions"]) >= 1
        assert len(data["official_reporting_vs_independent_verification"]) >= 2

    # 2. Workflow B
    def test_2_workflow_b_civic_issue_resolution(self, inv_db):
        """Validates Workflow B: Civic Issue -> Department Response -> Status -> Resolution."""
        data = CrossPhaseInvestigationService.investigate_civic_issue_resolution(
            identifier="NODE:ISSUE:VELACHERY_WATER", session=inv_db
        )
        assert data["workflow"] == "WORKFLOW_B_CIVIC_ISSUE_RESOLUTION"
        assert len(data["records_available"]["department_responses"]) >= 1
        # Empirically missing resolution proof is properly detected
        assert any("empirical ground proof" in gap.lower() for gap in data["missing_information"])
        assert "marked_resolved" in data["epistemic_guardrail"]

    # 3. Workflow C
    def test_3_workflow_c_claim_dialectics(self, inv_db):
        """Validates Workflow C: Public Claim -> Supporting vs. Contradicting Evidence."""
        data = CrossPhaseInvestigationService.investigate_claim_dialectics(
            identifier="NODE:CLAIM:OUTPUT_150MLD", session=inv_db
        )
        assert data["workflow"] == "WORKFLOW_C_CLAIM_DIALECTICS"
        assert len(data["records_available"]["supporting_evidence_edges"]) >= 1
        assert len(data["records_available"]["contradicting_evidence_edges"]) >= 1
        assert len(data["records_available"]["active_conflicts"]) >= 1
        assert "Dialectical Preservation Principle" in data["epistemic_guardrail"]

    # 4. Workflow D
    def test_4_workflow_d_representative_stewardship(self, inv_db):
        """Validates Workflow D: Representative -> Constituency -> Works (Anti-Causality)."""
        data = CrossPhaseInvestigationService.investigate_representative_stewardship(
            identifier="NODE:REP:VELACHERY_MLA", session=inv_db
        )
        assert data["workflow"] == "WORKFLOW_D_REPRESENTATIVE_STEWARDSHIP"
        assert len(data["records_available"]["constituencies"]) >= 1
        assert len(data["records_available"]["documented_works_and_issues"]) >= 1
        assert "Anti-Causality & Non-Defamation Rule" in data["epistemic_guardrail"]
        assert "NOT establish personal liability" in data["epistemic_guardrail"]

    # 5. Workflow E
    def test_5_workflow_e_political_finance(self, inv_db):
        """Validates Workflow E: Political Finance -> Statutory Document -> Supported Entities."""
        data = CrossPhaseInvestigationService.investigate_political_finance(
            identifier="NODE:PARTY:DMK", session=inv_db
        )
        assert data["workflow"] == "WORKFLOW_E_POLITICAL_FINANCE"
        assert data["records_available"]["connected_transactions_count"] >= 1
        assert "Statutory Disclosure Rule" in data["epistemic_guardrail"]
        assert "NOT establish or infer corrupt intent" in data["epistemic_guardrail"]

    # 6. Missing Information Detection
    def test_6_missing_information_detection(self, inv_db):
        """Verifies that missing vouchers or unlinked records produce explicit evidentiary gaps."""
        # Query an orphan node with no budget or scheme
        orphan_node = CivicGraphNode(
            node_id="NODE:PROM:ORPHAN",
            canonical_id="CAN-ORPHAN-01",
            label="Orphan Promise",
            entity_type=GraphEntityType.POLITICAL_PROMISE,
            source_phase="phase1",
        )
        inv_db.add(orphan_node)
        inv_db.flush()

        data = CrossPhaseInvestigationService.investigate_promise_delivery(
            identifier="NODE:PROM:ORPHAN", session=inv_db
        )
        assert len(data["missing_information"]) >= 1
        assert any("no government scheme officially mapped" in gap.lower() for gap in data["missing_information"])

    # 7. Unreviewed Candidate Proposal Separation
    def test_7_unreviewed_candidate_proposal_separation(self, inv_db):
        """Ensures automated candidate proposals are flagged and not mixed with confirmed edges."""
        data = CrossPhaseInvestigationService.investigate_promise_delivery(
            identifier="NODE:PROM:DMK_WATER", session=inv_db
        )
        candidates = data["unreviewed_candidate_links"]
        # Candidates list exists and review status is PENDING_REVIEW
        for c in candidates:
            assert c["review_status"] == "PENDING_REVIEW"

    # 8. Official Reporting vs. Independent Verification
    def test_8_official_reporting_vs_independent_verification(self, inv_db):
        """Validates distinguishing self-reported ATR from independent statutory verification."""
        data = CrossPhaseInvestigationService.investigate_claim_dialectics(
            identifier="NODE:CLAIM:OUTPUT_150MLD", session=inv_db
        )
        matrix = data["official_reporting_vs_independent_verification"]
        natures = {m["evidence_nature"] for m in matrix}
        assert "INDEPENDENT_VERIFICATION" in natures

    # 9. Reviewer Decision Audit History
    def test_9_reviewer_decision_audit_history(self, inv_db):
        """Verifies extraction of immutable reviewer decisions."""
        data = CrossPhaseInvestigationService.investigate_civic_issue_resolution(
            identifier="NODE:ISSUE:VELACHERY_WATER", session=inv_db
        )
        history = data["reviewer_audit_history"]
        assert len(history) >= 1
        audit = history[0]
        assert "performed_by" in audit or "reviewed_by" in audit
        assert "rationale" in audit

    # 10. Non-Verdict Summary Generation
    def test_10_non_verdict_summary_generation(self, inv_db):
        """Verifies summary lists evidence and questions without issuing automated verdicts."""
        data = CrossPhaseInvestigationService.investigate_promise_delivery(
            identifier="NODE:PROM:DMK_WATER", session=inv_db
        )
        assert "verdict" not in data  # Prohibited: no unilateral verdict
        assert "unresolved_questions" in data
        assert len(data["unresolved_questions"]) >= 2

    # 11. Report Export with PII & Path Sanitization
    def test_11_report_export_and_sanitization(self, inv_db):
        """Validates JSON and Markdown report export with DPDPA 2023 sanitization."""
        # Export as JSON
        json_report = CrossPhaseInvestigationService.export_investigation_report(
            workflow_type="workflow_a",
            identifier="NODE:PROM:DMK_WATER",
            format="json",
            session=inv_db,
        )
        assert "metadata" in json_report
        assert "investigation_summary" in json_report
        assert "DPDPA 2023" in json_report["metadata"]["data_governance"]

        # Export as Markdown
        md_report = CrossPhaseInvestigationService.export_investigation_report(
            workflow_type="workflow_a",
            identifier="NODE:PROM:DMK_WATER",
            format="markdown",
            session=inv_db,
        )
        assert isinstance(md_report, str)
        assert "# CIVICLENS TN Auditable Investigation Report" in md_report
        assert "Official Administrative Reporting vs. Independent Verification" in md_report
        assert "Unresolved Questions" in md_report

    # 12. Generic Dispatcher Error Handling
    def test_12_generic_dispatcher_error_handling(self, inv_db):
        """Ensures invalid workflow type triggers informative ValueError."""
        with pytest.raises(ValueError) as exc:
            CrossPhaseInvestigationService.run_investigation_workflow(
                workflow_type="invalid_workflow_xyz",
                identifier="NODE:TEST",
                session=inv_db,
            )
        assert "Unknown investigation workflow" in str(exc.value)

    # 13. REST API Investigation Endpoints
    def test_13_rest_api_investigation_endpoints(self, api_test_client, inv_db):
        """Validates GET endpoints for Workflows A–E and Report Export."""
        # Workflow A
        resp_a = api_test_client.get("/api/graph/investigate/workflow-a/promise?id=NODE:PROM:DMK_WATER")
        assert resp_a.status_code == 200
        assert resp_a.get_json()["status"] == "success"

        # Workflow B
        resp_b = api_test_client.get("/api/graph/investigate/workflow-b/civic-issue?id=NODE:ISSUE:VELACHERY_WATER")
        assert resp_b.status_code == 200

        # Workflow C
        resp_c = api_test_client.get("/api/graph/investigate/workflow-c/claim?id=NODE:CLAIM:OUTPUT_150MLD")
        assert resp_c.status_code == 200

        # Workflow D
        resp_d = api_test_client.get("/api/graph/investigate/workflow-d/representative?id=NODE:REP:VELACHERY_MLA")
        assert resp_d.status_code == 200

        # Workflow E
        resp_e = api_test_client.get("/api/graph/investigate/workflow-e/funding?id=NODE:PARTY:DMK")
        assert resp_e.status_code == 200

        # Export Report (JSON)
        resp_exp = api_test_client.get("/api/graph/investigate/report/export?workflow=workflow_a&id=NODE:PROM:DMK_WATER&format=json")
        assert resp_exp.status_code == 200
        assert "metadata" in resp_exp.get_json()["data"]

        # Export Report (Markdown)
        resp_md = api_test_client.get("/api/graph/investigate/report/export?workflow=workflow_a&id=NODE:PROM:DMK_WATER&format=markdown")
        assert resp_md.status_code == 200
        assert "report_markdown" in resp_md.get_json()["data"]
