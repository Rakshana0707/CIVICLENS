"""
CIVICLENS TN — Phase 8.8 Unit & Integration Test Suite
======================================================
Tests the Civic Issue Intelligence Database, REST APIs, and Cross-Phase Integration.

Validates:
1. Model serialization (to_dict) and strict privacy safeguards across all Phase 8 entities.
2. Issue search & multi-attribute filtering (category, area, department, status, text, pagination).
3. Issue details endpoint with resolved relations and SLA standards.
4. Categories, administrative areas, and department summaries endpoints.
5. Response history and empirical resolution evidence endpoints.
6. Recurring clusters and trend analytics API integration.
7. Source documents endpoints.
8. Cross-phase relationship linking with strict anti-causality guards.
9. Cross-phase entity resolution across Phases 1–7.
"""

from datetime import datetime, timezone
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.database.base_class import Base
from backend.models.civic_issue import (
    AdministrativeArea,
    AdministrativeLevel,
    CivicCrossPhaseLink,
    CivicDepartment,
    CivicIssue,
    CivicIssueSeverity,
    CivicIssueStatus,
    DataQualityIssue,
    GrievanceRecord,
    IssueCategory,
    IssueCategoryEnum,
    IssueEvent,
    IssueMetric,
    PublicWork,
    ResolutionEvidence,
    ResolutionVerificationStatus,
    ResponseActionType,
    ResponseRecord,
    ServiceStandard,
    SourceDocument,
)
from backend.models.budget import BudgetDepartment, BudgetScheme, HistoricalScheme
from backend.models.manifesto import Manifesto
from backend.models.promise import PoliticalPromise
from backend.models.news import Article, NewsSource
from backend.models.funding import FinancialDocument
from backend.models.representative import Constituency, ConstituencyType, Representative
from backend.models.claim import Claim, ClaimCategory, ClaimStatus, VerificationOutcome
from backend.api.app import create_app


