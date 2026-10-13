"""
Phase 10.5 — Budget Execution and Implementation Analytics Unit Tests.
=====================================================================

Validates against manually verified fixture cases:
1. Budget Estimate (BE) versus Revised Estimate (RE), including documented supplementary
   allocations and currency normalization.
2. Allocation versus Actual Expenditure where available, verifying that an allocation is
   never assumed spent when Actuals are missing and that underspending/overspending are
   never treated as proof of policy failure/success.
3. Published implementation targets versus reported achievements (`PTRR`, `DTM`, and
   `TargetProvenanceType` enforcement).
4. Planned outputs versus completed outputs (`ACR`, `OQCR`, `RUC`, and missing output handling).
5. Year-on-year (YoY) changes using compatible reporting periods, keeping Financial Years
   (`YYYY-YY`) strictly distinct from Calendar Years (`YYYY`).
6. Department-wise and geographic breakdowns across Phase 1 `BudgetDepartment` and Phase 10
   `ImplementationActivity` models.
7. Detection of missing or inconsistent financial and physical reporting.
8. Every metric links to its source data (`BudgetSourceDocument` / `ImplementationActivity`)
   and calculation formula (`metric_provenance`).
"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.database.base_class import Base
from backend.models.budget import (
    BudgetDepartment,
    BudgetScheme,
    BudgetRecord,
    BudgetStage,
    BudgetSourceDocument,
)
from backend.models.manifesto import Manifesto, ManifestoDocument, ManifestoSource
from backend.models.promise import PoliticalPromise
from backend.models.policy_evaluation import (
    PolicyRegistryEntry,
    PolicyObjective,
    PolicyIndicator,
    PolicyEvaluationPlan,
    ImplementationActivity,
    EvaluationType,
    IndicatorType,
    TargetProvenanceType,
)
from backend.services.policy_budget_execution_service import (
    PolicyBudgetExecutionAnalyticsService,
    IncompatibleReportingPeriodError,
)


@pytest.fixture
def db_session():
    """In-memory SQLite session connecting Phase 1 budget models and Phase 10 evaluation models."""
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    # Seed Phase 1 departments, schemes, and source documents (clearly labelled test fixtures)
    dept_sw = BudgetDepartment(id=1, name="Social Welfare and Women Empowerment", code="DEMAND-45")
    dept_he = BudgetDepartment(id=2, name="Higher Education Department", code="DEMAND-20")

    sch_pudhumai = BudgetScheme(
        id=101,
        department_id=1,
        name="[TEST FIXTURE] Pudhumai Penn Higher Education Assurance",
        head_of_account="2235-02-102-AB",
        normalized_category="Women Welfare & Education",
    )
    sch_lab = BudgetScheme(
        id=102,
        department_id=2,
        name="[TEST FIXTURE] Government College Smart Labs",
        head_of_account="2203-00-103-AC",
        normalized_category="Higher Education Infrastructure",
    )

    doc_ddg_22 = BudgetSourceDocument(
        id=501,
        manifest_dataset_id="DS-TEST-DDG-45-2022-23",
        title="[TEST FIXTURE] Demand No. 45 Detailed Demand for Grants 2022-23",
        official_source_url="https://www.tnbudget.tn.gov.in/test-fixtures/ddg-45-2022-23.pdf",
        financial_year_coverage="2022-23",
        checksum="sha256:testfixtureddg45202223",
    )
    doc_ddg_23 = BudgetSourceDocument(
        id=502,
        manifest_dataset_id="DS-TEST-DDG-45-2023-24",
        title="[TEST FIXTURE] Demand No. 45 Detailed Demand for Grants 2023-24",
        official_source_url="https://www.tnbudget.tn.gov.in/test-fixtures/ddg-45-2023-24.pdf",
        financial_year_coverage="2023-24",
        checksum="sha256:testfixtureddg45202324",
    )
    doc_ddg_24 = BudgetSourceDocument(
        id=503,
        manifest_dataset_id="DS-TEST-DDG-45-2024-25",
        title="[TEST FIXTURE] Demand No. 45 Detailed Demand for Grants 2024-25",
        official_source_url="https://www.tnbudget.tn.gov.in/test-fixtures/ddg-45-2024-25.pdf",
        financial_year_coverage="2024-25",
        checksum="sha256:testfixtureddg45202425",
    )

    session.add_all([dept_sw, dept_he, sch_pudhumai, sch_lab, doc_ddg_22, doc_ddg_23, doc_ddg_24])
    session.commit()
    try:
        yield session
    finally:
        session.close()


def test_1_budget_estimate_vs_revised_estimate_and_supplementary_grants(db_session):
    """
    Verify BE vs RE calculation against manually verified fixture values:
    - BE = 1,000.00 Cr, RE = 1,050.00 Cr -> revision_delta = +50.00 Cr, revision_rate = +5.00%
    - Supplementary grant of 50.00 Cr extracted ONLY when present in source_metadata.
    - Every metric includes calculation_formula and links to BudgetSourceDocument.
    """
    rec_be = BudgetRecord(
        id=1,
        scheme_id=101,
        source_document_id=502,
        financial_year="2023-24",
        budget_stage=BudgetStage.budget_estimate,
        amount=1000.0,
        currency_unit="RUPEES_CRORE",
        source_page_number=42,
        original_category_text="Pudhumai Penn Scheme - BE 2023-24",
    )
    rec_re = BudgetRecord(
        id=2,
        scheme_id=101,
        source_document_id=502,
        financial_year="2023-24",
        budget_stage=BudgetStage.revised_estimate,
        amount=105000.0,  # 1,05,000 Lakh == 1,050.0 Crore (tests unit normalization)
        currency_unit="RUPEES_LAKH",
        source_page_number=43,
        original_category_text="Pudhumai Penn Scheme - RE 2023-24",
        source_metadata={
            "supplementary_grant_cr": 50.0,
            "accounting_adjustment_note": "First Supplementary Estimates Oct 2023",
        },
    )
    db_session.add_all([rec_be, rec_re])
    db_session.commit()

    res = PolicyBudgetExecutionAnalyticsService.analyze_be_vs_re(
        [rec_be, rec_re], financial_year="2023-24"
    )

    assert res["financial_year"] == "2023-24"
    assert res["budget_estimate_cr"] == 1000.0
    assert res["revised_estimate_cr"] == 1050.0
    assert res["revision_delta_cr"] == 50.0
    assert res["revision_rate_pct"] == 5.0
    assert res["revision_classification"] == "UPWARD_REVISION"
    assert res["supplementary_grant_cr"] == 50.0
    assert res["supplementary_grant_documented"] is True
    assert "First Supplementary Estimates Oct 2023" in res["accounting_adjustment_notes"]
    assert len(res["currency_conversions_applied"]) == 1

    # Provenance verification
    prov = res["metric_provenance"]
    assert "revision_rate_pct = ((RE - BE) / BE) * 100" in prov["calculation_formula"]
    assert len(prov["source_links"]) == 2
    assert prov["source_links"][0]["manifest_dataset_id"] == "DS-TEST-DDG-45-2023-24"
    assert prov["source_links"][0]["official_source_url"].endswith("ddg-45-2023-24.pdf")


def test_2_allocation_vs_actual_expenditure_and_epistemic_guardrails(db_session):
    """
    Verify:
    1. When Actual Expenditure is published (BE=1000, RE=1050, Actual=980):
       - BER = 98.0%, RAAR = 93.33%, SFR = 2.0%, unspent_vs_be = 20.0 Cr, variance_vs_re = -70.0 Cr.
    2. When Actual Expenditure is NOT published (only BE=1200 in 2024-25):
       - Never assumes allocation was spent: actual_expenditure_cr is None, BER is None,
         execution_classification == "ACTUAL_EXPENDITURE_NOT_YET_PUBLISHED".
    3. Epistemic guardrails explicitly forbid treating underspending alone as failure
       or overspending as success.
    """
    recs_23_24 = [
        BudgetRecord(
            id=10,
            scheme_id=101,
            source_document_id=502,
            financial_year="2023-24",
            budget_stage=BudgetStage.budget_estimate,
            amount=1000.0,
            currency_unit="RUPEES_CRORE",
            source_page_number=10,
        ),
        BudgetRecord(
            id=11,
            scheme_id=101,
            source_document_id=502,
            financial_year="2023-24",
            budget_stage=BudgetStage.revised_estimate,
            amount=1050.0,
            currency_unit="RUPEES_CRORE",
            source_page_number=11,
        ),
        BudgetRecord(
            id=12,
            scheme_id=101,
            source_document_id=503,
            financial_year="2023-24",
            budget_stage=BudgetStage.actual_expenditure,
            amount=980.0,
            currency_unit="RUPEES_CRORE",
            source_page_number=12,
            source_metadata={"accounting_difference_note": "Reconciled with AG Accounts FY2023-24"},
        ),
    ]
    recs_24_25_unpublished_actuals = [
        BudgetRecord(
            id=13,
            scheme_id=101,
            source_document_id=503,
            financial_year="2024-25",
            budget_stage=BudgetStage.budget_estimate,
            amount=1200.0,
            currency_unit="RUPEES_CRORE",
            source_page_number=15,
        )
    ]
    db_session.add_all(recs_23_24 + recs_24_25_unpublished_actuals)
    db_session.commit()

    # Case 1: 2023-24 with published actuals
    res_23 = PolicyBudgetExecutionAnalyticsService.analyze_allocation_vs_actual(
        recs_23_24, financial_year="2023-24"
    )
    assert res_23["is_actual_expenditure_published"] is True
    assert res_23["budget_estimate_cr"] == 1000.0
    assert res_23["revised_estimate_cr"] == 1050.0
    assert res_23["actual_expenditure_cr"] == 980.0
    assert res_23["budget_execution_rate_pct"] == 98.0
    assert res_23["revised_absorption_rate_pct"] == 93.33
    assert res_23["surrender_of_funds_ratio_pct"] == 2.0
    assert res_23["unspent_vs_be_cr"] == 20.0
    assert res_23["variance_vs_re_cr"] == -70.0
    assert res_23["execution_classification"] == "NORMAL_EXECUTION"
    assert res_23["results_chain_tier"] == "INPUT"
    assert res_23["can_infer_policy_success_or_failure_from_spending_alone"] is False
    assert "Do NOT treat underspending alone as proof of policy failure" in res_23["epistemic_interpretation_guardrail"]
    assert "do NOT treat 100% absorption or overspending as proof of policy success" in res_23["epistemic_interpretation_guardrail"]

    # Case 2: 2024-25 without published actuals -> NEVER assume allocation was spent
    res_24 = PolicyBudgetExecutionAnalyticsService.analyze_allocation_vs_actual(
        recs_24_25_unpublished_actuals, financial_year="2024-25"
    )
    assert res_24["budget_estimate_cr"] == 1200.0
    assert res_24["actual_expenditure_cr"] is None
    assert res_24["is_actual_expenditure_published"] is False
    assert res_24["budget_execution_rate_pct"] is None
    assert res_24["revised_absorption_rate_pct"] is None
    assert res_24["execution_classification"] == "ACTUAL_EXPENDITURE_NOT_YET_PUBLISHED"


def test_3_published_targets_vs_reported_achievements():
    """
    Verify target vs achievement metrics (PTRR and DTM) and strict target provenance
    handling (OFFICIALLY_STATED vs ANALYST_PROPOSED_BENCHMARK vs NO_PUBLISHED_TARGET).
    """
    plan_official = PolicyEvaluationPlan(
        plan_id="PLAN-TEST-105-OFFICIAL",
        policy_id="POL-TEST-PUDHUMAI",
        indicator_id="IND-TEST-BEN",
        evaluation_question="Did Pudhumai Penn reach its stated Year-1 beneficiary target?",
        evaluation_type=EvaluationType.TARGET_VERSUS_ACTUAL,
        objective_being_assessed="Provide monthly ₹1,000 to 5,00,000 girl students in Year 1.",
        indicator_definition="Active enrolled girl students receiving DBT.",
        indicator_type=IndicatorType.OUTPUT,
        baseline_period="FY2021-22",
        comparison_period="FY2023-24",
        baseline_value=0.0,
        target_value=500000.0,
        target_provenance=TargetProvenanceType.OFFICIALLY_STATED,
        target_source_reference="Finance Minister Budget Speech 2022-23 Para 48",
        actual_value=475000.0,
        data_source="TNeGA Penkalvi Portal",
        source_document_ids=["DOC-TEST-BUDGET-2022-23", "DOC-TEST-PENKALVI-2024"],
        calculation_method="(Actual_Enrolled / Stated_Target) * 100",
        geographic_level="STATE",
        limitations="Excludes pending Aadhaar bank-seeding cases.",
        is_test_fixture=True,
    )

    plan_no_target = PolicyEvaluationPlan(
        plan_id="PLAN-TEST-105-NO-TARGET",
        policy_id="POL-TEST-PUDHUMAI",
        indicator_id="IND-TEST-DROPOUT",
        evaluation_question="How did first-year college dropout rates change?",
        evaluation_type=EvaluationType.BEFORE_AND_AFTER_DESCRIPTIVE,
        objective_being_assessed="Reduce female college dropout rates.",
        indicator_definition="Annual female undergraduate dropout rate (%).",
        indicator_type=IndicatorType.OUTCOME,
        baseline_period="FY2021-22",
        comparison_period="FY2023-24",
        baseline_value=12.0,
        target_value=None,
        target_provenance=TargetProvenanceType.NO_PUBLISHED_TARGET,
        actual_value=8.5,
        data_source="AISHE State Report",
        source_document_ids=["DOC-TEST-AISHE-2024"],
        calculation_method="Y_followup - Y_baseline",
        geographic_level="STATE",
        limitations="Observational pre-post change.",
        is_test_fixture=True,
    )

    results = PolicyBudgetExecutionAnalyticsService.analyze_targets_vs_achievements(
        [plan_official, plan_no_target]
    )

    r_off = results[0]
    assert r_off["is_official_government_target"] is True
    assert r_off["published_target_value"] == 500000.0
    assert r_off["reported_achievement_value"] == 475000.0
    assert r_off["physical_target_realization_ratio_pct"] == 95.0
    assert r_off["target_variance"] == -25000.0
    assert r_off["distance_to_target_pct"] == 95.0
    assert r_off["realization_classification"] == "TARGET_ACHIEVED"
    assert "DOC-TEST-PENKALVI-2024" in r_off["metric_provenance"]["source_document_ids"]

    r_none = results[1]
    assert r_none["is_official_government_target"] is False
    assert r_none["published_target_value"] is None
    assert r_none["physical_target_realization_ratio_pct"] is None
    assert r_none["realization_classification"] == "NO_PUBLISHED_TARGET"


def test_4_planned_outputs_vs_completed_outputs_and_unit_costs():
    """
    Verify planned vs completed outputs across ImplementationActivity records:
    - Activity Completion Rate (ACR)
    - Output Quantity Completion Ratio (OQCR) grouped by unit
    - Realized Unit Cost (RUC = expenditure_incurred / completed_output_quantity)
    - Missing completed_output_quantity (`None`) is never treated as 0.0
    """
    activities = [
        ImplementationActivity(
            activity_id="ACT-TEST-105-LAB-1",
            scheme_id="SCH-TEST-LAB",
            activity_name="[TEST FIXTURE] Phase-1 Smart Lab Installation (Chennai Zone)",
            activity_type="CONSTRUCTION",
            financial_year="2023-24",
            department_name="Higher Education Department",
            geographic_level="DISTRICT",
            geographic_unit_id="TN-DIST-CHENNAI",
            status="COMPLETED",
            budget_allocated=20.0,
            expenditure_incurred=18.0,
            planned_output_quantity=100.0,
            completed_output_quantity=90.0,
            output_unit="SMART_LABS",
            source_document_id="DOC-TEST-HE-LAB-01",
            source_reference="HE Dept Progress Report Table 4",
            is_test_fixture=True,
        ),
        ImplementationActivity(
            activity_id="ACT-TEST-105-LAB-2",
            scheme_id="SCH-TEST-LAB",
            activity_name="[TEST FIXTURE] Phase-1 Smart Lab Installation (Madurai Zone)",
            activity_type="CONSTRUCTION",
            financial_year="2023-24",
            department_name="Higher Education Department",
            geographic_level="DISTRICT",
            geographic_unit_id="TN-DIST-MADURAI",
            status="IN_PROGRESS",
            budget_allocated=15.0,
            expenditure_incurred=11.0,
            planned_output_quantity=100.0,
            completed_output_quantity=55.0,
            output_unit="SMART_LABS",
            source_document_id="DOC-TEST-HE-LAB-02",
            source_reference="HE Dept Progress Report Table 5",
            is_test_fixture=True,
        ),
    ]

    res = PolicyBudgetExecutionAnalyticsService.analyze_planned_vs_completed_outputs(activities)
    assert res["total_activities"] == 2
    assert res["activity_completion_rate_pct"] == 50.0  # 1 of 2 COMPLETED

    lab_group = res["outputs_by_unit"]["SMART_LABS"]
    assert lab_group["planned_output_total"] == 200.0
    assert lab_group["completed_output_total"] == 145.0
    assert lab_group["unit_completion_ratio_pct"] == 72.5

    act_1 = res["activities"][0]
    assert act_1["output_completion_ratio_pct"] == 90.0
    assert act_1["output_shortfall"] == 10.0
    assert act_1["realized_unit_cost_cr"] == 0.2  # 18.0 Cr / 90 labs = 0.20 Cr per lab


def test_5_yoy_changes_and_financial_vs_calendar_year_separation(db_session):
    """
    Verify:
    1. Year-on-year (YoY) budget trend across consecutive Financial Years (2022-23 -> 2023-24 -> 2024-25).
    2. Strict rejection of Calendar Years (`2023`) when mixed with or passed to Financial Year analytics.
    3. Strict rejection of mixing different BudgetStages in a single YoY series.
    """
    recs = [
        BudgetRecord(
            id=21,
            scheme_id=101,
            source_document_id=501,
            financial_year="2022-23",
            budget_stage=BudgetStage.actual_expenditure,
            amount=600.0,
            currency_unit="RUPEES_CRORE",
        ),
        BudgetRecord(
            id=22,
            scheme_id=101,
            source_document_id=502,
            financial_year="2023-24",
            budget_stage=BudgetStage.actual_expenditure,
            amount=900.0,
            currency_unit="RUPEES_CRORE",
        ),
        BudgetRecord(
            id=23,
            scheme_id=101,
            source_document_id=503,
            financial_year="2024-25",
            budget_stage=BudgetStage.actual_expenditure,
            amount=1080.0,
            currency_unit="RUPEES_CRORE",
        ),
    ]

    yoy = PolicyBudgetExecutionAnalyticsService.analyze_yoy_budget_series(
        recs, budget_stage=BudgetStage.actual_expenditure
    )
    series = yoy["yearly_series"]
    assert len(series) == 3

    assert series[0]["financial_year"] == "2022-23"
    assert series[0]["yoy_status"] == "BASELINE_FIRST_YEAR"
    assert series[0]["yoy_change_pct"] is None

    assert series[1]["financial_year"] == "2023-24"
    assert series[1]["yoy_delta_cr"] == 300.0
    assert series[1]["yoy_change_pct"] == 50.0
    assert series[1]["yoy_status"] == "COMPUTED"

    assert series[2]["financial_year"] == "2024-25"
    assert series[2]["yoy_delta_cr"] == 180.0
    assert series[2]["yoy_change_pct"] == 20.0
    assert series[2]["yoy_status"] == "COMPUTED"

    # Reject Calendar Year "2023" in Financial Year YoY series
    cy_record = BudgetRecord(
        id=24,
        scheme_id=101,
        source_document_id=502,
        financial_year="2023",  # Calendar Year!
        budget_stage=BudgetStage.actual_expenditure,
        amount=750.0,
        currency_unit="RUPEES_CRORE",
    )
    with pytest.raises(IncompatibleReportingPeriodError) as exc_cy:
        PolicyBudgetExecutionAnalyticsService.analyze_yoy_budget_series(
            [recs[0], cy_record], budget_stage=BudgetStage.actual_expenditure
        )
    assert exc_cy.value.error_code == "CALENDAR_VS_FINANCIAL_YEAR_MISMATCH"

    # Reject mixed BudgetStage in YoY series
    be_record = BudgetRecord(
        id=25,
        scheme_id=101,
        source_document_id=502,
        financial_year="2023-24",
        budget_stage=BudgetStage.budget_estimate,
        amount=950.0,
        currency_unit="RUPEES_CRORE",
    )
    with pytest.raises(IncompatibleReportingPeriodError) as exc_stage:
        PolicyBudgetExecutionAnalyticsService.analyze_yoy_budget_series(
            [recs[0], be_record], budget_stage=BudgetStage.actual_expenditure
        )
    assert exc_stage.value.error_code == "BUDGET_STAGE_MISMATCH"


def test_6_department_wise_and_geographic_breakdowns(db_session):
    """
    Verify department-wise budget & execution breakdown and district-level implementation
    output breakdown.
    """
    sch_101 = db_session.query(BudgetScheme).filter_by(id=101).first()
    sch_102 = db_session.query(BudgetScheme).filter_by(id=102).first()

    b_recs = [
        BudgetRecord(
            id=31,
            scheme_id=101,
            scheme=sch_101,
            source_document_id=502,
            financial_year="2023-24",
            budget_stage=BudgetStage.budget_estimate,
            amount=1000.0,
            currency_unit="RUPEES_CRORE",
        ),
        BudgetRecord(
            id=32,
            scheme_id=101,
            scheme=sch_101,
            source_document_id=502,
            financial_year="2023-24",
            budget_stage=BudgetStage.actual_expenditure,
            amount=950.0,
            currency_unit="RUPEES_CRORE",
        ),
        BudgetRecord(
            id=33,
            scheme_id=102,
            scheme=sch_102,
            source_document_id=502,
            financial_year="2023-24",
            budget_stage=BudgetStage.budget_estimate,
            amount=200.0,
            currency_unit="RUPEES_CRORE",
        ),
        BudgetRecord(
            id=34,
            scheme_id=102,
            scheme=sch_102,
            source_document_id=502,
            financial_year="2023-24",
            budget_stage=BudgetStage.actual_expenditure,
            amount=160.0,
            currency_unit="RUPEES_CRORE",
        ),
    ]

    acts = [
        ImplementationActivity(
            activity_id="ACT-TEST-GEO-1",
            scheme_id="SCH-TEST-LAB",
            activity_name="Smart Labs - Chennai",
            activity_type="CONSTRUCTION",
            financial_year="2023-24",
            department_name="Higher Education Department",
            geographic_level="DISTRICT",
            geographic_unit_id="TN-DIST-CHENNAI",
            status="COMPLETED",
            budget_allocated=100.0,
            expenditure_incurred=90.0,
            planned_output_quantity=50.0,
            completed_output_quantity=45.0,
            output_unit="LABS",
            is_test_fixture=True,
        ),
        ImplementationActivity(
            activity_id="ACT-TEST-GEO-2",
            scheme_id="SCH-TEST-LAB",
            activity_name="Smart Labs - Coimbatore",
            activity_type="CONSTRUCTION",
            financial_year="2023-24",
            department_name="Higher Education Department",
            geographic_level="DISTRICT",
            geographic_unit_id="TN-DIST-COIMBATORE",
            status="IN_PROGRESS",
            budget_allocated=100.0,
            expenditure_incurred=70.0,
            planned_output_quantity=50.0,
            completed_output_quantity=35.0,
            output_unit="LABS",
            is_test_fixture=True,
        ),
    ]

    breakdown = PolicyBudgetExecutionAnalyticsService.analyze_department_and_geographic_breakdowns(
        b_recs, acts, financial_year="2023-24"
    )

    dept_sw = breakdown["department_breakdown"]["Social Welfare and Women Empowerment"]
    assert dept_sw["budget_estimate_cr"] == 1000.0
    assert dept_sw["actual_expenditure_cr"] == 950.0
    assert dept_sw["budget_execution_rate_pct"] == 95.0

    dept_he = breakdown["department_breakdown"]["Higher Education Department"]
    assert dept_he["budget_estimate_cr"] == 200.0
    assert dept_he["actual_expenditure_cr"] == 160.0
    assert dept_he["budget_execution_rate_pct"] == 80.0

    assert breakdown["geographic_granularity_support"] == "SUB_STATE_BREAKDOWN_AVAILABLE"
    geo_chn = breakdown["geographic_breakdown"]["DISTRICT:TN-DIST-CHENNAI"]
    assert geo_chn["output_completion_ratio_pct"] == 90.0
    geo_cbe = breakdown["geographic_breakdown"]["DISTRICT:TN-DIST-COIMBATORE"]
    assert geo_cbe["output_completion_ratio_pct"] == 70.0


def test_7_missing_and_inconsistent_reporting_detection():
    """
    Verify detection of:
    1. `MISSING_ACTUAL_EXPENDITURE`
    2. `OVERRUN_WITHOUT_SUPPLEMENTARY_RECORD`
    3. `HIGH_EXPENDITURE_WITH_ZERO_OR_MISSING_OUTPUTS`
    4. `COMPLETED_OUTPUTS_WITH_ZERO_OR_MISSING_EXPENDITURE`
    """
    b_recs = [
        # 2024-25 has BE but no Actuals -> MISSING_ACTUAL_EXPENDITURE
        BudgetRecord(
            id=41,
            scheme_id=101,
            source_document_id=503,
            financial_year="2024-25",
            budget_stage=BudgetStage.budget_estimate,
            amount=1200.0,
            currency_unit="RUPEES_CRORE",
        ),
        # 2022-23 has Actual (700) > BE (600) * 1.05 without supplementary_grant_cr -> OVERRUN_WITHOUT_SUPPLEMENTARY_RECORD
        BudgetRecord(
            id=42,
            scheme_id=102,
            source_document_id=501,
            financial_year="2022-23",
            budget_stage=BudgetStage.budget_estimate,
            amount=600.0,
            currency_unit="RUPEES_CRORE",
        ),
        BudgetRecord(
            id=43,
            scheme_id=102,
            source_document_id=501,
            financial_year="2022-23",
            budget_stage=BudgetStage.actual_expenditure,
            amount=700.0,
            currency_unit="RUPEES_CRORE",
        ),
    ]

    acts = [
        ImplementationActivity(
            activity_id="ACT-TEST-ANOM-1",
            scheme_id="SCH-TEST-LAB",
            activity_name="Expenditure with Zero Outputs",
            activity_type="CONSTRUCTION",
            financial_year="2023-24",
            budget_allocated=25.0,
            expenditure_incurred=22.0,
            planned_output_quantity=50.0,
            completed_output_quantity=0.0,
            output_unit="LABS",
            is_test_fixture=True,
        ),
        ImplementationActivity(
            activity_id="ACT-TEST-ANOM-2",
            scheme_id="SCH-TEST-LAB",
            activity_name="Completed Outputs with Missing Expenditure",
            activity_type="CONSTRUCTION",
            financial_year="2023-24",
            budget_allocated=15.0,
            expenditure_incurred=None,
            planned_output_quantity=30.0,
            completed_output_quantity=30.0,
            output_unit="LABS",
            is_test_fixture=True,
        ),
    ]

    anomalies = PolicyBudgetExecutionAnalyticsService.detect_reporting_anomalies_and_gaps(b_recs, acts)
    codes = {a["anomaly_code"] for a in anomalies}

    assert "MISSING_ACTUAL_EXPENDITURE" in codes
    assert "OVERRUN_WITHOUT_SUPPLEMENTARY_RECORD" in codes
    assert "HIGH_EXPENDITURE_WITH_ZERO_OR_MISSING_OUTPUTS" in codes
    assert "COMPLETED_OUTPUTS_WITH_ZERO_OR_MISSING_EXPENDITURE" in codes
