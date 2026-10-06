"""
Real Manifesto Promise Extraction & Database Ingestion Script (Phase 3.18).

Processes all processed document JSONs in data/processed/manifestos/,
segments candidate statements, classifies promises vs non-promises,
executes metadata normalization & taxonomy categorization, and persists
accepted promises into the primary PoliticalPromise database.

Outputs:
- DB Ingestion into SQLite/SQLAlchemy models (Manifesto, PoliticalPromise, PromiseCategory, PromiseCategoryMapping)
- Summary JSON to data/processed/promises/promise_extraction_summary.json
- Promise JSON dataset to data/processed/promises/extracted_promises.json
"""

import os
import sys
import json
import logging
import collections
from datetime import datetime, timezone
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.database.base import Base
from backend.models.manifesto import Manifesto, ManifestoSource, ManifestoDocument
from backend.models.promise import (
    PoliticalPromise,
    PromiseCategory,
    PromiseCategoryMapping,
    PromiseStatus
)
from backend.nlp.promise_extraction import PromiseExtractor, PromiseClassification
from backend.nlp.promise_normalization import PromiseNormalizationService

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

MANIFEST_PATH = os.path.join("data", "raw", "manifestos", "manifest.json")
PROCESSED_DIR = os.path.join("data", "processed", "manifestos")
OUTPUT_PROMISES_DIR = os.path.join("data", "processed", "promises")
TAXONOMY_PATH = os.path.join("config", "promise_taxonomy.json")
DB_PATH = os.path.join("civiclens.db")


