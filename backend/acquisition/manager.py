import os
import json
import logging
import hashlib
import time
from typing import List, Dict, Any
from .http_client import PoliteHTTPClient

logger = logging.getLogger(__name__)

class AcquisitionManager:
    """
    Manages the end-to-end acquisition pipeline for manifesto documents.
    Architecture: Source Registry -> Manager -> Retriever -> Validation -> Checksum -> Raw Storage -> Manifest Update
    """
    def __init__(self, manifest_path: str, raw_storage_dir: str):
        self.manifest_path = manifest_path
        self.raw_storage_dir = raw_storage_dir
        self.client = PoliteHTTPClient(cache_dir=os.path.join(raw_storage_dir, ".cache"))
        
        os.makedirs(self.raw_storage_dir, exist_ok=True)
        
    def _load_manifest(self) -> List[Dict[str, Any]]:
        if not os.path.exists(self.manifest_path):
            return []
        with open(self.manifest_path, 'r', encoding='utf-8') as f:
            return json.load(f)
            
    def _save_manifest(self, data: List[Dict[str, Any]]):
        with open(self.manifest_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
            
    def run_pipeline(self):
        """
        Executes the acquisition pipeline on pending or identified sources.
        """
        manifest = self._load_manifest()
        updated_manifest = []
        
        for item in manifest:
            url = item.get("source_url")
            status = item.get("retrieval_status", "pending")
            
            # Skip if already successfully acquired or flagged manual
            if status in ("collected", "success", "manual_acquisition_required"):
                updated_manifest.append(item)
                continue
                
            if not url:
                logger.warning(f"Source missing URL: {item.get('manifesto_id')}")
                updated_manifest.append(item)
                continue
                
            logger.info(f"Acquiring document from {url}")
            content, metadata = self.client.fetch(url)
            
            item["retrieval_method"] = "PoliteHTTPClient_GET"
            item["collection_timestamp"] = metadata.collection_date.isoformat()
            
            if content and metadata.retrieval_status == "success":
                # Validation (basic file format sanity check)
                is_valid = True
                if url.endswith('.pdf') and not content.startswith(b'%PDF'):
                    logger.warning(f"Failed validation: {url} did not return a valid PDF signature.")
                    is_valid = False
                    
                if is_valid:
                    # Checksum & Storage
                    safe_party = "".join([c if c.isalnum() else "_" for c in item.get("party", "Unknown")])
                    year = item.get("election_year", "Unknown")
                    
                    dir_path = os.path.join(self.raw_storage_dir, str(year), safe_party)
                    os.makedirs(dir_path, exist_ok=True)
                    
                    filename = metadata.original_filename or f"document_{int(time.time())}.bin"
                    local_path = os.path.join(dir_path, filename)
                    
                    with open(local_path, 'wb') as f:
                        f.write(content)
                        
                    item["retrieval_status"] = "collected"
                    item["storage_path"] = local_path.replace("\\", "/")
                    item["content_hash"] = metadata.content_hash
                    item["checksum"] = hashlib.sha256(content).hexdigest()
                    item["file_size"] = len(content)
                    item["document_format"] = metadata.document_format
                    logger.info(f"Successfully collected to {local_path}")
                else:
                    item["retrieval_status"] = "failed_validation"
            else:
                logger.error(f"Failed to fetch {url}: {metadata.retrieval_status}")
                if metadata.retrieval_status in ("failed_http_403", "failed_http_404", "failed_network"):
                    item["retrieval_status"] = "manual_acquisition_required"
                else:
                    item["retrieval_status"] = "failed"
                    
            updated_manifest.append(item)
            
        self._save_manifest(updated_manifest)
        logger.info("Acquisition pipeline run completed.")
