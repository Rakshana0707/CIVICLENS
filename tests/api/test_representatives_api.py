"""
Tests for Phase 6.9 — Representative Performance API and Dashboard Endpoints.

Validates:
1. Search & filter representatives by query, type, and party.
2. Retrieve detailed representative profile with historical terms and completeness.
3. Retrieve constituency profiles and geographic taluk mappings.
4. Retrieve sitting-adjusted legislative activity records.
5. Retrieve constituency works with status and attribution filtering.
6. Retrieve development indicators and baseline trend trajectories.
7. Retrieve promise links and evidence scorecards.
8. Within-cohort comparative analysis and rejection of invalid cohorts.
9. Data completeness index and statutory disclaimers.
10. Empty states and non-existent IDs.
"""

import json
import pytest
from sqlalchemy.orm import Session

from backend.database.base_class import Base
from backend.database.session import SessionLocal, engine
from backend.models.representative import (
    Representative,
    Constituency,
    RepresentativeTerm,
    LegislativeActivity,
    ConstituencyWork,
    DevelopmentIndicator,
    ConstituencyGeographicMapping,
    PromisePerformanceLink,
    RepresentativeType,
    ConstituencyType,
    WorkProjectStatus,
    AttributionType,
    PromiseEvidenceStage,
    GeographicLevel
)
from backend.models.news import PoliticalParty
from backend.models.manifesto import Manifesto
from backend.models.promise import PoliticalPromise


