import pytest
import pandas as pd
from backend.core.pipeline.base import BaseDataPipeline
from backend.utils.data_utils import (
    validate_required_columns,
    inspect_missing_values,
    detect_duplicates,
    normalize_dates,
    normalize_text,
    normalize_text_column
)

class DummyPipeline(BaseDataPipeline):
    """A concrete implementation of the pipeline purely for testing framework robustness."""
    def ingest(self, source: pd.DataFrame) -> pd.DataFrame:
        # source is an in-memory dataframe
        return source.copy()
        
    def validate(self, data: pd.DataFrame) -> bool:
        return validate_required_columns(data, ["id", "text", "date"])
        
    def clean(self, data: pd.DataFrame) -> pd.DataFrame:
        # Drop duplicates for testing
        return data.drop_duplicates(subset=["id"])
        
    def transform(self, data: pd.DataFrame) -> pd.DataFrame:
        data = normalize_text_column(data, "text")
        data = normalize_dates(data, "date")
        return data
        
    def store(self, data: pd.DataFrame) -> int:
        # Simulate storing by returning the final row count
        return len(data)

def test_pipeline_execution():
    df = pd.DataFrame({
        "id": [1, 2, 2],
        "text": [" Hello ", "WORLD", "WORLD"],
        "date": ["2024-01-01", "2024-01-02", "2024-01-02"]
    })
    
    pipeline = DummyPipeline()
    final_count = pipeline.run(df)
    
    # One duplicate dropped, leaving 2 records total
    assert final_count == 2
    
def test_pipeline_validation_failure():
    df = pd.DataFrame({
        "wrong_column": [1, 2],
    })
    pipeline = DummyPipeline()
    
    with pytest.raises(ValueError, match="Data validation failed"):
        pipeline.run(df)

def test_data_utils_operations():
    df = pd.DataFrame({
        "A": [1, 2, None],
        "B": ["foo", "foo", "bar"]
    })
    
    # Test Missing values
    missing = inspect_missing_values(df)
    assert missing["A"] == 1
    assert missing["B"] == 0
    
    # Test Duplicates
    dups = detect_duplicates(df, subset=["B"])
    assert len(dups) == 2 # "foo" appears twice
    
    # Test Text normalization
    assert normalize_text("  TEST  ") == "test"
    assert normalize_text(None) == ""
    
    # Test Text normalization on column
    df_norm = normalize_text_column(df, "B")
    assert df_norm.iloc[0]["B"] == "foo"
