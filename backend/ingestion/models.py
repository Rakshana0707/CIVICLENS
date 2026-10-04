from dataclasses import dataclass
from typing import Optional
from backend.models.budget import BudgetStage

@dataclass
class RawBudgetRecord:
    record_id: str
    department_name: str
    scheme_name: str
    financial_year: str
    budget_stage: BudgetStage
    source_document_id: str
    head_of_account: Optional[str] = None
    original_category: Optional[str] = None
    normalized_category: Optional[str] = None
    amount: Optional[float] = None
    currency_unit: str = "INR_Absolute"
    source_page_number: Optional[int] = None

@dataclass
class RawSchemeRecord:
    record_id: str
    department_name: str
    scheme_name: str
    financial_year: str
    source_document_id: str
    source_page_number: Optional[int] = None
    description: Optional[str] = None
    objectives: Optional[str] = None
    target_beneficiaries: Optional[str] = None
    sector_category: Optional[str] = None
    allocation_amount: Optional[str] = None
    implementation_details: Optional[str] = None

@dataclass
class ExtractedManifestoSegment:
    """
    Represents an extracted segment of a political manifesto.
    Preserves original text, language, and precise source location.
    """
    manifesto_id: str
    page_number: Optional[int] = None
    section: Optional[str] = None
    original_text: str = ""
    normalized_text: Optional[str] = None
    language: str = "Unknown"
    extraction_method: str = "pdfplumber"
    OCR_used: bool = False
    extraction_confidence: float = 1.0
