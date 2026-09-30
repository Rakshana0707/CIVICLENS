import os, sys
sys.path.insert(0, os.path.abspath('.'))
import json
from backend.ingestion.budget_ingestor import BudgetIngestor
from backend.database.session import SessionLocal, engine
from backend.database.base import Base

Base.metadata.create_all(bind=engine)
db = SessionLocal()

manifest = {'datasets': [{
    'dataset_id': 'TN_BUDGET_2019_d01',
    'dataset_title': 'Demand 1 State Legislature (2019)',
    'financial_year': '2019-20',
    'original_filename': '2019-2020/2019-2020/2019-2020_d01.pdf',
    'file_format': 'pdf',
    'collection_status': 'verified'
}]}
manifest_path = 'data/raw/budget/mini_manifest.json'
with open(manifest_path, 'w') as f:
    json.dump(manifest, f)

ingestor = BudgetIngestor(db, manifest_path, 'data/raw/budget')
ingestor.ingest()
