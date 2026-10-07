import re
import unicodedata
from backend.core.logger import setup_logger

logger = setup_logger("civiclens.nlp.news_analyzer")

# Predefined political taxonomy keywords for topic classification
TOPIC_TAXONOMY = {
    "TOPIC_BUDGET_ECONOMY": {
        "name": "Budget & Economy",
        "keywords": ["budget", "finance", "tax", "allocation", "crore", "economy", "revenue", "நிதி", "வரவு செலவு", "பட்ஜெட்", "வரி", "முதலீடு", "பொருளாதாரம்"]
    },
    "TOPIC_EDUCATION": {
        "name": "Education & Youth",
        "keywords": ["school", "university", "education", "student", "teacher", "scholarship", "கல்லூரி", "பள்ளி", "கல்வி", "மாணவர்", "ஆசிரியர்", "பல்கலைக்கழகம்"]
    },
    "TOPIC_HEALTHCARE": {
        "name": "Healthcare & Public Health",
        "keywords": ["hospital", "health", "medical", "doctor", "medicine", "dengue", "மருத்துவமனை", "சுகாதாரம்", "மருத்துவம்", "டாக்டர்", "சிகிச்சை"]
    },
    "TOPIC_AGRICULTURE": {
        "name": "Agriculture & Rural Development",
        "keywords": ["farmer", "agriculture", "crop", "irrigation", "monsoon", "paddy", "விவசாயி", "வேளாண்மை", "பயிர்", "பாசனம்", "விவசாயம்", "நெல்"]
    },
    "TOPIC_INFRASTRUCTURE": {
        "name": "Infrastructure & Transport",
        "keywords": ["metro", "road", "bridge", "bus", "railway", "power", "electricity", "சாலை", "பாலம்", "பேருந்து", "மின்சாரம்", "மெட்ரோ", "போக்குவரத்து"]
    },
    "TOPIC_ELECTIONS_GOVERNANCE": {
        "name": "Elections & Party Governance",
        "keywords": ["election", "vote", "campaign", "party", "assembly", "constituency", "தேர்தல்", "வாக்கு", "பிரச்சாரம்", "கட்சி", "சட்டமன்றம்", "தொகுதி"]
    }
}

# Predefined gazetteer of key political entities in Tamil Nadu
POLITICAL_GAZETTEER = [
    {"entity_id": "ent_party_dmk", "name": "DMK", "normalized_name": "DMK", "type": "political_party", "aliases": ["DMK", "Dravida Munnetra Kazhagam", "திமுக", "திராவிட முன்னேற்றக் கழகம்"]},
    {"entity_id": "ent_party_aiadmk", "name": "AIADMK", "normalized_name": "AIADMK", "type": "political_party", "aliases": ["AIADMK", "ADMK", "All India Anna Dravida Munnetra Kazhagam", "அதிமுக", "அனைத்திந்திய அண்ணா திராவிட முன்னேற்றக் கழகம்"]},
    {"entity_id": "ent_party_bjp", "name": "BJP", "normalized_name": "BJP", "type": "political_party", "aliases": ["BJP", "Bharatiya Janata Party", "பாஜக", "பாரதிய ஜனதா கட்சி"]},
    {"entity_id": "ent_party_inc", "name": "INC", "normalized_name": "INC", "type": "political_party", "aliases": ["Congress", "INC", "Indian National Congress", "காங்கிரஸ்"]},
    {"entity_id": "ent_party_ntk", "name": "NTK", "normalized_name": "NTK", "type": "political_party", "aliases": ["NTK", "Naam Tamilar Katchi", "நாம் தமிழர் கட்சி"]},
    {"entity_id": "ent_party_vck", "name": "VCK", "normalized_name": "VCK", "type": "political_party", "aliases": ["VCK", "Viduthalai Chiruthaigal Katchi", "விடுதலை சிறுத்தைகள் கட்சி"]},
    {"entity_id": "ent_person_cm_mkstalin", "name": "M.K. Stalin", "normalized_name": "M.K. Stalin", "type": "person", "aliases": ["M.K. Stalin", "Stalin", "Chief Minister Stalin", "மு.க. ஸ்டாலின்", "ஸ்டாலின்", "முதல்வர்"]},
    {"entity_id": "ent_person_eps", "name": "Edappadi K. Palaniswami", "normalized_name": "Edappadi K. Palaniswami", "type": "person", "aliases": ["Edappadi K. Palaniswami", "EPS", "Palaniswami", "எடப்பாடி பழனிசாமி", "இபிஎஸ்"]},
    {"entity_id": "ent_dept_finance", "name": "Department of Finance", "normalized_name": "Department of Finance", "type": "government_department", "aliases": ["Finance Department", "Ministry of Finance", "நிதித்துறை", "நிதி அமைச்சகம்"]}
]


