import re
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Set
from backend.core.logger import setup_logger

logger = setup_logger("civiclens.nlp.intelligence_layer")

# ---------------------------------------------------------------------------
# TOPIC TAXONOMY DEFINITION (14 TARGET POLICY AREAS)
# ---------------------------------------------------------------------------
TOPIC_TAXONOMY_14 = {
    "elections": {
        "name": "Elections & Campaigning",
        "description": "Elections, polls, candidate nominations, voting, campaign rallies, ballot counting, and electoral reforms.",
        "keywords": ["election", "vote", "voter", "campaign", "ballot", "polling", "candidate", "nomination", "constituency", "தேர்தல்", "வாக்கு", "பிரச்சாரம்", "வேட்பாளர்", "தொகுதி", "வாக்குப்பதிவு"]
    },
    "governance": {
        "name": "Governance & Administration",
        "description": "Government policy decisions, executive orders, legislative assembly debates, cabinet meetings, and official announcements.",
        "keywords": ["governance", "assembly", "cabinet", "policy", "minister", "chief minister", "government order", "dipr", "சட்டமன்றம்", "அமைச்சரவை", "அரசாணை", "கொள்கை", "நிர்வாகம்", "முதல்வர்"]
    },
    "education": {
        "name": "Education & Learning",
        "description": "Schools, universities, exams, scholarships, teachers, higher education, syllabus, and educational schemes.",
        "keywords": ["school", "university", "education", "student", "teacher", "exam", "syllabus", "scholarship", "கல்லூரி", "பள்ளி", "கல்வி", "மாணவர்", "ஆசிரியர்", "பல்கலைக்கழகம்", "தேர்வு"]
    },
    "healthcare": {
        "name": "Healthcare & Public Health",
        "keywords": ["hospital", "health", "doctor", "medicine", "medical", "dengue", "vaccine", "clinic", "மருத்துவமனை", "சுகாதாரம்", "மருத்துவம்", "டாக்டர்", "சிகிச்சை", "தடுப்பூசி"]
    },
    "agriculture": {
        "name": "Agriculture & Farmers",
        "keywords": ["farmer", "agriculture", "crop", "paddy", "irrigation", "monsoon", "fertilizer", "விவசாயி", "வேளாண்மை", "பயிர்", "பாசனம்", "விவசாயம்", "நெல்", "உரம்"]
    },
    "welfare": {
        "name": "Welfare & Social Security",
        "keywords": ["welfare", "pension", "ration", "subsidy", "scheme", "women welfare", "poor", "பயனாளி", "நலத்திட்டம்", "ரேஷன்", "மானியம", "ஓய்வூதியம்", "மகளிர்"]
    },
    "employment": {
        "name": "Employment & Skill Development",
        "keywords": ["job", "employment", "vacancy", "recruitment", "salary", "skill", "unemployment", "வேலைவாய்ப்பு", "பணி", "நியமனம்", "சம்பளம்", "வேலையில்லாத் திண்டாட்டம்"]
    },
    "infrastructure": {
        "name": "Infrastructure & Transportation",
        "keywords": ["metro", "road", "bridge", "bus", "highway", "railway", "airport", "electricity", "power", "சாலை", "பாலம்", "பேருந்து", "மின்சாரம்", "மெட்ரோ", "போக்குவரத்து", "நெடுஞ்சாலை"]
    },
    "economy": {
        "name": "Economy, Finance & Budget",
        "keywords": ["budget", "finance", "tax", "revenue", "investment", "crore", "gdp", "industry", "நிதி", "வரவு செலவு", "பட்ஜெட்", "வரி", "முதலீடு", "பொருளாதாரம்", "தொழில்துறை"]
    },
    "law_and_order": {
        "name": "Law, Order & Judiciary",
        "keywords": ["police", "court", "judge", "crime", "investigation", "arrest", "justice", "high court", "காவல்துறை", "நீதிமன்றம்", "நீதிபதி", "குற்றம்", "கைது", "வழக்கு"]
    },
    "environment": {
        "name": "Environment & Climate Action",
        "keywords": ["environment", "climate", "forest", "river", "pollution", "water", "lake", "green", "சுற்றுச்சூழல்", "காடு", "நதி", "மாசு", "நீர்", "ஏரி", "பசுமை"]
    },
    "technology": {
        "name": "Technology & E-Governance",
        "keywords": ["technology", "digital", "internet", "software", "it park", "e-governance", "ai", "தொழில்நுட்பம்", "டிஜிட்டல்", "இணையம்", "மென்பொருள்"]
    },
    "social_issues": {
        "name": "Social Issues & Community",
        "keywords": ["caste", "reservation", "language", "rights", "community", "equality", "social justice", "சாதி", "இடஒதுக்கீடு", "மொழி", "உரிமை", "சமூக நீதி"]
    },
    "other": {
        "name": "Other Civic & General News",
        "keywords": ["news", "update", "report", "general", "event", "செய்தி", "அறிக்கை", "நிகழ்வு"]
    }
}


