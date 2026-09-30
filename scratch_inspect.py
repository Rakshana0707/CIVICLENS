import sys
try:
    import pdfplumber
    has_pdfplumber = True
except ImportError:
    has_pdfplumber = False

if has_pdfplumber:
    print("pdfplumber found")
    paths = [
        r"E:\CIVCLENS\data\raw\schemes\2023-2024\Appendix_Budget_Speech.pdf",
        r"E:\CIVCLENS\data\raw\schemes\2023-2024\Policy_Note_School_Ed.pdf"
    ]
    for path in paths:
        try:
            with pdfplumber.open(path) as pdf:
                print(f"\n--- {path} ---")
                print(f"Pages: {len(pdf.pages)}")
                first_page = pdf.pages[0].extract_text()
                print("First page snippet:")
                print(first_page[:500] if first_page else "NO TEXT EXTRACTED")
        except Exception as e:
            print(f"Error reading {path}: {e}")
else:
    print("pdfplumber not found")
