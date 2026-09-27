import pytest
from backend.repositories.budget import budget_repo
from backend.models.budget import BudgetDepartment, BudgetScheme, BudgetRecord, BudgetStage, BudgetSourceDocument

@pytest.fixture
def seeded_db(db_session):
    dept1 = BudgetDepartment(name="Education")
    dept2 = BudgetDepartment(name="Health")
    db_session.add_all([dept1, dept2])
    db_session.commit()
    
    scheme1 = BudgetScheme(department_id=dept1.id, name="Primary Schools")
    scheme2 = BudgetScheme(department_id=dept2.id, name="Hospitals")
    db_session.add_all([scheme1, scheme2])
    db_session.commit()
    
    doc = BudgetSourceDocument(manifest_dataset_id="test_doc", title="Test")
    db_session.add(doc)
    db_session.commit()
    
    record1 = BudgetRecord(
        scheme_id=scheme1.id,
        source_document_id=doc.id,
        financial_year="2023-24",
        budget_stage=BudgetStage.budget_estimate,
        amount=100.0
    )
    record2 = BudgetRecord(
        scheme_id=scheme1.id,
        source_document_id=doc.id,
        financial_year="2024-25",
        budget_stage=BudgetStage.budget_estimate,
        amount=150.0
    )
    record3 = BudgetRecord(
        scheme_id=scheme2.id,
        source_document_id=doc.id,
        financial_year="2024-25",
        budget_stage=BudgetStage.revised_estimate,
        amount=500.0
    )
    db_session.add_all([record1, record2, record3])
    db_session.commit()
    
    return {
        "dept1": dept1,
        "dept2": dept2,
        "scheme1": scheme1,
        "scheme2": scheme2,
        "doc": doc
    }

def test_get_records_pagination(seeded_db, db_session):
    records, total = budget_repo.get_records(db_session, skip=0, limit=2)
    assert total == 3
    assert len(records) == 2
    
    records_page2, total2 = budget_repo.get_records(db_session, skip=2, limit=2)
    assert total2 == 3
    assert len(records_page2) == 1

def test_get_records_filters(seeded_db, db_session):
    # Filter by financial year
    records, total = budget_repo.get_records(db_session, financial_year="2024-25")
    assert total == 2
    
    # Filter by department name (ilike)
    records, total = budget_repo.get_records(db_session, department_name="edu")
    assert total == 2
    assert records[0].scheme.department.name == "Education"
    
    # Filter by department id
    records, total = budget_repo.get_records(db_session, department_id=seeded_db["dept2"].id)
    assert total == 1
    assert records[0].amount == 500.0
    
    # Filter by scheme id
    records, total = budget_repo.get_records(db_session, scheme_id=seeded_db["scheme1"].id)
    assert total == 2
    
    # Filter by budget stage
    records, total = budget_repo.get_records(db_session, budget_stage=BudgetStage.revised_estimate)
    assert total == 1
    assert records[0].scheme.name == "Hospitals"

def test_get_metadata_queries(seeded_db, db_session):
    years = budget_repo.get_available_years(db_session)
    assert "2024-25" in years
    assert "2023-24" in years
    assert len(years) == 2
    
    depts = budget_repo.get_departments(db_session, search_term="health")
    assert len(depts) == 1
    assert depts[0].name == "Health"
    
    schemes = budget_repo.get_schemes(db_session, department_id=seeded_db["dept1"].id)
    assert len(schemes) == 1
    assert schemes[0].name == "Primary Schools"
    
def test_get_records_invalid_filter(seeded_db, db_session):
    # Should safely return empty list without crashing
    records, total = budget_repo.get_records(db_session, financial_year="3000-01")
    assert total == 0
    assert len(records) == 0
