from dataclasses import dataclass, asdict
from typing import List, Optional, Any, Dict
from backend.models.budget import BudgetRecord, BudgetStage

@dataclass
class BudgetRecordResponse:
    id: int
    financial_year: str
    budget_stage: str
    amount: Optional[float]
    currency_unit: str
    department_name: str
    scheme_name: str
    source_document_title: str

    @classmethod
    def from_model(cls, record: BudgetRecord) -> 'BudgetRecordResponse':
        return cls(
            id=record.id,
            financial_year=record.financial_year,
            budget_stage=record.budget_stage.value,
            amount=record.amount,
            currency_unit=record.currency_unit,
            department_name=record.scheme.department.name if record.scheme and record.scheme.department else "Unknown",
            scheme_name=record.scheme.name if record.scheme else "Unknown",
            source_document_title=record.source_document.title if record.source_document else "Unknown"
        )

@dataclass
class PaginatedResponse:
    records: List[Dict[str, Any]]
    total_count: int
    skip: int
    limit: int

@dataclass
class DepartmentResponse:
    id: int
    name: str

@dataclass
class SchemeResponse:
    id: int
    name: str
    department_id: int
