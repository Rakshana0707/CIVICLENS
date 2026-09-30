import os, sys, json
sys.path.insert(0, os.path.abspath('.'))
from backend.ingestion.readers import PDFBudgetReader

reader = PDFBudgetReader()
# Pick a small file from 2026-27
pdf_path = 'data/raw/budget/2026-2027/DemandBook_39-2.pdf'

records = []
try:
    for r in reader.extract_records(pdf_path):
        records.append(r)
except Exception as e:
    print(e)

# Just show top 5 extracted rows
for r in records[:5]:
    print(r)
