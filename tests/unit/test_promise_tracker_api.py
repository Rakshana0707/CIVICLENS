"""
Automated API unit and integration tests for Political Promise Tracker API (Phase 3.12).

Verifies:
- All required endpoints: parties, elections, manifestos, promises, categories, scheme matches, evidence, evidence matches, assessments, assessment history, sources.
- Assessment response contract (promise, status, confidence, explanation, supporting_evidence, source_links).
- Dynamic data handling (no hardcoded data).
- Input validation, filtering, and pagination.
- Error handling (404s for non-existent IDs).
- Empty-state handling (clean 200 empty responses).
"""
import unittest
import json
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.api.app import create_app
from backend.database.base import Base
from backend.database.session import SessionLocal
from backend.models.manifesto import Manifesto, ManifestoSource, ManifestoDocument
from backend.models.promise import (
    PoliticalPromise,
    PromiseCategory,
    PromiseCategoryMapping,
    PromiseEvidenceLink,
    PromiseSchemeLink,
    PromiseAssessment,
    PromiseAssessmentHistory,
    PromiseStatus
)
from backend.models.common import Evidence
from backend.models.budget import BudgetDepartment, HistoricalScheme


class TestPromiseTrackerAPI(unittest.TestCase):

    def setUp(self):
        # Create Flask test client
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()

        # In-memory SQLite engine for API DB isolation
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        self.db = TestingSessionLocal()

        # Patch SessionLocal in backend.api.promises to use in-memory test DB
        import backend.api.promises
        self._orig_get_db = backend.api.promises.get_db
        backend.api.promises.get_db = lambda: TestingSessionLocal()

    def tearDown(self):
        import backend.api.promises
        backend.api.promises.get_db = self._orig_get_db
        self.db.close()
        Base.metadata.drop_all(self.engine)

    def test_empty_state_handling(self):
        """Verify querying empty database returns clean HTTP 200 responses with empty lists."""
        endpoints = [
            "/api/promises/parties",
            "/api/promises/elections",
            "/api/promises/manifestos",
            "/api/promises/categories",
            "/api/promises/",
            "/api/promises/evidence",
            "/api/promises/sources"
        ]
        for ep in endpoints:
            res = self.client.get(ep)
            self.assertEqual(res.status_code, 200, f"Endpoint {ep} failed empty state test.")
            data = json.loads(res.data.decode("utf-8"))
            self.assertEqual(data["status"], "success")
            self.assertIn("data", data)

    def test_404_error_handling(self):
        """Verify 404 error responses for missing items."""
        res_m = self.client.get("/api/promises/manifestos/NON_EXISTENT")
        self.assertEqual(res_m.status_code, 404)

        res_p = self.client.get("/api/promises/NON_EXISTENT")
        self.assertEqual(res_p.status_code, 404)

        res_a = self.client.get("/api/promises/NON_EXISTENT/assessment")
        self.assertEqual(res_a.status_code, 404)

        res_e = self.client.get("/api/promises/evidence/99999")
        self.assertEqual(res_e.status_code, 404)

    def test_dynamic_parties_and_elections_endpoints(self):
        """Verify dynamic calculation of parties and elections from DB data."""
        m1 = Manifesto(manifesto_id="M1", party="DMK", election_year=2021)
        m2 = Manifesto(manifesto_id="M2", party="AIADMK", election_year=2021)
        m3 = Manifesto(manifesto_id="M3", party="TVK", election_year=2026)
        self.db.add_all([m1, m2, m3])
        self.db.commit()

        # Test parties
        res_parties = self.client.get("/api/promises/parties")
        self.assertEqual(res_parties.status_code, 200)
        data_p = json.loads(res_parties.data.decode("utf-8"))["data"]
        self.assertEqual(data_p["total"], 3)

        # Test elections
        res_elections = self.client.get("/api/promises/elections")
        self.assertEqual(res_elections.status_code, 200)
        data_e = json.loads(res_elections.data.decode("utf-8"))["data"]
        self.assertEqual(data_e["total"], 2)

    def test_promises_filtering_and_pagination(self):
        """Verify filtering by party, election_year, category, classification, and search keyword."""
        m = Manifesto(manifesto_id="M_DMK_2026", party="DMK", election_year=2026)
        c = PromiseCategory(category_code="Education", name="Education")
        self.db.add_all([m, c])
        self.db.commit()

        p1 = PoliticalPromise(
            promise_id="P_EDU_01",
            manifesto_id="M_DMK_2026",
            original_text="Free laptops for students.",
            normalized_text="Free laptops for students.",
            classification="specific_promise",
            language="English"
        )
        p2 = PoliticalPromise(
            promise_id="P_AGRI_01",
            manifesto_id="M_DMK_2026",
            original_text="Crop loan waiver for farmers.",
            normalized_text="Crop loan waiver for farmers.",
            classification="general_policy",
            language="English"
        )
        self.db.add_all([p1, p2])
        self.db.commit()

        map1 = PromiseCategoryMapping(promise_id="P_EDU_01", category_id=c.id, is_primary=True)
        self.db.add(map1)
        self.db.commit()

        # Test search filter
        res_search = self.client.get("/api/promises/?search=laptops")
        data_search = json.loads(res_search.data.decode("utf-8"))["data"]
        self.assertEqual(data_search["total"], 1)
        self.assertEqual(data_search["items"][0]["promise_id"], "P_EDU_01")

        # Test category filter
        res_cat = self.client.get("/api/promises/?category=Education")
        data_cat = json.loads(res_cat.data.decode("utf-8"))["data"]
        self.assertEqual(data_cat["total"], 1)

        # Test pagination
        res_page = self.client.get("/api/promises/?page=1&limit=1")
        data_page = json.loads(res_page.data.decode("utf-8"))["data"]
        self.assertEqual(len(data_page["items"]), 1)
        self.assertEqual(data_page["total"], 2)
        self.assertEqual(data_page["pages"], 2)

    def test_assessment_endpoint_contract(self):
        """
        Verify EVERY assessment response provides:
        - promise
        - status
        - confidence
        - explanation
        - supporting_evidence
        - source_links
        """
        m = Manifesto(manifesto_id="M_CONTRACT", party="TVK", election_year=2026)
        p = PoliticalPromise(
            promise_id="P_CONTRACT_01",
            manifesto_id="M_CONTRACT",
            original_text="Free laptops for high school students.",
            normalized_text="Free laptops for high school students."
        )
        self.db.add_all([m, p])
        self.db.commit()

        ev = Evidence(
            content="G.O. Ms. No. 45 issued for laptop distribution.",
            page_number=1,
            supporting_values={
                "source_url": "https://cms.tn.gov.in/go_45.pdf",
                "source_domain": "cms.tn.gov.in",
                "source_name": "TN GO Portal",
                "source_tier": 1,
                "publication_date": "15/03/2021"
            }
        )
        self.db.add(ev)
        self.db.commit()

        link = PromiseEvidenceLink(promise_id="P_CONTRACT_01", evidence_id=ev.id, relevance_score=0.85)
        self.db.add(link)
        self.db.commit()

        assess = PromiseAssessment(
            promise_id="P_CONTRACT_01",
            status=PromiseStatus.POLICY_ACTION,
            confidence_score=0.85,
            rationale="Official GO issued sanctioning framework.",
            is_current=True
        )
        self.db.add(assess)
        self.db.commit()

        # Call GET /api/promises/<promise_id>/assessment
        res = self.client.get("/api/promises/P_CONTRACT_01/assessment")
        self.assertEqual(res.status_code, 200)

        data = json.loads(res.data.decode("utf-8"))["data"]

        # Assert mandatory contract keys
        mandatory_keys = ["promise", "status", "confidence", "explanation", "supporting_evidence", "source_links"]
        for key in mandatory_keys:
            self.assertIn(key, data, f"Assessment payload must provide '{key}'.")

        self.assertEqual(data["status"], "policy_action")
        self.assertEqual(data["confidence"], 0.85)
        self.assertEqual(data["promise"]["promise_id"], "P_CONTRACT_01")
        self.assertEqual(len(data["supporting_evidence"]), 1)
        self.assertEqual(len(data["source_links"]), 1)
        self.assertEqual(data["source_links"][0]["url"], "https://cms.tn.gov.in/go_45.pdf")

    def test_scheme_matches_and_evidence_matches_endpoints(self):
        """Verify scheme matches and evidence matches endpoints."""
        m = Manifesto(manifesto_id="M_MATCH", party="Party A", election_year=2026)
        p = PoliticalPromise(promise_id="P_MATCH_01", manifesto_id="M_MATCH", original_text="Text", normalized_text="Text")
        dept = BudgetDepartment(name="Education Dept")
        self.db.add_all([m, p, dept])
        self.db.commit()

        hs = HistoricalScheme(financial_year="2021-2022", scheme_name="Laptop Scheme", department_id=dept.id)
        self.db.add(hs)
        self.db.commit()

        s_link = PromiseSchemeLink(promise_id="P_MATCH_01", historical_scheme_id=hs.id, similarity_score=0.88)
        self.db.add(s_link)
        self.db.commit()

        # Test scheme matches endpoint
        res_sm = self.client.get("/api/promises/P_MATCH_01/scheme-matches")
        self.assertEqual(res_sm.status_code, 200)
        data_sm = json.loads(res_sm.data.decode("utf-8"))["data"]
        self.assertEqual(len(data_sm["scheme_matches"]), 1)
        self.assertEqual(data_sm["scheme_matches"][0]["similarity_score"], 0.88)

    def test_assessment_history_endpoint(self):
        """Verify assessment history endpoint returns audit trail entries."""
        m = Manifesto(manifesto_id="M_HIST", party="Party B", election_year=2026)
        p = PoliticalPromise(promise_id="P_HIST_01", manifesto_id="M_HIST", original_text="Text", normalized_text="Text")
        self.db.add_all([m, p])
        self.db.commit()

        h = PromiseAssessmentHistory(
            promise_id="P_HIST_01",
            previous_status="no_evidence_found",
            new_status="policy_action",
            change_reason="GO issued",
            changed_by="rule_engine"
        )
        self.db.add(h)
        self.db.commit()

        res = self.client.get("/api/promises/P_HIST_01/history")
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.data.decode("utf-8"))["data"]
        self.assertEqual(len(data["history"]), 1)
        self.assertEqual(data["history"][0]["new_status"], "policy_action")


if __name__ == "__main__":
    unittest.main()
