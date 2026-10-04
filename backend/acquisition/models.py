from datetime import datetime, timezone
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field

class AcquisitionMetadata(BaseModel):
    """
    Provenance and metadata for acquired documents.
    Maps to the Source Provenance Schema in docs/phase3/source_reliability.md.
    """
    source_id: Optional[str] = None
    url: str
    source_organization: Optional[str] = None
    source_title: Optional[str] = None
    source_type: Optional[str] = None
    source_tier: int = Field(default=5, ge=1, le=5)
    
    publication_date: Optional[datetime] = None
    collection_timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    document_type: str  # HTML, PDF, CSV, API_JSON, etc.
    financial_year: Optional[str] = None
    
    content_hash: Optional[str] = None
    http_status: Optional[int] = None
    extraction_method: Optional[str] = None
    
    original_filename: Optional[str] = None
    local_storage_path: Optional[str] = None
    license_notes: Optional[str] = None
    retrieval_status: str = "pending" # pending, success, failed, rate_limited
    
    additional_metadata: Dict[str, Any] = Field(default_factory=dict)
