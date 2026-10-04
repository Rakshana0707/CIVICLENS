"""
Unit tests for Promise Normalization and Categorization (Phase 3.6).

ALL TEXT BELOW IS SYNTHETIC TEST_FIXTURE DATA written to exercise the pipeline.
It is not taken from, and must not be presented as, any party's manifesto.
"""
import unittest
import os
from backend.nlp.promise_extraction import PromiseRecord, PromiseClassification
from backend.nlp.promise_normalization import (
    PromiseNormalizationService,
    PromiseCategorizer,
    PromiseMetadataExtractor,
    NormalizedPromise,
    PromiseMetadata
)

FIXTURE_ID = "TEST_FIXTURE_manifesto_norm_001"


def make_promise_record(text: str, classification=PromiseClassification.SPECIFIC_PROMISE, **kwargs) -> PromiseRecord:
    return PromiseRecord(
        promise_id=f"{FIXTURE_ID}:p1:001",
        manifesto_id=FIXTURE_ID,
        original_text=text,
        normalized_text=text.strip(),
        page_number=1,
        section="TEST_FIXTURE Section",
        language="English",
        extraction_method="rule_based_v1",
        extraction_confidence=0.8,
        classification=classification,
        is_test_fixture=True,
        **kwargs
    )


class TestPromiseCategorization(unittest.TestCase):

    def setUp(self):
        self.categorizer = PromiseCategorizer()

    def test_education_categorization(self):
        text = "We will construct 50 new schools and provide scholarships to students."
        primary, categories, conf = self.categorizer.categorize(text)
        self.assertEqual(primary, "Education")
        self.assertIn("Education", categories)
        self.assertGreater(conf, 0.0)

    def test_healthcare_categorization(self):
        text = "We will establish a multi-specialty hospital and provide free medical insurance."
        primary, categories, conf = self.categorizer.categorize(text)
        self.assertEqual(primary, "Healthcare")
        self.assertIn("Healthcare", categories)

    def test_agriculture_tamil_categorization(self):
        text = "விவசாயிகளுக்கு பயிர் கடன் தள்ளுபடி செய்யப்படும்."
        primary, categories, conf = self.categorizer.categorize(text)
        self.assertEqual(primary, "Agriculture")
        self.assertIn("Agriculture", categories)

    def test_ambiguous_promise_not_forced(self):
        text = "The committee reviewed various test parameters."
        primary, categories, conf = self.categorizer.categorize(text, is_ambiguous=True)
        self.assertEqual(primary, "Uncategorized")
        self.assertEqual(categories, ["Uncategorized"])
        self.assertEqual(conf, 0.0)

    def test_unmatched_text_returns_uncategorized(self):
        text = "Random unclassifiable gibberish text without matching keywords."
        primary, categories, conf = self.categorizer.categorize(text)
        self.assertEqual(primary, "Uncategorized")
        self.assertEqual(categories, ["Uncategorized"])


class TestMetadataExtraction(unittest.TestCase):

    def setUp(self):
        self.extractor = PromiseMetadataExtractor()

    def test_monetary_target_extraction(self):
        text = "We will provide Rs. 1,000 per month as assistance."
        meta = self.extractor.extract_metadata(text)
        self.assertEqual(meta.monetary_target, "Rs. 1,000")

    def test_monetary_target_crore_extraction(self):
        text = "We will allocate 10000 crore for rural development."
        meta = self.extractor.extract_metadata(text)
        self.assertIsNotNone(meta.monetary_target)
        self.assertIn("10000 crore", meta.monetary_target)

    def test_numeric_target_extraction(self):
        text = "We will achieve 100% literacy across the state."
        meta = self.extractor.extract_metadata(text)
        self.assertEqual(meta.numeric_target, "100%")

    def test_target_population_women(self):
        text = "Financial support of Rs. 1000 for women households."
        meta = self.extractor.extract_metadata(text)
        self.assertEqual(meta.target_population, "Women")

    def test_target_population_farmers_tamil(self):
        text = "விவசாயிகளுக்கு பாசன வசதி ஏற்படுத்தப்படும்."
        meta = self.extractor.extract_metadata(text)
        self.assertEqual(meta.target_population, "Farmers")

    def test_proposed_action_construct(self):
        text = "We will construct a new bridge over the river."
        meta = self.extractor.extract_metadata(text)
        self.assertEqual(meta.proposed_action, "Construct / Establish")

    def test_time_horizon_extraction(self):
        text = "We will complete this project within 3 years."
        meta = self.extractor.extract_metadata(text)
        self.assertEqual(meta.time_horizon, "within 3 years")

    def test_implementation_mechanism(self):
        text = "Funds will be transferred via direct benefit transfer scheme."
        meta = self.extractor.extract_metadata(text)
        self.assertIsNotNone(meta.implementation_mechanism)

    def test_geography_extraction(self):
        text = "New industrial park in Chennai and Madurai."
        meta = self.extractor.extract_metadata(text)
        self.assertIsNotNone(meta.geography)


class TestPromiseNormalizationService(unittest.TestCase):

    def setUp(self):
        self.service = PromiseNormalizationService()

    def test_exact_original_wording_preserved(self):
        original = "  We  will   provide\u00a0Rs. 1000 to   women.  "
        rec = make_promise_record(original)
        norm = self.service.normalize_promise(rec)

        # original_text MUST be preserved EXACTLY as provided
        self.assertEqual(norm.original_text, original)
        # normalized_text applies NFC and whitespace collapsing
        self.assertEqual(norm.normalized_text, "We will provide Rs. 1000 to women.")

    def test_normalization_service_batch(self):
        records = [
            make_promise_record("We will construct 100 new schools."),
            make_promise_record("விவசாயிகளுக்கு கடன் தள்ளுபடி செய்யப்படும்.")
        ]
        results = self.service.normalize_batch(records)
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0].primary_category, "Education")
        self.assertEqual(results[1].primary_category, "Agriculture")

    def test_ambiguous_classification_handling(self):
        rec = make_promise_record(
            "Ambiguous statement without clear commitment.",
            classification=PromiseClassification.AMBIGUOUS
        )
        norm = self.service.normalize_promise(rec)
        self.assertTrue(norm.is_ambiguous)
        self.assertEqual(norm.primary_category, "Uncategorized")
        self.assertEqual(norm.categories, ["Uncategorized"])


if __name__ == "__main__":
    unittest.main()
