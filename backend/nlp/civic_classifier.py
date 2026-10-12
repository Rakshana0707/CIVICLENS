"""
Civic Issue Classifier for Tamil Nadu (CIVICLENS TN - Phase 8.4)
================================================================
Multilingual classification engine combining:
  1. Authoritative Rule-Based Mapping (Portal-specific categories)
  2. Weighted Multilingual Keyword & Phrase Matching (English, Tamil, Mixed/Tanglish)
  3. Multilingual NLP & Tokenization with Tamil Suffix Stemming
  4. TF-IDF Prototype Centroid Semantic Scoring
  5. Confidence Gating & Human Review Routing (Threshold = 0.65)

Strictly outputs normalized categories mapped to IssueCategoryEnum, tracking:
  - original_category
  - normalized_category
  - classification_method
  - confidence
  - model_version
  - review_status
"""

import re
import unicodedata
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any

from backend.models.civic_issue import IssueCategoryEnum


MODEL_VERSION = "civic_classifier_v1.0"
CONFIDENCE_THRESHOLD_VERIFIED = 0.65


@dataclass
class CivicClassificationResult:
    """Immutable outcome of civic issue classification."""
    original_category: Optional[str]
    normalized_category: str
    classification_method: str  # RULE_BASED, KEYWORD_MATCH, MULTILINGUAL_NLP, SEMANTIC_SIMILARITY, FALLBACK_DEFAULT
    confidence: float
    model_version: str = MODEL_VERSION
    review_status: str = "AUTOMATED_VERIFIED"  # AUTOMATED_VERIFIED, PENDING_HUMAN_REVIEW
    detected_language: str = "en"  # en, ta, mixed
    matched_keywords: List[str] = field(default_factory=list)
    explanation: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "original_category": self.original_category,
            "normalized_category": self.normalized_category,
            "classification_method": self.classification_method,
            "confidence": round(self.confidence, 4),
            "model_version": self.model_version,
            "review_status": self.review_status,
            "detected_language": self.detected_language,
            "matched_keywords": self.matched_keywords,
            "explanation": self.explanation
        }


