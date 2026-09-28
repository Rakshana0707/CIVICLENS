import pandas as pd
import numpy as np
from typing import List, Dict, Any, Tuple, Optional
from sklearn.decomposition import PCA
from sklearn.impute import SimpleImputer
from backend.models.budget import BudgetRecord
from backend.ml.budget_features import BudgetFeatureEngineering

class BudgetPCAAnalysis:
    """
    Principal Component Analysis (PCA) pipeline for budget records.
    
    Interpretations & Limitations:
    - Principal components are orthogonal mathematical transformations capturing 
      maximum variance. They are NOT directly interpretable budget categories 
      (e.g., 'PC1 is not the education budget').
    - PCA highlights correlations and variance in the feature space, but it 
      DOES NOT prove causal relationships between features.
    - Feature Scaling: Crucial for PCA since it is variance-based. 
      The BudgetFeatureEngineering pipeline handles zero-mean, unit-variance scaling.
    - Identifiers are strictly separated from the transformation matrix.
    """
    
    def __init__(self, n_components: Optional[int] = 2, random_state: int = 42):
        self.n_components = n_components
        self.random_state = random_state
        self.feature_extractor = BudgetFeatureEngineering()
        # Impute missing values with 0.0 for the geometric transformation
        self.imputer = SimpleImputer(strategy="constant", fill_value=0.0)
        self.pca_model = None
        
    def fit_transform(self, records: List[BudgetRecord]) -> pd.DataFrame:
        """
        Fits PCA and returns the principal components merged with record identifiers.
        """
        if len(records) < 2:
            raise ValueError("Insufficient data for PCA. Minimum 2 records required.")
            
        self.feature_extractor.fit(records)
        scaled_features, identifiers = self.feature_extractor.transform(records)
        
        n_features = scaled_features.shape[1]
        
        if self.n_components is not None and self.n_components > n_features:
            raise ValueError(f"Cannot request {self.n_components} components when there are only {n_features} features.")
            
        if len(scaled_features) < 2:
            raise ValueError("Insufficient valid data after feature engineering exclusions.")
            
        X = self.imputer.fit_transform(scaled_features)
        
        self.pca_model = PCA(n_components=self.n_components, random_state=self.random_state)
        components = self.pca_model.fit_transform(X)
        
        result_df = identifiers.copy()
        
        for i in range(components.shape[1]):
            result_df[f"PC{i+1}"] = components[:, i]
            
        return result_df
        
    def get_explained_variance(self) -> Dict[str, Any]:
        """
        Returns explained variance ratios and cumulative explained variance.
        Must be called after fit_transform.
        """
        if self.pca_model is None:
            raise ValueError("PCA model has not been fitted. Call fit_transform first.")
            
        ratios = self.pca_model.explained_variance_ratio_
        cumulative = np.cumsum(ratios)
        
        return {
            "explained_variance_ratio": ratios.tolist(),
            "cumulative_explained_variance": cumulative.tolist(),
            "total_variance_explained": float(cumulative[-1])
        }
