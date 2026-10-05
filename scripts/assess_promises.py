"""
Batch script to run Evidence-Based Promise Assessment Engine across all database promises.

Evaluates evidence links and updates PromiseAssessment and PromiseAssessmentHistory records.
"""
import logging
from backend.database.session import SessionLocal
from backend.services.promise_assessment_engine import PromiseAssessmentEngine

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def main():
    db = SessionLocal()
    try:
        engine = PromiseAssessmentEngine(db_session=db)
        summary = engine.evaluate_all_promises()
        logger.info(f"Promise assessment engine execution summary: {summary}")
    except Exception as e:
        logger.error(f"Error running promise assessment engine: {e}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
