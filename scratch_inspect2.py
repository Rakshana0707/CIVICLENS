import sys
import io
import pdfplumber

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf8")

paths = [
    r"E:\CIVCLENS\data\raw\schemes\2023-2024\Appendix_Budget_Speech.pdf",
    r"E:\CIVCLENS\data\raw\schemes\2023-2024\Policy_Note_School_Ed.pdf"
]

with open(r"E:\CIVCLENS\scratch_out.txt", "w", encoding="utf-8") as out_f:
    for path in paths:
        try:
            with pdfplumber.open(path) as pdf:
                out_f.write(f"\n--- {path} ---\n")
                out_f.write(f"Pages: {len(pdf.pages)}\n")
                for p_num in [2, 10, 50]: # Look at pages 2, 10, 50
                    if p_num < len(pdf.pages):
                        page = pdf.pages[p_num]
                        text = page.extract_text()
                        out_f.write(f"Page {p_num} snippet:\n")
                        out_f.write((text[:500] if text else "NO TEXT EXTRACTED") + "\n")
        except Exception as e:
            out_f.write(f"Error reading {path}: {e}\n")
