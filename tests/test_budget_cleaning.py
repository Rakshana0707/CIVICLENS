import pytest
import os
import json
from backend.models.budget import BudgetRecord, BudgetStage
from backend.ingestion.cleaner import BudgetCleaner

@pytest.fixture
def mock_mappings_file(tmp_path):
    mappings = {
        "departments": {
            "H & FW": "Health and Family Welfare"
        },
        "schemes": {
            "MDM": "Mid Day Meal Scheme"
        }
    }
    file_path = tmp_path / "test_mappings.json"
    with open(file_path, 'w') as f:
        json.dump(mappings, f)
    return str(file_path)

@pytest.fixture
def dirty_record():
    return BudgetRecord(
        record_id="test-clean-1",
        department_name="  H & FW  ", # Needs mapping and strip
        scheme_name="  MDM  ", # Needs mapping and strip
        financial_year="2024/25", # Needs normalization to 2024-25
        budget_stage=BudgetStage.budget_estimate,
        amount=50.0,
        original_category="Raw string here",
        source_document_id="doc-1"
    )

def test_cleaning_normalizations(mock_mappings_file, dirty_record):
    cleaner = BudgetCleaner(mappings_file=mock_mappings_file)
    cleaned, unresolved, report = cleaner.clean_batch([dirty_record])
    
    assert len(cleaned) == 1
    assert len(unresolved) == 0
    
    rec = cleaned[0]
    assert rec.department_name == "Health and Family Welfare"
    assert rec.scheme_name == "Mid Day Meal Scheme"
    assert rec.financial_year == "2024-25"
    
    # Check that original raw data was preserved
    assert rec.original_category == "Raw string here"
    
    # Check report
    assert report["total_processed"] == 1
    assert report["total_cleaned"] == 1
    assert len(report["transformations"]) == 1
    
    changes = report["transformations"][0]["changes"]
    assert any("Normalized whitespace" in c for c in changes)
    assert any("Mapped department" in c for c in changes)
    assert any("Standardized FY" in c for c in changes)

def test_missing_mappings_graceful_fallback(dirty_record):
    # No mapping file
    cleaner = BudgetCleaner(mappings_file="nonexistent.json")
    cleaned, _, _ = cleaner.clean_batch([dirty_record])
    
    rec = cleaned[0]
    # It should still strip whitespace and fix FY, even if mapping fails
    assert rec.department_name == "H & FW"
    assert rec.scheme_name == "MDM"
    assert rec.financial_year == "2024-25"

def test_unresolved_records():
    cleaner = BudgetCleaner()
    # A record that gets its department stripped to empty string
    empty_dept_record = BudgetRecord(
        record_id="test-clean-2",
        department_name="   ", 
        scheme_name="Valid Scheme",
        financial_year="2024-25",
        budget_stage=BudgetStage.budget_estimate,
        amount=10.0,
        source_document_id="doc-1"
    )
    
    cleaned, unresolved, report = cleaner.clean_batch([empty_dept_record])
    assert len(cleaned) == 0
    assert len(unresolved) == 1
    assert unresolved[0]["reason"] == "Missing or emptied department/scheme after cleaning"
