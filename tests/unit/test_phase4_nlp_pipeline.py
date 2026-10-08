"""
Unit & Integration Test Suite for Phase 4.4 Multilingual News NLP Pipeline.

IMPORTANT:
All test cases use synthetic local text fixtures tagged with `is_test_fixture=True`.
No real political news articles or live websites are used during unit tests.
"""

import pytest
from backend.nlp.multilingual_pipeline import (
    MultilingualNewsNLPPipeline, TextCleaner, MultilingualLanguageDetector,
    TamilUnicodeNormalizer, SentenceSegmenter, ScriptTokenizer, StopwordProcessor, StemmerLemmatizer
)

SYNTHETIC_TAMIL_TEXT = """TEST FIXTURE — சென்னை மெட்ரோ திட்ட இரண்டாம் கட்ட பணிகளுக்கு நிதி ஒதுக்கீடு செய்யப்பட்டது.
திமுக மற்றும் அதிமுக தலைவர்கள் இந்த அறிக்கையை பரிசீலித்தனர்."""

SYNTHETIC_ENGLISH_TEXT = """TEST FIXTURE — Dr. M.K. Stalin announced Rs 500 Cr for urban infrastructure development.
The opposition leaders discussed the state budget allocation."""

SYNTHETIC_MIXED_TEXT = """TEST FIXTURE — Chennai Metro Phase 2 update: சென்னை மெட்ரோ திட்ட பணிகளுக்கு Rs 500 crore நிதி ஒதுக்கீடு செய்யப்பட்டது."""

SYNTHETIC_MALFORMED_HTML = """<script>var x = 10;</script><p>TEST FIXTURE — <b>சென்னை</b> மெட்ரோ &amp; நிதி</p><style>body {color:red;}</style>"""


