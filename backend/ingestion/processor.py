import os
import logging
import mimetypes
from typing import Iterator, List
from backend.ingestion.models import ExtractedManifestoSegment

logger = logging.getLogger(__name__)

class DocumentProcessor:
    """
    Manifesto Document Processing Pipeline:
    Raw PDF/HTML -> File Validation -> Document Type Detection -> Text Extraction -> Page/Section Preservation -> OCR if necessary -> Extracted Document
    """
    
    def __init__(self, allow_mock: bool = False):
        # allow_mock enables the fake PDF extractor. TEST USE ONLY: it decodes raw
        # bytes as text and would produce garbage for a real PDF.
        self.allow_mock = allow_mock
        
    def _validate_file(self, file_path: str) -> bool:
        """Validates that the file exists and has size > 0."""
        if not os.path.exists(file_path):
            logger.error(f"Validation failed: File {file_path} does not exist.")
            return False
        if os.path.getsize(file_path) == 0:
            logger.error(f"Validation failed: File {file_path} is empty.")
            return False
        return True
        
    def _detect_document_type(self, file_path: str) -> str:
        """Detects the document type based on mime type and extension."""
        mime_type, _ = mimetypes.guess_type(file_path)
        if mime_type == 'application/pdf' or file_path.lower().endswith('.pdf'):
            return "PDF"
        elif mime_type in ('text/html', 'application/xhtml+xml') or file_path.lower().endswith('.html'):
            return "HTML"
        else:
            return "UNKNOWN"
            
    def _extract_pdf(self, file_path: str, manifesto_id: str, language: str) -> Iterator[ExtractedManifestoSegment]:
        """Routes to PDF reader logic, handling text and OCR."""
        # Real extraction needs pdfplumber. The mock is only used when allow_mock=True.
        try:
            import pdfplumber  # noqa: F401
        except ImportError:
            if not self.allow_mock:
                raise RuntimeError(
                    "pdfplumber is not installed; cannot extract PDF text. "
                    "Install it (pip install pdfplumber) before processing real manifestos."
                )
            logger.warning("pdfplumber not found. allow_mock=True: using MOCK PDF extractor (tests only).")
            yield from self._mock_pdf_extractor(file_path, manifesto_id, language)
            return
        from backend.ingestion.readers import ManifestoPDFReader
        yield from ManifestoPDFReader().extract_segments(file_path, manifesto_id, language)
            
    def _extract_html(self, file_path: str, manifesto_id: str, language: str) -> Iterator[ExtractedManifestoSegment]:
        """Routes to HTML reader logic."""
        # Simple HTML parser for architecture testing
        try:
            from html.parser import HTMLParser
            
            class SimpleHTMLParser(HTMLParser):
                def __init__(self):
                    super().__init__()
                    self.text_blocks = []
                    self.current_data = []
                    
                def handle_data(self, data):
                    if data.strip():
                        self.current_data.append(data.strip())
                        
                def handle_endtag(self, tag):
                    if tag in ('p', 'div', 'h1', 'h2', 'h3', 'li') and self.current_data:
                        self.text_blocks.append(" ".join(self.current_data))
                        self.current_data = []

            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            parser = SimpleHTMLParser()
            parser.feed(content)
            if parser.current_data:
                parser.text_blocks.append(" ".join(parser.current_data))
                
            for i, block in enumerate(parser.text_blocks):
                yield ExtractedManifestoSegment(
                    manifesto_id=manifesto_id,
                    page_number=1, # HTML is single page
                    section=None,
                    original_text=block,
                    language=language,
                    extraction_method="html_parser",
                    OCR_used=False
                )
        except Exception as e:
            logger.error(f"HTML extraction failed: {e}")

    def _mock_pdf_extractor(self, file_path: str, manifesto_id: str, language: str) -> Iterator[ExtractedManifestoSegment]:
        """Simulates PDF extraction including OCR detection for test fixtures."""
        with open(file_path, 'rb') as f:
            content = f.read().decode('utf-8', errors='ignore')
            
        is_scanned = "SCANNED_FIXTURE" in content
        ocr_used = is_scanned
        method = "tesseract_ocr_mock" if ocr_used else "pdfplumber_mock"
        
        paragraphs = [p for p in content.split('\n\n') if p.strip()]
        for i, p in enumerate(paragraphs):
            yield ExtractedManifestoSegment(
                manifesto_id=manifesto_id,
                page_number=1,
                section="Mock Section",
                original_text=p.strip(),
                language=language,
                extraction_method=method,
                OCR_used=ocr_used,
                extraction_confidence=0.85 if ocr_used else 1.0
            )

    def process(self, file_path: str, manifesto_id: str, language: str = "Unknown") -> List[ExtractedManifestoSegment]:
        """
        Main pipeline entrypoint.
        """
        logger.info(f"Starting processing pipeline for {file_path}")
        
        if not self._validate_file(file_path):
            return []
            
        doc_type = self._detect_document_type(file_path)
        logger.info(f"Detected document type: {doc_type}")
        
        segments = []
        if doc_type == "PDF":
            segments = list(self._extract_pdf(file_path, manifesto_id, language))
        elif doc_type == "HTML":
            segments = list(self._extract_html(file_path, manifesto_id, language))
        else:
            logger.error(f"Unsupported document type for {file_path}")
            return []
            
        logger.info(f"Pipeline completed. Extracted {len(segments)} segments. OCR used: {any(s.OCR_used for s in segments)}")
        return segments
