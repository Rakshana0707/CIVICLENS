import pytest
from flask import Flask
from unittest.mock import MagicMock
from backend.api.routes import api_bp

@pytest.fixture
def app():
    app = Flask(__name__)
    app.register_blueprint(api_bp)
    
    # Mock DB session in the routes
    import backend.api.schemes as schemes_module
    mock_db = MagicMock()
    def get_test_db():
        yield mock_db
    schemes_module.get_db = get_test_db
    return app

@pytest.fixture
def client(app):
    return app.test_client()

def test_semantic_search_api_missing_query(client):
    response = client.get("/api/schemes/semantic_search")
    assert response.status_code == 400
    assert "Query parameter is required" in response.json["message"]

def test_semantic_search_api_valid(client, monkeypatch):
    # Mock SemanticSchemeSearcher
    from backend.nlp.similarity import SemanticSchemeSearcher
    mock_searcher = MagicMock(spec=SemanticSchemeSearcher)
    mock_searcher.search_by_text.return_value = {
        "query": "education",
        "items": [{"id": 1, "scheme_name": "Ed Scheme", "similarity_score": 0.85, "disclaimer": "overlap"}],
        "total": 1,
        "page": 1,
        "limit": 5
    }
    
    monkeypatch.setattr("backend.nlp.similarity.SemanticSchemeSearcher", lambda db: mock_searcher)
    
    response = client.get("/api/schemes/semantic_search?query=education&top_k=5")
    assert response.status_code == 200
    
    data = response.json["data"]
    assert data["query"] == "education"
    assert data["total"] == 1
    assert len(data["items"]) == 1
    assert data["items"][0]["similarity_score"] == 0.85
    assert "disclaimer" in data["items"][0]

def test_similar_schemes_api_valid(client, monkeypatch):
    # Mock SemanticSchemeSearcher
    from backend.nlp.similarity import SemanticSchemeSearcher
    mock_searcher = MagicMock(spec=SemanticSchemeSearcher)
    mock_searcher.search_by_scheme_id.return_value = {
        "query_scheme": {"id": 1, "scheme_name": "Source Scheme"},
        "items": [{"id": 2, "scheme_name": "Similar Scheme", "similarity_score": 0.9, "disclaimer": "overlap"}],
        "total": 1,
        "page": 1,
        "limit": 5
    }
    
    monkeypatch.setattr("backend.nlp.similarity.SemanticSchemeSearcher", lambda db: mock_searcher)
    
    response = client.get("/api/schemes/1/similar?top_k=5&threshold=0.5")
    assert response.status_code == 200
    
    data = response.json["data"]
    assert data["query_scheme"]["scheme_name"] == "Source Scheme"
    assert len(data["items"]) == 1
    
print("Creating tests file.")
