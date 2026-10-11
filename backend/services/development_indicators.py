"""
Phase 6 — Constituency Development Indicator Analysis Service.

Manages demographic, socioeconomic, and departmental indicators from Census,
state statistics (DES TN), and Open Government Data (data.gov.in).

Enforces:
1. Defensible geographic mapping (no arbitrary assignment of district values to constituencies).
2. Explicit causality disclaimers (indicator delta is NOT proof of representative causality).
3. Unit consistency verification and normalization.
4. Comparable baseline calculations across reporting periods.
"""

import logging
from typing import Dict, Any, List, Optional, Tuple, Set
from datetime import datetime, timezone
from sqlalchemy.orm import Session

from backend.models.representative import (
    Constituency,
    DevelopmentIndicator,
    ConstituencyGeographicMapping,
    GeographicLevel,
    CalculationMethod,
    IndicatorQualityStatus
)

logger = logging.getLogger("civiclens.phase6.indicators")
logging.basicConfig(level=logging.INFO)


class InconsistentUnitError(Exception):
    """Raised when comparing indicators with incompatible measurement units."""
    pass


class GeographicMappingError(Exception):
    """Raised when attempting to map district indicators without a defensible mapping."""
    pass


class DevelopmentIndicatorService:
    """
    Core service for recording, interpolating, and analyzing constituency development indicators.
    """

    def __init__(self, db: Optional[Session] = None):
        self.db = db

    def record_indicator(
        self,
        indicator_id: str,
        geographic_unit_id: str,
        indicator_name: str,
        value: float,
        unit: str,
        reference_period: str,
        geographic_level: str = GeographicLevel.CONSTITUENCY,
        constituency_id: Optional[str] = None,
        source_document_id: Optional[str] = None,
        source_reference: Optional[str] = None,
        calculation_method: str = CalculationMethod.OFFICIAL_PUBLICATION,
        data_quality_status: str = IndicatorQualityStatus.VERIFIED,
        notes: Optional[str] = None
    ) -> DevelopmentIndicator:
        """Records or updates an indicator observation with provenance and calculation method."""
        ind = None
        if self.db:
            ind = self.db.query(DevelopmentIndicator).filter(DevelopmentIndicator.indicator_id == indicator_id).first()

        if ind:
            ind.geographic_unit_id = geographic_unit_id
            ind.constituency_id = constituency_id
            ind.indicator_name = indicator_name
            ind.value = value
            ind.unit = unit.upper()
            ind.reference_period = reference_period
            ind.geographic_level = geographic_level
            ind.source_document_id = source_document_id
            ind.source_reference = source_reference
            ind.calculation_method = calculation_method
            ind.data_quality_status = data_quality_status
            ind.notes = notes
        else:
            ind = DevelopmentIndicator(
                indicator_id=indicator_id,
                geographic_unit_id=geographic_unit_id,
                constituency_id=constituency_id,
                indicator_name=indicator_name,
                value=value,
                unit=unit.upper(),
                reference_period=reference_period,
                geographic_level=geographic_level,
                source_document_id=source_document_id,
                source_reference=source_reference,
                calculation_method=calculation_method,
                data_quality_status=data_quality_status,
                notes=notes
            )
            if self.db:
                self.db.add(ind)

        if self.db:
            self.db.commit()
            self.db.refresh(ind)

        logger.info(f"Recorded indicator {indicator_id} ({indicator_name}={value} {unit} for {geographic_unit_id} [{reference_period}])")
        return ind

    def record_geographic_mapping(
        self,
        mapping_id: str,
        constituency_id: str,
        district_name: str,
        taluk_names: Optional[List[str]] = None,
        area_share_in_district: float = 1.0,
        population_share_in_district: float = 1.0,
        delimitation_year: int = 2008,
        mapping_methodology: str = "ECI_DELIMITATION_ORDER_2008"
    ) -> ConstituencyGeographicMapping:
        """Records a spatial/administrative mapping between a constituency and a district."""
        m = None
        if self.db:
            m = self.db.query(ConstituencyGeographicMapping).filter(ConstituencyGeographicMapping.mapping_id == mapping_id).first()

        if m:
            m.constituency_id = constituency_id
            m.district_name = district_name
            m.taluk_names = taluk_names or []
            m.area_share_in_district = area_share_in_district
            m.population_share_in_district = population_share_in_district
            m.delimitation_year = delimitation_year
            m.mapping_methodology = mapping_methodology
        else:
            m = ConstituencyGeographicMapping(
                mapping_id=mapping_id,
                constituency_id=constituency_id,
                district_name=district_name,
                taluk_names=taluk_names or [],
                area_share_in_district=area_share_in_district,
                population_share_in_district=population_share_in_district,
                delimitation_year=delimitation_year,
                mapping_methodology=mapping_methodology
            )
            if self.db:
                self.db.add(m)

        if self.db:
            self.db.commit()
            self.db.refresh(m)

        return m

    def get_constituency_indicator(
        self,
        constituency_id: str,
        indicator_name: str,
        reference_period: str,
        allow_interpolation: bool = True
    ) -> Optional[Dict[str, Any]]:
        """
        Retrieves indicator value for a constituency.
        CRITICAL RULE: Does NOT assign district-level values without defensible geographic mapping.
        """
        if not self.db:
            return None

        # 1. Look for direct constituency-level observation
        direct_obs = self.db.query(DevelopmentIndicator).filter(
            DevelopmentIndicator.constituency_id == constituency_id,
            DevelopmentIndicator.indicator_name == indicator_name,
            DevelopmentIndicator.reference_period == reference_period
        ).first()

        if direct_obs:
            return {
                "indicator_id": direct_obs.indicator_id,
                "constituency_id": constituency_id,
                "geographic_unit_id": direct_obs.geographic_unit_id,
                "indicator_name": direct_obs.indicator_name,
                "value": direct_obs.value,
                "unit": direct_obs.unit,
                "reference_period": direct_obs.reference_period,
                "geographic_level": direct_obs.geographic_level,
                "calculation_method": direct_obs.calculation_method,
                "data_quality_status": direct_obs.data_quality_status,
                "is_interpolated": False,
                "source_reference": direct_obs.source_reference
            }

        if not allow_interpolation:
            return None

        # 2. Defensible geographic mapping lookup
        mapping = self.db.query(ConstituencyGeographicMapping).filter(
            ConstituencyGeographicMapping.constituency_id == constituency_id
        ).first()

        if not mapping:
            raise GeographicMappingError(
                f"No direct observation found for {constituency_id} ({indicator_name}, {reference_period}), "
                f"and no defensible geographic mapping exists to interpolate from district data."
            )

        district_id = f"DISTRICT-{mapping.district_name.upper()}"
        district_obs = self.db.query(DevelopmentIndicator).filter(
            DevelopmentIndicator.geographic_unit_id == district_id,
            DevelopmentIndicator.indicator_name == indicator_name,
            DevelopmentIndicator.reference_period == reference_period
        ).first()

        if not district_obs:
            return None

        # Interpolate based on indicator unit type
        interpolated_value = district_obs.value
        calc_method = CalculationMethod.AREA_WEIGHTED_INTERPOLATION

        if district_obs.unit in ("PERCENT", "RATIO", "PER_1000", "PER_LAKH"):
            # Intensive rates: apply district baseline directly with population weighting annotation
            interpolated_value = district_obs.value
            calc_method = CalculationMethod.POPULATION_WEIGHTED_AGGREGATION
        elif district_obs.unit in ("COUNT", "KM"):
            # Extensive counts: scale by population share or area share
            interpolated_value = round(district_obs.value * mapping.population_share_in_district, 2)
            calc_method = CalculationMethod.AREA_WEIGHTED_INTERPOLATION

        return {
            "indicator_id": f"INTERPOLATED_{constituency_id}_{indicator_name}_{reference_period}",
            "constituency_id": constituency_id,
            "geographic_unit_id": district_id,
            "indicator_name": indicator_name,
            "value": interpolated_value,
            "unit": district_obs.unit,
            "reference_period": reference_period,
            "geographic_level": GeographicLevel.DISTRICT,
            "calculation_method": calc_method,
            "data_quality_status": IndicatorQualityStatus.INTERPOLATED,
            "is_interpolated": True,
            "interpolation_notes": (
                f"Derived from parent district '{mapping.district_name}' via {calc_method} "
                f"(pop share: {mapping.population_share_in_district:.3f}, area share: {mapping.area_share_in_district:.3f})."
            ),
            "source_reference": district_obs.source_reference
        }

    def compare_across_periods(
        self,
        geographic_unit_id: str,
        indicator_name: str,
        start_period: str,
        end_period: str,
        constituency_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Calculates baseline trajectory between two reference periods.
        Enforces unit consistency, boundary change detection, and causality safeguards.
        """
        if not self.db:
            return {}

        q = self.db.query(DevelopmentIndicator).filter(
            DevelopmentIndicator.indicator_name == indicator_name,
            DevelopmentIndicator.geographic_unit_id == geographic_unit_id
        )
        if constituency_id:
            q = q.filter(DevelopmentIndicator.constituency_id == constituency_id)

        obs_start = q.filter(DevelopmentIndicator.reference_period == start_period).first()
        obs_end = q.filter(DevelopmentIndicator.reference_period == end_period).first()

        if not obs_start or not obs_end:
            missing_periods = []
            if not obs_start:
                missing_periods.append(start_period)
            if not obs_end:
                missing_periods.append(end_period)
            return {
                "geographic_unit_id": geographic_unit_id,
                "indicator_name": indicator_name,
                "status": IndicatorQualityStatus.MISSING,
                "error": f"Missing observations for required periods: {missing_periods}"
            }

        # Unit consistency check
        if obs_start.unit.upper() != obs_end.unit.upper():
            raise InconsistentUnitError(
                f"Inconsistent measurement units for {indicator_name}: "
                f"{start_period} has unit '{obs_start.unit}', whereas {end_period} has unit '{obs_end.unit}'."
            )

        val_start = obs_start.value
        val_end = obs_end.value
        abs_delta = round(val_end - val_start, 2)
        pct_change = round(((val_end - val_start) / val_start * 100), 2) if val_start != 0 else 0.0

        # Boundary change check: check if delimitation occurred between periods
        has_delimitation_shift = False
        try:
            start_y = int(start_period[:4])
            end_y = int(end_period[:4])
            if start_y < 2008 and end_y >= 2008:
                has_delimitation_shift = True
        except (ValueError, TypeError):
            pass

        return {
            "geographic_unit_id": geographic_unit_id,
            "indicator_name": indicator_name,
            "unit": obs_start.unit,
            "baseline_period": start_period,
            "baseline_value": val_start,
            "comparison_period": end_period,
            "comparison_value": val_end,
            "absolute_change": abs_delta,
            "percent_change": pct_change,
            "trajectory": "IMPROVEMENT" if abs_delta > 0 else ("DECLINE" if abs_delta < 0 else "STABLE"),
            "has_delimitation_shift": has_delimitation_shift,
            "data_quality": {
                "start_status": obs_start.data_quality_status,
                "end_status": obs_end.data_quality_status,
                "delimitation_warning": (
                    "CAUTION: Comparison crosses 2008 Delimitation Order boundary reorganization. "
                    "Geographical boundaries are not identically matched." if has_delimitation_shift else None
                )
            },
            "causality_disclaimer": (
                "NON-CAUSALITY NOTICE: Socioeconomic indicator changes reflect multi-factor macro conditions, "
                "state/central funding, and demographic dynamics. Temporal progress is NOT proof of individual representative causality."
            )
        }
