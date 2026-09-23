from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from backend.repositories.common import source_repo
from backend.models.common import Source

class SourceService:
    """
    Business logic for managing information Sources.
    """
    
    @staticmethod
    def create_source(db: Session, *, obj_in: Dict[str, Any]) -> Source:
        # Validate inputs
        if not obj_in.get("name"):
            raise ValueError("Source name is strictly required.")
            
        # Example of business logic: Normalize source types
        if obj_in.get("type"):
            obj_in["type"] = obj_in["type"].strip().capitalize()
            
        # Delegate persistence to the repository
        return source_repo.create(db, obj_in=obj_in)
        
    @staticmethod
    def get_source(db: Session, source_id: int) -> Optional[Source]:
        return source_repo.get(db, id=source_id)

    @staticmethod
    def list_sources(db: Session, skip: int = 0, limit: int = 100) -> List[Source]:
        return source_repo.get_multi(db, skip=skip, limit=limit)