@pytest.fixture
def app_and_db(monkeypatch):
    """
    Sets up an in-memory SQLite database populated with test fixtures
    across Phases 1-8, monkeypatching SessionLocal in both backend.database.session
    and backend.api.civic.
    """
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(bind=engine)

    # Monkeypatch SessionLocal
    import backend.database.session
    import backend.api.civic
    monkeypatch.setattr(backend.database.session, "SessionLocal", TestingSessionLocal)
    monkeypatch.setattr(backend.api.civic, "SessionLocal", TestingSessionLocal)

    session = TestingSessionLocal()

    # Prepopulate Phase 8 Entities
    cat_roads = IssueCategory(
        code=IssueCategoryEnum.ROADS,
        name_en="Roads & Footpaths",
        name_ta="சாலைகள் மற்றும் நடைபாதைகள்",
        description="Potholes and road defects",
        default_department_code="DEPT-MAWS-001",
    )
    cat_water = IssueCategory(
        code=IssueCategoryEnum.WATER_SUPPLY,
        name_en="Water Supply",
        name_ta="குடிநீர் வழங்கல்",
        description="Drinking water supply pipelines",
        default_department_code="DEPT-CMWSSB",
    )
    session.add_all([cat_roads, cat_water])
    session.flush()

    dept_maws = CivicDepartment(
        code="DEPT-MAWS-001",
        name_en="Municipal Administration and Water Supply",
        name_ta="நகராட்சி நிர்வாகம் மற்றும் குடிநீர் வழங்கல் துறை",
        jurisdiction_level="STATE",
        helpline_number="1913",
    )
    dept_cmwssb = CivicDepartment(
        code="DEPT-CMWSSB",
        name_en="Chennai Metro Water",
        name_ta="சென்னை பெருநகர குடிநீர் வழங்கல் வாரியம்",
        jurisdiction_level="DISTRICT",
        helpline_number="044-45674567",
    )
    session.add_all([dept_maws, dept_cmwssb])
    session.flush()

    area_chennai = AdministrativeArea(
        area_code="ADM-TN-DIST-002-CHENNAI",
        name_en="Chennai District",
        name_ta="சென்னை மாவட்டம்",
        administrative_level=AdministrativeLevel.DISTRICT,
        population=7_000_000,
    )
    session.add(area_chennai)
    session.flush()

    sla_roads = ServiceStandard(
        standard_code="SLA-ROADS-48H",
        department_id=dept_maws.id,
        category_id=cat_roads.id,
        service_name_en="Pothole Restoration Standard",
        service_name_ta="சாலை குழி சீரமைப்பு தரம்",
        stipulated_time_hours=48,
        designated_officer="Assistant Executive Engineer",
    )
    session.add(sla_roads)
    session.flush()

    source_doc = SourceDocument(
        document_code="DOC-GCC-2024-001",
        title="GCC Grievance Disposal Report Q1 2024",
        source_tier=1,
        source_url="https://chennaicorporation.gov.in/atr-q1.pdf",
        publisher="Greater Chennai Corporation",
        published_date=datetime(2024, 1, 15, tzinfo=timezone.utc),
        sha256_hash="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
    )
    session.add(source_doc)
    session.flush()

    issue1 = CivicIssue(
        issue_code="ISS-GCC-2024-001",
        title="Severe potholes on Anna Salai",
        title_ta="அண்ணா சாலையில் கடுமையான பள்ளங்கள்",
        description="Hazardous craters on the main carriageway near Thousand Lights.",
        category_id=cat_roads.id,
        department_id=dept_maws.id,
        administrative_area_id=area_chennai.id,
        status=CivicIssueStatus.OPEN,
        severity=CivicIssueSeverity.HIGH,
        reported_date=datetime(2024, 1, 10, 10, 0, tzinfo=timezone.utc),
        repeat_count=3,
        is_test_fixture=True,
    )
    session.add(issue1)
    session.flush()

    grievance1 = GrievanceRecord(
        grievance_id="GRIEV-2024-001",
        source_id="GCC_1913",
        issue_category=IssueCategoryEnum.ROADS,
        description_or_permitted_summary="Pothole near bus stop",
        submission_date=datetime(2024, 1, 10, 10, 0, tzinfo=timezone.utc),
        department_id="DEPT-MAWS-001",
        administrative_area_id="ADM-TN-DIST-002-CHENNAI",
        status="open",
        civic_issue_id=issue1.id,
        source_document_id=source_doc.id,
        is_test_fixture=True,
    )
    session.add(grievance1)

    response1 = ResponseRecord(
        civic_issue_id=issue1.id,
        department_id=dept_maws.id,
        action_taken_by="Ward 112 Junior Engineer",
        action_type=ResponseActionType.INSPECTION_CONDUCTED,
        reported_status="under_review",
        verification_status=ResolutionVerificationStatus.PENDING_VERIFICATION,
        response_summary="Inspection conducted; cold mix patching scheduled.",
        action_taken_date=datetime(2024, 1, 11, 14, 0, tzinfo=timezone.utc),
        is_sla_breached=False,
        delay_hours=0.0,
        is_test_fixture=True,
    )
    session.add(response1)
    session.flush()

    evidence1 = ResolutionEvidence(
        response_id=response1.id,
        evidence_type="FIELD_INSPECTION_REPORT",
        title="Site Inspection Sheet",
        description="Verified 3 square meters of road wear.",
        evidence_url="https://chennaicorporation.gov.in/inspections/001.pdf",
        is_verified=True,
        is_test_fixture=True,
    )
    session.add(evidence1)

    event1 = IssueEvent(
        civic_issue_id=issue1.id,
        event_timestamp=datetime(2024, 1, 10, 10, 0, tzinfo=timezone.utc),
        event_type="CREATED",
        actor_type="SYSTEM",
        notes="Issue initialized from docket GRIEV-2024-001",
    )
    session.add(event1)

    # Prepopulate Cross-Phase Mock Entities (Phases 1-7)
    # Phase 2: Historical Scheme
    dept_b = BudgetDepartment(id=1, name="Highways and Minor Ports TN", code="DEMAND_15")
    hscheme = HistoricalScheme(
        id=201,
        scheme_name="Chief Minister Road Development Programme (CMRDP)",
        department_id=1,
        financial_year="2023-2024",
        objectives="Upgradation of major bus routes and arterial corridors.",
    )
    session.add_all([dept_b, hscheme])

    # Phase 3: Political Promise
    man = Manifesto(
        manifesto_id="MAN-2021-DMK",
        party="DMK",
        election_year=2021,
        title="DMK 2021 State Assembly Manifesto",
    )
    promise = PoliticalPromise(
        promise_id="PRM-2021-DMK-ROAD-01",
        manifesto_id="MAN-2021-DMK",
        original_text="Re-laying of all bus route roads with paved shoulders across municipal corporations.",
        normalized_text="relaying of all bus route roads with paved shoulders across municipal corporations",
        classification="infrastructure",
    )
    session.add_all([man, promise])

    # Phase 4: News Article
    nsrc = NewsSource(source_id="NS-TH", source_name="The Hindu", domain="thehindu.com", language="en")
    art = Article(
        article_id="ART-2024-ROADS-01",
        source_id="NS-TH",
        url="https://thehindu.com/news/cities/chennai/pothole-repairs-underway.html",
        title="Corporation takes up urgent patchwork on Anna Salai arterial stretch",
        article_text="The Greater Chennai Corporation has deployed mechanized cold mix units on Anna Salai.",
        publication_date=datetime(2024, 1, 12, tzinfo=timezone.utc),
        text_hash="hash-roads-01",
    )
    session.add_all([nsrc, art])

    # Phase 5: Financial Document
    findoc = FinancialDocument(
        document_id="FIN-PWD-2023-01",
        source_id="TN_BUDGET_PORTAL",
        financial_year="2023-2024",
        filing_type="DemandForGrants",
        file_hash_sha256="hash-fin-doc-demand15",
        source_url="https://tnbudget.tn.gov.in/demand-15.pdf",
    )
    session.add(findoc)

    # Phase 6: Representative & Constituency
    con = Constituency(
        constituency_id="CON-TN-THOUSAND-LIGHTS",
        official_name="Thousand Lights",
        constituency_type=ConstituencyType.ASSEMBLY,
        district="Chennai",
        state="Tamil Nadu",
    )
    rep = Representative(
        representative_id="REP-TN-MLA-018",
        official_name="Dr. Ezhilan Naganathan",
        representative_type="MLA",
        party_id="DMK",
        constituency_id="CON-TN-THOUSAND-LIGHTS",
        term_start="2021-05-07",
    )
    session.add_all([con, rep])

    # Phase 7: Claim
    claim = Claim(
        claim_id="CLM-2024-ROADS-001",
        original_text="Over 95% of pothole complaints in Chennai are resolved within 48 hours.",
        normalized_text="over 95 percent of pothole complaints in chennai are resolved within 48 hours",
        speaker_name="Mayor of Chennai",
        claim_category=ClaimCategory.PUBLIC_INFRASTRUCTURE,
        status=ClaimStatus.VERIFIED,
    )
    session.add(claim)

    session.commit()

    app = create_app()
    app.config["TESTING"] = True
    client = app.test_client()

    yield client, session, issue1

    session.close()


