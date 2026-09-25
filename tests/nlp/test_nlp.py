import unicodedata
from backend.nlp.preprocessing import (
    normalize_whitespace,
    normalize_unicode,
    remove_punctuation,
    normalize_tamil_text
)
from backend.nlp.core import NLPResult, LanguageMetadata

def test_whitespace_normalization():
    assert normalize_whitespace("  Hello   \n\t World  ") == "Hello World"
    assert normalize_whitespace(None) == ""

def test_unicode_normalization():
    composed = "\u0b95\u0bbe" # கா
    decomposed = "\u0b95" + "\u0bbe"
    
    assert normalize_unicode(composed) == normalize_unicode(decomposed)

def test_punctuation_handling():
    assert remove_punctuation("Hello, World! (This is a test.)") == "Hello World This is a test"
    assert remove_punctuation("Tamil!") == "Tamil"

def test_tamil_text_normalization():
    tamil_text = "   தமிழ்   மொழி, மிகத் தொன்மையானது!  "
    normalized = normalize_tamil_text(tamil_text)
    
    assert normalized == "தமிழ் மொழி மிகத் தொன்மையானது"

def test_nlp_result_structure():
    meta = LanguageMetadata(language_code="ta", script="Tamil", confidence=0.99)
    result = NLPResult(
        original_text="தமிழ்",
        normalized_text="தமிழ்",
        language=meta,
        tokens=["த", "மி", "ழ்"],
        embedding=[0.1, 0.2, 0.3]
    )
    
    assert result.language.language_code == "ta"
    assert result.language.confidence == 0.99
    assert len(result.tokens) == 3
    assert result.embedding[1] == 0.2
