import json
import logging
import os
import uuid
from typing import List, Dict
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from backend.models.budget import BudgetRecord, BudgetStage, BudgetDepartment, BudgetScheme, BudgetSourceDocument, BudgetImportBatch
from backend.ingestion.models import RawBudgetRecord
from backend.ingestion.readers import get_reader_for_format
from backend.ingestion.validator import BudgetValidator
from backend.ingestion.cleaner import BudgetCleaner
from backend.database.session import SessionLocal

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

class BudgetIngestor:
    def __init__(self, db_session: Session, manifest_path: str, raw_dir: str):
        self.db = db_session
        self.manifest_path = manifest_path
        self.raw_dir = raw_dir
        self.validator = BudgetValidator()

    def _map_raw_to_canonical(self, raw_row: Dict, metadata: Dict) -> list:
        """
        Maps a raw extracted row to a list of Canonical BudgetRecords (one per budget stage).
        """
        records = []
        department_name = metadata.get('dataset_title', 'Unknown Department')
        scheme_name = raw_row.get('scheme_name') or 'Unknown Scheme'
        head_of_account = raw_row.get('head_of_account', '')
        financial_year = metadata.get('financial_year', '')
        
        # In our PDF reader, raw_row gives us actuals, revised_estimate, and budget_estimate natively!
        if raw_row.get('actuals'):
            try:
                amt = float(raw_row['actuals'])
                records.append(RawBudgetRecord(
                    record_id=str(uuid.uuid4()),
                    department_name=department_name,
                    scheme_name=scheme_name,
                    head_of_account=head_of_account,
                    original_category=str(raw_row),
                    financial_year=financial_year,
                    budget_stage=BudgetStage.actual_expenditure,
                    amount=amt,
                    currency_unit="INR_Thousands",
                    source_document_id=metadata.get('dataset_id', ''),
                    source_page_number=raw_row.get('_source_page_number')
                ))
            except ValueError:
                pass

        if raw_row.get('revised_estimate'):
            try:
                amt = float(raw_row['revised_estimate'])
                records.append(RawBudgetRecord(
                    record_id=str(uuid.uuid4()),
                    department_name=department_name,
                    scheme_name=scheme_name,
                    head_of_account=head_of_account,
                    original_category=str(raw_row),
                    financial_year=financial_year,
                    budget_stage=BudgetStage.revised_estimate,
                    amount=amt,
                    currency_unit="INR_Thousands",
                    source_document_id=metadata.get('dataset_id', ''),
                    source_page_number=raw_row.get('_source_page_number')
                ))
            except ValueError:
                pass

        if raw_row.get('budget_estimate'):
            try:
                amt = float(raw_row['budget_estimate'])
                records.append(RawBudgetRecord(
                    record_id=str(uuid.uuid4()),
                    department_name=department_name,
                    scheme_name=scheme_name,
                    head_of_account=head_of_account,
                    original_category=str(raw_row),
                    financial_year=financial_year,
                    budget_stage=BudgetStage.budget_estimate,
                    amount=amt,
                    currency_unit="INR_Thousands",
                    source_document_id=metadata.get('dataset_id', ''),
                    source_page_number=raw_row.get('_source_page_number')
                ))
            except ValueError:
                pass

        return records

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
            logger.warning("Manifest contains no dataset entries.")
            return

        total_records_added = 0
        total_records_skipped = 0

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
            
            logger.info(f"Extracting dataset {ds.get('dataset_id')}...")
            batch = []
            for raw_row in reader.extract_records(file_path):
                records = self._map_raw_to_canonical(raw_row, ds)
                batch.extend(records)
                
            logger.info(f"Validating {len(batch)} records...")
            valid, invalid, val_report = self.validator.validate_batch(batch)
            
            logger.info(f"Validation Report for {ds.get('dataset_id')}: {json.dumps(val_report, indent=2)}")
            if invalid:
                logger.warning(f"Found {len(invalid)} invalid records. Sample rejection reasons: {list(val_report['rejection_reasons'].keys())[:3]}")

            logger.info(f"Cleaning {len(valid)} valid records...")
            cleaner = BudgetCleaner()
            cleaned, unresolved, clean_report = cleaner.clean_batch(valid)
            
            logger.info(f"Cleaning Report for {ds.get('dataset_id')}: {json.dumps(clean_report, indent=2)}")
            if unresolved:
                logger.warning(f"Found {len(unresolved)} unresolved records after cleaning.")

            # DB Insertion for Normalized Schema
            added, skipped = 0, 0
            
            # 1. Ensure Source Document exists
            doc = self.db.query(BudgetSourceDocument).filter_by(manifest_dataset_id=ds.get('dataset_id')).first()
            if not doc:
                doc = BudgetSourceDocument(
                    manifest_dataset_id=ds.get('dataset_id', ''),
                    title=ds.get('dataset_title', ''),
                    financial_year_coverage=ds.get('financial_year', '')
                )
                self.db.add(doc)
                self.db.commit()

            # 2. Get or Create Batch
            batch = BudgetImportBatch(notes=f"Ingesting {ds.get('dataset_id')}")
            self.db.add(batch)
            self.db.commit()

            for raw_record in cleaned:
                # 3. Get or Create Department
                dept = self.db.query(BudgetDepartment).filter_by(name=raw_record.department_name).first()
                if not dept:
                    dept = BudgetDepartment(name=raw_record.department_name)
                    self.db.add(dept)
                    self.db.commit()

                # 4. Get or Create Scheme
                scheme = self.db.query(BudgetScheme).filter_by(
                    department_id=dept.id, 
                    name=raw_record.scheme_name,
                    head_of_account=raw_record.head_of_account
                ).first()
                if not scheme:
                    scheme = BudgetScheme(
                        department_id=dept.id,
                        name=raw_record.scheme_name,
                        head_of_account=raw_record.head_of_account
                    )
                    self.db.add(scheme)
                    self.db.commit()

                # 5. Insert Record
                record = BudgetRecord(
                    scheme_id=scheme.id,
                    source_document_id=doc.id,
                    import_batch_id=batch.id,
                    financial_year=raw_record.financial_year,
                    budget_stage=raw_record.budget_stage,
                    amount=raw_record.amount,
                    currency_unit=raw_record.currency_unit,
                    source_page_number=raw_record.source_page_number,
                    original_category_text=raw_record.original_category
                )
                
                self.db.add(record)
                try:
                    self.db.commit()
                    added += 1
                except IntegrityError:
                    self.db.rollback()
                    skipped += 1
            
            batch.records_added = added
            batch.records_skipped = skipped
            self.db.commit()

            
            logger.info(f"Dataset {ds.get('dataset_id')} -> Inserted: {added}, Duplicates Skipped: {skipped}")
            total_records_added += added
            total_records_skipped += skipped
                    
        logger.info(f"Total Ingestion Complete. Inserted: {total_records_added}, Skipped (Duplicates): {total_records_skipped}")

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
