import pandas as pd
import numpy as np
from typing import List, Dict, Any, Tuple
from sklearn.cluster import KMeans
from sklearn.impute import SimpleImputer
from backend.models.budget import BudgetRecord
from backend.ml.budget_features import BudgetFeatureEngineering
from backend.ml.evaluation import evaluate_clustering

class BudgetKMeansClustering:
    """
    K-Means clustering pipeline for budget records.
    
    Assumptions:
    - Feature scaling: Features are standard-scaled (mean=0, variance=1) by BudgetFeatureEngineering
      so monetary magnitudes don't overpower percentage changes in Euclidean distance.
    - Missing Values: Scikit-learn K-Means requires complete matrices. We impute missing 
      year-over-year changes or missing actuals with 0.0 purely for the clustering geometry 
      (representing 'no known change/variance'), but original values are kept for summaries.
    - Interpretation: Clusters represent mathematical groupings of allocation patterns, not 
      inherently 'good' or 'bad' performance, nor proof of political intent.
    """
    
    def __init__(self, random_state: int = 42):
        self.random_state = random_state
        self.feature_extractor = BudgetFeatureEngineering()
        # Impute NaNs with 0 for K-Means geometric distances
        self.imputer = SimpleImputer(strategy="constant", fill_value=0.0)
        
    def prepare_data(self, records: List[BudgetRecord]) -> Tuple[pd.DataFrame, pd.DataFrame, np.ndarray]:
        """Runs the feature engineering pipeline and prepares the matrix for clustering."""
        if len(records) < 2:
            raise ValueError("Insufficient data for clustering. Minimum 2 records required.")
            
        self.feature_extractor.fit(records)
        scaled_features, identifiers = self.feature_extractor.transform(records)
        
        if len(scaled_features) < 2:
            raise ValueError("Insufficient valid data after feature engineering exclusions.")
            
        # Impute missing scaled values (NaNs from YoY/Actuals) with 0.0
        X = self.imputer.fit_transform(scaled_features)
        return scaled_features, identifiers, X
        
    def evaluate_clusters(self, X: np.ndarray, k_range: range = range(2, 10)) -> List[Dict[str, Any]]:
        """Evaluates candidate cluster counts using inertia and silhouette score."""
        n_samples = len(X)
        evaluations = []
        
        for k in k_range:
            if k >= n_samples:
                continue
                
            model = KMeans(n_clusters=k, random_state=self.random_state, n_init="auto")
            labels = model.fit_predict(X)
            
            metrics = evaluate_clustering(X, labels)
            
            evaluations.append({
                "k": k,
                "inertia": float(model.inertia_),
                "silhouette_score": metrics.get("silhouette_score", -1.0)
            })
            
        return evaluations
        
    def fit_predict(self, records: List[BudgetRecord], k: int) -> pd.DataFrame:
        """
        Fits K-Means with k clusters and returns assignments mapped to original identifiers.
        """
        scaled_features, identifiers, X = self.prepare_data(records)
        
        if k >= len(X) or k < 2:
            raise ValueError(f"Invalid cluster count k={k} for {len(X)} samples.")
            
        model = KMeans(n_clusters=k, random_state=self.random_state, n_init="auto")
        labels = model.fit_predict(X)
        
        # Merge identifiers, original unscaled features (if we could, but here we just have scaled)
        # We will append the cluster label to the identifiers dataframe.
        result_df = identifiers.copy()
        result_df["cluster"] = labels
        
        # Include raw unscaled features for interpretable summaries
        # Re-run _create_raw_matrix and _engineer_features from the extractor without scaling
        raw_df = self.feature_extractor._create_raw_matrix(records)
        raw_features, _ = self.feature_extractor._engineer_features(raw_df)
        
        for col in raw_features.columns:
            result_df[col] = raw_features[col]
            
        return result_df
        
    def get_cluster_summaries(self, result_df: pd.DataFrame) -> Dict[int, Dict[str, Any]]:
        """
        Generates interpretable feature statistics per cluster from the unscaled data.
        """
        if result_df.empty or "cluster" not in result_df:
            return {}
            
        summaries = {}
        for cluster_id, group in result_df.groupby("cluster"):
            summaries[int(cluster_id)] = {
                "count": len(group),
                "mean_be_amount": float(group["be_amount"].mean()),
                "median_allocation_share": float(group["allocation_share"].median()),
                # Use mean ignoring NaNs for percentage changes
                "mean_yoy_change_be": float(group["yoy_change_be"].mean(skipna=True)) if not group["yoy_change_be"].isna().all() else None,
                "mean_actual_vs_be_diff": float(group["actual_vs_be_diff"].mean(skipna=True)) if not group["actual_vs_be_diff"].isna().all() else None,
            }
            
        return summaries
