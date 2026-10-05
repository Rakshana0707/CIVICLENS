"""
Unit tests for Promise-to-Historical-Scheme Matching (Phase 3.8).

Verifies:
- Text preprocessing & embedding generation pipeline
- Cosine similarity computation against Phase 2 HistoricalScheme objects
- Top-K ranking and threshold filtering
- Persisted PromiseSchemeLink fields (promise_id, scheme_id, similarity_score, model_name, model_version, generated_at, matching_method)
- Disclaimer logging (similarity != implementation/fulfillment)
- Handling Phase 2 DB data & synthetic TEST_FIXTURE objects
"""
import unittest
from datetime import datetime, timezone
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.database.base import Base
from backend.models.budget import BudgetDepartment, HistoricalScheme
from backend.models.manifesto import Manifesto
from backend.models.promise import PoliticalPromise, PromiseSchemeLink
from backend.nlp.promise_scheme_matcher import (
    PromiseSchemeMatcher,
    DEFAULT_MODEL_NAME,
    DEFAULT_MODEL_VERSION,
    MATCHING_METHOD,
    DISCLAIMER_NOTE
)
from backend.nlp.similarity import SemanticSchemeSearcher


class MockEmbedder:
    """Mock embedder providing deterministic vectors for testing without sentence-transformers dependency."""

    def generate_embedding(self, text: str):
        # Generate simple deterministic mock vectors based on text features
        text_lower = text.lower()
        v = [0.0] * 8
        if "school" in text_lower or "education" in text_lower or "student" in text_lower:
            v[0] = 1.0
            v[1] = 0.8
        if "laptop" in text_lower or "computer" in text_lower or "digital" in text_lower:
            v[0] = 0.7
            v[2] = 0.9
        if "farmer" in text_lower or "agriculture" in text_lower or "crop" in text_lower:
            v[3] = 1.0
            v[4] = 0.9
        if "hospital" in text_lower or "health" in text_lower or "doctor" in text_lower:
            v[5] = 1.0
            v[6] = 0.9
        # Normalize
        norm = sum(x**2 for x in v)**0.5
        if norm > 0:
            v = [x / norm for x in v]
        return v


