import os
import json
import collections
from backend.nlp.promise_extraction import PromiseExtractor, PromiseClassification
from backend.nlp.promise_normalization import PromiseNormalizationService

processed_dir = r"e:\CIVCLENS\data\processed\manifestos"
manifest_path = r"e:\CIVCLENS\data\raw\manifestos\manifest.json"

with open(manifest_path, "r", encoding="utf-8") as f:
    manifest = json.load(f)

extractor = PromiseExtractor()
normalizer = PromiseNormalizationService()

total_candidates = 0
counts_by_class = collections.Counter()
records_by_party = collections.Counter()
records_by_year = collections.Counter()
records_by_lang = collections.Counter()
records_by_cat = collections.Counter()

accepted_records = []

for item in manifest["files"]:
    file_id = item["file_id"]
    doc_path = os.path.join(processed_dir, f"{file_id}.json")
    if not os.path.exists(doc_path):
        continue

    with open(doc_path, "r", encoding="utf-8") as f:
        doc = json.load(f)

    party = item.get("party") or "Archive / Multi-Party"
    year = str(item.get("election_year") or "Archive")
    manifesto_id = f"MF-{party}-{year}"

    segments = []
    for p in doc.get("pages", []):
        txt = p.get("text", "")
        if len(txt.strip()) < 10:
            continue
        segments.append({
            "manifesto_id": manifesto_id,
            "document_id": doc["document_id"],
            "source_file_id": file_id,
            "page_number": p.get("page_number"),
            "section": p.get("section"),
            "original_text": txt,
            "language": doc.get("language", "Unknown"),
            "OCR_used": doc.get("ocr_used", False),
            "extraction_confidence": 1.0
        })

    extracted = extractor.extract(segments)
    total_candidates += len(extracted)

    for rec in extracted:
        cls_val = rec.classification.value if hasattr(rec.classification, "value") else rec.classification
        counts_by_class[cls_val] += 1

        if cls_val in ["specific_promise", "general_policy"]:
            norm = normalizer.normalize_promise(rec)
            accepted_records.append({
                "record": rec,
                "norm": norm,
                "party": party,
                "year": year
            })

            records_by_party[party] += 1
            records_by_year[year] += 1
            records_by_lang[rec.language] += 1
            records_by_cat[norm.primary_category] += 1

print(f"Total Candidate Statements Extracted: {total_candidates:,}")
print(f"Accepted Promises & Policies: {len(accepted_records):,}")
print("\nClassification Counts:")
for k, v in counts_by_class.most_common():
    print(f"  {k:<20}: {v:,}")

print("\nAccepted Promises by Party:")
for k, v in records_by_party.most_common():
    print(f"  {k:<25}: {v:,}")

print("\nAccepted Promises by Year:")
for k, v in sorted(records_by_year.items()):
    print(f"  {k:<15}: {v:,}")

print("\nAccepted Promises by Language:")
for k, v in records_by_lang.most_common():
    print(f"  {k:<15}: {v:,}")

print("\nAccepted Promises by Category:")
for k, v in records_by_cat.most_common():
    print(f"  {k:<20}: {v:,}")
