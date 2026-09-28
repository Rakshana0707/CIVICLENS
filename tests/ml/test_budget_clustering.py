import pytest
import pandas as pd
import numpy as np
from backend.models.budget import BudgetRecord, BudgetStage, BudgetDepartment, BudgetScheme
from backend.ml.budget_clustering import BudgetKMeansClustering

def _generate_mock_records(n: int) -> list:
    dept = BudgetDepartment(name="Test Dept")
    records = []
    # Create distinct patterns for clustering
    for i in range(n):
        scheme = BudgetScheme(name=f"Scheme {i}", department=dept)
        # Cluster 0 pattern: Small amount, low share
        # Cluster 1 pattern: High amount, high share
        amount = 100.0 if i % 2 == 0 else 10000.0
        records.append(
            BudgetRecord(scheme=scheme, financial_year="2023-24", budget_stage=BudgetStage.budget_estimate, amount=amount)
        )
    return records

def test_clustering_insufficient_data():
    clustering = BudgetKMeansClustering()
    records = _generate_mock_records(1)
    with pytest.raises(ValueError, match="Insufficient data"):
        clustering.prepare_data(records)

def test_clustering_invalid_k():
    clustering = BudgetKMeansClustering()
    records = _generate_mock_records(5)
    with pytest.raises(ValueError, match="Invalid cluster count"):
        clustering.fit_predict(records, k=10)
    with pytest.raises(ValueError, match="Invalid cluster count"):
        clustering.fit_predict(records, k=1)

def test_clustering_evaluation():
    clustering = BudgetKMeansClustering(random_state=42)
    records = _generate_mock_records(10)
    
    _, _, X = clustering.prepare_data(records)
    evaluations = clustering.evaluate_clusters(X, k_range=range(2, 5))
    
    assert len(evaluations) == 3
    assert evaluations[0]["k"] == 2
    assert "inertia" in evaluations[0]
    assert "silhouette_score" in evaluations[0]
    assert evaluations[0]["silhouette_score"] > 0

def test_clustering_reproducibility_and_summaries():
    records = _generate_mock_records(10)
    
    # Run 1
    clustering1 = BudgetKMeansClustering(random_state=42)
    df1 = clustering1.fit_predict(records, k=2)
    
    # Run 2
    clustering2 = BudgetKMeansClustering(random_state=42)
    df2 = clustering2.fit_predict(records, k=2)
    
    # Check reproducibility
    assert (df1["cluster"].values == df2["cluster"].values).all()
    
    # Check assignments
    assert "cluster" in df1.columns
    assert "department" in df1.columns
    assert "scheme" in df1.columns
    assert "be_amount" in df1.columns
    
    # Check summaries
    summaries = clustering1.get_cluster_summaries(df1)
    assert len(summaries) == 2
    assert 0 in summaries and 1 in summaries
    
    # Since we designed small vs large, means should differ significantly
    means = [summaries[0]["mean_be_amount"], summaries[1]["mean_be_amount"]]
    assert min(means) == 100.0
    assert max(means) == 10000.0
