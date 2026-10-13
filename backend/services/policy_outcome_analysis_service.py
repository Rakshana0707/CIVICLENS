"""
Phase 10.6 — Policy Outcome Analysis and Comparison Methods Service.
====================================================================

Implements descriptive outcome analysis and structured comparison methods using
validated Phase 10 indicators (`PolicyIndicator`, `IndicatorObservation`,
`BeneficiaryGroup`, `EvaluationStudy`, `EvaluationFinding`, `EvaluationLimitation`)
and Phase 10.4 compatibility rules (`PolicyIndicatorRegistryService`).

Supports:
1. Baseline versus follow-up comparisons (`analyze_baseline_vs_followup`)
2. Changes in indicator values (handling zero baselines, negative changes, and
   directional improvement semantics)
3. Target-versus-actual outcome comparisons (`analyze_target_vs_actual_outcome`)
4. Geographic comparisons (`analyze_geographic_comparison`) with mandatory explanations
   of differences in coverage, demographics, and data quality
5. Beneficiary-group comparisons (`analyze_beneficiary_group_comparison`) where valid
   and privacy-safe (enforcing small-cell privacy suppression and small-sample warnings)
6. Trends across compatible reporting periods (`analyze_outcome_trend_series`)
7. Documented evaluation findings (`evaluate_finding_epistemic_status`) with strict
   causal downgrading when causal design/evidence is absent
8. Sensitivity checks (`run_outcome_sensitivity_checks`) where sufficient data exists

Every result reports all 9 mandatory fields:
- `indicator_definition`
- `baseline_value` and `followup_value`
- `absolute_change`
- `percentage_change` (only where mathematically valid; `None` on zero baseline)
- `time_period`
- `geographic_scope`
- `source_references`
- `missing_data_info`
- `interpretation_limitations`
"""

from __future__ import annotations

import math
import statistics
from typing import Any, Dict, List, Optional, Tuple

from backend.models.policy_evaluation import (
    PolicyIndicator,
    IndicatorObservation,
    BeneficiaryGroup,
    EvaluationStudy,
    EvaluationFinding,
    EvaluationLimitation,
    ObservationStage,
    EvaluationType,
    CausalRigorGrade,
    MissingDataStatus,
)
from backend.services.policy_indicator_service import (
    PolicyIndicatorRegistryService,
    IncompatibleIndicatorComparisonError,
)


NON_CAUSAL_DESCRIPTIVE_LABEL = "DESCRIPTIVE_ASSOCIATION_OR_OBSERVED_CHANGE"
VERIFIED_CAUSAL_LABEL = "CAUSAL_IMPACT_ESTIMATE"

NON_CAUSAL_LIMITATION_NOTE = (
    "EPISTEMIC GUARDRAIL: This before-and-after or cross-sectional comparison measures an "
    "OBSERVED CHANGE / DESCRIPTIVE ASSOCIATION only. Do NOT infer that the change was caused "
    "by the policy without a credible counterfactual evaluation design (e.g., RCT, DiD, RDD, IV) "
    "and supporting evidence ruling out macroeconomic trends, concurrent schemes, or selection bias."
)

VALID_CAUSAL_STRATEGIES = {
    "RCT",
    "RANDOMIZED_CONTROLLED_TRIAL",
    "DID",
    "DIFFERENCE_IN_DIFFERENCES",
    "RDD",
    "REGRESSION_DISCONTINUITY",
    "IV",
    "INSTRUMENTAL_VARIABLES",
    "SYNTHETIC_CONTROL",
}

PRIVACY_MIN_CELL_SIZE = 5
SMALL_SAMPLE_WARNING_THRESHOLD = 30
MIN_OBSERVATIONS_FOR_SENSITIVITY = 4