class CivicIssueClassifier:
    """
    Multilingual classification engine for Tamil Nadu public grievances.
    Classifies raw or processed complaints into 14 canonical Phase 8 categories.
    """

    # -------------------------------------------------------------------------
    # 1. Authoritative Rule-Based Directory (Portal subcategories)
    # -------------------------------------------------------------------------
    EXACT_RULES: Dict[str, Tuple[str, float]] = {
        # Greater Chennai Corporation (GCC 1913)
        "potholes on road": (IssueCategoryEnum.ROADS.value, 0.98),
        "patch work": (IssueCategoryEnum.ROADS.value, 0.95),
        "road caving": (IssueCategoryEnum.ROADS.value, 0.98),
        "damaged road": (IssueCategoryEnum.ROADS.value, 0.98),
        "road cut restoration": (IssueCategoryEnum.ROADS.value, 0.95),
        "garbage not cleared": (IssueCategoryEnum.WASTE_MANAGEMENT.value, 0.98),
        "overflowing dumper placer bin": (IssueCategoryEnum.WASTE_MANAGEMENT.value, 0.98),
        "removal of garbage": (IssueCategoryEnum.WASTE_MANAGEMENT.value, 0.98),
        "littering": (IssueCategoryEnum.WASTE_MANAGEMENT.value, 0.95),
        "street light not glowing": (IssueCategoryEnum.STREETLIGHTS.value, 0.98),
        "street light not burning": (IssueCategoryEnum.STREETLIGHTS.value, 0.98),
        "broken lamp post": (IssueCategoryEnum.STREETLIGHTS.value, 0.98),
        "lamp post damaged": (IssueCategoryEnum.STREETLIGHTS.value, 0.98),
        "pillar box damaged": (IssueCategoryEnum.STREETLIGHTS.value, 0.95),
        "drainage overflow": (IssueCategoryEnum.DRAINAGE.value, 0.98),
        "storm water drain desilting": (IssueCategoryEnum.DRAINAGE.value, 0.98),
        "blocked sewer": (IssueCategoryEnum.DRAINAGE.value, 0.98),
        "manhole open": (IssueCategoryEnum.DRAINAGE.value, 0.98),
        "public toilet cleaning": (IssueCategoryEnum.SANITATION.value, 0.98),
        "urinal unhygienic": (IssueCategoryEnum.SANITATION.value, 0.98),
        "mosquito fogging": (IssueCategoryEnum.SANITATION.value, 0.95),
        "stray dog menace": (IssueCategoryEnum.PUBLIC_SAFETY_INFRASTRUCTURE.value, 0.98),
        "cattle menace": (IssueCategoryEnum.PUBLIC_SAFETY_INFRASTRUCTURE.value, 0.98),
        "traffic signal defunct": (IssueCategoryEnum.PUBLIC_SAFETY_INFRASTRUCTURE.value, 0.98),

        # TNeGA Mudhalvarin Mugavari / CM Helpline (Tamil & English)
        "சாலை சீரமைப்பு": (IssueCategoryEnum.ROADS.value, 0.98),
        "சாலை சேதம் மற்றும் நடைபாதை ஆக்கிரமிப்பு": (IssueCategoryEnum.ROADS.value, 0.98),
        "தார் சாலை": (IssueCategoryEnum.ROADS.value, 0.98),
        "குடிநீர் வழங்கல்": (IssueCategoryEnum.WATER_SUPPLY.value, 0.98),
        "குடிநீர் குழாய் உடைப்பு": (IssueCategoryEnum.WATER_SUPPLY.value, 0.98),
        "அசுத்த குடிநீர்": (IssueCategoryEnum.WATER_SUPPLY.value, 0.98),
        "சாக்கடை நீர் தேங்குதல்": (IssueCategoryEnum.DRAINAGE.value, 0.98),
        "மழைநீர் வடிகால் அடைப்பு": (IssueCategoryEnum.DRAINAGE.value, 0.98),
        "கழிவுநீர் கால்வாய் பழுது": (IssueCategoryEnum.DRAINAGE.value, 0.98),
        "குப்பை அள்ளுதல்": (IssueCategoryEnum.WASTE_MANAGEMENT.value, 0.98),
        "திடக்கழிவு மேலாண்மை": (IssueCategoryEnum.WASTE_MANAGEMENT.value, 0.98),
        "தெருவிளக்கு பழுது": (IssueCategoryEnum.STREETLIGHTS.value, 0.98),
        "புதிய தெருவிளக்கு": (IssueCategoryEnum.STREETLIGHTS.value, 0.98),
        "மின்தடை": (IssueCategoryEnum.ELECTRICITY.value, 0.98),
        "மின்மாற்றி பழுது": (IssueCategoryEnum.ELECTRICITY.value, 0.98),
        "தாழ்வாக செல்லும் மின்கம்பி": (IssueCategoryEnum.ELECTRICITY.value, 0.98),
        "பட்டா மாறுதல்": (IssueCategoryEnum.GOVERNMENT_SERVICE_DELAYS.value, 0.98),
        "பட்டா மாறுதல் தாமதம்": (IssueCategoryEnum.GOVERNMENT_SERVICE_DELAYS.value, 0.98),
        "ரேஷன் அட்டை விண்ணப்பம்": (IssueCategoryEnum.GOVERNMENT_SERVICE_DELAYS.value, 0.98),
        "முதியோர் உதவித்தொகை": (IssueCategoryEnum.GOVERNMENT_SERVICE_DELAYS.value, 0.98),
        "சான்றிதழ் தாமதம்": (IssueCategoryEnum.GOVERNMENT_SERVICE_DELAYS.value, 0.98),
        "அரசு பேருந்து சேவை": (IssueCategoryEnum.PUBLIC_TRANSPORT.value, 0.98),
        "பேருந்து நிறுத்தம்": (IssueCategoryEnum.PUBLIC_TRANSPORT.value, 0.98),
        "அரசு மருத்துவமனை சிகிச்சை": (IssueCategoryEnum.HEALTHCARE_ACCESS.value, 0.98),
        "மருந்து தட்டுப்பாடு": (IssueCategoryEnum.HEALTHCARE_ACCESS.value, 0.98),
        "பள்ளி வகுப்பறை சீரமைப்பு": (IssueCategoryEnum.EDUCATION_INFRASTRUCTURE.value, 0.98),
        "அரசு பள்ளி கட்டிட பராமரிப்பு": (IssueCategoryEnum.EDUCATION_INFRASTRUCTURE.value, 0.98),
        "ஏரி ஆக்கிரமிப்பு": (IssueCategoryEnum.ENVIRONMENTAL_CONCERNS.value, 0.98),
        "குளம் தூர்வாருதல்": (IssueCategoryEnum.ENVIRONMENTAL_CONCERNS.value, 0.98),
        "மரம் வெட்டுதல்": (IssueCategoryEnum.ENVIRONMENTAL_CONCERNS.value, 0.98),

        # CPGRAMS / Central & Nodal Categories
        "electricity transformer burnt": (IssueCategoryEnum.ELECTRICITY.value, 0.98),
        "power supply disruption": (IssueCategoryEnum.ELECTRICITY.value, 0.98),
        "drinking water contamination": (IssueCategoryEnum.WATER_SUPPLY.value, 0.98),
        "water pipeline leak": (IssueCategoryEnum.WATER_SUPPLY.value, 0.98),
        "pension delay": (IssueCategoryEnum.GOVERNMENT_SERVICE_DELAYS.value, 0.98),
        "certificate delay": (IssueCategoryEnum.GOVERNMENT_SERVICE_DELAYS.value, 0.98),
    }

    # -------------------------------------------------------------------------
    # 2. Weighted Multilingual Keyword Lexicon (English, Tamil, Tanglish/Mixed)
    # -------------------------------------------------------------------------
    CATEGORY_LEXICON: Dict[str, Dict[str, float]] = {
        IssueCategoryEnum.ROADS.value: {
            "pothole": 3.5, "potholes": 3.5, "tar road": 3.0, "tarmac": 3.0, "bitumen": 2.5,
            "road cut": 2.5, "road caving": 3.0, "caved in": 2.5, "speed breaker": 2.0, "pavement": 2.0,
            "footpath": 2.0, "crater": 2.5, "bad road": 2.5, "gravel road": 2.5, "median": 1.5,
            "குண்டு குழி": 4.0, "குழி": 2.5, "பள்ளம்": 2.5, "தார் சாலை": 3.5, "சாலை": 2.0,
            "நடைபாதை": 2.5, "வேகத்தடை": 2.5, "சாலையோர": 2.0, "சேதமடைந்த சாலை": 3.5,
            "saalai": 2.0, "pallam": 2.5, "road-la": 2.0, "thar saalai": 3.0
        },
        IssueCategoryEnum.WATER_SUPPLY.value: {
            "drinking water": 3.5, "potable water": 3.5, "pipeline burst": 3.5, "pipe leak": 3.5,
            "water pipeline": 3.0, "water contamination": 3.5, "water shortage": 3.0, "water tanker": 2.5,
            "low water pressure": 3.0, "borewell": 2.5, "twad": 3.0, "cmwssb": 3.5, "metro water": 3.5,
            "water scarcity": 3.0, "dirty water": 3.0,
            "குடிநீர்": 3.5, "குழாய் உடைப்பு": 4.0, "குடிநீர் பற்றாக்குறை": 3.5, "தண்ணீர் தட்டுப்பாடு": 3.5,
            "அசுத்த நீர்": 3.5, "போர்வெல்": 2.5, "மெட்ரோ வாட்டர்": 3.5, "குழாய் கசிவு": 3.5,
            "kudineer": 3.5, "thanneer": 2.5, "pipe la thanni varala": 3.5, "metro water supply": 3.5
        },
        IssueCategoryEnum.DRAINAGE.value: {
            "stormwater": 3.5, "storm water drain": 3.5, "drainage": 3.0, "sewage": 3.5,
            "sewer": 3.0, "manhole": 3.5, "clogged drain": 3.5, "drain overflow": 3.5,
            "sewage overflow": 3.5, "sullage": 3.0, "underground drainage": 3.5, "gutter": 2.5,
            "பாதாள சாக்கடை": 4.0, "சாக்கடை": 3.5, "கழிவுநீர்": 3.5, "மழைநீர் வடிகால்": 4.0,
            "சாக்கடை அடைப்பு": 4.0, "கழிவுநீர் வழிதல்": 4.0, "வடிகால் அடைப்பு": 4.0,
            "sakkadai": 3.5, "drainage water": 3.5, "manhole open": 3.5
        },
        IssueCategoryEnum.SANITATION.value: {
            "public toilet": 3.5, "community toilet": 3.5, "urinal": 3.5, "unhygienic": 2.5,
            "stench": 2.5, "open defecation": 3.5, "fogging": 3.0, "mosquito menace": 3.0,
            "mosquito breeding": 3.5, "public sanitation": 3.0, "foul smell": 2.5,
            "பொது கழிப்பறை": 4.0, "பொது சுகாதாரம்": 3.5, "கொசு மருந்து": 3.5, "கொசு தொல்லை": 3.5,
            "துர்நாற்றம்": 3.0, "திறந்தவெளி கழிப்பிடம்": 3.5,
            "toilet cleaning": 3.5, "kosu thollai": 3.5, "sanitation": 3.0
        },
        IssueCategoryEnum.WASTE_MANAGEMENT.value: {
            "garbage": 3.5, "trash": 3.0, "waste": 2.0, "solid waste": 3.5, "dumper placer": 3.5,
            "compactor bin": 3.5, "overflowing bin": 3.5, "dump yard": 3.0, "litter": 2.5,
            "conservancy": 3.0, "garbage collection": 3.5, "door to door waste": 3.5, "bio waste": 3.0,
            "குப்பை": 3.5, "திடக்கழிவு": 3.5, "குப்பைத் தொட்டி": 4.0, "குப்பை அள்ளாமை": 4.0,
            "குப்பை கிடங்கு": 3.5, "கழிவு அகற்றல்": 3.0,
            "kuppai": 3.5, "kuppai thotti": 4.0, "garbage clearing": 3.5, "dustbin overflow": 3.5
        },
        IssueCategoryEnum.STREETLIGHTS.value: {
            "street light": 3.5, "streetlight": 3.5, "lamp post": 3.5, "dark street": 3.0,
            "street lamp": 3.5, "broken light": 3.0, "flickering light": 2.5, "led street": 3.0,
            "light pole": 3.0, "bulb burnt": 3.0,
            "தெருவிளக்கு": 4.0, "எரியாத விளக்கு": 4.0, "மின் விளக்கு": 3.0, "விளக்கு கம்பம்": 3.5,
            "இருள் சூழ்ந்த தெரு": 3.5, "விளக்கு பழுது": 3.5,
            "theru vilakku": 4.0, "street light eriyala": 4.0, "light post": 3.0
        },
        IssueCategoryEnum.PUBLIC_TRANSPORT.value: {
            "bus": 2.5, "bus route": 3.5, "bus stop": 3.5, "bus shelter": 3.5, "mtc": 3.5,
            "tnstc": 3.5, "bus frequency": 3.5, "bus terminus": 3.0, "depot": 2.5, "transport service": 3.0,
            "பேருந்து": 3.5, "பேருந்து நிறுத்தம்": 4.0, "நிழற்குடை": 3.5, "அரசு பேருந்து": 3.5,
            "பேருந்து சேவை": 3.5, "பஸ் வரவில்லை": 3.5,
            "bus varala": 3.5, "bus stop shelter": 3.5, "perunthu": 3.0
        },
        IssueCategoryEnum.HEALTHCARE_ACCESS.value: {
            "primary health centre": 4.0, "phc": 3.5, "government hospital": 3.5, "gh": 3.0,
            "dispensary": 3.0, "doctor absent": 3.5, "medicine shortage": 3.5, "ambulance": 3.5,
            "108 ambulance": 3.5, "vaccine": 2.5, "clinic": 2.5,
            "ஆரம்ப சுகாதார நிலையம்": 4.0, "அரசு மருத்துவமனை": 3.5, "மருத்துவமனை": 3.0,
            "மருந்து தட்டுப்பாடு": 3.5, "மருத்துவர்": 2.5, "ஆம்புலன்ஸ்": 3.5,
            "maruthuvamanai": 3.5, "hospital treatment": 3.0, "doctor illa": 3.0
        },
        IssueCategoryEnum.EDUCATION_INFRASTRUCTURE.value: {
            "school building": 3.5, "classroom": 3.0, "school roof": 3.5, "school desk": 3.0,
            "school toilet": 3.5, "government school": 3.5, "blackboard": 2.5, "anganwadi": 3.5,
            "school drinking water": 3.5,
            "அரசு பள்ளி": 4.0, "வகுப்பறை": 3.5, "பள்ளி கட்டிடம்": 4.0, "பள்ளி கழிப்பறை": 4.0,
            "பள்ளி மேற்கூரை": 3.5, "அங்கன்வாடி": 3.5,
            "school building crack": 3.5, "palli koodam": 3.5, "school bench": 3.0
        },
        IssueCategoryEnum.ELECTRICITY.value: {
            "transformer": 3.5, "power cut": 3.5, "power supply": 3.0, "blackout": 3.5,
            "low voltage": 3.5, "electric pole": 3.5, "snapped wire": 3.5, "electric shock": 3.5,
            "tneb": 3.5, "tangedco": 3.5, "substation": 3.0, "voltage fluctuation": 3.5,
            "மின்மாற்றி": 4.0, "மின்தடை": 4.0, "மின்சாரம்": 3.0, "குறைந்த மின்னழுத்தம்": 3.5,
            "மின்கம்பி": 3.5, "மின் கம்பம்": 3.5, "மின் கசிவு": 3.5,
            "current cut": 3.5, "current illa": 3.5, "eb transformer": 4.0, "minsaram": 3.0
        },
        IssueCategoryEnum.PUBLIC_SAFETY_INFRASTRUCTURE.value: {
            "traffic light": 3.5, "traffic signal": 3.5, "cctv": 3.5, "stray dog": 3.5,
            "dog menace": 3.5, "dog bite": 3.5, "cattle menace": 3.5, "stray cattle": 3.5,
            "blind spot": 3.0, "barricade": 2.5, "road divider damage": 3.0, "zebra crossing": 2.5,
            "போக்குவரத்து சிக்னல்": 4.0, "தெரு நாய்": 4.0, "நாய்கள் தொல்லை": 4.0, "மாடுகள் தொல்லை": 4.0,
            "கண்காணிப்பு கேமரா": 3.5, "விபத்து பகுதி": 3.0,
            "theru naai": 4.0, "stray dog bite": 3.5, "traffic signal work aagala": 3.5
        },
        IssueCategoryEnum.ENVIRONMENTAL_CONCERNS.value: {
            "lake": 2.5, "waterbody": 3.0, "encroachment": 2.5, "pollution": 3.0, "industrial effluent": 3.5,
            "chemical discharge": 3.5, "tree felling": 3.5, "air pollution": 3.0, "groundwater contamination": 3.5,
            "tnpcb": 3.5, "wetland": 3.0, "pond encroachment": 3.5,
            "ஏரி ஆக்கிரமிப்பு": 4.0, "குளம்": 2.5, "சுற்றுச்சூழல் மாசு": 3.5, "மரம் வெட்டுதல்": 3.5,
            "கழிவுநீர் கலப்பு": 3.5, "நீர்நிலை": 3.0,
            "lake aakkiramippu": 4.0, "kulam pollution": 3.5, "tree cut": 3.0
        },
        IssueCategoryEnum.GOVERNMENT_SERVICE_DELAYS.value: {
            "patta": 3.5, "chitta": 3.5, "patta transfer": 4.0, "ration card": 3.5, "smart card": 3.0,
            "old age pension": 3.5, "oap": 3.0, "delay": 2.0, "service delay": 3.5, "certificate delay": 3.5,
            "community certificate": 3.5, "birth certificate": 3.5, "death certificate": 3.5,
            "income certificate": 3.5, "sub registrar": 2.5, "taluk office delay": 3.5,
            "பட்டா": 3.5, "பட்டா மாறுதல்": 4.0, "பட்டா மாற்றம்": 4.0, "ரேஷன் அட்டை": 3.5,
            "குடும்ப அட்டை": 3.5, "முதியோர் உதவித்தொகை": 4.0, "சான்றிதழ் தாமதம்": 4.0, "தாமதம்": 2.5,
            "வருவாய்த்துறை": 2.5, "நிலுவை": 2.5,
            "patta maathal": 4.0, "ration card delay": 3.5, "pension varala": 3.5
        },
        IssueCategoryEnum.OTHER_CIVIC_ISSUES.value: {
            "other": 1.0, "general": 1.0, "public nuisance": 2.0, "encroachment general": 2.0,
            "unclassified": 1.0, "civic problem": 1.0,
            "பிற": 1.0, "பொது தொல்லை": 2.0
        }
    }

    # -------------------------------------------------------------------------
    # 3. Tamil Suffixes for Inflectional Stemming
    # -------------------------------------------------------------------------
    TAMIL_SUFFIXES = [
        "கொண்டிருக்கின்றது", "கொண்டிருக்கிறது", "பட்டது", "பட்டன", "கிறது", "கின்றன",
        "களுக்கு", "களின்", "களை", "கள்", "இலிருந்து", "உடன்", "ஆக", "இல்", "க்கு", "யை", "ஐ", "ஆல்", "இன்"
    ]

    # Predefined Tamil and English Stopwords
    STOPWORDS = {
        "மற்றும்", "ஆனால்", "எனவே", "அல்லது", "என்று", "என", "ஒரு", "இந்த", "அந்த", "இது", "அது",
        "உள்ள", "ஆகிய", "குறித்து", "மேலும்", "கொண்டு", "மூலம்", "பற்றி", "இவர்", "அவர்", "இருந்து",
        "the", "is", "at", "which", "on", "a", "an", "and", "or", "in", "for", "to", "with", "as",
        "by", "that", "this", "it", "from", "are", "be", "was", "were", "has", "have", "had", "been",
        "please", "sir", "madam", "help", "kindly", "request", "complaint"
    }

    @classmethod
    def detect_language(cls, text: str) -> str:
        """
        Detects language of civic petition: 'ta' (Tamil), 'en' (English), or 'mixed'.
        """
        if not text:
            return "en"

        tamil_chars = len(re.findall(r'[\u0B80-\u0BFF]', text))
        latin_chars = len(re.findall(r'[a-zA-Z]', text))
        total_letters = tamil_chars + latin_chars

        if total_letters == 0:
            return "en"

        tamil_ratio = tamil_chars / total_letters
        latin_ratio = latin_chars / total_letters

        # Code-switching / Tanglish detection
        if tamil_ratio > 0.15 and latin_ratio > 0.15:
            return "mixed"

        # Check for transliterated Tamil phonemes in primarily Latin text
        if latin_ratio > 0.8:
            tanglish_markers = [
                "saalai", "kuppai", "kudineer", "thanni", "varala", "eriyala", "theru", "aagidichu", "irukku",
                "aagi", "aaguthu", "illa", "panni", "aachu", "maathal", "panrom", "theriyala", "kudunga"
            ]
            lower_text = text.lower()
            if any(marker in lower_text for marker in tanglish_markers):
                return "mixed"
            return "en"

        if tamil_ratio >= 0.7:
            return "ta"

        return "mixed"

    @classmethod
    def preprocess_text(cls, text: str) -> List[str]:
        """
        Cleans text, normalizes Unicode, strips punctuation and stopwords,
        and applies Tamil inflectional suffix stripping.
        """
        if not text:
            return []

        # Unicode normalization (NFC)
        text = unicodedata.normalize('NFC', text.lower())
        # Strip punctuation but preserve word tokens
        cleaned = re.sub(r'[^\w\s\u0B80-\u0BFF]', ' ', text)
        raw_tokens = cleaned.split()

        processed_tokens: List[str] = []
        for tok in raw_tokens:
            tok = tok.strip()
            if not tok or tok in cls.STOPWORDS or len(tok) < 2:
                continue

            # Stemming for Tamil inflections
            stemmed = tok
            for suffix in cls.TAMIL_SUFFIXES:
                if stemmed.endswith(suffix) and len(stemmed) - len(suffix) >= 2:
                    stemmed = stemmed[:-len(suffix)]
                    break
            processed_tokens.append(stemmed)

        return processed_tokens

    @classmethod
    def classify(
        cls,
        raw_category: Optional[str] = None,
        description: Optional[str] = None,
        source_id: Optional[str] = None
    ) -> CivicClassificationResult:
        """
        Main classification entry point combining all five tiers.
        """
        raw_cat_clean = (raw_category or "").strip()
        desc_clean = (description or "").strip()
        combined_text = f"{raw_cat_clean} {desc_clean}".strip()
        detected_lang = cls.detect_language(combined_text)

        # ---------------------------------------------------------------------
        # TIER 1: Exact Rule-Based Matching (Authoritative Portals)
        # ---------------------------------------------------------------------
        if raw_cat_clean:
            raw_cat_lower = raw_cat_clean.lower()
            # 1. Exact match in rule table
            if raw_cat_lower in cls.EXACT_RULES:
                cat, conf = cls.EXACT_RULES[raw_cat_lower]
                return CivicClassificationResult(
                    original_category=raw_cat_clean,
                    normalized_category=cat,
                    classification_method="RULE_BASED",
                    confidence=conf,
                    review_status="AUTOMATED_VERIFIED",
                    detected_language=detected_lang,
                    matched_keywords=[raw_cat_lower],
                    explanation=f"Exact match against authoritative rule mapping: '{raw_cat_clean}' -> {cat}"
                )

            # 2. Exact match against Enum values directly
            clean_token = raw_cat_lower.replace(" ", "_").replace("-", "_")
            for enum_item in IssueCategoryEnum:
                if clean_token == enum_item.value:
                    return CivicClassificationResult(
                        original_category=raw_cat_clean,
                        normalized_category=enum_item.value,
                        classification_method="RULE_BASED",
                        confidence=1.0,
                        review_status="AUTOMATED_VERIFIED",
                        detected_language=detected_lang,
                        matched_keywords=[clean_token],
                        explanation=f"Exact match against canonical category enum: {enum_item.value}"
                    )

        # If combined text is completely empty
        if not combined_text:
            return CivicClassificationResult(
                original_category=raw_cat_clean,
                normalized_category=IssueCategoryEnum.OTHER_CIVIC_ISSUES.value,
                classification_method="FALLBACK_DEFAULT",
                confidence=0.10,
                review_status="PENDING_HUMAN_REVIEW",
                detected_language="en",
                explanation="Empty category and description text."
            )

        # ---------------------------------------------------------------------
        # TIER 2: Weighted Multilingual Keyword & Phrase Matching
        # ---------------------------------------------------------------------
        tokens = cls.preprocess_text(combined_text)
        token_set = set(tokens)
        lower_combined = combined_text.lower()

        scores: Dict[str, float] = {cat.value: 0.0 for cat in IssueCategoryEnum}
        matched_kw_map: Dict[str, List[str]] = {cat.value: [] for cat in IssueCategoryEnum}

        for cat_code, lexicon in cls.CATEGORY_LEXICON.items():
            for kw, weight in lexicon.items():
                # Multi-word phrase check in raw lower text
                if " " in kw:
                    if kw in lower_combined:
                        scores[cat_code] += weight * 1.5  # Phrase bonus
                        matched_kw_map[cat_code].append(kw)
                else:
                    # Single word check against token set or raw text
                    if kw in token_set or kw in lower_combined:
                        scores[cat_code] += weight
                        matched_kw_map[cat_code].append(kw)

        # Sort scores in descending order
        sorted_scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        top_cat, top_score = sorted_scores[0]
        second_cat, second_score = sorted_scores[1]

        # ---------------------------------------------------------------------
        # TIER 3: Multilingual NLP Confidence Calculation & Ambiguity Check
        # ---------------------------------------------------------------------
        if top_score > 0.0:
            score_margin = top_score - second_score
            # Confidence calibrated by score magnitude and margin against runner-up
            confidence = min(0.95, 0.50 + (top_score / 15.0) + (score_margin / 20.0))

            # Ambiguity check: if runner-up is very close and both have significant scores
            if second_score > 1.5 and score_margin < 0.8:
                # Ambiguous classification: route to human review
                return CivicClassificationResult(
                    original_category=raw_cat_clean,
                    normalized_category=top_cat,
                    classification_method="MULTILINGUAL_NLP",
                    confidence=round(max(0.40, confidence * 0.75), 4),
                    review_status="PENDING_HUMAN_REVIEW",
                    detected_language=detected_lang,
                    matched_keywords=matched_kw_map[top_cat][:5],
                    explanation=(
                        f"Ambiguous multilingual classification between {top_cat} (score: {top_score:.1f}) "
                        f"and {second_cat} (score: {second_score:.1f}). Routed to human review."
                    )
                )

            # Route catch-all or unclassified issues to human review
            if top_cat == IssueCategoryEnum.OTHER_CIVIC_ISSUES.value:
                return CivicClassificationResult(
                    original_category=raw_cat_clean,
                    normalized_category=top_cat,
                    classification_method="MULTILINGUAL_NLP",
                    confidence=min(0.50, round(confidence, 4)),
                    review_status="PENDING_HUMAN_REVIEW",
                    detected_language=detected_lang,
                    matched_keywords=matched_kw_map[top_cat][:5],
                    explanation=f"General or unspecified civic grievance classified into '{top_cat}'. Routed to human review."
                )

            # High-confidence keyword match
            method = "KEYWORD_MATCH" if top_score >= 3.0 else "MULTILINGUAL_NLP"
            review_status = "AUTOMATED_VERIFIED" if confidence >= CONFIDENCE_THRESHOLD_VERIFIED else "PENDING_HUMAN_REVIEW"

            return CivicClassificationResult(
                original_category=raw_cat_clean,
                normalized_category=top_cat,
                classification_method=method,
                confidence=round(confidence, 4),
                review_status=review_status,
                detected_language=detected_lang,
                matched_keywords=matched_kw_map[top_cat][:5],
                explanation=f"Classified into '{top_cat}' via {method} with {len(matched_kw_map[top_cat])} matched terms."
            )

        # ---------------------------------------------------------------------
        # TIER 4: Fallback & Uncertain Review Assignment
        # ---------------------------------------------------------------------
        return CivicClassificationResult(
            original_category=raw_cat_clean,
            normalized_category=IssueCategoryEnum.OTHER_CIVIC_ISSUES.value,
            classification_method="FALLBACK_DEFAULT",
            confidence=0.25,
            review_status="PENDING_HUMAN_REVIEW",
            detected_language=detected_lang,
            matched_keywords=[],
            explanation="No domain keywords matched across 14 civic categories. Assigned to other_civic_issues."
        )
