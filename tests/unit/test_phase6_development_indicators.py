"""
Unit tests for Phase 6 Constituency Development Indicator Analysis Pipeline.

Tests:
1. Direct constituency indicator recording and retrieval.
2. Defensible geographic mapping and weighted interpolation from district baselines.
3. Rejection of unmapped district assignment (raising GeographicMappingError).
4. Inconsistent measurement units detection (raising InconsistentUnitError).
5. Comparisons across reporting periods and non-causality disclaimer.
6. Delimitation boundary shift detection (2001 vs 2011).
7. Missing observations handling and diagnostics.
"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.database.base_class import Base
from backend.models.representative import (
    Constituency,
    DevelopmentIndicator,
    ConstituencyGeographicMapping,
    GeographicLevel,
    CalculationMethod,
    IndicatorQualityStatus,
    ConstituencyType
)
from backend.services.development_indicators import (
    DevelopmentIndicatorService,
    InconsistentUnitError,
    GeographicMappingError
)


@pytest.fixture
def db_session():
    """In-memory SQLite database session for isolated testing."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    # Pre-populate sample constituency
    const = Constituency(
        constituency_id="AC-013",
        official_name="Kolathur",
        constituency_type=ConstituencyType.ASSEMBLY,
        district="Chennai",
        valid_from="2008"
    )
    session.add(const)
    session.commit()

    yield session
    session.close()


def test_1_record_direct_constituency_indicator(db_session):
    service = DevelopmentIndicatorService(db=db_session)

    service.record_indicator(
        indicator_id="IND-AC013-LIT-2011",
        geographic_unit_id="AC-013",
        constituency_id="AC-013",
        indicator_name="LITERACY_RATE",
        value=91.0,
        unit="PERCENT",
        reference_period="2011",
        geographic_level=GeographicLevel.CONSTITUENCY,
        calculation_method=CalculationMethod.DIRECT_OBSERVATION,
        source_reference="Census 2011 PCA Tamil Nadu Table A-1"
    )

    result = service.get_constituency_indicator(
        constituency_id="AC-013",
        indicator_name="LITERACY_RATE",
        reference_period="2011"
    )

    assert result is not None
    assert result["value"] == 91.0
    assert result["unit"] == "PERCENT"
    assert result["is_interpolated"] is False
    assert result["calculation_method"] == CalculationMethod.DIRECT_OBSERVATION


def test_2_defensible_geographic_mapping_interpolation(db_session):
    """
    Verifies that district data is interpolated to a constituency ONLY when
    a defensible geographic mapping with area/population weights is documented.
    """
    service = DevelopmentIndicatorService(db=db_session)

    # 1. Record district-level indicator
    service.record_indicator(
        indicator_id="IND-DIST-CHN-WATER-2021",
        geographic_unit_id="DISTRICT-CHENNAI",
        indicator_name="HOUSEHOLD_TAP_WATER_PCT",
        value=84.5,
        unit="PERCENT",
        reference_period="2021",
        geographic_level=GeographicLevel.DISTRICT,
        source_reference="DES TN District Statistical Handbook 2021"
    )

    # 2. Record extensive count indicator at district level
    service.record_indicator(
        indicator_id="IND-DIST-CHN-SCHOOLS-2021",
        geographic_unit_id="DISTRICT-CHENNAI",
        indicator_name="PRIMARY_SCHOOLS_COUNT",
        value=800.0,
        unit="COUNT",
        reference_period="2021",
        geographic_level=GeographicLevel.DISTRICT
    )

    # 3. Register defensible geographic mapping for AC-013
    service.record_geographic_mapping(
        mapping_id="MAP-AC013-CHN",
        constituency_id="AC-013",
        district_name="Chennai",
        area_share_in_district=0.075,
        population_share_in_district=0.08,  # AC-013 represents 8% of Chennai's population
        delimitation_year=2008
    )

    # Retrieve intensive rate (PERCENT): keeps rate, annotates population aggregation
    res_water = service.get_constituency_indicator("AC-013", "HOUSEHOLD_TAP_WATER_PCT", "2021")
    assert res_water is not None
    assert res_water["value"] == 84.5
    assert res_water["is_interpolated"] is True
    assert res_water["data_quality_status"] == IndicatorQualityStatus.INTERPOLATED

    # Retrieve extensive count (COUNT): scales by population share 800 * 0.08 = 64.0
    res_schools = service.get_constituency_indicator("AC-013", "PRIMARY_SCHOOLS_COUNT", "2021")
    assert res_schools is not None
    assert res_schools["value"] == 64.0
    assert res_schools["is_interpolated"] is True


