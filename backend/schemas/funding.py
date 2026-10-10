"""
Phase 5 — Canonical Schemas for Political Funding Records.

Defines Pydantic/dataclass canonical schemas for:
A. Political Parties
B. Contributions
C. Financial Statements
D. Election Expenditure
"""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from datetime import datetime, timezone
from backend.funding.processor import AmountStatus, ExtractionMethod


@dataclass
class PoliticalPartySchema:
    """Canonical schema for a political party profile."""
    party_id: str
    official_name: str
    aliases: List[str] = field(default_factory=list)
    recognition_status: str = "STATE_RECOGNIZED_TN"  # NATIONAL, STATE_RECOGNIZED_TN, UNRECOGNIZED_REGISTERED
    valid_from: Optional[str] = None
    valid_to: Optional[str] = None
    source_references: List[str] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass
class ContributionSchema:
    """Canonical schema for an individual or corporate contribution record."""
    contribution_id: str
    party_id: str
    donor_name_as_reported: str
    donor_name_normalized: str
    amount: Optional[float]
    amount_status: str = AmountStatus.VALID_NUMERIC.value
    currency: str = "INR"
    contribution_date_as_reported: Optional[str] = None
    contribution_date_normalized: Optional[str] = None  # YYYY-MM-DD
    financial_year: str = "FY2021-22"
    contribution_type: str = "Unknown"  # Cheque, DemandDraft, EFT_RTGS, ElectoralBond, Cash, ElectoralTrust, Other
    document_id: str = ""
    page_number: int = 1
    table_number: int = 1
    original_row: str = ""
    extraction_method: str = ExtractionMethod.PDF_NATIVE_TABLE.value
    extraction_confidence: float = 1.0
    processed_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass
class FinancialStatementSchema:
    """Canonical schema for annual audited financial statements."""
    statement_id: str
    party_id: str
    financial_year: str
    income_categories: Dict[str, float] = field(default_factory=dict)
    expenditure_categories: Dict[str, float] = field(default_factory=dict)
    assets_and_liabilities: Dict[str, float] = field(default_factory=dict)
    total_income_reported: Optional[float] = None
    total_expenditure_reported: Optional[float] = None
    net_surplus_deficit: Optional[float] = None
    auditor_name: Optional[str] = None
    audit_date: Optional[str] = None
    document_id: str = ""
    processed_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass
class ElectionExpenditureSchema:
    """Canonical schema for party election campaign expenditure filings."""
    expenditure_id: str
    party_id: str
    election: str  # e.g., "TN Legislative Assembly 2021"
    reporting_period: str  # e.g., "FY2021-22"
    expenditure_categories: Dict[str, float] = field(default_factory=dict)
    reported_totals: Optional[float] = None
    document_id: str = ""
    processed_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass
class ValidationIssueRecord:
    """Schema for recording data quality and validation rule violations."""
    issue_id: str
    rule_code: str
    severity: str  # CRITICAL, WARNING, INFO
    entity_type: str  # Contribution, FinancialStatement, ElectionExpenditure, Party
    entity_id: str
    field_name: str
    description: str
    raw_value: Optional[str]
    suggested_action: str
    flagged_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
