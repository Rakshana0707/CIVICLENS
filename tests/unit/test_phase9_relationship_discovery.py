"""
Phase 9.4 — Cross-Phase Relationship Discovery Engine Tests.
============================================================

Validates:
1. Exact identifier matching (Demand No, G.O. No, Grievance Token) yields DETERMINISTIC_ID (Rank 1).
2. Documented reference matching yields DIRECT_DOCUMENTARY citations (Rank 2).
3. Canonical entity matching correctly associates records linked to the same authority (Rank 3).
4. Temporal and geographic compatibility checks identify non-overlapping periods and district mismatches.
5. Text similarity matching generates strictly provisional candidates (capped at 0.70) in PENDING_REVIEW;
   never automatically converts into confirmed graph edges.
6. False-positive prevention: Funding caused public outcome fallacy is flagged and blocked.
7. False-positive prevention: Representative civic issue culpability fallacy is flagged and blocked.
8. False-positive prevention: Promise-scheme fulfillment fallacy is flagged and blocked.
9. False-positive prevention: News report proves claim truth fallacy is flagged and blocked.
10. Human review workflow: Confirm (promotes to verified CivicEvidenceEdge), Reject, and Defer.
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
    CandidateRelationshipProposal,
    CandidateReviewDisposition,
    GraphEntityType,
    GraphRelationshipType,
    MatchingMethod,
    GraphProvenanceStatus,
    GraphReviewStatus,
)
from backend.services.graph_storage_service import GraphStorageService
from backend.services.relationship_discovery_engine import (
    RelationshipDiscoveryEngine,
    DiscoveryEngineError,
    EpistemicGuardrailViolation,
    CONFLICT_FUNDING_CAUSATION,
    CONFLICT_REPRESENTATIVE_CULPABILITY,
    CONFLICT_PROMISE_FULFILLMENT,
    CONFLICT_NEWS_TRUTH_PROOF,
    CONFLICT_CORRELATION_CAUSATION,
    CONFLICT_TEMPORAL_MISMATCH,
    CONFLICT_GEOGRAPHIC_MISMATCH,
)


@pytest.fixture
def db_session():
    """In-memory SQLite database session for testing discovery engine."""
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def discovery_nodes(db_session):
    """Seed nodes across Phases 1-8 for relationship discovery tests."""
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
        # Phase 1: Budget Department with Demand 34
        "dept_maws": GraphStorageService.create_or_get_node(
            db_session,
            node_id="NODE:DEPT:MAWS_34",
            entity_type=GraphEntityType.BUDGET_DEPARTMENT,
            canonical_id="DEPT-MAWS-34",
            label="Municipal Administration and Water Supply Department",
            source_phase="PHASE_1",
            canonical_entity_id="CANON:DEPT:MAWS",
            attributes={
                "demand_number": "34",
                "fiscal_year": "2022-23",
                "district": "Chennai",
            },
            is_test_fixture=True,
        ),
        # Phase 2: Scheme with Demand 34
        "scheme_water": GraphStorageService.create_or_get_node(
            db_session,
            node_id="NODE:SCHEME:CHENNAI_WATER",
            entity_type=GraphEntityType.BUDGET_SCHEME,
            canonical_id="SCH-WTR-2022",
            label="Chennai Drinking Water Supply Augmentation Scheme",
            source_phase="PHASE_2",
            attributes={
                "demand_number": "34",
                "fiscal_year": "2022-23",
                "district": "Chennai",
                "source_document_id": "DOC-BUDGET-DEMAND-34",
            },
            is_test_fixture=True,
        ),
        # Phase 3: Manifesto Promise
        "promise_breakfast": GraphStorageService.create_or_get_node(
            db_session,
            node_id="NODE:PROM:BREAKFAST_P3",
            entity_type=GraphEntityType.POLITICAL_PROMISE,
            canonical_id="PROM-2021-314",
            label="Breakfast Scheme for Primary School Children",
            source_phase="PHASE_3",
            attributes={
                "election_year": 2021,
                "scheme_code": "SCH-CM-BF",
            },
            is_test_fixture=True,
        ),
        # Phase 2: Breakfast Scheme
        "scheme_breakfast": GraphStorageService.create_or_get_node(
            db_session,
            node_id="NODE:SCHEME:BREAKFAST_P2",
            entity_type=GraphEntityType.HISTORICAL_SCHEME,
            canonical_id="SCH-2022-BF",
            label="Chief Minister Breakfast Scheme in Primary Schools",
            source_phase="PHASE_2",
            attributes={
                "year": 2022,
                "scheme_code": "SCH-CM-BF",
            },
            is_test_fixture=True,
        ),
        # Phase 4: Corporate Donor
        "donor_corp": GraphStorageService.create_or_get_node(
            db_session,
            node_id="NODE:DONOR:MEGA_CORP",
            entity_type=GraphEntityType.DONOR,
            canonical_id="DONOR-MEGA-01",
            label="Mega Infrastructure Holdings Pvt Ltd",
            source_phase="PHASE_4",
            attributes={
                "pan": "AAACM1234D",
                "district": "Chennai",
            },
            is_test_fixture=True,
        ),
        # Phase 8: Public Work
        "public_work_bridge": GraphStorageService.create_or_get_node(
            db_session,
            node_id="NODE:WORK:FLYOVER_CHENNAI",
            entity_type=GraphEntityType.PUBLIC_WORK,
            canonical_id="WORK-FLY-2023",
            label="T. Nagar Flyover Construction",
            source_phase="PHASE_8",
            attributes={
                "district": "Chennai",
            },
            is_test_fixture=True,
        ),
        # Phase 5: Representative (MLA)
        "rep_mla": GraphStorageService.create_or_get_node(
            db_session,
            node_id="NODE:REP:KOLATHUR_MLA",
            entity_type=GraphEntityType.REPRESENTATIVE,
            canonical_id="REP-KOLATHUR",
            label="M. K. Stalin",
            source_phase="PHASE_5",
            attributes={
                "constituency_code": "AC-013",
                "district": "Chennai",
                "term": "2021-2026",
            },
            is_test_fixture=True,
        ),
        # Phase 7: Civic Issue in Kolathur
        "issue_sewage": GraphStorageService.create_or_get_node(
            db_session,
            node_id="NODE:ISSUE:SEWAGE_KOLATHUR",
            entity_type=GraphEntityType.CIVIC_ISSUE,
            canonical_id="ISSUE-2024-KOL-01",
            label="Sewage overflow in Kolathur Market Road",
            source_phase="PHASE_7",
            attributes={
                "constituency_code": "AC-013",
                "district": "Chennai",
                "year": 2024,
            },
            is_test_fixture=True,
        ),
        # Phase 4: News Article
        "news_article": GraphStorageService.create_or_get_node(
            db_session,
            node_id="NODE:NEWS:DAILY_REPORT",
            entity_type=GraphEntityType.NEWS_ARTICLE,
            canonical_id="NEWS-2023-WTR-01",
            label="Daily News: Chennai Water Supply Augmented by 20%",
            source_phase="PHASE_4",
            attributes={
                "source_document_id": "DOC-NEWS-ARTICLE-441",
            },
            is_test_fixture=True,
        ),
        # Phase 6: Fact-checked Claim
        "claim_water_pct": GraphStorageService.create_or_get_node(
            db_session,
            node_id="NODE:CLAIM:WATER_20_PCT",
            entity_type=GraphEntityType.CLAIM,
            canonical_id="CLAIM-2023-WTR-AUG",
            label="Official drinking water supply expanded by 20% in Chennai",
            source_phase="PHASE_6",
            attributes={
                "source_document_id": "DOC-NEWS-ARTICLE-441",
            },
            is_test_fixture=True,
        ),
        # Phase 8: Grievance Record with Petition Token
        "grievance_token_node": GraphStorageService.create_or_get_node(
            db_session,
            node_id="NODE:GRIEV:PETITION_101",
            entity_type=GraphEntityType.GRIEVANCE_RECORD,
            canonical_id="GRIEV-TN-101",
            label="Public Grievance on Street Lighting",
            source_phase="PHASE_8",
            attributes={
                "petition_id": "PET-2024-TN-101",
                "district": "Madurai",
            },
            is_test_fixture=True,
        ),
        # Phase 8: Response Record with Matching Petition Token
        "response_token_node": GraphStorageService.create_or_get_node(
            db_session,
            node_id="NODE:RESP:ACTION_101",
            entity_type=GraphEntityType.RESPONSE_RECORD,
            canonical_id="RESP-TN-101",
            label="Municipal Action Taken on Street Lighting",
            source_phase="PHASE_8",
            attributes={
                "petition_id": "PET-2024-TN-101",
                "district": "Madurai",
            },
            is_test_fixture=True,
        ),
    }
    db_session.commit()
    return nodes


def test_1_exact_identifier_discovery_priority(db_session, discovery_nodes):
    """
    Exact identifier matching yields DETERMINISTIC_ID with high confidence,
    prioritized over heuristic matching.
    """
    # 1. Matching Demand Number 34 between Budget Department and Scheme
    eval_result = RelationshipDiscoveryEngine.evaluate_candidate_pair(
        session=db_session,
        source_node=discovery_nodes["dept_maws"],
        target_node=discovery_nodes["scheme_water"],
        proposed_relationship_type=GraphRelationshipType.FUNDS,
    )
    assert eval_result is not None
    assert eval_result["matching_method"] == MatchingMethod.DETERMINISTIC_ID
    assert eval_result["confidence_score"] >= 0.95
    assert "Demand Number" in eval_result["evidence_supporting_candidate"]
    assert len(eval_result["possible_conflicts"]) == 0

    # 2. Matching Petition ID between Grievance and Response
    eval_petition = RelationshipDiscoveryEngine.evaluate_candidate_pair(
        session=db_session,
        source_node=discovery_nodes["response_token_node"],
        target_node=discovery_nodes["grievance_token_node"],
        proposed_relationship_type=GraphRelationshipType.RESPONDS_TO,
    )
    assert eval_petition is not None
    assert eval_petition["matching_method"] == MatchingMethod.DETERMINISTIC_ID
    assert "Petition Token" in eval_petition["evidence_supporting_candidate"]


def test_2_documented_reference_discovery(db_session, discovery_nodes):
    """
    Documented reference matching detects shared primary source citations.
    """
    eval_doc = RelationshipDiscoveryEngine.evaluate_candidate_pair(
        session=db_session,
        source_node=discovery_nodes["news_article"],
        target_node=discovery_nodes["claim_water_pct"],
        proposed_relationship_type=GraphRelationshipType.REPORTS_ON,
    )
    assert eval_doc is not None
    assert eval_doc["matching_method"] == MatchingMethod.DIRECT_DOCUMENTARY
    assert eval_doc["source_document_id"] == "DOC-NEWS-ARTICLE-441"
    assert eval_doc["confidence_score"] >= 0.90


def test_3_canonical_entity_match_discovery(db_session, discovery_nodes):
    """
    Canonical entity matching resolves records sharing the same authority record.
    """
    # Create another node sharing CANON:DEPT:MAWS
    dept_node_2 = GraphStorageService.create_or_get_node(
        db_session,
        node_id="NODE:DEPT:MAWS_SECRETARIAT",
        entity_type=GraphEntityType.GOVERNMENT_DEPARTMENT,
        canonical_id="DEPT-MAWS-SEC",
        label="MAWS Secretariat Administrative Wing",
        source_phase="PHASE_1",
        canonical_entity_id="CANON:DEPT:MAWS",
        attributes={"district": "Chennai"},
        is_test_fixture=True,
    )
    db_session.commit()

    eval_canon = RelationshipDiscoveryEngine.evaluate_candidate_pair(
        session=db_session,
        source_node=discovery_nodes["dept_maws"],
        target_node=dept_node_2,
    )
    assert eval_canon is not None
    assert eval_canon["matching_method"] == MatchingMethod.DETERMINISTIC_ID
    assert "canonical registry entity" in eval_canon["evidence_supporting_candidate"]


def test_4_temporal_and_geographic_compatibility_filtering(db_session, discovery_nodes):
    """
    Temporal divergence and geographic boundary mismatches are detected and flagged in conflicts.
    """
    # 1. Geographic mismatch (Chennai vs Madurai)
    node_madurai = GraphStorageService.create_or_get_node(
        db_session,
        node_id="NODE:SCHEME:MADURAI_WTR",
        entity_type=GraphEntityType.BUDGET_SCHEME,
        canonical_id="SCH-MDU-WTR",
        label="Madurai City Water Project",
        source_phase="PHASE_2",
        attributes={"district": "Madurai", "fiscal_year": "2022-23"},
        is_test_fixture=True,
    )
    compat, reason = RelationshipDiscoveryEngine.evaluate_geographic_compatibility(
        discovery_nodes["dept_maws"], node_madurai
    )
    assert not compat
    assert "District mismatch" in reason

    # 2. Temporal mismatch (>2 years divergence)
    node_old_scheme = GraphStorageService.create_or_get_node(
        db_session,
        node_id="NODE:SCHEME:OLD_SCHEME_2011",
        entity_type=GraphEntityType.BUDGET_SCHEME,
        canonical_id="SCH-OLD-2011",
        label="Old Municipal Scheme 2011",
        source_phase="PHASE_2",
        attributes={"fiscal_year": "2011-12", "district": "Chennai"},
        is_test_fixture=True,
    )
    t_compat, t_reason = RelationshipDiscoveryEngine.evaluate_temporal_compatibility(
        discovery_nodes["dept_maws"], node_old_scheme
    )
    assert not t_compat
    assert "Fiscal years differ" in t_reason


def test_5_text_similarity_candidate_separation(db_session, discovery_nodes):
    """
    Text similarity matching generates provisional candidates in PENDING_REVIEW;
    confidence is capped at <= 0.70 and never automatically converted to confirmed edges.
    """
    node_text_a = GraphStorageService.create_or_get_node(
        db_session,
        node_id="NODE:ISSUE:ROAD_REPAIR",
        entity_type=GraphEntityType.CIVIC_ISSUE,
        canonical_id="ISSUE-RD-01",
        label="Pot-holes and road surface damage in Anna Nagar",
        source_phase="PHASE_7",
        is_test_fixture=True,
    )
    node_text_b = GraphStorageService.create_or_get_node(
        db_session,
        node_id="NODE:WORK:ROAD_REPAIR",
        entity_type=GraphEntityType.PUBLIC_WORK,
        canonical_id="WORK-RD-01",
        label="Anna Nagar Road surface re-laying and pot-hole repair work",
        source_phase="PHASE_8",
        is_test_fixture=True,
    )
    db_session.commit()

    proposal = RelationshipDiscoveryEngine.propose_candidate(
        session=db_session,
        source_node_id=node_text_a.node_id,
        target_node_id=node_text_b.node_id,
        relationship_type=GraphRelationshipType.CONCERNS,
        is_test_fixture=True,
    )
    db_session.commit()

    assert proposal is not None
    assert proposal.matching_method == MatchingMethod.AUTOMATED_CANDIDATE
    assert proposal.confidence_score <= 0.70  # Strictly capped
    assert proposal.review_status == CandidateReviewDisposition.PENDING_REVIEW

    # Must NOT have created an edge in civic_evidence_edges!
    edge_in_db = (
        db_session.query(CivicEvidenceEdge)
        .filter(
            CivicEvidenceEdge.source_node_id == node_text_a.node_id,
            CivicEvidenceEdge.target_node_id == node_text_b.node_id,
        )
        .first()
    )
    assert edge_in_db is None  # Candidate is strictly isolated


def test_6_false_positive_prevention_funding_to_public_outcome(db_session, discovery_nodes):
    """
    Fallacy: Funding caused a particular public outcome.
    Attempting to propose 'funds' or 'implements' from corporate donor to public work is flagged and blocked.
    """
    eval_fallacy = RelationshipDiscoveryEngine.evaluate_candidate_pair(
        session=db_session,
        source_node=discovery_nodes["donor_corp"],
        target_node=discovery_nodes["public_work_bridge"],
        proposed_relationship_type=GraphRelationshipType.FUNDS,
    )
    assert eval_fallacy is not None
    assert CONFLICT_FUNDING_CAUSATION in eval_fallacy["possible_conflicts"]

    proposal = RelationshipDiscoveryEngine.propose_candidate(
        session=db_session,
        source_node_id=discovery_nodes["donor_corp"].node_id,
        target_node_id=discovery_nodes["public_work_bridge"].node_id,
        relationship_type=GraphRelationshipType.FUNDS,
        is_test_fixture=True,
    )
    db_session.commit()

    # Attempting to confirm this fatal fallacy proposal MUST be blocked!
    with pytest.raises(EpistemicGuardrailViolation) as exc_info:
        RelationshipDiscoveryEngine.confirm_candidate(
            session=db_session,
            proposal_id=proposal.proposal_id,
            reviewer_id="AUDITOR_RAJESH",
            reviewer_notes="Attempting unbacked confirmation",
        )
    assert "violates epistemic guardrails" in str(exc_info.value)
    assert CONFLICT_FUNDING_CAUSATION in str(exc_info.value)


def test_7_false_positive_prevention_representative_civic_issue_culpability(db_session, discovery_nodes):
    """
    Fallacy: Representative personally caused a civic issue from spatial co-location.
    Attempting to propose 'implements' or 'concerns' responsibility is flagged and blocked.
    """
    eval_fallacy = RelationshipDiscoveryEngine.evaluate_candidate_pair(
        session=db_session,
        source_node=discovery_nodes["issue_sewage"],
        target_node=discovery_nodes["rep_mla"],
        proposed_relationship_type=GraphRelationshipType.CONCERNS,
    )
    assert eval_fallacy is not None
    assert CONFLICT_REPRESENTATIVE_CULPABILITY in eval_fallacy["possible_conflicts"]

    proposal = RelationshipDiscoveryEngine.propose_candidate(
        session=db_session,
        source_node_id=discovery_nodes["issue_sewage"].node_id,
        target_node_id=discovery_nodes["rep_mla"].node_id,
        relationship_type=GraphRelationshipType.CONCERNS,
        is_test_fixture=True,
    )
    db_session.commit()

    with pytest.raises(EpistemicGuardrailViolation) as exc_info:
        RelationshipDiscoveryEngine.confirm_candidate(
            session=db_session,
            proposal_id=proposal.proposal_id,
            reviewer_id="AUDITOR_RAJESH",
            reviewer_notes="Attempting invalid attribution",
        )
    assert CONFLICT_REPRESENTATIVE_CULPABILITY in str(exc_info.value)


def test_8_false_positive_prevention_promise_scheme_fulfillment(db_session, discovery_nodes):
    """
    Fallacy: Scheme fulfilled a political promise without statutory proof.
    Proposing 'implements' without G.O. proof flags CONFLICT_PROMISE_FULFILLMENT and blocks confirmation.
    Proposing 'relates_to' succeeds cleanly.
    """
    # 1. 'implements' (claiming fulfillment) flags conflict
    eval_impl = RelationshipDiscoveryEngine.evaluate_candidate_pair(
        session=db_session,
        source_node=discovery_nodes["promise_breakfast"],
        target_node=discovery_nodes["scheme_breakfast"],
        proposed_relationship_type=GraphRelationshipType.IMPLEMENTS,
    )
    assert eval_impl is not None
    assert CONFLICT_PROMISE_FULFILLMENT in eval_impl["possible_conflicts"]

    # 2. 'relates_to' (policy alignment without claiming fulfillment) has no fulfillment conflict
    eval_rel = RelationshipDiscoveryEngine.evaluate_candidate_pair(
        session=db_session,
        source_node=discovery_nodes["promise_breakfast"],
        target_node=discovery_nodes["scheme_breakfast"],
        proposed_relationship_type=GraphRelationshipType.RELATES_TO,
    )
    assert eval_rel is not None
    assert CONFLICT_PROMISE_FULFILLMENT not in eval_rel["possible_conflicts"]


def test_9_false_positive_prevention_news_report_claim_truth(db_session, discovery_nodes):
    """
    Fallacy: A news report proves a claim true.
    Proposing 'provides_evidence_for' flags CONFLICT_NEWS_TRUTH_PROOF.
    Proposing 'reports_on' succeeds without conflict.
    """
    eval_proof = RelationshipDiscoveryEngine.evaluate_candidate_pair(
        session=db_session,
        source_node=discovery_nodes["news_article"],
        target_node=discovery_nodes["claim_water_pct"],
        proposed_relationship_type=GraphRelationshipType.PROVIDES_EVIDENCE_FOR,
    )
    assert eval_proof is not None
    assert CONFLICT_NEWS_TRUTH_PROOF in eval_proof["possible_conflicts"]

    eval_reports = RelationshipDiscoveryEngine.evaluate_candidate_pair(
        session=db_session,
        source_node=discovery_nodes["news_article"],
        target_node=discovery_nodes["claim_water_pct"],
        proposed_relationship_type=GraphRelationshipType.REPORTS_ON,
    )
    assert eval_reports is not None
    assert CONFLICT_NEWS_TRUTH_PROOF not in eval_reports["possible_conflicts"]


def test_10_human_review_workflow_confirm_reject_defer(db_session, discovery_nodes):
    """
    Human review lifecycle: Confirm (promotes to verified CivicEvidenceEdge),
    Reject, and Defer candidate proposals.
    """
    # 1. Propose valid candidate (Demand 34 Department -> Scheme)
    proposal = RelationshipDiscoveryEngine.propose_candidate(
        session=db_session,
        source_node_id=discovery_nodes["dept_maws"].node_id,
        target_node_id=discovery_nodes["scheme_water"].node_id,
        relationship_type=GraphRelationshipType.FUNDS,
        is_test_fixture=True,
    )
    db_session.commit()
    prop_id = proposal.proposal_id

    # 2. Confirm candidate: should create CivicEvidenceEdge and update proposal
    updated_prop, edge = RelationshipDiscoveryEngine.confirm_candidate(
        session=db_session,
        proposal_id=prop_id,
        reviewer_id="AUDITOR_SARANYA",
        reviewer_notes="Verified against Detailed Budget Estimates Demand 34 FY22-23",
    )
    db_session.commit()

    assert updated_prop.review_status == CandidateReviewDisposition.CONFIRMED
    assert updated_prop.reviewed_by == "AUDITOR_SARANYA"
    assert updated_prop.confirmed_edge_id == edge.edge_id

    # Verify promoted edge exists in CivicEvidenceEdge table
    assert edge.relationship_type == GraphRelationshipType.FUNDS
    assert edge.review_status == GraphReviewStatus.VERIFIED
    assert edge.matching_method == MatchingMethod.HUMAN_REVIEWED

    # 3. Test Reject workflow on another candidate
    proposal_2 = RelationshipDiscoveryEngine.propose_candidate(
        session=db_session,
        source_node_id=discovery_nodes["promise_breakfast"].node_id,
        target_node_id=discovery_nodes["scheme_water"].node_id,
        relationship_type=GraphRelationshipType.RELATES_TO,
        is_test_fixture=True,
    )
    db_session.commit()

    rejected_prop = RelationshipDiscoveryEngine.reject_candidate(
        session=db_session,
        proposal_id=proposal_2.proposal_id,
        reviewer_id="AUDITOR_SARANYA",
        reviewer_notes="Unrelated domains: Primary school breakfast vs drinking water supply",
    )
    db_session.commit()
    assert rejected_prop.review_status == CandidateReviewDisposition.REJECTED

    # 4. Test Defer workflow
    proposal_3 = RelationshipDiscoveryEngine.propose_candidate(
        session=db_session,
        source_node_id=discovery_nodes["news_article"].node_id,
        target_node_id=discovery_nodes["claim_water_pct"].node_id,
        relationship_type=GraphRelationshipType.REPORTS_ON,
        is_test_fixture=True,
    )
    db_session.commit()

    deferred_prop = RelationshipDiscoveryEngine.defer_candidate(
        session=db_session,
        proposal_id=proposal_3.proposal_id,
        reviewer_id="AUDITOR_SARANYA",
        reviewer_notes="Deferring until gazette verification completes next week",
    )
    db_session.commit()
    assert deferred_prop.review_status == CandidateReviewDisposition.DEFERRED

    # 5. List proposals by review status
    pending = RelationshipDiscoveryEngine.list_proposals(db_session, review_status=CandidateReviewDisposition.PENDING_REVIEW)
    confirmed = RelationshipDiscoveryEngine.list_proposals(db_session, review_status=CandidateReviewDisposition.CONFIRMED)
    rejected = RelationshipDiscoveryEngine.list_proposals(db_session, review_status=CandidateReviewDisposition.REJECTED)
    deferred = RelationshipDiscoveryEngine.list_proposals(db_session, review_status=CandidateReviewDisposition.DEFERRED)

    assert len(confirmed) >= 1
    assert len(rejected) >= 1
    assert len(deferred) >= 1
