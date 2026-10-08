"""
Unit & Integration Test Suite for Phase 4.5 Political Entity, Topic, and Event Intelligence Layer.

IMPORTANT:
All test cases use synthetic local text fixtures tagged with `is_test_fixture=True`.
No real political news articles or live websites are used during unit tests.
"""

import pytest
from datetime import datetime, timezone
from backend.database.session import SessionLocal, engine
from backend.database.base import Base
from backend.models.news import (
    PoliticalParty, PoliticalPerson, GovernmentDepartment, PoliticalEntity, PoliticalEvent, Topic
)
from backend.nlp.intelligence_layer import (
    EntityRecognizer, EntityProminenceCalculator, TopicClassifier, EventIdentifier, IntelligenceLayerService
)

SYNTHETIC_INTEL_HEADLINE = "TEST FIXTURE — Chief Minister M.K. Stalin Inaugrates Chennai Metro Infrastructure"
SYNTHETIC_INTEL_BODY = """TEST FIXTURE — NOT REAL NEWS DATA. Chief Minister M.K. Stalin announced state budget allocation for DMK governance in Chennai.
Edappadi K. Palaniswami of AIADMK reviewed the report in Madras High Court and Kolathur constituency."""





class TestPhase4IntelligenceLayer:
    """Test suite for Phase 4.5 intelligence extraction layer."""

    def test_entity_recognition_categories(self):
        """Test entity extraction for People, Parties, Departments, Locations, Constituencies, and Organizations."""
        recognizer = EntityRecognizer()
        mentions = recognizer.extract_mentions(SYNTHETIC_INTEL_BODY, headline=SYNTHETIC_INTEL_HEADLINE)
        
        entity_ids = [m["entity_id"] for m in mentions]
        entity_types = set(m["entity_type"] for m in mentions)

        assert "ent_person_mkstalin" in entity_ids
        assert "ent_person_eps" in entity_ids
        assert "ent_party_dmk" in entity_ids
        assert "ent_party_aiadmk" in entity_ids
        assert "ent_loc_chennai" in entity_ids
        assert "ent_const_kolathur" in entity_ids
        assert "ent_org_madras_hc" in entity_ids

        assert "person" in entity_types
        assert "political_party" in entity_types
        assert "location" in entity_types

    def test_entity_prominence_calculator(self):
        """Test formula P_entity = 0.4*Title + 0.3*Lead + 0.3*min(1, Count/5)."""
        calc = EntityProminenceCalculator()

        # Mentioned in Headline, Lead, and 5 times
        high_prom = calc.calculate({"found_in_headline": True, "found_in_lead": True, "mention_count": 5})
        assert high_prom == 1.0

        # Mentioned in body only (1 mention, not lead, not headline)
        low_prom = calc.calculate({"found_in_headline": False, "found_in_lead": False, "mention_count": 1})
        assert low_prom == 0.06

    def test_14_category_topic_classification(self):
        """Test classification across 14 policy categories (infrastructure, governance, economy, etc.)."""
        classifier = TopicClassifier()
        
        infra_text = "TEST FIXTURE — Metro expansion, road construction, bus transport, and highway infrastructure."
        topics_infra = classifier.classify(infra_text)
        assert topics_infra[0]["topic_id"] == "infrastructure"

        agri_text = "TEST FIXTURE — Farmers monsoon paddy crop harvest and irrigation fertilizer subsidy."
        topics_agri = classifier.classify(agri_text)
        assert topics_agri[0]["topic_id"] == "agriculture"

        edu_text = "TEST FIXTURE — School education, university student exams, and teacher recruitment."
        topics_edu = classifier.classify(edu_text)
        assert topics_edu[0]["topic_id"] == "education"

        other_text = "TEST FIXTURE — Unrelated general update report."
        topics_other = classifier.classify(other_text)
        assert topics_other[0]["topic_id"] in ["other", "governance"]

    def test_event_identification(self):
        """Test ground-truth event identification for budget and assembly sessions."""
        identifier = EventIdentifier()
        text = "TEST FIXTURE — Tamil Nadu state budget 2026 presentation and assembly session debate."
        events = identifier.identify_events(text)
        
        event_ids = [e["event_id"] for e in events]
        assert "evt_tn_budget_2026" in event_ids or "evt_tn_assembly_session" in event_ids

    def test_decoupling_safeguard(self):
        """Verify entity detection returns neutral frequency/prominence without assuming positive/negative sentiment."""
        service = IntelligenceLayerService()
        analysis = service.analyze_article(SYNTHETIC_INTEL_HEADLINE, SYNTHETIC_INTEL_BODY)
        
        assert "entities" in analysis
        assert "topics" in analysis
        assert "events" in analysis

        for ent in analysis["entities"]:
            assert "mention_count" in ent
            assert "prominence_score" in ent
            # Ensure entity detection does not dictate sentiment
            assert "sentiment_bias_claim" not in ent

    def test_database_intelligence_entities_persistence(self, db_session):
        """Test database persistence for PoliticalPerson, PoliticalParty, GovernmentDepartment, PoliticalEntity, PoliticalEvent, and Topic."""
        # 1. Party
        party = PoliticalParty(party_id="party_test", party_name="Test Party", party_code="TPC")
        db_session.add(party)

        # 2. Person
        person = PoliticalPerson(person_id="person_test", name="Test Leader", party_id="party_test")
        db_session.add(person)

        # 3. Department
        dept = GovernmentDepartment(dept_id="dept_test", dept_code="DOC", name_en="Department of Commerce")
        db_session.add(dept)

        # 4. Entity
        entity = PoliticalEntity(entity_id="ent_test", entity_type="person", name="Test Leader", normalized_name="Test Leader")
        db_session.add(entity)

        # 5. Event
        event = PoliticalEvent(event_id="evt_test", event_name="Test Event", event_date=datetime.now(timezone.utc).date())
        db_session.add(event)

        # 6. Topic
        topic = Topic(topic_id="top_test", topic_code="top_test", topic_name="Test Policy Area")
        db_session.add(topic)

        db_session.commit()

        assert db_session.query(PoliticalParty).filter(PoliticalParty.party_id == "party_test").first() is not None
        assert db_session.query(PoliticalPerson).filter(PoliticalPerson.person_id == "person_test").first() is not None
        assert db_session.query(GovernmentDepartment).filter(GovernmentDepartment.dept_id == "dept_test").first() is not None
        assert db_session.query(PoliticalEntity).filter(PoliticalEntity.entity_id == "ent_test").first() is not None
        assert db_session.query(PoliticalEvent).filter(PoliticalEvent.event_id == "evt_test").first() is not None
        assert db_session.query(Topic).filter(Topic.topic_id == "top_test").first() is not None
