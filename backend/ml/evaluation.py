from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    confusion_matrix, silhouette_score
)
from typing import Dict, Any

def evaluate_classification(y_true: Any, y_pred: Any) -> Dict[str, Any]:
    """
    Generates a standardized dictionary of classification metrics.
    Suitable for supervised tasks like intent classification or claim categorization.
    """
    return {
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "precision": float(precision_score(y_true, y_pred, average='weighted', zero_division=0)),
        "recall": float(recall_score(y_true, y_pred, average='weighted', zero_division=0)),
        "f1_score": float(f1_score(y_true, y_pred, average='weighted', zero_division=0)),
        "confusion_matrix": confusion_matrix(y_true, y_pred).tolist()
    }

def evaluate_clustering(X: Any, labels: Any) -> Dict[str, Any]:
    """
    Generates standardized metrics for unsupervised clustering tasks,
    like Topic Modeling or DBSCAN grouping.
    """
    unique_labels = len(set(labels))
    # Silhouette score is only calculable with 1 < clusters < samples
    if 1 < unique_labels < len(X):
        return {"silhouette_score": float(silhouette_score(X, labels))}
    
    # Indicate invalid state gracefully
    return {"silhouette_score": -1.0}
