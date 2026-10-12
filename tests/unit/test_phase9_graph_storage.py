"""
Phase 9.3 — Evidence Graph Storage & Relationship Validation Tests.
====================================================================

Validates:
1. Referential integrity: Rejects edges referencing non-existent nodes and self-loops.
2. Missing evidence rejection: Rejects edges lacking evidence reference or source document citation.
3. Duplicate edge prevention & repeatable imports: Ensures idempotent repeat ingestion without duplicate edge records.
4. Epistemic Rule 1: Response -> Civic Issue requires source document or verified review; unbacked candidates rejected.
5. Epistemic Rule 2: Promise -> Scheme relates_to allowed, but 'implements' rejected without documentary fulfillment proof.
6. Epistemic Rule 3: Funding disclosure identity match requires high confidence or verified review.
7. Epistemic Rule 4: Claim dialectic permits simultaneous supporting and contradicting evidence edges.
8. Epistemic Rule 5: Civic issue geographic association does not establish representative responsibility.
9. Reversible entity-link corrections: Soft-reversals (RETRACTED, SUPERSEDED, RESTORED) and metadata corrections
   retain full chronological provenance in CivicEdgeAuditRecord without deleting data.
10. Canonical entity integration & bidirectional traversal queries.
"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.database.base_class import Base
from backend.models.entity_registry import (
    CanonicalEntity,
    RegistryEntityType,
    EntityLifecycleStatus,
)
from backend.models.graph import (
    CivicGraphNode,
    CivicEvidenceEdge,
    CivicEdgeAuditRecord,
    GraphEntityType,
    GraphRelationshipType,
    MatchingMethod,
    GraphProvenanceStatus,
    GraphReviewStatus,
    EdgeOperationType,
)
from backend.services.graph_storage_service import (
    GraphStorageService,
    GraphStorageError,
    NodeNotFoundError,
    InvalidEvidenceError,
    EpistemicRuleViolationError,
)


@pytest.fixture
def db_session():
    """Isolated in-memory SQLite database session for Phase 9.3 tests."""
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def seed_nodes(db_session):
    """Creates a standard set of labelled test nodes representing Phases 1-8."""
    # Canonical entity
    canon_dept = CanonicalEntity(
        entity_id="CANON:DEPT:MAWS",
        entity_type=RegistryEntityType.GOVERNMENT_DEPARTMENT,
        canonical_name_en="Municipal Administration and Water Supply Department",
        canonical_name_ta="நகராட்சி நிர்வாகம் மற்றும் குடிநீர் வழங்கல் துறை",
        normalized_name="municipal administration and water supply department",
        status=EntityLifecycleStatus.ACTIVE,
        is_test_fixture=True,
    )
    db_session.add(canon_dept)
    db_session.flush()

    nodes = {
        "dept": GraphStorageService.create_or_get_node(
            db_session,
            node_id="NODE:DEPT:MAWS",
            entity_type=GraphEntityType.GOVERNMENT_DEPARTMENT,
            canonical_id="DEPT-MAWS-034",
            label="Municipal Administration and Water Supply Department",
            source_phase="PHASE_1",
            canonical_entity_id="CANON:DEPT:MAWS",
            is_test_fixture=True,
        ),
        "scheme": GraphStorageService.create_or_get_node(
            db_session,
            node_id="NODE:SCHEME:BREAKFAST",
            entity_type=GraphEntityType.HISTORICAL_SCHEME,
            canonical_id="SCH-TN-2022-001",
            label="Chief Minister's Breakfast Scheme",
            source_phase="PHASE_2",
            is_test_fixture=True,
        ),
        "promise": GraphStorageService.create_or_get_node(
            db_session,
            node_id="NODE:PROM:BREAKFAST",
            entity_type=GraphEntityType.POLITICAL_PROMISE,
            canonical_id="PROM-DMK-2021-314",
            label="Provide free breakfast in all government primary schools",
            source_phase="PHASE_3",
            is_test_fixture=True,
        ),
        "donor": GraphStorageService.create_or_get_node(
            db_session,
            node_id="NODE:DONOR:INFRA_CORP",
            entity_type=GraphEntityType.DONOR,
            canonical_id="DONOR-CORP-99",
            label="Tamil Nadu Infrastructure Investments Pvt Ltd",
            source_phase="PHASE_4",
            is_test_fixture=True,
        ),
        "party": GraphStorageService.create_or_get_node(
            db_session,
            node_id="NODE:PARTY:DMK",
            entity_type=GraphEntityType.POLITICAL_PARTY,
            canonical_id="PARTY-DMK",
            label="Dravida Munnetra Kazhagam",
            source_phase="PHASE_4",
            is_test_fixture=True,
        ),
        "contribution": GraphStorageService.create_or_get_node(
            db_session,
            node_id="NODE:CONTRIB:EB_2023_01",
            entity_type=GraphEntityType.CONTRIBUTION,
            canonical_id="CONTRIB-EB-2023-01",
            label="Electoral Bond Disclosure Entry #1042",
            source_phase="PHASE_4",
            is_test_fixture=True,
        ),
        "rep": GraphStorageService.create_or_get_node(
            db_session,
            node_id="NODE:REP:STALIN",
            entity_type=GraphEntityType.REPRESENTATIVE,
            canonical_id="REP-TN-KOLATHUR",
            label="M. K. Stalin",
            source_phase="PHASE_5",
            is_test_fixture=True,
        ),
        "constituency": GraphStorageService.create_or_get_node(
            db_session,
            node_id="NODE:CONST:KOLATHUR",
            entity_type=GraphEntityType.CONSTITUENCY,
            canonical_id="AC-013",
            label="Kolathur Assembly Constituency",
            source_phase="PHASE_5",
            is_test_fixture=True,
        ),
        "claim": GraphStorageService.create_or_get_node(
            db_session,
            node_id="NODE:CLAIM:BREAKFAST_ATTENDANCE",
            entity_type=GraphEntityType.CLAIM,
            canonical_id="CLAIM-2023-EDU-01",
            label="Breakfast scheme boosted primary school attendance by 18%",
            source_phase="PHASE_6",
            is_test_fixture=True,
        ),
        "evidence_doc_pos": GraphStorageService.create_or_get_node(
            db_session,
            node_id="NODE:DOC:DPI_REPORT",
            entity_type=GraphEntityType.EVIDENCE_DOCUMENT,
            canonical_id="DOC-DPI-EVAL-2023",
            label="DPI Evaluation Report on School Attendance 2023",
            source_phase="PHASE_6",
            is_test_fixture=True,
        ),
        "evidence_doc_neg": GraphStorageService.create_or_get_node(
            db_session,
            node_id="NODE:DOC:CAG_AUDIT",
            entity_type=GraphEntityType.EVIDENCE_DOCUMENT,
            canonical_id="DOC-CAG-2023-EDUCATION",
            label="CAG Audit on Mid-Day Scheme & Attendance Patterns",
            source_phase="PHASE_6",
            is_test_fixture=True,
        ),
        "civic_issue": GraphStorageService.create_or_get_node(
            db_session,
            node_id="NODE:ISSUE:WATER_KOLATHUR",
            entity_type=GraphEntityType.CIVIC_ISSUE,
            canonical_id="ISSUE-2024-KOL-WTR-01",
            label="Contaminated drinking water in Ward 65, Kolathur",
            source_phase="PHASE_7",
            is_test_fixture=True,
        ),
        "response": GraphStorageService.create_or_get_node(
            db_session,
            node_id="NODE:RESP:MAWS_ACTION",
            entity_type=GraphEntityType.RESPONSE_RECORD,
            canonical_id="RESP-MAWS-2024-089",
            label="CMWSSB Pipeline Flushing and Chlorination Action Report",
            source_phase="PHASE_8",
            is_test_fixture=True,
        ),
    }
    db_session.commit()
    return nodes


def test_1_referential_integrity_nonexistent_nodes(db_session, seed_nodes):
    """Rejects edges where either source or target node does not exist, or self-loops."""
    # 1. Non-existent source node
    with pytest.raises(NodeNotFoundError) as exc_info:
        GraphStorageService.add_evidence_edge(
            session=db_session,
            source_node_id="NODE:NON_EXISTENT_SRC",
            target_node_id="NODE:SCHEME:BREAKFAST",
            relationship_type=GraphRelationshipType.RELATES_TO,
            evidence_reference="Some citation",
            source_document_id="DOC-01",
            is_test_fixture=True,
        )
    assert "NODE:NON_EXISTENT_SRC" in str(exc_info.value)

    # 2. Non-existent target node
    with pytest.raises(NodeNotFoundError) as exc_info:
        GraphStorageService.add_evidence_edge(
            session=db_session,
            source_node_id="NODE:DEPT:MAWS",
            target_node_id="NODE:NON_EXISTENT_TGT",
            relationship_type=GraphRelationshipType.FUNDS,
            evidence_reference="Some citation",
            source_document_id="DOC-01",
            is_test_fixture=True,
        )
    assert "NODE:NON_EXISTENT_TGT" in str(exc_info.value)

    # 3. Self-referential loop
    with pytest.raises(EpistemicRuleViolationError) as exc_info:
        GraphStorageService.add_evidence_edge(
            session=db_session,
            source_node_id="NODE:DEPT:MAWS",
            target_node_id="NODE:DEPT:MAWS",
            relationship_type=GraphRelationshipType.RELATES_TO,
            evidence_reference="Self loop citation",
            source_document_id="DOC-01",
            is_test_fixture=True,
        )
    assert "Self-referential edge" in str(exc_info.value)


def test_2_missing_evidence_rejection(db_session, seed_nodes):
    """Rejects edges lacking both an evidence reference and a source document citation."""
    with pytest.raises(InvalidEvidenceError) as exc_info:
        GraphStorageService.add_evidence_edge(
            session=db_session,
            source_node_id="NODE:DEPT:MAWS",
            target_node_id="NODE:SCHEME:BREAKFAST",
            relationship_type=GraphRelationshipType.IMPLEMENTS,
            evidence_reference=None,
            source_document_id=None,
            is_test_fixture=True,
        )
    assert "lacks mandatory evidence reference or source document citation" in str(exc_info.value)

    # Blank whitespace strings are also rejected
    with pytest.raises(InvalidEvidenceError):
        GraphStorageService.add_evidence_edge(
            session=db_session,
            source_node_id="NODE:DEPT:MAWS",
            target_node_id="NODE:SCHEME:BREAKFAST",
            relationship_type=GraphRelationshipType.IMPLEMENTS,
            evidence_reference="   ",
            source_document_id="",
            is_test_fixture=True,
        )


def test_3_duplicate_edges_and_repeatable_imports(db_session, seed_nodes):
    """Repeatable imports must be idempotent and prevent duplicate active edges."""
    edge1 = GraphStorageService.add_evidence_edge(
        session=db_session,
        source_node_id="NODE:DEPT:MAWS",
        target_node_id="NODE:SCHEME:BREAKFAST",
        relationship_type=GraphRelationshipType.FUNDS,
        evidence_reference="Demand 34, Page 12, Detailed Budget Estimates 2022-23",
        source_document_id="DOC-BUDGET-2022-34",
        source_document_hash="a1b2c3d4e5f67890123456789abcdef0123456789abcdef0123456789abcdef0",
        matching_method=MatchingMethod.DIRECT_DOCUMENTARY,
        confidence_score=1.0,
        valid_from="2022-04-01",
        valid_to="2023-03-31",
        is_test_fixture=True,
    )
    db_session.commit()

    # Re-import identical edge (repeatable import simulation)
    edge2 = GraphStorageService.add_evidence_edge(
        session=db_session,
        source_node_id="NODE:DEPT:MAWS",
        target_node_id="NODE:SCHEME:BREAKFAST",
        relationship_type=GraphRelationshipType.FUNDS,
        evidence_reference="Demand 34, Page 12, Detailed Budget Estimates 2022-23",
        source_document_id="DOC-BUDGET-2022-34",
        source_document_hash="a1b2c3d4e5f67890123456789abcdef0123456789abcdef0123456789abcdef0",
        matching_method=MatchingMethod.DIRECT_DOCUMENTARY,
        confidence_score=1.0,
        is_test_fixture=True,
    )
    db_session.commit()

    # Must be the exact same edge ID, not a duplicate row
    assert edge1.edge_id == edge2.edge_id

    # Total edges between these nodes must be exactly 1
    edges_in_db = (
        db_session.query(CivicEvidenceEdge)
        .filter(
            CivicEvidenceEdge.source_node_id == "NODE:DEPT:MAWS",
            CivicEvidenceEdge.target_node_id == "NODE:SCHEME:BREAKFAST",
            CivicEvidenceEdge.relationship_type == GraphRelationshipType.FUNDS,
        )
        .all()
    )
    assert len(edges_in_db) == 1


def test_4_epistemic_rule_1_response_to_civic_issue(db_session, seed_nodes):
    """
    Rule 1: A response can relate to a civic issue only when supported by
    a source or reviewed matching decision. Automated heuristic candidates without proof are rejected.
    """
    # 1. Reject automated candidate match with no official source document and no human review
    with pytest.raises(EpistemicRuleViolationError) as exc_info:
        GraphStorageService.add_evidence_edge(
            session=db_session,
            source_node_id="NODE:RESP:MAWS_ACTION",
            target_node_id="NODE:ISSUE:WATER_KOLATHUR",
            relationship_type=GraphRelationshipType.RESPONDS_TO,
            evidence_reference="Keyword match on 'water pipeline'",
            source_document_id=None,  # Missing source document!
            matching_method=MatchingMethod.AUTOMATED_CANDIDATE,
            review_status=GraphReviewStatus.PENDING_REVIEW,  # Unreviewed!
            is_test_fixture=True,
        )
    assert "A response (NODE:RESP:MAWS_ACTION) can relate to a civic issue" in str(exc_info.value)

    # 2. Allow when backed by official source document
    edge_doc = GraphStorageService.add_evidence_edge(
        session=db_session,
        source_node_id="NODE:RESP:MAWS_ACTION",
        target_node_id="NODE:ISSUE:WATER_KOLATHUR",
        relationship_type=GraphRelationshipType.RESPONDS_TO,
        evidence_reference="CMWSSB Action Taken Report ATR-2024-W65-01, dispatched to petitioner",
        source_document_id="DOC-ATR-2024-CMWSSB-01",
        matching_method=MatchingMethod.DIRECT_DOCUMENTARY,
        review_status=GraphReviewStatus.PENDING_REVIEW,
        is_test_fixture=True,
    )
    assert edge_doc is not None
    assert edge_doc.provenance_status == GraphProvenanceStatus.VALID

    # 3. Allow candidate when human-reviewed & verified
    edge_reviewed = GraphStorageService.add_evidence_edge(
        session=db_session,
        source_node_id="NODE:RESP:MAWS_ACTION",
        target_node_id="NODE:ISSUE:WATER_KOLATHUR",
        relationship_type=GraphRelationshipType.RELATES_TO,
        evidence_reference="Human auditor validated token resolution to ward grievance",
        source_document_id="DOC-REVIEW-AUDIT-01",
        matching_method=MatchingMethod.HUMAN_REVIEWED,
        review_status=GraphReviewStatus.VERIFIED,
        is_test_fixture=True,
    )
    assert edge_reviewed is not None
    assert edge_reviewed.review_status == GraphReviewStatus.VERIFIED


def test_5_epistemic_rule_2_promise_to_scheme_fulfillment_guardrail(db_session, seed_nodes):
    """
    Rule 2: A promise can relate to a scheme without automatically proving fulfillment.
    'implements' / fulfillment claims are rejected without documentary proof.
    """
    # 1. 'relates_to' is permitted without asserting fulfillment
    edge_relates = GraphStorageService.add_evidence_edge(
        session=db_session,
        source_node_id="NODE:PROM:BREAKFAST",
        target_node_id="NODE:SCHEME:BREAKFAST",
        relationship_type=GraphRelationshipType.RELATES_TO,
        evidence_reference="DMK Election Manifesto 2021 Item 314 shares policy objective with scheme",
        source_document_id="DOC-MAN-DMK-2021",
        is_test_fixture=True,
    )
    assert edge_relates.relationship_type == GraphRelationshipType.RELATES_TO

    # 2. Reject asserting 'implements' without documentary proof of fulfillment
    with pytest.raises(EpistemicRuleViolationError) as exc_info:
        GraphStorageService.add_evidence_edge(
            session=db_session,
            source_node_id="NODE:PROM:BREAKFAST",
            target_node_id="NODE:SCHEME:BREAKFAST",
            relationship_type=GraphRelationshipType.IMPLEMENTS,
            evidence_reference="Promised breakfast and scheme launched, so promise was implemented",
            source_document_id="DOC-MAN-DMK-2021",
            properties={"proof_of_fulfillment": False},
            is_test_fixture=True,
        )
    assert "cannot be asserted as 'implements'" in str(exc_info.value)
    assert "A promise relating to a scheme does not prove fulfillment" in str(exc_info.value)

    # 3. Allow 'implements' when supported by official Government Order & verified fulfillment proof
    edge_fulfilled = GraphStorageService.add_evidence_edge(
        session=db_session,
        source_node_id="NODE:PROM:BREAKFAST",
        target_node_id="NODE:SCHEME:BREAKFAST",
        relationship_type=GraphRelationshipType.IMPLEMENTS,
        evidence_reference="G.O. (Ms) No. 43, Social Welfare & Women Empowerment Dept dated 27.07.2022",
        source_document_id="DOC-GO-MS-43-SW-2022",
        properties={
            "proof_of_fulfillment": True,
            "government_order_number": "G.O. (Ms) No. 43",
            "expenditure_verified": True,
        },
        is_test_fixture=True,
    )
    assert edge_fulfilled.relationship_type == GraphRelationshipType.IMPLEMENTS


def test_6_epistemic_rule_3_funding_disclosure_identity_support(db_session, seed_nodes):
    """
    Rule 3: A funding disclosure can relate to a party or donor only when
    the identity match is supported.
    """
    # 1. Reject candidate match with low confidence (< 0.70) without review
    with pytest.raises(EpistemicRuleViolationError) as exc_info:
        GraphStorageService.add_evidence_edge(
            session=db_session,
            source_node_id="NODE:CONTRIB:EB_2023_01",
            target_node_id="NODE:DONOR:INFRA_CORP",
            relationship_type=GraphRelationshipType.RELATES_TO,
            evidence_reference="Fuzzy name similarity 'Infra Investments' -> 0.45",
            source_document_id="DOC-ECI-EB-2023",
            matching_method=MatchingMethod.AUTOMATED_CANDIDATE,
            confidence_score=0.45,
            review_status=GraphReviewStatus.PENDING_REVIEW,
            is_test_fixture=True,
        )
    assert "has insufficient confidence (0.45 < 0.70)" in str(exc_info.value)

    # 2. Reject explicitly flagged unsupported match
    with pytest.raises(EpistemicRuleViolationError) as exc_info:
        GraphStorageService.add_evidence_edge(
            session=db_session,
            source_node_id="NODE:CONTRIB:EB_2023_01",
            target_node_id="NODE:PARTY:DMK",
            relationship_type=GraphRelationshipType.FUNDS,
            evidence_reference="Uncertain receipt mapping",
            source_document_id="DOC-ECI-EB-2023",
            properties={"unsupported_match": True},
            is_test_fixture=True,
        )
    assert "is explicitly flagged as unsupported match" in str(exc_info.value)

    # 3. Allow when supported by deterministic ID or high-confidence match
    edge_funding = GraphStorageService.add_evidence_edge(
        session=db_session,
        source_node_id="NODE:CONTRIB:EB_2023_01",
        target_node_id="NODE:PARTY:DMK",
        relationship_type=GraphRelationshipType.FUNDS,
        evidence_reference="SBI Bond Redemption Serial #TL40283 matched to DMK Account in ECI Affidavit",
        source_document_id="DOC-ECI-AFFIDAVIT-DMK-2024",
        matching_method=MatchingMethod.DETERMINISTIC_ID,
        confidence_score=1.0,
        review_status=GraphReviewStatus.VERIFIED,
        is_test_fixture=True,
    )
    assert edge_funding.relationship_type == GraphRelationshipType.FUNDS
    assert edge_funding.confidence_score == 1.0


def test_7_epistemic_rule_4_claim_dialectical_supporting_and_contradicting_evidence(db_session, seed_nodes):
    """
    Rule 4: A claim can have supporting and contradicting evidence simultaneously.
    Both edges must coexist without throwing conflict errors.
    """
    # 1. Edge providing supporting evidence
    edge_pro = GraphStorageService.add_evidence_edge(
        session=db_session,
        source_node_id="NODE:DOC:DPI_REPORT",
        target_node_id="NODE:CLAIM:BREAKFAST_ATTENDANCE",
        relationship_type=GraphRelationshipType.PROVIDES_EVIDENCE_FOR,
        evidence_reference="Table 4.1: Average primary attendance rose from 73.2% to 91.4% post-launch",
        source_document_id="DOC-DPI-EVAL-2023",
        matching_method=MatchingMethod.DIRECT_DOCUMENTARY,
        is_test_fixture=True,
    )
    db_session.commit()

    # 2. Edge providing contradicting evidence
    edge_con = GraphStorageService.add_evidence_edge(
        session=db_session,
        source_node_id="NODE:DOC:CAG_AUDIT",
        target_node_id="NODE:CLAIM:BREAKFAST_ATTENDANCE",
        relationship_type=GraphRelationshipType.CONTRADICTS,
        evidence_reference="Paragraph 2.18: Baseline attendance registers in 4 districts show unadjusted seasonal variation; net gain estimated at only 4.2%",
        source_document_id="DOC-CAG-2023-EDUCATION",
        matching_method=MatchingMethod.DIRECT_DOCUMENTARY,
        is_test_fixture=True,
    )
    db_session.commit()

    # Both edges must exist simultaneously on the target claim node
    claim_incoming = GraphStorageService.get_node_edges(
        session=db_session,
        node_id="NODE:CLAIM:BREAKFAST_ATTENDANCE",
        direction="incoming",
    )
    assert len(claim_incoming) == 2
    rel_types = {e.relationship_type for e in claim_incoming}
    assert GraphRelationshipType.PROVIDES_EVIDENCE_FOR in rel_types
    assert GraphRelationshipType.CONTRADICTS in rel_types


def test_8_epistemic_rule_5_civic_issue_geographic_association_guardrail(db_session, seed_nodes):
    """
    Rule 5: A civic issue's geographic association does not establish
    an individual representative's responsibility.
    """
    # 1. Direct 'located_in' between civic issue and individual representative is rejected
    with pytest.raises(EpistemicRuleViolationError) as exc_info:
        GraphStorageService.add_evidence_edge(
            session=db_session,
            source_node_id="NODE:ISSUE:WATER_KOLATHUR",
            target_node_id="NODE:REP:STALIN",
            relationship_type=GraphRelationshipType.LOCATED_IN,
            evidence_reference="Issue occurred in MLA's constituency",
            source_document_id="DOC-NEWS-2024",
            is_test_fixture=True,
        )
    assert "cannot have relationship 'located_in' directly to an individual representative" in str(exc_info.value)

    # 2. Direct causal attribution or responsibility from mere geographic co-occurrence is rejected
    with pytest.raises(EpistemicRuleViolationError) as exc_info:
        GraphStorageService.add_evidence_edge(
            session=db_session,
            source_node_id="NODE:ISSUE:WATER_KOLATHUR",
            target_node_id="NODE:REP:STALIN",
            relationship_type=GraphRelationshipType.CONCERNS,
            evidence_reference="Water contamination located in Kolathur constituency",
            source_document_id="DOC-NEWS-2024",
            properties={"geographic_association_only": True},
            is_test_fixture=True,
        )
    assert "geographic co-occurrence within a constituency does not establish individual representative" in str(exc_info.value)

    # 3. Correct representation: Issue located in Constituency, Representative represents Constituency
    edge_issue_const = GraphStorageService.add_evidence_edge(
        session=db_session,
        source_node_id="NODE:ISSUE:WATER_KOLATHUR",
        target_node_id="NODE:CONST:KOLATHUR",
        relationship_type=GraphRelationshipType.LOCATED_IN,
        evidence_reference="Grievance GIS coordinates fall within Kolathur AC-013 boundary",
        source_document_id="DOC-GIS-BOUNDARY-2024",
        matching_method=MatchingMethod.DETERMINISTIC_ID,
        is_test_fixture=True,
    )
    edge_rep_const = GraphStorageService.add_evidence_edge(
        session=db_session,
        source_node_id="NODE:REP:STALIN",
        target_node_id="NODE:CONST:KOLATHUR",
        relationship_type=GraphRelationshipType.REPRESENTS,
        evidence_reference="ECI Form 21E Official Declaration of Result 2021",
        source_document_id="DOC-ECI-21E-2021-013",
        matching_method=MatchingMethod.DIRECT_DOCUMENTARY,
        is_test_fixture=True,
    )
    assert edge_issue_const.relationship_type == GraphRelationshipType.LOCATED_IN
    assert edge_rep_const.relationship_type == GraphRelationshipType.REPRESENTS


def test_9_reversible_edge_corrections_and_soft_reversals(db_session, seed_nodes):
    """
    Reversible link corrections: soft-reversal (RETRACTED, SUPERSEDED, RESTORED)
    and metadata corrections without deleting history or losing provenance.
    """
    edge = GraphStorageService.add_evidence_edge(
        session=db_session,
        source_node_id="NODE:DEPT:MAWS",
        target_node_id="NODE:SCHEME:BREAKFAST",
        relationship_type=GraphRelationshipType.RELATES_TO,
        evidence_reference="Preliminary departmental mention",
        source_document_id="DOC-TEMP-001",
        matching_method=MatchingMethod.AUTOMATED_CANDIDATE,
        confidence_score=0.80,
        valid_from="2022-01-01",
        is_test_fixture=True,
        performed_by="INGESTION_BOT",
    )
    db_session.commit()
    edge_id = edge.edge_id

    # 1. Verify initial audit record
    audit_records = GraphStorageService.get_edge_audit_records(db_session, edge_id)
    assert len(audit_records) == 1
    assert audit_records[0].operation_type == EdgeOperationType.CREATE

    # 2. Correct edge metadata (e.g. adjust valid_to and confidence)
    corrected = GraphStorageService.correct_edge(
        session=db_session,
        edge_id=edge_id,
        rationale="Audit confirmed exact fiscal year validity and primary documentary backing",
        performed_by="AUDITOR_KARTHIK",
        confidence_score=0.95,
        valid_to="2023-03-31",
        matching_method=MatchingMethod.HUMAN_REVIEWED,
    )
    db_session.commit()
    assert corrected.confidence_score == 0.95
    assert corrected.valid_to == "2023-03-31"

    # 3. Soft-reversal: Retract edge
    retracted = GraphStorageService.retract_edge(
        session=db_session,
        edge_id=edge_id,
        rationale="Source document DOC-TEMP-001 was replaced by official gazette notification",
        performed_by="AUDITOR_KARTHIK",
    )
    db_session.commit()
    assert retracted.provenance_status == GraphProvenanceStatus.RETRACTED

    # Active query should now exclude this retracted edge
    active_edges = GraphStorageService.get_node_edges(
        session=db_session,
        node_id="NODE:DEPT:MAWS",
        active_only=True,
    )
    assert not any(e.edge_id == edge_id for e in active_edges)

    # But row STILL EXISTS in database (never deleted!)
    edge_in_db = GraphStorageService.get_edge(db_session, edge_id)
    assert edge_in_db is not None
    assert edge_in_db.provenance_status == GraphProvenanceStatus.RETRACTED

    # 4. Reversible restore: Restore edge back to VALID
    restored = GraphStorageService.restore_edge(
        session=db_session,
        edge_id=edge_id,
        rationale="Retraction reversed after cross-verification with secondary gazette",
        performed_by="SENIOR_AUDITOR",
    )
    db_session.commit()
    assert restored.provenance_status == GraphProvenanceStatus.VALID

    # 5. Supersede edge with a new edge ID
    superseded = GraphStorageService.supersede_edge(
        session=db_session,
        old_edge_id=edge_id,
        new_edge_id="EDGE:FUNDS:NODE:DEPT:MAWS:NODE:SCHEME:BREAKFAST:DOC_OFFICIAL_GAZETTE",
        rationale="Superseded by definitive gazette edge",
        performed_by="SENIOR_AUDITOR",
    )
    db_session.commit()
    assert superseded.provenance_status == GraphProvenanceStatus.SUPERSEDED

    # 6. Verify complete audit trail retains all 5 lifecycle operations
    audit_history = GraphStorageService.get_edge_audit_records(db_session, edge_id)
    assert len(audit_history) == 5
    op_sequence = [r.operation_type for r in audit_history]
    assert op_sequence == [
        EdgeOperationType.CREATE,
        EdgeOperationType.CORRECT,
        EdgeOperationType.RETRACT,
        EdgeOperationType.RESTORE,
        EdgeOperationType.SUPERSEDE,
    ]
    for r in audit_history:
        assert r.rationale is not None
        assert r.performed_by is not None
        assert r.timestamp is not None


def test_10_canonical_entity_linking_and_traversal(db_session, seed_nodes):
    """
    Validates canonical entity foreign key linkage on nodes and
    bidirectional edge querying with temporal filtering.
    """
    node = GraphStorageService.get_node(db_session, "NODE:DEPT:MAWS")
    assert node.canonical_entity_id == "CANON:DEPT:MAWS"

    # Add edges with temporal ranges
    e1 = GraphStorageService.add_evidence_edge(
        session=db_session,
        source_node_id="NODE:DEPT:MAWS",
        target_node_id="NODE:SCHEME:BREAKFAST",
        relationship_type=GraphRelationshipType.FUNDS,
        evidence_reference="Budget Demand 34 FY2022-23",
        source_document_id="DOC-BUD-22-23",
        valid_from="2022-04-01",
        valid_to="2023-03-31",
        is_test_fixture=True,
    )
    e2 = GraphStorageService.add_evidence_edge(
        session=db_session,
        source_node_id="NODE:DEPT:MAWS",
        target_node_id="NODE:SCHEME:BREAKFAST",
        relationship_type=GraphRelationshipType.IMPLEMENTS,
        evidence_reference="MAWS Annual Administrative Report 2023-24",
        source_document_id="DOC-ADMIN-23-24",
        valid_from="2023-04-01",
        valid_to="2024-03-31",
        is_test_fixture=True,
    )
    db_session.commit()

    # Query outgoing
    outgoing = GraphStorageService.get_node_edges(db_session, "NODE:DEPT:MAWS", direction="outgoing")
    assert len(outgoing) == 2

    # Query incoming on scheme
    incoming = GraphStorageService.get_node_edges(db_session, "NODE:SCHEME:BREAKFAST", direction="incoming")
    assert len(incoming) == 2

    # Query specific relationship
    funds_only = GraphStorageService.get_node_edges(
        db_session,
        "NODE:DEPT:MAWS",
        direction="outgoing",
        relationship_type=GraphRelationshipType.FUNDS,
    )
    assert len(funds_only) == 1
    assert funds_only[0].valid_from == "2022-04-01"
    assert funds_only[0].valid_to == "2023-03-31"
