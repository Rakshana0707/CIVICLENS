import os
import json
import logging
from backend.acquisition.manager import AcquisitionManager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    test_manifest_path = "data/tests/test_manifest.json"
    test_storage_dir = "data/tests/raw/manifestos"
    
    os.makedirs(os.path.dirname(test_manifest_path), exist_ok=True)
    
    # Create test fixtures
    test_data = [
        {
            "manifesto_id": "TEST_FIXTURE_1",
            "party": "Test Party A",
            "election": "Test Election",
            "election_year": 2026,
            "source_url": "https://httpbin.org/get",
            "source_type": "primary",
            "source_tier": 1,
            "retrieval_status": "pending"
        },
        {
            "manifesto_id": "TEST_FIXTURE_2",
            "party": "Test Party B",
            "election": "Test Election",
            "election_year": 2026,
            "source_url": "https://httpbin.org/status/404",
            "source_type": "archive",
            "source_tier": 3,
            "retrieval_status": "pending"
        }
    ]
    
    with open(test_manifest_path, 'w', encoding='utf-8') as f:
        json.dump(test_data, f, indent=2)
        
    logger.info("Initializing AcquisitionManager for TEST_FIXTURES...")
    manager = AcquisitionManager(manifest_path=test_manifest_path, raw_storage_dir=test_storage_dir)
    
    logger.info("Running pipeline on test fixtures...")
    manager.run_pipeline()
    
    logger.info("Pipeline run complete. Verifying results...")
    
    with open(test_manifest_path, 'r', encoding='utf-8') as f:
        results = json.load(f)
        
    for res in results:
        logger.info(f"Fixture {res['manifesto_id']} -> Status: {res['retrieval_status']}")
        if res['retrieval_status'] == "collected":
            logger.info(f"   Stored at: {res['storage_path']}")
            logger.info(f"   Checksum: {res['checksum']}")

if __name__ == "__main__":
    main()