# ---------------------------------------------------------------------------
# GAZETTEER DATABASE FOR EXTRACTING POLITICAL ENTITIES
# ---------------------------------------------------------------------------
ENTITY_GAZETTEER = [
    # --- PEOPLE / LEADERS ---
    {
        "entity_id": "ent_person_mkstalin",
        "name": "M.K. Stalin",
        "normalized_name": "M.K. Stalin",
        "entity_type": "person",
        "aliases": ["M.K. Stalin", "Stalin", "Chief Minister Stalin", "CM Stalin", "மு.க. ஸ்டாலின்", "ஸ்டாலின்", "முதல்வர் ஸ்டாலின்"]
    },
    {
        "entity_id": "ent_person_eps",
        "name": "Edappadi K. Palaniswami",
        "normalized_name": "Edappadi K. Palaniswami",
        "entity_type": "person",
        "aliases": ["Edappadi K. Palaniswami", "Edappadi Palaniswami", "EPS", "Palaniswami", "எடப்பாடி பழனிசாமி", "இபிஎஸ்", "பழனிசாமி"]
    },
    {
        "entity_id": "ent_person_ops",
        "name": "O. Panneerselvam",
        "normalized_name": "O. Panneerselvam",
        "entity_type": "person",
        "aliases": ["O. Panneerselvam", "OPS", "Panneerselvam", "ஓ. பன்னீர்செல்வம்", "ஓபிஎஸ்"]
    },
    {
        "entity_id": "ent_person_udhayanidhi",
        "name": "Udhayanidhi Stalin",
        "normalized_name": "Udhayanidhi Stalin",
        "entity_type": "person",
        "aliases": ["Udhayanidhi Stalin", "Udhayanidhi", "உதயநிதி ஸ்டாலின்", "உதயநிதி"]
    },
    {
        "entity_id": "ent_person_annamalai",
        "name": "K. Annamalai",
        "normalized_name": "K. Annamalai",
        "entity_type": "person",
        "aliases": ["K. Annamalai", "Annamalai", "அண்ணாமலை"]
    },
    {
        "entity_id": "ent_person_seeman",
        "name": "Seeman",
        "normalized_name": "Seeman",
        "entity_type": "person",
        "aliases": ["Seeman", "NTK Seeman", "சீமான்"]
    },
    {
        "entity_id": "ent_person_thirumavalavan",
        "name": "Thol. Thirumavalavan",
        "normalized_name": "Thol. Thirumavalavan",
        "entity_type": "person",
        "aliases": ["Thol. Thirumavalavan", "Thirumavalavan", "தொல். திருமாவளவன்", "திருமாவளவன்"]
    },

    # --- POLITICAL PARTIES ---
    {
        "entity_id": "ent_party_dmk",
        "name": "DMK",
        "normalized_name": "Dravida Munnetra Kazhagam",
        "entity_type": "political_party",
        "aliases": ["DMK", "Dravida Munnetra Kazhagam", "திமுக", "திராவிட முன்னேற்றக் கழகம்"]
    },
    {
        "entity_id": "ent_party_aiadmk",
        "name": "AIADMK",
        "normalized_name": "All India Anna Dravida Munnetra Kazhagam",
        "entity_type": "political_party",
        "aliases": ["AIADMK", "ADMK", "All India Anna Dravida Munnetra Kazhagam", "அதிமுக", "அனைத்திந்திய அண்ணா திராவிட முன்னேற்றக் கழகம்"]
    },
    {
        "entity_id": "ent_party_bjp",
        "name": "BJP",
        "normalized_name": "Bharatiya Janata Party",
        "entity_type": "political_party",
        "aliases": ["BJP", "Bharatiya Janata Party", "பாஜக", "பாரதிய ஜனதா கட்சி"]
    },
    {
        "entity_id": "ent_party_inc",
        "name": "INC",
        "normalized_name": "Indian National Congress",
        "entity_type": "political_party",
        "aliases": ["Congress", "INC", "Indian National Congress", "காங்கிரஸ்"]
    },
    {
        "entity_id": "ent_party_ntk",
        "name": "NTK",
        "normalized_name": "Naam Tamilar Katchi",
        "entity_type": "political_party",
        "aliases": ["NTK", "Naam Tamilar Katchi", "நாம் தமிழர் கட்சி"]
    },
    {
        "entity_id": "ent_party_vck",
        "name": "VCK",
        "normalized_name": "Viduthalai Chiruthaigal Katchi",
        "entity_type": "political_party",
        "aliases": ["VCK", "Viduthalai Chiruthaigal Katchi", "விடுதலை சிறுத்தைகள் கட்சி"]
    },

    # --- GOVERNMENT DEPARTMENTS ---
    {
        "entity_id": "ent_dept_finance",
        "name": "Department of Finance",
        "normalized_name": "Department of Finance",
        "entity_type": "government_department",
        "aliases": ["Department of Finance", "Finance Ministry", "நிதித்துறை", "நிதி அமைச்சகம்"]
    },
    {
        "entity_id": "ent_dept_school_edu",
        "name": "Department of School Education",
        "normalized_name": "Department of School Education",
        "entity_type": "government_department",
        "aliases": ["Department of School Education", "School Education Department", "பள்ளிக் கல்வித் துறை"]
    },
    {
        "entity_id": "ent_dept_health",
        "name": "Department of Health & Family Welfare",
        "normalized_name": "Department of Health & Family Welfare",
        "entity_type": "government_department",
        "aliases": ["Department of Health", "Health Department", "மக்கள் நல்வாழ்வுத் துறை", "சுகாதாரத்துறை"]
    },

    # --- LOCATIONS ---
    {
        "entity_id": "ent_loc_chennai",
        "name": "Chennai",
        "normalized_name": "Chennai",
        "entity_type": "location",
        "aliases": ["Chennai", "Madras", "சென்னை"]
    },
    {
        "entity_id": "ent_loc_madurai",
        "name": "Madurai",
        "normalized_name": "Madurai",
        "entity_type": "location",
        "aliases": ["Madurai", "மதுரை"]
    },
    {
        "entity_id": "ent_loc_coimbatore",
        "name": "Coimbatore",
        "normalized_name": "Coimbatore",
        "entity_type": "location",
        "aliases": ["Coimbatore", "Kovai", "கோயம்புத்தூர்", "கோவை"]
    },
    {
        "entity_id": "ent_loc_tn",
        "name": "Tamil Nadu",
        "normalized_name": "Tamil Nadu",
        "entity_type": "location",
        "aliases": ["Tamil Nadu", "TN", "தமிழ்நாடு", "தமிழகம்"]
    },

    # --- CONSTITUENCIES ---
    {
        "entity_id": "ent_const_kolathur",
        "name": "Kolathur Assembly Constituency",
        "normalized_name": "Kolathur",
        "entity_type": "constituency",
        "aliases": ["Kolathur", "கொளத்தூர் தொகுதி", "கொளத்தூர்"]
    },
    {
        "entity_id": "ent_const_edappadi",
        "name": "Edappadi Assembly Constituency",
        "normalized_name": "Edappadi",
        "entity_type": "constituency",
        "aliases": ["Edappadi Constituency", "எடப்பாடி தொகுதி"]
    },

    # --- ORGANIZATIONS ---
    {
        "entity_id": "ent_org_madras_hc",
        "name": "Madras High Court",
        "normalized_name": "Madras High Court",
        "entity_type": "organization",
        "aliases": ["Madras High Court", "High Court of Madras", "சென்னை உயர்நீதிமன்றம்", "உயர்நீதிமன்றம்"]
    },
    {
        "entity_id": "ent_org_eci",
        "name": "Election Commission of India",
        "normalized_name": "Election Commission of India",
        "entity_type": "organization",
        "aliases": ["Election Commission of India", "ECI", "இந்திய தேர்தல் ஆணையம்", "தேர்தல் ஆணையம்"]
    }
]


