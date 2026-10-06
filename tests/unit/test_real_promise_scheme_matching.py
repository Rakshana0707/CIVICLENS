"""
Unit tests for Phase 3.21 — Real Promise Embeddings & Historical Scheme Matching.
"""

import os
import json
import unittest
from backend.database.session import SessionLocal
from backend.models.promise import PoliticalPromise, PromiseSchemeLink
from backend.models.budget import HistoricalScheme
from scripts.match_real_promises_to_schemes import run_scheme_matching_pipeline


class TestRealPromiseSchemeMatching(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        # Run scheme matching pipeline
        run_scheme_matching_pipeline()

    def test_database_scheme_links_persisted(self):
        db = SessionLocal()
        try:
            link_count = db.query(PromiseSchemeLink).count()
            self.assertGreater(link_count, 0, "At least one PromiseSchemeLink record must be persisted")
            
            first_link = db.query(PromiseSchemeLink).first()
            self.assertIsNotNone(first_link.promise_id)
            self.assertIsNotNone(first_link.historical_scheme_id)
            self.assertGreater(first_link.similarity_score, 0.0)
            self.assertIsNotNone(first_link.model_name)
            self.assertIsNotNone(first_link.model_version)
            self.assertIsNotNone(first_link.matching_method)
            self.assertIn("topical/description overlap only", first_link.notes)
        finally:
            db.close()

    def test_output_json_files(self):
        matches_file = "data/processed/promises/promise_scheme_matches.json"
        summary_file = "data/processed/promises/promise_scheme_matching_summary.json"

        self.assertTrue(os.path.exists(matches_file), f"Missing {matches_file}")
        self.assertTrue(os.path.exists(summary_file), f"Missing {summary_file}")

        with open(matches_file, "r", encoding="utf-8") as f:
            matches = json.load(f)
        self.assertGreater(len(matches), 0)

        with open(summary_file, "r", encoding="utf-8") as f:
            summary = json.load(f)
        self.assertEqual(summary["total_promises_embedded"], 1065)
        self.assertIn("similarity_distribution", summary)

    def test_report_existence_and_disclaimer(self):
        report_file = "docs/phase3/promise_scheme_matching_report.md"
        self.assertTrue(os.path.exists(report_file), f"Missing report at {report_file}")

        with open(report_file, "r", encoding="utf-8") as f:
            report_text = f.read()

        self.assertIn("Real Promise Embeddings & Historical Scheme Matching Report", report_text)
        self.assertIn("IMPORTANT DISCLAIMER: SEMANTIC SIMILARITY ONLY", report_text)
        self.assertIn("1065", report_text)


if __name__ == "__main__":
    unittest.main()
