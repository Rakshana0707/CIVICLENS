from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from backend.repositories.common import document_repo
from backend.models.common import Document

class DocumentService:
    """
    Business logic for processing and managing Documents.
    """

    @staticmethod
    def create_document(db: Session, *, obj_in: Dict[str, Any]) -> Document:
        # Basic validation
        if not obj_in.get("title") or not obj_in.get("content"):
            raise ValueError("Both Document 'title' and 'content' are required.")
            
        return document_repo.create(db, obj_in=obj_in)

    @staticmethod
    def get_document(db: Session, doc_id: int) -> Optional[Document]:
        return document_repo.get(db, id=doc_id)
        
    @staticmethod
    def list_documents(db: Session, skip: int = 0, limit: int = 100) -> List[Document]:
        return document_repo.get_multi(db, skip=skip, limit=limit)
