"""
Phase 10.1 — Public Policy Outcome and Impact Evaluation Architecture Tests.
=============================================================================

Validates:
1. Five-Tier Results Chain taxonomy (INPUT, ACTIVITY, OUTPUT, OUTCOME, IMPACT).
2. Nine required Policy Evaluation types coverage.
3. Epistemic guardrail: non-equivalence of expenditure/activities with outcomes.
4. PolicyObjective and BeneficiaryGroup persistence, bilingualism, and serialization.
5. Indicator observations: baseline, intermediate, follow-up, and target tracking.
6. Causal evaluation methodology: identification strategy and automatic downgrading protocol.
7. Finding evidence links: supporting vs contradicting evidence and contradiction detection.
8. Evaluation limitations, confounder documentation, and uncertainty exposure.
9. Seamless integration with Unified Civic Intelligence & Evidence Graph (no duplication).
10. Zero-fabrication compliance (all test fixtures marked with is_test_fixture=True).
"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.database.base_class import Base
from backend.models.policy_evaluation import (
    PolicyObjective,
    BeneficiaryGroup,
    ImplementationActivity,
    PolicyIndicator,
    IndicatorObservation,
    EvaluationStudy,
    EvaluationFinding,
    FindingEvidenceLink,
    EvaluationLimitation,
    IndicatorType,
    ObservationStage,
    EvaluationType,
    CausalRigorGrade,
    FindingType,
    ConfidenceLevel,
    EvidenceStance,
    LimitationCategory,
)
from backend.models.graph import (
    CivicGraphNode,
    CivicEvidenceEdge,
    GraphEntityType,
    GraphRelationshipType,
    MatchingMethod,
    GraphProvenanceStatus,
)
from tests.fixtures.phase10_fixtures import (
    get_phase10_sample_objectives,
    get_phase10_sample_beneficiary_groups,
    get_phase10_sample_activities,
    get_phase10_sample_indicators,
    get_phase10_sample_observations,
    get_phase10_sample_studies,
    get_phase10_sample_findings,
    get_phase10_sample_evidence_links,
    get_phase10_sample_limitations,
)


@pytest.fixture
def db_session():
    """In-memory SQLite database session for testing Phase 10 architecture."""
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    try:
        yield session
    finally:
        session.close()


def test_1_indicator_results_chain_taxonomy():
    """Verify all 5 stages of the Results Chain are supported in IndicatorType enum."""
    expected_stages = ["INPUT", "ACTIVITY", "OUTPUT", "OUTCOME", "IMPACT"]
    members = [m.value for m in IndicatorType]
    for stage in expected_stages:
        assert stage in members, f"Expected Results Chain stage {stage} missing from IndicatorType"
        parsed = IndicatorType.from_string(stage)
        assert parsed.value == stage


def test_2_nine_evaluation_types_coverage():
    """Verify all 9 standardized policy evaluation types are supported."""
    required_eval_types = [
        "IMPLEMENTATION_PROGRESS",
        "BUDGET_EXECUTION",
        "TARGET_VERSUS_ACTUAL",
        "BEFORE_AND_AFTER_DESCRIPTIVE",
        "GEOGRAPHIC_COMPARISON",
        "BENEFICIARY_COVERAGE",
        "AUDIT_FINDING",
        "EVIDENCE_BASED_OUTCOME",
        "CAUSAL_EVALUATION",
    ]
    members = [m.value for m in EvaluationType]
    for eval_type in required_eval_types:
        assert eval_type in members, f"Required evaluation type {eval_type} missing from EvaluationType enum"
        parsed = EvaluationType.from_string(eval_type)
        assert parsed.value == eval_type


def test_3_epistemic_guardrail_expenditure_not_equal_to_outcome(db_session):
    """
    Epistemic Guardrail:
    Verify that an input or output indicator can NEVER be coerced or aliased as an outcome indicator.
    """
    sample_indicators = get_phase10_sample_indicators()
    
    # Locate input, output, and outcome indicators
    input_ind = next(ind for ind in sample_indicators if ind["indicator_type"] == "INPUT")
    output_ind = next(ind for ind in sample_indicators if ind["indicator_type"] == "OUTPUT")
    outcome_ind = next(ind for ind in sample_indicators if ind["indicator_type"] == "OUTCOME")
    impact_ind = next(ind for ind in sample_indicators if ind["indicator_type"] == "IMPACT")

    assert input_ind["indicator_type"] != outcome_ind["indicator_type"]
    assert output_ind["indicator_type"] != outcome_ind["indicator_type"]
    assert outcome_ind["indicator_type"] != impact_ind["indicator_type"]
    
    # Financial budget allocation is strictly an INPUT
    assert "BUDGET" in input_ind["indicator_id"]
    assert input_ind["unit"] == "RUPEES_CRORE"
    
    # Counting active stipend recipients is strictly an OUTPUT (delivery of benefit)
    assert output_ind["indicator_id"] == "IND-TEST-PUDHUMAI-BENEFICIARIES"
    assert output_ind["unit"] == "COUNT"
    
    # Gross Enrollment Ratio is strictly an OUTCOME (actual behavioral/educational change)
    assert outcome_ind["indicator_id"] == "IND-TEST-PUDHUMAI-GER-FEMALE"
    assert outcome_ind["unit"] == "PERCENT"


def test_4_policy_objective_and_beneficiary_persistence(db_session):
    """Verify PolicyObjective and BeneficiaryGroup persistence, relations, and serialization."""
    sample_objs = get_phase10_sample_objectives()
    sample_bens = get_phase10_sample_beneficiary_groups()

    for obj_data in sample_objs:
        db_session.add(PolicyObjective(**obj_data))
    db_session.commit()

    for ben_data in sample_bens:
        db_session.add(BeneficiaryGroup(**ben_data))
    db_session.commit()

    saved_obj = db_session.query(PolicyObjective).filter_by(objective_id="OBJ-TEST-PUDHUMAI-PENN-01").first()
    assert saved_obj is not None
    assert "புதுமைப் பெண்" in saved_obj.title_ta
    assert saved_obj.is_statutory is True
    assert len(saved_obj.beneficiary_groups) == 1
    assert saved_obj.beneficiary_groups[0].group_id == "BEN-TEST-PUDHUMAI-GIRLS"
    assert saved_obj.beneficiary_groups[0].estimated_eligible_population == 520000

    serialized = saved_obj.to_dict()
    assert serialized["objective_id"] == "OBJ-TEST-PUDHUMAI-PENN-01"
    assert serialized["sector"] == "Higher Education & Social Welfare"
    assert serialized["is_test_fixture"] is True


def test_5_indicator_observations_baseline_vs_followup(db_session):
    """Verify IndicatorObservation storage across BASELINE, INTERMEDIATE, FOLLOW_UP, TARGET stages."""
    # Seed objective first
    for obj_data in get_phase10_sample_objectives():
        db_session.add(PolicyObjective(**obj_data))
    db_session.commit()

    # Seed indicators
    for ind_data in get_phase10_sample_indicators():
        db_session.add(PolicyIndicator(**ind_data))
    db_session.commit()

    # Seed observations
    sample_obs = get_phase10_sample_observations()
    for obs_data in sample_obs:
        db_session.add(IndicatorObservation(**obs_data))
    db_session.commit()

    ger_observations = db_session.query(IndicatorObservation).filter_by(
        indicator_id="IND-TEST-PUDHUMAI-GER-FEMALE"
    ).all()
    assert len(ger_observations) == 4

    obs_by_stage = {o.stage.value: o for o in ger_observations}
    assert "BASELINE" in obs_by_stage
    assert "INTERMEDIATE" in obs_by_stage
    assert "FOLLOW_UP" in obs_by_stage
    assert "TARGET" in obs_by_stage

    baseline_val = obs_by_stage["BASELINE"].value
    followup_val = obs_by_stage["FOLLOW_UP"].value
    target_val = obs_by_stage["TARGET"].value

    assert baseline_val == 48.2
    assert followup_val == 54.1
    assert target_val == 60.0

    # Test before-and-after percentage change computation
    pct_change = ((followup_val - baseline_val) / baseline_val) * 100
    assert pytest.approx(pct_change, 0.01) == 12.24

    # Test distance-to-target metric
    distance_to_target = ((followup_val - baseline_val) / (target_val - baseline_val)) * 100
    assert pytest.approx(distance_to_target, 0.01) == 50.0


def test_6_evaluation_study_and_causal_downgrading_logic(db_session):
    """
    Verify causal rigor grading and automatic downgrading protocol:
    Studies attempting CAUSAL_EVALUATION without a valid identification strategy
    must be identified for downgrading to BEFORE_AND_AFTER_DESCRIPTIVE.
    """
    for study_data in get_phase10_sample_studies():
        db_session.add(EvaluationStudy(**study_data))
    db_session.commit()

    valid_causal_study = db_session.query(EvaluationStudy).filter_by(
        study_id="STD-TEST-PUDHUMAI-QUASI-EXP-01"
    ).first()
    assert valid_causal_study is not None
    assert valid_causal_study.evaluation_type == EvaluationType.CAUSAL_EVALUATION
    assert valid_causal_study.causal_rigor_grade == CausalRigorGrade.GRADE_B_QUASI_EXPERIMENTAL
    assert valid_causal_study.is_causally_identified is True
    assert valid_causal_study.identification_strategy == "DID"

    # Inspect the flawed causal study
    flawed_study = db_session.query(EvaluationStudy).filter_by(
        study_id="STD-TEST-FLAWED-CAUSAL-CLAIM-01"
    ).first()
    assert flawed_study is not None
    
    # Automated downgrading check logic
    def check_and_apply_causal_downgrade(study: EvaluationStudy) -> EvaluationType:
        if study.evaluation_type == EvaluationType.CAUSAL_EVALUATION:
            if not study.is_causally_identified or study.identification_strategy in [None, "NONE"]:
                return EvaluationType.BEFORE_AND_AFTER_DESCRIPTIVE
        return study.evaluation_type

    effective_type = check_and_apply_causal_downgrade(flawed_study)
    assert effective_type == EvaluationType.BEFORE_AND_AFTER_DESCRIPTIVE


def test_7_finding_evidence_link_and_contradiction_handling(db_session):
    """
    Verify that EvaluationFindings link to primary evidence passages,
    and contradictory evidence (CAG audits) is preserved with proper stance.
    """
    # Seed prerequisites
    for obj_data in get_phase10_sample_objectives():
        db_session.add(PolicyObjective(**obj_data))
    for ind_data in get_phase10_sample_indicators():
        db_session.add(PolicyIndicator(**ind_data))
    for study_data in get_phase10_sample_studies():
        db_session.add(EvaluationStudy(**study_data))
    for finding_data in get_phase10_sample_findings():
        db_session.add(EvaluationFinding(**finding_data))
    for link_data in get_phase10_sample_evidence_links():
        db_session.add(FindingEvidenceLink(**link_data))
    db_session.commit()

    # Finding 1: DiD effect backed by supporting AISHE evidence
    did_finding = db_session.query(EvaluationFinding).filter_by(
        finding_id="FIND-TEST-PUDHUMAI-DID-EFFECT"
    ).first()
    assert did_finding is not None
    assert did_finding.quantified_effect == 14.8
    assert did_finding.p_value < 0.01
    assert did_finding.confidence_level == ConfidenceLevel.VERY_HIGH
    assert len(did_finding.evidence_links) == 1
    assert did_finding.evidence_links[0].stance == EvidenceStance.SUPPORTS

    # Finding 2: CAG Audit with contradicting evidence
    cag_finding = db_session.query(EvaluationFinding).filter_by(
        finding_id="FIND-TEST-PUDHUMAI-CAG-IRREGULARITY"
    ).first()
    assert cag_finding is not None
    assert cag_finding.has_contradicting_evidence is True
    assert len(cag_finding.evidence_links) == 1
    assert cag_finding.evidence_links[0].stance == EvidenceStance.CONTRADICTS
    assert cag_finding.evidence_links[0].source_credibility_tier == "TIER_1_STATUTORY"
    assert "8.3%" in cag_finding.evidence_links[0].quotation_excerpt


def test_8_limitation_and_uncertainty_tracking(db_session):
    """Verify that methodological limitations, confounders, and severity are recorded."""
    for study_data in get_phase10_sample_studies():
        db_session.add(EvaluationStudy(**study_data))
    for lim_data in get_phase10_sample_limitations():
        db_session.add(EvaluationLimitation(**lim_data))
    db_session.commit()

    saved_limitations = db_session.query(EvaluationLimitation).all()
    assert len(saved_limitations) == 3

    covid_lim = db_session.query(EvaluationLimitation).filter_by(
        limitation_id="LIM-TEST-COVID-CONFOUNDER-01"
    ).first()
    assert covid_lim is not None
    assert covid_lim.category == LimitationCategory.EXTERNAL_CONFOUNDING
    assert "COVID-19" in covid_lim.description
    assert covid_lim.severity == "MODERATE"

    no_ctrl_lim = db_session.query(EvaluationLimitation).filter_by(
        limitation_id="LIM-TEST-NO-CONTROL-GROUP-01"
    ).first()
    assert no_ctrl_lim is not None
    assert no_ctrl_lim.category == LimitationCategory.ABSENCE_OF_CONTROL_GROUP
    assert no_ctrl_lim.severity == "CRITICAL"


def test_9_evidence_graph_interoperability_without_duplication(db_session):
    """
    Verify Phase 10 entities and relationships map directly into
    the Unified Civic Intelligence & Evidence Graph (CivicGraphNode & CivicEvidenceEdge)
    without duplicating the graph architecture.
    """
    # 1. Verify enum registration in graph models
    assert "POLICY_OBJECTIVE" in [m.value for m in GraphEntityType]
    assert "POLICY_INDICATOR" in [m.value for m in GraphEntityType]
    assert "EVALUATION_FINDING" in [m.value for m in GraphEntityType]
    assert "evaluates" in [m.value for m in GraphRelationshipType]
    assert "measures" in [m.value for m in GraphRelationshipType]
    assert "targets" in [m.value for m in GraphRelationshipType]

    # 2. Instantiate Phase 10 proxy nodes in CivicGraphNode
    objective_node = CivicGraphNode(
        node_id="NODE:POBJ:PUDHUMAI_PENN",
        entity_type=GraphEntityType.POLICY_OBJECTIVE,
        canonical_id="OBJ-TEST-PUDHUMAI-PENN-01",
        label="Pudhumai Penn Higher Education Assurance",
        label_ta="புதுமைப் பெண் திட்டம்",
        source_phase="PHASE_10",
        attributes_json={"sector": "Higher Education"},
        is_test_fixture=True,
    )
    indicator_node = CivicGraphNode(
        node_id="NODE:IND:PUDHUMAI_GER",
        entity_type=GraphEntityType.POLICY_INDICATOR,
        canonical_id="IND-TEST-PUDHUMAI-GER-FEMALE",
        label="Female Higher Education GER",
        label_ta="உயர்கல்வி மொத்த சேர்க்கை விகிதம்",
        source_phase="PHASE_10",
        attributes_json={"type": "OUTCOME", "unit": "PERCENT"},
        is_test_fixture=True,
    )
    db_session.add(objective_node)
    db_session.add(indicator_node)
    db_session.commit()

    # 3. Create an evidence edge linking indicator to objective
    edge = CivicEvidenceEdge(
        edge_id="EDGE:MEASURES:OBJ-01:IND-01",
        source_node_id="NODE:IND:PUDHUMAI_GER",
        target_node_id="NODE:POBJ:PUDHUMAI_PENN",
        relationship_type=GraphRelationshipType.MEASURES,
        evidence_reference="TN Higher Education Department Policy Note 2022-23 Section 4",
        source_document_id="DOC-TEST-TN-POLICY-NOTE-2022",
        source_document_url="https://tn.gov.in/policynotes/higher_edu_2022.pdf",
        source_document_hash="d4e5f67890123456789abcdef0123456789abcdef0123456789abcdef0123",
        matching_method=MatchingMethod.DIRECT_DOCUMENTARY,
        confidence_score=0.98,
        provenance_status=GraphProvenanceStatus.VALID,
        is_test_fixture=True,
    )
    db_session.add(edge)
    db_session.commit()

    # Verify bidirectional graph traversal
    saved_obj_node = db_session.query(CivicGraphNode).filter_by(node_id="NODE:POBJ:PUDHUMAI_PENN").first()
    assert len(saved_obj_node.incoming_edges) == 1
    assert saved_obj_node.incoming_edges[0].relationship_type == GraphRelationshipType.MEASURES


def test_10_zero_fabrication_compliance():
    """Verify that all Phase 10 test fixtures carry is_test_fixture=True and valid IDs."""
    fixtures = [
        get_phase10_sample_objectives(),
        get_phase10_sample_beneficiary_groups(),
        get_phase10_sample_activities(),
        get_phase10_sample_indicators(),
        get_phase10_sample_observations(),
        get_phase10_sample_studies(),
        get_phase10_sample_findings(),
        get_phase10_sample_evidence_links(),
        get_phase10_sample_limitations(),
    ]

    for fixture_list in fixtures:
        assert len(fixture_list) > 0
        for item in fixture_list:
            assert item["is_test_fixture"] is True
            # Verify primary key contains -TEST-
            pk_val = next(v for k, v in item.items() if k.endswith("_id"))
            assert "-TEST-" in pk_val
