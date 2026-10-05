"""
Unit tests for Evidence-Based Promise Assessment Engine (Phase 3.11).

Verifies:
- Critical Rule: Absence of evidence evaluates to `no_evidence_found` (NEVER `not_implemented`).
- Full support for the 8 status taxonomy states:
  (`not_assessed`, `no_evidence_found`, `announced`, `policy_action`, `partially_implemented`, `implemented`, `unclear`, `disputed`).
- Mandatory assessment payload fields: (status, confidence, explanation, evidence_ids, source_tiers, assessment_date, methodology).
- Audit trail logging in PromiseAssessmentHistory.
- Deterministic, auditable rule-engine methodology without unexplainable ML political judgments.
"""
import unittest
from datetime import datetime, timezone
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.database.base import Base
from backend.models.manifesto import Manifesto
from backend.models.promise import (
    PoliticalPromise,
    PromiseAssessment,
    PromiseAssessmentHistory,
    PromiseEvidenceLink,
    PromiseStatus
)
from backend.models.common import Evidence
from backend.services.promise_assessment_engine import PromiseAssessmentEngine, METHODOLOGY_ID


class TestPromiseAssessmentEngine(unittest.TestCase):

    def setUp(self):
        # Create SQLite in-memory database
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        self.db = TestingSessionLocal()

        self.assessment_engine = PromiseAssessmentEngine(db_session=self.db)

    def tearDown(self):
        self.db.close()
        Base.metadata.drop_all(self.engine)

    def test_critical_rule_absence_of_evidence_evaluates_to_no_evidence_found(self):
        """CRITICAL RULE: Absence of evidence must evaluate to no_evidence_found, NEVER not_implemented."""
        m = Manifesto(manifesto_id="M_NO_EVID", party="Party A", election_year=2026)
        p = PoliticalPromise(
            promise_id="P_NO_EVID_01",
            manifesto_id="M_NO_EVID",
            original_text="We will construct 100 new bridges.",
            normalized_text="We will construct 100 new bridges."
        )
        self.db.add_all([m, p])
        self.db.commit()

        res = self.assessment_engine.evaluate_promise(p, persist=True)

        self.assertEqual(res["status"], PromiseStatus.NO_EVIDENCE_FOUND.value)
        self.assertNotEqual(res["status"], "not_implemented")
        self.assertEqual(res["confidence"], 0.5)
        self.assertIn("Absence of evidence is not proof of non-implementation", res["explanation"])
        self.assertEqual(res["evidence_ids"], [])
        self.assertEqual(res["methodology"], METHODOLOGY_ID)

    def test_mandatory_assessment_payload_attributes(self):
        """Verify that every assessment payload contains all required attributes."""
        m = Manifesto(manifesto_id="M_PAYLOAD", party="Party B", election_year=2026)
        p = PoliticalPromise(promise_id="P_PAYLOAD_01", manifesto_id="M_PAYLOAD", original_text="Text", normalized_text="Text")
        self.db.add_all([m, p])
        self.db.commit()

        res = self.assessment_engine.evaluate_promise(p, persist=False)

        required_keys = ["status", "confidence", "explanation", "evidence_ids", "source_tiers", "assessment_date", "methodology"]
        for key in required_keys:
            self.assertIn(key, res, f"Assessment payload must contain '{key}' key.")

    def test_status_announced(self):
        """Verify press release / announcement evidence evaluates to 'announced'."""
        m = Manifesto(manifesto_id="M_ANN", party="Party C", election_year=2026)
        p = PoliticalPromise(promise_id="P_ANN_01", manifesto_id="M_ANN", original_text="Text", normalized_text="Text")
        self.db.add_all([m, p])
        self.db.commit()

        ev = Evidence(
            content="Government announced intention to launch scheme.",
            supporting_values={"source_type": "Official press releases", "source_tier": 1}
        )
        self.db.add(ev)
        self.db.commit()

        link = PromiseEvidenceLink(promise_id="P_ANN_01", evidence_id=ev.id, relevance_score=0.7)
        self.db.add(link)
        self.db.commit()

        res = self.assessment_engine.evaluate_promise(p, persist=True)
        self.assertEqual(res["status"], PromiseStatus.ANNOUNCED.value)

    def test_status_policy_action(self):
        """Verify Government Order (G.O.) evidence evaluates to 'policy_action'."""
        m = Manifesto(manifesto_id="M_GO", party="Party D", election_year=2026)
        p = PoliticalPromise(promise_id="P_GO_01", manifesto_id="M_GO", original_text="Text", normalized_text="Text")
        self.db.add_all([m, p])
        self.db.commit()

        ev = Evidence(
            content="G.O. Ms. No. 45 issued sanctioning policy framework.",
            supporting_values={"source_type": "Government Orders", "source_tier": 1}
        )
        self.db.add(ev)
        self.db.commit()

        link = PromiseEvidenceLink(promise_id="P_GO_01", evidence_id=ev.id, relevance_score=0.85)
        self.db.add(link)
        self.db.commit()

        res = self.assessment_engine.evaluate_promise(p, persist=True)
        self.assertEqual(res["status"], PromiseStatus.POLICY_ACTION.value)

    def test_status_implemented(self):
        """Verify G.O. + Budget Demand execution evaluates to 'implemented'."""
        m = Manifesto(manifesto_id="M_IMP", party="Party E", election_year=2026)
        p = PoliticalPromise(promise_id="P_IMP_01", manifesto_id="M_IMP", original_text="Text", normalized_text="Text")
        self.db.add_all([m, p])
        self.db.commit()

        ev = Evidence(
            content="G.O. Ms. No. 10 and Budget Demand No 15 allocation 1000 crore completed.",
            supporting_values={"source_type": "Government Orders", "source_tier": 1}
        )
        self.db.add(ev)
        self.db.commit()

        link = PromiseEvidenceLink(promise_id="P_IMP_01", evidence_id=ev.id, relevance_score=0.9)
        self.db.add(link)
        self.db.commit()

        res = self.assessment_engine.evaluate_promise(p, persist=True)
        self.assertEqual(res["status"], PromiseStatus.IMPLEMENTED.value)
        self.assertEqual(res["confidence"], 0.95)

    def test_status_disputed(self):
        """Verify conflicting or disputed evidence evaluates to 'disputed'."""
        m = Manifesto(manifesto_id="M_DISP", party="Party F", election_year=2026)
        p = PoliticalPromise(promise_id="P_DISP_01", manifesto_id="M_DISP", original_text="Text", normalized_text="Text")
        self.db.add_all([m, p])
        self.db.commit()

        ev = Evidence(
            content="Report indicates disputed status with contradictory claims.",
            supporting_values={"source_type": "Government website", "source_tier": 1}
        )
        self.db.add(ev)
        self.db.commit()

        link = PromiseEvidenceLink(promise_id="P_DISP_01", evidence_id=ev.id, relevance_score=0.6)
        self.db.add(link)
        self.db.commit()

        res = self.assessment_engine.evaluate_promise(p, persist=True)
        self.assertEqual(res["status"], PromiseStatus.DISPUTED.value)

    def test_assessment_audit_trail_history(self):
        """Verify that updating a promise's assessment logs entries in PromiseAssessmentHistory."""
        m = Manifesto(manifesto_id="M_AUDIT", party="Party G", election_year=2026)
        p = PoliticalPromise(promise_id="P_AUDIT_01", manifesto_id="M_AUDIT", original_text="Text", normalized_text="Text")
        self.db.add_all([m, p])
        self.db.commit()

        # Step 1: Initial evaluation (no evidence -> no_evidence_found)
        res1 = self.assessment_engine.evaluate_promise(p, persist=True)
        self.assertEqual(res1["status"], PromiseStatus.NO_EVIDENCE_FOUND.value)

        # Add evidence
        ev = Evidence(
            content="G.O. Ms. No. 10 issued.",
            supporting_values={"source_type": "Government Orders", "source_tier": 1}
        )
        self.db.add(ev)
        self.db.commit()

        link = PromiseEvidenceLink(promise_id="P_AUDIT_01", evidence_id=ev.id, relevance_score=0.85)
        self.db.add(link)
        self.db.commit()

        # Step 2: Re-evaluation (evidence added -> policy_action)
        res2 = self.assessment_engine.evaluate_promise(p, persist=True)
        self.assertEqual(res2["status"], PromiseStatus.POLICY_ACTION.value)

        # Verify audit history log entries
        history_entries = self.db.query(PromiseAssessmentHistory).filter_by(promise_id="P_AUDIT_01").order_by(PromiseAssessmentHistory.id).all()
        self.assertEqual(len(history_entries), 2)

        # Entry 1: initial creation
        self.assertIsNone(history_entries[0].previous_status)
        self.assertEqual(history_entries[0].new_status, PromiseStatus.NO_EVIDENCE_FOUND.value)

        # Entry 2: transition from no_evidence_found to policy_action
        self.assertEqual(history_entries[1].previous_status, PromiseStatus.NO_EVIDENCE_FOUND.value)
        self.assertEqual(history_entries[1].new_status, PromiseStatus.POLICY_ACTION.value)
        self.assertIn("deterministic_rule_engine_v1", history_entries[1].changed_by)


if __name__ == "__main__":
    unittest.main()
