"""
Phase 10.6 — Policy Outcome Analysis and Comparison Methods Unit Tests.
======================================================================

Validates:
1. Baseline vs follow-up comparisons, all 9 mandatory result fields, non-causal labeling,
   and zero baseline handling (`baseline_value = 0.0` -> `percentage_change = None`,
   `UNDEFINED_ZERO_BASELINE`).
2. Negative changes under both `INCREASE` and `DECREASE` improvement directions.
3. Target-versus-actual outcome comparisons and incomplete periods in multi-year trend series.
4. Geographic comparisons and mandatory explanations of coverage, demographics, and data quality.
5. Beneficiary-group comparisons with small-sample warnings ($n < 30$) and small-cell
   privacy suppression ($n < 5$).
6. Rejection of incompatible indicators (`INDICATOR_ID_MISMATCH`, `DEFINITION_MISMATCH`,
   `UNIT_MISMATCH`, `BOUNDARY_MISMATCH`).
7. Documented evaluation findings (automatic causal downgrading when causal design is absent)
   and leave-one-out sensitivity checks (including small-sample refusal when $n < 4$).
"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.database.base_class import Base
from backend.models.budget import BudgetDepartment, BudgetScheme, HistoricalScheme
from backend.models.manifesto import Manifesto, ManifestoDocument, ManifestoSource
from backend.models.promise import PoliticalPromise
from backend.models.policy_evaluation import (
    PolicyObjective,
    PolicyIndicator,
    IndicatorObservation,
    BeneficiaryGroup,
    EvaluationStudy,
    EvaluationFinding,
    EvaluationLimitation,
    IndicatorType,
    IndicatorDomain,
    ObservationStage,
    ReportingFrequency,
    EvaluationType,
    CausalRigorGrade,
    FindingType,
    ConfidenceLevel,
    LimitationCategory,
)
from backend.services.policy_indicator_service import (
    PolicyIndicatorRegistryService,
    IncompatibleIndicatorComparisonError,
)
from backend.services.policy_outcome_analysis_service import (
    PolicyOutcomeAnalysisService,
    NON_CAUSAL_DESCRIPTIVE_LABEL,
    VERIFIED_CAUSAL_LABEL,
)


@pytest.fixture
def db_session():
    """In-memory SQLite session for Phase 10.6 outcome analysis tests."""
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    obj = PolicyObjective(
        objective_id="OBJ-TEST-106",
        scheme_id="SCH-TEST-106",
        title="[TEST FIXTURE] Phase 10.6 Outcome Evaluation Objective",
        description="Assess education and health outcomes with rigorous descriptive and comparison methods.",
        sector="Education & Health",
        is_test_fixture=True,
    )
    session.add(obj)
    session.commit()
    try:
        yield session
    finally:
        session.close()


def test_1_baseline_vs_followup_all_9_fields_and_zero_baseline(db_session):
    """
    Verify:
    1. All 9 mandatory fields are returned for baseline vs follow-up comparisons.
    2. Simple pre-post comparisons are strictly labelled `DESCRIPTIVE_ASSOCIATION_OR_OBSERVED_CHANGE`
       with `causal_claim_permitted = False`.
    3. Zero baselines (`0.0`) compute exact `absolute_change` while setting `percentage_change = None`
       (`UNDEFINED_ZERO_BASELINE`).
    """
    ind_ger = PolicyIndicatorRegistryService.register_indicator(
        db_session,
        indicator_id="IND-TEST-106-GER",
        objective_id="OBJ-TEST-106",
        indicator_name="[TEST FIXTURE] Female Higher Education Gross Enrollment Ratio",
        indicator_type=IndicatorType.OUTCOME,
        indicator_domain=IndicatorDomain.EDUCATION_INDICATOR,
        unit="PERCENTAGE",
        definition="Female students enrolled in higher education as a % of 18-23 age cohort.",
        definition_code="DEF:GER:FEMALE:V1",
        source="AISHE State Report (Test Fixture)",
        direction_of_improvement="INCREASE",
        is_test_fixture=True,
    )

    obs_base = IndicatorObservation(
        observation_id="OBS-TEST-106-GER-BASE",
        indicator_id=ind_ger.indicator_id,
        stage=ObservationStage.BASELINE,
        reference_period="FY2021-22",
        geographic_level="STATE",
        geographic_unit_id="TN-STATE",
        value=48.0,
        source_document_id="DOC-TEST-AISHE-21",
        source_reference="AISHE 2021-22 Table 3",
        is_test_fixture=True,
    )
    obs_follow = IndicatorObservation(
        observation_id="OBS-TEST-106-GER-FOLLOW",
        indicator_id=ind_ger.indicator_id,
        stage=ObservationStage.FOLLOW_UP,
        reference_period="FY2023-24",
        geographic_level="STATE",
        geographic_unit_id="TN-STATE",
        value=54.0,
        source_document_id="DOC-TEST-AISHE-23",
        source_reference="AISHE 2023-24 Table 3",
        is_test_fixture=True,
    )

    res = PolicyOutcomeAnalysisService.analyze_baseline_vs_followup(ind_ger, obs_base, obs_follow)

    # Verify non-causal guardrails
    assert res["epistemic_label"] == NON_CAUSAL_DESCRIPTIVE_LABEL
    assert res["causal_claim_permitted"] is False

    # Verify all 9 mandatory fields
    assert res["indicator_definition"]["indicator_id"] == "IND-TEST-106-GER"
    assert res["baseline_value"] == 48.0
    assert res["followup_value"] == 54.0
    assert res["absolute_change"] == 6.0
    assert res["percentage_change"] == 12.5
    assert res["percentage_change_validity"] == "MATHEMATICALLY_VALID"
    assert res["normative_trajectory"] == "FAVORABLE_OBSERVED_CHANGE"
    assert res["time_period"]["baseline_period"] == "FY2021-22"
    assert res["time_period"]["followup_period"] == "FY2023-24"
    assert res["geographic_scope"]["geographic_unit_id"] == "TN-STATE"
    assert len(res["source_references"]) == 2
    assert res["missing_data_info"]["is_complete"] is True
    assert any("Do NOT infer that the change was caused by the policy" in lim for lim in res["interpretation_limitations"])

    # Verify Zero Baseline handling (`baseline_value = 0.0`)
    obs_zero_base = IndicatorObservation(
        observation_id="OBS-TEST-106-ZERO-BASE",
        indicator_id=ind_ger.indicator_id,
        stage=ObservationStage.BASELINE,
        reference_period="FY2020-21",
        geographic_level="STATE",
        geographic_unit_id="TN-STATE",
        value=0.0,
        source_reference="Baseline Pre-Launch",
        is_test_fixture=True,
    )
    res_zero = PolicyOutcomeAnalysisService.analyze_baseline_vs_followup(
        ind_ger, obs_zero_base, obs_follow
    )
    assert res_zero["baseline_value"] == 0.0
    assert res_zero["followup_value"] == 54.0
    assert res_zero["absolute_change"] == 54.0
    assert res_zero["percentage_change"] is None
    assert res_zero["percentage_change_validity"] == "UNDEFINED_ZERO_BASELINE"
    assert any("ZERO_BASELINE_NOTE" in lim for lim in res_zero["interpretation_limitations"])


def test_2_negative_changes_and_directional_improvement_semantics(db_session):
    """
    Verify negative changes:
    1. When `direction_of_improvement == "DECREASE"` (e.g., Maternal Mortality Ratio),
       a negative change (-15.0, -25.0%) is classified as `FAVORABLE_OBSERVED_CHANGE`.
    2. When `direction_of_improvement == "INCREASE"`, a negative change (-4.6, -5.0%)
       is classified as `ADVERSE_OBSERVED_CHANGE`.
    """
    ind_mmr = PolicyIndicatorRegistryService.register_indicator(
        db_session,
        indicator_id="IND-TEST-106-MMR",
        objective_id="OBJ-TEST-106",
        indicator_name="[TEST FIXTURE] Maternal Mortality Ratio (MMR)",
        indicator_type=IndicatorType.IMPACT,
        indicator_domain=IndicatorDomain.HEALTH_INDICATOR,
        unit="PER_100000_LIVE_BIRTHS",
        definition="Maternal deaths per 100,000 live births.",
        definition_code="DEF:MMR:SRS",
        source="SRS Special Bulletin (Test Fixture)",
        direction_of_improvement="DECREASE",
        is_test_fixture=True,
    )

    obs_mmr_base = IndicatorObservation(
        observation_id="OBS-TEST-MMR-BASE",
        indicator_id=ind_mmr.indicator_id,
        stage=ObservationStage.BASELINE,
        reference_period="2018-20",
        geographic_level="STATE",
        geographic_unit_id="TN-STATE",
        value=60.0,
        source_reference="SRS 2018-20",
        is_test_fixture=True,
    )
    obs_mmr_follow = IndicatorObservation(
        observation_id="OBS-TEST-MMR-FOLLOW",
        indicator_id=ind_mmr.indicator_id,
        stage=ObservationStage.FOLLOW_UP,
        reference_period="2021-23",
        geographic_level="STATE",
        geographic_unit_id="TN-STATE",
        value=45.0,
        source_reference="SRS 2021-23",
        is_test_fixture=True,
    )

    res_mmr = PolicyOutcomeAnalysisService.analyze_baseline_vs_followup(
        ind_mmr, obs_mmr_base, obs_mmr_follow
    )
    assert res_mmr["absolute_change"] == -15.0
    assert res_mmr["percentage_change"] == -25.0
    assert res_mmr["change_direction"] == "DECREASE"
    assert res_mmr["normative_trajectory"] == "FAVORABLE_OBSERVED_CHANGE"

    # Now test negative change on an indicator where INCREASE is desired
    ind_att = PolicyIndicatorRegistryService.register_indicator(
        db_session,
        indicator_id="IND-TEST-106-ATT",
        objective_id="OBJ-TEST-106",
        indicator_name="[TEST FIXTURE] Secondary School Attendance Rate",
        indicator_type=IndicatorType.OUTCOME,
        indicator_domain=IndicatorDomain.EDUCATION_INDICATOR,
        unit="PERCENTAGE",
        definition="Average daily attendance percentage in government secondary schools.",
        definition_code="DEF:ATT:SEC",
        source="EMIS Portal (Test Fixture)",
        direction_of_improvement="INCREASE",
        is_test_fixture=True,
    )
    obs_att_base = IndicatorObservation(
        observation_id="OBS-TEST-ATT-BASE",
        indicator_id=ind_att.indicator_id,
        stage=ObservationStage.BASELINE,
        reference_period="FY2022-23",
        geographic_level="STATE",
        geographic_unit_id="TN-STATE",
        value=92.0,
        source_reference="EMIS 2022-23",
        is_test_fixture=True,
    )
    obs_att_follow = IndicatorObservation(
        observation_id="OBS-TEST-ATT-FOLLOW",
        indicator_id=ind_att.indicator_id,
        stage=ObservationStage.FOLLOW_UP,
        reference_period="FY2023-24",
        geographic_level="STATE",
        geographic_unit_id="TN-STATE",
        value=87.4,
        source_reference="EMIS 2023-24",
        is_test_fixture=True,
    )
    res_att = PolicyOutcomeAnalysisService.analyze_baseline_vs_followup(
        ind_att, obs_att_base, obs_att_follow
    )
    assert res_att["absolute_change"] == -4.6
    assert res_att["percentage_change"] == -5.0
    assert res_att["normative_trajectory"] == "ADVERSE_OBSERVED_CHANGE"


def test_3_target_vs_actual_and_incomplete_periods_in_trends(db_session):
    """
    Verify:
    1. Target-versus-actual outcome comparison (`target_gap`, `target_realization_pct`, `distance_to_target_pct`).
    2. Multi-period trend series with an incomplete/missing intermediate period (`FY2022-23` missing)
       preserves `None` and marks the subsequent period `OBSERVED_AFTER_MISSING_GAP`.
    """
    ind = PolicyIndicatorRegistryService.register_indicator(
        db_session,
        indicator_id="IND-TEST-106-WATER",
        objective_id="OBJ-TEST-106",
        indicator_name="[TEST FIXTURE] Rural Piped Water Access Rate",
        indicator_type=IndicatorType.OUTCOME,
        indicator_domain=IndicatorDomain.SERVICE_ACCESS,
        unit="PERCENTAGE",
        definition="Share of rural households with functional household tap connections.",
        definition_code="DEF:FHTC:V1",
        source="JJM IMIS (Test Fixture)",
        direction_of_improvement="INCREASE",
        is_test_fixture=True,
    )

    obs_21 = IndicatorObservation(
        observation_id="OBS-TEST-W-21",
        indicator_id=ind.indicator_id,
        stage=ObservationStage.BASELINE,
        reference_period="FY2021-22",
        geographic_level="STATE",
        geographic_unit_id="TN-STATE",
        value=50.0,
        source_reference="JJM 2021-22",
        is_test_fixture=True,
    )
    obs_23 = IndicatorObservation(
        observation_id="OBS-TEST-W-23",
        indicator_id=ind.indicator_id,
        stage=ObservationStage.INTERMEDIATE,
        reference_period="FY2023-24",
        geographic_level="STATE",
        geographic_unit_id="TN-STATE",
        value=75.0,
        source_reference="JJM 2023-24",
        is_test_fixture=True,
    )
    obs_24 = IndicatorObservation(
        observation_id="OBS-TEST-W-24",
        indicator_id=ind.indicator_id,
        stage=ObservationStage.FOLLOW_UP,
        reference_period="FY2024-25",
        geographic_level="STATE",
        geographic_unit_id="TN-STATE",
        value=80.0,
        source_reference="JJM 2024-25",
        is_test_fixture=True,
    )
    obs_target = IndicatorObservation(
        observation_id="OBS-TEST-W-TARGET",
        indicator_id=ind.indicator_id,
        stage=ObservationStage.TARGET,
        reference_period="FY2024-25",
        geographic_level="STATE",
        geographic_unit_id="TN-STATE",
        value=100.0,
        source_reference="Policy Note Target",
        is_test_fixture=True,
    )

    # 1. Target vs Actual
    t_res = PolicyOutcomeAnalysisService.analyze_target_vs_actual_outcome(
        ind, obs_21, obs_24, obs_target
    )
    tc = t_res["target_comparison"]
    assert tc["target_value"] == 100.0
    assert tc["target_gap"] == -20.0
    assert tc["target_realization_pct"] == 80.0
    assert tc["distance_to_target_pct"] == 60.0  # (80 - 50) / (100 - 50) * 100
    assert tc["target_status"] == "BELOW_STATED_TARGET"

    # 2. Trend series with missing FY2022-23
    trend = PolicyOutcomeAnalysisService.analyze_outcome_trend_series(
        ind,
        [obs_21, obs_23, obs_24],
        expected_periods=["FY2021-22", "FY2022-23", "FY2023-24", "FY2024-25"],
    )
    assert trend["missing_data_info"]["is_complete"] is False
    assert trend["missing_data_info"]["missing_periods"] == ["FY2022-23"]
    pts = trend["trend_points"]
    assert pts[1]["reference_period"] == "FY2022-23"
    assert pts[1]["value"] is None
    assert pts[1]["status"] == "MISSING_PERIOD_OBSERVATION"
    # Period right after a missing gap must not fabricate a 1-year change across a 2-year gap
    assert pts[2]["reference_period"] == "FY2023-24"
    assert pts[2]["status"] == "OBSERVED_AFTER_MISSING_GAP"
    assert pts[2]["period_over_period_change"] is None
    # Consecutive period FY2023-24 -> FY2024-25 computes change normally
    assert pts[3]["reference_period"] == "FY2024-25"
    assert pts[3]["period_over_period_change"] == 5.0


def test_4_geographic_comparison_and_context_explanation_requirement(db_session):
    """
    Verify geographic comparisons across districts:
    - Computes district changes and Coefficient of Variation (`coefficient_of_variation_pct`).
    - Flags districts compared without `comparability_context` explaining coverage,
      demographics, and data quality.
    """
    ind_dist = PolicyIndicatorRegistryService.register_indicator(
        db_session,
        indicator_id="IND-TEST-106-GEO",
        objective_id="OBJ-TEST-106",
        indicator_name="[TEST FIXTURE] District Hypertension Control Rate",
        indicator_type=IndicatorType.OUTCOME,
        indicator_domain=IndicatorDomain.HEALTH_INDICATOR,
        unit="PERCENTAGE",
        definition="Percentage of enrolled hypertension patients with controlled BP.",
        definition_code="DEF:MTM:BP:V1",
        source="MTM District Registry (Test Fixture)",
        geographic_level="DISTRICT",
        boundary_reference="TN_38_DISTRICTS_2020",
        is_test_fixture=True,
    )

    b_obs = [
        IndicatorObservation(
            observation_id="OBS-GEO-CHN-B",
            indicator_id=ind_dist.indicator_id,
            stage=ObservationStage.BASELINE,
            reference_period="FY2021-22",
            geographic_level="DISTRICT",
            geographic_unit_id="TN-DIST-CHENNAI",
            boundary_reference="TN_38_DISTRICTS_2020",
            value=40.0,
            source_reference="DPH 2021",
            is_test_fixture=True,
        ),
        IndicatorObservation(
            observation_id="OBS-GEO-NIL-B",
            indicator_id=ind_dist.indicator_id,
            stage=ObservationStage.BASELINE,
            reference_period="FY2021-22",
            geographic_level="DISTRICT",
            geographic_unit_id="TN-DIST-NILGIRIS",
            boundary_reference="TN_38_DISTRICTS_2020",
            value=35.0,
            source_reference="DPH 2021",
            is_test_fixture=True,
        ),
    ]
    f_obs = [
        IndicatorObservation(
            observation_id="OBS-GEO-CHN-F",
            indicator_id=ind_dist.indicator_id,
            stage=ObservationStage.FOLLOW_UP,
            reference_period="FY2023-24",
            geographic_level="DISTRICT",
            geographic_unit_id="TN-DIST-CHENNAI",
            boundary_reference="TN_38_DISTRICTS_2020",
            value=60.0,
            source_reference="DPH 2023",
            is_test_fixture=True,
        ),
        IndicatorObservation(
            observation_id="OBS-GEO-NIL-F",
            indicator_id=ind_dist.indicator_id,
            stage=ObservationStage.FOLLOW_UP,
            reference_period="FY2023-24",
            geographic_level="DISTRICT",
            geographic_unit_id="TN-DIST-NILGIRIS",
            boundary_reference="TN_38_DISTRICTS_2020",
            value=50.0,
            source_reference="DPH 2023",
            is_test_fixture=True,
        ),
    ]

    # 1. Without comparability_context -> flags UNEXPLAINED_POPULATION_OR_GEOGRAPHIC_HETEROGENEITY
    res_no_ctx = PolicyOutcomeAnalysisService.analyze_geographic_comparison(ind_dist, b_obs, f_obs)
    assert res_no_ctx["has_complete_comparability_context"] is False
    assert any(
        "UNEXPLAINED_POPULATION_OR_GEOGRAPHIC_HETEROGENEITY" in lim
        for lim in res_no_ctx["interpretation_limitations"]
    )

    # 2. With complete comparability_context -> has_complete_comparability_context is True
    ctx = {
        "TN-DIST-CHENNAI": {
            "coverage_note": "100% urban UPHC coverage",
            "demographic_context": "High urban density, older age structure",
            "data_quality_note": "VERIFIED electronic tablet entry",
        },
        "TN-DIST-NILGIRIS": {
            "coverage_note": "88% hilly habitation mobile van coverage",
            "demographic_context": "High tribal/plantation population dispersed across steep terrain",
            "data_quality_note": "VERIFIED with offline sync latency",
        },
    }
    res_with_ctx = PolicyOutcomeAnalysisService.analyze_geographic_comparison(
        ind_dist, b_obs, f_obs, comparability_context=ctx
    )
    assert res_with_ctx["has_complete_comparability_context"] is True
    assert res_with_ctx["baseline_value"] == 37.5
    assert res_with_ctx["followup_value"] == 55.0
    assert res_with_ctx["coefficient_of_variation_pct"] is not None


def test_5_beneficiary_group_comparison_small_samples_and_privacy_suppression(db_session):
    """
    Verify beneficiary-group comparisons:
    - Privacy-safe aggregate group ($n = 500$) computes changes and Demographic Parity Index (DPI).
    - Small-sample group ($n = 18 < 30$) includes `SMALL_SAMPLE_HIGH_VARIANCE_WARNING`.
    - Micro-cell group ($n = 3 < 5$) is suppressed (`PRIVACY_SUPPRESSED_SMALL_CELL`) with `None` values.
    """
    ind_ben = PolicyIndicatorRegistryService.register_indicator(
        db_session,
        indicator_id="IND-TEST-106-BEN",
        objective_id="OBJ-TEST-106",
        indicator_name="[TEST FIXTURE] Scholarship Continuation Rate by Beneficiary Group",
        indicator_type=IndicatorType.OUTCOME,
        indicator_domain=IndicatorDomain.EDUCATION_INDICATOR,
        unit="PERCENTAGE",
        definition="Share of scholarship recipients continuing into 2nd year.",
        definition_code="DEF:CONT:V1",
        source="Social Welfare Dept (Test Fixture)",
        is_test_fixture=True,
    )

    grp_rural = BeneficiaryGroup(
        group_id="BEN-TEST-RURAL",
        objective_id="OBJ-TEST-106",
        name="Rural Government School Alumnae",
        eligibility_criteria="Classes 6-12 in rural govt schools",
        estimated_eligible_population=300000,
        is_test_fixture=True,
    )
    grp_small = BeneficiaryGroup(
        group_id="BEN-TEST-PVTG-SMALL",
        objective_id="OBJ-TEST-106",
        name="Remote Hill Block Sub-Cohort",
        eligibility_criteria="PVTG students in sampled block",
        estimated_eligible_population=150,
        is_test_fixture=True,
    )
    grp_micro = BeneficiaryGroup(
        group_id="BEN-TEST-MICRO-CELL",
        objective_id="OBJ-TEST-106",
        name="Single-Village Special Category Cell",
        eligibility_criteria="Micro stratum with <5 individuals",
        estimated_eligible_population=4,
        is_test_fixture=True,
    )

    res = PolicyOutcomeAnalysisService.analyze_beneficiary_group_comparison(
        ind_ben,
        [
            {
                "group": grp_rural,
                "sample_or_cell_count": 500,
                "baseline_value": 82.0,
                "followup_value": 94.0,
                "population_share_pct": 60.0,
                "beneficiary_share_pct": 66.0,
                "coverage_and_demographic_note": "Statewide rural census coverage",
                "source_reference": "SWD Annual Report Table 8",
            },
            {
                "group": grp_small,
                "sample_or_cell_count": 18,  # < 30 -> small sample warning
                "baseline_value": 70.0,
                "followup_value": 85.0,
                "population_share_pct": 2.0,
                "beneficiary_share_pct": 2.0,
                "coverage_and_demographic_note": "Sampled block survey",
                "source_reference": "SWD Block Survey Table 2",
            },
            {
                "group": grp_micro,
                "sample_or_cell_count": 3,  # < 5 -> privacy suppression
                "baseline_value": 66.7,
                "followup_value": 100.0,
                "source_reference": "SWD Micro Table",
            },
        ],
    )

    g_list = res["group_comparisons"]
    assert g_list[0]["privacy_status"] == "PRIVACY_SAFE_AGGREGATE"
    assert g_list[0]["absolute_change"] == 12.0
    assert g_list[0]["demographic_parity_index"] == 1.1  # 66.0 / 60.0

    assert g_list[1]["privacy_status"] == "PRIVACY_SAFE_AGGREGATE"
    assert any("SMALL_SAMPLE_HIGH_VARIANCE_WARNING" in w for w in g_list[1]["group_limitations"])

    assert g_list[2]["privacy_status"] == "PRIVACY_SUPPRESSED_SMALL_CELL"
    assert g_list[2]["sample_or_cell_count"] is None
    assert g_list[2]["followup_value"] is None
    assert "BEN-TEST-MICRO-CELL" in res["missing_data_info"]["suppressed_group_ids"]


def test_6_incompatible_indicators_rejected(db_session):
    """
    Verify that attempting to compare observations from two different indicators
    raises `IncompatibleIndicatorComparisonError("INDICATOR_ID_MISMATCH")`.
    """
    ind_a = PolicyIndicatorRegistryService.register_indicator(
        db_session,
        indicator_id="IND-TEST-106-A",
        objective_id="OBJ-TEST-106",
        indicator_name="[TEST FIXTURE] Indicator A",
        indicator_type=IndicatorType.OUTCOME,
        unit="PERCENTAGE",
        definition="Definition A",
        source="Source A",
        is_test_fixture=True,
    )
    ind_b = PolicyIndicatorRegistryService.register_indicator(
        db_session,
        indicator_id="IND-TEST-106-B",
        objective_id="OBJ-TEST-106",
        indicator_name="[TEST FIXTURE] Indicator B",
        indicator_type=IndicatorType.OUTCOME,
        unit="PERCENTAGE",
        definition="Definition B",
        source="Source B",
        is_test_fixture=True,
    )

    obs_a = IndicatorObservation(
        observation_id="OBS-A",
        indicator_id=ind_a.indicator_id,
        stage=ObservationStage.BASELINE,
        reference_period="FY2021-22",
        geographic_level="STATE",
        geographic_unit_id="TN-STATE",
        value=50.0,
        is_test_fixture=True,
    )
    obs_b = IndicatorObservation(
        observation_id="OBS-B",
        indicator_id=ind_b.indicator_id,
        stage=ObservationStage.FOLLOW_UP,
        reference_period="FY2023-24",
        geographic_level="STATE",
        geographic_unit_id="TN-STATE",
        value=60.0,
        is_test_fixture=True,
    )

    with pytest.raises(IncompatibleIndicatorComparisonError) as exc_info:
        PolicyOutcomeAnalysisService.analyze_baseline_vs_followup(ind_a, obs_a, obs_b)
    assert exc_info.value.error_code == "INDICATOR_ID_MISMATCH"


def test_7_documented_findings_causal_downgrading_and_sensitivity_checks(db_session):
    """
    Verify:
    1. A study claiming `CAUSAL_EVALUATION` without a valid identification strategy is
       automatically downgraded to `DESCRIPTIVE_ASSOCIATION_OR_OBSERVED_CHANGE`.
    2. A study with verified `GRADE_B_QUASI_EXPERIMENTAL` (`DID`) design is labelled
       `CAUSAL_IMPACT_ESTIMATE`.
    3. Sensitivity checks refuse small samples ($n < 4$) and compute leave-one-out
       stability when n >= 4.
    """
    ind = PolicyIndicatorRegistryService.register_indicator(
        db_session,
        indicator_id="IND-TEST-106-CAUSAL",
        objective_id="OBJ-TEST-106",
        indicator_name="[TEST FIXTURE] Primary School Morning Attendance Rate",
        indicator_type=IndicatorType.OUTCOME,
        unit="PERCENTAGE",
        definition="Morning attendance rate in primary schools.",
        source="SPC Evaluation Report (Test Fixture)",
        is_test_fixture=True,
    )

    # 1. Unsubstantiated causal claim -> automatically downgraded
    study_unverified = EvaluationStudy(
        study_id="STD-TEST-106-WEAK",
        scheme_id="SCH-TEST-106",
        title="[TEST FIXTURE] Simple Before-After Report Claiming Causality",
        evaluation_type=EvaluationType.CAUSAL_EVALUATION,
        conducting_agency="Departmental Internal Cell",
        publication_date="2024-06-01",
        methodology_description="Simple pre-post comparison without control group.",
        causal_rigor_grade=CausalRigorGrade.GRADE_D_DESCRIPTIVE_CORRELATIONAL,
        is_causally_identified=False,
        identification_strategy="NONE",
        is_test_fixture=True,
    )
    finding_weak = EvaluationFinding(
        finding_id="FND-TEST-106-WEAK",
        study_id=study_unverified.study_id,
        indicator_id=ind.indicator_id,
        finding_type=FindingType.POSITIVE_IMPACT,
        finding_text="Attendance rose by 4.2 percentage points.",
        quantified_effect=4.2,
        confidence_level=ConfidenceLevel.LOW,
        is_test_fixture=True,
    )

    res_downgraded = PolicyOutcomeAnalysisService.evaluate_finding_epistemic_status(
        study_unverified, finding_weak, ind, baseline_value=88.0, followup_value=92.2
    )
    assert res_downgraded["was_causal_claim_downgraded"] is True
    assert res_downgraded["causal_claim_permitted"] is False
    assert res_downgraded["epistemic_label"] == NON_CAUSAL_DESCRIPTIVE_LABEL

    # 2. Verified Difference-in-Differences (DiD) quasi-experimental study -> causal label permitted
    study_did = EvaluationStudy(
        study_id="STD-TEST-106-DID",
        scheme_id="SCH-TEST-106",
        title="[TEST FIXTURE] Phase-1 vs Non-Phase-1 Schools DiD Evaluation",
        evaluation_type=EvaluationType.CAUSAL_EVALUATION,
        conducting_agency="State Planning Commission (Test Fixture)",
        publication_date="2024-09-15",
        methodology_description="Matched Difference-in-Differences with parallel pre-trends verified.",
        causal_rigor_grade=CausalRigorGrade.GRADE_B_QUASI_EXPERIMENTAL,
        is_causally_identified=True,
        identification_strategy="DID",
        is_test_fixture=True,
    )
    finding_did = EvaluationFinding(
        finding_id="FND-TEST-106-DID",
        study_id=study_did.study_id,
        indicator_id=ind.indicator_id,
        finding_type=FindingType.POSITIVE_IMPACT,
        finding_text="DiD estimate shows +3.8 percentage point attendance increase (p=0.004).",
        quantified_effect=3.8,
        p_value=0.004,
        confidence_level=ConfidenceLevel.VERY_HIGH,
        is_test_fixture=True,
    )
    lim_did = EvaluationLimitation(
        limitation_id="LIM-TEST-106-01",
        study_id=study_did.study_id,
        category=LimitationCategory.EXTERNAL_CONFOUNDING,
        description="Potential spillover to adjacent non-treatment schools.",
        severity="LOW",
        is_test_fixture=True,
    )

    res_causal = PolicyOutcomeAnalysisService.evaluate_finding_epistemic_status(
        study_did, finding_did, ind, baseline_value=88.0, followup_value=91.8, limitations=[lim_did]
    )
    assert res_causal["was_causal_claim_downgraded"] is False
    assert res_causal["causal_claim_permitted"] is True
    assert res_causal["epistemic_label"] == VERIFIED_CAUSAL_LABEL

    # 3. Sensitivity checks: small sample (< 4) vs sufficient sample (>= 4)
    sens_small = PolicyOutcomeAnalysisService.run_outcome_sensitivity_checks(
        ind, [("DIST-1", 3.5), ("DIST-2", 4.0)]
    )
    assert sens_small["status"] == "INSUFFICIENT_DATA_FOR_SENSITIVITY_CHECK"
    assert sens_small["is_robust"] is None

    sens_valid = PolicyOutcomeAnalysisService.run_outcome_sensitivity_checks(
        ind,
        [
            ("DIST-1", 3.5),
            ("DIST-2", 4.0),
            ("DIST-3", 3.8),
            ("DIST-4", 4.2),
            ("DIST-5", 3.9),
        ],
    )
    assert sens_valid["status"] == "SENSITIVITY_COMPLETED"
    assert sens_valid["is_sign_stable_under_leave_one_out"] is True
    assert sens_valid["is_robust"] is True
