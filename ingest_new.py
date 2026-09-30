import os, sys, json
sys.path.insert(0, os.path.abspath('.'))
from backend.ingestion.budget_ingestor import BudgetIngestor
from backend.database.session import SessionLocal

manifest_path = 'data/raw/budget/manifest.json'
with open(manifest_path, 'r') as f:
    manifest = json.load(f)

# Filter only new years
manifest['datasets'] = [ds for ds in manifest['datasets'] if ds['financial_year'] in ['2025-26', '2026-27']]

temp_manifest = 'data/raw/budget/temp_manifest.json'
with open(temp_manifest, 'w') as f:
    json.dump(manifest, f)

db = SessionLocal()
ingestor = BudgetIngestor(db, temp_manifest, 'data/raw/budget')
ingestor.ingest()
