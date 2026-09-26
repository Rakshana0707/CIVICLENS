import abc
import os
import pandas as pd
import logging

logger = logging.getLogger(__name__)

class BaseBudgetReader(abc.ABC):
    """Abstract base class for reading raw budget documents."""
    
    @abc.abstractmethod
    def extract_records(self, file_path: str):
        """Extracts and yields raw rows as dictionaries from the file."""
        pass

class PDFBudgetReader(BaseBudgetReader):
    """Format-specific reader for Demands for Grants PDFs."""
    
    def extract_records(self, file_path: str):
        try:
            import pdfplumber
        except ImportError:
            logger.error("pdfplumber not installed. Cannot read PDF.")
            return

        logger.info(f"Extracting tables from PDF: {file_path}")
        try:
            with pdfplumber.open(file_path) as pdf:
                for page_num, page in enumerate(pdf.pages):
                    tables = page.extract_tables()
                    for table in tables:
                        if not table:
                            continue
                        df = pd.DataFrame(table)
                        df.dropna(how='all', inplace=True)
                        df.dropna(axis=1, how='all', inplace=True)
                        if df.empty:
                            continue
                        
                        # Yield each row as a dict
                        for _, row in df.iterrows():
                            # We just yield raw rows with source page tracking.
                            # Actual mapping logic will happen in the ingestor.
                            raw_dict = row.to_dict()
                            raw_dict['_source_page_number'] = page_num + 1
                            yield raw_dict
        except Exception as e:
            logger.error(f"Failed to extract from PDF {file_path}: {e}")

class CSVBudgetReader(BaseBudgetReader):
    """Format-specific reader for CSV fixtures or open data portal downloads."""
    
    def extract_records(self, file_path: str):
        logger.info(f"Extracting data from CSV: {file_path}")
        try:
            df = pd.read_csv(file_path)
            for _, row in df.iterrows():
                raw_dict = row.to_dict()
                raw_dict['_source_page_number'] = None
                yield raw_dict
        except Exception as e:
            logger.error(f"Failed to read CSV {file_path}: {e}")

def get_reader_for_format(file_format: str) -> BaseBudgetReader:
    if file_format.upper() == "PDF":
        return PDFBudgetReader()
    elif file_format.upper() == "CSV":
        return CSVBudgetReader()
    else:
        raise ValueError(f"Unsupported format: {file_format}")
