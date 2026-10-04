from datetime import datetime, timezone
from typing import Optional, Dict, Any
from dataclasses import dataclass, field

@dataclass
class AcquisitionMetadata:
    """
    Provenance and metadata for acquired documents.
    Maps to the Source Provenance Schema in docs/phase3/source_reliability.md.
    """
    url: str
    document_type: str  # HTML, PDF, CSV, API_JSON, etc.
    
    source_id: Optional[str] = None
    source_organization: Optional[str] = None
    source_title: Optional[str] = None
    source_type: Optional[str] = None
    source_tier: int = 5
    
    publication_date: Optional[datetime] = None
    collection_timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    financial_year: Optional[str] = None
    
    content_hash: Optional[str] = None
    http_status: Optional[int] = None
    extraction_method: Optional[str] = None
    
    original_filename: Optional[str] = None
    local_storage_path: Optional[str] = None
    license_notes: Optional[str] = None
    retrieval_status: str = "pending" # pending, success, failed, rate_limited
    
    additional_metadata: Dict[str, Any] = field(default_factory=dict)