class PolicyOutcomeAnalysisService:
    """
    Phase 10.6 service for evidence-based descriptive outcome analysis, cross-group/geographic
    comparisons, trend analysis, sensitivity checks, and causal-claim epistemic enforcement.
    """

    # -----------------------------------------------------------------------
    # Internal Helpers: Standard 9-Field Result Envelope & Compatibility
    # -----------------------------------------------------------------------
    @staticmethod
    def _build_indicator_definition_block(indicator: PolicyIndicator) -> Dict[str, Any]:
        return {
            "indicator_id": indicator.indicator_id,
            "indicator_name": indicator.indicator_name,
            "indicator_type": (
                indicator.indicator_type.value
                if hasattr(indicator.indicator_type, "value")
                else str(indicator.indicator_type)
            ),
            "indicator_domain": (
                indicator.indicator_domain.value
                if indicator.indicator_domain and hasattr(indicator.indicator_domain, "value")
                else indicator.indicator_domain
            ),
            "definition": indicator.definition or indicator.description,
            "definition_code": indicator.definition_code or f"DEF:{indicator.indicator_id}",
            "unit": indicator.unit,
            "direction_of_improvement": (indicator.direction_of_improvement or "INCREASE").upper(),
            "calculation_formula": indicator.calculation_formula or "DIRECT_OBSERVATION",
        }

    @staticmethod
    def _extract_obs_source_ref(obs: Optional[IndicatorObservation]) -> Optional[Dict[str, Any]]:
        if obs is None:
            return None
        return {
            "observation_id": obs.observation_id,
            "reference_period": obs.reference_period,
            "stage": obs.stage.value if hasattr(obs.stage, "value") else str(obs.stage),
            "source_document_id": obs.source_document_id,
            "source_reference": obs.source_reference,
            "source_url": obs.source_url,
            "document_hash": obs.document_hash,
            "data_quality_status": obs.data_quality_status,
        }

    @staticmethod
    def _compute_change_metrics(
        baseline_val: Optional[float],
        followup_val: Optional[float],
        direction_of_improvement: str = "INCREASE",
    ) -> Dict[str, Any]:
        """
        Computes absolute and percentage change with strict mathematical validity checks:
        - Preserves `None` when either value is missing (never treats missing data as zero).
        - Handles zero baseline (`baseline_val == 0.0`): `absolute_change` is computed,
          `percentage_change` is `None` (`percentage_change_validity = "UNDEFINED_ZERO_BASELINE"`).
        - Handles negative baselines (`baseline_val < 0.0`): `percentage_change` is `None`
          (`percentage_change_validity = "UNDEFINED_NEGATIVE_BASELINE"`).
        - Evaluates qualitative trajectory (`FAVORABLE_CHANGE`, `ADVERSE_CHANGE`, `NO_CHANGE`)
          based on `direction_of_improvement` (`INCREASE` vs `DECREASE`).
        """
        if baseline_val is None or followup_val is None:
            return {
                "is_calculable": False,
                "absolute_change": None,
                "percentage_change": None,
                "percentage_change_validity": "MISSING_INPUT_VALUE",
                "change_direction": "UNKNOWN_DUE_TO_MISSING_DATA",
                "normative_trajectory": "INCONCLUSIVE_MISSING_DATA",
            }

        abs_change = round(float(followup_val) - float(baseline_val), 4)

        if abs_change > 0:
            change_dir = "INCREASE"
        elif abs_change < 0:
            change_dir = "DECREASE"
        else:
            change_dir = "NO_CHANGE"

        desired = (direction_of_improvement or "INCREASE").strip().upper()
        if abs_change == 0.0:
            normative = "NO_CHANGE"
        elif (desired == "INCREASE" and abs_change > 0) or (desired == "DECREASE" and abs_change < 0):
            normative = "FAVORABLE_OBSERVED_CHANGE"
        else:
            normative = "ADVERSE_OBSERVED_CHANGE"

        if baseline_val == 0.0:
            pct_change = None
            pct_validity = "UNDEFINED_ZERO_BASELINE"
        elif baseline_val < 0.0:
            pct_change = None
            pct_validity = "UNDEFINED_NEGATIVE_BASELINE"
        else:
            pct_change = round((abs_change / float(baseline_val)) * 100.0, 2)
            pct_validity = "MATHEMATICALLY_VALID"

        return {
            "is_calculable": True,
            "absolute_change": abs_change,
            "percentage_change": pct_change,
            "percentage_change_validity": pct_validity,
            "change_direction": change_dir,
            "normative_trajectory": normative,
        }

    # -----------------------------------------------------------------------
    # 1. Baseline vs Follow-Up Comparison & Indicator Changes
    # -----------------------------------------------------------------------
    @classmethod
    def analyze_baseline_vs_followup(
        cls,
        indicator: PolicyIndicator,
        baseline_obs: Optional[IndicatorObservation],
        followup_obs: Optional[IndicatorObservation],
        *,
        sample_size: Optional[int] = None,
        allow_linear_unit_conversion: bool = False,
    ) -> Dict[str, Any]:
        """
        Performs a validated baseline-versus-follow-up comparison for a single indicator.
        - Rejects cross-indicator comparisons (`INDICATOR_ID_MISMATCH`), unit mismatches,
          definition mismatches, boundary changes, and reporting frequency mismatches.
        - Always labels the result as `DESCRIPTIVE_ASSOCIATION_OR_OBSERVED_CHANGE` (never
          infers causal impact from a simple before-and-after comparison).
        - Reports all 9 mandatory Phase 10.6 fields.
        """
        for obs in (baseline_obs, followup_obs):
            if obs is not None and obs.indicator_id != indicator.indicator_id:
                raise IncompatibleIndicatorComparisonError(
                    "INDICATOR_ID_MISMATCH",
                    f"Observation '{obs.observation_id}' belongs to indicator '{obs.indicator_id}', "
                    f"not '{indicator.indicator_id}'. Cannot compare incompatible indicators.",
                )

        limitations: List[str] = [NON_CAUSAL_LIMITATION_NOTE]
        if indicator.known_limitations:
            limitations.append(indicator.known_limitations)

        if sample_size is not None and sample_size < SMALL_SAMPLE_WARNING_THRESHOLD:
            limitations.append(
                f"SMALL_SAMPLE_HIGH_VARIANCE_WARNING: Sample size (n={sample_size}) is below "
                f"recommended minimum ({SMALL_SAMPLE_WARNING_THRESHOLD}); observed change has high sampling uncertainty."
            )

        # Handle missing observation objects
        if baseline_obs is None or followup_obs is None:
            b_val = baseline_obs.value if baseline_obs else None
            f_val = followup_obs.value if followup_obs else None
            m_status = PolicyIndicatorRegistryService.determine_missing_data_status(b_val, f_val)
            limitations.append(
                f"Incomplete period coverage ({m_status.value}): change cannot be calculated without both baseline and follow-up observations."
            )
            return {
                "epistemic_label": NON_CAUSAL_DESCRIPTIVE_LABEL,
                "causal_claim_permitted": False,
                "indicator_definition": cls._build_indicator_definition_block(indicator),
                "baseline_value": b_val,
                "followup_value": f_val,
                "absolute_change": None,
                "percentage_change": None,
                "percentage_change_validity": "MISSING_INPUT_VALUE",
                "change_direction": "UNKNOWN_DUE_TO_MISSING_DATA",
                "normative_trajectory": "INCONCLUSIVE_MISSING_DATA",
                "time_period": {
                    "baseline_period": baseline_obs.reference_period if baseline_obs else indicator.baseline_period,
                    "followup_period": followup_obs.reference_period if followup_obs else indicator.comparison_period,
                    "reporting_frequency": (
                        indicator.reporting_frequency.value
                        if hasattr(indicator.reporting_frequency, "value")
                        else str(indicator.reporting_frequency)
                    ),
                },
                "geographic_scope": {
                    "geographic_level": (
                        baseline_obs.geographic_level
                        if baseline_obs
                        else (followup_obs.geographic_level if followup_obs else indicator.geographic_level)
                    ),
                    "geographic_unit_id": (
                        baseline_obs.geographic_unit_id
                        if baseline_obs
                        else (followup_obs.geographic_unit_id if followup_obs else "UNKNOWN")
                    ),
                    "boundary_reference": indicator.boundary_reference,
                },
                "source_references": [
                    ref for ref in (cls._extract_obs_source_ref(baseline_obs), cls._extract_obs_source_ref(followup_obs)) if ref
                ],
                "missing_data_info": {
                    "missing_data_status": m_status.value,
                    "is_complete": False,
                    "missing_baseline": b_val is None,
                    "missing_followup": f_val is None,
                },
                "interpretation_limitations": limitations,
            }

        # Validate compatibility of definitions, units, boundaries, and reporting periods
        norm_base, norm_follow = PolicyIndicatorRegistryService.validate_observation_compatibility(
            indicator=indicator,
            baseline_obs=baseline_obs,
            comparison_obs=followup_obs,
            allow_linear_unit_conversion=allow_linear_unit_conversion,
        )

        m_status = PolicyIndicatorRegistryService.determine_missing_data_status(norm_base, norm_follow)
        change_info = cls._compute_change_metrics(
            norm_base, norm_follow, direction_of_improvement=indicator.direction_of_improvement
        )

        if change_info["percentage_change_validity"] == "UNDEFINED_ZERO_BASELINE":
            limitations.append(
                "ZERO_BASELINE_NOTE: Baseline value is 0.0; absolute change is exact, "
                "but percentage change is mathematically undefined (division by zero) and omitted."
            )
        if not change_info["is_calculable"]:
            limitations.append(
                f"MISSING_OBSERVATION_VALUE: Observation value is null ({m_status.value}); "
                "missing data is never coerced to 0.0."
            )
        if baseline_obs.data_quality_status != "VERIFIED" or followup_obs.data_quality_status != "VERIFIED":
            limitations.append(
                f"DATA_QUALITY_ADVISORY: Observation quality statuses are baseline='{baseline_obs.data_quality_status}', "
                f"followup='{followup_obs.data_quality_status}'."
            )

        return {
            "epistemic_label": NON_CAUSAL_DESCRIPTIVE_LABEL,
            "causal_claim_permitted": False,
            "indicator_definition": cls._build_indicator_definition_block(indicator),
            "baseline_value": norm_base,
            "followup_value": norm_follow,
            "absolute_change": change_info["absolute_change"],
            "percentage_change": change_info["percentage_change"],
            "percentage_change_validity": change_info["percentage_change_validity"],
            "change_direction": change_info["change_direction"],
            "normative_trajectory": change_info["normative_trajectory"],
            "time_period": {
                "baseline_period": baseline_obs.reference_period,
                "followup_period": followup_obs.reference_period,
                "reporting_frequency": (
                    baseline_obs.reporting_frequency
                    or (
                        indicator.reporting_frequency.value
                        if hasattr(indicator.reporting_frequency, "value")
                        else str(indicator.reporting_frequency)
                    )
                ),
            },
            "geographic_scope": {
                "geographic_level": baseline_obs.geographic_level,
                "geographic_unit_id": baseline_obs.geographic_unit_id,
                "boundary_reference": baseline_obs.boundary_reference or indicator.boundary_reference,
            },
            "source_references": [
                cls._extract_obs_source_ref(baseline_obs),
                cls._extract_obs_source_ref(followup_obs),
            ],
            "missing_data_info": {
                "missing_data_status": m_status.value,
                "is_complete": m_status == MissingDataStatus.COMPLETE,
                "missing_baseline": norm_base is None,
                "missing_followup": norm_follow is None,
            },
            "interpretation_limitations": limitations,
        }

    # -----------------------------------------------------------------------
    # 2. Target-versus-Actual Outcome Comparison
    # -----------------------------------------------------------------------
    @classmethod
    def analyze_target_vs_actual_outcome(
        cls,
        indicator: PolicyIndicator,
        baseline_obs: Optional[IndicatorObservation],
        followup_obs: IndicatorObservation,
        target_obs: Optional[IndicatorObservation],
    ) -> Dict[str, Any]:
        """
        Compares an observed outcome follow-up value against a documented TARGET observation
        and optional BASELINE observation, reporting all 9 mandatory fields.
        """
        for obs in (baseline_obs, followup_obs, target_obs):
            if obs is not None and obs.indicator_id != indicator.indicator_id:
                raise IncompatibleIndicatorComparisonError(
                    "INDICATOR_ID_MISMATCH",
                    f"Observation '{obs.observation_id}' does not match indicator '{indicator.indicator_id}'.",
                )

        base_follow = cls.analyze_baseline_vs_followup(indicator, baseline_obs, followup_obs)
        limitations = list(base_follow["interpretation_limitations"])
        source_refs = list(base_follow["source_references"])

        if target_obs is None or target_obs.value is None:
            limitations.append(
                "NO_PUBLISHED_TARGET: No quantitative target observation is available; target achievement cannot be computed."
            )
            base_follow["target_comparison"] = {
                "target_value": None,
                "target_period": target_obs.reference_period if target_obs else None,
                "target_gap": None,
                "target_realization_pct": None,
                "distance_to_target_pct": None,
                "target_status": "NO_PUBLISHED_TARGET",
            }
            base_follow["interpretation_limitations"] = limitations
            return base_follow

        # Validate compatibility between follow-up and target observation
        norm_follow, norm_target = PolicyIndicatorRegistryService.validate_observation_compatibility(
            indicator=indicator,
            baseline_obs=followup_obs,
            comparison_obs=target_obs,
        )
        source_refs.append(cls._extract_obs_source_ref(target_obs))

        target_gap: Optional[float] = None
        target_realization_pct: Optional[float] = None
        dtm_pct: Optional[float] = None
        target_status = "INCOMPLETE_FOLLOWUP"

        if norm_follow is not None and norm_target is not None:
            target_gap = round(norm_follow - norm_target, 4)
            if norm_target > 0:
                target_realization_pct = round((norm_follow / norm_target) * 100.0, 2)
            b_val = base_follow["baseline_value"]
            if b_val is not None and (norm_target - b_val) != 0:
                dtm_pct = round(((norm_follow - b_val) / (norm_target - b_val)) * 100.0, 2)

            desired = (indicator.direction_of_improvement or "INCREASE").upper()
            if (desired == "INCREASE" and norm_follow >= norm_target) or (
                desired == "DECREASE" and norm_follow <= norm_target
            ):
                target_status = "TARGET_MET_OR_EXCEEDED"
            else:
                target_status = "BELOW_STATED_TARGET"

        base_follow["target_comparison"] = {
            "target_value": norm_target,
            "target_period": target_obs.reference_period,
            "target_gap": target_gap,
            "target_realization_pct": target_realization_pct,
            "distance_to_target_pct": dtm_pct,
            "target_status": target_status,
        }
        base_follow["source_references"] = source_refs
        base_follow["interpretation_limitations"] = limitations
        return base_follow

    # -----------------------------------------------------------------------
    # 3. Geographic Comparisons (With Mandatory Context Explanations)
    # -----------------------------------------------------------------------
    @classmethod
    def analyze_geographic_comparison(
        cls,
        indicator: PolicyIndicator,
        baseline_observations: List[IndicatorObservation],
        followup_observations: List[IndicatorObservation],
        *,
        comparability_context: Optional[Dict[str, Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """
        Compares indicator outcomes across multiple geographic units (e.g., districts).
        - Enforces identical indicator_id, definition_code, unit, boundary_reference, and reporting_frequency.
        - Never compares unrelated districts without explaining differences in coverage,
          demographics, and data quality (`comparability_context`). If `comparability_context`
          is missing for compared units, flags `UNEXPLAINED_DEMOGRAPHIC_AND_COVERAGE_DIFFERENCES`
          and marks direct ranking as `UNADJUSTED_DESCRIPTIVE_ONLY`.
        - Reports all 9 mandatory Phase 10.6 fields per district and in the summary.
        """
        base_by_unit = {obs.geographic_unit_id: obs for obs in baseline_observations}
        follow_by_unit = {obs.geographic_unit_id: obs for obs in followup_observations}
        all_units = sorted(set(base_by_unit.keys()) | set(follow_by_unit.keys()))

        expected_bound = indicator.boundary_reference or "TN_38_DISTRICTS_2020"
        unit_results: List[Dict[str, Any]] = []
        valid_followup_vals: List[float] = []
        valid_abs_changes: List[float] = []
        missing_units: List[str] = []
        all_source_refs: List[Dict[str, Any]] = []
        unexplained_units: List[str] = []

        for unit_id in all_units:
            b_obs = base_by_unit.get(unit_id)
            f_obs = follow_by_unit.get(unit_id)

            for obs in (b_obs, f_obs):
                if obs is not None:
                    if obs.indicator_id != indicator.indicator_id:
                        raise IncompatibleIndicatorComparisonError(
                            "INDICATOR_ID_MISMATCH",
                            f"Observation '{obs.observation_id}' belongs to '{obs.indicator_id}', not '{indicator.indicator_id}'.",
                        )
                    if obs.boundary_reference and obs.boundary_reference != expected_bound:
                        raise IncompatibleIndicatorComparisonError(
                            "BOUNDARY_MISMATCH",
                            f"Geographic unit '{unit_id}' uses boundary '{obs.boundary_reference}' vs '{expected_bound}'.",
                        )

            unit_comp = cls.analyze_baseline_vs_followup(indicator, b_obs, f_obs)
            ctx = (comparability_context or {}).get(unit_id)
            if not ctx or not all(k in ctx for k in ("coverage_note", "demographic_context", "data_quality_note")):
                unexplained_units.append(unit_id)
                unit_comp["interpretation_limitations"].append(
                    f"UNEXPLAINED_CONTEXT_DIFFERENCE: Unit '{unit_id}' lacks complete coverage, demographic, "
                    "and data-quality context notes; do not interpret cross-district gaps as pure policy performance."
                )
            else:
                unit_comp["comparability_context"] = ctx
                unit_comp["interpretation_limitations"].append(
                    f"Cross-district context ({unit_id}): coverage='{ctx['coverage_note']}', "
                    f"demographics='{ctx['demographic_context']}', data_quality='{ctx['data_quality_note']}'."
                )

            unit_results.append(unit_comp)
            all_source_refs.extend(unit_comp["source_references"])

            if unit_comp["followup_value"] is not None:
                valid_followup_vals.append(float(unit_comp["followup_value"]))
            else:
                missing_units.append(unit_id)

            if unit_comp["absolute_change"] is not None:
                valid_abs_changes.append(float(unit_comp["absolute_change"]))

        # Compute spatial dispersion metrics across valid follow-up values
        mean_followup = round(statistics.mean(valid_followup_vals), 4) if valid_followup_vals else None
        mean_baseline_vals = [
            float(u["baseline_value"]) for u in unit_results if u["baseline_value"] is not None
        ]
        mean_baseline = round(statistics.mean(mean_baseline_vals), 4) if mean_baseline_vals else None

        cv_geo_pct: Optional[float] = None
        if len(valid_followup_vals) >= 2 and mean_followup and mean_followup > 0:
            stdev_val = statistics.stdev(valid_followup_vals)
            cv_geo_pct = round((stdev_val / mean_followup) * 100.0, 2)

        global_limitations = [
            NON_CAUSAL_LIMITATION_NOTE,
            "GEOGRAPHIC_HETEROGENEITY_NOTE: Cross-district outcome differences reflect baseline urbanization, "
            "demographic structure, historical infrastructure, and administrative reporting completeness in addition to scheme execution.",
        ]
        if unexplained_units:
            global_limitations.append(
                f"UNEXPLAINED_POPULATION_OR_GEOGRAPHIC_HETEROGENEITY: Units {unexplained_units} were compared "
                "without complete coverage, demographic, and data quality context metadata."
            )

        agg_change = cls._compute_change_metrics(
            mean_baseline, mean_followup, direction_of_improvement=indicator.direction_of_improvement
        )

        return {
            "epistemic_label": NON_CAUSAL_DESCRIPTIVE_LABEL,
            "causal_claim_permitted": False,
            "indicator_definition": cls._build_indicator_definition_block(indicator),
            "baseline_value": mean_baseline,
            "followup_value": mean_followup,
            "absolute_change": agg_change["absolute_change"],
            "percentage_change": agg_change["percentage_change"],
            "percentage_change_validity": agg_change["percentage_change_validity"],
            "coefficient_of_variation_pct": cv_geo_pct,
            "time_period": {
                "baseline_period": baseline_observations[0].reference_period if baseline_observations else None,
                "followup_period": followup_observations[0].reference_period if followup_observations else None,
            },
            "geographic_scope": {
                "geographic_level": "DISTRICT",
                "boundary_reference": expected_bound,
                "total_units_evaluated": len(all_units),
                "units_with_complete_followup": len(valid_followup_vals),
            },
            "source_references": all_source_refs,
            "missing_data_info": {
                "missing_data_status": (
                    MissingDataStatus.PARTIAL_GEOGRAPHIC_COVERAGE.value
                    if missing_units
                    else MissingDataStatus.COMPLETE.value
                ),
                "missing_units": missing_units,
                "is_complete": len(missing_units) == 0 and len(all_units) > 0,
            },
            "interpretation_limitations": global_limitations,
            "has_complete_comparability_context": len(unexplained_units) == 0,
            "unit_comparisons": unit_results,
        }

    # -----------------------------------------------------------------------
    # 4. Beneficiary-Group Comparisons (Privacy-Safe & Context-Aware)
    # -----------------------------------------------------------------------
    @classmethod
    def analyze_beneficiary_group_comparison(
        cls,
        indicator: PolicyIndicator,
        group_observations: List[Dict[str, Any]],
        *,
        privacy_min_cell_size: int = PRIVACY_MIN_CELL_SIZE,
    ) -> Dict[str, Any]:
        """
        Compares indicator outcomes or coverage across BeneficiaryGroup strata where valid
        and privacy-safe.
        Each item in `group_observations` contains:
        - `group`: `BeneficiaryGroup` instance (or dict with `group_id`, `name`, `eligibility_criteria`, `estimated_eligible_population`)
        - `baseline_value`: Optional[float]
        - `followup_value`: Optional[float]
        - `sample_or_cell_count`: int (number of individuals/observations in cell)
        - `population_share_pct`: Optional[float]
        - `beneficiary_share_pct`: Optional[float]
        - `coverage_and_demographic_note`: Optional[str]
        - `source_reference`: str

        Enforces:
        1. Privacy suppression (`PRIVACY_SUPPRESSED_SMALL_CELL`) when `sample_or_cell_count < privacy_min_cell_size`.
        2. Small-sample warning (`SMALL_SAMPLE_HIGH_VARIANCE_WARNING`) when `sample_or_cell_count < 30`.
        3. Demographic/eligibility explanation requirement across groups.
        """
        evaluated_groups: List[Dict[str, Any]] = []
        suppressed_groups: List[str] = []
        small_sample_groups: List[str] = []
        source_refs: List[Dict[str, Any]] = []
        limitations: List[str] = [
            NON_CAUSAL_LIMITATION_NOTE,
            "BENEFICIARY_GROUP_COMPARISON_NOTE: Differences across beneficiary groups may reflect "
            "divergent baseline socioeconomic vulnerability, eligibility thresholds, and historical access gaps.",
        ]

        for entry in group_observations:
            grp = entry["group"]
            group_id = grp.group_id if hasattr(grp, "group_id") else grp["group_id"]
            group_name = grp.name if hasattr(grp, "name") else grp["name"]
            eligibility = (
                grp.eligibility_criteria if hasattr(grp, "eligibility_criteria") else grp.get("eligibility_criteria")
            )
            eligible_pop = (
                grp.estimated_eligible_population
                if hasattr(grp, "estimated_eligible_population")
                else grp.get("estimated_eligible_population")
            )

            cell_count = entry.get("sample_or_cell_count", 0)
            b_val = entry.get("baseline_value")
            f_val = entry.get("followup_value")
            pop_share = entry.get("population_share_pct")
            ben_share = entry.get("beneficiary_share_pct")
            ctx_note = entry.get("coverage_and_demographic_note")
            src_ref = entry.get("source_reference", "Unspecified Group Source")

            source_refs.append({"group_id": group_id, "source_reference": src_ref})

            # 1. Privacy small-cell suppression check
            if cell_count is not None and cell_count < privacy_min_cell_size:
                suppressed_groups.append(group_id)
                evaluated_groups.append(
                    {
                        "group_id": group_id,
                        "group_name": group_name,
                        "privacy_status": "PRIVACY_SUPPRESSED_SMALL_CELL",
                        "sample_or_cell_count": None,  # Exact small count masked
                        "baseline_value": None,
                        "followup_value": None,
                        "absolute_change": None,
                        "percentage_change": None,
                        "demographic_parity_index": None,
                        "group_limitations": [
                            f"PRIVACY_SUPPRESSED_SMALL_CELL: Cell count (<{privacy_min_cell_size}) suppressed "
                            "to prevent re-identification and unreliable micro-cell inference."
                        ],
                    }
                )
                continue

            grp_lims: List[str] = []
            if cell_count is not None and cell_count < SMALL_SAMPLE_WARNING_THRESHOLD:
                small_sample_groups.append(group_id)
                grp_lims.append(
                    f"SMALL_SAMPLE_HIGH_VARIANCE_WARNING: Group sample size (n={cell_count}) is below "
                    f"{SMALL_SAMPLE_WARNING_THRESHOLD}; interpret group differences with caution."
                )

            if not ctx_note:
                grp_lims.append(
                    f"MISSING_DEMOGRAPHIC_CONTEXT_NOTE: Group '{group_id}' lacks an explicit explanation "
                    "of demographic, coverage, and data quality differences."
                )

            change_info = cls._compute_change_metrics(
                b_val, f_val, direction_of_improvement=indicator.direction_of_improvement
            )

            dpi: Optional[float] = None
            if pop_share is not None and pop_share > 0 and ben_share is not None:
                dpi = round(ben_share / pop_share, 3)

            evaluated_groups.append(
                {
                    "group_id": group_id,
                    "group_name": group_name,
                    "eligibility_criteria": eligibility,
                    "estimated_eligible_population": eligible_pop,
                    "privacy_status": "PRIVACY_SAFE_AGGREGATE",
                    "sample_or_cell_count": cell_count,
                    "baseline_value": b_val,
                    "followup_value": f_val,
                    "absolute_change": change_info["absolute_change"],
                    "percentage_change": change_info["percentage_change"],
                    "percentage_change_validity": change_info["percentage_change_validity"],
                    "demographic_parity_index": dpi,
                    "coverage_and_demographic_note": ctx_note,
                    "group_limitations": grp_lims,
                }
            )

        if suppressed_groups:
            limitations.append(
                f"PRIVACY_PROTECTION_APPLIED: {len(suppressed_groups)} group(s) ({suppressed_groups}) had cell "
                f"counts below k={privacy_min_cell_size} and were suppressed."
            )
        if small_sample_groups:
            limitations.append(
                f"SMALL_SAMPLE_WARNING: Group(s) {small_sample_groups} have sample sizes below {SMALL_SAMPLE_WARNING_THRESHOLD}."
            )

        valid_b = [g["baseline_value"] for g in evaluated_groups if g["baseline_value"] is not None]
        valid_f = [g["followup_value"] for g in evaluated_groups if g["followup_value"] is not None]
        mean_b = round(statistics.mean(valid_b), 4) if valid_b else None
        mean_f = round(statistics.mean(valid_f), 4) if valid_f else None
        overall_change = cls._compute_change_metrics(
            mean_b, mean_f, direction_of_improvement=indicator.direction_of_improvement
        )

        return {
            "epistemic_label": NON_CAUSAL_DESCRIPTIVE_LABEL,
            "causal_claim_permitted": False,
            "indicator_definition": cls._build_indicator_definition_block(indicator),
            "baseline_value": mean_b,
            "followup_value": mean_f,
            "absolute_change": overall_change["absolute_change"],
            "percentage_change": overall_change["percentage_change"],
            "time_period": {
                "baseline_period": indicator.baseline_period,
                "followup_period": indicator.comparison_period,
            },
            "geographic_scope": {
                "geographic_level": indicator.geographic_level,
                "boundary_reference": indicator.boundary_reference,
            },
            "source_references": source_refs,
            "missing_data_info": {
                "suppressed_group_ids": suppressed_groups,
                "is_complete": len(suppressed_groups) == 0 and len(valid_f) == len(group_observations),
            },
            "interpretation_limitations": limitations,
            "group_comparisons": evaluated_groups,
        }

    # -----------------------------------------------------------------------
    # 5. Trends Across Compatible Reporting Periods
    # -----------------------------------------------------------------------
    @classmethod
    def analyze_outcome_trend_series(
        cls,
        indicator: PolicyIndicator,
        observations: List[IndicatorObservation],
        *,
        expected_periods: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Analyzes multi-period indicator trends across compatible reporting periods.
        - Validates that all observations belong to the same indicator, unit, definition,
          geographic unit, boundary reference, and reporting frequency.
        - Detects incomplete periods (`expected_periods` missing from `observations` or
          observations with `value=None`) without interpolating or treating missing data as zero.
        - Reports all 9 mandatory Phase 10.6 fields.
        """
        if not observations:
            return {
                "epistemic_label": NON_CAUSAL_DESCRIPTIVE_LABEL,
                "causal_claim_permitted": False,
                "indicator_definition": cls._build_indicator_definition_block(indicator),
                "baseline_value": None,
                "followup_value": None,
                "absolute_change": None,
                "percentage_change": None,
                "time_period": {"periods_evaluated": [], "missing_periods": expected_periods or []},
                "geographic_scope": {"geographic_level": indicator.geographic_level},
                "source_references": [],
                "missing_data_info": {"missing_data_status": "MISSING_BOTH", "is_complete": False},
                "interpretation_limitations": [NON_CAUSAL_LIMITATION_NOTE, "No observations provided."],
                "trend_points": [],
            }

        first_obs = observations[0]
        for obs in observations[1:]:
            if obs.indicator_id != indicator.indicator_id or first_obs.indicator_id != indicator.indicator_id:
                raise IncompatibleIndicatorComparisonError(
                    "INDICATOR_ID_MISMATCH", "All trend observations must belong to the same indicator."
                )
            PolicyIndicatorRegistryService.validate_observation_compatibility(
                indicator=indicator, baseline_obs=first_obs, comparison_obs=obs
            )

        obs_by_period = {obs.reference_period: obs for obs in observations}
        ordered_periods = expected_periods if expected_periods else sorted(obs_by_period.keys())

        trend_points: List[Dict[str, Any]] = []
        missing_periods: List[str] = []
        source_refs: List[Dict[str, Any]] = []
        prev_val: Optional[float] = None
        prev_period_had_gap = False

        for period in ordered_periods:
            obs = obs_by_period.get(period)
            if obs is None or obs.value is None:
                missing_periods.append(period)
                trend_points.append(
                    {
                        "reference_period": period,
                        "value": None,
                        "period_over_period_change": None,
                        "period_over_period_pct": None,
                        "status": "MISSING_PERIOD_OBSERVATION",
                    }
                )
                prev_val = None
                prev_period_had_gap = True
                continue

            source_refs.append(cls._extract_obs_source_ref(obs))
            val = float(obs.value)
            pop_change: Optional[float] = None
            pop_pct: Optional[float] = None
            pt_status = "OBSERVED"

            if prev_val is not None and not prev_period_had_gap:
                pop_change = round(val - prev_val, 4)
                if prev_val > 0:
                    pop_pct = round((pop_change / prev_val) * 100.0, 2)
                elif prev_val == 0.0:
                    pt_status = "OBSERVED_AFTER_ZERO_BASE"
            elif prev_period_had_gap:
                pt_status = "OBSERVED_AFTER_MISSING_GAP"

            trend_points.append(
                {
                    "reference_period": period,
                    "value": val,
                    "period_over_period_change": pop_change,
                    "period_over_period_pct": pop_pct,
                    "status": pt_status,
                }
            )
            prev_val = val
            prev_period_had_gap = False

        first_point = trend_points[0]["value"] if trend_points else None
        last_point = trend_points[-1]["value"] if trend_points else None
        overall_change = cls._compute_change_metrics(
            first_point, last_point, direction_of_improvement=indicator.direction_of_improvement
        )

        limitations = [NON_CAUSAL_LIMITATION_NOTE]
        if missing_periods:
            limitations.append(
                f"INCOMPLETE_TIME_SERIES: Missing observations for period(s) {missing_periods}; "
                "values were preserved as None and never interpolated or set to zero."
            )

        return {
            "epistemic_label": NON_CAUSAL_DESCRIPTIVE_LABEL,
            "causal_claim_permitted": False,
            "indicator_definition": cls._build_indicator_definition_block(indicator),
            "baseline_value": first_point,
            "followup_value": last_point,
            "absolute_change": overall_change["absolute_change"],
            "percentage_change": overall_change["percentage_change"],
            "percentage_change_validity": overall_change["percentage_change_validity"],
            "time_period": {
                "start_period": ordered_periods[0] if ordered_periods else None,
                "end_period": ordered_periods[-1] if ordered_periods else None,
                "periods_evaluated": ordered_periods,
            },
            "geographic_scope": {
                "geographic_level": first_obs.geographic_level,
                "geographic_unit_id": first_obs.geographic_unit_id,
                "boundary_reference": first_obs.boundary_reference or indicator.boundary_reference,
            },
            "source_references": source_refs,
            "missing_data_info": {
                "missing_periods": missing_periods,
                "is_complete": len(missing_periods) == 0,
            },
            "interpretation_limitations": limitations,
            "trend_points": trend_points,
        }

    # -----------------------------------------------------------------------
    # 6. Documented Evaluation Findings & Causal Downgrading Guardrail
    # -----------------------------------------------------------------------
    @classmethod
    def evaluate_finding_epistemic_status(
        cls,
        study: EvaluationStudy,
        finding: EvaluationFinding,
        indicator: PolicyIndicator,
        *,
        baseline_value: Optional[float] = None,
        followup_value: Optional[float] = None,
        limitations: Optional[List[EvaluationLimitation]] = None,
    ) -> Dict[str, Any]:
        """
        Evaluates a documented `EvaluationStudy` and `EvaluationFinding` and enforces
        strict causal identification rules:
        - A result can ONLY be labelled `CAUSAL_IMPACT_ESTIMATE` if:
          1. `study.evaluation_type == EvaluationType.CAUSAL_EVALUATION`
          2. `study.causal_rigor_grade` is `GRADE_A_EXPERIMENTAL` or `GRADE_B_QUASI_EXPERIMENTAL`
          3. `study.is_causally_identified is True`
          4. `study.identification_strategy` is in `VALID_CAUSAL_STRATEGIES` (e.g., RCT, DID, RDD, IV)
        - Otherwise, even if the study claims causal impact, it is automatically downgraded
          to `DESCRIPTIVE_ASSOCIATION_OR_OBSERVED_CHANGE` (`causal_claim_permitted = False`).
        """
        eval_type = (
            study.evaluation_type
            if isinstance(study.evaluation_type, EvaluationType)
            else EvaluationType.from_string(study.evaluation_type)
        )
        rigor_grade = (
            study.causal_rigor_grade
            if isinstance(study.causal_rigor_grade, CausalRigorGrade)
            else CausalRigorGrade.from_string(study.causal_rigor_grade)
        )
        strategy = (study.identification_strategy or "NONE").strip().upper()

        has_valid_causal_design = (
            eval_type == EvaluationType.CAUSAL_EVALUATION
            and rigor_grade
            in (CausalRigorGrade.GRADE_A_EXPERIMENTAL, CausalRigorGrade.GRADE_B_QUASI_EXPERIMENTAL)
            and bool(study.is_causally_identified)
            and strategy in VALID_CAUSAL_STRATEGIES
        )

        was_downgraded = False
        downgrade_reason: Optional[str] = None
        if eval_type == EvaluationType.CAUSAL_EVALUATION and not has_valid_causal_design:
            was_downgraded = True
            downgrade_reason = (
                f"Study '{study.study_id}' requested CAUSAL_EVALUATION but lacks verified counterfactual "
                f"identification (rigor={rigor_grade.value}, is_causally_identified={study.is_causally_identified}, "
                f"strategy='{strategy}'). Automatically downgraded to {NON_CAUSAL_DESCRIPTIVE_LABEL}."
            )
            effective_rigor = CausalRigorGrade.GRADE_D_DESCRIPTIVE_CORRELATIONAL.value
        else:
            effective_rigor = rigor_grade.value

        epistemic_label = VERIFIED_CAUSAL_LABEL if has_valid_causal_design else NON_CAUSAL_DESCRIPTIVE_LABEL
        change_info = cls._compute_change_metrics(
            baseline_value, followup_value, direction_of_improvement=indicator.direction_of_improvement
        )

        lim_texts: List[str] = []
        if not has_valid_causal_design:
            lim_texts.append(NON_CAUSAL_LIMITATION_NOTE)
        if downgrade_reason:
            lim_texts.append(downgrade_reason)
        if finding.has_contradicting_evidence:
            lim_texts.append(
                "CONTRADICTING_EVIDENCE_PRESENT: One or more documentary evidence links contradict or qualify this finding."
            )
        for lim in limitations or []:
            lim_texts.append(f"[{lim.category.value if hasattr(lim.category, 'value') else lim.category}] {lim.description}")

        return {
            "study_id": study.study_id,
            "finding_id": finding.finding_id,
            "epistemic_label": epistemic_label,
            "causal_claim_permitted": has_valid_causal_design,
            "was_causal_claim_downgraded": was_downgraded,
            "effective_causal_rigor_grade": effective_rigor,
            "identification_strategy": strategy,
            "quantified_effect": finding.quantified_effect,
            "p_value": finding.p_value,
            "confidence_level": (
                finding.confidence_level.value
                if hasattr(finding.confidence_level, "value")
                else str(finding.confidence_level)
            ),
            "indicator_definition": cls._build_indicator_definition_block(indicator),
            "baseline_value": baseline_value,
            "followup_value": followup_value,
            "absolute_change": change_info["absolute_change"],
            "percentage_change": change_info["percentage_change"],
            "time_period": {
                "publication_date": study.publication_date,
                "baseline_period": indicator.baseline_period,
                "followup_period": indicator.comparison_period,
            },
            "geographic_scope": {
                "geographic_level": indicator.geographic_level,
                "boundary_reference": indicator.boundary_reference,
            },
            "source_references": [
                {
                    "study_id": study.study_id,
                    "conducting_agency": study.conducting_agency,
                    "source_document_id": study.source_document_id,
                    "source_url": study.source_url,
                    "document_hash": study.document_hash,
                }
            ],
            "missing_data_info": {
                "is_complete": baseline_value is not None and followup_value is not None,
            },
            "interpretation_limitations": lim_texts,
        }

    # -----------------------------------------------------------------------
    # 7. Sensitivity Checks Where Sufficient Data Exists
    # -----------------------------------------------------------------------
    @classmethod
    def run_outcome_sensitivity_checks(
        cls,
        indicator: PolicyIndicator,
        unit_changes: List[Tuple[str, float]],
    ) -> Dict[str, Any]:
        """
        Performs sensitivity checks across geographic/sub-group outcome changes
        (`unit_changes` = list of `(unit_id, observed_change)`):
        - Requires at least `MIN_OBSERVATIONS_FOR_SENSITIVITY` (4) valid observations;
          otherwise returns `status = "INSUFFICIENT_DATA_FOR_SENSITIVITY_CHECK"`.
        - Computes:
          1. Full-sample mean and median change.
          2. Leave-one-out (jackknife) min/max mean range to test whether a single outlier
             district drives the statewide conclusion.
          3. Sign-stability check (whether removing any single unit flips the direction of change).
        """
        n = len(unit_changes)
        if n < MIN_OBSERVATIONS_FOR_SENSITIVITY:
            return {
                "indicator_id": indicator.indicator_id,
                "status": "INSUFFICIENT_DATA_FOR_SENSITIVITY_CHECK",
                "sample_size": n,
                "minimum_required": MIN_OBSERVATIONS_FOR_SENSITIVITY,
                "is_robust": None,
                "interpretation_note": (
                    f"Only {n} valid unit observation(s) available; at least {MIN_OBSERVATIONS_FOR_SENSITIVITY} "
                    "are required for leave-one-out and outlier sensitivity analysis."
                ),
            }

        vals = [float(v) for _, v in unit_changes]
        full_mean = round(statistics.mean(vals), 4)
        full_median = round(statistics.median(vals), 4)

        loo_means: List[Tuple[str, float]] = []
        for idx, (u_id, _) in enumerate(unit_changes):
            subset = vals[:idx] + vals[idx + 1 :]
            loo_means.append((u_id, round(statistics.mean(subset), 4)))

        min_loo_unit, min_loo_val = min(loo_means, key=lambda x: x[1])
        max_loo_unit, max_loo_val = max(loo_means, key=lambda x: x[1])

        # Check if sign of mean flips when any single observation is omitted
        full_sign = 1 if full_mean > 0 else (-1 if full_mean < 0 else 0)
        sign_stable = all(
            (1 if m > 0 else (-1 if m < 0 else 0)) == full_sign for _, m in loo_means
        )

        return {
            "indicator_id": indicator.indicator_id,
            "status": "SENSITIVITY_COMPLETED",
            "sample_size": n,
            "full_sample_mean_change": full_mean,
            "full_sample_median_change": full_median,
            "leave_one_out_min_mean": {"omitted_unit": min_loo_unit, "mean_change": min_loo_val},
            "leave_one_out_max_mean": {"omitted_unit": max_loo_unit, "mean_change": max_loo_val},
            "is_sign_stable_under_leave_one_out": sign_stable,
            "is_robust": sign_stable,
            "interpretation_note": (
                "Direction of observed change remains stable across all leave-one-out sub-samples."
                if sign_stable
                else "SENSITIVITY_WARNING: Direction of mean change is sensitive to a single outlier unit."
            ),
        }
