"""
Unit tests for Promise-to-Evidence Candidate Matching (Phase 3.10).

Verifies:
- Multi-signal combination (semantic, keywords, entities, department, time, scheme link)
- Candidate relevance scoring & threshold filtering
- Output payload attributes (promise_id, evidence_id, relevance_score, matching_method, matched_metadata, model_information, timestamp)
- Persisted PromiseEvidenceLink DB records
- Candidate retrieval disclaimer (candidate retrieval != implementation assessment)
"""
import unittest
from datetime import datetime, timezone
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.database.base import Base
from backend.models.manifesto import Manifesto
from backend.models.promise import PoliticalPromise, PromiseEvidenceLink, PromiseSchemeLink
from backend.models.common import Evidence
from backend.models.budget import BudgetDepartment, HistoricalScheme
from backend.nlp.promise_evidence_matcher import (
    PromiseEvidenceMatcher,
    DEFAULT_MODEL_NAME,
    DEFAULT_MODEL_VERSION,
    MATCHING_METHOD,
    DISCLAIMER_NOTE
)


class MockEmbedder:
    """Mock embedder providing deterministic vectors for testing without sentence-transformers dependency."""

    def generate_embedding(self, text: str):
        text_lower = text.lower()
        v = [0.0] * 8
        if "laptop" in text_lower or "student" in text_lower or "education" in text_lower:
            v[0] = 0.9
            v[1] = 0.8
        if "farmer" in text_lower or "crop" in text_lower or "loan" in text_lower:
            v[2] = 0.9
            v[3] = 0.9
        if "hospital" in text_lower or "health" in text_lower or "insurance" in text_lower:
            v[4] = 0.9
            v[5] = 0.8
        norm = sum(x**2 for x in v)**0.5
        if norm > 0:
            v = [x / norm for x in v]
        return v