# ---------------------------------------------------------------------------
# GROUND-TRUTH EVENT PATTERNS
# ---------------------------------------------------------------------------
KNOWN_EVENT_PATTERNS = [
    {
        "event_id": "evt_tn_budget_2026",
        "event_name": "Tamil Nadu State Budget Presentation 2026",
        "keywords": ["state budget 2026", "tn budget 2026", "பட்ஜெட் தாக்கல் 2026", "நிதிநிலை அறிக்கை 2026"]
    },
    {
        "event_id": "evt_tn_assembly_session",
        "event_name": "TN Legislative Assembly Session",
        "keywords": ["assembly session", "legislative assembly debate", "சட்டமன்றக் கூட்டம்", "சட்டமன்ற விவாதம்"]
    }
]


class EntityRecognizer:
    """Multi-granular named entity recognizer for political leaders, parties, depts, locations, constituencies, and orgs."""

    def __init__(self, gazetteer: List[Dict] = ENTITY_GAZETTEER):
        self.gazetteer = gazetteer

    def extract_mentions(self, text: str, headline: str = "") -> List[Dict[str, Any]]:
        """
        Extracts entity mentions from text and calculates frequency and positions.
        Strictly decouples entity detection from sentiment/bias logic.
        """
        if not text:
            return []

        text_lower = text.lower()
        headline_lower = headline.lower() if headline else ""
        extracted = []

        for entity in self.gazetteer:
            mention_count = 0
            found_in_headline = False
            found_in_lead = False
            first_pos = -1

            for alias in entity["aliases"]:
                alias_lower = alias.lower()
                
                # Check headline presence
                if headline_lower and alias_lower in headline_lower:
                    found_in_headline = True

                # Check body text matches
                matches = [m.start() for m in re.finditer(re.escape(alias_lower), text_lower)]
                if matches:
                    mention_count += len(matches)
                    if first_pos == -1 or matches[0] < first_pos:
                        first_pos = matches[0]

            if mention_count > 0 or found_in_headline:
                if first_pos != -1 and first_pos < 300:
                    found_in_lead = True

                extracted.append({
                    "entity_id": entity["entity_id"],
                    "name": entity["name"],
                    "normalized_name": entity["normalized_name"],
                    "entity_type": entity["entity_type"],
                    "mention_count": max(1, mention_count),
                    "found_in_headline": found_in_headline,
                    "found_in_lead": found_in_lead,
                    "first_position": first_pos
                })

        return extracted


