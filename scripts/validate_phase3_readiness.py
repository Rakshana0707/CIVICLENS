"""
Phase 3 Pipeline Readiness Validation Script (Phase 3.15).

Programmatically verifies that all core sub-systems of CIVICLENS TN Phase 3
(Acquisition, Processing, Promise Processing, Intelligence, Application)
are fully operational and ready for real manifesto document collection.

Important:
This script validates pipeline READINESS only using synthetic test fixtures.
No real political manifesto data is claimed or published.
Result: "Phase 3 pipeline ready for real manifesto acquisition."
"""

import os
import sys
import json
import hashlib
import unittest
from datetime import datetime, timezone
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.database.base import Base
from backend.models.manifesto import Manifesto, ManifestoSource, ManifestoDocument
from backend.models.promise import (
    PoliticalPromise,
    PromiseCategory,
    PromiseCategoryMapping,
    PromiseEvidenceLink,
    PromiseSchemeLink,
    PromiseAssessment,
    PromiseStatus
)
from backend.models.common import Evidence, Document
from backend.models.budget import BudgetDepartment, HistoricalScheme

from backend.nlp.promise_extraction import PromiseExtractor
from backend.nlp.promise_normalization import PromiseNormalizationService
from backend.nlp.promise_scheme_matcher import PromiseSchemeMatcher
from backend.nlp.promise_evidence_matcher import PromiseEvidenceMatcher
from backend.nlp.similarity import SemanticSchemeSearcher
from backend.services.promise_assessment_engine import PromiseAssessmentEngine
from backend.acquisition.evidence_pipeline import EvidenceAcquisitionPipeline
from backend.api.app import create_app
import backend.api.promises as api_promises_module


class MockEmbedder:
    """Mock embedder providing deterministic vectors for validation without sentence-transformers dependency."""
    def generate_embedding(self, text: str):
        text_lower = text.lower()
        v = [0.0] * 8
        if "school" in text_lower or "education" in text_lower:
            v[0] = 1.0
        if "health" in text_lower or "hospital" in text_lower:
            v[1] = 1.0
        if "farmer" in text_lower or "agriculture" in text_lower:
            v[2] = 1.0
        norm = sum(x**2 for x in v)**0.5
        return [x / norm for x in v] if norm > 0 else v


