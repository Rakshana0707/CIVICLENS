import os
import json
import logging
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

def main():
    manifest_path = "data/raw/manifestos/manifest.json"
    download_dir = "data/raw/manifestos"
    
    os.makedirs(download_dir, exist_ok=True)
    
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
        item["http_status"] = metadata.http_status
        item["collection_timestamp"] = metadata.collection_timestamp.isoformat()
        
        if content and metadata.retrieval_status == "success":
            # Avoid filename collisions
            safe_org = "".join([c if c.isalnum() else "_" for c in item.get("organization", "org")])
            safe_year = "".join([c if c.isalnum() else "_" for c in item.get("election_year", "year")])
            filename = f"{safe_org}_{safe_year}_{metadata.original_filename}"
            local_path = os.path.join(download_dir, filename)
            
            with open(local_path, 'wb') as f:
                f.write(content)
                
            item["local_storage_path"] = local_path
            item["content_hash"] = metadata.content_hash
            item["original_filename"] = metadata.original_filename
            logger.info(f"Successfully downloaded to {local_path}")
        else:
            logger.error(f"Failed to download {url}: {metadata.retrieval_status}")
            
        updated_manifest.append(item)
        
    with open(manifest_path, 'w', encoding='utf-8') as f:
        json.dump(updated_manifest, f, indent=2, ensure_ascii=False)
        
    logger.info("Manifesto download process completed.")

if __name__ == "__main__":
    main()