class TestPhase4NLPPipeline:
    """Test suite for Phase 4.4 multilingual news NLP pipeline components."""

    def test_text_cleaner_html_and_chrome_stripping(self):
        """Test HTML tag removal, script/style stripping, and entity decoding."""
        cleaned = TextCleaner.clean(SYNTHETIC_MALFORMED_HTML)
        assert "<script>" not in cleaned
        assert "<style>" not in cleaned
        assert "<b>" not in cleaned
        assert "&amp;" not in cleaned
        assert "சென்னை மெட்ரோ & நிதி" in cleaned

    def test_language_detection(self):
        """Test language detection for Tamil (ta), English (en), and Mixed (mixed)."""
        detector = MultilingualLanguageDetector()
        assert detector.detect(SYNTHETIC_TAMIL_TEXT) == "ta"
        assert detector.detect(SYNTHETIC_ENGLISH_TEXT) == "en"
        assert detector.detect(SYNTHETIC_MIXED_TEXT) == "mixed"

    def test_unicode_normalization_and_zero_width_stripping(self):
        """Test NFKC Unicode normalization and zero-width character removal."""
        normalizer = TamilUnicodeNormalizer()
        raw_text = "சென்னை\u200c மெட்\u200dரோ\u200b “திட்டம்” – 2026"
        normalized = normalizer.normalize(raw_text)
        
        assert "\u200c" not in normalized
        assert "\u200d" not in normalized
        assert "\u200b" not in normalized
        assert 'சென்னை மெட்ரோ "திட்டம்" - 2026' in normalized

    def test_abbreviation_aware_sentence_segmentation(self):
        """Test sentence segmentation with English/Tamil abbreviation safeguards."""
        segmenter = SentenceSegmenter()
        text = "Dr. M.K. Stalin presented the budget for Rs 500 Cr. The assembly session concluded."
        sentences = segmenter.segment(text, language="en")
        
        assert len(sentences) == 2
        assert "Dr. M.K. Stalin presented the budget for Rs 500 Cr." in sentences[0]
        assert "The assembly session concluded." in sentences[1]

    def test_headline_sentence_segmentation(self):
        """Test segmentation of headlines without trailing periods."""
        segmenter = SentenceSegmenter()
        headline_body = "TEST FIXTURE — State Budget 2026\nFinance Minister introduced new fiscal policy."
        sentences = segmenter.segment(headline_body)
        
        assert len(sentences) == 2
        assert sentences[0] == "TEST FIXTURE — State Budget 2026"

    def test_script_tokenizer(self):
        """Test script-aware tokenization preserving Tamil compound letters and English words."""
        tokens = ScriptTokenizer.tokenize("சென்னை Metro-Phase 2 நிதி ஒதுக்கீடு")
        assert "சென்னை" in tokens
        assert "Metro-Phase" in tokens
        assert "2" in tokens
        assert "நிதி" in tokens

    def test_stopword_filtering(self):
        """Test Tamil and English stopword filtering."""
        processor = StopwordProcessor()
        
        # Tamil stopword test
        ta_tokens = ["மற்றும்", "சென்னை", "இந்த", "மெட்ரோ"]
        filtered_ta = processor.filter_stopwords(ta_tokens, language="ta")
        assert "மற்றும்" not in filtered_ta
        assert "இந்த" not in filtered_ta
        assert "சென்னை" in filtered_ta
        assert "மெட்ரோ" in filtered_ta

        # English stopword test
        en_tokens = ["the", "budget", "for", "infrastructure"]
        filtered_en = processor.filter_stopwords(en_tokens, language="en")
        assert "the" not in filtered_en
        assert "for" not in filtered_en
        assert "budget" in filtered_en

    def test_tamil_and_english_stemming(self):
        """Test rule-based Tamil inflection suffix stripping and English stemming."""
        stemmer = StemmerLemmatizer()
        
        # Tamil suffix stemming: "-களுக்கு" -> base
        assert stemmer.stem_tamil_word("திட்டங்களுக்கு") == "திட்டங்"
        assert stemmer.stem_tamil_word("அறிக்கையை") == "அறிக்கை"

        # English stemming: "-ing" -> base
        assert stemmer.stem_english_word("allocating") == "allocat"
        assert stemmer.stem_english_word("developments") == "development"

    def test_empty_and_whitespace_content(self):
        """Test pipeline handling of empty, None, and whitespace-only strings."""
        pipeline = MultilingualNewsNLPPipeline()
        
        res_empty = pipeline.process("")
        assert res_empty.original_text == ""
        assert res_empty.cleaned_text == ""
        assert len(res_empty.sentences) == 0
        assert len(res_empty.tokens) == 0

        res_none = pipeline.process(None)
        assert res_none.original_text == ""
        assert res_none.cleaned_text == ""

        res_spaces = pipeline.process("   \n\t  ")
        assert res_spaces.cleaned_text == ""

    def test_malformed_text_handling(self):
        """Test pipeline handling of unclosed HTML tags and corrupted strings."""
        pipeline = MultilingualNewsNLPPipeline()
        malformed = "<div class='content'>TEST FIXTURE — சென்னை <b>மெட்ரோ <p>திட்டம்"
        res = pipeline.process(malformed)
        
        assert res.original_text == malformed
        assert "TEST FIXTURE — சென்னை மெட்ரோ திட்டம்" in res.cleaned_text
        assert len(res.tokens) > 0

    def test_full_nlp_pipeline_execution(self):
        """Test end-to-end NLP processing flow while preserving original text intact."""
        pipeline = MultilingualNewsNLPPipeline()
        payload = pipeline.process(SYNTHETIC_MIXED_TEXT)

        assert payload.original_text == SYNTHETIC_MIXED_TEXT
        assert payload.language == "mixed"
        assert payload.processing_version == "nlp_v1.0"
        assert len(payload.sentences) >= 1
        assert len(payload.tokens) > 5
        assert len(payload.filtered_tokens) <= len(payload.tokens)
        assert payload.stats["tamil_token_count"] > 0
        assert payload.stats["english_token_count"] > 0
        
        payload_dict = payload.to_dict()
        assert payload_dict["processing_version"] == "nlp_v1.0"
        assert "sentences" in payload_dict
