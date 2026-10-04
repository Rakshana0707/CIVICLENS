import os
import json
import logging
from dataclasses import asdict
from backend.ingestion.processor import DocumentProcessor

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_fixtures(fixture_dir: str):
    os.makedirs(fixture_dir, exist_ok=True)
    
    # 1. Normal PDF (English)
    normal_pdf = os.path.join(fixture_dir, "normal_english.pdf")
    with open(normal_pdf, 'wb') as f:
        # Mocking PDF content for the fallback mock reader
        f.write(b"This is a normal English manifesto promise.\n\nWe will build a new bridge.")

    # 2. Scanned PDF (Tamil)
    scanned_pdf = os.path.join(fixture_dir, "scanned_tamil.pdf")
    with open(scanned_pdf, 'wb') as f:
        f.write(b"SCANNED_FIXTURE\n\n\xe0\xae\xa8\xe0\xae\xbe\xe0\xae\x99\xe0\xaf\x8d\xe0\xae\x95\xe0\xae\xb3\xe0\xaf\x8d \xe0\xae\xaa\xe0\xaf\x81\xe0\xae\xa4\xe0\xae\xbf\xe0\xae\xaf \xe0\xae\xaa\xe0\xae\xbe\xe0\xae\xb2\xe0\xae\xae\xe0\xaf\x8d \xe0\xae\x95\xe0\xae\x9f\xe0\xaf\x8d\xe0\xae\x9f\xe0\xaf\x81\xe0\xae\xb5\xe0\xaf\x8b\xe0\xae\xae\xe0\xaf\x8d.")

    # 3. HTML (Mixed Tamil-English)
    html_file = os.path.join(fixture_dir, "mixed_language.html")
    with open(html_file, 'w', encoding='utf-8') as f:
        f.write("<html><body><h1>Education Policy</h1><p>We will provide free laptops. இலவச மடிக்கணினி வழங்கப்படும்.</p></body></html>")
        
    return [
        (normal_pdf, "manifesto_en_01", "English"),
        (scanned_pdf, "manifesto_ta_01", "Tamil"),
        (html_file, "manifesto_mixed_01", "Mixed")
    ]

def main():
    fixture_dir = "data/tests/fixtures/processing"
    fixtures = create_fixtures(fixture_dir)
    
    processor = DocumentProcessor(allow_mock=True)  # TEST_FIXTURE run only
    
    for file_path, manifesto_id, language in fixtures:
        logger.info(f"--- Testing {file_path} ---")
        segments = processor.process(file_path, manifesto_id, language=language)
        
        for i, seg in enumerate(segments):
            logger.info(f"Segment {i}:")
            logger.info(f"  Method: {seg.extraction_method}")
            logger.info(f"  OCR: {seg.OCR_used}")
            logger.info(f"  Language: {seg.language}")
            logger.info(f"  Original Text: {seg.original_text}")
        
        logger.info("-" * 40)

if __name__ == "__main__":
    main()