@pytest.fixture(autouse=True)
def setup_teardown_phase6_data():
    """Seed test fixtures into the test database and clean up afterwards."""
    Base.metadata.create_all(bind=engine)
    db: Session = SessionLocal()

    # Pre-populate Party, Manifesto, Promise
    party = PoliticalParty(party_id="PARTY-DMK", party_name="Dravida Munnetra Kazhagam", party_code="DMK")
    db.merge(party)
    db.commit()

    manifesto = Manifesto(
        manifesto_id="MAN-DMK-2021",
        party="DMK",
        election_year=2021
    )
    db.merge(manifesto)
    db.commit()

    promise = PoliticalPromise(
        promise_id="PROM-DMK-2021-001",
        manifesto_id="MAN-DMK-2021",
        original_text="Upgrade primary schools to smart classrooms",
        normalized_text="Upgrade primary schools to smart classrooms"
    )
    db.merge(promise)
    db.commit()

    # Pre-populate Constituencies
    c1 = Constituency(
        constituency_id="AC-013",
        official_name="Kolathur",
        constituency_type=ConstituencyType.ASSEMBLY,
        district="Chennai",
        state="Tamil Nadu"
    )
    c2 = Constituency(
        constituency_id="AC-014",
        official_name="Villivakkam",
        constituency_type=ConstituencyType.ASSEMBLY,
        district="Chennai",
        state="Tamil Nadu"
    )
    db.merge(c1)
    db.merge(c2)
    db.commit()

    # Pre-populate Geographic Mapping
    g_map = ConstituencyGeographicMapping(
        mapping_id="MAP-AC-013",
        constituency_id="AC-013",
        district_name="Chennai",
        taluk_names=["Ayanavaram", "Purasawalkam"],
        population_share_in_district=0.08
    )
    db.merge(g_map)
    db.commit()

    # Pre-populate Representatives
    rep1 = Representative(
        representative_id="REP-MLA-013",
        official_name="M. K. Stalin",
        aliases=["MK Stalin", "மு.க. ஸ்டாலின்"],
        representative_type=RepresentativeType.MLA,
        constituency_id="AC-013",
        party_id="PARTY-DMK",
        term_start="2021-05-07"
    )
    rep2 = Representative(
        representative_id="REP-MLA-014",
        official_name="A. Vetriazhagan",
        aliases=["Vetriazhagan"],
        representative_type=RepresentativeType.MLA,
        constituency_id="AC-014",
        party_id="PARTY-DMK",
        term_start="2021-05-07"
    )
    db.merge(rep1)
    db.merge(rep2)
    db.commit()

    # Pre-populate Terms
    term1 = RepresentativeTerm(
        term_id="TERM-TNLA-16-013",
        representative_id="REP-MLA-013",
        election_id="TNLA-2021",
        house_type="TN_ASSEMBLY",
        party_id="PARTY-DMK",
        term_start="2021-05-07"
    )
    db.merge(term1)
    db.commit()

    # Pre-populate Legislative Activities
    act1 = LegislativeActivity(
        activity_id="ACT-API-001",
        representative_id="REP-MLA-013",
        legislative_body="TN_ASSEMBLY",
        session="16th TNLA - Session 1",
        activity_type="QUESTION_STARRED",
        count=19,
        data_quality_status="VERIFIED"
    )
    act2 = LegislativeActivity(
        activity_id="ACT-API-002",
        representative_id="REP-MLA-013",
        legislative_body="TN_ASSEMBLY",
        session="16th TNLA - Session 1",
        activity_type="DEBATE",
        count=8,
        data_quality_status="VERIFIED"
    )
    db.merge(act1)
    db.merge(act2)
    db.commit()

    # Pre-populate Constituency Works
    work1 = ConstituencyWork(
        work_id="WRK-API-001",
        constituency_id="AC-013",
        representative_id="REP-MLA-013",
        scheme_id="MLACDS",
        project_description="Supply of interactive smart boards to 5 schools",
        sanctioned_amount=2000000.0,
        released_amount=2000000.0,
        reported_expenditure=1800000.0,
        project_status=WorkProjectStatus.REPORTED_COMPLETED,
        approval_date="2022-01-15",
        attribution_type=AttributionType.REPRESENTATIVE_SPONSORED
    )
    db.merge(work1)
    db.commit()

    # Pre-populate Indicators
    ind1 = DevelopmentIndicator(
        indicator_id="IND-API-2011",
        geographic_unit_id="AC-013",
        indicator_name="LITERACY_RATE",
        value=85.0,
        unit="PERCENT",
        reference_period="2011",
        geographic_level=GeographicLevel.CONSTITUENCY
    )
    ind2 = DevelopmentIndicator(
        indicator_id="IND-API-2021",
        geographic_unit_id="AC-013",
        indicator_name="LITERACY_RATE",
        value=91.5,
        unit="PERCENT",
        reference_period="2021",
        geographic_level=GeographicLevel.CONSTITUENCY
    )
    db.merge(ind1)
    db.merge(ind2)
    db.commit()

    # Pre-populate Promise Link
    link1 = PromisePerformanceLink(
        link_id="LNK-API-001",
        representative_id="REP-MLA-013",
        promise_id="PROM-DMK-2021-001",
        work_id="WRK-API-001",
        evidence_stage=PromiseEvidenceStage.PROJECT_WORK_RECORDED
    )
    db.merge(link1)
    db.commit()

    yield

    # Teardown
    try:
        db.query(PromisePerformanceLink).delete()
        db.query(DevelopmentIndicator).delete()
        db.query(ConstituencyWork).delete()
        db.query(LegislativeActivity).delete()
        db.query(RepresentativeTerm).delete()
        db.query(Representative).delete()
        db.query(ConstituencyGeographicMapping).delete()
        db.query(Constituency).delete()
        db.query(PoliticalPromise).delete()
        db.query(Manifesto).delete()
        db.commit()
    except Exception:
        db.rollback()
    finally:
        db.close()


# -----------------------------------------------------------------------------
# API TESTS
# -----------------------------------------------------------------------------
def test_1_search_representatives(api_client):
    """Test searching representatives with query and filters."""
    res = api_client.get("/api/representatives/search?q=Stalin&type=MLA")
    assert res.status_code == 200
    data = res.get_json()["data"]
    assert data["total_count"] >= 1
    assert data["representatives"][0]["official_name"] == "M. K. Stalin"
    assert data["representatives"][0]["representative_type"] == "MLA"


def test_2_get_representative_profile(api_client):
    """Test fetching profile, terms, and data completeness."""
    res = api_client.get("/api/representatives/REP-MLA-013")
    assert res.status_code == 200
    data = res.get_json()["data"]
    assert data["representative_id"] == "REP-MLA-013"
    assert len(data["historical_terms"]) >= 1
    assert "completeness_ratio" in data["data_completeness"]


