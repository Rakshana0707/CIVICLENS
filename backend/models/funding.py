"""
Phase 5 — Political Funding Database Models.

Defines SQLAlchemy ORM entities for:
- FinancialDocument
- Donor
- ElectoralTrust
- Contribution
- PartyFinancialStatement
- ElectionExpenditure
- FinancialMetric
- ValidationIssue
"""

import enum
from datetime import datetime, timezone
from sqlalchemy import (
    Column, Integer, String, Text, DateTime, ForeignKey, Float, Boolean, JSON, UniqueConstraint
)
from sqlalchemy.orm import relationship
from backend.database.base_class import Base


class FinancialDocument(Base):
    """
    Metadata for ingested statutory financial disclosures and audit documents.
    """
    __tablename__ = "financial_documents"

    document_id = Column(String, primary_key=True, index=True)
    source_id = Column(String, nullable=False, index=True)
    party_id = Column(String, ForeignKey("political_parties.party_id", ondelete="SET NULL"), nullable=True, index=True)
    financial_year = Column(String, nullable=False, index=True)
    filing_type = Column(String, nullable=False, index=True)  # Form24A, AnnualAudit, TrustReport, BondDisclosure, ElectionExpenditure
    file_path = Column(String, nullable=True)
    file_hash_sha256 = Column(String, nullable=False, unique=True, index=True)
    source_url = Column(String, nullable=True)
    submission_date = Column(String, nullable=True)
    page_count = Column(Integer, default=1)
    is_scanned = Column(Boolean, default=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    party = relationship("PoliticalParty", foreign_keys=[party_id])
    contributions = relationship("Contribution", back_populates="document", cascade="all, delete-orphan")
    statements = relationship("PartyFinancialStatement", back_populates="document", cascade="all, delete-orphan")
    expenditures = relationship("ElectionExpenditure", back_populates="document", cascade="all, delete-orphan")
    validation_issues = relationship("ValidationIssue", back_populates="document", cascade="all, delete-orphan")


class Donor(Base):
    """
    Entity profile for disaggregated individual/corporate donors.
    """
    __tablename__ = "donors"

    donor_id = Column(String, primary_key=True, index=True)
    legal_name = Column(String, nullable=False, index=True)  # Unaltered reported name
    normalized_name = Column(String, nullable=False, index=True)
    donor_type = Column(String, default="UNKNOWN")  # Corporate, Individual, ElectoralTrust, Unknown
    cin_number = Column(String, nullable=True, index=True)
    pan_hash = Column(String, nullable=True)
    address = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    contributions = relationship("Contribution", back_populates="donor")


class ElectoralTrust(Base):
    """
    Registered Electoral Trust profile.
    """
    __tablename__ = "electoral_trusts"

    trust_id = Column(String, primary_key=True, index=True)
    trust_name = Column(String, nullable=False, index=True)
    registration_no = Column(String, nullable=True)
    corporate_sponsor = Column(String, nullable=True)
    nodal_bank = Column(String, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class Contribution(Base):
    """
    Granular itemized political donation record (> ₹20,000 or disaggregated).
    """
    __tablename__ = "contributions"

    contribution_id = Column(String, primary_key=True, index=True)
    document_id = Column(String, ForeignKey("financial_documents.document_id", ondelete="CASCADE"), nullable=False, index=True)
    party_id = Column(String, ForeignKey("political_parties.party_id", ondelete="CASCADE"), nullable=False, index=True)
    donor_id = Column(String, ForeignKey("donors.donor_id", ondelete="SET NULL"), nullable=True, index=True)
    financial_year = Column(String, nullable=False, index=True)
    donor_name_as_reported = Column(String, nullable=False)
    donor_name_normalized = Column(String, nullable=False, index=True)
    amount_inr = Column(Float, nullable=True)
    amount_status = Column(String, default="VALID_NUMERIC")
    currency = Column(String, default="INR")
    contribution_date_as_reported = Column(String, nullable=True)
    contribution_date_normalized = Column(String, nullable=True, index=True)
    payment_mode = Column(String, nullable=True)
    page_number = Column(Integer, default=1)
    table_number = Column(Integer, default=1)
    original_row = Column(Text, nullable=True)
    extraction_method = Column(String, default="PDF_NATIVE_TABLE")
    extraction_confidence = Column(Float, default=1.0)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    document = relationship("FinancialDocument", back_populates="contributions")
    party = relationship("PoliticalParty", foreign_keys=[party_id])
    donor = relationship("Donor", back_populates="contributions")

    __table_args__ = (
        UniqueConstraint('document_id', 'page_number', 'table_number', 'contribution_id', name='uq_contribution_provenance'),
    )


class PartyFinancialStatement(Base):
    """
    Audited annual Income & Expenditure and Balance Sheet statement summaries.
    """
    __tablename__ = "party_financial_statements"

    statement_id = Column(String, primary_key=True, index=True)
    party_id = Column(String, ForeignKey("political_parties.party_id", ondelete="CASCADE"), nullable=False, index=True)
    financial_year = Column(String, nullable=False, index=True)
    total_income = Column(Float, nullable=True)
    total_expenditure = Column(Float, nullable=True)
    net_surplus_deficit = Column(Float, nullable=True)
    income_categories_json = Column(JSON, nullable=True)
    expenditure_categories_json = Column(JSON, nullable=True)
    assets_liabilities_json = Column(JSON, nullable=True)
    auditor_name = Column(String, nullable=True)
    audit_date = Column(String, nullable=True)
    document_id = Column(String, ForeignKey("financial_documents.document_id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    party = relationship("PoliticalParty", foreign_keys=[party_id])
    document = relationship("FinancialDocument", back_populates="statements")

    __table_args__ = (
        UniqueConstraint('party_id', 'financial_year', name='uq_party_financial_statement'),
    )


class ElectionExpenditure(Base):
    """
    Party election campaign expenditure statement details.
    """
    __tablename__ = "election_expenditures"

    expenditure_id = Column(String, primary_key=True, index=True)
    party_id = Column(String, ForeignKey("political_parties.party_id", ondelete="CASCADE"), nullable=False, index=True)
    election_name = Column(String, nullable=False, index=True)
    reporting_period = Column(String, nullable=False)
    expenditure_categories_json = Column(JSON, nullable=True)
    reported_totals = Column(Float, nullable=True)
    document_id = Column(String, ForeignKey("financial_documents.document_id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    party = relationship("PoliticalParty", foreign_keys=[party_id])
    document = relationship("FinancialDocument", back_populates="expenditures")

    __table_args__ = (
        UniqueConstraint('party_id', 'election_name', name='uq_party_election_expenditure'),
    )


class FinancialMetric(Base):
    """
    Precomputed statistical metrics per party per financial year.
    """
    __tablename__ = "financial_metrics"

    metric_id = Column(String, primary_key=True, index=True)
    party_id = Column(String, ForeignKey("political_parties.party_id", ondelete="CASCADE"), nullable=False, index=True)
    financial_year = Column(String, nullable=False, index=True)
    gini_coefficient = Column(Float, nullable=True)
    hhi_index = Column(Float, nullable=True)
    disclosed_donor_ratio = Column(Float, nullable=True)
    unknown_source_ratio = Column(Float, nullable=True)
    yoy_income_growth = Column(Float, nullable=True)
    surplus_ratio = Column(Float, nullable=True)
    metrics_json = Column(JSON, nullable=True)
    computed_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    party = relationship("PoliticalParty", foreign_keys=[party_id])

    __table_args__ = (
        UniqueConstraint('party_id', 'financial_year', name='uq_party_financial_metric'),
    )


class ValidationIssue(Base):
    """
    Auditable data quality issue flagged during document processing or validation.
    """
    __tablename__ = "funding_validation_issues"

    issue_id = Column(String, primary_key=True, index=True)
    rule_code = Column(String, nullable=False, index=True)
    severity = Column(String, nullable=False, index=True)
    entity_type = Column(String, nullable=False)
    entity_id = Column(String, nullable=False, index=True)
    document_id = Column(String, ForeignKey("financial_documents.document_id", ondelete="CASCADE"), nullable=True)
    field_name = Column(String, nullable=True)
    description = Column(Text, nullable=False)
    raw_value = Column(Text, nullable=True)
    suggested_action = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    document = relationship("FinancialDocument", back_populates="validation_issues")
