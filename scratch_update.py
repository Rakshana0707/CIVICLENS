import re

with open(r"E:\CIVCLENS\backend\models\budget.py", "r", encoding="utf-8") as f:
    content = f.read()

# We want to replace HistoricalScheme with a new version and add the new tables.
# Let's find where HistoricalScheme starts and remove it and everything after it.
match = re.search(r"class HistoricalScheme\(Base\):", content)
if match:
    content = content[:match.start()]

new_models = """class SchemeCategory(Base):
    __tablename__ = 'scheme_categories'
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, unique=True, index=True)
    description = Column(String, nullable=True)

class HistoricalScheme(Base):
    \"\"\"
    Phase 2: Represents qualitative intelligence for a historical scheme (versions by year).
    \"\"\"
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
    \"\"\"
    Maps a historical scheme to its source documents (many-to-many/one-to-many).
    \"\"\"
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
    \"\"\"
    Stores pre-computed or cached similarity results between historical schemes.
    \"\"\"
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
"""

content += new_models

with open(r"E:\CIVCLENS\backend\models\budget.py", "w", encoding="utf-8") as f:
    f.write(content)

print("Updated budget.py successfully.")
