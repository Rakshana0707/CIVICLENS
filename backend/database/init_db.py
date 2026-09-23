from backend.database.base import Base
from backend.database.session import engine

def init_db() -> None:
    """
    Initialize the database by creating all tables.
    In a real production environment, this is usually managed by Alembic migrations,
    but this is a helpful fallback for local testing and initial setup.
    """
    Base.metadata.create_all(bind=engine)
