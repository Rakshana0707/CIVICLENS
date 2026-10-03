import pytest
import os
from backend.nlp.scheme_preprocessing import SchemeTextPreprocessor

def test_scheme_text_preprocessor():
    preprocessor = SchemeTextPreprocessor()
    
    # Test 1: Full data including English and Tamil, plus extraction artifacts
    raw_scheme = {
        "scheme_name": "Muthulakshmi Reddy Maternity Scheme (cid:12)",
        "department_name": "Health Department",
        "description": "Provides maternity assistance to pregnant women. ????????? ??????????? ???? ????.",
        "objectives": "Reduce maternal mortality \x00 rate.",
        "target_beneficiaries": "Pregnant women below poverty line.",
        "sector_category": "Health & Welfare"
    }
    
    processed = preprocessor.process_record(raw_scheme)
    semantic_text = processed["semantic_text"]
    
    # Original text must be preserved
    assert processed["scheme_name"] == "Muthulakshmi Reddy Maternity Scheme (cid:12)"
    
    # Artifacts must be cleaned
    assert "(cid:12)" not in semantic_text
    assert "\x00" not in semantic_text
    
    # Semantic text must contain key domains
    assert "muthulakshmi reddy maternity scheme" in semantic_text
    assert "health & welfare" in semantic_text
    assert "maternity assistance" in semantic_text
    assert "reduce maternal mortality" in semantic_text
    assert "poverty line" in semantic_text
    
    # Bilingual support: Tamil text must be preserved
    assert "????????? ??????????? ???? ????" in semantic_text
    
    # Stopwords should not be removed (e.g. 'to', 'below')
    assert " to " in semantic_text
    assert " below " in semantic_text

    # Test 2: Missing descriptions
    minimal_scheme = {
        "department_name": "Education",
        "description": None,
        "objectives": ""
    }
    
    # Since all primary fields are missing, it should fall back to department name
    min_processed = preprocessor.process_record(minimal_scheme)
    assert min_processed["semantic_text"] == "education"
    
    # Test 3: Save config
    preprocessor.save_config("config/test_nlp_config.json")
    assert os.path.exists("config/test_nlp_config.json")
    os.remove("config/test_nlp_config.json")
    print("All tests passed.")

if __name__ == "__main__":
    test_scheme_text_preprocessor()
