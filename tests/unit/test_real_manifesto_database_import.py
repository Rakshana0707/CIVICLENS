"""
Unit tests for Phase 3.20 — Real Manifesto Database Import.
"""

import os
import json
import unittest
from backend.database.session import SessionLocal
from backend.models.manifesto import ManifestoSource, ManifestoDocument, Manifesto
from backend.models.promise import PoliticalPromise, PromiseCategory
from scripts.import_real_manifesto_data import run_database_import


class TestRealManifestoDatabaseImport(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        # Run database import to ensure DB is populated
        run_database_import()

    def test_database_record_counts(self):
        db = SessionLocal()
        try:
            promises_cnt = db.query(PoliticalPromise).filter(PoliticalPromise.is_test_fixture == False).count()
            manifestos_cnt = db.query(Manifesto).count()
            docs_cnt = db.query(ManifestoDocument).count()
            sources_cnt = db.query(ManifestoSource).count()
            categories_cnt = db.query(PromiseCategory).count()

            self.assertEqual(promises_cnt, 1065)
            self.assertGreaterEqual(manifestos_cnt, 19)
            self.assertGreaterEqual(docs_cnt, 20)
            self.assertGreaterEqual(sources_cnt, 20)
            self.assertGreaterEqual(categories_cnt, 17)
        finally:
            db.close()

    def test_lineage_traceability(self):
        """Verify 5-tier foreign key lineage: Promise -> Manifesto -> Document -> Source."""
        db = SessionLocal()
        try:
            promise = db.query(PoliticalPromise).first()
            self.assertIsNotNone(promise, "At least one PoliticalPromise must exist in DB")
            
            manifesto = promise.manifesto
            self.assertIsNotNone(manifesto, f"Promise {promise.promise_id} must link to a valid Manifesto")

            doc = manifesto.document
            self.assertIsNotNone(doc, f"Manifesto {manifesto.manifesto_id} must link to a valid ManifestoDocument")

            source = manifesto.source
            self.assertIsNotNone(source, f"Manifesto {manifesto.manifesto_id} must link to a valid ManifestoSource")
        finally:
            db.close()

    def test_import_report_existence(self):
        report_file = "docs/phase3/database_import_report.md"
        self.assertTrue(os.path.exists(report_file), f"Missing report at {report_file}")

        with open(report_file, "r", encoding="utf-8") as f:
            report_text = f.read()

        self.assertIn("Real Manifesto & Promise Database Import Report", report_text)
        self.assertIn("IMPORT AUDIT STATUS: SUCCESSFUL & VERIFIED", report_text)
        self.assertIn("1065", report_text)

    def test_db_count_matches_validated_dataset(self):
        validated_file = "data/processed/promises/validated_promises.json"
        with open(validated_file, "r", encoding="utf-8") as f:
            validated_data = json.load(f)

        db = SessionLocal()
        try:
            db_promises_cnt = db.query(PoliticalPromise).filter(PoliticalPromise.is_test_fixture == False).count()
            self.assertEqual(db_promises_cnt, len(validated_data))
        finally:
            db.close()


if __name__ == "__main__":
    unittest.main()
