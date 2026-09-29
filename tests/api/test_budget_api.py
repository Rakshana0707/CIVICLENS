import pytest
from backend.models.budget import BudgetDepartment, BudgetScheme, BudgetRecord, BudgetStage, BudgetSourceDocument
from backend.database.session import SessionLocal

@pytest.fixture(autouse=True)
def setup_teardown_db():
    db = SessionLocal()
    # Seed data
    dept = BudgetDepartment(name="Education")
    db.add(dept)
    db.commit()
    
    scheme = BudgetScheme(name="Scholarships", department_id=dept.id)
    scheme2 = BudgetScheme(name="Infrastructure", department_id=dept.id)
    db.add(scheme)
    db.add(scheme2)
    db.commit()
    
    doc = BudgetSourceDocument(manifest_dataset_id="doc1", title="test")
    db.add(doc)
    db.commit()
    
    record = BudgetRecord(
        scheme_id=scheme.id,
        source_document_id=doc.id,
        financial_year="2023-24",
        budget_stage=BudgetStage.budget_estimate,
        amount=500.0,
        currency_unit="INR_Absolute"
    )
    record2 = BudgetRecord(
        scheme_id=scheme2.id,
        source_document_id=doc.id,
        financial_year="2023-24",
        budget_stage=BudgetStage.budget_estimate,
        amount=1500.0,
        currency_unit="INR_Absolute"
    )
    scheme3 = BudgetScheme(name="Health", department_id=dept.id)
    db.add(scheme3)
    db.commit()
    record3 = BudgetRecord(
        scheme_id=scheme3.id,
        source_document_id=doc.id,
        financial_year="2023-24",
        budget_stage=BudgetStage.budget_estimate,
        amount=2000.0,
        currency_unit="INR_Absolute"
    )
    db.add(record)
    db.add(record2)
    db.add(record3)
    db.commit()
    
    yield
    
    # Teardown
    db.delete(record)
    db.delete(record2)
    db.delete(record3)
    db.delete(doc)
    db.delete(scheme)
    db.delete(scheme2)
    db.delete(scheme3)
    db.delete(dept)
    db.commit()
    db.close()
    db.close()

def test_get_years(api_client):
    res = api_client.get('/api/budget/years')
    assert res.status_code == 200
    data = res.get_json()['data']
    assert "2023-24" in data

def test_get_departments(api_client):
    res = api_client.get('/api/budget/departments')
    assert res.status_code == 200
    data = res.get_json()['data']
    assert any(d['name'] == "Education" for d in data)

def test_get_schemes(api_client):
    res = api_client.get('/api/budget/schemes?search=Scholar')
    assert res.status_code == 200
    data = res.get_json()['data']
    assert any(s['name'] == "Scholarships" for s in data)

def test_get_records(api_client):
    res = api_client.get('/api/budget/records?financial_year=2023-24')
    assert res.status_code == 200
    data = res.get_json()['data']
    assert data['total_count'] >= 1
    assert data['records'][0]['department_name'] == "Education"
    assert data['records'][0]['amount'] in [500.0, 1500.0, 2000.0]

def test_get_records_invalid_stage(api_client):
    res = api_client.get('/api/budget/records?budget_stage=fake_stage')
    assert res.status_code == 400
    assert "Invalid budget_stage" in res.get_json()['message']

def test_summarize_year(api_client):
    res = api_client.get('/api/budget/summarize/year?budget_stage=budget_estimate')
    assert res.status_code == 200
    data = res.get_json()['data']
    assert data["2023-24"] >= 500.0

def test_summarize_year_missing_stage(api_client):
    res = api_client.get('/api/budget/summarize/year')
    assert res.status_code == 400

def test_summarize_department(api_client):
    res = api_client.get('/api/budget/summarize/department?budget_stage=budget_estimate&financial_year=2023-24')
    assert res.status_code == 200
    data = res.get_json()['data']
    assert data["Education"] >= 500.0

def test_summarize_scheme(api_client):
    res = api_client.get('/api/budget/summarize/scheme?budget_stage=budget_estimate&financial_year=2023-24')
    assert res.status_code == 200
    data = res.get_json()['data']
    assert data["Scholarships"] >= 500.0

def test_trend_analysis(api_client):
    res = api_client.get('/api/budget/analysis/trend?budget_stage=budget_estimate')
    assert res.status_code == 200
    data = res.get_json()['data']
    assert "2023-24" in data
    assert data["2023-24"]["total"] >= 0
    assert data["2023-24"]["percentage_change"] is None or isinstance(data["2023-24"]["percentage_change"], float)

def test_scheme_trends(api_client):
    res = api_client.get('/api/budget/analysis/scheme-trends?budget_stage=budget_estimate')
    assert res.status_code == 200
    data = res.get_json()['data']
    assert "Scholarships" in data

def test_ml_clustering_kmeans(api_client):
    res = api_client.get('/api/ml/budget/clustering?budget_stage=budget_estimate&algorithm=kmeans&k=2')
    if res.status_code != 200:
        print(res.get_json())
    assert res.status_code == 200
    data = res.get_json()['data']
    assert data["algorithm"] == "kmeans"
    assert "explained_variance" in data
    assert "summaries" in data
    assert len(data["data_points"]) > 0
    assert "PC1" in data["data_points"][0]
    assert "cluster" in data["data_points"][0]

def test_ml_clustering_dbscan(api_client):
    res = api_client.get('/api/ml/budget/clustering?budget_stage=budget_estimate&algorithm=dbscan&eps=0.5&min_samples=2')
    if res.status_code != 200:
        print(res.get_json())
    assert res.status_code == 200
    data = res.get_json()['data']
    assert data["algorithm"] == "dbscan"
    assert "summaries" in data
    assert len(data["data_points"]) > 0
    assert "source_documents" in data["data_points"][0]

def test_ml_anomaly_detection(api_client):
    res = api_client.get('/api/ml/budget/anomaly?budget_stage=budget_estimate&contamination=0.1')
    if res.status_code != 200:
        print(res.get_json())
    assert res.status_code == 200
    data = res.get_json()['data']
    assert data["algorithm"] == "isolation_forest"
    assert "flagged_summary" in data
    assert "metadata" in data
    assert len(data["data_points"]) > 0
    assert "is_anomaly" in data["data_points"][0]
    assert "anomaly_score" in data["data_points"][0]
    assert "source_documents" in data["data_points"][0]