# ---------------------------------------------------------------------------
# Test 1: Model Serialization (to_dict) & Citizen Privacy Safeguards
# ---------------------------------------------------------------------------
def test_model_to_dict_and_privacy_safeguards(app_and_db):
    _, session, issue = app_and_db

    grievance = session.query(GrievanceRecord).first()
    g_dict = grievance.to_dict()

    # Privacy check: no citizen name, phone, or address exposed
    assert "citizen_name" not in g_dict
    assert "phone" not in g_dict
    assert "aadhaar" not in g_dict
    assert "credentials" not in g_dict
    assert g_dict["is_anonymized"] is True
    assert g_dict["grievance_id"] == "GRIEV-2024-001"

    issue_dict = issue.to_dict()
    assert issue_dict["issue_code"] == "ISS-GCC-2024-001"
    assert issue_dict["category_name"] == "Roads & Footpaths"
    assert issue_dict["repeat_count"] == 3


# ---------------------------------------------------------------------------
# Test 2: Issue Search & Filter API (GET /api/civic/issues)
# ---------------------------------------------------------------------------
def test_search_civic_issues_filters(app_and_db):
    client, _, _ = app_and_db

    # 1. Search all issues
    res = client.get("/api/civic/issues")
    assert res.status_code == 200
    data = res.get_json()["data"]
    assert len(data["issues"]) >= 1
    assert data["pagination"]["total"] >= 1

    # 2. Filter by keyword match
    res_kw = client.get("/api/civic/issues?q=Anna+Salai")
    assert res_kw.status_code == 200
    assert len(res_kw.get_json()["data"]["issues"]) == 1

    # 3. Filter by keyword mismatch
    res_nomatch = client.get("/api/civic/issues?q=Coimbatore+Expressway")
    assert res_nomatch.status_code == 200
    assert len(res_nomatch.get_json()["data"]["issues"]) == 0

    # 4. Filter by category
    res_cat = client.get("/api/civic/issues?category=roads")
    assert res_cat.status_code == 200
    assert len(res_cat.get_json()["data"]["issues"]) == 1

    # 5. Filter by status
    res_stat = client.get("/api/civic/issues?status=open")
    assert res_stat.status_code == 200
    assert len(res_stat.get_json()["data"]["issues"]) == 1


