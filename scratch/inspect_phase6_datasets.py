import zipfile
import csv
import io
import os
import hashlib

ds1_path = "E:/CIVCLENS/data/raw/phase6/Phase_6_DS_1.zip"
ds2_path = "E:/CIVCLENS/data/raw/phase6/Phase_6_DS_2.csv"

print("--- FILE INTEGRITY & CHECKSUMS ---")
for p in [ds1_path, ds2_path]:
    if os.path.exists(p):
        with open(p, "rb") as f:
            data = f.read()
        sha256 = hashlib.sha256(data).hexdigest()
        print(f"File: {p}")
        print(f"  Size: {len(data)} bytes")
        print(f"  SHA-256: {sha256}")

print("\n--- PHASE 6 DS 1 INVENTORY ANALYSIS ---")
with zipfile.ZipFile(ds1_path) as z:
    content = z.read("master_dataset_inventory.csv").decode("utf-8")
    reader = csv.DictReader(io.StringIO(content))
    rows = list(reader)
    print(f"Total Rows: {len(rows)}")
    print(f"Fields: {reader.fieldnames}")
    status_counts = {}
    for r in rows:
        st = r.get("download_status", "UNKNOWN")
        status_counts[st] = status_counts.get(st, 0) + 1
    print(f"Download Status Counts: {status_counts}")
    print("\nAll Dataset Inventory Rows:")
    for r in rows:
        print(f"  [{r.get('dataset_id')}] {r.get('dataset_name')} | Scope: {r.get('geographic_scope')} | Status: {r.get('download_status')} | URL: {r.get('source_url')}")

print("\n--- PHASE 6 DS 2 CSV ANALYSIS ---")
with open(ds2_path, "r", encoding="utf-8") as f:
    reader2 = csv.DictReader(f)
    rows2 = list(reader2)
    print(f"Total Rows: {len(rows2)}")
    print(f"Fields: {reader2.fieldnames}")
    status_counts2 = {}
    for r in rows2:
        st = r.get("download_status", "UNKNOWN")
        status_counts2[st] = status_counts2.get(st, 0) + 1
    print(f"Download Status Counts: {status_counts2}")
    print("\nAll Phase 6 DS 2 Rows:")
    for r in rows2:
        print(f"  [{r.get('dataset_id')}] {r.get('dataset_name')} | Status: {r.get('download_status')} | Scope: {r.get('geographic_scope')} | URL: {r.get('source_url')}")
