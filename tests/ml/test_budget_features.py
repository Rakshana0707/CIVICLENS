import pytest
import pandas as pd
import numpy as np
from backend.models.budget import BudgetRecord, BudgetStage, BudgetDepartment, BudgetScheme
from backend.ml.budget_features import BudgetFeatureEngineering

def test_budget_features_extraction():
    # Setup mock data
    dept = BudgetDepartment(name="Health")
    scheme_a = BudgetScheme(name="Scheme A", department=dept)
    scheme_b = BudgetScheme(name="Scheme B", department=dept)
    
    # We create multiple BudgetRecords
    records = [
        BudgetRecord(scheme=scheme_a, financial_year="2023-24", budget_stage=BudgetStage.budget_estimate, amount=1000.0),
        BudgetRecord(scheme=scheme_b, financial_year="2023-24", budget_stage=BudgetStage.budget_estimate, amount=3000.0),
        
        # Next year
        BudgetRecord(scheme=scheme_a, financial_year="2024-25", budget_stage=BudgetStage.budget_estimate, amount=1200.0), # +20% YoY
        BudgetRecord(scheme=scheme_a, financial_year="2024-25", budget_stage=BudgetStage.actual_expenditure, amount=1000.0), # Actuals vs BE = -16.6%
        
        # Missing amounts (should be dropped entirely or handled)
        BudgetRecord(scheme=scheme_b, financial_year="2024-25", budget_stage=BudgetStage.budget_estimate, amount=None)
    ]
    
    extractor = BudgetFeatureEngineering()
    extractor.fit(records)
    
    X, y_ids = extractor.transform(records)
    
    assert not X.empty
    assert len(X) == 3 # Scheme A 23-24, Scheme B 23-24, Scheme A 24-25 (Scheme B 24-25 dropped due to None BE)
    
    assert list(X.columns) == ["be_amount", "allocation_share", "yoy_change_be", "actual_vs_be_diff"]
    
    # 2023-24 tests
    idx_23_a = y_ids[(y_ids["scheme"] == "Scheme A") & (y_ids["financial_year"] == "2023-24")].index[0]
    idx_23_b = y_ids[(y_ids["scheme"] == "Scheme B") & (y_ids["financial_year"] == "2023-24")].index[0]
    
    # Raw tests on internal df before scaling (we can just check the raw matrix method for validation)
    raw_df = extractor._create_raw_matrix(records)
    features, ids = extractor._engineer_features(raw_df)
    
    f_23_a = features.loc[idx_23_a]
    f_23_b = features.loc[idx_23_b]
    
    assert f_23_a["be_amount"] == 1000.0
    assert f_23_b["be_amount"] == 3000.0
    assert f_23_a["allocation_share"] == 0.25 # 1000 / 4000
    assert f_23_b["allocation_share"] == 0.75 # 3000 / 4000
    
    assert pd.isna(f_23_a["yoy_change_be"]) # No prior history
    assert pd.isna(f_23_b["yoy_change_be"])
    
    # 2024-25 tests
    idx_24_a = y_ids[(y_ids["scheme"] == "Scheme A") & (y_ids["financial_year"] == "2024-25")].index[0]
    f_24_a = features.loc[idx_24_a]
    
    assert f_24_a["be_amount"] == 1200.0
    assert f_24_a["allocation_share"] == 1.0 # 1200 / 1200 (Scheme B was null)
    
    assert f_24_a["yoy_change_be"] == 0.2 # 1200 vs 1000
    np.testing.assert_almost_equal(f_24_a["actual_vs_be_diff"], -0.16666, decimal=4) # 1000 vs 1200

def test_no_data_leakage():
    # If we fit on year 1 and transform on year 2, the scaling params should remain from year 1
    # This proves we don't leak future stats into scaling.
    dept = BudgetDepartment(name="Test")
    scheme = BudgetScheme(name="Scheme C", department=dept)
    
    train = [BudgetRecord(scheme=scheme, financial_year="2023-24", budget_stage=BudgetStage.budget_estimate, amount=100.0)]
    test = [BudgetRecord(scheme=scheme, financial_year="2024-25", budget_stage=BudgetStage.budget_estimate, amount=500.0)]
    
    ext = BudgetFeatureEngineering().fit(train)
    
    # means_ should be based strictly on `train`
    assert ext.means_["be_amount"] == 100.0
    
    X_test, _ = ext.transform(test)
    
    # Standard scaled value for test point 500 when mean is 100 and std is 1.0 (since only 1 item std replaces 0 with 1.0)
    assert X_test.iloc[0]["be_amount"] == 400.0 