class TestPromiseEvidenceMatching(unittest.TestCase):

    def setUp(self):
        # Create SQLite in-memory database
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        self.db = TestingSessionLocal()

        self.embedder = MockEmbedder()
        self.matcher = PromiseEvidenceMatcher(
            db_session=self.db,
            embedder=self.embedder
        )

        self._populate_test_data()

    def tearDown(self):
        self.db.close()
        Base.metadata.drop_all(self.engine)

    def _populate_test_data(self):
        # Create Manifesto & Promise
        m = Manifesto(manifesto_id="M_EVID_TEST", party="Party A", election_year=2026)
        p1 = PoliticalPromise(
            promise_id="P_EVID_101",
            manifesto_id="M_EVID_TEST",
            original_text="We will provide free laptops to 50000 high school students.",
            normalized_text="We will provide free laptops to 50000 high school students.",
            metadata_json={
                "target_population": "Students",
                "sector": "Education",
                "department": "School Education",
                "monetary_target": "Rs. 1000",
                "numeric_target": "50000"
            }
        )
        self.db.add_all([m, p1])
        self.db.commit()

        # Create Evidence 1: Relevant government order
        ev1 = Evidence(
            content="G.O. Ms. No. 45 dated 15/03/2021: Sanction of Rs. 1000 crore for free laptop distribution to high school students in School Education department.",
            page_number=1,
            supporting_values={
                "source_url": "https://cms.tn.gov.in/go_45.pdf",
                "source_type": "Government Orders",
                "source_tier": 1,
                "publication_date": "15/03/2021"
            },
            result_type="GovernmentEvidence"
        )

        # Create Evidence 2: Irrelevant policy note
        ev2 = Evidence(
            content="Policy Note on Rural Fisheries Development and Coastal Infrastructure.",
            page_number=2,
            supporting_values={
                "source_url": "https://tn.gov.in/fisheries.html",
                "source_type": "Department pages",
                "source_tier": 1
            },
            result_type="GovernmentEvidence"
        )

        self.db.add_all([ev1, ev2])
        self.db.commit()

        # Create Historical Scheme Link for Phase 3.8 signal integration
        dept = BudgetDepartment(name="School Education Department")
        self.db.add(dept)
        self.db.commit()

        hs = HistoricalScheme(financial_year="2021-2022", scheme_name="Laptop Scheme", department_id=dept.id)
        self.db.add(hs)
        self.db.commit()

        s_link = PromiseSchemeLink(
            promise_id="P_EVID_101",
            historical_scheme_id=hs.id,
            similarity_score=0.9
        )
        self.db.add(s_link)
        self.db.commit()

    def test_calculate_candidate_match_signals(self):
        """Verify candidate match relevance calculation combining multi-signal inputs."""
        p = self.db.query(PoliticalPromise).filter_by(promise_id="P_EVID_101").first()
        ev_rel = self.db.query(Evidence).filter(Evidence.content.like("%laptop%")).first()

        match_res = self.matcher.calculate_candidate_match(p, ev_rel)

        self.assertEqual(match_res["promise_id"], "P_EVID_101")
        self.assertEqual(match_res["evidence_id"], ev_rel.id)
        self.assertGreater(match_res["relevance_score"], 0.3)
        self.assertEqual(match_res["matching_method"], MATCHING_METHOD)

        # Verify matched_metadata signals
        meta = match_res["matched_metadata"]
        self.assertIn("matched_signals", meta)
        self.assertIn("keywords_entities", meta["matched_signals"])
        self.assertIn("historical_scheme_relationship", meta["matched_signals"])

        # Verify model_information
        self.assertEqual(match_res["model_information"]["model_name"], DEFAULT_MODEL_NAME)
        self.assertEqual(match_res["model_information"]["model_version"], DEFAULT_MODEL_VERSION)
        self.assertIn("timestamp", match_res)

    def test_match_promise_with_evidence_candidates_persisted(self):
        """Verify candidate matching retrieves top matches and persists PromiseEvidenceLink DB records."""
        p = self.db.query(PoliticalPromise).filter_by(promise_id="P_EVID_101").first()

        top_candidates = self.matcher.match_promise_with_evidence_candidates(
            promise=p,
            top_k=2,
            relevance_threshold=0.2,
            persist_links=True
        )

        self.assertGreater(len(top_candidates), 0)
        self.assertEqual(top_candidates[0]["promise_id"], "P_EVID_101")

        # Verify persisted DB records
        links = self.db.query(PromiseEvidenceLink).filter_by(promise_id="P_EVID_101").all()
        self.assertGreater(len(links), 0)

        link = links[0]
        self.assertEqual(link.promise_id, "P_EVID_101")
        self.assertEqual(link.matching_method, MATCHING_METHOD)
        self.assertEqual(link.model_name, DEFAULT_MODEL_NAME)
        self.assertEqual(link.model_version, DEFAULT_MODEL_VERSION)
        self.assertIsNotNone(link.relevance_score)
        self.assertEqual(link.relevance_notes, DISCLAIMER_NOTE)
        self.assertIn("matched_signals", link.matched_metadata)

    def test_threshold_filtering(self):
        """Verify that irrelevant evidence is filtered out when below relevance_threshold."""
        p = self.db.query(PoliticalPromise).filter_by(promise_id="P_EVID_101").first()

        # High threshold (0.8) should exclude lower relevance items
        high_matches = self.matcher.match_promise_with_evidence_candidates(
            promise=p,
            top_k=5,
            relevance_threshold=0.8,
            persist_links=False
        )
        # Low threshold (0.1)
        low_matches = self.matcher.match_promise_with_evidence_candidates(
            promise=p,
            top_k=5,
            relevance_threshold=0.1,
            persist_links=False
        )

        self.assertLess(len(high_matches), len(low_matches))

    def test_match_all_promises_batch(self):
        """Verify batch candidate retrieval over all promises in the database."""
        summary = self.matcher.match_all_promises_with_evidence(top_k=3, relevance_threshold=0.2)
        self.assertEqual(summary["total_promises"], 1)
        self.assertEqual(summary["promises_with_candidates"], 1)
        self.assertGreater(summary["total_links_created"], 0)


if __name__ == "__main__":
    unittest.main()
