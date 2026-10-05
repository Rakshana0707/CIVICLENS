"""
Batch script to match Political Promises with Phase 2 Historical Schemes.

Reads promises from database (or JSON fixtures if DB is empty),
calculates Sentence-BERT / Cosine Similarity embeddings against historical schemes,
and stores the resulting PromiseSchemeLink records in the database.
"""
import logging
import os
import json
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.database.base import Base
from backend.database.session import SessionLocal
from backend.models.promise import PoliticalPromise
from backend.models.manifesto import Manifesto
from backend.models.budget import HistoricalScheme, BudgetDepartment
from backend.nlp.promise_scheme_matcher import PromiseSchemeMatcher

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def main():
    db = SessionLocal()
    try:
        matcher = PromiseSchemeMatcher(db_session=db)
        summary = matcher.match_all_promises()
        logger.info(f"Promise-to-Scheme Matching complete summary: {summary}")
    except Exception as e:
        logger.error(f"Error executing promise-to-scheme matching: {e}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
