from datetime import datetime, timezone
from typing import Optional, Dict, Any
from dataclasses import dataclass, field

@dataclass
class SourceRecord:
    """
    Source Record model representing the provenance of an acquired document.
    """
    source_id: Optional[str] = None
    organization: Optional[str] = None
    party: Optional[str] = None
    election: Optional[str] = None
    election_year: Optional[str] = None
    source_url: Optional[str] = None
    source_type: Optional[str] = None
    source_tier: Optional[int] = None
    title: Optional[str] = None
    language: Optional[str] = None
    publication_date: Optional[datetime] = None
    collection_date: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    document_format: Optional[str] = None
    original_filename: Optional[str] = None
    checksum: Optional[str] = None
    content_hash: Optional[str] = None
    retrieval_method: Optional[str] = None
    retrieval_status: str = "pending"
    source_notes: Optional[str] = None

@dataclass
class ManifestoModel:
    """
    Manifesto Model representing a specific political manifesto.
    """
    manifesto_id: Optional[str] = None
    party: Optional[str] = None
    election: Optional[str] = None
    election_year: Optional[str] = None
    language: Optional[str] = None
    title: Optional[str] = None
    source_id: Optional[str] = None
    document_id: Optional[str] = None
    page_count: Optional[int] = None
    extraction_status: str = "pending"
