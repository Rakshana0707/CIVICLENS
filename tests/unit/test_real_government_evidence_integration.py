"""
Unit tests for Phase 3.22 — Real Government Evidence Integration.
"""

import os
import json
import unittest
from backend.database.session import SessionLocal
from backend.models.common import Evidence, Document, Source
from backend.models.promise import PromiseEvidenceLink, PoliticalPromise
from scripts.integrate_government_evidence import (
    run_evidence_integration_pipeline,
    is_url_domain_allowed,
    ALLOWED_GOVT_DOMAINS
)


class TestRealGovernmentEvidenceIntegration(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        # Run evidence integration pipeline
        run_evidence_integration_pipeline()

    def test_domain_whitelist_enforcement(self):
        # Allowed official domains
        self.assertTrue(is_url_domain_allowed("https://cms.tn.gov.in/sites/default/files/go/test.pdf"))
        self.assertTrue(is_url_domain_allowed("https://budget.tn.gov.in/speech.pdf"))
        self.assertTrue(is_url_domain_allowed("https://dipr.tn.gov.in/press_release.pdf"))

        # Arbitrary / non-government domains must be blocked
        self.assertFalse(is_url_domain_allowed("https://randomwebsite.com/article.html"))
        self.assertFalse(is_url_domain_allowed("https://fake-news-portal.org/claim"))

    def test_evidence_schema_completeness(self):
        evidence_file = "data/processed/evidence/government_evidence.json"
        self.assertTrue(os.path.exists(evidence_file), f"Missing {evidence_file}")

        with open(evidence_file, "r", encoding="utf-8") as f:
            evidence_items = json.load(f)

        self.assertGreater(len(evidence_items), 0)

        required_keys = [
            "evidence_id", "source_url", "source_title", "source_type", "publisher",
            "publication_date", "retrieval_date", "source_tier", "document_reference",
            "relevant_text", "related_department", "related_scheme", "evidence_method"
        ]

        for ev in evidence_items:
            for k in required_keys:
                self.assertIn(k, ev, f"Missing key {k} in evidence record {ev.get('evidence_id')}")

    def test_database_evidence_links_persisted(self):
        db = SessionLocal()
        try:
            ev_count = db.query(Evidence).count()
            self.assertGreaterEqual(ev_count, 12, "At least 12 Evidence records must exist in DB")

            link_count = db.query(PromiseEvidenceLink).count()
            self.assertGreater(link_count, 0, "At least one PromiseEvidenceLink record must exist in DB")

            first_link = db.query(PromiseEvidenceLink).first()
            self.assertIsNotNone(first_link.promise_id)
            self.assertIsNotNone(first_link.evidence_id)
            self.assertGreater(first_link.relevance_score, 0.0)
            self.assertEqual(first_link.matching_method, "multi_signal_hybrid_retrieval")
            self.assertIn("NOT a final implementation status assessment", first_link.relevance_notes)
        finally:
            db.close()

    def test_absence_of_evidence_rule(self):
        summary_file = "data/processed/evidence/evidence_integration_summary.json"
        self.assertTrue(os.path.exists(summary_file))

        with open(summary_file, "r", encoding="utf-8") as f:
            summary = json.load(f)

        self.assertIn("promises_with_no_evidence_found", summary)
        self.assertGreater(summary["promises_with_no_evidence_found"], 0)

    def test_report_existence_and_disclaimer(self):
        report_file = "docs/phase3/evidence_integration_report.md"
        self.assertTrue(os.path.exists(report_file))

        with open(report_file, "r", encoding="utf-8") as f:
            report_text = f.read()

        self.assertIn("Real Government Evidence Integration Report", report_text)
        self.assertIn("CRITICAL RULE: CANDIDATE RETRIEVAL & EVIDENCE LINKING ONLY", report_text)
        self.assertIn("no_evidence_found", report_text)


if __name__ == "__main__":
    unittest.main()