def test_3_rejection_of_unmapped_district_data(db_session):
    """
    Attempting to retrieve district data for an unmapped constituency without
    a defensible geographic mapping MUST raise GeographicMappingError.
    """
    service = DevelopmentIndicatorService(db=db_session)

    # Register another constituency without geographic mapping
    const2 = Constituency(
        constituency_id="AC-999-UNMAPPED",
        official_name="Unmapped Constituency",
        constituency_type=ConstituencyType.ASSEMBLY,
        district="Ramanathapuram"
    )
    db_session.add(const2)
    db_session.commit()

    with pytest.raises(GeographicMappingError):
        service.get_constituency_indicator(
            constituency_id="AC-999-UNMAPPED",
            indicator_name="LITERACY_RATE",
            reference_period="2021"
        )


def test_4_inconsistent_units_detection_raises_error(db_session):
    """
    Comparing an indicator where one period has COUNT and another has PERCENT
    MUST raise InconsistentUnitError.
    """
    service = DevelopmentIndicatorService(db=db_session)

    # Period 1 in COUNT
    service.record_indicator(
        indicator_id="IND-COMP-01",
        geographic_unit_id="AC-013",
        indicator_name="ELECTRIFIED_HOUSEHOLDS",
        value=24000.0,
        unit="COUNT",
        reference_period="2011"
    )

    # Period 2 in PERCENT
    service.record_indicator(
        indicator_id="IND-COMP-02",
        geographic_unit_id="AC-013",
        indicator_name="ELECTRIFIED_HOUSEHOLDS",
        value=98.5,
        unit="PERCENT",
        reference_period="2021"
    )

    with pytest.raises(InconsistentUnitError):
        service.compare_across_periods(
            geographic_unit_id="AC-013",
            indicator_name="ELECTRIFIED_HOUSEHOLDS",
            start_period="2011",
            end_period="2021"
        )


def test_5_compare_across_periods_and_non_causality_disclaimer(db_session):
    """
    Verifies valid period trajectory calculation and mandatory non-causality disclaimer.
    """
    service = DevelopmentIndicatorService(db=db_session)

    service.record_indicator(
        indicator_id="IND-LIT-2011",
        geographic_unit_id="AC-013",
        indicator_name="LITERACY_RATE",
        value=85.0,
        unit="PERCENT",
        reference_period="2011"
    )
    service.record_indicator(
        indicator_id="IND-LIT-2021",
        geographic_unit_id="AC-013",
        indicator_name="LITERACY_RATE",
        value=91.5,
        unit="PERCENT",
        reference_period="2021"
    )

    comp = service.compare_across_periods(
        geographic_unit_id="AC-013",
        indicator_name="LITERACY_RATE",
        start_period="2011",
        end_period="2021"
    )

    assert comp["baseline_value"] == 85.0
    assert comp["comparison_value"] == 91.5
    assert comp["absolute_change"] == 6.5
    assert comp["percent_change"] == 7.65
    assert comp["trajectory"] == "IMPROVEMENT"
    assert comp["has_delimitation_shift"] is False
    assert "NON-CAUSALITY NOTICE" in comp["causality_disclaimer"]


def test_6_delimitation_shift_detection(db_session):
    """
    Comparing periods crossing 2008 (e.g., Census 2001 vs Census 2011)
    MUST flag delimitation shift warning.
    """
    service = DevelopmentIndicatorService(db=db_session)

    service.record_indicator(
        indicator_id="IND-LIT-2001",
        geographic_unit_id="AC-013",
        indicator_name="LITERACY_RATE",
        value=78.0,
        unit="PERCENT",
        reference_period="2001"
    )
    service.record_indicator(
        indicator_id="IND-LIT-2011",
        geographic_unit_id="AC-013",
        indicator_name="LITERACY_RATE",
        value=85.0,
        unit="PERCENT",
        reference_period="2011"
    )

    comp = service.compare_across_periods(
        geographic_unit_id="AC-013",
        indicator_name="LITERACY_RATE",
        start_period="2001",
        end_period="2011"
    )

    assert comp["has_delimitation_shift"] is True
    assert "crosses 2008 Delimitation Order" in comp["data_quality"]["delimitation_warning"]


def test_7_missing_observations_handling(db_session):
    """
    Verifies that missing observations return clean diagnostic dictionaries without exceptions.
    """
    service = DevelopmentIndicatorService(db=db_session)

    service.record_indicator(
        indicator_id="IND-ONLY-START",
        geographic_unit_id="AC-013",
        indicator_name="FEMALE_LITERACY_RATE",
        value=82.0,
        unit="PERCENT",
        reference_period="2011"
    )

    comp = service.compare_across_periods(
        geographic_unit_id="AC-013",
        indicator_name="FEMALE_LITERACY_RATE",
        start_period="2011",
        end_period="2026"  # Missing
    )

    assert comp["status"] == IndicatorQualityStatus.MISSING
    assert "Missing observations" in comp["error"]
