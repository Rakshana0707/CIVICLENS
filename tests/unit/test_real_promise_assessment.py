"""
Unit tests for Phase 3.23 — Real Promise Status Assessment.
"""

import os
import json
import unittest
from backend.database.session import SessionLocal
from backend.models.promise import PoliticalPromise, PromiseAssessment, PromiseAssessmentHistory, PromiseStatus
from scripts.assess_real_promises import run_real_promise_assessment


class TestRealPromiseAssessment(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        # Execute promise assessment pipeline
        run_real_promise_assessment()

    def test_assessment_field_completeness(self):
        assessments_file = "data/processed/assessments/real_promise_assessments.json"
        self.assertTrue(os.path.exists(assessments_file), f"Missing {assessments_file}")

        with open(assessments_file, "r", encoding="utf-8") as f:
            assessments = json.load(f)

        self.assertEqual(len(assessments), 1065)

        required_keys = [
            "promise_id", "status", "confidence", "explanation",
            "evidence_ids", "source_tiers", "assessment_date", "methodology"
        ]

        for item in assessments:
            for k in required_keys:
                self.assertIn(k, item, f"Missing required assessment key {k} in record {item.get('promise_id')}")

    def test_allowed_status_taxonomy(self):
        allowed_statuses = {
            "not_assessed", "no_evidence_found", "announced", "policy_action",
            "partially_implemented", "implemented", "unclear", "disputed"
        }

        assessments_file = "data/processed/assessments/real_promise_assessments.json"
        with open(assessments_file, "r", encoding="utf-8") as f:
            assessments = json.load(f)

        for item in assessments:
            st = item["status"]
            self.assertIn(st, allowed_statuses, f"Invalid status '{st}' found for promise {item['promise_id']}")

    def test_no_evidence_found_rule(self):
        assessments_file = "data/processed/assessments/real_promise_assessments.json"
        with open(assessments_file, "r", encoding="utf-8") as f:
            assessments = json.load(f)

        for item in assessments:
            if not item["evidence_ids"] and item["status"] == "no_evidence_found":
                self.assertIn("Absence of evidence is not proof of non-implementation", item["explanation"])
                self.assertNotIn("not_implemented", item["status"])

    def test_database_persistence(self):
        db = SessionLocal()
        try:
            assessments_cnt = db.query(PromiseAssessment).count()
            history_cnt = db.query(PromiseAssessmentHistory).count()

            self.assertEqual(assessments_cnt, 1065)
            self.assertEqual(history_cnt, 1065)

            first_ass = db.query(PromiseAssessment).first()
            self.assertIsNotNone(first_ass.promise_id)
            self.assertIsNotNone(first_ass.status)
            self.assertGreaterEqual(first_ass.confidence_score, 0.0)
            self.assertIsNotNone(first_ass.rationale)
        finally:
            db.close()

    def test_report_existence_and_safeguards(self):
        report_file = "docs/phase3/assessment_report.md"
        self.assertTrue(os.path.exists(report_file))

        with open(report_file, "r", encoding="utf-8") as f:
            report_text = f.read()

        self.assertIn("Real Promise Status Assessment Report", report_text)
        self.assertIn("NO EVIDENCE FOUND", report_text)
        self.assertIn("1065", report_text)


if __name__ == "__main__":
    unittest.main()