# ---------------------------------------------------------------------------
# Test 3: Issue Details API (GET /api/civic/issues/<issue_id>)
# ---------------------------------------------------------------------------
def test_get_civic_issue_details(app_and_db):
    client, _, issue = app_and_db

    # Get by issue_code
    res = client.get(f"/api/civic/issues/{issue.issue_code}")
    assert res.status_code == 200
    data = res.get_json()["data"]

    assert data["issue_code"] == issue.issue_code
    assert data["category"]["name_en"] == "Roads & Footpaths"
    assert data["department"]["code"] == "DEPT-MAWS-001"
    assert data["service_standard"]["stipulated_time_hours"] == 48
    assert data["responses_count"] == 1
    assert data["grievance_records_count"] == 1

    # Non-existent issue returns 404
    res_404 = client.get("/api/civic/issues/NONEXISTENT-999")
    assert res_404.status_code == 404


# ---------------------------------------------------------------------------
# Test 4: Categories & Service Standards API (GET /api/civic/categories)
# ---------------------------------------------------------------------------
def test_get_issue_categories(app_and_db):
    client, _, _ = app_and_db

    res = client.get("/api/civic/categories")
    assert res.status_code == 200
    cats = res.get_json()["data"]["categories"]

    assert len(cats) >= 2
    road_cat = [c for c in cats if c["code"] == "roads"][0]
    assert road_cat["active_issues_count"] >= 1
    assert len(road_cat["service_standards"]) >= 1
    assert road_cat["service_standards"][0]["stipulated_time_hours"] == 48


# ---------------------------------------------------------------------------
# Test 5: Administrative Areas API (GET /api/civic/areas)
# ---------------------------------------------------------------------------
def test_get_administrative_areas(app_and_db):
    client, _, _ = app_and_db

    res = client.get("/api/civic/areas?level=DISTRICT")
    assert res.status_code == 200
    areas = res.get_json()["data"]["areas"]

    assert len(areas) >= 1
    chennai = [a for a in areas if "CHENNAI" in a["area_code"]][0]
    assert chennai["population"] == 7_000_000
    assert chennai["active_issues_count"] >= 1


# ---------------------------------------------------------------------------
# Test 6: Departments & Performance Summary (GET /api/civic/departments/...)
# ---------------------------------------------------------------------------
def test_get_department_and_summary(app_and_db):
    client, _, _ = app_and_db

    # 1. Listing
    res_list = client.get("/api/civic/departments")
    assert res_list.status_code == 200
    depts = res_list.get_json()["data"]["departments"]
    assert len(depts) >= 2

    # 2. Performance Summary
    res_sum = client.get("/api/civic/departments/DEPT-MAWS-001/summary")
    assert res_sum.status_code == 200
    summary = res_sum.get_json()["data"]

    assert summary["department"]["code"] == "DEPT-MAWS-001"
    assert summary["total_assigned_issues"] >= 1
    assert summary["status_breakdown"]["open"] >= 1
    assert summary["sla_compliance_percentage"] == 100.0


# ---------------------------------------------------------------------------
# Test 7: Response History API (GET /api/civic/issues/<issue_id>/responses)
# ---------------------------------------------------------------------------
def test_get_issue_responses_history(app_and_db):
    client, _, issue = app_and_db

    res = client.get(f"/api/civic/issues/{issue.issue_code}/responses")
    assert res.status_code == 200
    data = res.get_json()["data"]

    assert len(data["responses"]) == 1
    assert data["responses"][0]["action_taken_by"] == "Ward 112 Junior Engineer"
    assert len(data["events"]) == 1
    assert data["events"][0]["event_type"] == "CREATED"


# ---------------------------------------------------------------------------
# Test 8: Resolution Evidence API (GET /api/civic/issues/<issue_id>/evidence)
# ---------------------------------------------------------------------------
def test_get_issue_resolution_evidence(app_and_db):
    client, _, issue = app_and_db

    res = client.get(f"/api/civic/issues/{issue.issue_code}/evidence")
    assert res.status_code == 200
    data = res.get_json()["data"]

    assert data["evidence_count"] == 1
    assert data["evidences"][0]["evidence_type"] == "FIELD_INSPECTION_REPORT"
    assert data["evidences"][0]["is_verified"] is True