class EntityProminenceCalculator:
    """
    Calculates numerical entity prominence score P_entity in range [0.0, 1.0]:
    P_entity = 0.4 * TitlePresence + 0.3 * LeadPresence + 0.3 * min(1.0, MentionCount / 5)
    """

    @staticmethod
    def calculate(mention_data: Dict[str, Any]) -> float:
        title_score = 0.4 if mention_data.get("found_in_headline") else 0.0
        lead_score = 0.3 if mention_data.get("found_in_lead") else 0.0
        count = mention_data.get("mention_count", 0)
        freq_score = 0.3 * min(1.0, count / 5.0)

        prominence = round(title_score + lead_score + freq_score, 3)
        return min(1.0, prominence)


class TopicClassifier:
    """Multi-label topic classifier categorizing news text across 14 policy areas."""

    def __init__(self, taxonomy: Dict[str, Dict] = TOPIC_TAXONOMY_14):
        self.taxonomy = taxonomy

    def classify(self, text: str, headline: str = "") -> List[Dict[str, Any]]:
        """Classifies text and returns topic scores sorted by relevance."""
        combined = f"{headline} {text}".lower()
        topic_results = []

        for topic_code, topic_info in self.taxonomy.items():
            if topic_code == "other":
                continue

            matches = 0
            for kw in topic_info["keywords"]:
                kw_lower = kw.lower()
                matches += len(re.findall(re.escape(kw_lower), combined))

            if matches > 0:
                relevance = min(1.0, round(matches / 3.0, 2))
                topic_results.append({
                    "topic_id": topic_code,
                    "topic_name": topic_info["name"],
                    "relevance_score": relevance,
                    "match_count": matches
                })

        # Fallback to "other" topic if no specific policy areas matched
        if not topic_results:
            topic_results.append({
                "topic_id": "other",
                "topic_name": self.taxonomy["other"]["name"],
                "relevance_score": 1.0,
                "match_count": 0
            })

        # Sort by relevance descending
        topic_results.sort(key=lambda x: x["relevance_score"], reverse=True)
        return topic_results


