import pandas as pd
import json
from typing import List, Dict, Any, Union, Optional

def load_csv(filepath: str, **kwargs) -> pd.DataFrame:
    """Load CSV into a Pandas DataFrame."""
    return pd.read_csv(filepath, **kwargs)

def load_json(filepath: str) -> Union[Dict, List]:
    """Load JSON file."""
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)

def validate_required_columns(df: pd.DataFrame, required_columns: List[str]) -> bool:
    """Check if all required columns exist in the DataFrame."""
    return all(col in df.columns for col in required_columns)

def inspect_missing_values(df: pd.DataFrame) -> pd.Series:
    """Return the count of missing values per column."""
    return df.isnull().sum()

def detect_duplicates(df: pd.DataFrame, subset: Optional[List[str]] = None) -> pd.DataFrame:
    """Return duplicate rows in the DataFrame."""
    return df[df.duplicated(subset=subset, keep=False)]

def normalize_dates(df: pd.DataFrame, column: str, date_format: Optional[str] = None) -> pd.DataFrame:
    """Convert a column to datetime format, coercing errors to NaT."""
    df = df.copy()
    df[column] = pd.to_datetime(df[column], format=date_format, errors='coerce')
    return df

def normalize_text(text: Any) -> str:
    """Basic text normalization: lowercasing and stripping whitespace."""
    if not isinstance(text, str):
        return str(text) if text is not None else ""
    return text.strip().lower()

def normalize_text_column(df: pd.DataFrame, column: str) -> pd.DataFrame:
    """Apply text normalization to an entire DataFrame column."""
    df = df.copy()
    df[column] = df[column].apply(normalize_text)
    return df
