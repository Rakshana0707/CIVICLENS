from sqlalchemy.orm import declarative_base, declared_attr

class CustomBase:
    """Base class for all SQLAlchemy declarative models."""
    
    @declared_attr
    def __tablename__(cls) -> str:
        # Automatically generate the table name from the class name
        return cls.__name__.lower()

# Create the declarative base instance
Base = declarative_base(cls=CustomBase)
