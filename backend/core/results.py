from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional

@dataclass
class SourceReference:
    """Standardized source reference to ensure data traceability."""
    source_name: str
    url: Optional[str] = None
    document_title: Optional[str] = None
    page_number: Optional[int] = None

@dataclass
class EvidenceItem:
    """Standardized evidence representation returned by analysis modules."""
    content: str
    context: Optional[str] = None
    explanation: Optional[str] = None
    supporting_values: Dict[str, Any] = field(default_factory=dict)
    source_reference: Optional[SourceReference] = None

@dataclass
class ExplainableResult:
    """
    Standardized result structure that all analytical modules must return.
    Guarantees that statistical indicators and model assessments are paired with 
    evidence, transparent explanations, and noted limitations rather than opaque binary judgments.
    """
    result_type: str
    summary: str
    explanation: str
    numerical_indicators: Dict[str, float] = field(default_factory=dict)
    model_output: Dict[str, Any] = field(default_factory=dict)
    confidence: Optional[float] = None
    evidence: List[EvidenceItem] = field(default_factory=list)
    source_references: List[SourceReference] = field(default_factory=list)
    limitations: List[str] = field(default_factory=list)
