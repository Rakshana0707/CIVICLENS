import os, sys
sys.path.insert(0, os.path.abspath('.'))
from backend.ingestion.budget_ingestor import run_ingestion
from backend.database.session import engine
from backend.database.base import Base
Base.metadata.create_all(bind=engine)
run_ingestion()
