import pandas as pd
import numpy as np
from typing import List, Dict, Any, Tuple, Union
from sklearn.ensemble import IsolationForest
from sklearn.impute import SimpleImputer
from backend.models.budget import BudgetRecord
from backend.ml.budget_features import BudgetFeatureEngineering

class BudgetIsolationForest:
    """
    Isolation Forest pipeline for flagging statistical anomalies in budget records.
    
    Interpretations & Limitations (CRITICAL):
    - An anomaly here is strictly a statistical deviation (e.g., an unusually large 
      allocation, a dramatic year-over-year percentage change, or a unique variance).
    - Statistical anomalies DO NOT constitute evidence of corruption, fraud, or wrongdoing.
      They simply identify records that are structurally different from the majority.
    - Departments and schemes flagged by this model should NOT be automatically labeled 
      as suspicious. They are simply prioritized for manual review or contextual analysis.
    - Scikit-learn's Isolation Forest requires complete matrices. Missing historical 
      percentage changes are imputed with 0.0 purely for model execution, but raw 
      values are preserved for interpretable output.
    """
    
    def __init__(
        self, 
        contamination: Union[float, str] = "auto", 
        n_estimators: int = 100, 
        random_state: int = 42
    ):
        self.contamination = contamination
        self.n_estimators = n_estimators
        self.random_state = random_state
        self.feature_extractor = BudgetFeatureEngineering()
        # Impute missing values with 0.0 for the tree splitting geometry
        self.imputer = SimpleImputer(strategy="constant", fill_value=0.0)
        self.model = None
        
    def prepare_data(self, records: List[BudgetRecord]) -> Tuple[pd.DataFrame, pd.DataFrame, np.ndarray]:
        """Runs the feature engineering pipeline and prepares the matrix for anomaly detection."""
        if len(records) < 2:
            raise ValueError("Insufficient data for Isolation Forest. Minimum 2 records required.")
            
        self.feature_extractor.fit(records)
        scaled_features, identifiers = self.feature_extractor.transform(records)
        
        if len(scaled_features) < 2:
            raise ValueError("Insufficient valid data after feature engineering exclusions.")
            
        X = self.imputer.fit_transform(scaled_features)
        return scaled_features, identifiers, X
        
    def fit_predict(self, records: List[BudgetRecord]) -> pd.DataFrame:
        """
        Fits the Isolation Forest and returns scores alongside identifiers and raw features.
        """
        scaled_features, identifiers, X = self.prepare_data(records)
        
        self.model = IsolationForest(
            n_estimators=self.n_estimators,
            contamination=self.contamination,
            random_state=self.random_state
        )
        
        # -1 for anomalies/outliers, 1 for normal/inliers
        labels = self.model.fit_predict(X)
        
        # Lower scores indicate higher abnormality (negative scores are outliers)
        scores = self.model.decision_function(X)
        
        result_df = identifiers.copy()
        result_df["is_anomaly"] = (labels == -1)
        result_df["anomaly_score"] = scores
        
        # Include raw unscaled features for interpretable summaries
        raw_df = self.feature_extractor._create_raw_matrix(records)
        raw_features, _ = self.feature_extractor._engineer_features(raw_df)
        
        for col in raw_features.columns:
            result_df[col] = raw_features[col]
            
        # Sort by anomaly score ascending (most anomalous first)
        result_df = result_df.sort_values(by="anomaly_score", ascending=True).reset_index(drop=True)
            
        return result_df
        
    def get_flagged_records(self, result_df: pd.DataFrame) -> List[Dict[str, Any]]:
        """
        Filters and returns the anomalous records as a list of dictionaries.
        """
        if result_df.empty or "is_anomaly" not in result_df:
            return []
            
        flagged = result_df[result_df["is_anomaly"] == True].copy()
        
        # Convert NaNs to None for valid downstream JSON representation
        flagged = flagged.replace({np.nan: None})
        
        return flagged.to_dict(orient="records")
