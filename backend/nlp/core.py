from dataclasses import dataclass
from typing import List, Dict, Any, Optional

@dataclass
class LanguageMetadata:
    """Structure to hold information about the detected language."""
    language_code: str
    script: str
    confidence: float

@dataclass
class NLPResult:
    """
    Standardized result structure for all NLP processing tasks.
    Ensures that regardless of which model (mBERT, IndicBERT) is used,
    the output format remains consistent.
    """
    original_text: str
    normalized_text: str
    tokens: Optional[List[str]] = None
    embedding: Optional[List[float]] = None
    language: Optional[LanguageMetadata] = None
    metadata: Optional[Dict[str, Any]] = None
