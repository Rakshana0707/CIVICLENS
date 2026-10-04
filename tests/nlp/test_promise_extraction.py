"""
Tests for the promise extraction pipeline.

ALL TEXT BELOW IS SYNTHETIC TEST_FIXTURE DATA written to exercise the pipeline.
It is not taken from, and must not be presented as, any party's manifesto.
"""
import unittest

from backend.nlp.promise_extraction import (
    PromiseClassification as C,
    PromiseExtractor,
    classify,
    detect_language,
    split_units,
)

FIXTURE_ID = "TEST_FIXTURE_manifesto_001"


def seg(text, **kw):
    base = {
        "manifesto_id": FIXTURE_ID,
        "page_number": 3,
        "section": "TEST_FIXTURE section",
        "original_text": text,
        "language": "Unknown",
        "extraction_method": "pdfplumber",
        "OCR_used": False,
        "extraction_confidence": 1.0,
    }
    base.update(kw)
    return base


class TestClassification(unittest.TestCase):
    def test_specific_english(self):
        self.assertEqual(classify("We will provide Rs. 1000 per month to every test household.")[0], C.SPECIFIC_PROMISE)

    def test_specific_tamil(self):
        # synthetic: "Rs. 1000 will be provided to test families."
        self.assertEqual(classify("சோதனை குடும்பங்களுக்கு ரூ.1000 வழங்கப்படும்.")[0], C.SPECIFIC_PROMISE)

    def test_general_policy(self):
        self.assertEqual(classify("We will strengthen the fictional test department.")[0], C.GENERAL_POLICY)

    def test_vision(self):
        self.assertEqual(classify("Our vision is a prosperous and fictional test region for everyone.")[0], C.VISION)

    def test_slogan(self):
        self.assertEqual(classify("Test Fixture Forever!")[0], C.SLOGAN)

    def test_ambiguous(self):
        self.assertEqual(classify("The fictional test committee discussed several matters in detail.")[0], C.AMBIGUOUS)


class TestSplittingAndTraceability(unittest.TestCase):
    def test_sentences_split_and_exact_substrings(self):
        text = "We will build 10 test bridges.  We will improve test roads. Test Fixture Forever!"
        for s, e in split_units(text):
            self.assertEqual(text[s:e], text[s:e].strip())
        self.assertEqual(len(split_units(text)), 3)

    def test_list_markers_excluded(self):
        text = "Pledges:\n1. We will build 5 test schools.\n2. We will hire 100 test teachers."
        units = [text[s:e] for s, e in split_units(text)]
        self.assertIn("We will build 5 test schools.", units)
        self.assertIn("We will hire 100 test teachers.", units)

    def test_original_text_preserved_exactly(self):
        text = "We  will   provide\u00a0free test laptops to 50 students."
        rec = PromiseExtractor().extract([seg(text)])[0]
        self.assertEqual(rec.original_text, text)  # untouched, including odd spacing
        self.assertEqual(rec.normalized_text, "We will provide free test laptops to 50 students.")
        self.assertNotEqual(rec.original_text, rec.normalized_text)

    def test_record_fields_and_offsets(self):
        text = "Intro text here. We will open 3 test clinics."
        recs = PromiseExtractor().extract([seg(text)])
        r = recs[1]
        self.assertEqual(text[r.char_start:r.char_end], r.original_text)
        self.assertEqual(r.manifesto_id, FIXTURE_ID)
        self.assertEqual(r.page_number, 3)
        self.assertEqual(r.section, "TEST_FIXTURE section")
        self.assertEqual(r.extraction_method, "rule_based_v1")
        self.assertTrue(r.is_test_fixture)
        self.assertTrue(r.promise_id.startswith(FIXTURE_ID))

    def test_ids_deterministic_and_unique(self):
        segs = [seg("We will build 1 test bridge. We will build 2 test bridges.")]
        a = [r.promise_id for r in PromiseExtractor().extract(segs)]
        b = [r.promise_id for r in PromiseExtractor().extract(segs)]
        self.assertEqual(a, b)
        self.assertEqual(len(set(a)), len(a))

    def test_ocr_lowers_confidence(self):
        text = "We will provide 5 test buses."
        clean = PromiseExtractor().extract([seg(text)])[0]
        ocr = PromiseExtractor().extract([seg(text, OCR_used=True, extraction_confidence=0.5)])[0]
        self.assertLess(ocr.extraction_confidence, clean.extraction_confidence)
        self.assertIn("source_ocr", ocr.classification_signals)

    def test_empty_segment(self):
        self.assertEqual(PromiseExtractor().extract([seg("   ")]), [])


class TestLanguage(unittest.TestCase):
    def test_detect(self):
        self.assertEqual(detect_language("We will build test roads."), "English")
        self.assertEqual(detect_language("சோதனை சாலைகள் அமைக்கப்படும்."), "Tamil")
        self.assertEqual(detect_language("Free test laptops இலவச மடிக்கணினி"), "Mixed")


if __name__ == "__main__":
    unittest.main()
