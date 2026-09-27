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
