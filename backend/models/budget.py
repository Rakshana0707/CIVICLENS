from sqlalchemy import Column, String, Integer, Float, Enum, DateTime, ForeignKey, UniqueConstraint, JSON
from sqlalchemy.orm import relationship
import enum
from backend.database.base_class import Base
from datetime import datetime

class BudgetStage(str, enum.Enum):
    budget_estimate = "budget_estimate"
    revised_estimate = "revised_estimate"
    actual_expenditure = "actual_expenditure"

class BudgetDepartment(Base):
    """
    Represents a government department for budget allocations.
    """
    __tablename__ = 'budget_departments'

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, unique=True, index=True)
    code = Column(String, nullable=True, index=True)  # E.g., Demand Number

    # Relationships
    schemes = relationship("BudgetScheme", back_populates="department")


class BudgetScheme(Base):
    """
    Represents a specific scheme or budget line item under a department.
    """
    __tablename__ = 'budget_schemes'

    id = Column(Integer, primary_key=True, index=True)
    department_id = Column(Integer, ForeignKey('budget_departments.id'), nullable=False)
    name = Column(String, nullable=False, index=True)
    
    # Not all records have a scheme-level identifier (head of account)
    head_of_account = Column(String, nullable=True, index=True)
    normalized_category = Column(String, nullable=True)

    # Relationships
    department = relationship("BudgetDepartment", back_populates="schemes")
    records = relationship("BudgetRecord", back_populates="scheme")

    __table_args__ = (
        UniqueConstraint('department_id', 'name', 'head_of_account', name='uq_budget_scheme'),
    )


class BudgetSourceDocument(Base):
    """
    Tracks the specific budget document (e.g., DDG PDF) a record came from.
    """
    __tablename__ = 'budget_source_documents'

    id = Column(Integer, primary_key=True, index=True)
    manifest_dataset_id = Column(String, unique=True, nullable=False, index=True)
    title = Column(String, nullable=False)
    official_source_url = Column(String, nullable=True)
    financial_year_coverage = Column(String, nullable=True)
    checksum = Column(String, nullable=True)
    
    # Relationships
    records = relationship("BudgetRecord", back_populates="source_document")


class BudgetImportBatch(Base):
    """
    Tracks an ingestion batch run for auditing.
    """
    __tablename__ = 'budget_import_batches'

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)
    status = Column(String, nullable=False, default="SUCCESS")
    records_added = Column(Integer, default=0)
    records_skipped = Column(Integer, default=0)
    notes = Column(String, nullable=True)

    # Relationships
    records = relationship("BudgetRecord", back_populates="import_batch")


class BudgetRecord(Base):
    """
    The transactional record for a specific budget allocation or expenditure.
    Multiple stages (BE, RE, Actuals) and years exist for the same scheme.
    """
    __tablename__ = 'budget_records'

    id = Column(Integer, primary_key=True, index=True)
    
    scheme_id = Column(Integer, ForeignKey('budget_schemes.id'), nullable=False)
    source_document_id = Column(Integer, ForeignKey('budget_source_documents.id'), nullable=False)
    import_batch_id = Column(Integer, ForeignKey('budget_import_batches.id'), nullable=True)

    financial_year = Column(String, nullable=False, index=True)
    budget_stage = Column(Enum(BudgetStage), nullable=False, index=True)
    amount = Column(Float, nullable=True)
    currency_unit = Column(String, nullable=False, default="INR_Absolute")
    
    # Traceability
    source_page_number = Column(Integer, nullable=True)
    original_category_text = Column(String, nullable=True) # The exact text from the source
    source_metadata = Column(JSON, nullable=True) # Any other source-specific metadata

    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    scheme = relationship("BudgetScheme", back_populates="records")
    source_document = relationship("BudgetSourceDocument", back_populates="records")
    import_batch = relationship("BudgetImportBatch", back_populates="records")

    # Prevent duplicate records for the exact same entity, year, stage, and source
    __table_args__ = (
        UniqueConstraint('scheme_id', 'financial_year', 'budget_stage', 'source_document_id', name='uq_budget_record_entry'),
    )

