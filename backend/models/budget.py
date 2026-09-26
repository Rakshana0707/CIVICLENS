from sqlalchemy import Column, String, Integer, Float, Enum, DateTime, UniqueConstraint
import enum
from backend.database.base_class import Base
from datetime import datetime

class BudgetStage(enum.Enum):
    budget_estimate = "budget_estimate"
    revised_estimate = "revised_estimate"
    actual_expenditure = "actual_expenditure"

class BudgetRecord(Base):
    __tablename__ = 'budget_records'

    record_id = Column(String, primary_key=True, index=True)
    department_name = Column(String, nullable=False, index=True)
    department_code = Column(String, nullable=True)
    scheme_name = Column(String, nullable=False, index=True)
    head_of_account = Column(String, nullable=True, index=True)
    original_category = Column(String, nullable=True)
    normalized_category = Column(String, nullable=True)
    financial_year = Column(String, nullable=False, index=True)
    budget_stage = Column(Enum(BudgetStage), nullable=False)
    amount = Column(Float, nullable=True)
    currency_unit = Column(String, nullable=False, default="INR_Absolute")
    source_document_id = Column(String, nullable=False)
    source_page_number = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Ensure idempotency
    __table_args__ = (
        UniqueConstraint('source_document_id', 'department_name', 'scheme_name', 'head_of_account', 'financial_year', 'budget_stage', name='uq_budget_record'),
    )
