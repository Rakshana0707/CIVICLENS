"""
CLI script to acquire government implementation evidence documents.

Pipeline:
Promise / Query URL -> Allowed Source Domains -> Web Acquisition -> Candidate Documents -> Extraction -> Evidence Records
"""
import logging
import sys
from backend.database.session import SessionLocal
from backend.acquisition.evidence_pipeline import EvidenceAcquisitionPipeline

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def main():
    target_urls = sys.argv[1:] if len(sys.argv) > 1 else [
        "https://cms.tn.gov.in/sites/default/files/go/sw_e_2021.pdf",
        "https://httpbin.org/get"  # TEST_FIXTURE endpoint in allowed_domains
    ]

    db = SessionLocal()
    try:
        pipeline = EvidenceAcquisitionPipeline(db_session=db)
        for url in target_urls:
            logger.info(f"Processing target evidence URL: {url}")
            records = pipeline.fetch_and_extract_evidence(url=url, result_id="BATCH_RUN_001")
            logger.info(f"  Extracted {len(records)} evidence items from {url}")
    except Exception as e:
        logger.error(f"Evidence acquisition error: {e}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
