from sqlalchemy import text
from backend.database.session import SessionLocal, engine
from backend.database.base_class import Base

def test_database_connection():
    """
    Test that we can connect to the database and execute a basic query.
    Acts as a health check for the database layer.
    """
    # Ensure tables are created (currently none exist)
    Base.metadata.create_all(bind=engine)
    
    db = SessionLocal()
    try:
        # Execute a simple health check query
        result = db.execute(text("SELECT 1")).scalar()
        assert result == 1
    finally:
        db.close()
