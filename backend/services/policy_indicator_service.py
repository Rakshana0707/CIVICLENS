"""
Phase 10.4 — Policy Indicator Registry and Baseline Construction Service.
=========================================================================

Implements the indicator registry, baseline construction engine, and strict
compatibility validators for measuring documented policy implementation and outcome changes:

1. Supports all 10 indicator domains (budget expenditure, beneficiary count, facilities
   constructed/upgraded, service delivery count, target achievement, service access,
   education, health, infrastructure/development, complaint/resolution measures).
2. Records all 12 required indicator attributes (canonical ID, definition, unit, source,
   reporting frequency, geographic level, baseline period & value, comparison period & value,
   collection method, missing-data status, calculation formula, known limitations).
3. Enforces compatibility checks across 4 dimensions before any comparison or aggregation:
   - Compatible Units (blocks silent unit mismatches; supports explicit linear scale conversion)
   - Compatible Definitions (never silently combines observations with differing definition codes)
   - Compatible Geographic Boundaries (detects district bifurcations and boundary changes)
   - Compatible Reporting Periods / Frequencies (blocks comparing quarterly vs annual flows)
4. Enforces Missing-Data Integrity:
   - Never treats missing data (None) as 0.0.
   - Records whether a baseline is OFFICIAL_PUBLISHED, CALCULATED_FROM_SOURCE_DATA, or UNAVAILABLE.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple
from sqlalchemy.orm import Session

from backend.models.policy_evaluation import (
    PolicyIndicator,
    IndicatorObservation,
    IndicatorType,
    IndicatorDomain,
    ObservationStage,
    ReportingFrequency,
    BaselineConstructionStatus,
    MissingDataStatus,
)


class IncompatibleIndicatorComparisonError(ValueError):
    """
    Raised when attempting to compare or combine indicator observations with
    incompatible units, definitions, geographic boundaries, or reporting periods.
    """

    def __init__(self, error_code: str, message: str):
        self.error_code = error_code
        super().__init__(f"{error_code}: {message}")


# Safe linear unit conversion multipliers (within identical physical/monetary dimensions only)
LINEAR_UNIT_CONVERSIONS: Dict[Tuple[str, str], float] = {
    ("RUPEES_LAKH", "RUPEES_CRORE"): 0.01,
    ("RUPEES_CRORE", "RUPEES_LAKH"): 100.0,
    ("INR_ABSOLUTE", "RUPEES_CRORE"): 1e-7,
    ("RUPEES_CRORE", "INR_ABSOLUTE"): 1e7,
    ("THOUSANDS", "COUNT"): 1000.0,
    ("COUNT", "THOUSANDS"): 0.001,
    ("LAKHS", "COUNT"): 100000.0,
    ("COUNT", "LAKHS"): 0.00001,
    ("METERS", "KM"): 0.001,
    ("KM", "METERS"): 1000.0,
}


class PolicyIndicatorRegistryService:
    """
    Service for registering policy indicators, constructing baselines with explicit
    provenance, and validating cross-period and cross-geography comparisons.
    """

    # -----------------------------------------------------------------------
    # 1. Missing-Data Status Resolution (Never Treat Missing Data as Zero)
    # -----------------------------------------------------------------------
    @staticmethod
    def determine_missing_data_status(
        baseline_value: Optional[float],
        comparison_value: Optional[float],
        explicit_status: Optional[MissingDataStatus | str] = None,
    ) -> MissingDataStatus:
        """
        Determines the MissingDataStatus based on baseline and comparison presence.
        Distinguishes a genuine 0.0 observation from None (missing/unavailable).
        """
        if explicit_status is not None:
            parsed = MissingDataStatus.from_string(explicit_status)
            if parsed in (
                MissingDataStatus.PARTIAL_GEOGRAPHIC_COVERAGE,
                MissingDataStatus.NOT_PUBLISHED_BY_SOURCE,
            ):
                return parsed

        has_baseline = baseline_value is not None
        has_comparison = comparison_value is not None

        if has_baseline and has_comparison:
            return MissingDataStatus.COMPLETE
        if not has_baseline and not has_comparison:
            return MissingDataStatus.MISSING_BOTH
        if not has_baseline:
            return MissingDataStatus.MISSING_BASELINE
        return MissingDataStatus.MISSING_COMPARISON

    # -----------------------------------------------------------------------
    # 2. Indicator Registration
    # -----------------------------------------------------------------------
    @classmethod
    def register_indicator(
        cls,
        db: Session,
        *,
        indicator_id: str,
        objective_id: str,
        indicator_name: str,
        indicator_type: IndicatorType | str,
        unit: str,
        definition: str,
        source: str,
        reporting_frequency: ReportingFrequency | str = ReportingFrequency.ANNUAL,
        geographic_level: str = "STATE",
        indicator_domain: Optional[IndicatorDomain | str] = None,
        scheme_id: Optional[str] = None,
        indicator_name_ta: Optional[str] = None,
        definition_code: Optional[str] = None,
        boundary_reference: str = "TN_38_DISTRICTS_2020",
        baseline_period: Optional[str] = None,
        baseline_value: Optional[float] = None,
        baseline_construction_status: Optional[BaselineConstructionStatus | str] = None,
        comparison_period: Optional[str] = None,
        comparison_value: Optional[float] = None,
        collection_method: str = "ADMIN_REGISTRY",
        missing_data_status: Optional[MissingDataStatus | str] = None,
        calculation_formula: str = "DIRECT_OBSERVATION",
        known_limitations: str = "Standard administrative reporting latency applies.",
        direction_of_improvement: str = "INCREASE",
        aggregation_method: str = "SUM",
        is_test_fixture: bool = False,
    ) -> PolicyIndicator:
        """
        Registers a canonical PolicyIndicator with all 12 required Phase 10.4 attributes.
        Never coerces None baseline_value or comparison_value to 0.0.
        """
        if not definition or not definition.strip():
            raise ValueError("Indicator definition is required.")
        if not unit or not unit.strip():
            raise ValueError("Indicator unit is required.")
        if not source or not source.strip():
            raise ValueError("Indicator source is required.")

        # Resolve baseline construction status
        if baseline_construction_status is not None:
            b_status = BaselineConstructionStatus.from_string(baseline_construction_status)
            if b_status == BaselineConstructionStatus.UNAVAILABLE and baseline_value is not None:
                raise ValueError(
                    "Epistemic error: baseline_value must be None when baseline_construction_status is UNAVAILABLE."
                )
            if b_status in (
                BaselineConstructionStatus.OFFICIAL_PUBLISHED,
                BaselineConstructionStatus.CALCULATED_FROM_SOURCE_DATA,
            ) and baseline_value is None:
                raise ValueError(
                    f"Epistemic error: baseline_construction_status={b_status.value} requires a non-null baseline_value."
                )
        else:
            b_status = (
                BaselineConstructionStatus.OFFICIAL_PUBLISHED
                if baseline_value is not None
                else BaselineConstructionStatus.UNAVAILABLE
            )

        m_status = cls.determine_missing_data_status(
            baseline_value=baseline_value,
            comparison_value=comparison_value,
            explicit_status=missing_data_status,
        )

        domain_enum = IndicatorDomain.from_string(indicator_domain) if indicator_domain else None

        indicator = PolicyIndicator(
            indicator_id=indicator_id,
            objective_id=objective_id,
            scheme_id=scheme_id,
            indicator_name=indicator_name.strip(),
            indicator_name_ta=indicator_name_ta,
            indicator_type=IndicatorType.from_string(indicator_type),
            indicator_domain=domain_enum,
            definition=definition.strip(),
            definition_code=definition_code or f"DEF:{indicator_id}",
            description=definition.strip(),
            unit=unit.strip().upper(),
            source=source.strip(),
            reporting_frequency=ReportingFrequency.from_string(reporting_frequency),
            geographic_level=geographic_level.strip().upper(),
            boundary_reference=boundary_reference.strip(),
            baseline_period=baseline_period,
            baseline_value=baseline_value,  # Strictly preserves None if missing
            baseline_construction_status=b_status,
            comparison_period=comparison_period,
            comparison_value=comparison_value,  # Strictly preserves None if missing
            collection_method=collection_method.strip(),
            missing_data_status=m_status,
            calculation_formula=calculation_formula.strip(),
            known_limitations=known_limitations.strip(),
            direction_of_improvement=direction_of_improvement.strip().upper(),
            aggregation_method=aggregation_method.strip().upper(),
            is_test_fixture=is_test_fixture,
        )

        db.add(indicator)
        db.commit()
        db.refresh(indicator)
        return indicator

    # -----------------------------------------------------------------------
    # 3. Unit Conversion & Compatibility Validation
    # -----------------------------------------------------------------------
    @staticmethod
    def convert_unit_if_compatible(
        value: Optional[float],
        from_unit: str,
        to_unit: str,
        allow_linear_conversion: bool = False,
    ) -> float:
        """
        Verifies unit compatibility or performs an explicit safe linear conversion
        (e.g., RUPEES_LAKH -> RUPEES_CRORE) when allow_linear_conversion=True.
        Raises IncompatibleIndicatorComparisonError on incompatible units.
        """
        u_from = from_unit.strip().upper()
        u_to = to_unit.strip().upper()

        if u_from == u_to:
            return value  # type: ignore

        if not allow_linear_conversion:
            raise IncompatibleIndicatorComparisonError(
                "UNIT_MISMATCH",
                f"Cannot compare observations with different units ('{u_from}' vs '{u_to}') "
                "without explicit unit conversion enabled.",
            )

        pair = (u_from, u_to)
        if pair not in LINEAR_UNIT_CONVERSIONS:
            raise IncompatibleIndicatorComparisonError(
                "UNIT_MISMATCH",
                f"Units '{u_from}' and '{u_to}' belong to incompatible measurement dimensions and cannot be converted.",
            )

        if value is None:
            return None  # type: ignore

        return value * LINEAR_UNIT_CONVERSIONS[pair]

    @classmethod
    def validate_observation_compatibility(
        cls,
        indicator: PolicyIndicator,
        baseline_obs: IndicatorObservation,
        comparison_obs: IndicatorObservation,
        *,
        allow_linear_unit_conversion: bool = False,
        allow_rate_frequency_difference: bool = False,
    ) -> Tuple[Optional[float], Optional[float]]:
        """
        Validates that baseline_obs and comparison_obs share compatible:
        1. Definitions (definition_code)
        2. Units (unit / unit_override)
        3. Geographic Levels & Boundaries (geographic_level, geographic_unit_id, boundary_reference)
        4. Reporting Periods / Frequencies (reporting_frequency)

        Returns (normalized_baseline_value, normalized_comparison_value).
        Never silently combines incompatible observations.
        """
        # 1. Definition Compatibility
        base_def = baseline_obs.definition_code or indicator.definition_code or f"DEF:{indicator.indicator_id}"
        comp_def = comparison_obs.definition_code or indicator.definition_code or f"DEF:{indicator.indicator_id}"
        if base_def != comp_def:
            raise IncompatibleIndicatorComparisonError(
                "DEFINITION_MISMATCH",
                f"Cannot silently combine observations with incompatible definitions: "
                f"baseline='{base_def}' vs comparison='{comp_def}'.",
            )

        # 2. Unit Compatibility
        target_unit = indicator.unit.strip().upper()
        base_unit = (baseline_obs.unit_override or target_unit).strip().upper()
        comp_unit = (comparison_obs.unit_override or target_unit).strip().upper()

        norm_base_val = baseline_obs.value
        norm_comp_val = comparison_obs.value

        if base_unit != target_unit:
            norm_base_val = cls.convert_unit_if_compatible(
                norm_base_val, base_unit, target_unit, allow_linear_conversion=allow_linear_unit_conversion
            )
        if comp_unit != target_unit:
            norm_comp_val = cls.convert_unit_if_compatible(
                norm_comp_val, comp_unit, target_unit, allow_linear_conversion=allow_linear_unit_conversion
            )
        if base_unit != comp_unit and not allow_linear_unit_conversion:
            raise IncompatibleIndicatorComparisonError(
                "UNIT_MISMATCH",
                f"Baseline unit '{base_unit}' does not match comparison unit '{comp_unit}'.",
            )

        # 3. Geographic Level, Unit, and Boundary Compatibility
        if baseline_obs.geographic_level.upper() != comparison_obs.geographic_level.upper():
            raise IncompatibleIndicatorComparisonError(
                "GEOGRAPHIC_LEVEL_MISMATCH",
                f"Cannot directly compare different geographic levels: "
                f"'{baseline_obs.geographic_level}' vs '{comparison_obs.geographic_level}'.",
            )
        if baseline_obs.geographic_unit_id != comparison_obs.geographic_unit_id:
            raise IncompatibleIndicatorComparisonError(
                "GEOGRAPHIC_UNIT_MISMATCH",
                f"Cannot directly compare different geographic units: "
                f"'{baseline_obs.geographic_unit_id}' vs '{comparison_obs.geographic_unit_id}'.",
            )

        base_bound = baseline_obs.boundary_reference or indicator.boundary_reference
        comp_bound = comparison_obs.boundary_reference or indicator.boundary_reference
        if base_bound and comp_bound and base_bound != comp_bound:
            raise IncompatibleIndicatorComparisonError(
                "BOUNDARY_MISMATCH",
                f"Geographic administrative boundary changed between baseline ('{base_bound}') "
                f"and comparison ('{comp_bound}') for unit '{baseline_obs.geographic_unit_id}'. "
                "Requires boundary harmonization before comparison.",
            )

        # 4. Reporting Period / Frequency Compatibility
        ind_freq = (
            indicator.reporting_frequency.value
            if hasattr(indicator.reporting_frequency, "value")
            else str(indicator.reporting_frequency)
        )
        base_freq = (baseline_obs.reporting_frequency or ind_freq).upper()
        comp_freq = (comparison_obs.reporting_frequency or ind_freq).upper()

        if base_freq != comp_freq and not allow_rate_frequency_difference:
            raise IncompatibleIndicatorComparisonError(
                "REPORTING_PERIOD_MISMATCH",
                f"Cannot compare observations collected over different reporting frequencies: "
                f"baseline='{base_freq}' ({baseline_obs.reference_period}) vs "
                f"comparison='{comp_freq}' ({comparison_obs.reference_period}).",
            )

        return norm_base_val, norm_comp_val

    # -----------------------------------------------------------------------
    # 4. Baseline Construction Engine
    # -----------------------------------------------------------------------
    @classmethod
    def construct_baseline_from_observations(
        cls,
        db: Session,
        indicator: PolicyIndicator,
        source_observations: List[IndicatorObservation],
        *,
        baseline_period: str,
        construction_mode: BaselineConstructionStatus | str = BaselineConstructionStatus.OFFICIAL_PUBLISHED,
        calculation_formula: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Constructs a baseline for an indicator and updates its baseline metadata.
        Records whether the baseline is:
        - OFFICIAL_PUBLISHED (single authoritative baseline observation)
        - CALCULATED_FROM_SOURCE_DATA (aggregated from compatible sub-observations, e.g., districts)
        - UNAVAILABLE (when observations are empty or contain missing values)
        Never treats missing data as zero.
        """
        mode = BaselineConstructionStatus.from_string(construction_mode)

        if not source_observations:
            indicator.baseline_period = baseline_period
            indicator.baseline_value = None
            indicator.baseline_construction_status = BaselineConstructionStatus.UNAVAILABLE
            indicator.missing_data_status = cls.determine_missing_data_status(None, indicator.comparison_value)
            db.commit()
            return {
                "indicator_id": indicator.indicator_id,
                "baseline_period": baseline_period,
                "baseline_value": None,
                "baseline_construction_status": BaselineConstructionStatus.UNAVAILABLE.value,
                "missing_data_status": indicator.missing_data_status.value,
            }

        # Check for any missing values in source_observations — NEVER treat None as 0.0!
        missing_obs = [obs for obs in source_observations if obs.value is None]
        if missing_obs:
            indicator.baseline_period = baseline_period
            indicator.baseline_value = None
            indicator.baseline_construction_status = BaselineConstructionStatus.UNAVAILABLE
            indicator.missing_data_status = (
                MissingDataStatus.PARTIAL_GEOGRAPHIC_COVERAGE
                if len(missing_obs) < len(source_observations)
                else cls.determine_missing_data_status(None, indicator.comparison_value)
            )
            db.commit()
            return {
                "indicator_id": indicator.indicator_id,
                "baseline_period": baseline_period,
                "baseline_value": None,
                "baseline_construction_status": BaselineConstructionStatus.UNAVAILABLE.value,
                "missing_data_status": indicator.missing_data_status.value,
                "missing_observation_ids": [o.observation_id for o in missing_obs],
            }

        # Verify unit and definition compatibility across all source observations
        expected_def = indicator.definition_code or f"DEF:{indicator.indicator_id}"
        expected_unit = indicator.unit.strip().upper()
        expected_bound = source_observations[0].boundary_reference or indicator.boundary_reference

        values: List[float] = []
        for obs in source_observations:
            obs_def = obs.definition_code or expected_def
            if obs_def != expected_def:
                raise IncompatibleIndicatorComparisonError(
                    "DEFINITION_MISMATCH",
                    f"Observation {obs.observation_id} has incompatible definition '{obs_def}' vs '{expected_def}'.",
                )
            obs_unit = (obs.unit_override or expected_unit).strip().upper()
            if obs_unit != expected_unit:
                raise IncompatibleIndicatorComparisonError(
                    "UNIT_MISMATCH",
                    f"Observation {obs.observation_id} has unit '{obs_unit}' vs indicator unit '{expected_unit}'.",
                )
            obs_bound = obs.boundary_reference or expected_bound
            if obs_bound != expected_bound:
                raise IncompatibleIndicatorComparisonError(
                    "BOUNDARY_MISMATCH",
                    f"Observation {obs.observation_id} uses boundary '{obs_bound}' vs '{expected_bound}'.",
                )
            values.append(float(obs.value))  # type: ignore

        if len(values) == 1 and mode == BaselineConstructionStatus.OFFICIAL_PUBLISHED:
            computed_val = values[0]
            effective_status = BaselineConstructionStatus.OFFICIAL_PUBLISHED
        else:
            agg_method = (indicator.aggregation_method or "SUM").upper()
            if agg_method == "MEAN":
                computed_val = round(sum(values) / len(values), 4)
            else:
                computed_val = round(sum(values), 4)
            effective_status = BaselineConstructionStatus.CALCULATED_FROM_SOURCE_DATA
            if calculation_formula:
                indicator.calculation_formula = calculation_formula

        indicator.baseline_period = baseline_period
        indicator.baseline_value = computed_val
        indicator.baseline_construction_status = effective_status
        indicator.missing_data_status = cls.determine_missing_data_status(computed_val, indicator.comparison_value)
        db.commit()

        return {
            "indicator_id": indicator.indicator_id,
            "baseline_period": baseline_period,
            "baseline_value": computed_val,
            "baseline_construction_status": effective_status.value,
            "missing_data_status": indicator.missing_data_status.value,
            "source_observation_count": len(values),
        }

    # -----------------------------------------------------------------------
    # 5. Cross-Period Indicator Comparison
    # -----------------------------------------------------------------------
    @classmethod
    def compare_observations(
        cls,
        indicator: PolicyIndicator,
        baseline_obs: IndicatorObservation,
        comparison_obs: IndicatorObservation,
        *,
        allow_linear_unit_conversion: bool = False,
    ) -> Dict[str, Any]:
        """
        Compares a baseline observation and a follow-up/comparison observation after
        verifying compatibility of units, definitions, boundaries, and reporting periods.
        Preserves None when data is missing instead of treating missing data as zero.
        """
        norm_base, norm_comp = cls.validate_observation_compatibility(
            indicator=indicator,
            baseline_obs=baseline_obs,
            comparison_obs=comparison_obs,
            allow_linear_unit_conversion=allow_linear_unit_conversion,
        )

        missing_status = cls.determine_missing_data_status(norm_base, norm_comp)

        if norm_base is None or norm_comp is None:
            return {
                "indicator_id": indicator.indicator_id,
                "unit": indicator.unit,
                "baseline_period": baseline_obs.reference_period,
                "comparison_period": comparison_obs.reference_period,
                "baseline_value": norm_base,
                "comparison_value": norm_comp,
                "baseline_construction_status": (
                    baseline_obs.value_origin.value
                    if hasattr(baseline_obs.value_origin, "value")
                    else str(baseline_obs.value_origin)
                ),
                "missing_data_status": missing_status.value,
                "is_calculable": False,
                "absolute_change": None,
                "percentage_change": None,
            }

        abs_change = round(norm_comp - norm_base, 4)
        pct_change = round((abs_change / norm_base) * 100.0, 2) if norm_base != 0 else None

        return {
            "indicator_id": indicator.indicator_id,
            "unit": indicator.unit,
            "baseline_period": baseline_obs.reference_period,
            "comparison_period": comparison_obs.reference_period,
            "baseline_value": norm_base,
            "comparison_value": norm_comp,
            "baseline_construction_status": (
                baseline_obs.value_origin.value
                if hasattr(baseline_obs.value_origin, "value")
                else str(baseline_obs.value_origin)
            ),
            "missing_data_status": missing_status.value,
            "is_calculable": True,
            "absolute_change": abs_change,
            "percentage_change": pct_change,
        }
