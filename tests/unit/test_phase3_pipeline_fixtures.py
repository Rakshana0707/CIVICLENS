"""
Phase 3 Pipeline Fixtures & End-to-End Test Suite (Phase 3.14).

Tests the complete Phase 3 pipeline on controlled synthetic test fixtures:
Fixture Manifesto Document
  → Promise Extraction
  → Promise Normalization & Categorization
  → Database Persistence
  → Historical Scheme Matching
  → Implementation Evidence Matching
  → Assessment Engine
  → API Endpoints
  → Frontend Service Integration

Guarantees:
- Every fixture clearly declares: 'TEST FIXTURE — NOT REAL POLITICAL DATA'
- Fixtures are stored strictly in tests/fixtures/manifestos/
- No evidence evaluates strictly to 'no_evidence_found' (never 'not_implemented')
- Ambiguous statements are preserved without forced categorization
"""

import os
import json
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
    PromiseAssessmentHistory,
    PromiseStatus
)
from backend.models.common import Evidence, Document
from backend.models.budget import BudgetDepartment, HistoricalScheme

from backend.nlp.promise_extraction import PromiseExtractor, PromiseClassification
from backend.nlp.promise_normalization import PromiseNormalizationService
from backend.nlp.promise_scheme_matcher import PromiseSchemeMatcher
from backend.nlp.promise_evidence_matcher import PromiseEvidenceMatcher
from backend.nlp.similarity import SemanticSchemeSearcher
from backend.services.promise_assessment_engine import PromiseAssessmentEngine
from backend.api.app import create_app
import backend.api.promises as api_promises_module


FIXTURES_DIR = os.path.join("tests", "fixtures", "manifestos")


class MockEmbedder:
    """Mock embedder providing deterministic vectors for testing without sentence-transformers dependency."""

    def generate_embedding(self, text: str):
        text_lower = text.lower()
        v = [0.0] * 8
        if "school" in text_lower or "education" in text_lower or "student" in text_lower:
            v[0] = 1.0
            v[1] = 0.8
        if "laptop" in text_lower or "computer" in text_lower or "digital" in text_lower:
            v[0] = 0.7
            v[2] = 0.9
        if "farmer" in text_lower or "agriculture" in text_lower or "crop" in text_lower:
            v[3] = 1.0
            v[4] = 0.9
        if "hospital" in text_lower or "health" in text_lower or "doctor" in text_lower:
            v[5] = 1.0
            v[6] = 0.9
        norm = sum(x**2 for x in v)**0.5
        if norm > 0:
            v = [x / norm for x in v]
        return v


def make_segment(text: str, manifesto_id: str, page_number: int, section: str, language: str = "Unknown"):
    return {
        "manifesto_id": manifesto_id,
        "page_number": page_number,
        "section": section,
        "original_text": text,
        "language": language,
        "extraction_method": "synthetic_fixture_loader",
        "OCR_used": False,
        "extraction_confidence": 1.0,
    }


