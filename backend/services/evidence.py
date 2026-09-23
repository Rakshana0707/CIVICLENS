from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from backend.repositories.common import evidence_repo
from backend.models.common import Evidence

class EvidenceService:
    """
    Business logic for handling Evidence extraction and recording.
    """

    @staticmethod
    def extract_and_record_evidence(
        db: Session, 
        *, 
        document_id: Optional[int] = None, 
        data_source_id: Optional[int] = None, 
        content: str, 
        context: Optional[str] = None
    ) -> Evidence:
        """
        Record a piece of extracted evidence for model explainability.
        """
        if not content or content.strip() == "":
            raise ValueError("Evidence content cannot be empty.")
            
        if not document_id and not data_source_id:
            raise ValueError("Evidence must be linked to either a document or a data source.")
            
        obj_in = {
            "content": content,
            "context": context
        }
        
        if document_id:
            obj_in["document_id"] = document_id
        if data_source_id:
            obj_in["data_source_id"] = data_source_id
            
        return evidence_repo.create(db, obj_in=obj_in)
