import pytest
from unittest.mock import MagicMock
from backend.nlp.similarity import SemanticSchemeSearcher, cosine_similarity

def test_cosine_similarity():
    vec1 = [1.0, 0.0, 0.0]
    vec2 = [1.0, 0.0, 0.0]
    assert cosine_similarity(vec1, vec2) == 1.0
    
    vec3 = [0.0, 1.0, 0.0]
    assert cosine_similarity(vec1, vec3) == 0.0
    
    vec4 = [0.0, 0.0, 0.0]
    assert cosine_similarity(vec1, vec4) == 0.0

def test_semantic_searcher():
    # Mock DB session and Embedder
    mock_db = MagicMock()
    mock_embedder = MagicMock()
    
    # Mock embedder response
    mock_embedder.generate_embedding.return_value = [1.0, 0.0, 0.0]
    
    # Mock HistoricalScheme
    mock_scheme1 = MagicMock()
    mock_scheme1.id = 1
    mock_scheme1.scheme_name = "Target Scheme"
    mock_scheme1.financial_year = "2023-24"
    mock_scheme1.description = "Exact match scheme"
    mock_scheme1.embedding = {"vector": [1.0, 0.0, 0.0]}
    mock_scheme1.department.name = "Health"
    
    mock_scheme2 = MagicMock()
    mock_scheme2.id = 2
    mock_scheme2.scheme_name = "Different Scheme"
    mock_scheme2.financial_year = "2023-24"
    mock_scheme2.description = "Not related"
    mock_scheme2.embedding = {"vector": [0.0, 1.0, 0.0]}
    mock_scheme2.department.name = "Education"
    
    mock_db.query().filter().all.return_value = [] # Mock for sources
    mock_db.query().all.return_value = [mock_scheme1, mock_scheme2]
    
    searcher = SemanticSchemeSearcher(mock_db, mock_embedder)
    results = searcher.search_by_text("Find me health", top_k=5, threshold=0.5)
    
    assert len(results) == 1
    assert results[0]["id"] == 1
    assert results[0]["similarity_score"] == 1.0
    assert "disclaimer" in results[0]
    
    print("All tests passed.")
    
if __name__ == "__main__":
    test_cosine_similarity()
    test_semantic_searcher()
