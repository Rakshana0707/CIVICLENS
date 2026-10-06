"""
Unit tests for Phase 3.19 — Real Promise Data Validation & Normalization Pipeline.
"""

import os
import json
import unittest
from scripts.validate_real_promises import (
    check_tamil_unicode_integrity,
    is_incomplete_sentence,
    is_page_or_header_artifact,
    jaccard_similarity,
    validate_promise_record
)


class TestRealPromiseValidation(unittest.TestCase):

    def test_tamil_unicode_integrity_check(self):
        # Valid Tamil text
        valid_tamil = "விவசாயிகளுக்கு இலவச மின்சாரம் வழங்கப்படும்"
        self.assertEqual(len(check_tamil_unicode_integrity(valid_tamil)), 0)

        # Unattached diacritic at start or after space
        broken_tamil = " ொ ாருளாதார வளர்ச்சி"
        flags = check_tamil_unicode_integrity(broken_tamil)
        self.assertTrue(len(flags) > 0)

    def test_incomplete_sentence_detection(self):
        # Complete sentence
        complete = "A new medical college will be established in every district."
        self.assertFalse(is_incomplete_sentence(complete))

        # Fragment starting with lower-case leading verb/conjunction
        fragment_start = "will prescribe fees for private school students"
        self.assertTrue(is_incomplete_sentence(fragment_start))

        # Fragment ending with dangling preposition
        fragment_end = "Higher education subsidies will be provided to"
        self.assertTrue(is_incomplete_sentence(fragment_end))

        # Short text < 15 chars
        short_fragment = "Free laptops"
        self.assertTrue(is_incomplete_sentence(short_fragment))

    def test_page_or_header_artifact_detection(self):
        # Page numbers
        self.assertTrue(is_page_or_header_artifact("Page 12 of 150"))
        self.assertTrue(is_page_or_header_artifact("12"))
        self.assertTrue(is_page_or_header_artifact("--- 45 ---"))

        # Banner title
        self.assertTrue(is_page_or_header_artifact("ELECTION MANIFESTO 2026"))

        # Valid promise text should NOT be an artifact
        self.assertFalse(is_page_or_header_artifact("100 days of guaranteed wage employment will be provided."))

    def test_jaccard_similarity(self):
        s1 = {"state", "highway", "infrastructure", "modernized"}
        s2 = {"state", "highway", "infrastructure", "expanded"}
        sim = jaccard_similarity(s1, s2)
        self.assertGreater(sim, 0.5)

        s3 = {"education", "schools", "teachers"}
        self.assertEqual(jaccard_similarity(s1, s3), 0.0)

    def test_validate_promise_record_status(self):
        seen_exact = {}
        seen_token_sets = []

        valid_record = {
            "promise_id": "P-TEST-001",
            "manifesto_id": "MF-DMK-2026",
            "document_id": "DOC-001",
            "source_file_id": "SRC-001",
            "original_text": "Special economic zones for textiles and technology will be established.",
            "normalized_text": "Special economic zones for textiles and technology will be established.",
            "page_number": 5,
            "section": "Industry & Infrastructure",
            "language": "English",
            "category": "Industry",
            "classification": "specific_promise",
            "confidence": 0.95
        }

        status, score, flags, v_result = validate_promise_record(valid_record, seen_exact, seen_token_sets)
        self.assertEqual(status, "valid")
        self.assertEqual(score, 1.0)
        self.assertEqual(v_result["validation_status"], "valid")

        # Duplicate record test
        dup_record = dict(valid_record)
        dup_record["promise_id"] = "P-TEST-002"
        status_dup, score_dup, flags_dup, _ = validate_promise_record(dup_record, seen_exact, seen_token_sets)
        self.assertEqual(status_dup, "duplicate")
        self.assertIn("exact_duplicate", flags_dup)

    def test_output_artifacts_exist_and_valid(self):
        validated_file = "data/processed/promises/validated_promises.json"
        summary_file = "data/processed/promises/promise_validation_summary.json"
        report_file = "docs/phase3/promise_validation_report.md"

        self.assertTrue(os.path.exists(validated_file), f"Missing {validated_file}")
        self.assertTrue(os.path.exists(summary_file), f"Missing {summary_file}")
        self.assertTrue(os.path.exists(report_file), f"Missing {report_file}")

        with open(validated_file, "r", encoding="utf-8") as f:
            validated_data = json.load(f)
        self.assertEqual(len(validated_data), 1065)

        with open(summary_file, "r", encoding="utf-8") as f:
            summary = json.load(f)
        self.assertEqual(summary["total_promises_evaluated"], 1065)
        self.assertIn("valid", summary["validation_status_breakdown"])

        with open(report_file, "r", encoding="utf-8") as f:
            report_text = f.read()
        self.assertIn("Real Promise Dataset Validation & Normalization Report", report_text)
        self.assertIn("DISCLAIMER: DATA QUALITY ASSESSMENT ONLY", report_text)


if __name__ == "__main__":
    unittest.main()
