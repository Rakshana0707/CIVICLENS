import pytest
from unittest.mock import MagicMock
from backend.ml.theme_analysis import ThemeAnalyzer

def test_theme_analyzer_keywords():
    mock_db = MagicMock()
    analyzer = ThemeAnalyzer(mock_db)
    
    texts = [
        "Provides agriculture funding for rural farmers",
        "Assistance for agriculture machinery in rural areas",
        "Rural farmers get agriculture subsidies"
    ]
    
    keywords = analyzer.extract_keywords_tfidf(texts, top_n=3)
    assert len(keywords) == 3
    assert "agriculture" in keywords
    assert "rural" in keywords

def test_analyze_themes():
    mock_db = MagicMock()
    
    # Mock schemas
    mock_scheme1 = MagicMock()
    mock_scheme1.id = 1
    mock_scheme1.scheme_name = "Agri 1"
    mock_scheme1.embedding = {"vector": [1.0, 0.0]}
    
    mock_scheme2 = MagicMock()
    mock_scheme2.id = 2
    mock_scheme2.scheme_name = "Agri 2"
    mock_scheme2.embedding = {"vector": [0.9, 0.1]}
    
    mock_scheme3 = MagicMock()
    mock_scheme3.id = 3
    mock_scheme3.scheme_name = "Edu 1"
    mock_scheme3.embedding = {"vector": [0.0, 1.0]}
    
    mock_scheme4 = MagicMock()
    mock_scheme4.id = 4
    mock_scheme4.scheme_name = "Edu 2"
    mock_scheme4.embedding = {"vector": [0.1, 0.9]}
    
    mock_db.query().all.return_value = [mock_scheme1, mock_scheme2, mock_scheme3, mock_scheme4]
    
    analyzer = ThemeAnalyzer(mock_db)
    # Mock text generation so tfidf doesn't crash on empty
    analyzer.preprocessor.generate_semantic_text = MagicMock(return_value="sample text agriculture education")
    
    results = analyzer.analyze_themes(n_clusters=2)
    assert results["n_clusters"] == 2
    assert results["total_schemes_analyzed"] == 4
    assert len(results["themes"]) == 2
    
    print("Tests passed.")
    
if __name__ == "__main__":
    test_theme_analyzer_keywords()
    test_analyze_themes()
