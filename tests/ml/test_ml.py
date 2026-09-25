import numpy as np
from backend.ml.evaluation import evaluate_classification, evaluate_clustering
from backend.ml.dataset import split_dataset
from backend.ml.experiment import ExperimentTrackingMetadata

def test_evaluate_classification():
    y_true = [0, 1, 1, 0, 1]
    y_pred = [0, 1, 0, 0, 1] 
    
    metrics = evaluate_classification(y_true, y_pred)
    assert "accuracy" in metrics
    assert "f1_score" in metrics
    assert "confusion_matrix" in metrics
    assert metrics["accuracy"] == 0.8
    assert len(metrics["confusion_matrix"]) == 2

def test_evaluate_clustering():
    X = np.array([[1, 2], [1, 4], [1, 0],
                  [10, 2], [10, 4], [10, 0]])
    labels = [0, 0, 0, 1, 1, 1]
    
    metrics = evaluate_clustering(X, labels)
    assert "silhouette_score" in metrics
    assert metrics["silhouette_score"] > 0.0
    
def test_evaluate_clustering_invalid():
    X = np.array([[1, 2], [1, 4]])
    labels = [0, 0]
    
    metrics = evaluate_clustering(X, labels)
    assert metrics["silhouette_score"] == -1.0

def test_split_dataset():
    X = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
    y = [0, 1, 0, 1, 0, 1, 0, 1, 0, 1]
    
    X_train, X_test, y_train, y_test = split_dataset(X, y, test_size=0.2, random_state=42)
    assert len(X_train) == 8
    assert len(X_test) == 2
    assert len(y_train) == 8

def test_experiment_metadata():
    exp = ExperimentTrackingMetadata(
        experiment_id="exp_001",
        model_name="test_random_forest",
        model_version="1.0"
    )
    assert exp.model_name == "test_random_forest"
    assert exp.hyperparameters == {}
    assert exp.training_time_seconds == 0.0
    assert exp.timestamp is not None