class EventIdentifier:
    """Ground-truth event identifier linking news text to confirmed political events."""

    def __init__(self, patterns: List[Dict] = KNOWN_EVENT_PATTERNS):
        self.patterns = patterns

    def identify_events(self, text: str, headline: str = "") -> List[Dict[str, Any]]:
        combined = f"{headline} {text}".lower()
        matched_events = []

        for evt in self.patterns:
            matches = 0
            for kw in evt["keywords"]:
                if kw.lower() in combined:
                    matches += 1

            if matches > 0:
                matched_events.append({
                    "event_id": evt["event_id"],
                    "event_name": evt["event_name"],
                    "relevance_score": min(1.0, round(matches / len(evt["keywords"]), 2))
                })

        return matched_events


class IntelligenceLayerService:
    """
    Unified Intelligence Layer coordinator running entity extraction, prominence scoring,
    14-category topic classification, and event identification on news articles.
    """

    def __init__(self):
        self.entity_recognizer = EntityRecognizer()
        self.prominence_calculator = EntityProminenceCalculator()
        self.topic_classifier = TopicClassifier()
        self.event_identifier = EventIdentifier()

    def analyze_article(self, headline: str, body_text: str) -> Dict[str, Any]:
        """
        Runs intelligence analysis on headline and body text.
        Strictly separates entity detection from sentiment and bias analysis.
        """
        # 1. Entity Extraction & Prominence Scoring
        raw_mentions = self.entity_recognizer.extract_mentions(body_text, headline=headline)
        analyzed_entities = []

        for ment in raw_mentions:
            prominence = self.prominence_calculator.calculate(ment)
            ment["prominence_score"] = prominence
            analyzed_entities.append(ment)

        # 2. 14-Category Topic Classification
        classified_topics = self.topic_classifier.classify(body_text, headline=headline)

        # 3. Ground-Truth Event Identification
        identified_events = self.event_identifier.identify_events(body_text, headline=headline)

        # Entity Breakdown Summary
        entity_counts_by_type = {}
        for ent in analyzed_entities:
            etype = ent["entity_type"]
            entity_counts_by_type[etype] = entity_counts_by_type.get(etype, 0) + 1

        return {
            "entities": analyzed_entities,
            "topics": classified_topics,
            "events": identified_events,
            "entity_summary": {
                "total_entities_detected": len(analyzed_entities),
                "entity_counts_by_type": entity_counts_by_type
            }
        }