# ---------------------------------------------------------------------------
# Test 9: Recurring Issue Clusters (GET /api/civic/clusters)
# ---------------------------------------------------------------------------
def test_get_recurring_clusters(app_and_db):
    client, _, _ = app_and_db

    res = client.get("/api/civic/clusters")
    assert res.status_code == 200
    data = res.get_json()["data"]

    assert data["recurring_records_count"] >= 1
    assert "caveats" in data


# ---------------------------------------------------------------------------
# Test 10: Trend Analytics API (GET /api/civic/analytics/trends)
# ---------------------------------------------------------------------------
def test_get_trend_analytics(app_and_db):
    client, _, _ = app_and_db

    res = client.get("/api/civic/analytics/trends?period=2024-Q1")
    assert res.status_code == 200
    data = res.get_json()["data"]

    assert data["reporting_period"] == "2024-Q1"
    assert "ISSUE_COUNT_BY_CATEGORY" in data["metrics"]
    assert "RESOLUTION_EVIDENCE_COVERAGE" in data["metrics"]
    assert "COMPLAINTS DO NOT EQUAL PREVALENCE" in data["general_disclaimer"]


# ---------------------------------------------------------------------------
# Test 11: Source Documents API (GET /api/civic/source-documents)
# ---------------------------------------------------------------------------
def test_get_source_documents(app_and_db):
    client, _, issue = app_and_db

    res_all = client.get("/api/civic/source-documents")
    assert res_all.status_code == 200
    assert len(res_all.get_json()["data"]["source_documents"]) >= 1

    res_issue = client.get(f"/api/civic/issues/{issue.issue_code}/source-documents")
    assert res_issue.status_code == 200
    assert len(res_issue.get_json()["data"]["source_documents"]) == 1


# ---------------------------------------------------------------------------
# Test 12: Cross-Phase Link Creation & Strict Anti-Causality Guard
# ---------------------------------------------------------------------------
def test_cross_phase_link_creation_and_anti_causality_guard(app_and_db):
    client, _, issue = app_and_db

    # 1. Anti-causality guard test:
    # Attempting to link merely because of shared geographic area must fail with 400
    bad_payload = {
        "target_phase": "PHASE_3_PROMISE",
        "entity_type": "POLITICAL_PROMISE",
        "entity_id": "PRM-2021-DMK-ROAD-01",
        "relationship_nature": "promised_remedy",
        "matching_method": "same_area",  # FORBIDDEN METHOD
        "provenance_summary": "Both pertain to Chennai.",
    }
    res_bad = client.post(f"/api/civic/issues/{issue.issue_code}/cross-phase-link", json=bad_payload)
    assert res_bad.status_code == 400
    assert "Cannot create cross-phase links merely because records share a geographic area" in res_bad.get_json()["message"]

    # 2. Legitimate link with documented tender reference / constituency mapping succeeds
    good_payload = {
        "target_phase": "PHASE_1_2_BUDGET_SCHEME",
        "entity_type": "HISTORICAL_SCHEME",
        "entity_id": "201",
        "relationship_nature": "addressed_by_scheme",
        "matching_method": "DEPARTMENT_SCHEME_ALIGNMENT",
        "provenance_summary": "Anna Salai road improvement sanctioned under CMRDP Demand 15.",
        "confidence": 0.95,
        "is_test_fixture": True,
    }
    res_good = client.post(f"/api/civic/issues/{issue.issue_code}/cross-phase-link", json=good_payload)
    assert res_good.status_code == 201
    link_data = res_good.get_json()["data"]
    assert link_data["target_phase"] == "PHASE_1_2_BUDGET_SCHEME"
    assert link_data["entity_id"] == "201"