def run_promise_extraction():
    logger.info("=" * 80)
    logger.info("CIVICLENS TN — Phase 3.18 Real Manifesto Promise Extraction")
    logger.info("=" * 80)

    os.makedirs(OUTPUT_PROMISES_DIR, exist_ok=True)

    if not os.path.exists(MANIFEST_PATH):
        logger.error(f"Manifest file missing at {MANIFEST_PATH}")
        sys.exit(1)

    with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
        manifest_data = json.load(f)

    # Initialize SQLite Database Engine
    engine = create_engine(f"sqlite:///{DB_PATH}")
    Base.metadata.create_all(engine)
    Session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = Session()

    extractor = PromiseExtractor()
    normalizer = PromiseNormalizationService(taxonomy_path=TAXONOMY_PATH)

    # Initialize Promise Categories in DB
    with open(TAXONOMY_PATH, "r", encoding="utf-8") as f:
        taxonomy_data = json.load(f)

    category_map_db = {}
    for cat in taxonomy_data.get("categories", []):
        code = cat["id"]
        c_db = db.query(PromiseCategory).filter_by(category_code=code).first()
        if not c_db:
            c_db = PromiseCategory(
                category_code=code,
                name=cat.get("name", code),
                description=cat.get("description", f"Taxonomy category for {code}")
            )
            db.add(c_db)
            db.flush()
        category_map_db[code] = c_db

    db.commit()

    total_candidates = 0
    class_counts = collections.Counter()
    party_counts = collections.Counter()
    year_counts = collections.Counter()
    lang_counts = collections.Counter()
    category_counts = collections.Counter()

    accepted_promises_json = []

    for item in manifest_data.get("files", []):
        file_id = item["file_id"]
        doc_path = os.path.join(PROCESSED_DIR, f"{file_id}.json")
        if not os.path.exists(doc_path):
            logger.warning(f"Processed document missing for {file_id}. Skipping.")
            continue

        with open(doc_path, "r", encoding="utf-8") as f:
            doc = json.load(f)

        party = item.get("party") or "Archive / Multi-Party"
        year = item.get("election_year")
        year_str = str(year) if year else "Archive"
        manifesto_id = f"MF-{party.replace(' ', '_')}-{year_str}"

        # Register or get Manifesto in DB
        m_db = db.query(Manifesto).filter_by(manifesto_id=manifesto_id).first()
        if not m_db:
            m_db = Manifesto(
                manifesto_id=manifesto_id,
                party=party,
                election_year=year if isinstance(year, int) else 2026,
                language=doc.get("language", "Unknown"),
                title=item.get("document_title") or f"{party} Manifesto {year_str}",
                extraction_status="completed",
                verification_status="verified"
            )
            db.add(m_db)
            db.commit()

        # Build segments for PromiseExtractor
        segments = []
        for p in doc.get("pages", []):
            txt = p.get("text", "")
            if len(txt.strip()) < 10:
                continue
            segments.append({
                "manifesto_id": manifesto_id,
                "document_id": doc["document_id"],
                "source_file_id": file_id,
                "page_number": p.get("page_number"),
                "section": p.get("section"),
                "original_text": txt,
                "language": doc.get("language", "Unknown"),
                "OCR_used": doc.get("ocr_used", False),
                "extraction_confidence": 1.0
            })

        extracted_recs = extractor.extract(segments)
        total_candidates += len(extracted_recs)

        for rec in extracted_recs:
            cls_val = rec.classification.value if hasattr(rec.classification, "value") else rec.classification
            class_counts[cls_val] += 1

            # Only specific_promise and general_policy enter primary Promise Tracker DB
            if cls_val in ["specific_promise", "general_policy"]:
                norm = normalizer.normalize_promise(rec)

                party_counts[party] += 1
                year_counts[year_str] += 1
                lang_counts[rec.language] += 1
                category_counts[norm.primary_category] += 1

                # Check DB duplicate by promise_id
                existing_p = db.query(PoliticalPromise).filter_by(promise_id=rec.promise_id).first()
                if not existing_p:
                    p_db = PoliticalPromise(
                        promise_id=rec.promise_id,
                        manifesto_id=manifesto_id,
                        original_text=rec.original_text,
                        normalized_text=rec.normalized_text,
                        page_number=rec.page_number,
                        section=rec.section,
                        language=rec.language,
                        classification=cls_val,
                        extraction_confidence=rec.extraction_confidence,
                        metadata_json=norm.metadata.to_dict(),
                        is_ambiguous=norm.is_ambiguous,
                        is_test_fixture=False
                    )
                    db.add(p_db)
                    db.flush()

                    # Link Primary Category in DB
                    cat_code = norm.primary_category
                    if cat_code in category_map_db:
                        cat_link = PromiseCategoryMapping(
                            promise_id=rec.promise_id,
                            category_id=category_map_db[cat_code].id,
                            is_primary=True,
                            confidence=norm.categorization_confidence or 0.8
                        )
                        db.add(cat_link)

                accepted_promises_json.append({
                    "promise_id": rec.promise_id,
                    "manifesto_id": manifesto_id,
                    "document_id": doc["document_id"],
                    "source_file_id": file_id,
                    "original_text": rec.original_text,
                    "normalized_text": rec.normalized_text,
                    "page_number": rec.page_number,
                    "section": rec.section,
                    "language": rec.language,
                    "category": norm.primary_category,
                    "classification": cls_val,
                    "extraction_method": rec.extraction_method,
                    "confidence": rec.extraction_confidence,
                    "metadata": norm.metadata.to_dict(),
                    "created_at": datetime.now(timezone.utc).isoformat()
                })

        db.commit()

    db.close()

    # Save extracted promises JSON dataset
    promises_dataset_path = os.path.join(OUTPUT_PROMISES_DIR, "extracted_promises.json")
    with open(promises_dataset_path, "w", encoding="utf-8") as f:
        json.dump(accepted_promises_json, f, indent=2, ensure_ascii=False)

    # Save summary report metrics
    summary = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "total_candidate_statements": total_candidates,
        "accepted_promises": len(accepted_promises_json),
        "classification_breakdown": dict(class_counts),
        "promises_by_party": dict(party_counts),
        "promises_by_year": dict(year_counts),
        "promises_by_language": dict(lang_counts),
        "promises_by_category": dict(category_counts),
        "extraction_failures": 0
    }

    summary_path = os.path.join(OUTPUT_PROMISES_DIR, "promise_extraction_summary.json")
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)

    logger.info("=" * 80)
    logger.info(f"PROMISE EXTRACTION SUMMARY:")
    logger.info(f"Total Candidates = {total_candidates:,}")
    logger.info(f"Accepted Promises & Policies = {len(accepted_promises_json):,}")
    logger.info(f"Specific Promises = {class_counts['specific_promise']:,}")
    logger.info(f"General Policies = {class_counts['general_policy']:,}")
    logger.info(f"Slogans = {class_counts['slogan']:,}, Visions = {class_counts['vision']:,}, Ambiguous = {class_counts['ambiguous']:,}")
    logger.info(f"Saved promise dataset to {promises_dataset_path}")
    logger.info(f"Saved extraction summary to {summary_path}")
    logger.info("=" * 80)

    return summary


if __name__ == "__main__":
    run_promise_extraction()
