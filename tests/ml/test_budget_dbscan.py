import pytest
import pandas as pd
import numpy as np
from backend.models.budget import BudgetRecord, BudgetStage, BudgetDepartment, BudgetScheme
from backend.ml.budget_dbscan import BudgetDBSCANClustering

def _generate_mock_records(n: int) -> list:
    dept = BudgetDepartment(name="Test Dept")
    records = []
    # Create distinct patterns for clustering
    for i in range(n):
        scheme = BudgetScheme(name=f"Scheme {i}", department=dept)
        # Create a dense group and one outlier
        if i == 0:
            amount = 99999.0 # Outlier
        else:
            amount = 100.0 + (i * 0.1) # Dense cluster
            
        records.append(
            BudgetRecord(
                scheme=scheme, 
                financial_year="2023-24", 
                budget_stage=BudgetStage.budget_estimate, 
                amount=amount
            )
        )
    return records

def test_dbscan_insufficient_data():
    clustering = BudgetDBSCANClustering()
    records = _generate_mock_records(1)
    with pytest.raises(ValueError, match="Insufficient data"):
        clustering.prepare_data(records)

def test_dbscan_clustering_and_noise():
    # 1 outlier + 10 dense points = 11 records
    records = _generate_mock_records(11)
    
    # eps=1.0, min_samples=3
    clustering = BudgetDBSCANClustering(eps=1.0, min_samples=3)
    df = clustering.fit_predict(records)
    
    assert "cluster" in df.columns
    
    # Check that -1 (noise) exists due to the outlier
    assert -1 in df["cluster"].values
    
    # The dense points should form at least one cluster (e.g., 0)
    assert 0 in df["cluster"].values
    
    summaries = clustering.get_cluster_summaries(df)
    assert "Noise (Isolated)" in summaries
    assert "Cluster 0" in summaries
    
    # The outlier was 99999.0
    assert summaries["Noise (Isolated)"]["mean_be_amount"] > 50000.0

def test_dbscan_reproducibility():
    records = _generate_mock_records(15)
    
    clustering1 = BudgetDBSCANClustering(eps=0.5, min_samples=4)
    df1 = clustering1.fit_predict(records)
    
    clustering2 = BudgetDBSCANClustering(eps=0.5, min_samples=4)
    df2 = clustering2.fit_predict(records)
    
    # DBSCAN is deterministic given the same data order
    assert (df1["cluster"].values == df2["cluster"].values).all()

def test_dbscan_evaluation():
    records = _generate_mock_records(20)
    clustering = BudgetDBSCANClustering(eps=0.5, min_samples=3)
    
    _, _, X = clustering.prepare_data(records)
    df = clustering.fit_predict(records)
    
    metrics = clustering.evaluate(X, df["cluster"].values)
    
    # silhouette_score could be valid or -1 depending on if it found >1 cluster
    assert "silhouette_score" in metrics
