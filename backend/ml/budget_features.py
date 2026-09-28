import pandas as pd
import numpy as np
from typing import List, Tuple, Dict, Any
from sklearn.preprocessing import StandardScaler
from backend.models.budget import BudgetRecord
from backend.ml.features import BaseFeatureExtractor

class BudgetFeatureEngineering(BaseFeatureExtractor):
    """
    Prepares budget records for clustering at the scheme-year level.
    
    Documented Rules for Missing Values:
    - Missing base Budget Estimates (BE) result in the scheme-year being excluded from analysis.
    - Missing Revised Estimates (RE) or Actuals are left as NaN (not invented as zero).
    - Missing year-over-year change is represented as NaN.
    - Allocation share is calculated strictly based on available department totals.
    """
    
    def __init__(self):
        self.scaler = StandardScaler()
        self.feature_columns = [
            "be_amount", 
            "allocation_share", 
            "yoy_change_be", 
            "actual_vs_be_diff"
        ]
        self.is_fitted = False
        
    def _create_raw_matrix(self, records: List[BudgetRecord]) -> pd.DataFrame:
        """Converts raw BudgetRecords into a scheme-year grouped DataFrame."""
        data = []
        for r in records:
            if r.amount is None or not r.scheme or not r.scheme.department:
                continue
            data.append({
                "department": r.scheme.department.name,
                "scheme": r.scheme.name,
                "financial_year": r.financial_year,
                "stage": r.budget_stage.value,
                "amount": r.amount
            })
            
        if not data:
            return pd.DataFrame()
            
        df = pd.DataFrame(data)
        
        # Group by department, scheme, year, stage
        grouped = df.groupby(["department", "scheme", "financial_year", "stage"])["amount"].sum().reset_index()
        
        # Pivot stages into columns
        pivot_df = grouped.pivot(
            index=["department", "scheme", "financial_year"],
            columns="stage",
            values="amount"
        ).reset_index()
        
        # Ensure columns exist even if missing from data
        for col in ["budget_estimate", "revised_estimate", "actual_expenditure"]:
            if col not in pivot_df.columns:
                pivot_df[col] = np.nan
                
        # Drop rows where budget_estimate is missing
        pivot_df = pivot_df.dropna(subset=["budget_estimate"])
        
        # Sort values to calculate Year-over-Year safely
        pivot_df = pivot_df.sort_values(by=["department", "scheme", "financial_year"]).reset_index(drop=True)
        
        return pivot_df
        
    def _engineer_features(self, df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """Calculates derived features and separates identifiers."""
        if df.empty:
            return pd.DataFrame(), pd.DataFrame()
            
        # 1. Budget amount (BE)
        df["be_amount"] = df["budget_estimate"]
        
        # 2. Allocation Share
        dept_totals = df.groupby(["department", "financial_year"])["be_amount"].transform("sum")
        df["allocation_share"] = np.where(dept_totals > 0, df["be_amount"] / dept_totals, 0)
        
        # 3. Year-over-Year change (BE)
        # Shift amounts grouped by scheme to find previous year
        df["prev_be"] = df.groupby(["department", "scheme"])["be_amount"].shift(1)
        df["yoy_change_be"] = np.where(
            df["prev_be"] > 0, 
            (df["be_amount"] - df["prev_be"]) / df["prev_be"], 
            np.nan
        )
        
        # 4. Budget-stage differences
        df["actual_vs_be_diff"] = np.where(
            (df["actual_expenditure"].notnull()) & (df["be_amount"] > 0),
            (df["actual_expenditure"] - df["be_amount"]) / df["be_amount"],
            np.nan
        )
        
        # Separate features from identifiers
        identifiers = df[["department", "scheme", "financial_year"]].copy()
        features = df[self.feature_columns].copy()
        
        return features, identifiers

    def fit(self, records: List[BudgetRecord], y: Any = None) -> "BudgetFeatureEngineering":
        raw_df = self._create_raw_matrix(records)
        features, _ = self._engineer_features(raw_df)
        
        if not features.empty:
            self.means_ = features.mean()
            self.stds_ = features.std(ddof=0)
            self.stds_ = self.stds_.replace(0, 1.0) # Avoid div by zero
        
        self.is_fitted = True
        return self
        
    def transform(self, records: List[BudgetRecord]) -> Tuple[pd.DataFrame, pd.DataFrame]:
        if not self.is_fitted:
            raise ValueError("Feature extractor must be fitted before transform.")
            
        raw_df = self._create_raw_matrix(records)
        features, identifiers = self._engineer_features(raw_df)
        
        if features.empty:
            return features, identifiers
            
        # Scale manually preserving NaNs strictly (no fabricated values)
        scaled_features = (features - self.means_) / self.stds_
        scaled_df = pd.DataFrame(scaled_features, columns=self.feature_columns, index=features.index)
        
        return scaled_df, identifiers
        
    def get_feature_dictionary(self) -> Dict[str, str]:
        """Returns metadata about the engineered features."""
        return {
            "be_amount": "Total Budget Estimate for the scheme in a given financial year. Observed numeric feature.",
            "allocation_share": "Derived numeric feature. Ratio of the scheme's BE to the total department BE for that year.",
            "yoy_change_be": "Derived numeric feature. Percentage change in BE from the previous available year. Kept as NaN if missing.",
            "actual_vs_be_diff": "Derived numeric feature. Percentage difference between Actual Expenditure and BE. Kept as NaN if missing."
        }
