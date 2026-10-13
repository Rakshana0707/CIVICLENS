"""
Phase 10.5 — Budget Execution and Implementation Analytics Service.
==================================================================

Connects Phase 10 (Policy Outcome & Impact Evaluation) to Phase 1's budget and scheme
data (`BudgetDepartment`, `BudgetScheme`, `BudgetRecord`, `BudgetStage`, `BudgetSourceDocument`)
and Phase 10's implementation and evaluation models (`PolicyRegistryEntry`,
`PolicyEvaluationPlan`, `ImplementationActivity`, `PolicyIndicator`, `IndicatorObservation`).

Implements 8 core analytical capabilities:
1. Budget Estimate (BE) versus Revised Estimate (RE) analysis, including documented
   supplementary allocations and accounting adjustments where supported by source records.
2. Allocation (BE / RE) versus Actual Expenditure analysis, with strict epistemic guardrails
   that never assume an allocation was spent and never treat underspending alone as proof of
   policy failure or overspending as proof of policy success.
3. Published implementation targets versus reported achievements, respecting target provenance.
4. Planned outputs versus completed outputs (`ImplementationActivity` & `OUTPUT` indicators),
   including Activity Completion Rate (ACR), Output Quantity Completion Ratio (OQCR), and
   Realized Unit Cost (RUC).
5. Year-on-year (YoY) changes using compatible reporting periods, keeping Financial Years
   (e.g., `2023-24`, April 1 – March 31) strictly distinct from Calendar Years (e.g., `2023`).
6. Department-wise and geographic breakdowns where supported by source data.
7. Missing or inconsistent reporting detection across financial and physical records.
8. Explicit metric provenance linking every computed metric to its formula, input lineage,
   and original budget/implementation source documents.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple
from sqlalchemy.orm import Session

from backend.models.budget import (
    BudgetDepartment,
    BudgetScheme,
    BudgetRecord,
    BudgetStage,
    BudgetSourceDocument,
)
from backend.models.policy_evaluation import (
    PolicyRegistryEntry,
    PolicyEvaluationPlan,
    ImplementationActivity,
    PolicyIndicator,
    IndicatorObservation,
    TargetProvenanceType,
    ObservationStage,
)


class IncompatibleReportingPeriodError(ValueError):
    """
    Raised when attempting to compare or trend financial/implementation records across
    incompatible reporting calendar systems (e.g., Financial Year vs Calendar Year)
    or incompatible budget stages.
    """

    def __init__(self, error_code: str, message: str):
        self.error_code = error_code
        super().__init__(f"{error_code}: {message}")


# Regex patterns for strict period classification
_FY_REGEX = re.compile(r"^(?:FY\s*)?(\d{4})-(\d{2}|\d{4})$", re.IGNORECASE)
_CY_REGEX = re.compile(r"^(?:CY\s*)?(\d{4})$", re.IGNORECASE)
_AY_REGEX = re.compile(r"^AY\s*(\d{4})-(\d{2}|\d{4})$", re.IGNORECASE)
_QUARTER_REGEX = re.compile(r"^(?:FY\s*)?(\d{4})-(\d{2}|\d{4})-Q([1-4])$", re.IGNORECASE)

# Explicit currency conversion factors to ₹ Crores (1 Crore = 10^7 INR = 100 Lakhs)
_CURRENCY_TO_CRORE_FACTORS: Dict[str, float] = {
    "RUPEES_CRORE": 1.0,
    "INR_CRORE": 1.0,
    "CRORE": 1.0,
    "CRORES": 1.0,
    "RUPEES_LAKH": 0.01,
    "INR_LAKH": 0.01,
    "LAKH": 0.01,
    "LAKHS": 0.01,
    "RUPEES_THOUSAND": 0.0001,
    "INR_THOUSAND": 0.0001,
    "INR_ABSOLUTE": 1e-7,
}

EPISTEMIC_SPENDING_GUARDRAIL = (
    "EPISTEMIC GUARDRAIL: Financial allocation or expenditure belongs strictly to the INPUT/ACTIVITY "
    "tiers of the Results Chain. Do NOT treat underspending alone as proof of policy failure "
    "(it may reflect phased procurement schedules, unit-cost savings, or treasury release timing), "
    "and do NOT treat 100% absorption or overspending as proof of policy success or public benefit "
    "(it may reflect cost overruns or inflation without commensurate citizen outcomes)."
)


class PolicyBudgetExecutionAnalyticsService:
    """
    Phase 10.5 service connecting Phase 1 budget records and Phase 10 implementation
    outputs with full provenance, formula transparency, and epistemic guardrails.
    """

    # -----------------------------------------------------------------------
    # 0. Period Classification & Currency Normalization Helpers
    # -----------------------------------------------------------------------
    @staticmethod
    def classify_reporting_period(period_str: str) -> Tuple[str, str, Optional[int]]:
        """
        Classifies a period string and keeps Financial Years strictly distinct from Calendar Years.
        Returns `(period_type, canonical_label, start_year_int)`.
        - `FINANCIAL_YEAR`: e.g. `"2023-24"` or `"FY2023-24"` -> `("FINANCIAL_YEAR", "2023-24", 2023)`
        - `CALENDAR_YEAR`: e.g. `"2023"` or `"CY2023"` -> `("CALENDAR_YEAR", "2023", 2023)`
        - `ACADEMIC_YEAR`: e.g. `"AY2023-24"` -> `("ACADEMIC_YEAR", "AY2023-24", 2023)`
        - `FINANCIAL_QUARTER`: e.g. `"2023-24-Q1"` -> `("FINANCIAL_QUARTER", "2023-24-Q1", 2023)`
        """
        if not period_str or not str(period_str).strip():
            raise IncompatibleReportingPeriodError(
                "EMPTY_REPORTING_PERIOD", "Reporting period string cannot be empty."
            )
        raw = str(period_str).strip()

        m_ay = _AY_REGEX.match(raw)
        if m_ay:
            start_yr = int(m_ay.group(1))
            suffix = m_ay.group(2)[-2:]
            return ("ACADEMIC_YEAR", f"AY{start_yr}-{suffix}", start_yr)

        m_q = _QUARTER_REGEX.match(raw)
        if m_q:
            start_yr = int(m_q.group(1))
            suffix = m_q.group(2)[-2:]
            q_num = m_q.group(3)
            return ("FINANCIAL_QUARTER", f"{start_yr}-{suffix}-Q{q_num}", start_yr)

        m_fy = _FY_REGEX.match(raw)
        if m_fy:
            start_yr = int(m_fy.group(1))
            suffix_raw = m_fy.group(2)
            end_yr_two_digit = int(suffix_raw[-2:])
            expected_two_digit = (start_yr + 1) % 100
            if end_yr_two_digit != expected_two_digit:
                raise IncompatibleReportingPeriodError(
                    "MALFORMED_FINANCIAL_YEAR",
                    f"Financial year '{raw}' does not span consecutive years (expected '{start_yr}-{expected_two_digit:02d}').",
                )
            return ("FINANCIAL_YEAR", f"{start_yr}-{expected_two_digit:02d}", start_yr)

        m_cy = _CY_REGEX.match(raw)
        if m_cy:
            yr = int(m_cy.group(1))
            return ("CALENDAR_YEAR", f"{yr}", yr)

        raise IncompatibleReportingPeriodError(
            "UNRECOGNIZED_REPORTING_PERIOD",
            f"Reporting period '{raw}' is not a recognized Financial Year (YYYY-YY) or Calendar Year (YYYY).",
        )

    @staticmethod
    def normalize_amount_to_crore(
        amount: Optional[float], currency_unit: Optional[str] = "RUPEES_CRORE"
    ) -> Tuple[Optional[float], str, bool]:
        """
        Normalizes a budget amount into ₹ Crores using explicit conversion factors.
        Preserves `None` when `amount is None` (never treats missing data as zero).
        Returns `(amount_in_crore, normalized_unit, was_converted)`.
        """
        if amount is None:
            return None, "RUPEES_CRORE", False

        unit_key = (currency_unit or "RUPEES_CRORE").strip().upper()
        if unit_key not in _CURRENCY_TO_CRORE_FACTORS:
            raise ValueError(f"Unsupported currency_unit '{currency_unit}'.")

        factor = _CURRENCY_TO_CRORE_FACTORS[unit_key]
        converted = factor != 1.0
        return round(float(amount) * factor, 4), "RUPEES_CRORE", converted

    @staticmethod
    def extract_source_link(record: BudgetRecord) -> Dict[str, Any]:
        """
        Builds a structured document provenance link from a Phase 1 BudgetRecord
        and its associated BudgetSourceDocument.
        """
        doc: Optional[BudgetSourceDocument] = getattr(record, "source_document", None)
        return {
            "budget_record_id": record.id,
            "financial_year": record.financial_year,
            "budget_stage": (
                record.budget_stage.value
                if hasattr(record.budget_stage, "value")
                else str(record.budget_stage)
            ),
            "source_document_id": record.source_document_id,
            "manifest_dataset_id": doc.manifest_dataset_id if doc else None,
            "title": doc.title if doc else None,
            "official_source_url": doc.official_source_url if doc else None,
            "source_page_number": record.source_page_number,
            "checksum": doc.checksum if doc else None,
            "original_category_text": record.original_category_text,
        }

    # -----------------------------------------------------------------------
    # 1. Budget Estimate (BE) vs Revised Estimate (RE) Analysis
    # -----------------------------------------------------------------------
    @classmethod
    def analyze_be_vs_re(
        cls,
        records: List[BudgetRecord],
        *,
        financial_year: str,
    ) -> Dict[str, Any]:
        """
        Analyzes Budget Estimate (BE) versus Revised Estimate (RE) for a given financial year.
        - Validates that `financial_year` is a genuine Financial Year (distinct from Calendar Year).
        - Handles supplementary allocations and accounting adjustments ONLY when explicitly
          present in `record.source_metadata`.
        - Attaches explicit calculation formulas and source document links.
        """
        p_type, norm_fy, _ = cls.classify_reporting_period(financial_year)
        if p_type != "FINANCIAL_YEAR":
            raise IncompatibleReportingPeriodError(
                "CALENDAR_VS_FINANCIAL_YEAR_MISMATCH",
                f"Budget analysis requires a Financial Year (YYYY-YY), got {p_type} '{financial_year}'.",
            )

        fy_records = [
            r for r in records if cls.classify_reporting_period(r.financial_year)[1] == norm_fy
        ]

        be_records = [r for r in fy_records if r.budget_stage == BudgetStage.budget_estimate]
        re_records = [r for r in fy_records if r.budget_stage == BudgetStage.revised_estimate]

        be_val: Optional[float] = None
        re_val: Optional[float] = None
        supplementary_grant_cr: Optional[float] = None
        accounting_adjustment_notes: List[str] = []
        currency_conversions_applied: List[str] = []
        source_links: List[Dict[str, Any]] = []

        for r in be_records:
            source_links.append(cls.extract_source_link(r))
            val_cr, _, converted = cls.normalize_amount_to_crore(r.amount, r.currency_unit)
            if converted:
                currency_conversions_applied.append(
                    f"BE record {r.id}: converted from {r.currency_unit} to RUPEES_CRORE"
                )
            if val_cr is not None:
                be_val = (be_val or 0.0) + val_cr

        for r in re_records:
            source_links.append(cls.extract_source_link(r))
            val_cr, _, converted = cls.normalize_amount_to_crore(r.amount, r.currency_unit)
            if converted:
                currency_conversions_applied.append(
                    f"RE record {r.id}: converted from {r.currency_unit} to RUPEES_CRORE"
                )
            if val_cr is not None:
                re_val = (re_val or 0.0) + val_cr
            if isinstance(r.source_metadata, dict):
                if "supplementary_grant_cr" in r.source_metadata and r.source_metadata["supplementary_grant_cr"] is not None:
                    supp = float(r.source_metadata["supplementary_grant_cr"])
                    supplementary_grant_cr = (supplementary_grant_cr or 0.0) + supp
                if r.source_metadata.get("accounting_adjustment_note"):
                    accounting_adjustment_notes.append(str(r.source_metadata["accounting_adjustment_note"]))

        if be_val is not None:
            be_val = round(be_val, 4)
        if re_val is not None:
            re_val = round(re_val, 4)

        revision_delta_cr: Optional[float] = None
        revision_rate_pct: Optional[float] = None
        revision_classification = "INCOMPLETE_STAGE_DATA"

        if be_val is not None and re_val is not None:
            revision_delta_cr = round(re_val - be_val, 4)
            if be_val > 0:
                revision_rate_pct = round((revision_delta_cr / be_val) * 100.0, 2)
                if re_val == 0.0:
                    revision_classification = "ALLOCATION_SURRENDERED_MIDYEAR"
                elif revision_delta_cr > 0:
                    revision_classification = "UPWARD_REVISION"
                elif revision_delta_cr < 0:
                    revision_classification = "DOWNWARD_REVISION"
                else:
                    revision_classification = "UNCHANGED_ALLOCATION"
            elif be_val == 0.0 and re_val > 0:
                revision_classification = "UNBUDGETED_MIDYEAR_INTRODUCTION"
            else:
                revision_classification = "UNCHANGED_ZERO_ALLOCATION"

        return {
            "financial_year": norm_fy,
            "period_type": "FINANCIAL_YEAR",
            "unit": "RUPEES_CRORE",
            "budget_estimate_cr": be_val,
            "revised_estimate_cr": re_val,
            "revision_delta_cr": revision_delta_cr,
            "revision_rate_pct": revision_rate_pct,
            "revision_classification": revision_classification,
            "supplementary_grant_cr": supplementary_grant_cr,
            "supplementary_grant_documented": supplementary_grant_cr is not None,
            "accounting_adjustment_notes": accounting_adjustment_notes,
            "currency_conversions_applied": currency_conversions_applied,
            "metric_provenance": {
                "metric_code": "BE_VS_RE_REVISION_RATE",
                "metric_name": "Budget Estimate to Revised Estimate Revision Rate",
                "calculation_formula": "revision_delta_cr = RE - BE; revision_rate_pct = ((RE - BE) / BE) * 100",
                "inputs_used": {
                    "BE_cr": be_val,
                    "RE_cr": re_val,
                    "supplementary_grant_cr": supplementary_grant_cr,
                },
                "source_links": source_links,
            },
        }

    # -----------------------------------------------------------------------
    # 2. Allocation (BE / RE) vs Actual Expenditure Analysis
    # -----------------------------------------------------------------------
    @classmethod
    def analyze_allocation_vs_actual(
        cls,
        records: List[BudgetRecord],
        *,
        financial_year: str,
    ) -> Dict[str, Any]:
        """
        Evaluates Budget Estimate (BE) and Revised Estimate (RE) against Actual Expenditure.
        - NEVER assumes that a budget allocation was spent when Actual Expenditure is missing (`None`).
        - NEVER treats underspending alone as proof of policy failure or overspending as proof of success.
        - Computes Budget Execution Rate (BER), Revised Allocation Absorption Rate (RAAR),
          and Surrender of Funds Ratio (SFR) with full provenance.
        """
        p_type, norm_fy, _ = cls.classify_reporting_period(financial_year)
        if p_type != "FINANCIAL_YEAR":
            raise IncompatibleReportingPeriodError(
                "CALENDAR_VS_FINANCIAL_YEAR_MISMATCH",
                f"Budget execution analysis requires a Financial Year (YYYY-YY), got {p_type} '{financial_year}'.",
            )

        be_re_summary = cls.analyze_be_vs_re(records, financial_year=norm_fy)
        be_val = be_re_summary["budget_estimate_cr"]
        re_val = be_re_summary["revised_estimate_cr"]

        fy_records = [
            r for r in records if cls.classify_reporting_period(r.financial_year)[1] == norm_fy
        ]
        actual_records = [
            r for r in fy_records if r.budget_stage == BudgetStage.actual_expenditure
        ]

        actual_val: Optional[float] = None
        accounting_differences: List[str] = []
        source_links = list(be_re_summary["metric_provenance"]["source_links"])

        for r in actual_records:
            source_links.append(cls.extract_source_link(r))
            val_cr, _, _ = cls.normalize_amount_to_crore(r.amount, r.currency_unit)
            if val_cr is not None:
                actual_val = (actual_val or 0.0) + val_cr
            if isinstance(r.source_metadata, dict) and r.source_metadata.get("accounting_difference_note"):
                accounting_differences.append(str(r.source_metadata["accounting_difference_note"]))

        if actual_val is not None:
            actual_val = round(actual_val, 4)

        ber_pct: Optional[float] = None
        raar_pct: Optional[float] = None
        sfr_pct: Optional[float] = None
        unspent_vs_be_cr: Optional[float] = None
        variance_vs_re_cr: Optional[float] = None
        execution_classification = "ACTUAL_EXPENDITURE_NOT_YET_PUBLISHED"

        if actual_val is not None:
            if be_val is not None:
                unspent_vs_be_cr = round(be_val - actual_val, 4)
                if be_val > 0:
                    ber_pct = round((actual_val / be_val) * 100.0, 2)
                    sfr_pct = round(max(0.0, (be_val - actual_val) / be_val) * 100.0, 2)
                    if ber_pct < 75.0:
                        execution_classification = "SEVERE_UNDERUTILIZATION"
                    elif ber_pct <= 105.0:
                        execution_classification = "NORMAL_EXECUTION"
                    else:
                        execution_classification = "BUDGET_OVERRUN"
                elif be_val == 0.0 and actual_val > 0:
                    execution_classification = "UNBUDGETED_EXPENDITURE"
            if re_val is not None:
                variance_vs_re_cr = round(actual_val - re_val, 4)
                if re_val > 0:
                    raar_pct = round((actual_val / re_val) * 100.0, 2)
                elif re_val == 0.0:
                    execution_classification = "ALLOCATION_SURRENDERED_MIDYEAR"

        return {
            "financial_year": norm_fy,
            "period_type": "FINANCIAL_YEAR",
            "unit": "RUPEES_CRORE",
            "budget_estimate_cr": be_val,
            "revised_estimate_cr": re_val,
            "actual_expenditure_cr": actual_val,
            "is_actual_expenditure_published": actual_val is not None,
            "budget_execution_rate_pct": ber_pct,
            "revised_absorption_rate_pct": raar_pct,
            "surrender_of_funds_ratio_pct": sfr_pct,
            "unspent_vs_be_cr": unspent_vs_be_cr,
            "variance_vs_re_cr": variance_vs_re_cr,
            "execution_classification": execution_classification,
            "accounting_differences": accounting_differences,
            "results_chain_tier": "INPUT",
            "can_infer_policy_success_or_failure_from_spending_alone": False,
            "epistemic_interpretation_guardrail": EPISTEMIC_SPENDING_GUARDRAIL,
            "metric_provenance": {
                "metric_code": "BER_RAAR_SFR",
                "metric_name": "Budget Execution Rate (BER), Revised Absorption Rate (RAAR), and Surrender of Funds Ratio (SFR)",
                "calculation_formula": (
                    "BER = (Actual / BE) * 100; "
                    "RAAR = (Actual / RE) * 100; "
                    "SFR = max(0, (BE - Actual) / BE) * 100"
                ),
                "inputs_used": {
                    "BE_cr": be_val,
                    "RE_cr": re_val,
                    "Actual_cr": actual_val,
                },
                "source_links": source_links,
            },
        }

    # -----------------------------------------------------------------------
    # 3. Published Implementation Targets vs Reported Achievements
    # -----------------------------------------------------------------------
    @classmethod
    def analyze_targets_vs_achievements(
        cls,
        plans: List[PolicyEvaluationPlan],
    ) -> List[Dict[str, Any]]:
        """
        Evaluates published implementation targets against reported achievements across
        PolicyEvaluationPlan records.
        - Distinguishes OFFICIALLY_STATED targets from ANALYST_PROPOSED_BENCHMARK and NO_PUBLISHED_TARGET.
        - Never invents a policy target when target_provenance == NO_PUBLISHED_TARGET.
        - Links every metric to its data source, source_document_ids, and calculation formula.
        """
        results: List[Dict[str, Any]] = []

        for plan in plans:
            prov_str = (
                plan.target_provenance.value
                if hasattr(plan.target_provenance, "value")
                else str(plan.target_provenance)
            )
            t_val = plan.target_value
            a_val = plan.actual_value
            b_val = plan.baseline_value

            ptrr_pct: Optional[float] = None
            target_variance: Optional[float] = None
            distance_to_target_pct: Optional[float] = None
            realization_classification = "INCOMPLETE_DATA"

            if prov_str == TargetProvenanceType.NO_PUBLISHED_TARGET.value or t_val is None:
                realization_classification = "NO_PUBLISHED_TARGET"
            elif t_val <= 0:
                realization_classification = "NON_POSITIVE_TARGET_DENOMINATOR"
            elif a_val is None:
                realization_classification = "ACHIEVEMENT_NOT_YET_REPORTED"
            else:
                target_variance = round(a_val - t_val, 4)
                ptrr_pct = round((a_val / t_val) * 100.0, 2)
                if b_val is not None and (t_val - b_val) != 0:
                    distance_to_target_pct = round(((a_val - b_val) / (t_val - b_val)) * 100.0, 2)

                if ptrr_pct < 50.0:
                    realization_classification = "CRITICAL_DELIVERY_SHORTFALL"
                elif ptrr_pct < 90.0:
                    realization_classification = "PARTIAL_TARGET_ACHIEVEMENT"
                elif ptrr_pct <= 120.0:
                    realization_classification = "TARGET_ACHIEVED"
                else:
                    realization_classification = "TARGET_EXCEEDED_CHECK_DENOMINATOR"

            results.append(
                {
                    "plan_id": plan.plan_id,
                    "policy_id": plan.policy_id,
                    "indicator_id": plan.indicator_id,
                    "evaluation_question": plan.evaluation_question,
                    "comparison_period": plan.comparison_period,
                    "geographic_level": plan.geographic_level,
                    "target_provenance": prov_str,
                    "is_official_government_target": prov_str == TargetProvenanceType.OFFICIALLY_STATED.value,
                    "published_target_value": t_val,
                    "reported_achievement_value": a_val,
                    "baseline_value": b_val,
                    "physical_target_realization_ratio_pct": ptrr_pct,
                    "target_variance": target_variance,
                    "distance_to_target_pct": distance_to_target_pct,
                    "realization_classification": realization_classification,
                    "limitations": plan.limitations,
                    "metric_provenance": {
                        "metric_code": "PTRR_AND_DTM",
                        "metric_name": "Physical Target Realization Ratio (PTRR) & Distance-to-Target Metric (DTM)",
                        "calculation_formula": (
                            "PTRR = (reported_achievement / published_target) * 100; "
                            "DTM = ((reported_achievement - baseline) / (published_target - baseline)) * 100"
                        ),
                        "declared_plan_calculation_method": plan.calculation_method,
                        "inputs_used": {
                            "baseline_value": b_val,
                            "published_target_value": t_val,
                            "reported_achievement_value": a_val,
                        },
                        "data_source": plan.data_source,
                        "target_source_reference": plan.target_source_reference,
                        "source_document_ids": plan.source_document_ids or [],
                    },
                }
            )

        return results

    # -----------------------------------------------------------------------
    # 4. Planned Outputs vs Completed Outputs Analysis
    # -----------------------------------------------------------------------
    @classmethod
    def analyze_planned_vs_completed_outputs(
        cls,
        activities: List[ImplementationActivity],
    ) -> Dict[str, Any]:
        """
        Evaluates planned outputs versus completed outputs across ImplementationActivity records.
        - Never assumes planned outputs were completed when `completed_output_quantity` is None.
        - Never assumes `budget_allocated` was spent when `expenditure_incurred` is None.
        - Computes Activity Completion Rate (ACR), per-unit Output Quantity Completion Ratio (OQCR),
          and Realized Unit Cost (RUC = expenditure_incurred / completed_output_quantity).
        """
        total_activities = len(activities)
        status_counts = {"PLANNED": 0, "IN_PROGRESS": 0, "COMPLETED": 0, "DELAYED": 0}

        # Group physical quantities by output_unit so incompatible units are never summed together
        unit_groups: Dict[str, Dict[str, Any]] = {}
        activity_details: List[Dict[str, Any]] = []
        source_links: List[Dict[str, Any]] = []

        for act in activities:
            st = (act.status or "IN_PROGRESS").strip().upper()
            status_counts[st] = status_counts.get(st, 0) + 1

            planned_q = act.planned_output_quantity
            completed_q = act.completed_output_quantity
            unit = (act.output_unit or "UNSPECIFIED_UNIT").strip().upper()
            alloc_cr = act.budget_allocated
            exp_cr = act.expenditure_incurred

            oqcr_pct: Optional[float] = None
            output_shortfall: Optional[float] = None
            realized_unit_cost_cr: Optional[float] = None

            if planned_q is not None and completed_q is not None and planned_q > 0:
                oqcr_pct = round((completed_q / planned_q) * 100.0, 2)
                output_shortfall = round(planned_q - completed_q, 4)

            if exp_cr is not None and completed_q is not None and completed_q > 0:
                realized_unit_cost_cr = round(exp_cr / completed_q, 6)

            if unit not in unit_groups:
                unit_groups[unit] = {
                    "output_unit": unit,
                    "activity_count": 0,
                    "planned_output_total": 0.0,
                    "completed_output_total": 0.0,
                    "has_missing_planned": False,
                    "has_missing_completed": False,
                }
            ug = unit_groups[unit]
            ug["activity_count"] += 1
            if planned_q is None:
                ug["has_missing_planned"] = True
            else:
                ug["planned_output_total"] = round(ug["planned_output_total"] + planned_q, 4)

            if completed_q is None:
                ug["has_missing_completed"] = True
            else:
                ug["completed_output_total"] = round(ug["completed_output_total"] + completed_q, 4)

            src_entry = {
                "activity_id": act.activity_id,
                "source_document_id": act.source_document_id,
                "source_reference": act.source_reference,
                "source_url": act.source_url,
            }
            source_links.append(src_entry)

            activity_details.append(
                {
                    "activity_id": act.activity_id,
                    "scheme_id": act.scheme_id,
                    "activity_name": act.activity_name,
                    "financial_year": act.financial_year,
                    "department_name": act.department_name,
                    "geographic_level": act.geographic_level,
                    "geographic_unit_id": act.geographic_unit_id,
                    "status": st,
                    "output_unit": unit,
                    "planned_output_quantity": planned_q,
                    "completed_output_quantity": completed_q,
                    "output_completion_ratio_pct": oqcr_pct,
                    "output_shortfall": output_shortfall,
                    "budget_allocated_cr": alloc_cr,
                    "expenditure_incurred_cr": exp_cr,
                    "realized_unit_cost_cr": realized_unit_cost_cr,
                    "source_link": src_entry,
                }
            )

        # Finalize unit-group completion ratios
        for unit, ug in unit_groups.items():
            if ug["has_missing_planned"] or ug["has_missing_completed"] or ug["planned_output_total"] <= 0:
                ug["unit_completion_ratio_pct"] = None
            else:
                ug["unit_completion_ratio_pct"] = round(
                    (ug["completed_output_total"] / ug["planned_output_total"]) * 100.0, 2
                )

        acr_pct = (
            round((status_counts.get("COMPLETED", 0) / total_activities) * 100.0, 2)
            if total_activities > 0
            else None
        )

        return {
            "total_activities": total_activities,
            "status_counts": status_counts,
            "activity_completion_rate_pct": acr_pct,
            "outputs_by_unit": unit_groups,
            "activities": activity_details,
            "results_chain_tier": "OUTPUT",
            "epistemic_note": (
                "Completed physical outputs verify operational delivery (OUTPUT tier) "
                "but do not by themselves prove downstream outcome improvement (OUTCOME tier)."
            ),
            "metric_provenance": {
                "metric_code": "ACR_OQCR_RUC",
                "metric_name": "Activity Completion Rate (ACR), Output Quantity Completion Ratio (OQCR), and Realized Unit Cost (RUC)",
                "calculation_formula": (
                    "ACR = (completed_activities / total_activities) * 100; "
                    "OQCR = (completed_output_quantity / planned_output_quantity) * 100; "
                    "RUC = expenditure_incurred_cr / completed_output_quantity"
                ),
                "source_links": source_links,
            },
        }

    # -----------------------------------------------------------------------
    # 5. Year-on-Year (YoY) Changes Using Compatible Reporting Periods
    # -----------------------------------------------------------------------
    @classmethod
    def analyze_yoy_budget_series(
        cls,
        records: List[BudgetRecord],
        *,
        budget_stage: BudgetStage,
    ) -> Dict[str, Any]:
        """
        Computes year-on-year (YoY) changes for a single BudgetStage across compatible
        Financial Years (`YYYY-YY`).
        - Strictly blocks mixing Calendar Years (`2023`) with Financial Years (`2023-24`).
        - Strictly blocks mixing different BudgetStages in a single YoY trend.
        - Preserves missing years (`None`) rather than coercing missing values to `0.0`.
        """
        if not records:
            return {
                "budget_stage": budget_stage.value,
                "period_type": "FINANCIAL_YEAR",
                "unit": "RUPEES_CRORE",
                "yearly_series": [],
                "metric_provenance": {
                    "metric_code": "YOY_BUDGET_CHANGE",
                    "calculation_formula": "yoy_delta_cr = V_t - V_{t-1}; yoy_pct = ((V_t - V_{t-1}) / V_{t-1}) * 100",
                    "source_links": [],
                },
            }

        grouped_by_fy: Dict[int, Dict[str, Any]] = {}
        all_source_links: List[Dict[str, Any]] = []

        for r in records:
            p_type, norm_label, start_yr = cls.classify_reporting_period(r.financial_year)
            if p_type != "FINANCIAL_YEAR" or start_yr is None:
                raise IncompatibleReportingPeriodError(
                    "CALENDAR_VS_FINANCIAL_YEAR_MISMATCH",
                    f"Cannot compute YoY financial trend with non-financial year '{r.financial_year}' ({p_type}). "
                    "Financial years (April–March, YYYY-YY) must remain distinct from calendar years (YYYY).",
                )
            if r.budget_stage != budget_stage:
                raise IncompatibleReportingPeriodError(
                    "BUDGET_STAGE_MISMATCH",
                    f"Cannot mix stage '{r.budget_stage.value}' into YoY series for '{budget_stage.value}'.",
                )

            val_cr, _, _ = cls.normalize_amount_to_crore(r.amount, r.currency_unit)
            link = cls.extract_source_link(r)
            all_source_links.append(link)

            if start_yr not in grouped_by_fy:
                grouped_by_fy[start_yr] = {
                    "financial_year": norm_label,
                    "start_year": start_yr,
                    "amount_cr": None,
                    "has_null_record": False,
                    "source_links": [],
                }
            entry = grouped_by_fy[start_yr]
            entry["source_links"].append(link)
            if val_cr is None:
                entry["has_null_record"] = True
            else:
                entry["amount_cr"] = round((entry["amount_cr"] or 0.0) + val_cr, 4)

        sorted_years = sorted(grouped_by_fy.keys())
        yearly_series: List[Dict[str, Any]] = []

        prev_year: Optional[int] = None
        prev_amount: Optional[float] = None

        for yr in sorted_years:
            item = grouped_by_fy[yr]
            amt = item["amount_cr"]
            yoy_delta_cr: Optional[float] = None
            yoy_change_pct: Optional[float] = None
            yoy_status = "BASELINE_FIRST_YEAR"

            if prev_year is not None:
                if yr != prev_year + 1:
                    yoy_status = "NON_CONSECUTIVE_YEAR_GAP"
                elif amt is None or prev_amount is None:
                    yoy_status = "MISSING_PERIOD_VALUE"
                else:
                    yoy_delta_cr = round(amt - prev_amount, 4)
                    if prev_amount > 0:
                        yoy_change_pct = round((yoy_delta_cr / prev_amount) * 100.0, 2)
                        yoy_status = "COMPUTED"
                    else:
                        yoy_status = "ZERO_PRIOR_YEAR_BASE"

            yearly_series.append(
                {
                    "financial_year": item["financial_year"],
                    "amount_cr": amt,
                    "yoy_delta_cr": yoy_delta_cr,
                    "yoy_change_pct": yoy_change_pct,
                    "yoy_status": yoy_status,
                    "source_links": item["source_links"],
                }
            )
            prev_year = yr
            prev_amount = amt

        return {
            "budget_stage": budget_stage.value,
            "period_type": "FINANCIAL_YEAR",
            "unit": "RUPEES_CRORE",
            "yearly_series": yearly_series,
            "metric_provenance": {
                "metric_code": "YOY_BUDGET_CHANGE",
                "metric_name": f"Year-on-Year {budget_stage.value} Trend",
                "calculation_formula": "yoy_delta_cr = V_t - V_{t-1}; yoy_change_pct = ((V_t - V_{t-1}) / V_{t-1}) * 100",
                "source_links": all_source_links,
            },
        }

    # -----------------------------------------------------------------------
    # 6. Department-Wise and Geographic Breakdowns
    # -----------------------------------------------------------------------
    @classmethod
    def analyze_department_and_geographic_breakdowns(
        cls,
        budget_records: List[BudgetRecord],
        activities: List[ImplementationActivity],
        *,
        financial_year: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Produces department-wise budget & execution breakdowns and geographic implementation
        breakdowns where supported by the underlying records.
        """
        norm_fy: Optional[str] = None
        if financial_year:
            p_type, norm_fy, _ = cls.classify_reporting_period(financial_year)
            if p_type != "FINANCIAL_YEAR":
                raise IncompatibleReportingPeriodError(
                    "CALENDAR_VS_FINANCIAL_YEAR_MISMATCH",
                    f"Expected Financial Year (YYYY-YY), got '{financial_year}' ({p_type}).",
                )

        # 1. Department-wise budget breakdown
        dept_map: Dict[str, Dict[str, Any]] = {}
        for r in budget_records:
            if norm_fy and cls.classify_reporting_period(r.financial_year)[1] != norm_fy:
                continue
            dept_name = (
                r.scheme.department.name
                if (getattr(r, "scheme", None) and getattr(r.scheme, "department", None))
                else "UNASSIGNED_DEPARTMENT"
            )
            if dept_name not in dept_map:
                dept_map[dept_name] = {
                    "department_name": dept_name,
                    "budget_estimate_cr": None,
                    "revised_estimate_cr": None,
                    "actual_expenditure_cr": None,
                    "missing_actuals_count": 0,
                    "source_links": [],
                }
            d_entry = dept_map[dept_name]
            d_entry["source_links"].append(cls.extract_source_link(r))
            val_cr, _, _ = cls.normalize_amount_to_crore(r.amount, r.currency_unit)

            if r.budget_stage == BudgetStage.budget_estimate and val_cr is not None:
                d_entry["budget_estimate_cr"] = round((d_entry["budget_estimate_cr"] or 0.0) + val_cr, 4)
            elif r.budget_stage == BudgetStage.revised_estimate and val_cr is not None:
                d_entry["revised_estimate_cr"] = round((d_entry["revised_estimate_cr"] or 0.0) + val_cr, 4)
            elif r.budget_stage == BudgetStage.actual_expenditure:
                if val_cr is None:
                    d_entry["missing_actuals_count"] += 1
                else:
                    d_entry["actual_expenditure_cr"] = round((d_entry["actual_expenditure_cr"] or 0.0) + val_cr, 4)

        for dept_name, d_entry in dept_map.items():
            be_v = d_entry["budget_estimate_cr"]
            act_v = d_entry["actual_expenditure_cr"]
            d_entry["budget_execution_rate_pct"] = (
                round((act_v / be_v) * 100.0, 2)
                if (be_v is not None and be_v > 0 and act_v is not None)
                else None
            )

        # 2. Geographic breakdown from ImplementationActivity
        geo_map: Dict[str, Dict[str, Any]] = {}
        has_sub_state = False

        for act in activities:
            if norm_fy and act.financial_year:
                if cls.classify_reporting_period(act.financial_year)[1] != norm_fy:
                    continue
            g_level = (act.geographic_level or "STATE").strip().upper()
            g_unit = (act.geographic_unit_id or "TN-STATE").strip()
            if g_level != "STATE":
                has_sub_state = True

            key = f"{g_level}:{g_unit}"
            if key not in geo_map:
                geo_map[key] = {
                    "geographic_level": g_level,
                    "geographic_unit_id": g_unit,
                    "activity_count": 0,
                    "completed_activity_count": 0,
                    "budget_allocated_cr": None,
                    "expenditure_incurred_cr": None,
                    "planned_output_quantity": None,
                    "completed_output_quantity": None,
                    "source_links": [],
                }
            g_entry = geo_map[key]
            g_entry["activity_count"] += 1
            if (act.status or "").upper() == "COMPLETED":
                g_entry["completed_activity_count"] += 1
            if act.budget_allocated is not None:
                g_entry["budget_allocated_cr"] = round(
                    (g_entry["budget_allocated_cr"] or 0.0) + act.budget_allocated, 4
                )
            if act.expenditure_incurred is not None:
                g_entry["expenditure_incurred_cr"] = round(
                    (g_entry["expenditure_incurred_cr"] or 0.0) + act.expenditure_incurred, 4
                )
            if act.planned_output_quantity is not None:
                g_entry["planned_output_quantity"] = round(
                    (g_entry["planned_output_quantity"] or 0.0) + act.planned_output_quantity, 4
                )
            if act.completed_output_quantity is not None:
                g_entry["completed_output_quantity"] = round(
                    (g_entry["completed_output_quantity"] or 0.0) + act.completed_output_quantity, 4
                )
            g_entry["source_links"].append(
                {
                    "activity_id": act.activity_id,
                    "source_document_id": act.source_document_id,
                    "source_reference": act.source_reference,
                }
            )

        for key, g_entry in geo_map.items():
            p_q = g_entry["planned_output_quantity"]
            c_q = g_entry["completed_output_quantity"]
            g_entry["output_completion_ratio_pct"] = (
                round((c_q / p_q) * 100.0, 2)
                if (p_q is not None and p_q > 0 and c_q is not None)
                else None
            )

        return {
            "financial_year_filter": norm_fy,
            "department_breakdown": dept_map,
            "geographic_breakdown": geo_map,
            "geographic_granularity_support": (
                "SUB_STATE_BREAKDOWN_AVAILABLE" if has_sub_state else "STATE_AGGREGATE_ONLY"
            ),
            "metric_provenance": {
                "metric_code": "DEPT_AND_GEO_BREAKDOWN",
                "calculation_formula": (
                    "Department_BER = (SUM(Dept_Actual) / SUM(Dept_BE)) * 100; "
                    "Geo_OQCR = (SUM(Geo_Completed_Outputs) / SUM(Geo_Planned_Outputs)) * 100"
                ),
            },
        }

    # -----------------------------------------------------------------------
    # 7. Missing or Inconsistent Reporting Detection
    # -----------------------------------------------------------------------
    @classmethod
    def detect_reporting_anomalies_and_gaps(
        cls,
        budget_records: List[BudgetRecord],
        activities: List[ImplementationActivity],
    ) -> List[Dict[str, Any]]:
        """
        Audits budget records and implementation activities to surface missing or
        inconsistent reporting without fabricating missing data:
        1. `MISSING_ACTUAL_EXPENDITURE`: BE or RE exists for a scheme-year, but Actuals is missing/null.
        2. `OVERRUN_WITHOUT_SUPPLEMENTARY_RECORD`: Actual > BE * 1.05 without documented supplementary grant.
        3. `HIGH_EXPENDITURE_WITH_ZERO_OR_MISSING_OUTPUTS`: Activity incurred expenditure > 0,
           but completed_output_quantity is 0 or None.
        4. `COMPLETED_OUTPUTS_WITH_ZERO_OR_MISSING_EXPENDITURE`: Activity reports completed outputs > 0,
           but expenditure_incurred is 0 or None.
        5. `NEGATIVE_BUDGET_ENTRY_WITHOUT_DEDUCTION_NOTE`: Negative amount lacking accounting recovery note.
        """
        anomalies: List[Dict[str, Any]] = []

        # Group budget records by (scheme_id, canonical_fy)
        by_scheme_fy: Dict[Tuple[int, str], List[BudgetRecord]] = {}
        for r in budget_records:
            _, norm_fy, _ = cls.classify_reporting_period(r.financial_year)
            key = (r.scheme_id, norm_fy)
            by_scheme_fy.setdefault(key, []).append(r)

            if r.amount is not None and r.amount < 0:
                has_note = isinstance(r.source_metadata, dict) and bool(
                    r.source_metadata.get("accounting_deduction_or_recovery")
                )
                if not has_note:
                    anomalies.append(
                        {
                            "anomaly_code": "NEGATIVE_BUDGET_ENTRY_WITHOUT_DEDUCTION_NOTE",
                            "severity": "HIGH",
                            "financial_year": norm_fy,
                            "scheme_id": r.scheme_id,
                            "description": (
                                f"Budget record {r.id} has negative amount ({r.amount}) without an "
                                "accounting deduction/recovery note in source_metadata."
                            ),
                            "source_link": cls.extract_source_link(r),
                        }
                    )

        for (scheme_id, norm_fy), recs in by_scheme_fy.items():
            be_recs = [r for r in recs if r.budget_stage == BudgetStage.budget_estimate and r.amount is not None]
            re_recs = [r for r in recs if r.budget_stage == BudgetStage.revised_estimate and r.amount is not None]
            act_recs = [r for r in recs if r.budget_stage == BudgetStage.actual_expenditure and r.amount is not None]

            if (be_recs or re_recs) and not act_recs:
                anomalies.append(
                    {
                        "anomaly_code": "MISSING_ACTUAL_EXPENDITURE",
                        "severity": "MEDIUM",
                        "financial_year": norm_fy,
                        "scheme_id": scheme_id,
                        "description": (
                            f"Scheme {scheme_id} in {norm_fy} has published allocations (BE/RE) "
                            "but no published Actual Expenditure record. Do not assume allocation was spent."
                        ),
                        "source_links": [cls.extract_source_link(r) for r in recs],
                    }
                )

            if be_recs and act_recs:
                be_sum = sum(cls.normalize_amount_to_crore(r.amount, r.currency_unit)[0] or 0.0 for r in be_recs)
                act_sum = sum(cls.normalize_amount_to_crore(r.amount, r.currency_unit)[0] or 0.0 for r in act_recs)
                has_supp = any(
                    isinstance(r.source_metadata, dict) and r.source_metadata.get("supplementary_grant_cr")
                    for r in recs
                )
                if be_sum > 0 and act_sum > be_sum * 1.05 and not has_supp:
                    anomalies.append(
                        {
                            "anomaly_code": "OVERRUN_WITHOUT_SUPPLEMENTARY_RECORD",
                            "severity": "HIGH",
                            "financial_year": norm_fy,
                            "scheme_id": scheme_id,
                            "description": (
                                f"Actual expenditure ({act_sum:.2f} Cr) exceeded Budget Estimate ({be_sum:.2f} Cr) "
                                f"by >5% in {norm_fy} without a documented supplementary grant record."
                            ),
                            "source_links": [cls.extract_source_link(r) for r in recs],
                        }
                    )

        # Cross-check implementation activities
        for act in activities:
            exp = act.expenditure_incurred
            comp = act.completed_output_quantity

            if exp is not None and exp > 0 and (comp is None or comp == 0.0):
                anomalies.append(
                    {
                        "anomaly_code": "HIGH_EXPENDITURE_WITH_ZERO_OR_MISSING_OUTPUTS",
                        "severity": "HIGH",
                        "activity_id": act.activity_id,
                        "scheme_id": act.scheme_id,
                        "financial_year": act.financial_year,
                        "description": (
                            f"Activity '{act.activity_id}' reports expenditure of ₹{exp} Cr "
                            f"but completed_output_quantity is {comp}."
                        ),
                        "source_document_id": act.source_document_id,
                    }
                )
            elif comp is not None and comp > 0 and (exp is None or exp == 0.0):
                anomalies.append(
                    {
                        "anomaly_code": "COMPLETED_OUTPUTS_WITH_ZERO_OR_MISSING_EXPENDITURE",
                        "severity": "MEDIUM",
                        "activity_id": act.activity_id,
                        "scheme_id": act.scheme_id,
                        "financial_year": act.financial_year,
                        "description": (
                            f"Activity '{act.activity_id}' reports {comp} completed outputs "
                            f"but expenditure_incurred is {exp}."
                        ),
                        "source_document_id": act.source_document_id,
                    }
                )

        return anomalies
