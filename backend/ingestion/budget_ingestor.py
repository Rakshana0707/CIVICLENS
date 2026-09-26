import json
import logging
import os
import uuid
from typing import List, Dict
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from backend.models.budget import BudgetRecord, BudgetStage
from backend.ingestion.readers import get_reader_for_format
from backend.database.session import SessionLocal

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

class BudgetIngestor:
    def __init__(self, db_session: Session, manifest_path: str, raw_dir: str):
        self.db = db_session
        self.manifest_path = manifest_path
        self.raw_dir = raw_dir

    def _map_raw_to_canonical(self, raw_row: Dict, metadata: Dict) -> BudgetRecord:
        """
        Maps a raw extracted row to the Canonical BudgetRecord.
        If real data structure is unknown, applies a fallback heuristic.
        """
        # Convert all keys/values to string for safe heuristic checking
        safe_row = {str(k).lower(): str(v).strip() for k, v in raw_row.items() if not str(k).startswith('_')}
        
        # Heuristics based on provisional schema
        department_name = safe_row.get('department_name', metadata.get('dataset_title', 'Unknown Department'))
        scheme_name = safe_row.get('scheme_name') or safe_row.get('description') or safe_row.get('sub_head') or 'Unclassified Scheme'
        
        try:
            amount = float(safe_row.get('amount', safe_row.get('budget_estimate', 0)))
        except ValueError:
            amount = None

        # Determine stage heuristically
        stage = BudgetStage.budget_estimate
        if 'actuals' in safe_row or 'accounts' in safe_row:
            stage = BudgetStage.actual_expenditure
        elif 'revised_estimate' in safe_row:
            stage = BudgetStage.revised_estimate

        # Generate a deterministic ID based on unique constraint fields
        record_id = str(uuid.uuid4())

        return BudgetRecord(
            record_id=record_id,
            department_name=department_name,
            scheme_name=scheme_name,
            head_of_account=safe_row.get('head_of_account', 'Unknown'),
            original_category=str(raw_row), # Preserve exact original row payload
            financial_year=metadata.get('financial_year', 'Unknown'),
            budget_stage=stage,
            amount=amount,
            currency_unit="INR_Absolute",
            source_document_id=metadata.get('dataset_id', 'Unknown'),
            source_page_number=raw_row.get('_source_page_number')
        )

    def ingest(self):
        """Reads the manifest and ingests all verified/collected datasets."""
        logger.info(f"Starting ingestion from manifest: {self.manifest_path}")
        
        if not os.path.exists(self.manifest_path):
            logger.error("Manifest not found.")
            return

        with open(self.manifest_path, 'r') as f:
            manifest_data = json.load(f)

        datasets = manifest_data.get('datasets', [])
        if not datasets:
            logger.warning("Manifest contains no dataset entries. Are we still pending manual acquisition?")
            return

        records_added = 0
        records_skipped = 0

        for ds in datasets:
            status = ds.get('collection_status')
            if status not in ['collected', 'verified']:
                logger.info(f"Skipping {ds.get('dataset_id')} (Status: {status})")
                continue
            
            file_path = os.path.join(self.raw_dir, ds.get('original_filename', ''))
            if not os.path.exists(file_path):
                logger.error(f"File {file_path} marked as {status} but not found on disk.")
                continue

            try:
                reader = get_reader_for_format(ds.get('file_format', ''))
            except ValueError as e:
                logger.error(str(e))
                continue
            
            logger.info(f"Processing dataset {ds.get('dataset_id')}")
            for raw_row in reader.extract_records(file_path):
                record = self._map_raw_to_canonical(raw_row, ds)
                
                # Check for completeness based on strict rules
                if not record.department_name or not record.scheme_name:
                    logger.warning(f"Dropping incomplete record from {ds['dataset_id']}")
                    continue
                
                # Add to DB safely (idempotent insert)
                self.db.add(record)
                try:
                    self.db.commit()
                    records_added += 1
                except IntegrityError:
                    self.db.rollback()
                    records_skipped += 1
                    
        logger.info(f"Ingestion complete. Added: {records_added}, Skipped (Duplicates): {records_skipped}")

def run_ingestion():
    db = SessionLocal()
    try:
        manifest = os.path.join("data", "raw", "budget", "manifest.json")
        raw_dir = os.path.join("data", "raw", "budget")
        ingestor = BudgetIngestor(db, manifest, raw_dir)
        ingestor.ingest()
    finally:
        db.close()

if __name__ == "__main__":
    run_ingestion()