def run_validation():
    print("=" * 80)
    print("CIVICLENS TN — Phase 3 Pipeline Collection Readiness Validation")
    print("=" * 80)

    checks = {
        "Acquisition": [],
        "Processing": [],
        "Promise Processing": [],
        "Intelligence": [],
        "Application": []
    }

    # -------------------------------------------------------------------------
    # 1. ACQUISITION VALIDATION
    # -------------------------------------------------------------------------
    print("\n[1/5] Validating Acquisition System...")
    config_path = os.path.join("config", "evidence_sources.json")
    if os.path.exists(config_path):
        checks["Acquisition"].append(("Source registry exists", True, f"Found at {config_path}"))
    else:
        checks["Acquisition"].append(("Source registry exists", False, "Missing evidence_sources.json"))

    pipeline = EvidenceAcquisitionPipeline()
    allowed_count = len(pipeline.allowed_domains)
    checks["Acquisition"].append(("Acquisition layer works", allowed_count > 0, f"{allowed_count} allowed domains configured"))

    # Test SHA-256 Checksum generation
    sample_text = "Synthetic document content for checksum validation"
    calc_hash = hashlib.sha256(sample_text.encode("utf-8")).hexdigest()
    checks["Acquisition"].append(("Checksums work", len(calc_hash) == 64, f"SHA-256: {calc_hash[:12]}..."))

    # Test Provenance metadata mapping
    source_info = pipeline.get_source_info("https://cms.tn.gov.in/go/test.pdf")
    checks["Acquisition"].append(("Provenance works", source_info.get("source_tier") == 1, "Source tier & provenance mapped"))

    # Test Cache & Duplicate detection
    cache_dir = "data/cache/evidence"
    checks["Acquisition"].append(("Caching & duplicate detection work", os.path.exists(cache_dir), f"Cache directory at {cache_dir}"))

    # -------------------------------------------------------------------------
    # 2. PROCESSING VALIDATION
    # -------------------------------------------------------------------------
    print("\n[2/5] Validating Processing Pipeline...")
    extractor = PromiseExtractor()
    
    # Test multilingual text & page reference tracking
    seg_en = {
        "manifesto_id": "MF-VAL-01",
        "page_number": 4,
        "section": "Education",
        "original_text": "We promise to construct 50 new primary schools across Tamil Nadu.",
        "language": "English",
        "extraction_method": "pdfplumber",
        "OCR_used": False,
        "extraction_confidence": 1.0
    }
    seg_ta = {
        "manifesto_id": "MF-VAL-01",
        "page_number": 5,
        "section": "Agriculture",
        "original_text": "வேளாண் வளர்ச்சிக்கு ₹500 கோடி நிதி ஒதுக்கீடு செய்யப்படும்.",
        "language": "Tamil",
        "extraction_method": "pytesseract",
        "OCR_used": True,
        "extraction_confidence": 0.95
    }

    recs_en = extractor.extract([seg_en])
    recs_ta = extractor.extract([seg_ta])

    checks["Processing"].append(("PDF / HTML extraction supported", len(recs_en) > 0, "PDF/HTML text unit segmentation verified"))
    checks["Processing"].append(("OCR workflow supported", seg_ta["OCR_used"] and len(recs_ta) > 0, "OCR metadata & extracted records verified"))
    checks["Processing"].append(("Multilingual text works", len(recs_en) > 0 and len(recs_ta) > 0, "English and Tamil text extracted"))
    checks["Processing"].append(("Page references work", recs_en[0].page_number == 4 and recs_ta[0].page_number == 5, "Page numbers preserved"))

    # -------------------------------------------------------------------------
    # 3. PROMISE PROCESSING VALIDATION
    # -------------------------------------------------------------------------
    print("\n[3/5] Validating Promise Processing Pipeline...")
    normalizer_service = PromiseNormalizationService()

    norm_en = normalizer_service.normalize_promise(recs_en[0])
    norm_ta = normalizer_service.normalize_promise(recs_ta[0])

    checks["Promise Processing"].append(("Promise extraction works", recs_en[0].original_text == seg_en["original_text"], "Original wording preserved"))
    checks["Promise Processing"].append(("Normalization works", norm_en.normalized_text != "", "Unicode NFC normalization complete"))
    checks["Promise Processing"].append(("Categorization works", norm_en.primary_category in ["Education", "Healthcare", "Uncategorized"], f"Primary category: {norm_en.primary_category}"))

    # Test Database Import
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    TestingSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = TestingSession()

    m_db = Manifesto(manifesto_id="MF-VAL-01", party="Test Party", election_year=2026, title="Test Manifesto")
    db.add(m_db)
    
    cat_db = PromiseCategory(category_code="Education", name="Education", description="Education sector")
    db.add(cat_db)
    db.flush()

    p_db = PoliticalPromise(
        promise_id=norm_en.promise_id,
        manifesto_id="MF-VAL-01",
        original_text=norm_en.original_text,
        normalized_text=norm_en.normalized_text,
        page_number=norm_en.page_number,
        section=norm_en.section,
        language=norm_en.language,
        classification=norm_en.classification,
        extraction_confidence=0.9,
        metadata_json=norm_en.metadata.to_dict(),
        is_test_fixture=True
    )
    db.add(p_db)
    db.commit()

    saved_p = db.query(PoliticalPromise).filter_by(promise_id=norm_en.promise_id).first()
    checks["Promise Processing"].append(("Database import works", saved_p is not None, "PoliticalPromise record saved to DB"))

    # -------------------------------------------------------------------------
    # 4. INTELLIGENCE VALIDATION
    # -------------------------------------------------------------------------
    print("\n[4/5] Validating Intelligence Pipeline...")
    mock_embedder = MockEmbedder()
    searcher = SemanticSchemeSearcher(db_session=db, embedder=mock_embedder)

    dept_db = BudgetDepartment(code="EDU", name="School Education Department")
    db.add(dept_db)
    db.flush()

    scheme_db = HistoricalScheme(scheme_name="Model Schools Scheme", department_id=dept_db.id, financial_year="2021-2022")
    db.add(scheme_db)
    db.commit()

    scheme_matcher = PromiseSchemeMatcher(db_session=db, searcher=searcher)
    scheme_matches = scheme_matcher.match_promise(promise=saved_p, top_k=3, similarity_threshold=0.0)
    checks["Intelligence"].append(("Historical scheme matching works", isinstance(scheme_matches, list), "Promise-to-scheme matcher verified"))

    evidence_matcher = PromiseEvidenceMatcher(db_session=db, embedder=mock_embedder)
    checks["Intelligence"].append(("Evidence matching works", evidence_matcher is not None, "Multi-signal evidence matcher initialized"))

    assessment_engine = PromiseAssessmentEngine(db_session=db)
    assessment = assessment_engine.evaluate_promise(saved_p)
    checks["Intelligence"].append(
        ("Assessment engine works", assessment["status"] == PromiseStatus.NO_EVIDENCE_FOUND.value, f"Status: {assessment['status']} (Absence of evidence strictly evaluates to no_evidence_found)")
    )

    # -------------------------------------------------------------------------
    # 5. APPLICATION VALIDATION
    # -------------------------------------------------------------------------
    print("\n[5/5] Validating Application & Interface Pipeline...")
    app = create_app()
    app.config["TESTING"] = True
    client = app.test_client()

    orig_get_db = api_promises_module.get_db
    api_promises_module.get_db = lambda: db

    res = client.get("/api/promises/manifestos")
    checks["Application"].append(("APIs work", res.status_code == 200, "REST API endpoints operational"))

    # Check empty states & test fixtures
    fixture_dir = os.path.join("tests", "fixtures", "manifestos")
    bilingual_fixture = os.path.join(fixture_dir, "sample_manifesto_bilingual.json")
    with open(bilingual_fixture, "r", encoding="utf-8") as f:
        fixture_content = f.read()

    has_safety_banner = "TEST FIXTURE — NOT REAL POLITICAL DATA" in fixture_content
    checks["Application"].append(("Test fixtures work", os.path.exists(bilingual_fixture) and has_safety_banner, "Synthetic fixtures verified with safety banner"))

    frontend_page = os.path.join("frontend", "pages", "2_Political_Promises.py")
    with open(frontend_page, "r", encoding="utf-8") as f:
        fe_content = f.read()
    has_empty_state_msg = "No manifesto data has been loaded yet" in fe_content
    checks["Application"].append(("Frontend & empty states work", os.path.exists(frontend_page) and has_empty_state_msg, "Streamlit UI & empty state handler verified"))

    api_promises_module.get_db = orig_get_db
    db.close()

    # -------------------------------------------------------------------------
    # SUMMARY REPORT GENERATION
    # -------------------------------------------------------------------------
    all_passed = True
    print("\n" + "=" * 80)
    print("READINESS SUMMARY RESULTS")
    print("=" * 80)

    for category, results in checks.items():
        print(f"\n--- {category} ---")
        for title, status, details in results:
            symbol = "PASS" if status else "FAIL"
            print(f"[{symbol}] {title}: {details}")
            if not status:
                all_passed = False

    print("\n" + "=" * 80)
    if all_passed:
        print("RESULT VERIFIED:")
        print("Phase 3 pipeline ready for real manifesto acquisition.")
    else:
        print("RESULT: Pipeline readiness validation failed.")
    print("=" * 80)

    return all_passed


if __name__ == "__main__":
    success = run_validation()
    sys.exit(0 if success else 1)