class TestPromiseSchemeMatching(unittest.TestCase):

    def setUp(self):
        # Create in-memory SQLite database
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        self.db = TestingSessionLocal()

        self.embedder = MockEmbedder()
        self.searcher = SemanticSchemeSearcher(db_session=self.db, embedder=self.embedder)
        self.matcher = PromiseSchemeMatcher(db_session=self.db, searcher=self.searcher)

        self._populate_phase2_data()

    def tearDown(self):
        self.db.close()
        Base.metadata.drop_all(self.engine)

    def _populate_phase2_data(self):
        """Populate Phase 2 HistoricalScheme test records with embeddings."""
        dept_edu = BudgetDepartment(name="School Education Department")
        dept_agri = BudgetDepartment(name="Agriculture Department")
        dept_health = BudgetDepartment(name="Health & Family Welfare Department")
        self.db.add_all([dept_edu, dept_agri, dept_health])
        self.db.commit()

        # Scheme 1: Education
        text_1 = "Free Laptop Distribution Scheme for High School Students"
        vec_1 = self.embedder.generate_embedding(text_1)
        hs1 = HistoricalScheme(
            financial_year="2021-2022",
            scheme_name=text_1,
            description="Laptops distributed to Class 11 and 12 students in government schools.",
            department_id=dept_edu.id,
            embedding={
                "model_name": DEFAULT_MODEL_NAME,
                "model_version": DEFAULT_MODEL_VERSION,
                "vector": vec_1
            }
        )

        # Scheme 2: Agriculture
        text_2 = "Chief Minister Crop Insurance Assistance Scheme"
        vec_2 = self.embedder.generate_embedding(text_2)
        hs2 = HistoricalScheme(
            financial_year="2021-2022",
            scheme_name=text_2,
            description="Financial compensation for small farmers facing crop loss due to drought.",
            department_id=dept_agri.id,
            embedding={
                "model_name": DEFAULT_MODEL_NAME,
                "model_version": DEFAULT_MODEL_VERSION,
                "vector": vec_2
            }
        )

        # Scheme 3: Healthcare
        text_3 = "Comprehensive Health Insurance Scheme"
        vec_3 = self.embedder.generate_embedding(text_3)
        hs3 = HistoricalScheme(
            financial_year="2021-2022",
            scheme_name=text_3,
            description="Free hospital care coverage for low income families up to 5 lakhs.",
            department_id=dept_health.id,
            embedding={
                "model_name": DEFAULT_MODEL_NAME,
                "model_version": DEFAULT_MODEL_VERSION,
                "vector": vec_3
            }
        )

        self.db.add_all([hs1, hs2, hs3])
        self.db.commit()

    def test_text_preprocessing(self):
        """Verify promise text preprocessing prior to embedding generation."""
        raw = "  We  will   provide\u00a0free  laptops  to students.  "
        clean = self.matcher.preprocess_text(raw)
        self.assertEqual(clean, "We will provide free laptops to students.")

    def test_match_single_promise_to_historical_scheme(self):
        """Verify matching a single promise against Phase 2 scheme embeddings."""
        m = Manifesto(manifesto_id="M_TEST_1", party="Party A", election_year=2026)
        p = PoliticalPromise(
            promise_id="TEST_FIXTURE_P1",
            manifesto_id="M_TEST_1",
            original_text="We promise free laptops for all high school students.",
            normalized_text="We promise free laptops for all high school students.",
            is_test_fixture=True
        )
        self.db.add_all([m, p])
        self.db.commit()

        matches = self.matcher.match_promise(p, top_k=3, similarity_threshold=0.3, persist_links=True)
        self.assertGreater(len(matches), 0)

        top_match = matches[0]
        self.assertEqual(top_match["promise_id"], "TEST_FIXTURE_P1")
        self.assertIn("Laptop", top_match["scheme_name"])
        self.assertEqual(top_match["model_name"], DEFAULT_MODEL_NAME)
        self.assertEqual(top_match["model_version"], DEFAULT_MODEL_VERSION)
        self.assertEqual(top_match["matching_method"], MATCHING_METHOD)
        self.assertIn("generated_at", top_match)
        self.assertGreaterEqual(top_match["similarity_score"], 0.3)

    def test_persisted_promise_scheme_links(self):
        """Verify attributes stored in PromiseSchemeLink DB records."""
        m = Manifesto(manifesto_id="M_TEST_2", party="Party B", election_year=2026)
        p = PoliticalPromise(
            promise_id="TEST_FIXTURE_P2",
            manifesto_id="M_TEST_2",
            original_text="Crop loan waivers and relief for farmers.",
            normalized_text="Crop loan waivers and relief for farmers.",
            is_test_fixture=True
        )
        self.db.add_all([m, p])
        self.db.commit()

        self.matcher.match_promise(p, top_k=2, similarity_threshold=0.3, persist_links=True)

        links = self.db.query(PromiseSchemeLink).filter_by(promise_id="TEST_FIXTURE_P2").all()
        self.assertGreater(len(links), 0)

        link = links[0]
        self.assertEqual(link.promise_id, "TEST_FIXTURE_P2")
        self.assertIsNotNone(link.historical_scheme_id)
        self.assertIsNotNone(link.similarity_score)
        self.assertEqual(link.model_name, DEFAULT_MODEL_NAME)
        self.assertEqual(link.model_version, DEFAULT_MODEL_VERSION)
        self.assertEqual(link.matching_method, MATCHING_METHOD)
        self.assertEqual(link.notes, DISCLAIMER_NOTE)

    def test_top_k_ranking_and_threshold_filtering(self):
        """Verify that returned schemes are ranked descending by score and filtered by threshold."""
        m = Manifesto(manifesto_id="M_TEST_3", party="Party C", election_year=2026)
        p = PoliticalPromise(
            promise_id="TEST_FIXTURE_P3",
            manifesto_id="M_TEST_3",
            original_text="Free hospital care for all households.",
            normalized_text="Free hospital care for all households.",
            is_test_fixture=True
        )
        self.db.add_all([m, p])
        self.db.commit()

        # High threshold (0.9)
        matches_high = self.matcher.match_promise(p, top_k=5, similarity_threshold=0.9, persist_links=False)
        # Lower threshold (0.1)
        matches_low = self.matcher.match_promise(p, top_k=5, similarity_threshold=0.1, persist_links=False)

        self.assertLessEqual(len(matches_high), len(matches_low))

        # Check descending order of similarity score
        scores = [m["similarity_score"] for m in matches_low]
        self.assertEqual(scores, sorted(scores, reverse=True))

    def test_match_all_promises_batch(self):
        """Verify batch matching over all promises in the database."""
        m = Manifesto(manifesto_id="M_TEST_BATCH", party="Party D", election_year=2026)
        p1 = PoliticalPromise(promise_id="P_BATCH_1", manifesto_id="M_TEST_BATCH", original_text="Laptops for students", normalized_text="Laptops for students")
        p2 = PoliticalPromise(promise_id="P_BATCH_2", manifesto_id="M_TEST_BATCH", original_text="Free health insurance", normalized_text="Free health insurance")
        self.db.add_all([m, p1, p2])
        self.db.commit()

        summary = self.matcher.match_all_promises(top_k=2, similarity_threshold=0.3)
        self.assertEqual(summary["total_promises"], 2)
        self.assertEqual(summary["matched_promises"], 2)
        self.assertGreater(summary["total_links_created"], 0)


if __name__ == "__main__":
    unittest.main()
