import os, json
manifest_path = 'data/raw/budget/manifest.json'
with open(manifest_path, 'r') as f:
    manifest = json.load(f)

existing_files = {ds['original_filename'] for ds in manifest['datasets']}

for folder, year in [('2025-2026', '2025-26'), ('2026-2027', '2026-27')]:
    folder_path = os.path.join('data/raw/budget', folder)
    if os.path.exists(folder_path):
        for f in os.listdir(folder_path):
            if f.endswith('.pdf'):
                rel_path = f'{folder}/{f}'
                if rel_path not in existing_files:
                    entry = {
                        'dataset_id': f"TN_BUDGET_{year.replace('-', '_')}_{f.replace('.pdf','')}",
                        'dataset_title': f"{f} ({year})",
                        'financial_year': year,
                        'original_filename': rel_path,
                        'file_format': 'pdf',
                        'collection_status': 'verified'
                    }
                    manifest['datasets'].append(entry)

with open(manifest_path, 'w') as f:
    json.dump(manifest, f, indent=2)
print('Manifest updated.')
