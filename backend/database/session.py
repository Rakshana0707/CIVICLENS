from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from backend.core.config import config

# Add specific connect args for SQLite
connect_args = {}
if config.DATABASE_URL.startswith("sqlite"):
    connect_args["check_same_thread"] = False

# Create the SQLAlchemy engine
engine = create_engine(
    config.DATABASE_URL,
    connect_args=connect_args,
    # echo=config.DEBUG, # Can be enabled for detailed SQL logs
)

# Create a local session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    """
    Dependency that provides a database session and ensures it is safely closed.
    Use this to yield DB sessions in API endpoints or services.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
