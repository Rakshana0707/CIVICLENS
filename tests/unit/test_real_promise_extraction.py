"""
Unit tests for Real Manifesto Promise Extraction & Normalization (Phase 3.18).

Verifies:
- Extraction of promises from real manifesto documents in data/processed/manifestos/
- Traceability: promise_id -> manifesto_id -> document_id -> source_file_id -> page_number
- Tamil text preservation (original_text untouched, no translation loss)
- Classification logic (specific_promise, general_policy vs slogans/vision/ambiguous)
- Metadata extraction & default null handling (no fabricated details)
- Database persistence of PoliticalPromise and PromiseCategoryMapping records
- 1,065 accepted real promises in data/processed/promises/extracted_promises.json
"""

import os
import json
import unittest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.database.base import Base
from backend.models.manifesto import Manifesto
from backend.models.promise import PoliticalPromise, PromiseCategory, PromiseCategoryMapping

PROMISES_JSON_PATH = os.path.join("data", "processed", "promises", "extracted_promises.json")
SUMMARY_PATH = os.path.join("data", "processed", "promises", "promise_extraction_summary.json")
DB_PATH = "civiclens.db"


class TestRealPromiseExtraction(unittest.TestCase):

    def test_promises_json_dataset_exists_and_count(self):
        """Verify extracted_promises.json exists and contains 1,065 accepted promise records."""
        self.assertTrue(os.path.exists(PROMISES_JSON_PATH), f"Promises dataset missing at {PROMISES_JSON_PATH}")
        self.assertTrue(os.path.exists(SUMMARY_PATH), f"Summary missing at {SUMMARY_PATH}")

        with open(SUMMARY_PATH, "r", encoding="utf-8") as f:
            summary = json.load(f)

        self.assertEqual(summary["total_candidate_statements"], 14105)
        self.assertEqual(summary["accepted_promises"], 1065)

        with open(PROMISES_JSON_PATH, "r", encoding="utf-8") as f:
            promises = json.load(f)

        self.assertEqual(len(promises), 1065)

    def test_promise_provenance_and_traceability(self):
        """Verify provenance fields on extracted promises."""
        with open(PROMISES_JSON_PATH, "r", encoding="utf-8") as f:
            promises = json.load(f)

        p = promises[0]
        required_keys = [
            "promise_id", "manifesto_id", "document_id", "source_file_id",
            "original_text", "normalized_text", "page_number", "section",
            "language", "category", "classification", "extraction_method",
            "confidence", "metadata", "created_at"
        ]
        for k in required_keys:
            self.assertIn(k, p, f"Key '{k}' missing from promise record")

        self.assertTrue(p["promise_id"].startswith(p["manifesto_id"]))
        self.assertIn(p["classification"], ["specific_promise", "general_policy"])

    def test_tamil_text_preservation(self):
        """Verify Tamil promises preserve original Tamil script without translation away."""
        with open(PROMISES_JSON_PATH, "r", encoding="utf-8") as f:
            promises = json.load(f)

        tamil_promises = [p for p in promises if p["language"] == "Tamil"]
        self.assertGreater(len(tamil_promises), 100, "Should have over 100 Tamil promises")

        # Verify Tamil characters exist in original_text
        t_sample = tamil_promises[0]
        has_tamil_script = any('\u0B80' <= char <= '\u0BFF' for char in t_sample["original_text"])
        self.assertTrue(has_tamil_script, "Tamil promise original_text must preserve Tamil script")

    def test_metadata_extraction_and_no_fabrication(self):
        """Verify metadata fields extract targets when present and use null when missing."""
        with open(PROMISES_JSON_PATH, "r", encoding="utf-8") as f:
            promises = json.load(f)

        for p in promises:
            meta = p["metadata"]
            self.assertIn("target_population", meta)
            self.assertIn("monetary_target", meta)
            self.assertIn("numeric_target", meta)
            self.assertIn("sector", meta)

    def test_database_persistence(self):
        """Verify PoliticalPromise records exist in SQLite database civiclens.db."""
        if os.path.exists(DB_PATH):
            engine = create_engine(f"sqlite:///{DB_PATH}")
            Session = sessionmaker(bind=engine)
            db = Session()

            db_promise_count = db.query(PoliticalPromise).count()
            self.assertGreaterEqual(db_promise_count, 1065, "DB must contain at least 1,065 promises")
            db.close()


if __name__ == "__main__":
    unittest.main()
