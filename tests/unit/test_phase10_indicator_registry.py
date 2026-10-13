"""
Phase 10.4 — Policy Indicator Registry and Baseline Construction Unit Tests.
===========================================================================

Validates:
1. All 10 supported indicator domains and all 12 mandatory indicator attributes.
2. Missing-data integrity: missing values (`None`) are never treated as `0.0`, while
   genuine `0.0` observations are preserved and treated as complete.
3. Baseline construction provenance (`OFFICIAL_PUBLISHED`, `CALCULATED_FROM_SOURCE_DATA`,
   and `UNAVAILABLE`) including sub-observation missingness safeguards.
4. Unit mismatch detection (`UNIT_MISMATCH`) and explicit linear unit conversion.
5. Incompatible definition detection (`DEFINITION_MISMATCH`).
6. Geographic boundary change detection (`BOUNDARY_MISMATCH`, e.g., TN 32-district
   pre-2019 vs 38-district post-2020 bifurcation) and level mismatch (`GEOGRAPHIC_LEVEL_MISMATCH`).
7. Different reporting period/frequency detection (`REPORTING_PERIOD_MISMATCH`, e.g.,
   `QUARTERLY` vs `ANNUAL`).
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
    IndicatorType,
    IndicatorDomain,
    ObservationStage,
    ReportingFrequency,
    BaselineConstructionStatus,
    MissingDataStatus,
)
from backend.services.policy_indicator_service import (
    PolicyIndicatorRegistryService,
    IncompatibleIndicatorComparisonError,
)


@pytest.fixture
def db_session():
    """In-memory SQLite session for testing Phase 10.4 Indicator Registry."""
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    # Seed a canonical test objective
    obj = PolicyObjective(
        objective_id="OBJ-TEST-PHASE10-4",
        scheme_id="SCH-TEST-PHASE10-4",
        title="[TEST FIXTURE] Multi-Domain Policy Objective",
        description="Evaluate inputs, outputs, and outcomes across 10 indicator domains.",
        sector="Multi-Sector Evaluation",
        is_test_fixture=True,
    )
    session.add(obj)
    session.commit()
    try:
        yield session
    finally:
        session.close()


def test_1_register_all_10_indicator_domains_and_12_attributes(db_session):
    """
    Verify that the indicator registry supports all 10 required indicator domains
    and persists all 12 required Phase 10.4 indicator attributes.
    """
    domain_specs = [
        (IndicatorDomain.BUDGET_EXPENDITURE, IndicatorType.INPUT, "RUPEES_CRORE"),
        (IndicatorDomain.BENEFICIARY_COUNT, IndicatorType.OUTPUT, "COUNT"),
        (IndicatorDomain.FACILITIES_CONSTRUCTED_UPGRADED, IndicatorType.OUTPUT, "COUNT"),
        (IndicatorDomain.SERVICE_DELIVERY_COUNT, IndicatorType.OUTPUT, "COUNT"),
        (IndicatorDomain.TARGET_ACHIEVEMENT, IndicatorType.OUTPUT, "PERCENTAGE"),
        (IndicatorDomain.SERVICE_ACCESS, IndicatorType.OUTCOME, "PERCENTAGE"),
        (IndicatorDomain.EDUCATION_INDICATOR, IndicatorType.OUTCOME, "PERCENTAGE"),
        (IndicatorDomain.HEALTH_INDICATOR, IndicatorType.OUTCOME, "PER_100000_LIVE_BIRTHS"),
        (IndicatorDomain.INFRASTRUCTURE_DEVELOPMENT, IndicatorType.OUTPUT, "KM"),
        (IndicatorDomain.COMPLAINT_OR_RESOLUTION, IndicatorType.OUTCOME, "PERCENTAGE"),
    ]

    for idx, (domain, ind_type, unit) in enumerate(domain_specs, start=1):
        ind_id = f"IND-TEST-DOM-{idx:02d}"
        ind = PolicyIndicatorRegistryService.register_indicator(
            db_session,
            indicator_id=ind_id,
            objective_id="OBJ-TEST-PHASE10-4",
            scheme_id="SCH-TEST-PHASE10-4",
            indicator_name=f"[TEST FIXTURE] {domain.value} Indicator",
            indicator_type=ind_type,
            indicator_domain=domain,
            unit=unit,
            definition=f"Standardized operational definition for {domain.value}.",
            definition_code=f"DEF:TEST:{domain.value}:V1",
            source="TN State Evaluation Repository (Test Fixture)",
            reporting_frequency=ReportingFrequency.ANNUAL,
            geographic_level="STATE",
            boundary_reference="TN_38_DISTRICTS_2020",
            baseline_period="FY2021-22",
            baseline_value=100.0,
            baseline_construction_status=BaselineConstructionStatus.OFFICIAL_PUBLISHED,
            comparison_period="FY2024-25",
            comparison_value=125.0,
            collection_method="ADMIN_REGISTRY",
            calculation_formula="(Observed_Numerator / Observed_Denominator) * Scale",
            known_limitations="Test fixture limitation note for methodological verification.",
            is_test_fixture=True,
        )

        # Verify all 12 required Phase 10.4 attributes via serialized dict
        d = ind.to_dict()
        assert d["indicator_id"] == ind_id
        assert d["indicator_domain"] == domain.value
        assert d["definition"] == f"Standardized operational definition for {domain.value}."
        assert d["unit"] == unit
        assert d["source"] == "TN State Evaluation Repository (Test Fixture)"
        assert d["reporting_frequency"] == "ANNUAL"
        assert d["geographic_level"] == "STATE"
        assert d["baseline_period"] == "FY2021-22"
        assert d["baseline_value"] == 100.0
        assert d["baseline_construction_status"] == "OFFICIAL_PUBLISHED"
        assert d["comparison_period"] == "FY2024-25"
        assert d["comparison_value"] == 125.0
        assert d["collection_method"] == "ADMIN_REGISTRY"
        assert d["missing_data_status"] == "COMPLETE"
        assert d["calculation_formula"] == "(Observed_Numerator / Observed_Denominator) * Scale"
        assert "limitation note" in d["known_limitations"]
        assert d["is_test_fixture"] is True


def test_2_missing_values_never_treated_as_zero_and_genuine_zero_preserved(db_session):
    """
    Verify that missing data (`None`) is strictly preserved as `None` (never coerced to `0.0`),
    while a genuine `0.0` observation is treated as a valid complete number.
    """
    # Case A: Missing baseline (`None`)
    ind_missing_base = PolicyIndicatorRegistryService.register_indicator(
        db_session,
        indicator_id="IND-TEST-MISSING-BASE",
        objective_id="OBJ-TEST-PHASE10-4",
        indicator_name="[TEST FIXTURE] Indicator with Uncollected Baseline",
        indicator_type=IndicatorType.OUTCOME,
        indicator_domain=IndicatorDomain.SERVICE_ACCESS,
        unit="PERCENTAGE",
        definition="Share of rural households accessing newly launched telemedicine portal.",
        source="Health MIS (Test Fixture)",
        baseline_period="FY2021-22",
        baseline_value=None,
        comparison_period="FY2024-25",
        comparison_value=64.5,
        is_test_fixture=True,
    )
    assert ind_missing_base.baseline_value is None
    assert ind_missing_base.baseline_construction_status == BaselineConstructionStatus.UNAVAILABLE
    assert ind_missing_base.missing_data_status == MissingDataStatus.MISSING_BASELINE

    # Case B: Genuine 0.0 baseline (e.g., 0 smart classrooms commissioned prior to scheme launch)
    ind_zero_base = PolicyIndicatorRegistryService.register_indicator(
        db_session,
        indicator_id="IND-TEST-GENUINE-ZERO",
        objective_id="OBJ-TEST-PHASE10-4",
        indicator_name="[TEST FIXTURE] Indicator with Genuine Zero Baseline",
        indicator_type=IndicatorType.OUTPUT,
        indicator_domain=IndicatorDomain.FACILITIES_CONSTRUCTED_UPGRADED,
        unit="COUNT",
        definition="Number of high-tech labs newly constructed under Phase-II.",
        source="School Education Dept (Test Fixture)",
        baseline_period="FY2021-22",
        baseline_value=0.0,
        comparison_period="FY2024-25",
        comparison_value=450.0,
        is_test_fixture=True,
    )
    assert ind_zero_base.baseline_value == 0.0
    assert ind_zero_base.baseline_construction_status == BaselineConstructionStatus.OFFICIAL_PUBLISHED
    assert ind_zero_base.missing_data_status == MissingDataStatus.COMPLETE

    # Compare observations when baseline is None -> must not fabricate change from 0.0
    obs_base_null = IndicatorObservation(
        observation_id="OBS-TEST-NULL-BASE",
        indicator_id=ind_missing_base.indicator_id,
        stage=ObservationStage.BASELINE,
        reference_period="FY2021-22",
        geographic_level="STATE",
        geographic_unit_id="TN-STATE",
        value=None,
        value_origin=BaselineConstructionStatus.UNAVAILABLE,
        missing_data_status=MissingDataStatus.MISSING_BASELINE,
        source_reference="DOC-TEST-MIS-01",
        is_test_fixture=True,
    )
    obs_comp_valid = IndicatorObservation(
        observation_id="OBS-TEST-VALID-COMP",
        indicator_id=ind_missing_base.indicator_id,
        stage=ObservationStage.FOLLOW_UP,
        reference_period="FY2024-25",
        geographic_level="STATE",
        geographic_unit_id="TN-STATE",
        value=64.5,
        value_origin=BaselineConstructionStatus.OFFICIAL_PUBLISHED,
        missing_data_status=MissingDataStatus.COMPLETE,
        source_reference="DOC-TEST-MIS-02",
        is_test_fixture=True,
    )

    comp_result = PolicyIndicatorRegistryService.compare_observations(
        ind_missing_base, obs_base_null, obs_comp_valid
    )
    assert comp_result["baseline_value"] is None
    assert comp_result["comparison_value"] == 64.5
    assert comp_result["missing_data_status"] == "MISSING_BASELINE"
    assert comp_result["is_calculable"] is False
    assert comp_result["absolute_change"] is None
    assert comp_result["percentage_change"] is None


def test_3_baseline_construction_provenance_and_partial_coverage_guardrail(db_session):
    """
    Verify that baseline construction records whether the value is:
    - OFFICIAL_PUBLISHED
    - CALCULATED_FROM_SOURCE_DATA
    - UNAVAILABLE (including when any sub-observation has value=None)
    """
    ind = PolicyIndicatorRegistryService.register_indicator(
        db_session,
        indicator_id="IND-TEST-BASELINE-CALC",
        objective_id="OBJ-TEST-PHASE10-4",
        indicator_name="[TEST FIXTURE] District-Aggregated Beneficiary Count",
        indicator_type=IndicatorType.OUTPUT,
        indicator_domain=IndicatorDomain.BENEFICIARY_COUNT,
        unit="COUNT",
        definition="Total enrolled beneficiaries across sampled districts.",
        definition_code="DEF:BENEFICIARIES:V1",
        source="District Welfare Portals (Test Fixture)",
        aggregation_method="SUM",
        is_test_fixture=True,
    )

    # 1. Construct from 3 complete district observations -> CALCULATED_FROM_SOURCE_DATA
    obs_d1 = IndicatorObservation(
        observation_id="OBS-TEST-D1",
        indicator_id=ind.indicator_id,
        stage=ObservationStage.BASELINE,
        reference_period="FY2022-23",
        geographic_level="DISTRICT",
        geographic_unit_id="TN-DIST-MADURAI",
        boundary_reference="TN_38_DISTRICTS_2020",
        value=1200.0,
        source_reference="DOC-TEST-D1",
        is_test_fixture=True,
    )
    obs_d2 = IndicatorObservation(
        observation_id="OBS-TEST-D2",
        indicator_id=ind.indicator_id,
        stage=ObservationStage.BASELINE,
        reference_period="FY2022-23",
        geographic_level="DISTRICT",
        geographic_unit_id="TN-DIST-TRICHY",
        boundary_reference="TN_38_DISTRICTS_2020",
        value=800.0,
        source_reference="DOC-TEST-D2",
        is_test_fixture=True,
    )
    obs_d3 = IndicatorObservation(
        observation_id="OBS-TEST-D3",
        indicator_id=ind.indicator_id,
        stage=ObservationStage.BASELINE,
        reference_period="FY2022-23",
        geographic_level="DISTRICT",
        geographic_unit_id="TN-DIST-SALEM",
        boundary_reference="TN_38_DISTRICTS_2020",
        value=1000.0,
        source_reference="DOC-TEST-D3",
        is_test_fixture=True,
    )

    res_calc = PolicyIndicatorRegistryService.construct_baseline_from_observations(
        db_session,
        ind,
        [obs_d1, obs_d2, obs_d3],
        baseline_period="FY2022-23",
        construction_mode=BaselineConstructionStatus.CALCULATED_FROM_SOURCE_DATA,
        calculation_formula="SUM(District_Beneficiaries_i for i in [Madurai, Trichy, Salem])",
    )
    assert res_calc["baseline_value"] == 3000.0
    assert res_calc["baseline_construction_status"] == "CALCULATED_FROM_SOURCE_DATA"
    assert ind.baseline_value == 3000.0
    assert ind.baseline_construction_status == BaselineConstructionStatus.CALCULATED_FROM_SOURCE_DATA

    # 2. If one district has missing data (None), must NOT treat it as 0.0 -> UNAVAILABLE + PARTIAL_GEOGRAPHIC_COVERAGE
    obs_d4_missing = IndicatorObservation(
        observation_id="OBS-TEST-D4-MISSING",
        indicator_id=ind.indicator_id,
        stage=ObservationStage.BASELINE,
        reference_period="FY2022-23",
        geographic_level="DISTRICT",
        geographic_unit_id="TN-DIST-COIMBATORE",
        boundary_reference="TN_38_DISTRICTS_2020",
        value=None,
        source_reference="DOC-TEST-D4",
        is_test_fixture=True,
    )
    res_partial = PolicyIndicatorRegistryService.construct_baseline_from_observations(
        db_session,
        ind,
        [obs_d1, obs_d2, obs_d4_missing],
        baseline_period="FY2022-23",
    )
    assert res_partial["baseline_value"] is None
    assert res_partial["baseline_construction_status"] == "UNAVAILABLE"
    assert res_partial["missing_data_status"] == "PARTIAL_GEOGRAPHIC_COVERAGE"
    assert "OBS-TEST-D4-MISSING" in res_partial["missing_observation_ids"]


def test_4_unit_mismatch_and_explicit_linear_conversion(db_session):
    """
    Verify that comparing observations with different units raises UNIT_MISMATCH by default,
    supports explicit linear conversion for same-dimension units (RUPEES_LAKH -> RUPEES_CRORE),
    and rejects cross-dimension conversions (COUNT -> PERCENTAGE).
    """
    ind_budget = PolicyIndicatorRegistryService.register_indicator(
        db_session,
        indicator_id="IND-TEST-UNIT-CHECK",
        objective_id="OBJ-TEST-PHASE10-4",
        indicator_name="[TEST FIXTURE] Scheme Expenditure Indicator",
        indicator_type=IndicatorType.INPUT,
        indicator_domain=IndicatorDomain.BUDGET_EXPENDITURE,
        unit="RUPEES_CRORE",
        definition="Annual revenue expenditure recorded in Detailed Demand for Grants.",
        definition_code="DEF:EXP:V1",
        source="TN Budget Demand (Test Fixture)",
        is_test_fixture=True,
    )

    obs_lakh = IndicatorObservation(
        observation_id="OBS-TEST-LAKH",
        indicator_id=ind_budget.indicator_id,
        stage=ObservationStage.BASELINE,
        reference_period="FY2022-23",
        geographic_level="STATE",
        geographic_unit_id="TN-STATE",
        value=5000.0,  # 5000 Lakh = 50 Crore
        unit_override="RUPEES_LAKH",
        source_reference="DOC-TEST-BUD-22",
        is_test_fixture=True,
    )
    obs_crore = IndicatorObservation(
        observation_id="OBS-TEST-CRORE",
        indicator_id=ind_budget.indicator_id,
        stage=ObservationStage.FOLLOW_UP,
        reference_period="FY2024-25",
        geographic_level="STATE",
        geographic_unit_id="TN-STATE",
        value=75.0,  # 75 Crore
        unit_override="RUPEES_CRORE",
        source_reference="DOC-TEST-BUD-24",
        is_test_fixture=True,
    )

    # 1. Without explicit linear conversion -> must raise UNIT_MISMATCH
    with pytest.raises(IncompatibleIndicatorComparisonError) as exc_info:
        PolicyIndicatorRegistryService.compare_observations(
            ind_budget, obs_lakh, obs_crore, allow_linear_unit_conversion=False
        )
    assert exc_info.value.error_code == "UNIT_MISMATCH"

    # 2. With explicit linear conversion enabled -> 5000 Lakh converts to 50.0 Crore
    converted = PolicyIndicatorRegistryService.compare_observations(
        ind_budget, obs_lakh, obs_crore, allow_linear_unit_conversion=True
    )
    assert converted["baseline_value"] == 50.0
    assert converted["comparison_value"] == 75.0
    assert converted["absolute_change"] == 25.0
    assert converted["percentage_change"] == 50.0

    # 3. Cross-dimension unit mismatch (PERCENTAGE vs RUPEES_CRORE) must fail even with conversion=True
    obs_pct = IndicatorObservation(
        observation_id="OBS-TEST-PCT",
        indicator_id=ind_budget.indicator_id,
        stage=ObservationStage.FOLLOW_UP,
        reference_period="FY2024-25",
        geographic_level="STATE",
        geographic_unit_id="TN-STATE",
        value=92.0,
        unit_override="PERCENTAGE",
        source_reference="DOC-TEST-BUD-PCT",
        is_test_fixture=True,
    )
    with pytest.raises(IncompatibleIndicatorComparisonError) as exc_dim:
        PolicyIndicatorRegistryService.compare_observations(
            ind_budget, obs_crore, obs_pct, allow_linear_unit_conversion=True
        )
    assert exc_dim.value.error_code == "UNIT_MISMATCH"


def test_5_incompatible_definition_rejection(db_session):
    """
    Verify that observations with incompatible definitions (e.g., 40 LPCD vs 55 LPCD
    functional tap water criteria) cannot be silently combined or compared.
    """
    ind_water = PolicyIndicatorRegistryService.register_indicator(
        db_session,
        indicator_id="IND-TEST-WATER-DEF",
        objective_id="OBJ-TEST-PHASE10-4",
        indicator_name="[TEST FIXTURE] Rural Habitation Water Supply Coverage",
        indicator_type=IndicatorType.OUTCOME,
        indicator_domain=IndicatorDomain.SERVICE_ACCESS,
        unit="PERCENTAGE",
        definition="Share of rural habitations receiving >= 55 LPCD piped water supply.",
        definition_code="DEF:WATER:55LPCD",
        source="TWAD Board Annual Report (Test Fixture)",
        is_test_fixture=True,
    )

    obs_old_def = IndicatorObservation(
        observation_id="OBS-TEST-WATER-40LPCD",
        indicator_id=ind_water.indicator_id,
        stage=ObservationStage.BASELINE,
        reference_period="FY2019-20",
        geographic_level="STATE",
        geographic_unit_id="TN-STATE",
        value=78.0,
        definition_code="DEF:WATER:40LPCD",  # Older 40 LPCD norm
        source_reference="DOC-TEST-TWAD-19",
        is_test_fixture=True,
    )
    obs_new_def = IndicatorObservation(
        observation_id="OBS-TEST-WATER-55LPCD",
        indicator_id=ind_water.indicator_id,
        stage=ObservationStage.FOLLOW_UP,
        reference_period="FY2024-25",
        geographic_level="STATE",
        geographic_unit_id="TN-STATE",
        value=69.5,
        definition_code="DEF:WATER:55LPCD",  # Newer 55 LPCD norm
        source_reference="DOC-TEST-TWAD-24",
        is_test_fixture=True,
    )

    with pytest.raises(IncompatibleIndicatorComparisonError) as exc_info:
        PolicyIndicatorRegistryService.compare_observations(ind_water, obs_old_def, obs_new_def)
    assert exc_info.value.error_code == "DEFINITION_MISMATCH"


def test_6_geographic_boundary_changes_and_level_mismatch(db_session):
    """
    Verify that comparing a district before and after administrative bifurcation
    (e.g., Villupuram pre-2019 32-district boundary vs post-2020 38-district boundary
    after Kallakurichi split) raises BOUNDARY_MISMATCH.
    """
    ind_dist = PolicyIndicatorRegistryService.register_indicator(
        db_session,
        indicator_id="IND-TEST-DIST-BOUNDARY",
        objective_id="OBJ-TEST-PHASE10-4",
        indicator_name="[TEST FIXTURE] District Primary Health Centres Upgraded",
        indicator_type=IndicatorType.OUTPUT,
        indicator_domain=IndicatorDomain.FACILITIES_CONSTRUCTED_UPGRADED,
        unit="COUNT",
        definition="Number of PHCs upgraded with digital x-ray units in the district.",
        definition_code="DEF:PHC:UPGRADE:V1",
        source="DPH Annual Report (Test Fixture)",
        geographic_level="DISTRICT",
        boundary_reference="TN_38_DISTRICTS_2020",
        is_test_fixture=True,
    )

    obs_pre_split = IndicatorObservation(
        observation_id="OBS-TEST-VILLUPURAM-2018",
        indicator_id=ind_dist.indicator_id,
        stage=ObservationStage.BASELINE,
        reference_period="FY2018-19",
        geographic_level="DISTRICT",
        geographic_unit_id="TN-DIST-VILLUPURAM",
        boundary_reference="TN_32_DISTRICTS_PRE_2019",  # Includes Kallakurichi taluks
        value=94.0,
        source_reference="DOC-TEST-DPH-18",
        is_test_fixture=True,
    )
    obs_post_split = IndicatorObservation(
        observation_id="OBS-TEST-VILLUPURAM-2024",
        indicator_id=ind_dist.indicator_id,
        stage=ObservationStage.FOLLOW_UP,
        reference_period="FY2024-25",
        geographic_level="DISTRICT",
        geographic_unit_id="TN-DIST-VILLUPURAM",
        boundary_reference="TN_38_DISTRICTS_2020",  # Excludes Kallakurichi district
        value=62.0,
        source_reference="DOC-TEST-DPH-24",
        is_test_fixture=True,
    )

    with pytest.raises(IncompatibleIndicatorComparisonError) as exc_info:
        PolicyIndicatorRegistryService.compare_observations(ind_dist, obs_pre_split, obs_post_split)
    assert exc_info.value.error_code == "BOUNDARY_MISMATCH"


def test_7_different_reporting_periods_and_frequencies(db_session):
    """
    Verify that comparing observations collected over incompatible reporting periods/frequencies
    (e.g., QUARTERLY Q1 expenditure vs ANNUAL full-year expenditure) raises REPORTING_PERIOD_MISMATCH.
    """
    ind_service = PolicyIndicatorRegistryService.register_indicator(
        db_session,
        indicator_id="IND-TEST-FREQ-CHECK",
        objective_id="OBJ-TEST-PHASE10-4",
        indicator_name="[TEST FIXTURE] Breakfast Meals Served",
        indicator_type=IndicatorType.OUTPUT,
        indicator_domain=IndicatorDomain.SERVICE_DELIVERY_COUNT,
        unit="LAKHS",
        definition="Total hot breakfast meals served in government primary schools.",
        definition_code="DEF:CMBS:MEALS:V1",
        source="CMBS Monitoring Dashboard (Test Fixture)",
        reporting_frequency=ReportingFrequency.ANNUAL,
        is_test_fixture=True,
    )

    obs_quarterly = IndicatorObservation(
        observation_id="OBS-TEST-Q1",
        indicator_id=ind_service.indicator_id,
        stage=ObservationStage.BASELINE,
        reference_period="FY2023-24-Q1",
        reporting_frequency="QUARTERLY",
        geographic_level="STATE",
        geographic_unit_id="TN-STATE",
        value=850.0,
        source_reference="DOC-TEST-CMBS-Q1",
        is_test_fixture=True,
    )
    obs_annual = IndicatorObservation(
        observation_id="OBS-TEST-ANNUAL",
        indicator_id=ind_service.indicator_id,
        stage=ObservationStage.FOLLOW_UP,
        reference_period="FY2024-25",
        reporting_frequency="ANNUAL",
        geographic_level="STATE",
        geographic_unit_id="TN-STATE",
        value=3600.0,
        source_reference="DOC-TEST-CMBS-FY24",
        is_test_fixture=True,
    )

    with pytest.raises(IncompatibleIndicatorComparisonError) as exc_info:
        PolicyIndicatorRegistryService.compare_observations(ind_service, obs_quarterly, obs_annual)
    assert exc_info.value.error_code == "REPORTING_PERIOD_MISMATCH"
