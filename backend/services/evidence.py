from typing import Dict, Any, Optional, List
from sqlalchemy.orm import Session
from backend.repositories.common import evidence_repo
from backend.models.common import Evidence

class EvidenceService:
    """
    Business logic for handling Evidence extraction, recording, and explainability tracking.
    """

    @staticmethod
    def create_evidence(
        db: Session, 
        *, 
        content: str, 
        document_id: Optional[int] = None, 
        data_source_id: Optional[int] = None, 
        context: Optional[str] = None,
        explanation: Optional[str] = None,
        supporting_values: Optional[Dict[str, Any]] = None,
        result_type: Optional[str] = None,
        result_id: Optional[str] = None,
        page_number: Optional[int] = None
    ) -> Evidence:
        """
        Record a piece of extracted evidence for model explainability.
        """
        if not content or content.strip() == "":
            raise ValueError("Evidence content cannot be empty.")
            
        obj_in = {
            "content": content,
            "context": context,
            "explanation": explanation,
            "supporting_values": supporting_values or {},
            "result_type": result_type,
            "result_id": result_id,
            "page_number": page_number
        }
        
        if document_id:
            obj_in["document_id"] = document_id
        if data_source_id:
            obj_in["data_source_id"] = data_source_id
            
        return evidence_repo.create(db, obj_in=obj_in)

    @staticmethod
    def get_evidence_for_result(db: Session, result_type: str, result_id: str) -> List[Evidence]:
        """
        Retrieve all evidence supporting a specific analysis result.
        """
        return db.query(Evidence).filter(
            Evidence.result_type == result_type,
            Evidence.result_id == result_id
        ).all()
