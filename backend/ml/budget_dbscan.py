import pandas as pd
import numpy as np
from typing import List, Dict, Any, Tuple
from sklearn.cluster import DBSCAN
from sklearn.impute import SimpleImputer
from backend.models.budget import BudgetRecord
from backend.ml.budget_features import BudgetFeatureEngineering
from backend.ml.evaluation import evaluate_clustering

class BudgetDBSCANClustering:
    """
    DBSCAN clustering pipeline for identifying density-based groupings and isolated 
    observations (noise) in budget records.
    
    Assumptions & Parameters:
    - Feature Scaling: Crucial for DBSCAN. BudgetFeatureEngineering scales all features 
      to zero mean and unit variance. This ensures large monetary values do not artificially 
      dominate the `eps` neighborhood distance over percentage features.
    - eps (float): The maximum distance between two samples for one to be considered as 
      in the neighborhood of the other. In a standard-scaled space, eps=0.5 means a 
      half-standard-deviation radius.
    - min_samples (int): The number of samples (or total weight) in a neighborhood for 
      a point to be considered as a core point.
    - Interpretation of Noise: Points labeled as -1 (noise) are statistical observations 
      that do not fit into dense areas. They are NOT evidence of wrongdoing or erroneous 
      data, but simply unique or isolated allocation patterns.
    """
    
    def __init__(self, eps: float = 0.5, min_samples: int = 5):
        self.eps = eps
        self.min_samples = min_samples
        self.feature_extractor = BudgetFeatureEngineering()
        self.imputer = SimpleImputer(strategy="constant", fill_value=0.0)
        
    def prepare_data(self, records: List[BudgetRecord]) -> Tuple[pd.DataFrame, pd.DataFrame, np.ndarray]:
        """Runs the feature engineering pipeline and prepares the matrix for clustering."""
        if len(records) < 2:
            raise ValueError("Insufficient data for clustering. Minimum 2 records required.")
            
        self.feature_extractor.fit(records)
        scaled_features, identifiers = self.feature_extractor.transform(records)
        
        if len(scaled_features) < 2:
            raise ValueError("Insufficient valid data after feature engineering exclusions.")
            
        X = self.imputer.fit_transform(scaled_features)
        return scaled_features, identifiers, X
        
    def fit_predict(self, records: List[BudgetRecord]) -> pd.DataFrame:
        """
        Fits DBSCAN and returns assignments mapped to original identifiers.
        Noise points will have cluster label -1.
        """
        scaled_features, identifiers, X = self.prepare_data(records)
        
        model = DBSCAN(eps=self.eps, min_samples=self.min_samples)
        labels = model.fit_predict(X)
        
        result_df = identifiers.copy()
        result_df["cluster"] = labels
        
        raw_df = self.feature_extractor._create_raw_matrix(records)
        raw_features, _ = self.feature_extractor._engineer_features(raw_df)
        
        for col in raw_features.columns:
            result_df[col] = raw_features[col]
            
        return result_df
        
    def evaluate(self, X: np.ndarray, labels: np.ndarray) -> Dict[str, Any]:
        """Evaluates clustering using silhouette score where valid."""
        return evaluate_clustering(X, labels)
        
    def get_cluster_summaries(self, result_df: pd.DataFrame) -> Dict[str, Dict[str, Any]]:
        """
        Generates interpretable feature statistics per cluster (and noise group).
        Cluster '-1' denotes isolated/noise points.
        """
        if result_df.empty or "cluster" not in result_df:
            return {}
            
        summaries = {}
        for cluster_id, group in result_df.groupby("cluster"):
            label = "Noise (Isolated)" if cluster_id == -1 else f"Cluster {cluster_id}"
            
            summaries[label] = {
                "count": len(group),
                "mean_be_amount": float(group["be_amount"].mean()),
                "median_allocation_share": float(group["allocation_share"].median()),
                "mean_yoy_change_be": float(group["yoy_change_be"].mean(skipna=True)) if not group["yoy_change_be"].isna().all() else None,
                "mean_actual_vs_be_diff": float(group["actual_vs_be_diff"].mean(skipna=True)) if not group["actual_vs_be_diff"].isna().all() else None,
            }
            
        return summaries
