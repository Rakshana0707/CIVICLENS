import enum
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Float
from sqlalchemy.orm import relationship
from backend.database.base_class import Base

class ManifestoSource(Base):
    """
    Source entity representing the exact provenance of a manifesto document.
    """
    __tablename__ = "manifesto_sources"
    
    source_id = Column(String, primary_key=True, index=True)
    organization = Column(String, nullable=True)
    source_url = Column(String, nullable=True)
    source_type = Column(String, nullable=True) # e.g., primary, archive, discovery_only
    source_tier = Column(Integer, nullable=True) # 1 to 5
    publication_date = Column(DateTime, nullable=True)
    collection_date = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    retrieval_method = Column(String, nullable=True)
    retrieval_status = Column(String, default="pending")
    content_hash = Column(String, nullable=True)
    checksum = Column(String, nullable=True)
    notes = Column(Text, nullable=True)
    
    # Relationships
    manifestos = relationship("Manifesto", back_populates="source")
    documents = relationship("ManifestoDocument", back_populates="source")


class ManifestoDocument(Base):
    """
    Document entity representing the physical/digital file of the manifesto.
    """
    __tablename__ = "manifesto_documents"
    
    document_id = Column(String, primary_key=True, index=True)
    source_id = Column(String, ForeignKey("manifesto_sources.source_id"), nullable=True)
    original_filename = Column(String, nullable=True)
    file_format = Column(String, nullable=True) # PDF, HTML
    file_size = Column(Integer, nullable=True) # bytes
    storage_path = Column(String, nullable=True)
    checksum = Column(String, nullable=True)
    page_count = Column(Integer, nullable=True)
    extraction_method = Column(String, nullable=True)
    extraction_status = Column(String, default="pending")
    
    # Relationships
    source = relationship("ManifestoSource", back_populates="documents")
    manifestos = relationship("Manifesto", back_populates="document")


class Manifesto(Base):
    """
    Manifesto entity representing the logical political manifesto.
    """
    __tablename__ = "manifestos"
    
    manifesto_id = Column(String, primary_key=True, index=True)
    party = Column(String, nullable=False, index=True)
    election = Column(String, nullable=True)
    election_year = Column(Integer, nullable=False, index=True)
    language = Column(String, nullable=True)
    title = Column(String, nullable=True)
    
    source_id = Column(String, ForeignKey("manifesto_sources.source_id"), nullable=True)
    document_id = Column(String, ForeignKey("manifesto_documents.document_id"), nullable=True)
    
    publication_date = Column(DateTime, nullable=True)
    collection_date = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    format = Column(String, nullable=True)
    extraction_status = Column(String, default="pending")
    verification_status = Column(String, default="pending")
    
    # Relationships
    source = relationship("ManifestoSource", back_populates="manifestos")
    document = relationship("ManifestoDocument", back_populates="manifestos")
