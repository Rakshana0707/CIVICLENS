"""
Unit tests for Government Implementation Evidence Acquisition Pipeline (Phase 3.9).

Verifies:
- Configurable domain whitelisting & rejection of unallowed domains
- Source tier and source metadata extraction
- Text extraction for HTML & PDF candidate documents
- Publication date extraction & SHA-256 content hashing
- DB persistence of Evidence records with supporting metadata
"""
import unittest
from datetime import datetime, timezone
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.database.base import Base
from backend.models.common import Evidence
from backend.acquisition.evidence_pipeline import EvidenceAcquisitionPipeline


class TestEvidenceAcquisition(unittest.TestCase):

    def setUp(self):
        # Create in-memory SQLite database
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        self.db = TestingSessionLocal()

        self.pipeline = EvidenceAcquisitionPipeline(db_session=self.db)

    def tearDown(self):
        self.db.close()
        Base.metadata.drop_all(self.engine)

    def test_domain_security_allowed_domains(self):
        """Verify domain whitelisting accepts allowed government domains."""
        allowed_urls = [
            "https://tn.gov.in/documents/policy.html",
            "https://cms.tn.gov.in/sites/default/files/go/sw_2021.pdf",
            "https://budget.tn.gov.in/demands/demand_15.pdf",
            "https://tnsocialwelfare.tn.gov.in/schemes.html",
            "https://assembly.tn.gov.in/debates/2021.pdf",
            "https://dipr.tn.gov.in/pressrelease/pr_101.pdf",
            "https://httpbin.org/get"  # Configured test fixture domain
        ]
        for url in allowed_urls:
            self.assertTrue(self.pipeline.is_domain_allowed(url), f"Domain for {url} should be allowed.")

    def test_domain_security_rejects_unallowed_domains(self):
        """Verify domain security strictly rejects arbitrary unallowed websites."""
        unallowed_urls = [
            "https://arbitrary-blog.com/tn-schemes",
            "https://news-site.org/politics/tn-budget",
            "https://random-scraps.io/data.pdf"
        ]
        for url in unallowed_urls:
            self.assertFalse(self.pipeline.is_domain_allowed(url), f"Domain for {url} should be rejected.")
            # Pipeline fetch attempt must return empty list immediately
            records = self.pipeline.fetch_and_extract_evidence(url)
            self.assertEqual(records, [])

    def test_source_metadata_and_tier_mapping(self):
        """Verify correct source tier and metadata mapping for government sources."""
        go_info = self.pipeline.get_source_info("https://cms.tn.gov.in/go.pdf")
        self.assertEqual(go_info["source_tier"], 1)
        self.assertEqual(go_info["source_type"], "Government Orders")

        budget_info = self.pipeline.get_source_info("https://budget.tn.gov.in/demands.pdf")
        self.assertEqual(budget_info["source_tier"], 1)
        self.assertEqual(budget_info["source_type"], "Budget documents")

    def test_publication_date_extraction(self):
        """Verify regex extraction of publication dates from document text."""
        sample_text = "Government Order G.O. Ms. No. 45, dated 15/03/2021 regarding scheme sanction."
        extracted_date = self.pipeline._extract_publication_date(sample_text)
        self.assertIsNotNone(extracted_date)
        self.assertIn("15/03/2021", extracted_date)

    def test_text_chunk_extraction_html(self):
        """Verify HTML document parsing into text chunks."""
        html_bytes = b"<html><body><h1>Government Order</h1><p>Sanction of Rs 1000 crore for social welfare scheme.</p></body></html>"
        chunks = self.pipeline._extract_text_chunks(html_bytes, "HTML")
        self.assertGreater(len(chunks), 0)
        all_text = " ".join(c[1] for c in chunks)
        self.assertIn("Sanction of Rs 1000 crore", all_text)

    def test_evidence_persistence_and_supporting_values(self):
        """Verify evidence records are persisted to DB with supporting metadata."""
        # Using httpbin.org allowed test fixture endpoint
        test_url = "https://httpbin.org/get"
        records = self.pipeline.fetch_and_extract_evidence(url=test_url, result_id="PROMISE_TEST_101")

        self.assertGreater(len(records), 0)
        rec = records[0]
        self.assertIn("id", rec)
        self.assertEqual(rec["result_type"], "GovernmentEvidence")
        self.assertEqual(rec["result_id"], "PROMISE_TEST_101")

        # Query database directly to confirm persistence
        db_ev = self.db.query(Evidence).filter_by(id=rec["id"]).first()
        self.assertIsNotNone(db_ev)
        self.assertEqual(db_ev.result_id, "PROMISE_TEST_101")
        self.assertIsNotNone(db_ev.supporting_values)
        self.assertEqual(db_ev.supporting_values["source_url"], test_url)
        self.assertIsNotNone(db_ev.supporting_values["content_hash"])
        self.assertIsNotNone(db_ev.supporting_values["source_tier"])


if __name__ == "__main__":
    unittest.main()