class TamilNewsAnalyzer:
    """
    NLP analysis engine for Tamil and English political news text.
    Handles language detection, Unicode normalization, entity extraction,
    topic classification, and multi-dimensional feature calculation.
    """

    @staticmethod
    def detect_language(text):
        """Identifies language ('ta' for Tamil, 'en' for English) based on script range."""
        if not text:
            return "en"
        tamil_chars = sum(1 for c in text if '\u0B80' <= c <= '\u0BFF')
        total_alpha = sum(1 for c in text if c.isalpha())
        if total_alpha > 0 and (tamil_chars / total_alpha) > 0.15:
            return "ta"
        return "en"

    @staticmethod
    def normalize_tamil_text(text):
        """Performs NFKC Unicode normalization and removes zero-width characters."""
        if not text:
            return ""
        normalized = unicodedata.normalize("NFKC", text)
        # Remove zero-width non-joiner (\u200C) and zero-width joiner (\u200D)
        normalized = re.sub(r'[\u200c\u200d\u200b]', '', normalized)
        # Standardize multiple spaces
        normalized = re.sub(r'\s+', ' ', normalized).strip()
        return normalized

    def extract_entities(self, text):
        """Extracts political entities mentioned in the text with prominence scores."""
        if not text:
            return []

        text_lower = text.lower()
        extracted = []

        for entity in POLITICAL_GAZETTEER:
            mention_count = 0
            first_pos = -1

            for alias in entity["aliases"]:
                # Match alias with word boundaries where appropriate
                pattern = re.escape(alias.lower())
                matches = [m.start() for m in re.finditer(pattern, text_lower)]
                if matches:
                    mention_count += len(matches)
                    if first_pos == -1 or matches[0] < first_pos:
                        first_pos = matches[0]

            if mention_count > 0:
                # Prominence score: Higher if mentioned early in the text and frequently
                lead_bonus = 0.4 if (first_pos != -1 and first_pos < 200) else 0.1
                freq_score = min(0.6, (mention_count / 5.0) * 0.6)
                prominence_score = round(lead_bonus + freq_score, 3)

                extracted.append({
                    "entity_id": entity["entity_id"],
                    "name": entity["name"],
                    "type": entity["type"],
                    "mention_count": mention_count,
                    "prominence_score": prominence_score,
                    "sentiment_score": 0.0 # Neutral baseline signal
                })

        return extracted

    def classify_topics(self, text):
        """Classifies text into political topics based on taxonomy keyword matching."""
        if not text:
            return []

        text_lower = text.lower()
        topic_scores = []

        for topic_code, topic_info in TOPIC_TAXONOMY.items():
            matches = 0
            for kw in topic_info["keywords"]:
                matches += len(re.findall(re.escape(kw.lower()), text_lower))

            if matches > 0:
                relevance = min(1.0, round(matches / 3.0, 2))
                topic_scores.append({
                    "topic_id": topic_code,
                    "topic_name": topic_info["name"],
                    "relevance_score": relevance
                })

        # Sort by relevance descending
        topic_scores.sort(key=lambda x: x["relevance_score"], reverse=True)
        return topic_scores

    def extract_features(self, headline, body_text):
        """Extracts multi-dimensional linguistic signals for neutral framing analysis."""
        combined_text = f"{headline}\n{body_text}"
        words = combined_text.split()
        word_count = len(words)

        # Quote detection heuristics (matches "..." or “...”)
        quotes = re.findall(r'["“][^"”]{5,}[Wait"”]', combined_text)
        quote_count = len(quotes)

        # Official source citations (matches "official statement", "press release", "DIPR", "அறிக்கை", "அரசாணை")
        official_citations = re.findall(r'(press release|official statement|dipr|government order|அறிக்கை|அரசாணை|செய்திக்குறிப்பு)', combined_text, re.I)
        official_citation_count = len(official_citations)

        # Lexical diversity / vocabulary richness (unique word ratio)
        unique_words = set(w.lower() for w in words)
        vocab_richness = round(len(unique_words) / max(1, word_count), 3)

        # Rule-based sentiment signals (Rule: non-subjective baseline scoring)
        headline_sentiment = 0.0
        body_sentiment = 0.0

        return {
            "headline_sentiment": headline_sentiment,
            "body_sentiment": body_sentiment,
            "quote_count": quote_count,
            "official_source_citation_count": official_citation_count,
            "word_count": word_count,
            "vocabulary_richness": vocab_richness,
            "framing_indicators": {
                "has_direct_quotes": quote_count > 0,
                "has_official_citation": official_citation_count > 0,
                "length_category": "deep_analysis" if word_count > 400 else ("standard" if word_count > 150 else "brief")
            }
        }
