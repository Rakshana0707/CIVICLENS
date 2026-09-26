import pytest
from backend.models.budget import BudgetRecord, BudgetStage
from backend.ingestion.validator import BudgetValidator

@pytest.fixture
def base_valid_record():
    return BudgetRecord(
        record_id="test-1",
        department_name="Health",
        scheme_name="Primary Care",
        financial_year="2024-25",
        budget_stage=BudgetStage.budget_estimate,
        amount=100.5,
        source_document_id="doc-1"
    )

def test_valid_record(base_valid_record):
    validator = BudgetValidator()
    valid, invalid, report = validator.validate_batch([base_valid_record])
    assert len(valid) == 1
    assert len(invalid) == 0
    assert report["total_valid"] == 1

def test_missing_required_fields(base_valid_record):
    validator = BudgetValidator()
    
    # Intentionally break the record
    base_valid_record.department_name = ""
    base_valid_record.financial_year = ""
    
    valid, invalid, report = validator.validate_batch([base_valid_record])
    
    assert len(valid) == 0
    assert len(invalid) == 1
    errors = invalid[0]["errors"]
    assert "Missing department_name." in errors
    assert "Missing financial_year." in errors

def test_malformed_financial_year(base_valid_record):
    validator = BudgetValidator()
    
    base_valid_record.financial_year = "2024" # Should be YYYY-YY
    
    valid, invalid, report = validator.validate_batch([base_valid_record])
    assert len(invalid) == 1
    assert any("Malformed financial_year" in err for err in invalid[0]["errors"])

def test_null_amounts_handling(base_valid_record):
    # Null amounts are ALLOWED by default (so missing values aren't treated as 0)
    base_valid_record.amount = None
    
    validator = BudgetValidator()
    valid, invalid, _ = validator.validate_batch([base_valid_record])
    assert len(valid) == 1
    
    # If we configure it to strictly require amounts:
    strict_validator = BudgetValidator(config={
        "require_department": True,
        "allow_null_amounts": False
    })
    valid, invalid, _ = strict_validator.validate_batch([base_valid_record])
    assert len(invalid) == 1
    assert "amount is null and allow_null_amounts is False." in invalid[0]["errors"]

def test_duplicate_detection_within_batch(base_valid_record):
    # Two identical records
    validator = BudgetValidator()
    rec2 = BudgetRecord(
        record_id="test-2",
        department_name="Health",
        scheme_name="Primary Care",
        financial_year="2024-25",
        budget_stage=BudgetStage.budget_estimate,
        amount=200.0,
        source_document_id="doc-1"
    )
    
    valid, invalid, report = validator.validate_batch([base_valid_record, rec2])
    
    assert len(valid) == 1
    assert len(invalid) == 1
    assert "Likely duplicate record in batch." in invalid[0]["errors"]
