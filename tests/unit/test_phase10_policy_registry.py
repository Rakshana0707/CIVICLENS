"""
Phase 10.3 — Policy Registry and Evaluation Plan Builder Unit Tests.
====================================================================

Validates:
1. PolicyRegistryEntry persistence with all 11 required fields.
2. Canonical linkage to existing Phase 1 (BudgetScheme), Phase 2 (HistoricalScheme),
   and Phase 3 (PoliticalPromise) models, and rejection of unlinked policies.
3. Policy alias and Tamil/English name resolution.
4. Ambiguous objective handling: verbatim preservation of original wording and review flagging.
5. Target provenance separation: OFFICIALLY_STATED vs ANALYST_PROPOSED_BENCHMARK vs NO_PUBLISHED_TARGET.
6. Zero-target-invention guardrail: rejection of official targets lacking source reference
   and rejection of numeric values under NO_PUBLISHED_TARGET.
7. PolicyEvaluationPlan creation and validation of all 11 required plan attributes.
8. Plan assessment summary computation and epistemic labeling.
9. Synchronization of PolicyRegistryEntry and PolicyEvaluationPlan with the Unified Evidence Graph.
10. Zero-fabrication compliance (is_test_fixture=True on all fixtures).
"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.database.base_class import Base
from backend.models.budget import BudgetDepartment, BudgetScheme, HistoricalScheme
from backend.models.manifesto import Manifesto, ManifestoDocument, ManifestoSource
from backend.models.promise import PoliticalPromise
from backend.models.policy_evaluation import (
    PolicyRegistryEntry,
    PolicyObjective,
    PolicyIndicator,
    PolicyEvaluationPlan,
    PolicyEvaluationStatus,
    TargetProvenanceType,
    ObjectiveReviewStatus,
    EvaluationType,
    IndicatorType,
)
from backend.models.graph import (
    CivicGraphNode,
    CivicEvidenceEdge,
    GraphEntityType,
    GraphRelationshipType,
)
from backend.services.policy_registry_service import PolicyRegistryService
from tests.fixtures.phase10_fixtures import (
    get_phase10_sample_objectives,
    get_phase10_sample_indicators,
    get_phase10_sample_registry_entries,
    get_phase10_sample_evaluation_plans,
)


@pytest.fixture
def db_session():
    """In-memory SQLite session for testing Phase 10.3 Policy Registry and Plan Builder."""
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    try:
        yield session
    finally:
        session.close()


def test_1_policy_registry_full_attributes_and_persistence(db_session):
    """Verify PolicyRegistryEntry stores all 11 required policy attributes."""
    entries = get_phase10_sample_registry_entries()
    pudhumai_data = entries[0]

    entry = PolicyRegistryService.register_policy(db_session, **pudhumai_data)

    assert entry.policy_id == "POL-TEST-PUDHUMAI-PENN"
    assert entry.canonical_scheme_code == "SCH-TEST-PUDHUMAI-PENN"
    assert "Pudhumai Penn" in entry.policy_name
    assert "புதுமைப் பெண்" in entry.policy_name_ta
    assert "Pudhumai Penn" in entry.aliases
    assert entry.responsible_department == "Social Welfare and Women Empowerment Department"
    assert "monthly ₹1,000" in entry.objectives_summary
    assert "Provide ₹1,000 per month directly" in entry.original_objective_wording
    assert entry.is_objective_ambiguous is False
    assert entry.objective_review_status == ObjectiveReviewStatus.VERIFIED_CLEAR
    assert "Classes 6–12" in entry.intended_beneficiaries
    assert entry.geographic_scope == "STATEWIDE"
    assert entry.start_date == "2022-09-05"
    assert entry.end_date is None
    assert entry.implementation_rules["monthly_amount_inr"] == 1000
    assert len(entry.stated_targets) == 2
    assert "DOC-TEST-GO-SW-55-2022" in entry.source_documents
    assert entry.evaluation_status == PolicyEvaluationStatus.EVALUATED
    assert entry.is_test_fixture is True

    serialized = entry.to_dict()
    assert serialized["policy_id"] == "POL-TEST-PUDHUMAI-PENN"
    assert serialized["objective_review_status"] == "VERIFIED_CLEAR"


def test_2_canonical_linkage_to_phase1_phase2_phase3_models(db_session):
    """
    Verify that PolicyRegistryEntry integrates directly with existing Phase 1 (BudgetScheme),
    Phase 2 (HistoricalScheme), and Phase 3 (PoliticalPromise) models, and rejects unlinked records.
    """
    # Seed Phase 1 BudgetDepartment and BudgetScheme
    dept = BudgetDepartment(name="Higher Education Department", code="DEMAND-20")
    db_session.add(dept)
    db_session.flush()

    b_scheme = BudgetScheme(
        department_id=dept.id,
        name="Pudhumai Penn Higher Education Assurance",
        head_of_account="2202-03-102-AA",
        normalized_category="Higher Education",
    )
    db_session.add(b_scheme)
    db_session.flush()

    # Seed Phase 2 HistoricalScheme
    h_scheme = HistoricalScheme(
        original_source_identifier="HIST-SCH-PUDHUMAI-2022",
        budget_scheme_id=b_scheme.id,
        department_id=dept.id,
        financial_year="2022-23",
        scheme_name="Pudhumai Penn Scheme",
        objectives="Provide ₹1,000 monthly assistance to 500,000 government school girls in college.",
        target_beneficiaries="Girl students from government schools (Classes 6-12).",
    )
    db_session.add(h_scheme)
    db_session.commit()

    # Register policy using Phase 1 & Phase 2 IDs — fields auto-populate from canonical entities
    policy = PolicyRegistryService.register_policy(
        db_session,
        policy_id="POL-TEST-CANONICAL-LINK-01",
        policy_name="Pudhumai Penn Canonical Linked Policy",
        budget_scheme_id=b_scheme.id,
        historical_scheme_id=h_scheme.id,
        is_test_fixture=True,
    )

    assert policy.budget_scheme_id == b_scheme.id
    assert policy.historical_scheme_id == h_scheme.id
    assert policy.department_id == dept.id
    assert policy.responsible_department == "Higher Education Department"
    assert "500,000" in policy.original_objective_wording
    assert "Girl students" in policy.intended_beneficiaries

    # Reject registration when no canonical scheme code or Phase 1-3 FK is provided
    with pytest.raises(ValueError, match="canonical scheme or policy entity"):
        PolicyRegistryService.register_policy(
            db_session,
            policy_id="POL-TEST-UNLINKED-FAIL",
            policy_name="Orphan Unlinked Policy",
            objectives_summary="Some objective",
            intended_beneficiaries="Some beneficiaries",
            is_test_fixture=True,
        )


def test_3_policy_alias_and_bilingual_resolution(db_session):
    """Verify policy lookup by policy_id, canonical_scheme_code, Tamil name, and alias."""
    for entry_data in get_phase10_sample_registry_entries():
        PolicyRegistryService.register_policy(db_session, **entry_data)

    by_id = PolicyRegistryService.resolve_policy(db_session, "POL-TEST-PUDHUMAI-PENN")
    assert by_id is not None

    by_code = PolicyRegistryService.resolve_policy(db_session, "SCH-TEST-PUDHUMAI-PENN")
    assert by_code is not None and by_code.policy_id == "POL-TEST-PUDHUMAI-PENN"

    by_alias = PolicyRegistryService.resolve_policy(db_session, "pudhumai penn")
    assert by_alias is not None and by_alias.policy_id == "POL-TEST-PUDHUMAI-PENN"

    by_tamil = PolicyRegistryService.resolve_policy(db_session, "புதுமைப் பெண்")
    assert by_tamil is not None and by_tamil.policy_id == "POL-TEST-PUDHUMAI-PENN"


def test_4_ambiguous_objective_wording_preservation_and_flagging(db_session):
    """
    Verify that when objectives are ambiguous, the exact original wording is preserved
    and the record is automatically flagged for human review.
    """
    entries = get_phase10_sample_registry_entries()
    ambig_data = entries[1]  # POL-TEST-AMBIGUOUS-RURAL-VISION

    entry = PolicyRegistryService.register_policy(db_session, **ambig_data)

    # Exact original wording must be preserved verbatim
    assert entry.original_objective_wording == (
        "To usher in a world-class holistic transformation and overall upliftment of rural life "
        "through seamless empowerment across villages."
    )
    # Must be automatically flagged as ambiguous
    assert entry.is_objective_ambiguous is True
    assert entry.objective_review_status == ObjectiveReviewStatus.FLAGGED_AMBIGUOUS
    assert entry.evaluation_status == PolicyEvaluationStatus.FLAGGED_FOR_REVIEW
    assert entry.ambiguity_review_notes is not None
    assert "world-class" in entry.ambiguity_review_notes.lower()


def test_5_target_provenance_and_zero_invention_guardrail():
    """
    Verify that officially stated targets, analyst-proposed benchmarks, and
    un-targeted policies are strictly separated and invented targets are rejected.
    """
    # 1. Valid OFFICIALLY_STATED target with documentary reference
    val, prov, ref = PolicyRegistryService.validate_target_provenance(
        target_value=500000.0,
        target_provenance="OFFICIALLY_STATED",
        target_source_reference="TN Budget Speech 2022-23, Para 84",
    )
    assert val == 500000.0
    assert prov == TargetProvenanceType.OFFICIALLY_STATED

    # 2. Reject OFFICIALLY_STATED target without a documentary source reference (Never invent a target)
    with pytest.raises(ValueError, match="Never invent an official policy target"):
        PolicyRegistryService.validate_target_provenance(
            target_value=500000.0,
            target_provenance="OFFICIALLY_STATED",
            target_source_reference="",
        )

    # 3. Reject numeric target_value when target_provenance is NO_PUBLISHED_TARGET
    with pytest.raises(ValueError, match="Never invent a policy target"):
        PolicyRegistryService.validate_target_provenance(
            target_value=75.0,
            target_provenance="NO_PUBLISHED_TARGET",
            target_source_reference=None,
        )

    # 4. Valid ANALYST_PROPOSED_BENCHMARK requires analytical basis
    val_b, prov_b, ref_b = PolicyRegistryService.validate_target_provenance(
        target_value=60.0,
        target_provenance="ANALYST_PROPOSED_BENCHMARK",
        target_source_reference="National NEP 2030 Benchmark Comparison",
    )
    assert val_b == 60.0
    assert prov_b == TargetProvenanceType.ANALYST_PROPOSED_BENCHMARK

    with pytest.raises(ValueError, match="explicit analytical basis"):
        PolicyRegistryService.validate_target_provenance(
            target_value=60.0,
            target_provenance="ANALYST_PROPOSED_BENCHMARK",
            target_source_reference=None,
        )


def test_6_evaluation_plan_builder_all_required_fields(db_session):
    """
    Verify that PolicyEvaluationPlan stores all 11 required components:
    evaluation question, objective being assessed, indicator definition, baseline period,
    comparison period, target value, actual value, data source, calculation method,
    geographic level, and limitations.
    """
    for entry_data in get_phase10_sample_registry_entries():
        PolicyRegistryService.register_policy(db_session, **entry_data)
    for obj_data in get_phase10_sample_objectives():
        db_session.add(PolicyObjective(**obj_data))
    for ind_data in get_phase10_sample_indicators():
        db_session.add(PolicyIndicator(**ind_data))
    db_session.commit()

    plans_data = get_phase10_sample_evaluation_plans()
    created_plans = []
    for p_data in plans_data:
        plan = PolicyRegistryService.create_evaluation_plan(db_session, **p_data)
        created_plans.append(plan)

    assert len(created_plans) == 3

    # Plan 1: Officially stated target
    p1 = created_plans[0]
    assert p1.plan_id == "PLAN-TEST-PUDHUMAI-OUTPUT-01"
    assert p1.target_provenance == TargetProvenanceType.OFFICIALLY_STATED
    assert p1.target_value == 500000.0
    assert p1.actual_value == 482000.0
    assert p1.baseline_period == "2021-22"
    assert p1.comparison_period == "2023-24"
    assert p1.geographic_level == "STATE"
    assert "PTRR" in p1.calculation_method
    assert "CAG noted 8.3%" in p1.limitations
    assert p1.plan_status == "ACTIVE"

    # Plan 2: Analyst-proposed benchmark
    p2 = created_plans[1]
    assert p2.target_provenance == TargetProvenanceType.ANALYST_PROPOSED_BENCHMARK
    assert p2.target_value == 60.0
    assert p2.baseline_value == 48.2
    assert p2.actual_value == 54.1

    # Plan 3: No published target on ambiguous objective
    p3 = created_plans[2]
    assert p3.target_provenance == TargetProvenanceType.NO_PUBLISHED_TARGET
    assert p3.target_value is None
    assert p3.is_objective_ambiguous is True
    assert p3.plan_status == "FLAGGED_AMBIGUOUS_OBJECTIVE"


def test_7_plan_assessment_summary_and_epistemic_notes(db_session):
    """Verify compute_plan_assessment_summary distinguishes official targets from analyst benchmarks."""
    for entry_data in get_phase10_sample_registry_entries():
        PolicyRegistryService.register_policy(db_session, **entry_data)

    plans_data = get_phase10_sample_evaluation_plans()
    p1 = PolicyRegistryService.create_evaluation_plan(db_session, **plans_data[0])
    p2 = PolicyRegistryService.create_evaluation_plan(db_session, **plans_data[1])
    p3 = PolicyRegistryService.create_evaluation_plan(db_session, **plans_data[2])

    s1 = PolicyRegistryService.compute_plan_assessment_summary(p1)
    assert s1["is_official_target"] is True
    assert s1["is_analyst_benchmark"] is False
    assert s1["target_realization_pct"] == 96.4
    assert "OFFICIALLY STATED" in s1["epistemic_note"]
    assert "results_chain_warning" in s1  # Because p1 is an OUTPUT indicator

    s2 = PolicyRegistryService.compute_plan_assessment_summary(p2)
    assert s2["is_official_target"] is False
    assert s2["is_analyst_benchmark"] is True
    assert s2["baseline_to_actual_change"] == 5.9
    assert "ANALYST-PROPOSED BENCHMARK" in s2["epistemic_note"]

    s3 = PolicyRegistryService.compute_plan_assessment_summary(p3)
    assert s3["is_official_target"] is False
    assert s3["is_analyst_benchmark"] is False
    assert s3["target_realization_pct"] is None
    assert "without an invented target" in s3["epistemic_note"]


def test_8_unified_evidence_graph_synchronization(db_session):
    """Verify PolicyRegistryEntry and PolicyEvaluationPlan sync cleanly to CivicGraphNode and CivicEvidenceEdge."""
    entries = get_phase10_sample_registry_entries()
    policy = PolicyRegistryService.register_policy(db_session, **entries[0])
    plan = PolicyRegistryService.create_evaluation_plan(db_session, **get_phase10_sample_evaluation_plans()[0])

    policy_node, plan_node = PolicyRegistryService.sync_policy_and_plan_to_graph(
        db_session,
        policy=policy,
        plan=plan,
        source_document_hash="a" * 64,
    )

    assert policy_node.node_id == "NODE:POLICY:POL-TEST-PUDHUMAI-PENN"
    assert policy_node.entity_type == GraphEntityType.POLICY_REGISTRY_ENTRY
    assert plan_node is not None
    assert plan_node.node_id == "NODE:EVALPLAN:PLAN-TEST-PUDHUMAI-OUTPUT-01"
    assert plan_node.entity_type == GraphEntityType.POLICY_EVALUATION_PLAN

    edge = db_session.query(CivicEvidenceEdge).filter_by(
        source_node_id=plan_node.node_id,
        target_node_id=policy_node.node_id,
    ).first()
    assert edge is not None
    assert edge.relationship_type == GraphRelationshipType.EVALUATES


def test_9_zero_fabrication_compliance():
    """Verify all Phase 10.3 fixtures are explicitly flagged with is_test_fixture=True."""
    for entry in get_phase10_sample_registry_entries():
        assert entry["is_test_fixture"] is True
        assert "-TEST-" in entry["policy_id"]

    for plan in get_phase10_sample_evaluation_plans():
        assert plan["is_test_fixture"] is True
        assert "-TEST-" in plan["plan_id"]