class SchemeCategory(Base):
    __tablename__ = 'scheme_categories'
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, unique=True, index=True)
    description = Column(String, nullable=True)

class HistoricalScheme(Base):
    """
    Phase 2: Represents qualitative intelligence for a historical scheme (versions by year).
    """
    __tablename__ = 'historical_schemes'

    id = Column(Integer, primary_key=True, index=True)
    original_source_identifier = Column(String, nullable=True) # e.g. from original system
    budget_scheme_id = Column(Integer, ForeignKey('budget_schemes.id'), nullable=True, index=True)
    department_id = Column(Integer, ForeignKey('budget_departments.id'), nullable=False, index=True)
    category_id = Column(Integer, ForeignKey('scheme_categories.id'), nullable=True, index=True)
    
    financial_year = Column(String, nullable=False, index=True)
    scheme_name = Column(String, nullable=False)
    description = Column(String, nullable=True)
    objectives = Column(String, nullable=True)
    target_beneficiaries = Column(String, nullable=True)
    sector_category = Column(String, nullable=True) # Legacy string field
    
    # Future embedding storage
    embedding = Column(JSON, nullable=True) # Storing vector as JSON array for DB agnosticism
    
    # Matching metadata
    is_uncertain_match = Column(Integer, default=0) # 0 False, 1 True
    match_confidence = Column(Float, nullable=True)
    
    # Constraints
    __table_args__ = (
        UniqueConstraint('scheme_name', 'department_id', 'financial_year', name='uq_historical_scheme'),
    )

    budget_scheme = relationship("BudgetScheme", foreign_keys=[budget_scheme_id])
    department = relationship("BudgetDepartment", foreign_keys=[department_id])
    category = relationship("SchemeCategory", foreign_keys=[category_id])
    sources = relationship("SchemeSourceRelationship", back_populates="historical_scheme")

class SchemeSourceRelationship(Base):
    """
    Maps a historical scheme to its source documents (many-to-many/one-to-many).
    """
    __tablename__ = 'scheme_source_relationships'
    
    id = Column(Integer, primary_key=True, index=True)
    historical_scheme_id = Column(Integer, ForeignKey('historical_schemes.id'), nullable=False, index=True)
    source_document_id = Column(Integer, ForeignKey('budget_source_documents.id'), nullable=False, index=True)
    source_page_number = Column(Integer, nullable=True)
    extracted_text = Column(String, nullable=True)
    
    __table_args__ = (
        UniqueConstraint('historical_scheme_id', 'source_document_id', name='uq_scheme_source_rel'),
    )
    
    historical_scheme = relationship("HistoricalScheme", back_populates="sources")
    source_document = relationship("BudgetSourceDocument", foreign_keys=[source_document_id])

class SchemeSimilarity(Base):
    """
    Stores pre-computed or cached similarity results between historical schemes.
    """
    __tablename__ = 'scheme_similarities'
    
    id = Column(Integer, primary_key=True, index=True)
    source_scheme_id = Column(Integer, ForeignKey('historical_schemes.id'), nullable=False, index=True)
    target_scheme_id = Column(Integer, ForeignKey('historical_schemes.id'), nullable=False, index=True)
    similarity_score = Column(Float, nullable=False, index=True)
    explanation = Column(String, nullable=True)
    model_version = Column(String, nullable=True)
    
    __table_args__ = (
        UniqueConstraint('source_scheme_id', 'target_scheme_id', 'model_version', name='uq_scheme_similarity'),
    )
    
    source_scheme = relationship("HistoricalScheme", foreign_keys=[source_scheme_id])
    target_scheme = relationship("HistoricalScheme", foreign_keys=[target_scheme_id])
