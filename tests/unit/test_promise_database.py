"""
Unit tests for Political Promise Database Models (Phase 3.7).

Verifies:
- Explicit entity separation (Promise vs Evidence vs Match vs Assessment vs History)
- Relationships & Cascading deletions
- Multi-election, multi-party, multi-language support
- Multiple evidence records per promise
- Multiple historical schemes per promise
- Assessment history audit trail
- Empty dataset handling
- Constraints & Duplicate handling
"""
import unittest
from datetime import datetime, timezone
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import IntegrityError

from backend.database.base import Base
from backend.models.common import Document, Evidence, Source
from backend.models.budget import BudgetDepartment, HistoricalScheme, BudgetScheme
from backend.models.manifesto import ManifestoSource, ManifestoDocument, Manifesto
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


class TestPromiseDatabaseModels(unittest.TestCase):

    def setUp(self):
        # Create SQLite in-memory database for testing
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        self.db = TestingSessionLocal()

    def tearDown(self):
        self.db.close()
        Base.metadata.drop_all(self.engine)

    def test_empty_dataset_querying(self):
        """Verify that querying empty tables returns empty results without crashing."""
        self.assertEqual(self.db.query(Manifesto).all(), [])
        self.assertEqual(self.db.query(PoliticalPromise).all(), [])
        self.assertEqual(self.db.query(PromiseCategory).all(), [])
        self.assertEqual(self.db.query(PromiseEvidenceLink).all(), [])
        self.assertEqual(self.db.query(PromiseSchemeLink).all(), [])
        self.assertEqual(self.db.query(PromiseAssessment).all(), [])
        self.assertEqual(self.db.query(PromiseAssessmentHistory).all(), [])

    def test_multi_election_party_language_manifesto(self):
        """Verify support for multiple elections, parties, and languages."""
        m1 = Manifesto(
            manifesto_id="DMK_2021_Assembly",
            party="Dravida Munnetra Kazhagam",
            election="Tamil Nadu Legislative Assembly Election",
            election_year=2021,
            language="Tamil",
            title="DMK Election Manifesto 2021"
        )
        m2 = Manifesto(
            manifesto_id="AIADMK_2021_Assembly",
            party="All India Anna Dravida Munnetra Kazhagam",
            election="Tamil Nadu Legislative Assembly Election",
            election_year=2021,
            language="Tamil",
            title="AIADMK Election Manifesto 2021"
        )
        m3 = Manifesto(
            manifesto_id="TVK_2026_Assembly",
            party="Tamilaga Vettri Kazhagam",
            election="Tamil Nadu Legislative Assembly Election",
            election_year=2026,
            language="English",
            title="TVK Assembly Election Manifesto 2026"
        )

        self.db.add_all([m1, m2, m3])
        self.db.commit()

        manifestos = self.db.query(Manifesto).all()
        self.assertEqual(len(manifestos), 3)

        # Query by election year
        m_2026 = self.db.query(Manifesto).filter(Manifesto.election_year == 2026).first()
        self.assertIsNotNone(m_2026)
        self.assertEqual(m_2026.party, "Tamilaga Vettri Kazhagam")

    def test_promise_creation_and_preservation(self):
        """Verify creating a PoliticalPromise linked to a Manifesto preserving original wording."""
        m = Manifesto(
            manifesto_id="DMK_2021",
            party="DMK",
            election_year=2021
        )
        self.db.add(m)
        self.db.commit()

        p = PoliticalPromise(
            promise_id="DMK_2021:p1:001",
            manifesto_id="DMK_2021",
            original_text="விவசாயிகளுக்கு பயிர் கடன் தள்ளுபடி செய்யப்படும்.",
            normalized_text="விவசாயிகளுக்கு பயிர் கடன் தள்ளுபடி செய்யப்படும்.",
            page_number=5,
            section="Agriculture",
            language="Tamil",
            classification="specific_promise",
            extraction_confidence=0.9,
            metadata_json={"target_population": "Farmers", "sector": "Agriculture"}
        )
        self.db.add(p)
        self.db.commit()

        fetched = self.db.query(PoliticalPromise).filter_by(promise_id="DMK_2021:p1:001").first()
        self.assertIsNotNone(fetched)
        self.assertEqual(fetched.original_text, "விவசாயிகளுக்கு பயிர் கடன் தள்ளுபடி செய்யப்படும்.")
        self.assertEqual(fetched.manifesto.party, "DMK")
        self.assertEqual(fetched.metadata_json["sector"], "Agriculture")

    def test_multiple_categories_per_promise(self):
        """Verify promise category taxonomy and multi-category mappings."""
        m = Manifesto(manifesto_id="M1", party="Party A", election_year=2026)
        c1 = PromiseCategory(category_code="Education", name="Education", description="School and higher education")
        c2 = PromiseCategory(category_code="DigitalServices", name="Digital Services", description="Internet & IT")
        self.db.add_all([m, c1, c2])
        self.db.commit()

        p = PoliticalPromise(
            promise_id="P1",
            manifesto_id="M1",
            original_text="Free laptops and broadband internet for high school students.",
            normalized_text="Free laptops and broadband internet for high school students."
        )
        self.db.add(p)
        self.db.commit()

        map1 = PromiseCategoryMapping(promise_id="P1", category_id=c1.id, is_primary=True, confidence=0.9)
        map2 = PromiseCategoryMapping(promise_id="P1", category_id=c2.id, is_primary=False, confidence=0.7)
        self.db.add_all([map1, map2])
        self.db.commit()

        fetched_p = self.db.query(PoliticalPromise).filter_by(promise_id="P1").first()
        self.assertEqual(len(fetched_p.categories), 2)
        primary_map = [cat for cat in fetched_p.categories if cat.is_primary][0]
        self.assertEqual(primary_map.category.category_code, "Education")

    def test_multiple_evidence_links_per_promise(self):
        """Verify linking multiple Evidence records to a single Promise."""
        m = Manifesto(manifesto_id="M1", party="Party B", election_year=2026)
        self.db.add(m)
        self.db.commit()

        p = PoliticalPromise(
            promise_id="P_EVID_1",
            manifesto_id="M1",
            original_text="We will provide Rs. 1000 per month for women.",
            normalized_text="We will provide Rs. 1000 per month for women."
        )
        self.db.add(p)
        self.db.commit()

        ev1 = Evidence(content="GO Ms 45: Sanction of Rs 1000 monthly assistance scheme.", result_type="GO_Order")
        ev2 = Evidence(content="Budget demand demand No 15 allocation 4000 crore.", result_type="BudgetDemand")
        self.db.add_all([ev1, ev2])
        self.db.commit()

        link1 = PromiseEvidenceLink(promise_id="P_EVID_1", evidence_id=ev1.id, similarity_score=0.92, matching_method="vector_search")
        link2 = PromiseEvidenceLink(promise_id="P_EVID_1", evidence_id=ev2.id, similarity_score=0.85, matching_method="keyword_match")
        self.db.add_all([link1, link2])
        self.db.commit()

        fetched_p = self.db.query(PoliticalPromise).filter_by(promise_id="P_EVID_1").first()
        self.assertEqual(len(fetched_p.evidence_links), 2)
        scores = [l.similarity_score for l in fetched_p.evidence_links]
        self.assertIn(0.92, scores)
        self.assertIn(0.85, scores)

    def test_multiple_scheme_links_per_promise(self):
        """Verify linking multiple Historical / Budget Schemes to a single Promise."""
        m = Manifesto(manifesto_id="M1", party="Party C", election_year=2026)
        dept = BudgetDepartment(name="Agriculture Department")
        self.db.add_all([m, dept])
        self.db.commit()

        p = PoliticalPromise(
            promise_id="P_SCHEME_1",
            manifesto_id="M1",
            original_text="Free crop insurance for small farmers.",
            normalized_text="Free crop insurance for small farmers."
        )
        hs = HistoricalScheme(financial_year="2021-2022", scheme_name="Crop Insurance Scheme 2021", department_id=dept.id)
        bs = BudgetScheme(name="Pradhan Mantri Fasal Bima Yojana", department_id=dept.id)
        self.db.add_all([p, hs, bs])
        self.db.commit()

        s_link1 = PromiseSchemeLink(promise_id="P_SCHEME_1", historical_scheme_id=hs.id, similarity_score=0.89, match_type="historical_match")
        s_link2 = PromiseSchemeLink(promise_id="P_SCHEME_1", budget_scheme_id=bs.id, similarity_score=0.95, match_type="budget_match")
        self.db.add_all([s_link1, s_link2])
        self.db.commit()

        fetched_p = self.db.query(PoliticalPromise).filter_by(promise_id="P_SCHEME_1").first()
        self.assertEqual(len(fetched_p.scheme_links), 2)

    def test_promise_assessment_and_audit_history(self):
        """Verify assessment tracking and assessment history audit trail."""
        m = Manifesto(manifesto_id="M1", party="Party D", election_year=2026)
        p = PoliticalPromise(promise_id="P_ASSESS_1", manifesto_id="M1", original_text="Text", normalized_text="Text")
        self.db.add_all([m, p])
        self.db.commit()

        # Initial assessment: NOT_ASSESSED
        assess = PromiseAssessment(
            promise_id="P_ASSESS_1",
            status=PromiseStatus.NOT_ASSESSED,
            confidence_score=0.0,
            rationale="Initial state before evidence discovery",
            assessed_by="pipeline_init"
        )
        self.db.add(assess)
        self.db.commit()

        # Audit history log entry 1
        h1 = PromiseAssessmentHistory(
            promise_id="P_ASSESS_1",
            assessment_id=assess.id,
            previous_status=None,
            new_status="not_assessed",
            change_reason="Initial ingestion",
            changed_by="pipeline_init"
        )
        self.db.add(h1)
        self.db.commit()

        # Update assessment to PARTIALLY_IMPLEMENTED
        assess.status = PromiseStatus.PARTIALLY_IMPLEMENTED
        assess.confidence_score = 0.8
        assess.rationale = "Budget allocation found in FY2026 demands"
        assess.assessed_by = "evidence_engine_v1"

        h2 = PromiseAssessmentHistory(
            promise_id="P_ASSESS_1",
            assessment_id=assess.id,
            previous_status="not_assessed",
            new_status="partially_implemented",
            change_reason="Evidence matched with 0.8 confidence",
            changed_by="evidence_engine_v1"
        )
        self.db.add(h2)
        self.db.commit()

        fetched_p = self.db.query(PoliticalPromise).filter_by(promise_id="P_ASSESS_1").first()
        self.assertEqual(fetched_p.assessments[0].status, PromiseStatus.PARTIALLY_IMPLEMENTED)
        self.assertEqual(len(fetched_p.assessment_history), 2)
        self.assertEqual(fetched_p.assessment_history[1].previous_status, "not_assessed")
        self.assertEqual(fetched_p.assessment_history[1].new_status, "partially_implemented")

    def test_cascading_deletions(self):
        """Verify that deleting a Manifesto cascades deletion of its Promises and associated links."""
        m = Manifesto(manifesto_id="M_CASCADE", party="Party E", election_year=2026)
        self.db.add(m)
        self.db.commit()

        p = PoliticalPromise(promise_id="P_CASCADE", manifesto_id="M_CASCADE", original_text="Text", normalized_text="Text")
        self.db.add(p)
        self.db.commit()

        assess = PromiseAssessment(promise_id="P_CASCADE", status=PromiseStatus.ANNOUNCED)
        self.db.add(assess)
        self.db.commit()

        # Verify items exist
        self.assertIsNotNone(self.db.query(PoliticalPromise).filter_by(promise_id="P_CASCADE").first())
        self.assertIsNotNone(self.db.query(PromiseAssessment).filter_by(promise_id="P_CASCADE").first())

        # Delete Manifesto
        self.db.delete(m)
        self.db.commit()

        # Promises and assessments should be deleted automatically via cascade
        self.assertIsNone(self.db.query(PoliticalPromise).filter_by(promise_id="P_CASCADE").first())
        self.assertIsNone(self.db.query(PromiseAssessment).filter_by(promise_id="P_CASCADE").first())

    def test_duplicate_primary_key_handling(self):
        """Verify constraint enforcement for duplicate primary keys."""
        c1 = PromiseCategory(category_code="Edu", name="Education")
        self.db.add(c1)
        self.db.commit()

        c2 = PromiseCategory(category_code="Edu", name="Education Duplicate")
        self.db.add(c2)
        with self.assertRaises(IntegrityError):
            self.db.commit()
        self.db.rollback()


if __name__ == "__main__":
    unittest.main()