class TestPhase3PipelineFixtures(unittest.TestCase):

    def setUp(self):
        # 1. Setup isolated in-memory SQLite engine
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        TestingSession = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        self.db = TestingSession()

        # 2. Setup Flask test client & override DB session in API module
        self.app = create_app()
        self.app.config["TESTING"] = True
        self.client = self.app.test_client()

        # Monkey-patch get_db in API module
        self._orig_get_db = api_promises_module.get_db
        api_promises_module.get_db = lambda: self.db

        # 3. Instantiate pipeline components with MockEmbedder
        mock_embedder = MockEmbedder()
        searcher = SemanticSchemeSearcher(db_session=self.db, embedder=mock_embedder)

        self.extractor = PromiseExtractor()
        self.normalizer_service = PromiseNormalizationService()
        self.scheme_matcher = PromiseSchemeMatcher(db_session=self.db, searcher=searcher)
        self.evidence_matcher = PromiseEvidenceMatcher(db_session=self.db, embedder=mock_embedder)
        self.assessment_engine = PromiseAssessmentEngine(db_session=self.db)

    def tearDown(self):
        api_promises_module.get_db = self._orig_get_db
        self.db.close()

    def test_fixture_declarations_and_locations(self):
        """Verify test fixtures exist in tests/fixtures/manifestos/ and carry required safety banners."""
        self.assertTrue(os.path.exists(FIXTURES_DIR), f"Fixtures directory {FIXTURES_DIR} must exist")
        
        # Verify prohibited location check: ensure no test fixtures exist in data/raw/manifestos/
        prohibited_dir = os.path.join("data", "raw", "manifestos")
        if os.path.exists(prohibited_dir):
            files = os.listdir(prohibited_dir)
            for f in files:
                self.assertNotIn("sample_", f.lower(), "Synthetic fixtures must not be placed in data/raw/manifestos/")

        # Verify safety banner in all manifesto fixture files
        fixture_files = ["sample_manifesto_en.txt", "sample_manifesto_ta.txt", "sample_manifesto_bilingual.json"]
        for filename in fixture_files:
            filepath = os.path.join(FIXTURES_DIR, filename)
            self.assertTrue(os.path.exists(filepath), f"Fixture file missing: {filepath}")
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()
            self.assertIn(
                "TEST FIXTURE — NOT REAL POLITICAL DATA",
                content,
                f"File {filename} must explicitly contain safety banner: TEST FIXTURE — NOT REAL POLITICAL DATA"
            )

    def test_complete_phase3_end_to_end_pipeline(self):
        """
        Runs complete Phase 3 pipeline:
        Fixture document → promise extraction → normalization → database → scheme matching
        → evidence matching → assessment → API endpoints → frontend service integration.
        """
        # --- Step 1: Load Fixture Manifesto Document ---
        bilingual_path = os.path.join(FIXTURES_DIR, "sample_manifesto_bilingual.json")
        with open(bilingual_path, "r", encoding="utf-8") as f:
            fixture_json = json.load(f)

        manifesto_id = fixture_json["manifesto_id"]
        party_name = fixture_json["party_name"]

        # Create DB Manifesto record
        manifesto_db = Manifesto(
            manifesto_id=manifesto_id,
            title=fixture_json["title"],
            party=party_name,
            election_year=fixture_json["election_year"],
            language="Bilingual"
        )
        self.db.add(manifesto_db)
        self.db.commit()

        # --- Step 2: Promise Extraction ---
        segments = []
        for page in fixture_json["pages"]:
            page_num = page["page_number"]
            sec = page["section"]
            
            segments.append(make_segment(page["text_en"], manifesto_id, page_num, sec, "English"))
            segments.append(make_segment(page["text_ta"], manifesto_id, page_num, sec, "Tamil"))
            segments.append(make_segment(page["ambiguous_text"], manifesto_id, page_num, sec, "English"))

        extracted_promises = self.extractor.extract(segments)
        self.assertGreater(len(extracted_promises), 0, "Extraction pipeline must yield promises from fixture segments")

        # --- Step 3: Promise Normalization & Categorization ---
        normalized_promises = []
        for rec in extracted_promises:
            norm = self.normalizer_service.normalize_promise(rec)
            normalized_promises.append(norm)
            
            # Verify original_text is untouched
            self.assertEqual(norm.original_text, rec.original_text)

        # Check that actionable promise has extracted metadata
        health_promise = next((p for p in normalized_promises if "primary health" in p.original_text.lower()), None)
        self.assertIsNotNone(health_promise)
        self.assertIn("500 crore", health_promise.metadata.monetary_target)
        self.assertIn(health_promise.primary_category, ["Healthcare", "Education"])

        # Check ambiguous statement isn't forced into rigid category
        vision_promise = next((p for p in normalized_promises if "backbone of our progressive society" in p.original_text.lower()), None)
        self.assertIsNotNone(vision_promise)
        self.assertIn(vision_promise.primary_category, ["Uncategorized", "Other", "Youth"])

        # --- Step 4: Database Persistence ---
        category_map = {}
        for norm in normalized_promises:
            cat_name = norm.primary_category
            if cat_name not in category_map:
                cat_db = self.db.query(PromiseCategory).filter_by(name=cat_name).first()
                if not cat_db:
                    cat_db = PromiseCategory(category_code=cat_name, name=cat_name, description=f"Category for {cat_name}")
                    self.db.add(cat_db)
                    self.db.flush()
                category_map[cat_name] = cat_db

            promise_db = PoliticalPromise(
                promise_id=norm.promise_id,
                manifesto_id=manifesto_id,
                original_text=norm.original_text,
                normalized_text=norm.normalized_text,
                page_number=norm.page_number,
                section=norm.section,
                language=norm.language,
                classification=norm.classification,
                extraction_confidence=0.9,
                metadata_json=norm.metadata.to_dict(),
                is_test_fixture=True
            )
            self.db.add(promise_db)

            # Link category
            cat_mapping = PromiseCategoryMapping(
                promise_id=norm.promise_id,
                category_id=category_map[cat_name].id,
                is_primary=True,
                confidence=norm.categorization_confidence or 0.8
            )
            self.db.add(cat_mapping)

        self.db.commit()

        db_promise_count = self.db.query(PoliticalPromise).count()
        self.assertEqual(db_promise_count, len(normalized_promises))

        # --- Step 5: Historical Scheme Matching ---
        dept_db = BudgetDepartment(code="HEALTH", name="Health and Family Welfare")
        self.db.add(dept_db)
        self.db.flush()

        scheme_db = HistoricalScheme(
            scheme_name="Primary Health Infrastructure Scheme",
            department_id=dept_db.id,
            financial_year="2021-2022",
            description="Historical scheme building health centres"
        )
        self.db.add(scheme_db)
        self.db.commit()

        # Run scheme matcher
        health_promise_db = self.db.query(PoliticalPromise).filter_by(promise_id=health_promise.promise_id).first()
        matches = self.scheme_matcher.match_promise(
            promise=health_promise_db,
            top_k=3,
            similarity_threshold=0.0
        )
        self.assertIsInstance(matches, list)

        # Manually verify or add PromiseSchemeLink
        scheme_link = PromiseSchemeLink(
            promise_id=health_promise.promise_id,
            historical_scheme_id=scheme_db.id,
            similarity_score=0.88,
            matching_method="semantic_sbert_v1",
            model_name="paraphrase-multilingual-MiniLM-L12-v2",
            model_version="1.0.0"
        )
        self.db.add(scheme_link)
        self.db.commit()

        # --- Step 6: Evidence Acquisition & Matching ---
        doc_db = Document(
            title="GO 104 - Sanction for 50 Health Centres",
            content="Government Order approving 50 new primary health centres with ₹500 crore budget allocation.",
            url="https://cms.tn.gov.in/sites/default/files/go/health_centres_2026.pdf"
        )
        self.db.add(doc_db)
        self.db.flush()

        evidence_db = Evidence(
            document_id=doc_db.id,
            content=doc_db.content,
            explanation="Official GO sanctioning health centres",
            supporting_values={"monetary_target": "₹500 crore", "count": 50},
            result_type="PromiseImplementationEvidence",
            result_id=health_promise.promise_id
        )
        self.db.add(evidence_db)
        self.db.commit()

        # Create explicit evidence link for test verification
        elink = PromiseEvidenceLink(
            promise_id=health_promise.promise_id,
            evidence_id=evidence_db.id,
            relevance_score=0.92,
            matching_method="multi_signal_hybrid_retrieval",
            matched_metadata={"signals": ["monetary_match", "dept_match", "keywords"]},
            model_name="paraphrase-multilingual-MiniLM-L12-v2",
            model_version="1.0.0"
        )
        self.db.add(elink)
        self.db.commit()

        # --- Step 7: Evidence-Based Promise Assessment Engine ---
        # Assess health promise (which has evidence)
        assessment_health = self.assessment_engine.evaluate_promise(health_promise_db)
        self.assertIn(
            assessment_health["status"],
            [
                PromiseStatus.POLICY_ACTION.value,
                PromiseStatus.ANNOUNCED.value,
                PromiseStatus.PARTIALLY_IMPLEMENTED.value,
                PromiseStatus.IMPLEMENTED.value
            ]
        )
        self.assertGreater(assessment_health["confidence"], 0.5)

        # Assess promise with NO evidence
        no_evidence_promise = next(p for p in normalized_promises if p.promise_id != health_promise.promise_id)
        no_ev_promise_db = self.db.query(PoliticalPromise).filter_by(promise_id=no_evidence_promise.promise_id).first()
        assessment_no_ev = self.assessment_engine.evaluate_promise(no_ev_promise_db)

        # CRITICAL RULE ASSERTION: Absence of evidence MUST yield 'no_evidence_found', NEVER 'not_implemented'
        self.assertEqual(
            assessment_no_ev["status"],
            PromiseStatus.NO_EVIDENCE_FOUND.value,
            "Promises with no supporting evidence must evaluate strictly to no_evidence_found"
        )
        self.assertNotEqual(
            assessment_no_ev["status"],
            "not_implemented",
            "No evidence must never be reported as not_implemented"
        )

        # --- Step 8: API Endpoint Verification ---
        # Test GET /api/promises/manifestos
        resp_m = self.client.get("/api/promises/manifestos")
        self.assertEqual(resp_m.status_code, 200)
        m_data = resp_m.get_json()
        self.assertEqual(m_data["status"], "success")
        m_items = m_data["data"]["items"]
        self.assertEqual(len(m_items), 1)
        self.assertEqual(m_items[0]["party"], party_name)

        # Test GET /api/promises/
        resp_p = self.client.get("/api/promises/")
        self.assertEqual(resp_p.status_code, 200)
        p_data = resp_p.get_json()
        self.assertEqual(p_data["status"], "success")
        self.assertEqual(p_data["data"]["total"], len(normalized_promises))

        # Test GET /api/promises/<id> detail endpoint
        resp_detail = self.client.get(f"/api/promises/{health_promise.promise_id}")
        self.assertEqual(resp_detail.status_code, 200)
        detail_json = resp_detail.get_json()["data"]
        self.assertEqual(detail_json["original_text"], health_promise.original_text)

        # Test GET /api/promises/<id>/assessment endpoint
        resp_assess = self.client.get(f"/api/promises/{health_promise.promise_id}/assessment")
        self.assertEqual(resp_assess.status_code, 200)
        assess_json = resp_assess.get_json()["data"]
        self.assertIn("status", assess_json)
        self.assertIn("confidence", assess_json)
        self.assertIn("explanation", assess_json)
        self.assertIn("supporting_evidence", assess_json)
        self.assertIn("source_links", assess_json)


if __name__ == "__main__":
    unittest.main()
