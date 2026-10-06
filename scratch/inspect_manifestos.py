import os
import json
import hashlib
import docx
import pypdf

base_dir = r"e:\CIVCLENS\data\raw\manifestos\real_manifestos_20261006"

doc_inventory = []

for root, dirs, files in os.walk(base_dir):
    for f in sorted(files):
        if f in ["dataset_registration.json", "manifest.json"]:
            continue
        full_path = os.path.join(root, f)
        rel_path = os.path.relpath(full_path, base_dir).replace("\\", "/")
        ext = os.path.splitext(f)[1].lower()

        # SHA-256
        fh = hashlib.sha256()
        with open(full_path, "rb") as fp:
            while chunk := fp.read(8192 * 1024):
                fh.update(chunk)
        file_sha256 = fh.hexdigest()

        info = {
            "filename": f,
            "rel_path": rel_path,
            "ext": ext,
            "size_bytes": os.path.getsize(full_path),
            "sha256": file_sha256,
            "page_count": None,
            "has_direct_text": False,
            "requires_ocr": False,
            "sample_text": ""
        }

        if ext == ".pdf":
            try:
                reader = pypdf.PdfReader(full_path)
                info["page_count"] = len(reader.pages)
                extracted_text = ""
                for p in reader.pages[:5]:
                    t = p.extract_text() or ""
                    extracted_text += t + " "
                cleaned_text = extracted_text.strip()
                info["sample_text"] = cleaned_text[:150].replace("\n", " ")
                info["has_direct_text"] = len(cleaned_text) > 30
                info["requires_ocr"] = len(cleaned_text) <= 30
            except Exception as e:
                info["sample_text"] = f"PDF Read Error: {e}"
                info["requires_ocr"] = True
        elif ext == ".docx":
            try:
                d = docx.Document(full_path)
                info["page_count"] = len(d.paragraphs)
                text = " ".join([p.text for p in d.paragraphs if p.text])
                cleaned_text = text.strip()
                info["sample_text"] = cleaned_text[:150].replace("\n", " ")
                info["has_direct_text"] = len(cleaned_text) > 30
                info["requires_ocr"] = len(cleaned_text) <= 30
            except Exception as e:
                info["sample_text"] = f"DOCX Read Error: {e}"
                info["requires_ocr"] = True

        doc_inventory.append(info)

out_file = r"e:\CIVCLENS\scratch\inventory_summary.json"
with open(out_file, "w", encoding="utf-8") as fp:
    json.dump(doc_inventory, fp, indent=2, ensure_ascii=False)

print(f"Inspected {len(doc_inventory)} documents successfully.")
print(f"Direct text: {sum(1 for d in doc_inventory if d['has_direct_text'])}")
print(f"Requires OCR / Image extraction: {sum(1 for d in doc_inventory if d['requires_ocr'])}")
