import pytest
from backend.services.budget import budget_service
from backend.models.budget import BudgetRecord, BudgetScheme, BudgetDepartment, BudgetStage

def test_summarize_by_year():
    records = [
        BudgetRecord(financial_year="2023", amount=100.0),
        BudgetRecord(financial_year="2023", amount=200.0),
        BudgetRecord(financial_year="2024", amount=500.0),
        BudgetRecord(financial_year="2024", amount=None) # Missing amounts should be ignored
    ]
    
    summary = budget_service.summarize_by_year(records)
    
    assert summary["2023"] == 300.0
    assert summary["2024"] == 500.0

def test_summarize_by_department():
    dept_a = BudgetDepartment(name="Health")
    dept_b = BudgetDepartment(name="Education")
    
    scheme_a = BudgetScheme(name="Hospital", department=dept_a)
    scheme_b = BudgetScheme(name="School", department=dept_b)
    
    records = [
        BudgetRecord(scheme=scheme_a, amount=100.0),
        BudgetRecord(scheme=scheme_a, amount=50.0),
        BudgetRecord(scheme=scheme_b, amount=200.0),
        BudgetRecord(scheme=scheme_b, amount=None)
    ]
    
    summary = budget_service.summarize_by_department(records)
    
    assert summary["Health"] == 150.0
    assert summary["Education"] == 200.0

def test_summarize_by_scheme():
    scheme_a = BudgetScheme(name="Hospital")
    scheme_b = BudgetScheme(name="School")
    
    records = [
        BudgetRecord(scheme=scheme_a, amount=100.0),
        BudgetRecord(scheme=scheme_b, amount=200.0),
        BudgetRecord(scheme=scheme_b, amount=None)
    ]
    
    summary = budget_service.summarize_by_scheme(records)
    
    assert summary["Hospital"] == 100.0
    assert summary["School"] == 200.0

def test_compare_stages():
    scheme = BudgetScheme(name="Mid Day Meal")
    records = [
        BudgetRecord(scheme=scheme, financial_year="2023-24", budget_stage=BudgetStage.budget_estimate, amount=100.0),
        BudgetRecord(scheme=scheme, financial_year="2023-24", budget_stage=BudgetStage.actual_expenditure, amount=120.0),
        
        # Unmatched stages should be ignored in comparison
        BudgetRecord(scheme=scheme, financial_year="2024-25", budget_stage=BudgetStage.budget_estimate, amount=150.0)
    ]
    
    comparisons = budget_service.compare_stages(
        records, 
        BudgetStage.budget_estimate, 
        BudgetStage.actual_expenditure
    )
    
    assert "Mid Day Meal (2023-24)" in comparisons
    assert "Mid Day Meal (2024-25)" not in comparisons # Ignored because actuals missing
    
    res = comparisons["Mid Day Meal (2023-24)"]
    assert res["value_a"] == 100.0
    assert res["value_b"] == 120.0
    assert res["absolute_difference"] == 20.0
    assert res["percentage_difference"] == 20.0

def test_compare_stages_invalid():
    with pytest.raises(ValueError):
        budget_service.compare_stages([], BudgetStage.budget_estimate, BudgetStage.budget_estimate)
