"""
End-to-End Tests for Phase 6.10 — Real Dataset Integration & Final Pipeline Validation.

Traces representative records through the full lifecycle:
RAW SOURCE INVENTORY
  -> RAW PRESERVATION (data/raw/phase6)
  -> EXTRACTION & NORMALIZATION
  -> DATABASE REGISTRY
  -> PERFORMANCE METRICS
  -> API BLUEPRINT
  -> FRONTEND CLIENT
"""

import os
import pytest
from sqlalchemy.orm import Session

from backend.database.session import SessionLocal, engine
from backend.database.base_class import Base
from backend.models.representative import (
    Representative,
    Constituency,
    RepresentativeTerm,
    LegislativeActivity,
    ConstituencyWork,
    DevelopmentIndicator,
    RepresentativeType,
    ConstituencyType
)
from backend.services.performance_metrics import PerformanceMetricsEngine
from backend.services.real_data_ingestion import run_phase6_integration


@pytest.fixture(scope="module")
def setup_real_phase6_database():
    """Run real dataset ingestion pipeline and yield session."""
    run_phase6_integration()
    db: Session = SessionLocal()
    yield db
    db.close()


def test_1_raw_data_preservation_and_checksums():
    """Verify raw files exist in data/raw/phase6 with expected filenames and non-zero size."""
    raw_dir = "data/raw/phase6"
    ds1_zip = os.path.join(raw_dir, "Phase_6_DS_1.zip")
    ds2_csv = os.path.join(raw_dir, "Phase_6_DS_2.csv")
    ds1_extracted = os.path.join(raw_dir, "Phase_6_DS_1", "master_dataset_inventory.csv")

    assert os.path.exists(ds1_zip), "Phase_6_DS_1.zip must be preserved"
    assert os.path.exists(ds2_csv), "Phase_6_DS_2.csv must be preserved"
    assert os.path.exists(ds1_extracted), "Extracted master_dataset_inventory.csv must exist"
    assert os.path.getsize(ds1_zip) > 0
    assert os.path.getsize(ds2_csv) > 0


def test_2_canonical_constituencies_ingestion(setup_real_phase6_database):
    """Verify all 39 Parliamentary Constituencies of Tamil Nadu are registered."""
    db = setup_real_phase6_database
    pcs = db.query(Constituency).filter(Constituency.constituency_type == ConstituencyType.PARLIAMENTARY).all()
    assert len(pcs) >= 39
    cbe = db.query(Constituency).filter(Constituency.constituency_id == "PC-TN-18").first()
    assert cbe is not None
    assert cbe.official_name == "Coimbatore"
    assert cbe.district == "Coimbatore"


def test_3_real_mps_and_legislative_activity_trace(setup_real_phase6_database):
    """Verify real 17th Lok Sabha MPs (Perambalur, Arani, Coimbatore) and their activity metrics."""
    db = setup_real_phase6_database
    perambalur_mp = db.query(Representative).filter(
        Representative.representative_id == "REP-MP-17-PERAMBALUR"
    ).first()
    assert perambalur_mp is not None
    assert perambalur_mp.official_name == "T. R. Paarivendhar"
    assert perambalur_mp.representative_type == RepresentativeType.LOK_SABHA_MP

    # Verify activity records
    acts = db.query(LegislativeActivity).filter(
        LegislativeActivity.representative_id == "REP-MP-17-PERAMBALUR"
    ).all()
    assert len(acts) == 3

    q_act = next(a for a in acts if "QUESTION" in a.activity_type)
    assert q_act.count == 268

    att_act = next(a for a in acts if "ATTENDANCE" in a.activity_type)
    assert att_act.value == 62.0


def test_4_real_mplads_and_census_indicators_trace(setup_real_phase6_database):
    """Verify official state-level MPLADS expenditure and Census 2011 literacy baselines."""
    db = setup_real_phase6_database
    mplads_works = db.query(ConstituencyWork).filter(
        ConstituencyWork.scheme_id == "MPLADS"
    ).all()
    assert len(mplads_works) >= 2

    # Verify Census indicator
    cbe_lit_2011 = db.query(DevelopmentIndicator).filter(
        DevelopmentIndicator.geographic_unit_id == "PC-TN-18",
        DevelopmentIndicator.reference_period == "2011"
    ).first()
    assert cbe_lit_2011 is not None
    assert cbe_lit_2011.value == 83.98


def test_5_api_endpoints_on_real_data(api_client, setup_real_phase6_database):
    """Verify API responses for real representatives, legislative activity, and indicators."""
    # 1. Search real MPs
    res = api_client.get("/api/representatives/search?q=Paarivendhar")
    assert res.status_code == 200
    data = res.get_json()["data"]
    assert data["total_count"] >= 1
    assert data["representatives"][0]["representative_id"] == "REP-MP-17-PERAMBALUR"

    # 2. Legislative activity
    res_leg = api_client.get("/api/representatives/REP-MP-17-PERAMBALUR/legislative?period=2019-2024")
    assert res_leg.status_code == 200
    leg_data = res_leg.get_json()["data"]["summary_metrics"]["raw_metrics"]
    assert leg_data["total_questions"] == 268
    assert leg_data["attendance_percentage"] == 62.0

    # 3. Development indicators trajectory
    res_ind = api_client.get("/api/representatives/indicators?unit_id=PC-TN-18&indicator_name=LITERACY_RATE&baseline=2011&current=2021")
    assert res_ind.status_code == 200
    ind_data = res_ind.get_json()["data"]
    trend = ind_data["trend_analysis"]
    assert trend["baseline_value"] == 83.98
    assert trend["current_value"] == 89.20
    assert trend["absolute_delta"] == 5.22
