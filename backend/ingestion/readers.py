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
            import re
        except ImportError:
            logger.error("pdfplumber not installed. Cannot read PDF.")
            return

        logger.info(f"Extracting lines from PDF: {file_path}")
        
        # Regex to match budget lines like:
        # Charged 8,26  36,02 28,42 20,90 2011 02 101 AA 30100
        # Voted   100   ...   100   100   2011 02 101 AA 30100
        line_pattern = re.compile(r'(Charged|Voted)\s+([\d,\.]+|-|\.\.\.)\s+([\d,\.]+|-|\.\.\.)\s+([\d,\.]+|-|\.\.\.)\s+([\d,\.]+|-|\.\.\.)\s+([\d\sA-Z]+)$')
        
        # To track current context
        current_scheme = ""

        try:
            with pdfplumber.open(file_path) as pdf:
                for page_num, page in enumerate(pdf.pages):
                    text = page.extract_text(layout=True)
                    if not text:
                        continue
                    
                    for line in text.split('\n'):
                        line_clean = line.strip()
                        
                        # Extract scheme name contexts if line ends without numbers and doesn't look like Tamil garbage
                        # E.g. "101 Legislative Assembly"
                        if len(line_clean) > 3 and not line_pattern.search(line_clean) and not "" in line_clean:
                            # A simple heuristic: if it contains english words, we update context
                            if re.search(r'[A-Za-z]', line_clean):
                                # Just take the right-most part (usually English)
                                eng_part = re.split(r'\s{3,}', line_clean)[-1].strip()
                                if eng_part:
                                    current_scheme = eng_part
                        
                        match = line_pattern.search(line_clean)
                        if match:
                            voted_charged = match.group(1)
                            actuals = match.group(2)
                            budget_est_t_minus_1 = match.group(3)
                            revised_est_t_minus_1 = match.group(4)
                            budget_est_t = match.group(5)
                            dp_code = match.group(6).strip()
                            
                            # Clean amounts (e.g. replace ... with None)
                            def parse_amt(v):
                                v = v.replace(',', '').strip()
                                return v if v not in ['...', '-'] else None

                            raw_dict = {
                                'scheme_name': current_scheme,
                                'voted_charged': voted_charged,
                                'actuals': parse_amt(actuals),
                                'budget_estimate_prev': parse_amt(budget_est_t_minus_1),
                                'revised_estimate': parse_amt(revised_est_t_minus_1),
                                'budget_estimate': parse_amt(budget_est_t),
                                'head_of_account': dp_code,
                                '_source_page_number': page_num + 1
                            }
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
