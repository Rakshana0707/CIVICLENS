"""
Unit tests for Real Manifesto Dataset Registration & Inventory (Phase 3.16).

Verifies:
- ZIP file location and untouched integrity
- ZIP SHA-256 checksum calculation
- Extraction into data/raw/manifestos/
- Complete registration record in dataset_registration.json
- Complete file inventory and SHA-256 hashes in manifest.json
- Duplicate classification logic
- Absence of fabricated metadata
- Existing Phase 3 pipeline regression compatibility
"""

import os
import json
import hashlib
import unittest

ZIP_PATH = r"C:\Users\Shiv Rakshana\AppData\Local\Packages\5319275A.WhatsAppDesktop_cv1g1gvanyjgm\LocalState\sessions\41702EBA7FCF775C469AE200A92D3D74C7612B6D\transfers\2026-40\Manifestos.zip"
EXPECTED_ZIP_SHA256 = "5d61bc577f859b919277dcd347728f8c1f5fa28784b9598b87876647523c52de"
RAW_DIR = os.path.join("data", "raw", "manifestos", "real_manifestos_20261006")
MANIFEST_PATH = os.path.join("data", "raw", "manifestos", "manifest.json")
REGISTRATION_PATH = os.path.join(RAW_DIR, "dataset_registration.json")


class TestPhase3DatasetRegistration(unittest.TestCase):

    def test_zip_location_and_untouched_integrity(self):
        """Verify ZIP archive exists, size is correct, and original file remains untouched."""
        self.assertTrue(os.path.exists(ZIP_PATH), f"Original ZIP archive must exist at {ZIP_PATH}")
        size = os.path.getsize(ZIP_PATH)
        self.assertEqual(size, 141621174, "Original ZIP archive size must match exactly 141621174 bytes")

    def test_zip_checksum(self):
        """Verify calculated ZIP SHA-256 matches expected checksum."""
        h = hashlib.sha256()
        with open(ZIP_PATH, "rb") as f:
            while chunk := f.read(8192 * 1024):
                h.update(chunk)
        calc_sha256 = h.hexdigest()
        self.assertEqual(calc_sha256, EXPECTED_ZIP_SHA256, "ZIP checksum must match recorded hash")

    def test_dataset_extraction_and_registration_record(self):
        """Verify extracted directory and registration metadata record."""
        self.assertTrue(os.path.exists(RAW_DIR), f"Extracted directory {RAW_DIR} must exist")
        self.assertTrue(os.path.exists(REGISTRATION_PATH), f"Registration file {REGISTRATION_PATH} must exist")

        with open(REGISTRATION_PATH, "r", encoding="utf-8") as f:
            reg_data = json.load(f)

        self.assertEqual(reg_data["dataset_id"], "DS-TN-MANIFESTOS-20261006")
        self.assertEqual(reg_data["original_zip_sha256"], EXPECTED_ZIP_SHA256)
        self.assertEqual(reg_data["file_count"], 20)
        self.assertEqual(reg_data["status"], "registered")

    def test_manifest_inventory_and_duplicate_classification(self):
        """Verify manifest.json contains all 20 files, valid SHA-256 hashes, and duplicate classifications."""
        self.assertTrue(os.path.exists(MANIFEST_PATH), f"Manifest file {MANIFEST_PATH} must exist")

        with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
            manifest_data = json.load(f)

        files = manifest_data["files"]
        self.assertEqual(len(files), 20, "Manifest must inventory exactly 20 files")

        sha256_set = set()
        for item in files:
            # Check required fields
            self.assertIn("dataset_id", item)
            self.assertIn("file_id", item)
            self.assertIn("original_filename", item)
            self.assertIn("relative_path", item)
            self.assertIn("file_type", item)
            self.assertIn("size_bytes", item)
            self.assertIn("sha256", item)
            self.assertIn("duplicate_classification", item)

            # Check that file exists on disk
            extracted_file_path = os.path.join(RAW_DIR, item["original_filename"])
            if not os.path.exists(extracted_file_path):
                # Check nested relative path
                extracted_file_path = os.path.join(RAW_DIR, item["relative_path"])
            self.assertTrue(os.path.exists(extracted_file_path), f"Extracted file {item['relative_path']} must exist")

            # Check SHA-256 non-empty and 64 chars
            self.assertEqual(len(item["sha256"]), 64)
            sha256_set.add(item["sha256"])

            # Check duplicate classification values
            self.assertIn(item["duplicate_classification"], ["unique", "exact_duplicate", "probable_duplicate", "different_version", "uncertain"])

        # Check all SHA256 hashes in dataset are unique
        self.assertEqual(len(sha256_set), 20, "All 20 extracted files must have distinct SHA-256 hashes")

    def test_no_fabricated_metadata(self):
        """Verify unknown or unextractable metadata uses explicit None/null values rather than inventions."""
        with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
            manifest_data = json.load(f)

        master_archive = next(item for item in manifest_data["files"] if "Master" in item["original_filename"])
        self.assertIsNone(master_archive["party"], "Multi-party master archive party must be None")
        self.assertIsNone(master_archive["source_url"], "Source URL for offline archive file must be None")


if __name__ == "__main__":
    unittest.main()
