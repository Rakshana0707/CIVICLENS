import pytest
import pandas as pd
from backend.core.pipeline.base import BaseDataPipeline
from backend.utils.data_utils import validate_required_columns, detect_duplicates, normalize_text, normalize_dates

class DummyPipeline(BaseDataPipeline):
    def ingest(self, source):
        return pd.DataFrame(source)
    def validate(self, data):
        return validate_required_columns(data, ["id", "text"])
    def clean(self, data):
        return detect_duplicates(data, subset=["id"]).drop_duplicates(subset=["id"])
    def transform(self, data):
        data['text'] = data['text'].apply(normalize_text)
        return data
    def store(self, data):
        return data.to_dict('records')

def test_pipeline_execution():
    pipeline = DummyPipeline()
    raw_data = [
        {"id": 1, "text": "  Hello World  "},
        {"id": 1, "text": "Duplicate"},
        {"id": 2, "text": "UPPERCASE TEXT"}
    ]
    
    result = pipeline.run(raw_data)
    
    assert len(result) == 2
    assert result[0]["text"] == "hello world"
    assert result[1]["text"] == "uppercase text"

def test_pipeline_validation_failure():
    pipeline = DummyPipeline()
    bad_data = [{"id": 1, "missing_text": "data"}]
    
    with pytest.raises(ValueError):
        pipeline.run(bad_data)

def test_date_normalization():
    df = pd.DataFrame({"dates": ["01-15-2024", "2024/02/16", "not a date"]})
    cleaned_df = normalize_dates(df, "dates")
    
    assert cleaned_df["dates"].isna().iloc[2]
    assert str(cleaned_df["dates"].iloc[0]).startswith("2024-01-15")
