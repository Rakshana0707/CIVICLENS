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
        
        line_pattern = re.compile(r'(Charged|Voted)\s+([\d,\.]+|-|\.\.\.)\s+([\d,\.]+|-|\.\.\.)\s+([\d,\.]+|-|\.\.\.)\s+([\d,\.]+|-|\.\.\.)\s+([\d\sA-Z]+)$')
        current_scheme = ""

        try:
            with pdfplumber.open(file_path) as pdf:
                for page_num, page in enumerate(pdf.pages):
                    text = page.extract_text(layout=True)
                    if not text:
                        continue
                    
                    for line in text.split('\n'):
                        line_clean = line.strip()
                        
                        if len(line_clean) > 3 and not line_pattern.search(line_clean) and not "" in line_clean:
                            if re.search(r'[A-Za-z]', line_clean):
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

class ManifestoPDFReader:
    """Reader specifically for extracting contiguous text blocks from Manifesto PDFs."""
    
    def extract_segments(self, file_path: str, manifesto_id: str, language: str = "Unknown"):
        from backend.ingestion.models import ExtractedManifestoSegment
        try:
            import pdfplumber
        except ImportError:
            logger.error("pdfplumber not installed. Cannot read PDF.")
            return

        logger.info(f"Extracting manifesto text from PDF: {file_path}")
        
        try:
            with pdfplumber.open(file_path) as pdf:
                current_section = None
                for page_num, page in enumerate(pdf.pages):
                    
                    # Basic extraction without OCR first
                    text = page.extract_text(layout=False)
                    ocr_used = False
                    confidence = 1.0
                    
                    # Fallback to OCR logic if empty (mock OCR logic for the architecture phase)
                    if not text or not text.strip():
                        # Imagine OCR using Tesseract here: text = pytesseract.image_to_string(page.to_image().original)
                        # We will just mark it as OCR_used = True, text = "[OCR output]" for this phase if it was implemented
                        text = ""
                        ocr_used = True
                        confidence = 0.5
                    
                    if not text.strip():
                        continue
                        
                    # Basic heuristic to identify paragraphs (split by double newline)
                    paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
                    
                    # If we don't have double newlines, try splitting by single newlines 
                    # but joining sentences intelligently (heuristic for layout=False)
                    if len(paragraphs) == 1 and len(paragraphs[0].split('\n')) > 1:
                        raw_lines = paragraphs[0].split('\n')
                        cleaned_paragraphs = []
                        current_p = []
                        for line in raw_lines:
                            line = line.strip()
                            if not line:
                                continue
                            # Heuristic for headers: all caps or short lines without punctuation
                            if (line.isupper() and len(line) < 50) or (len(line) < 40 and not line.endswith(('.', ',', ';', ':'))):
                                if current_p:
                                    cleaned_paragraphs.append(" ".join(current_p))
                                    current_p = []
                                current_section = line
                                continue
                            current_p.append(line)
                            
                        if current_p:
                            cleaned_paragraphs.append(" ".join(current_p))
                        paragraphs = cleaned_paragraphs

                    for p in paragraphs:
                        if not p: continue
                        
                        yield ExtractedManifestoSegment(
                            manifesto_id=manifesto_id,
                            page_number=page_num + 1,
                            section=current_section,
                            original_text=p,
                            normalized_text=None,
                            language=language,
                            extraction_method="pdfplumber_ocr" if ocr_used else "pdfplumber",
                            OCR_used=ocr_used,
                            extraction_confidence=confidence
                        )
                        
        except Exception as e:
            logger.error(f"Failed to extract from manifesto PDF {file_path}: {e}")
