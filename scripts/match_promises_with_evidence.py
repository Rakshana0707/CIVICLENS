"""
Batch script to match Political Promises with candidate Evidence records.

Pipeline:
Promises -> Candidate Retrieval Engine -> Multi-Signal Matching (Semantic, Keywords, Entities, Dept, Time, Scheme Link) -> PromiseEvidenceLink Records
"""
import logging
from backend.database.session import SessionLocal
from backend.nlp.promise_evidence_matcher import PromiseEvidenceMatcher

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def main():
    db = SessionLocal()
    try:
        matcher = PromiseEvidenceMatcher(db_session=db)
        summary = matcher.match_all_promises_with_evidence()
        logger.info(f"Promise-to-Evidence candidate retrieval complete: {summary}")
    except Exception as e:
        logger.error(f"Error executing promise-to-evidence matching: {e}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
