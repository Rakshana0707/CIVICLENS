import pytest
import pandas as pd
import numpy as np
from backend.models.budget import BudgetRecord, BudgetStage, BudgetDepartment, BudgetScheme
from backend.ml.budget_anomaly import BudgetIsolationForest

def _generate_mock_records(n: int) -> list:
    dept = BudgetDepartment(name="Test Dept")
    records = []
    # Create mostly normal patterns and 1 massive outlier
    for i in range(n):
        scheme = BudgetScheme(name=f"Scheme {i}", department=dept)
        if i == n - 1:
            amount = 999999.0 # Extreme outlier
        else:
            amount = 100.0 + (i * 2.0) # Normal tight cluster
            
        records.append(
            BudgetRecord(
                scheme=scheme, 
                financial_year="2023-24", 
                budget_stage=BudgetStage.budget_estimate, 
                amount=amount
            )
        )
    return records

def test_anomaly_insufficient_data():
    model = BudgetIsolationForest()
    records = _generate_mock_records(1)
    with pytest.raises(ValueError, match="Insufficient data"):
        model.fit_predict(records)

def test_anomaly_detection_and_scoring():
    # 20 records: 19 normal, 1 outlier
    records = _generate_mock_records(20)
    
    # We specify contamination to ensure it forces out the outlier
    model = BudgetIsolationForest(contamination=0.1, random_state=42)
    df = model.fit_predict(records)
    
    assert "is_anomaly" in df.columns
    assert "anomaly_score" in df.columns
    
    # Since it's sorted by anomaly_score ascending, the top row should be the most anomalous
    assert bool(df.iloc[0]["is_anomaly"]) is True
    
    # Verify the most anomalous record is indeed Scheme 19 (the 999999.0 one)
    assert df.iloc[0]["scheme"] == "Scheme 19"
    assert df.iloc[0]["be_amount"] == 999999.0
    
    # The anomaly score for the outlier should be lower than for a normal point
    # Find a normal point
    normal_score = df[df["scheme"] == "Scheme 0"].iloc[0]["anomaly_score"]
    assert df.iloc[0]["anomaly_score"] < normal_score

def test_anomaly_flagged_records():
    records = _generate_mock_records(20)
    model = BudgetIsolationForest(contamination=0.05, random_state=42)
    df = model.fit_predict(records)
    
    flagged = model.get_flagged_records(df)
    
    assert isinstance(flagged, list)
    assert len(flagged) == 1 # Since contamination is 0.05 of 20 = 1 record
    
    anom = flagged[0]
    assert anom["scheme"] == "Scheme 19"
    assert anom["is_anomaly"] == True

def test_anomaly_reproducibility():
    records = _generate_mock_records(15)
    
    model1 = BudgetIsolationForest(contamination=0.1, random_state=42)
    df1 = model1.fit_predict(records)
    
    model2 = BudgetIsolationForest(contamination=0.1, random_state=42)
    df2 = model2.fit_predict(records)
    
    # Should be perfectly deterministic with the same random seed
    assert (df1["anomaly_score"].values == df2["anomaly_score"].values).all()
    assert (df1["is_anomaly"].values == df2["is_anomaly"].values).all()