def test_3_get_constituency_profile(api_client):
    """Test constituency profile including current representative and taluk mappings."""
    res = api_client.get("/api/representatives/constituencies/AC-013")
    assert res.status_code == 200
    data = res.get_json()["data"]
    assert data["official_name"] == "Kolathur"
    assert data["current_representative"]["official_name"] == "M. K. Stalin"
    assert len(data["geographic_mappings"]) >= 1
    assert "Ayanavaram" in data["geographic_mappings"][0]["taluk_names"]


def test_4_legislative_activity_endpoint(api_client):
    """Test legislative activity summary and record logs."""
    res = api_client.get("/api/representatives/REP-MLA-013/legislative?period=2021-2026")
    assert res.status_code == 200
    data = res.get_json()["data"]
    assert data["total_records"] == 2
    raw = data["summary_metrics"]["raw_metrics"]
    assert raw["total_questions"] == 19
    assert raw["total_debates"] == 8
    assert raw["attendance_status"] == "NOT_GAZETTED_ONLINE"


def test_5_constituency_works_endpoint(api_client):
    """Test constituency works filtering and financial execution summary."""
    res = api_client.get("/api/representatives/works?constituency_id=AC-013&status=REPORTED_COMPLETED")
    assert res.status_code == 200
    data = res.get_json()["data"]
    assert data["total_count"] >= 1
    work = data["works"][0]
    assert work["project_status"] == "REPORTED_COMPLETED"
    assert work["sanctioned_amount"] == 2000000.0


def test_6_development_indicators_endpoint(api_client):
    """Test indicator retrieval and baseline delta trajectory analysis."""
    res = api_client.get("/api/representatives/indicators?unit_id=AC-013&indicator_name=LITERACY_RATE&baseline=2011&current=2021")
    assert res.status_code == 200
    data = res.get_json()["data"]
    assert data["total_count"] >= 2
    trend = data["trend_analysis"]
    assert trend is not None
    assert trend["absolute_delta"] == 6.5
    assert trend["percentage_change"] == 7.65


def test_7_promises_endpoint(api_client):
    """Test representative promise linkages and evidence stage scorecard."""
    res = api_client.get("/api/representatives/REP-MLA-013/promises")
    assert res.status_code == 200
    data = res.get_json()["data"]
    assert data["total_count"] >= 1
    assert data["linked_promises"][0]["evidence_stage"] == "PROJECT_WORK_RECORDED"


def test_8_cohort_comparison_endpoint(api_client):
    """Test valid cohort comparison and rejection of invalid cohorts."""
    # Valid MLA comparison
    payload = {
        "representatives": ["REP-MLA-013", "REP-MLA-014"],
        "cohort_type": "TN_ASSEMBLY_MLA",
        "reporting_period": "2021-2024"
    }
    res = api_client.post("/api/representatives/compare", json=payload)
    assert res.status_code == 200
    data = res.get_json()["data"]
    assert len(data["comparisons"]) == 2

    # Insufficient reps
    res_err = api_client.post("/api/representatives/compare", json={"representatives": ["REP-MLA-013"]})
    assert res_err.status_code == 400


def test_9_transparent_composite_endpoint(api_client):
    """Test composite calculation, weight exposure, sensitivity, and anti-pejorative safeguard."""
    res = api_client.get("/api/representatives/REP-MLA-013/composite?period=2021-2024")
    assert res.status_code == 200
    data = res.get_json()["data"]
    assert data["composite_score"] is not None
    assert "sensitivity_analysis" in data
    assert "anti_pejorative_disclaimer" in data


def test_10_not_found_states(api_client):
    """Test 404 responses for non-existent representatives and constituencies."""
    res_rep = api_client.get("/api/representatives/NON-EXISTENT-REP")
    assert res_rep.status_code == 404

    res_const = api_client.get("/api/representatives/constituencies/NON-EXISTENT-CONST")
    assert res_const.status_code == 404
