import os
import pytest
import pandas as pd
from unittest.mock import patch
from backend.database.session import SessionLocal
from backend.models.budget import BudgetRecord, BudgetStage, BudgetDepartment, BudgetScheme, BudgetSourceDocument
from backend.ingestion.budget_ingestor import BudgetIngestor
from backend.api.app import create_app

@pytest.fixture(scope="function")
def e2e_db():
    db = SessionLocal()
    # Cleanup before test
    db.query(BudgetRecord).delete()
    db.query(BudgetSourceDocument).delete()
    db.query(BudgetScheme).delete()
    db.query(BudgetDepartment).delete()
    db.commit()
    
    yield db
    
    # Teardown
    db.query(BudgetRecord).delete()
    db.query(BudgetSourceDocument).delete()
    db.query(BudgetScheme).delete()
    db.query(BudgetDepartment).delete()
    db.commit()
    db.close()

@pytest.fixture
def e2e_client():
    app = create_app()
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

def test_e2e_budget_pipeline(e2e_db, e2e_client, tmp_path):
    """
    Simulates the entire pipeline: 
    1. CSV file on disk.
    2. Manifest JSON.
    3. Ingestion into DB.
    4. Retrieving through APIs.
    5. ML clustering and traceability.
    """
    
    # 1. Create a dummy CSV with messy data to test cleaning & ingestion
    raw_data = pd.DataFrame([
        # Row 1: Valid
        {"department_name": " Health ", "scheme_name": "Primary Care", "financial_year": "2023-2024", "budget_estimate": 100.5},
        # Row 2: Valid
        {"department_name": "Health", "scheme_name": "Hospital Infra", "financial_year": "2023-2024", "budget_estimate": 500.0},
        # Row 3: Duplicate of Row 2 to test duplicate handling (should be dropped during validation/cleaning)
        {"department_name": "Health", "scheme_name": "Hospital Infra", "financial_year": "2023-2024", "budget_estimate": 500.0},
        # Row 4: Missing financial year (should be dropped/error out)
        {"department_name": "Health", "scheme_name": "Maternity", "financial_year": None, "budget_estimate": 200.0},
    ])
    
    csv_path = tmp_path / "test_data.csv"
    raw_data.to_csv(csv_path, index=False)
    
    # 2. Create a dummy manifest
    import json
    manifest_data = {
        "datasets": [
            {
                "dataset_id": "E2E_DOC_01",
                "dataset_title": "E2E Test Budget Document",
                "collection_status": "verified",
                "file_format": "csv",
                "original_filename": "test_data.csv",
                "published_date": "2024-01-01",
                "financial_year": "2023-24"
            }
        ]
    }
    manifest_path = tmp_path / "manifest.json"
    with open(manifest_path, 'w') as f:
        json.dump(manifest_data, f)
        
    # 3. Ingestion
    ingestor = BudgetIngestor(e2e_db, str(manifest_path), str(tmp_path))
    ingestor.ingest()
    
    # Verify DB state
    docs = e2e_db.query(BudgetSourceDocument).all()
    assert len(docs) == 1
    
    records = e2e_db.query(BudgetRecord).all()
    
    # Expected valid records mapped to budget stages:
    # Row 1 -> 1 record (due to naive map logic choosing one stage)
    # Row 2 -> 1 record (BE)
    # Row 3 -> Dropped (duplicate)
    # Row 4 -> 1 record (Uses manifest financial year since row year is None)
    # Total = 3 records
    assert len(records) == 3, f"Expected 3 records, got {len(records)}"
    
    # 4. API Endpoints testing
    # Get Departments
    res = e2e_client.get('/api/budget/departments')
    assert res.status_code == 200
    depts = res.get_json()['data']
    assert len(depts) == 1
    assert depts[0]['name'] == "Health" # Whitespace cleaned
    dept_id = depts[0]['id']
    
    # Get Schemes
    res = e2e_client.get(f'/api/budget/schemes?department_id={dept_id}')
    schemes = res.get_json()['data']
    assert len(schemes) == 3
    
    # 5. ML Clustering and Traceability
    # Since we need at least 2 schemes with BE to run ML (Health -> Primary Care, Health -> Hospital Infra)
    records_debug = e2e_db.query(BudgetRecord).all()
    for r in records_debug:
        print(f"DEBUG: {r.scheme.name} - {r.budget_stage} - {r.amount}")
        
    res = e2e_client.get('/api/ml/budget/clustering?budget_stage=budget_estimate&algorithm=kmeans&k=2')
    if res.status_code != 200:
        print(res.get_json())
    assert res.status_code == 200
    ml_data = res.get_json()['data']
    
    assert ml_data["algorithm"] == "kmeans"
    assert len(ml_data["data_points"]) == 3
    
    # Verify Traceability
    pt1 = ml_data["data_points"][0]
    assert "source_documents" in pt1
    assert len(pt1["source_documents"]) > 0
    assert str(docs[0].id) in pt1["source_documents"]

def test_e2e_empty_database_handling(e2e_client):
    """
    Test how the system behaves when no data is ingested.
    """
    # 1. API should return 400 for ML if no data
    res = e2e_client.get('/api/ml/budget/clustering?budget_stage=budget_estimate&algorithm=kmeans&k=2')
    assert res.status_code == 400
    assert "Insufficient records" in res.get_json()['message']
    
    # 2. Analytics should return empty lists gracefully, not fabricate data
    res = e2e_client.get('/api/budget/records')
    assert res.status_code == 200
    assert len(res.get_json()['data']['records']) == 0
    
def test_e2e_invalid_file_handling(e2e_db, tmp_path):
    """
    Test how the ingestor handles missing files and unsupported formats.
    """
    import json
    manifest_data = {
        "datasets": [
            {
                "dataset_id": "ERR_01",
                "collection_status": "verified",
                "file_format": "csv",
                "original_filename": "does_not_exist.csv"
            },
            {
                "dataset_id": "ERR_02",
                "collection_status": "verified",
                "file_format": "xml",
                "original_filename": "test.xml"
            }
        ]
    }
    manifest_path = tmp_path / "manifest.json"
    with open(manifest_path, 'w') as f:
        json.dump(manifest_data, f)
        
    (tmp_path / "test.xml").write_text("<test></test>")
    
    ingestor = BudgetIngestor(e2e_db, str(manifest_path), str(tmp_path))
    ingestor.ingest()
    
    # Neither should produce DB records
    assert e2e_db.query(BudgetRecord).count() == 0