# ---------------------------------------------------------------------------
# Test 13: Cross-Phase Entity Resolution (GET /api/civic/issues/<issue_id>/cross-phase)
# ---------------------------------------------------------------------------
def test_cross_phase_entity_resolution(app_and_db):
    client, session, issue = app_and_db

    # Add cross-phase relationships connecting issue to all earlier phases:
    # Phase 2 Scheme, Phase 3 Promise, Phase 4 News, Phase 5 Funding, Phase 6 Rep, Phase 7 Claim
    links = [
        CivicCrossPhaseLink(
            link_id="CPL-TEST-001",
            civic_issue_id=issue.id,
            target_phase="PHASE_1_2_BUDGET_SCHEME",
            entity_type="HISTORICAL_SCHEME",
            entity_id="201",
            relationship_nature="addressed_by_scheme",
            matching_method="DEPARTMENT_SCHEME_ALIGNMENT",
            provenance_summary="Sanctioned under CMRDP",
            is_test_fixture=True,
        ),
        CivicCrossPhaseLink(
            link_id="CPL-TEST-002",
            civic_issue_id=issue.id,
            target_phase="PHASE_3_PROMISE",
            entity_type="POLITICAL_PROMISE",
            entity_id="PRM-2021-DMK-ROAD-01",
            relationship_nature="promised_remedy",
            matching_method="MANIFESTO_ITEM_CORRELATION",
            provenance_summary="Arterial road relaying promised in manifesto item 01",
            is_test_fixture=True,
        ),
        CivicCrossPhaseLink(
            link_id="CPL-TEST-003",
            civic_issue_id=issue.id,
            target_phase="PHASE_4_NEWS",
            entity_type="NEWS_ARTICLE",
            entity_id="ART-2024-ROADS-01",
            relationship_nature="reported_by_news",
            matching_method="MEDIA_EVENT_CO_REFERENCE",
            provenance_summary="The Hindu article reports immediate patchwork on this stretch",
            is_test_fixture=True,
        ),
        CivicCrossPhaseLink(
            link_id="CPL-TEST-004",
            civic_issue_id=issue.id,
            target_phase="PHASE_5_FUNDING",
            entity_type="FINANCIAL_DOCUMENT",
            entity_id="FIN-PWD-2023-01",
            relationship_nature="funded_by_allocation",
            matching_method="BUDGET_HEAD_CITING",
            provenance_summary="Demand 15 budget book allocation for arterial repairs",
            is_test_fixture=True,
        ),
        CivicCrossPhaseLink(
            link_id="CPL-TEST-005",
            civic_issue_id=issue.id,
            target_phase="PHASE_6_REPRESENTATIVE",
            entity_type="REPRESENTATIVE",
            entity_id="REP-TN-MLA-018",
            relationship_nature="constituency_representative",
            matching_method="ELECTORAL_WARD_BOUNDARY_OVERLAP",
            provenance_summary="Elected MLA for Thousand Lights Assembly Constituency",
            is_test_fixture=True,
        ),
        CivicCrossPhaseLink(
            link_id="CPL-TEST-006",
            civic_issue_id=issue.id,
            target_phase="PHASE_7_CLAIM",
            entity_type="CLAIM",
            entity_id="CLM-2024-ROADS-001",
            relationship_nature="evaluated_by_claim",
            matching_method="FACT_CHECK_EVALUATION",
            provenance_summary="Claim evaluates Chennai 48-hour pothole resolution rate",
            is_test_fixture=True,
        ),
    ]
    session.add_all(links)
    session.commit()

    res = client.get(f"/api/civic/issues/{issue.issue_code}/cross-phase")
    assert res.status_code == 200
    data = res.get_json()["data"]

    assert data["cross_phase_links_count"] == 6
    resolved = data["cross_phase_links"]

    # Verify resolution of Phase 2 Historical Scheme
    hs_link = [l for l in resolved if l["target_phase"] == "PHASE_1_2_BUDGET_SCHEME"][0]
    assert hs_link["resolved_entity"]["scheme_name"] == "Chief Minister Road Development Programme (CMRDP)"

    # Verify resolution of Phase 3 Promise
    p_link = [l for l in resolved if l["target_phase"] == "PHASE_3_PROMISE"][0]
    assert p_link["resolved_entity"]["promise_id"] == "PRM-2021-DMK-ROAD-01"

    # Verify resolution of Phase 4 News
    news_link = [l for l in resolved if l["target_phase"] == "PHASE_4_NEWS"][0]
    assert "Corporation takes up urgent patchwork" in news_link["resolved_entity"]["title"]

    # Verify resolution of Phase 5 Financial Document
    fin_link = [l for l in resolved if l["target_phase"] == "PHASE_5_FUNDING"][0]
    assert fin_link["resolved_entity"]["document_id"] == "FIN-PWD-2023-01"

    # Verify resolution of Phase 6 Representative
    rep_link = [l for l in resolved if l["target_phase"] == "PHASE_6_REPRESENTATIVE"][0]
    assert rep_link["resolved_entity"]["official_name"] == "Dr. Ezhilan Naganathan"

    # Verify resolution of Phase 7 Claim
    claim_link = [l for l in resolved if l["target_phase"] == "PHASE_7_CLAIM"][0]
    assert claim_link["resolved_entity"]["claim_id"] == "CLM-2024-ROADS-001"
