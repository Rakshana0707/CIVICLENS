import pytest
from sqlalchemy.exc import IntegrityError
from backend.models.budget import BudgetDepartment, BudgetScheme, BudgetRecord, BudgetStage, BudgetSourceDocument
from backend.database.base_class import Base
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(scope="function")
def db_session():
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    yield session
    session.close()
    Base.metadata.drop_all(bind=engine)

def test_department_uniqueness(db_session):
    dept1 = BudgetDepartment(name="Education")
    db_session.add(dept1)
    db_session.commit()
    
    # Try adding same department again
    dept2 = BudgetDepartment(name="Education")
    db_session.add(dept2)
    with pytest.raises(IntegrityError):
        db_session.commit()

def test_scheme_uniqueness_within_department(db_session):
    dept = BudgetDepartment(name="Health")
    db_session.add(dept)
    db_session.commit()
    
    scheme1 = BudgetScheme(department_id=dept.id, name="Primary Care", head_of_account="101")
    db_session.add(scheme1)
    db_session.commit()
    
    # Try adding same scheme to same department with same head_of_account
    scheme2 = BudgetScheme(department_id=dept.id, name="Primary Care", head_of_account="101")
    db_session.add(scheme2)
    with pytest.raises(IntegrityError):
        db_session.commit()

def test_record_uniqueness(db_session):
    dept = BudgetDepartment(name="Transport")
    db_session.add(dept)
    db_session.commit()
    
    scheme = BudgetScheme(department_id=dept.id, name="Roads")
    db_session.add(scheme)
    
    doc = BudgetSourceDocument(manifest_dataset_id="doc1", title="Test Doc")
    db_session.add(doc)
    db_session.commit()
    
    record1 = BudgetRecord(
        scheme_id=scheme.id,
        source_document_id=doc.id,
        financial_year="2024-25",
        budget_stage=BudgetStage.budget_estimate,
        amount=100.0
    )
    db_session.add(record1)
    db_session.commit()
    
    # Attempting to add exact same record (same scheme, year, stage, doc) should fail
    record2 = BudgetRecord(
        scheme_id=scheme.id,
        source_document_id=doc.id,
        financial_year="2024-25",
        budget_stage=BudgetStage.budget_estimate,
        amount=200.0 # Amount doesn't matter for the constraint
    )
    db_session.add(record2)
    with pytest.raises(IntegrityError):
        db_session.commit()
