import os
import json
import logging
import dataclasses
from backend.ingestion.readers import ManifestoPDFReader

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    manifest_path = "data/raw/manifestos/manifest.json"
    processed_dir = "data/processed/manifestos"
    
    os.makedirs(processed_dir, exist_ok=True)
    
    if not os.path.exists(manifest_path):
        logger.error(f"Manifest file not found: {manifest_path}")
        return
        
    with open(manifest_path, 'r', encoding='utf-8') as f:
        manifest = json.load(f)
        
    reader = ManifestoPDFReader()
    
    for item in manifest:
        local_path = item.get("local_storage_path")
        
        if not local_path or not os.path.exists(local_path):
            logger.info(f"Skipping {item.get('party')} {item.get('election_year')}: File not present locally.")
            continue
            
        party = item.get("party", "Unknown_Party")
        year = item.get("election_year", "Unknown_Year")
        language = item.get("language", "Unknown")
        # generate a simple ID
        manifesto_id = f"{year}_{party.replace(' ', '_')}"
        
        logger.info(f"Extracting manifesto: {manifesto_id} from {local_path}")
        
        segments = []
        for segment in reader.extract_segments(local_path, manifesto_id, language=language):
            segments.append(dataclasses.asdict(segment))
            
        if segments:
            # Create output dir
            out_dir = os.path.join(processed_dir, str(year), party.replace(" ", "_"))
            os.makedirs(out_dir, exist_ok=True)
            
            out_file = os.path.join(out_dir, "extracted_segments.jsonl")
            with open(out_file, 'w', encoding='utf-8') as out_f:
                for seg in segments:
                    out_f.write(json.dumps(seg, ensure_ascii=False) + "\n")
                    
            logger.info(f"Extracted {len(segments)} segments to {out_file}")
            
            # Update extraction_status
            item["extraction_status"] = "extracted"
        else:
            logger.warning(f"No text extracted for {manifesto_id}")
            item["extraction_status"] = "failed_extraction"
            
    with open(manifest_path, 'w', encoding='utf-8') as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)
        
    logger.info("Extraction process completed.")

if __name__ == "__main__":
    main()
