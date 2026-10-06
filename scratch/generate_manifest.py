import os
import json
import hashlib

base_dir = r"e:\CIVCLENS\data\raw\manifestos\real_manifestos_20261006"
manifest_file = r"e:\CIVCLENS\data\raw\manifestos\manifest.json"

dataset_id = "DS-TN-MANIFESTOS-20261006"

# Explicit, factual metadata mappings based strictly on filenames and document content
metadata_rules = [
    {
        "pattern": "Tamil_Nadu_Manifesto_Archive_1996.pdf",
        "party": None,
        "election_year": 1996,
        "language": "English",
        "title": "Tamil Nadu Election Manifesto Archive 1996",
        "duplicate_classification": "unique"
    },
    {
        "pattern": "Tamil_Nadu_Manifesto_Archive_1996_2011_Master.pdf",
        "party": None,
        "election_year": None, # Multi-year 1996-2011
        "language": "English",
        "title": "Tamil Nadu Election Manifesto Archive 1996-2011 Master Index",
        "duplicate_classification": "different_version"
    },
    {
        "pattern": "Tamil_Nadu_Manifesto_Archive_2001.pdf",
        "party": None,
        "election_year": 2001,
        "language": "English",
        "title": "Tamil Nadu Election Manifesto Archive 2001",
        "duplicate_classification": "unique"
    },
    {
        "pattern": "Tamil_Nadu_Manifesto_Archive_2006.pdf",
        "party": None,
        "election_year": 2006,
        "language": "English",
        "title": "Tamil Nadu Election Manifesto Archive 2006",
        "duplicate_classification": "unique"
    },
    {
        "pattern": "Tamil_Nadu_Manifesto_Archive_2011.pdf",
        "party": None,
        "election_year": 2011,
        "language": "English",
        "title": "Tamil Nadu Election Manifesto Archive 2011",
        "duplicate_classification": "unique"
    },
    {
        "pattern": "ADMK-Therthal-Arikkai-2016-Tamil-PDF-Tamilnadu-Election-Manifesto-2016-Full-List.pdf",
        "party": "AIADMK",
        "election_year": 2016,
        "language": "Tamil",
        "title": "AIADMK Election Manifesto 2016 (Tamil)",
        "duplicate_classification": "unique"
    },
    {
        "pattern": "Manifesto-Synopsis_2824129a.pdf",
        "party": "PMK",
        "election_year": 2016,
        "language": "English",
        "title": "PMK Election Manifesto Synopsis 2016",
        "duplicate_classification": "unique"
    },
    {
        "pattern": "congress.docx",
        "party": "INC",
        "election_year": 2016,
        "language": "Tamil",
        "title": "Congress Election Manifesto 2016",
        "duplicate_classification": "unique"
    },
    {
        "pattern": "dmk2016Manifesto_E_2811452a.pdf",
        "party": "DMK",
        "election_year": 2016,
        "language": "English",
        "title": "DMK Election Manifesto 2016 (English)",
        "duplicate_classification": "unique"
    },
    {
        "pattern": "4-AIADMK Election Manifesto - 14.03.2021.pdf",
        "party": "AIADMK",
        "election_year": 2021,
        "language": "Tamil",
        "title": "AIADMK Election Manifesto 2021 (Tamil)",
        "duplicate_classification": "unique"
    },
    {
        "pattern": "501785333-DMK-Election-Manifesto-2021.pdf",
        "party": "DMK",
        "election_year": 2021,
        "language": "Tamil",
        "title": "DMK Election Manifesto 2021 (Tamil)",
        "duplicate_classification": "unique"
    },
    {
        "pattern": "MDMK Election Manifesto 2021.pdf",
        "party": "MDMK",
        "election_year": 2021,
        "language": "Tamil",
        "title": "MDMK Election Manifesto 2021",
        "duplicate_classification": "unique"
    },
    {
        "pattern": "MNM-MANIFESTO-DOCUMENT-19th mar 2021 (1).pdf",
        "party": "MNM",
        "election_year": 2021,
        "language": "Tamil",
        "title": "Makkal Needhi Maiam Manifesto Document 2021",
        "duplicate_classification": "unique"
    },
    {
        "pattern": "Tamil Nadu 2021 Assembly Election BJP Vision Document vTamil (1).pdf",
        "party": "BJP",
        "election_year": 2021,
        "language": "Tamil",
        "title": "BJP Vision Document 2021 (Tamil)",
        "duplicate_classification": "unique"
    },
    {
        "pattern": "DMK_Manifesto_English_2026.pdf",
        "party": "DMK",
        "election_year": 2026,
        "language": "English",
        "title": "DMK Election Manifesto 2026 (English)",
        "duplicate_classification": "unique"
    },
    {
        "pattern": "aiadmk-election-manifesto-assembly-general-election-2026.pdf",
        "party": "AIADMK",
        "election_year": 2026,
        "language": "Tamil",
        "title": "AIADMK Election Manifesto 2026 (Tamil)",
        "duplicate_classification": "different_version" # English version exists
    },
    {
        "pattern": "aiadmk-manifesto-2026-english.pdf",
        "party": "AIADMK",
        "election_year": 2026,
        "language": "English",
        "title": "AIADMK Election Manifesto 2026 (English)",
        "duplicate_classification": "different_version" # Tamil version exists
    },
    {
        "pattern": "ntk-2026-manifesto_compressed.pdf",
        "party": "NTK",
        "election_year": 2026,
        "language": "Tamil",
        "title": "Naam Tamilar Katchi Manifesto 2026",
        "duplicate_classification": "unique"
    },
    {
        "pattern": "tnbjp_manifesto_2026_compressed.pdf",
        "party": "BJP",
        "election_year": 2026,
        "language": "Tamil",
        "title": "TN BJP Election Manifesto 2026",
        "duplicate_classification": "unique"
    },
    {
        "pattern": "tvk_manifesto_2026_compressed.pdf",
        "party": "TVK",
        "election_year": 2026,
        "language": "Tamil",
        "title": "Tamilaga Vettri Kazhagam Manifesto 2026",
        "duplicate_classification": "unique"
    }
]

