import pytest
from flask import Flask
from backend.api.routes import api_bp
from backend.models.budget import HistoricalScheme, BudgetDepartment, BudgetScheme, SchemeSourceRelationship, BudgetSourceDocument
from backend.database.session import get_db

@pytest.fixture
def app(db_session):
    app = Flask(__name__)
    app.register_blueprint(api_bp)
    
    # Override get_db to use db_session
    def get_db_session():
        yield db_session
        
    # We monkeypatch the get_db in the schemes module
    import backend.api.schemes as schemes_module
    schemes_module.get_db = get_db_session
    
    return app

@pytest.fixture
def client(app):
    return app.test_client()

@pytest.fixture
def setup_data(db_session):
    dept = BudgetDepartment(name="Education")
    db_session.add(dept)
    db_session.commit()
    
    b_scheme = BudgetScheme(department_id=dept.id, name="Test Budget Scheme")
    db_session.add(b_scheme)
    db_session.commit()

    doc = BudgetSourceDocument(manifest_dataset_id="TEST_01", title="Test Doc")
    db_session.add(doc)
    db_session.commit()
    
    hs1 = HistoricalScheme(
        budget_scheme_id=b_scheme.id,
        department_id=dept.id,
        financial_year="2023-24",
        scheme_name="Test Scheme 2023",
        description="A great scheme",
    )
    hs2 = HistoricalScheme(
        budget_scheme_id=b_scheme.id,
        department_id=dept.id,
        financial_year="2022-23",
        scheme_name="Test Scheme 2022",
        description="An old great scheme",
    )
    db_session.add_all([hs1, hs2])
    db_session.commit()

    rel = SchemeSourceRelationship(
        historical_scheme_id=hs1.id,
        source_document_id=doc.id,
        extracted_text="Some raw text"
    )
    db_session.add(rel)
    db_session.commit()
    
    return hs1.id, hs2.id, dept.id

def test_search_valid(client, setup_data):
    response = client.get("/api/schemes/search?name=Test")
    assert response.status_code == 200
    data = response.json["data"]
    assert data["total"] == 2
    assert len(data["items"]) == 2

def test_search_empty(client, setup_data):
    response = client.get("/api/schemes/search?name=NonExistent")
    assert response.status_code == 200
    assert response.json["data"]["total"] == 0
    assert len(response.json["data"]["items"]) == 0

def test_search_invalid_year(client):
    response = client.get("/api/schemes/search?year=2023")
    assert response.status_code == 400
    assert "Invalid year format" in response.json["message"]

def test_get_scheme_valid(client, setup_data):
    hs1_id = setup_data[0]
    response = client.get(f"/api/schemes/{hs1_id}")
    assert response.status_code == 200
    assert response.json["data"]["scheme_name"] == "Test Scheme 2023"

def test_get_scheme_unknown(client):
    response = client.get("/api/schemes/9999")
    assert response.status_code == 404

def test_get_scheme_history(client, setup_data):
    hs1_id = setup_data[0]
    response = client.get(f"/api/schemes/{hs1_id}/history")
    assert response.status_code == 200
    # Should return both versions linked to the same budget scheme
    assert len(response.json["data"]) == 2
    years = [item["financial_year"] for item in response.json["data"]]
    assert "2023-24" in years
    assert "2022-23" in years

def test_get_scheme_sources(client, setup_data):
    hs1_id = setup_data[0]
    response = client.get(f"/api/schemes/{hs1_id}/sources")
    assert response.status_code == 200
    data = response.json["data"]
    assert len(data) == 1
    assert data[0]["document_title"] == "Test Doc"
    assert data[0]["extracted_text_snippet"] == "Some raw text"

def test_search_pagination(client, setup_data):
    response = client.get("/api/schemes/search?limit=1&page=1")
    assert response.status_code == 200
    assert len(response.json["data"]["items"]) == 1
    assert response.json["data"]["total"] == 2

def test_combined_filters(client, setup_data):
    dept_id = setup_data[2]
    response = client.get(f"/api/schemes/search?name=Test&year=2023-24&department_id={dept_id}")
    assert response.status_code == 200
    data = response.json["data"]
    assert data["total"] == 1
    assert data["items"][0]["financial_year"] == "2023-24"
