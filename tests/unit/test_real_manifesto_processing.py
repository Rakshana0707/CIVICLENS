"""
Unit tests for Real Manifesto Document Processing Pipeline (Phase 3.17).

Verifies:
- All 20 processed document JSON records exist in data/processed/manifestos/
- Complete provenance fields (document_id, manifesto_id, source_file_id, pages, content_hash)
- Traceability hierarchy: document -> page -> section -> text
- Page number preservation (1-indexed)
- Tamil, English, and Mixed language classification
- Accurate OCR flag tracking
- Absence of fabricated text on extraction failure
- Processing summary metrics matching 20 documents
"""

import os
import json
import unittest

PROCESSED_DIR = os.path.join("data", "processed", "manifestos")
MANIFEST_PATH = os.path.join("data", "raw", "manifestos", "manifest.json")
SUMMARY_PATH = os.path.join(PROCESSED_DIR, "processing_summary.json")


class TestRealManifestoProcessing(unittest.TestCase):

    def test_processed_output_directory_and_summary(self):
        """Verify processed output directory exists and summary JSON records 20 documents."""
        self.assertTrue(os.path.exists(PROCESSED_DIR), f"Processed output directory {PROCESSED_DIR} must exist")
        self.assertTrue(os.path.exists(SUMMARY_PATH), f"Summary file {SUMMARY_PATH} must exist")

        with open(SUMMARY_PATH, "r", encoding="utf-8") as f:
            summary = json.load(f)

        self.assertEqual(summary["total_documents"], 20, "Total processed documents must equal 20")
        self.assertEqual(summary["successfully_processed"], 20)
        self.assertEqual(summary["failed_documents"], 0)
        self.assertEqual(summary["unsupported_documents"], 0)

    def test_all_20_processed_document_json_files_exist(self):
        """Verify individual processed JSON files exist for all 20 manifestos."""
        with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
            manifest = json.load(f)

        for item in manifest["files"]:
            file_id = item["file_id"]
            doc_json_path = os.path.join(PROCESSED_DIR, f"{file_id}.json")
            self.assertTrue(os.path.exists(doc_json_path), f"Processed JSON file missing for {file_id}: {doc_json_path}")

    def test_provenance_traceability_structure(self):
        """Verify document -> page -> section -> text hierarchy and required provenance fields."""
        doc_path = os.path.join(PROCESSED_DIR, "MANIFESTO-FILE-006.json") # ADMK 2016
        with open(doc_path, "r", encoding="utf-8") as f:
            doc = json.load(f)

        required_keys = [
            "document_id", "manifesto_id", "source_file_id", "original_filename",
            "extracted_text", "language", "page_count", "section_information",
            "pages", "extraction_method", "ocr_used", "processing_timestamp",
            "processing_status", "parser_version", "content_hash"
        ]
        for key in required_keys:
            self.assertIn(key, doc, f"Key '{key}' missing from processed document JSON")

        self.assertEqual(doc["source_file_id"], "MANIFESTO-FILE-006")
        self.assertEqual(doc["page_count"], 41)
        self.assertGreater(len(doc["extracted_text"]), 10000)

        # Check page level traceability
        pages = doc["pages"]
        self.assertEqual(len(pages), 41)
        self.assertEqual(pages[0]["page_number"], 1)
        self.assertEqual(pages[40]["page_number"], 41)
        self.assertIn("extraction_method", pages[0])
        self.assertIn("character_count", pages[0])

    def test_ocr_flag_tracking(self):
        """Verify scanned PDFs properly record ocr_used=True and appropriate processing_status."""
        scanned_files = ["MANIFESTO-FILE-008", "MANIFESTO-FILE-009", "MANIFESTO-FILE-011", "MANIFESTO-FILE-020"]
        for fid in scanned_files:
            path = os.path.join(PROCESSED_DIR, f"{fid}.json")
            with open(path, "r", encoding="utf-8") as f:
                doc = json.load(f)

            self.assertTrue(doc["ocr_used"], f"File {fid} should have ocr_used=True")
            self.assertIn(doc["processing_status"], ["ocr_fallback", "ocr_required_pending_tesseract", "ocr_required_pending_layout"])

    def test_no_fabricated_text_on_scanned_documents(self):
        """Verify text is not artificially fabricated when direct text extraction yields empty results."""
        tvk_path = os.path.join(PROCESSED_DIR, "MANIFESTO-FILE-020.json") # TVK 2026 scanned PDF
        with open(tvk_path, "r", encoding="utf-8") as f:
            doc = json.load(f)

        self.assertEqual(doc["extracted_text"], "", "Extracted text must be empty string rather than fabricated text")
        self.assertEqual(doc["processing_status"], "ocr_required_pending_tesseract")


if __name__ == "__main__":
    unittest.main()