rule_by_filename = {r["pattern"]: r for r in metadata_rules}

manifest_records = []
file_counter = 1

for root, dirs, files in os.walk(base_dir):
    for f in sorted(files):
        if f in ["dataset_registration.json", "manifest.json"]:
            continue
        full_path = os.path.join(root, f)
        rel_path = os.path.relpath(full_path, base_dir).replace("\\", "/")
        ext = os.path.splitext(f)[1].lower()

        # Calculate SHA256
        fh = hashlib.sha256()
        with open(full_path, "rb") as fp:
            while chunk := fp.read(8192 * 1024):
                fh.update(chunk)
        file_sha256 = fh.hexdigest()

        meta = rule_by_filename.get(f, {})

        rec = {
            "dataset_id": dataset_id,
            "file_id": f"MANIFESTO-FILE-{file_counter:03d}",
            "original_filename": f,
            "relative_path": rel_path,
            "file_type": ext[1:] if ext.startswith(".") else ext,
            "size_bytes": os.path.getsize(full_path),
            "sha256": file_sha256,
            "party": meta.get("party"),
            "election_year": meta.get("election_year"),
            "language": meta.get("language"),
            "source_url": None, # Not provided in ZIP archive
            "document_title": meta.get("title"),
            "duplicate_classification": meta.get("duplicate_classification", "unique"),
            "requires_ocr": ext == ".pdf" and f in ["dmk2016Manifesto_E_2811452a.pdf", "501785333-DMK-Election-Manifesto-2021.pdf", "tvk_manifesto_2026_compressed.pdf"] or ext == ".docx",
            "collection_status": "registered",
            "processing_status": "pending_text_extraction"
        }
        manifest_records.append(rec)
        file_counter += 1

manifest_data = {
    "dataset_id": dataset_id,
    "manifest_version": "1.0.0",
    "total_files": len(manifest_records),
    "files": manifest_records
}

with open(manifest_file, "w", encoding="utf-8") as fp:
    json.dump(manifest_data, fp, indent=2, ensure_ascii=False)

print(f"Generated manifest with {len(manifest_records)} records.")
print(f"Manifest written to: {manifest_file}")
