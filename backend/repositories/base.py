from typing import Any, Dict, Generic, List, Optional, Type, TypeVar
from sqlalchemy.orm import Session
from backend.database.base_class import Base

# Define a generic type variable bound to our SQLAlchemy Base
ModelType = TypeVar("ModelType", bound=Base)

class CRUDBase(Generic[ModelType]):
    """
    CRUD object with default methods to Create, Read, Update, Delete (CRUD).
    This abstracts away the database operations from the business logic layer.
    """
    def __init__(self, model: Type[ModelType]):
        """
        :param model: A SQLAlchemy model class
        """
        self.model = model

    def get(self, db: Session, id: Any) -> Optional[ModelType]:
        """Get a single record by its ID."""
        return db.get(self.model, id)

    def get_multi(self, db: Session, *, skip: int = 0, limit: int = 100) -> List[ModelType]:
        """List multiple records with optional pagination."""
        return db.query(self.model).offset(skip).limit(limit).all()

    def create(self, db: Session, *, obj_in: Dict[str, Any]) -> ModelType:
        """Create a new record from a dictionary of values."""
        db_obj = self.model(**obj_in)
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def update(self, db: Session, *, db_obj: ModelType, obj_in: Dict[str, Any]) -> ModelType:
        """Update an existing database record with a dictionary of values."""
        for field, value in obj_in.items():
            if hasattr(db_obj, field):
                setattr(db_obj, field, value)
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def remove(self, db: Session, *, id: Any) -> Optional[ModelType]:
        """Delete a record by its ID."""
        obj = db.get(self.model, id)
        if obj:
            db.delete(obj)
            db.commit()
        return obj
