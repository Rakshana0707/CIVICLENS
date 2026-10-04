import os
import json
import logging
import hashlib
import time
from backend.acquisition.http_client import PoliteHTTPClient

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("data/raw/manifestos/acquisition.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def get_safe_name(name):
    return "".join([c if c.isalnum() else "_" for c in str(name)])

def main():
    manifest_path = "data/raw/manifestos/manifest.json"
    base_dir = "data/raw/manifestos"
    
    os.makedirs(base_dir, exist_ok=True)
    
    with open(manifest_path, 'r', encoding='utf-8') as f:
        manifest = json.load(f)
        
    client = PoliteHTTPClient(cache_dir="data/cache")
    
    updated_manifest = []
    
    for item in manifest:
        url = item.get("source_url")
        if not url:
            updated_manifest.append(item)
            continue
            
        logger.info(f"Processing {url}")
        
        # Check if already successfully downloaded
        if item.get("retrieval_status") == "success" and item.get("local_storage_path"):
            if os.path.exists(item["local_storage_path"]):
                logger.info(f"Already downloaded: {item['local_storage_path']}")
                updated_manifest.append(item)
                continue
        
        content, metadata = client.fetch(url)
        
        item["retrieval_status"] = metadata.retrieval_status
        item["collection_timestamp"] = metadata.collection_date.isoformat()
        item["retrieval_method"] = "PoliteHTTPClient_GET"
        
        if content and metadata.retrieval_status == "success":
            party = item.get("party", "Unknown_Party")
            year = item.get("election_year", "Unknown_Year")
            
            # Extract short name for party (e.g. DMK from "Dravida Munnetra Kazhagam (DMK)")
            if "(" in party and ")" in party:
                short_party = party.split("(")[1].split(")")[0].strip()
            else:
                short_party = get_safe_name(party)
            
            dir_path = os.path.join(base_dir, str(year), short_party)
            os.makedirs(dir_path, exist_ok=True)
            
            filename = metadata.original_filename or f"manifesto_{int(time.time())}.pdf"
            local_path = os.path.join(dir_path, filename)
            
            with open(local_path, 'wb') as f:
                f.write(content)
                
            item["local_storage_path"] = local_path.replace("\\", "/")
            item["content_hash"] = metadata.content_hash
            item["original_filename"] = metadata.original_filename
            item["file_size_bytes"] = len(content)
            item["extraction_status"] = "pending"
            item["document_format"] = metadata.document_format
            
            logger.info(f"Successfully downloaded to {local_path}")
        else:
            if metadata.retrieval_status in ("failed_http_403", "failed_http_404", "failed_network"):
                item["retrieval_status"] = "manual_acquisition_required"
            logger.error(f"Failed to download {url}: {metadata.retrieval_status}")
            
        updated_manifest.append(item)
        
    with open(manifest_path, 'w', encoding='utf-8') as f:
        json.dump(updated_manifest, f, indent=2, ensure_ascii=False)
        
    logger.info("Manifesto download process completed.")

if __name__ == "__main__":
    main()
