"""
Phase 7.4 — Claim Decomposition & Multilingual NLP Pipeline.

Implements the end-to-end claim processing pipeline for Tamil, English, and mixed-language content:
ORIGINAL CLAIM
→ LANGUAGE DETECTION
→ TEXT NORMALIZATION
→ CLAIM TYPE CLASSIFICATION
→ ATOMIC CLAIM DECOMPOSITION
→ ENTITY EXTRACTION
→ DATE/NUMBER EXTRACTION
→ VERIFIABILITY ASSESSMENT

Preserves verbatim original claim wording.
Decomposes compound statements into atomic verifiable propositions.
Distinguishes factual claims from opinions, predictions, value judgments, rhetorical questions, slogans, and ambiguity.
Preserves units, denominators, timeframes, baselines, and Tamil text integrity.
"""

import re
import unicodedata
from datetime import datetime, timezone
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy.orm import Session

from backend.models.claim import (
    Claim,
    AtomicClaim,
    VerifiabilityStatus,
    AtomicClaimType
)
from backend.nlp.preprocessing import normalize_unicode, normalize_whitespace
from backend.core.logger import setup_logger

logger = setup_logger("civiclens.phase7.nlp_decomposition")


# ---------------------------------------------------------------------------
# 1. Linguistic Entities & Known Lexicon
# ---------------------------------------------------------------------------
KNOWN_ENTITIES = {
    "LEADERS": {
        "M.K. Stalin": ["stalin", "m.k. stalin", "mk stalin", "முதல்வர் ஸ்டாலின்", "மு.க. ஸ்டாலின்", "ஸ்டாலின்"],
        "Edappadi K. Palaniswami": ["edappadi", "eps", "edappadi palaniswami", "பழனிசாமி", "எடப்பாடி", "எடப்பாடி பழனிசாமி"],
        "K. Annamalai": ["annamalai", "k. annamalai", "அண்ணாமலை"],
        "Seeman": ["seeman", "சீமான்", "செந்தமிழன் சீமான்"],
        "O. Panneerselvam": ["ops", "panneerselvam", "பன்னீர்செல்வம்", "ஓபிஎஸ்"],
        "Udhayanidhi Stalin": ["udhayanidhi", "udhay", "உதயநிதி", "உதயநிதி ஸ்டாலின்"],
        "Vijay": ["vijay", "actor vijay", "தளபதி விஜய்", "விஜய்"]
    },
    "PARTIES": {
        "DMK": ["dmk", "திராவிட முன்னேற்றக் கழகம்", "திமுக", "தி.மு.க"],
        "AIADMK": ["aiadmk", "அதிமுக", "அண்ணா திராவிட முன்னேற்றக் கழகம்", "அ.தி.மு.க"],
        "BJP": ["bjp", "பாரதிய ஜனதா", "பாஜக", "பா.ஜ.க"],
        "INC": ["congress", "காங்கிரஸ்"],
        "NTK": ["ntk", "நாம் தமிழர்", "நாம் தமிழர் கட்சி"],
        "PMK": ["pmk", "பாமக", "பாகமுக"],
        "VCK": ["vck", "விடுதலைச் சிறுத்தைகள்", "விசிக"]
    },
    "SCHEMES": {
        "Kalaignar Magalir Urimai Thittam": [
            "kalaignar magalir urimai thittam", "kmut", "magalir urimai", "மகளிர் உரிமைத் திட்டம்",
            "கலைஞர் மகளிர் உரிமை", "உரிமைத்தொகை"
        ],
        "Pudhumai Penn": ["pudhumai penn", "புதுமைப் பெண்", "மூவலூர் ராமாமிர்தம் அம்மையார் திட்டம்"],
        "Naan Mudhalvan": ["naan mudhalvan", "நான் முதல்வன்"],
        "Makkalai Thedi Maruthuvam": ["makkalai thedi maruthuvam", "மக்களைத் தேடி மருத்துவம்"],
        "Chief Minister Breakfast Scheme": ["breakfast scheme", "காலை உணவுத் திட்டம்", "முதலமைச்சரின் காலை உணவு"],
        "Illam Thedi Kalvi": ["illam thedi kalvi", "இல்லம் தேடிக் கல்வி"]
    },
    "DEPARTMENTS": {
        "Finance Department": ["finance department", "நிதித்துறை", "பட்ஜெட்"],
        "School Education": ["school education", "பள்ளிக் கல்வித்துறை"],
        "Health & Family Welfare": ["health department", "சுகாதாரத்துறை", "மருத்துவத்துறை"],
        "Public Works": ["pwd", "பொதுப்பணித்துறை"],
        "Transport Department": ["transport department", "போக்குவரத்துத்துறை"]
    },
    "GEOGRAPHIC_REGIONS": {
        "Tamil Nadu": ["tamil nadu", "tn", "தமிழ்நாடு", "தமிழகம்", "மாநிலம்"],
        "Chennai": ["chennai", "சென்னை"],
        "Coimbatore": ["coimbatore", "கோவை", "கோயம்புத்தூர்"],
        "Madurai": ["madurai", "மதுரை"],
        "Tiruchirappalli": ["trichy", "திருச்சி", "திருச்சிராப்பள்ளி"],
        "Salem": ["salem", "சேலம்"]
    }
}


# ---------------------------------------------------------------------------
# 2. Pipeline Stage 1: Language Detection
# ---------------------------------------------------------------------------
class LanguageDetector:
    """
    Detects language of input text: Tamil ('ta'), English ('en'), or mixed ('mixed').
    """
    TAMIL_RANGE = re.compile(r'[\u0B80-\u0BFF]')
    LATIN_RANGE = re.compile(r'[a-zA-Z]')

    @classmethod
    def detect(cls, text: str) -> str:
        if not text or not text.strip():
            return "en"

        tamil_chars = len(cls.TAMIL_RANGE.findall(text))
        latin_chars = len(cls.LATIN_RANGE.findall(text))
        total_letters = tamil_chars + latin_chars

        if total_letters == 0:
            return "en"

        tamil_ratio = tamil_chars / total_letters
        latin_ratio = latin_chars / total_letters

        # Code-switched / Tanglish mixed threshold
        if tamil_ratio >= 0.15 and latin_ratio >= 0.15:
            return "mixed"

        if tamil_ratio > 0.70:
            return "ta"

        return "en"


# ---------------------------------------------------------------------------
# 3. Pipeline Stage 2: Text Normalization
# ---------------------------------------------------------------------------
class TextNormalizer:
    """
    Normalizes Unicode and whitespace while preserving original characters intact.
    """
    ZERO_WIDTH = re.compile(r'[\u200B\u200C\u200D\uFEFF]')

    @classmethod
    def normalize(cls, text: str) -> str:
        if not text:
            return ""
        # 1. Unicode NFC composition
        nfc = unicodedata.normalize("NFC", text)
        # 2. Strip zero-width markers
        cleaned = cls.ZERO_WIDTH.sub('', nfc)
        # 3. Whitespace normalization
        return normalize_whitespace(cleaned)


# ---------------------------------------------------------------------------
# 4. Pipeline Stage 3: Verifiability & Subjectivity Classifier
# ---------------------------------------------------------------------------
class VerifiabilityClassifier:
    """
    Distinguishes factual claims from:
    - opinions
    - predictions
    - value judgments
    - rhetorical questions
    - slogans
    - ambiguous statements
    """
    OPINION_PATTERNS = [
        r'\b(?:i believe|in my opinion|we feel|we think|in our view)\b',
        r'\b(?:best|greatest|fantastic|brilliant|wonderful|masterpiece)\b',
        r'\b(?:disastrous|worst|shameful|terrible|pathetic)\b',
        r'என்\s*கருத்து',
        r'நான்\s*கருதுகிறேன்',
        r'சிறப்பான\s*ஆட்சி',
        r'மிகச்\s*சிறந்த',
        r'மோசமான\s*அரசு',
        r'துரோகம்\s*செய்துவிட்டது',
        r'பெருமை\s*கொள்கிறோம்'
    ]

    PREDICTION_PATTERNS = [
        r'\b(?:by \d{4} will|in future will|will become|going to be|projected to reach)\b',
        r'\b(?:we will win|they will be defeated|promise that we will achieve)\b',
        r'\d{4}[-க்]*குள்\s*(?:மாறும்|வெல்வோம்|வளரும்|சென்றடையும்)',
        r'அடுத்த\s*தேர்தலில்',
        r'வெல்வோம்',
        r'வெற்றி\s*பெறுவோம்',
        r'ஆகிவிடும்',
        r'நடைபெறவிருக்கிறது'
    ]

    VALUE_JUDGMENT_PATTERNS = [
        r'\b(?:corrupt to the core|unethical|immoral|evil|noble deed|righteous)\b',
        r'அயோக்கியத்தனமான',
        r'புனிதமான',
        r'அநீதியான',
        r'கொடுங்கோல்'
    ]

    RHETORICAL_QUESTION_PATTERNS = [
        r'\?$',
        r'\b(?:can anyone deny|why should people trust|who asked them to|what did they do)\b',
        r'மக்களுக்கு\s*என்ன\s*செய்தது\?',
        r'யாராவது\s*மறுக்க\s*முடியுமா\?',
        r'எப்படி\s*நம்புவது\?'
    ]

    SLOGAN_PATTERNS = [
        r'\b(?:long live|vote for|victory is ours|together we shall rise)\b',
        r'வெல்வோம்[!\s]+வெல்வோம்',
        r'வளர்க\s*தமிழ்நாடு',
        r'வாழ்க\s*ஜனநாயகம்',
        r'வெற்றி\s*நமதே',
        r'நாளைய\s*விடியல்'
    ]

    AMBIGUOUS_PATTERNS = [
        r'\b(?:development is (?:visible )?everywhere|all people are happy|lots of good work done)\b',
        r'\b(?:major transformation happening|unprecedented progress|visible everywhere in the state)\b',
        r'எங்கும்\s*வளர்ச்சி',
        r'பல\s*நன்மைகள்\s*செய்யப்பட்டுள்ளன',
        r'ஏராளமான\s*மக்கள்\s*பயனடைந்துள்ளனர்'
    ]

    @classmethod
    def evaluate(cls, text: str) -> Tuple[VerifiabilityStatus, float, str]:
        """
        Returns: (VerifiabilityStatus, confidence, rationale)
        """
        clean = text.strip()

        # 1. Rhetorical Question Check
        for pat in cls.RHETORICAL_QUESTION_PATTERNS:
            if re.search(pat, clean, re.IGNORECASE):
                return (
                    VerifiabilityStatus.RHETORICAL_QUESTION,
                    0.95,
                    "Statement is framed as a rhetorical question without empirical assertion."
                )

        # 2. Slogan Check
        for pat in cls.SLOGAN_PATTERNS:
            if re.search(pat, clean, re.IGNORECASE):
                return (
                    VerifiabilityStatus.SLOGAN,
                    0.92,
                    "Statement is a political rally chant or ideological slogan."
                )

        # 3. Opinion Check
        for pat in cls.OPINION_PATTERNS:
            if re.search(pat, clean, re.IGNORECASE):
                return (
                    VerifiabilityStatus.OPINION,
                    0.88,
                    "Statement reflects subjective viewpoint, qualitative praise, or personal sentiment."
                )

        # 4. Prediction Check
        for pat in cls.PREDICTION_PATTERNS:
            if re.search(pat, clean, re.IGNORECASE):
                return (
                    VerifiabilityStatus.PREDICTION,
                    0.90,
                    "Statement is a future-tense projection or electoral forecast."
                )

        # 5. Value Judgment Check
        for pat in cls.VALUE_JUDGMENT_PATTERNS:
            if re.search(pat, clean, re.IGNORECASE):
                return (
                    VerifiabilityStatus.VALUE_JUDGMENT,
                    0.87,
                    "Statement expresses a moral or ethical characterization rather than a factual event."
                )

        # 6. Ambiguous / Vague Check
        for pat in cls.AMBIGUOUS_PATTERNS:
            if re.search(pat, clean, re.IGNORECASE):
                return (
                    VerifiabilityStatus.AMBIGUOUS_UNVERIFIABLE,
                    0.85,
                    "Statement is overly vague and lacks verifiable metrics, dates, or institutional scope."
                )

        # 7. Check for concrete empirical markers (numbers, dates, known schemes, statutory terms)
        has_number = bool(re.search(r'\d+', clean))
        has_scheme = any(kw in clean.lower() for cat in KNOWN_ENTITIES.values() for kwlist in cat.values() for kw in kwlist)
        has_stat_terms = bool(re.search(r'(?:crore|lakh|percent|கோடி|லட்சம்|சதவீதம்|ரூபாய்|allocated|disbursed|நிதி)', clean, re.IGNORECASE))

        if has_number or has_scheme or has_stat_terms:
            return (
                VerifiabilityStatus.VERIFIABLE_FACTUAL,
                0.95,
                "Statement asserts verifiable quantitative, programmatic, or statutory claims."
            )

        # Default fallback: If it's a declarative sentence with specific subject/verb
        return (
            VerifiabilityStatus.VERIFIABLE_FACTUAL,
            0.75,
            "Declarative statement with testable proposition."
        )


# ---------------------------------------------------------------------------
# 5. Pipeline Stage 4: Quantitative Attributes, Units & Denominators Extractor
# ---------------------------------------------------------------------------
class QuantitativeExtractor:
    """
    Extracts numbers, Indian scales (crore, lakh), units, denominators, comparison baselines, and dates.
    """
    TIME_PERIOD_PATTERNS = [
        # Fiscal Year (e.g., 2024-25, 2023-2024)
        (r'\b(20\d{2}[-–]\d{2,4})\b', "FISCAL_YEAR"),
        # Relative English time (e.g., last 3 years, past 2 years, in 2023)
        (r'\b(?:in the last|in past|over the last)\s+(\d+\s+(?:years?|months?))\b', "RELATIVE_YEARS"),
        (r'\b(in\s+20\d{2})\b', "CALENDAR_YEAR"),
        # Relative Tamil time (e.g. கடந்த 3 ஆண்டுகளில், 2024-25 நிதியாண்டில்)
        (r'(கடந்த\s+\d+\s+ஆண்டுகளில்)', "TAMIL_RELATIVE_YEARS"),
        (r'(இந்த\s+ஆண்டில்)', "TAMIL_CURRENT_YEAR"),
        (r'(20\d{2}[-–]\d{2,4}\s*நிதியாண்டில்)', "TAMIL_FISCAL_YEAR")
    ]

    COMPARISON_OPERATORS = [
        (r'\b(?:increased by|increased from|increased to|increased|rose by|hiked by)\b', "INCREASE_BY"),
        (r'\b(?:decreased by|decreased from|fell by|dropped by|reduced by)\b', "DECREASE_BY"),
        (r'\b(?:more than|above|over|exceeding)\b', "GREATER_THAN"),
        (r'\b(?:less than|below|under)\b', "LESS_THAN"),
        (r'(?:உயர்ந்துள்ளது|அதிகரித்துள்ளது|கூடியுள்ளது)', "INCREASE_BY"),
        (r'(?:குறைந்துள்ளது|சரிந்துள்ளது)', "DECREASE_BY"),
        (r'(?:விட\s*அதிகம்|மேல்)', "GREATER_THAN"),
        (r'(?:விட\s*குறைவு|கீழ்)', "LESS_THAN")
    ]

    DENOMINATORS = [
        (r'\b(?:per month|monthly)\b', "per month"),
        (r'\b(?:per year|annually)\b', "per year"),
        (r'\b(?:per student)\b', "per student"),
        (r'\b(?:per beneficiary)\b', "per beneficiary"),
        (r'\b(?:per day|daily)\b', "per day"),
        (r'\b(?:of gsdp|of state gdp)\b', "of GSDP"),
        (r'(?:மாதத்திற்கு|மாதந்தோறும்|ஒரு மாதத்திற்கு)', "மாதத்திற்கு"),
        (r'(?:ஆண்டிற்கு|ஆண்டுதோறும்)', "ஆண்டிற்கு"),
        (r'(?:மாணவருக்கு|மாணவிக்கு)', "மாணவருக்கு"),
        (r'(?:பயனாளிக்கு)', "பயனாளிக்கு"),
        (r'(?:மொத்த\s*உற்பத்தியில்)', "மொத்த உற்பத்தியில்")
    ]

    @classmethod
    def extract(cls, text: str) -> Dict[str, Any]:
        """
        Parses text for quantitative metrics.
        """
        res = {
            "numeric_value": None,
            "unit": None,
            "denominator": None,
            "comparison_operator": None,
            "baseline_value": None,
            "time_period": None
        }

        # 1. Extract Time Period
        for pat, tag in cls.TIME_PERIOD_PATTERNS:
            m = re.search(pat, text, re.IGNORECASE)
            if m:
                res["time_period"] = m.group(1).strip()
                break

        # 2. Extract Denominator
        for pat, denom in cls.DENOMINATORS:
            if re.search(pat, text, re.IGNORECASE):
                res["denominator"] = denom
                break

        # 3. Extract Comparison Operator
        for pat, op in cls.COMPARISON_OPERATORS:
            if re.search(pat, text, re.IGNORECASE):
                res["comparison_operator"] = op
                break

        # 4. Extract Comparison Baseline (e.g. from 500 to 1000, 500 இலிருந்து 1000 ஆக)
        baseline_match = re.search(
            r'(?:from\s+(?:Rs\.?|₹|ரூ\.?)?\s*(\d+(?:,\d+)*(?:\.\d+)?)\s*to\s*(?:Rs\.?|₹|ரூ\.?)?\s*(\d+(?:,\d+)*(?:\.\d+)?))',
            text,
            re.IGNORECASE
        )
        if not baseline_match:
            baseline_match = re.search(
                r'(?:(?:ரூ\.?|₹)?\s*(\d+(?:,\d+)*(?:\.\d+)?)\s*இலிருந்து\s*(?:ரூ\.?|₹)?\s*(\d+(?:,\d+)*(?:\.\d+)?)\s*ஆக)',
                text
            )

        if baseline_match:
            b_val = float(baseline_match.group(1).replace(",", ""))
            curr_val = float(baseline_match.group(2).replace(",", ""))
            res["baseline_value"] = b_val
            res["numeric_value"] = curr_val
            res["unit"] = "currency"
            if not res["comparison_operator"]:
                res["comparison_operator"] = "INCREASE_BY"

        # 5. Extract Numbers and Units if not already populated
        if res["numeric_value"] is None:
            # Mask out time_period so numbers inside the temporal scope are ignored
            search_text = text
            if res["time_period"]:
                search_text = search_text.replace(res["time_period"], " ")

            # Check Crore (e.g. 13,720 crore, 13720 கோடி)
            crore_m = re.search(r'(\d+(?:,\d+)*(?:\.\d+)?)\s*(?:crore|crores|cr|கோடி)', search_text, re.IGNORECASE)
            if crore_m:
                val = float(crore_m.group(1).replace(",", ""))
                res["numeric_value"] = val
                res["unit"] = "crore"
            else:
                # Check Lakh (e.g. 1.15 lakh, 50 லட்சம்)
                lakh_m = re.search(r'(\d+(?:,\d+)*(?:\.\d+)?)\s*(?:lakh|lakhs|லட்சம்)', search_text, re.IGNORECASE)
                if lakh_m:
                    val = float(lakh_m.group(1).replace(",", ""))
                    res["numeric_value"] = val
                    res["unit"] = "lakh"
                else:
                    # Check Percentage (e.g. 3.44 percent, 3.44%, 10 சதவீதம்)
                    pct_m = re.search(r'(\d+(?:\.\d+)?)\s*(?:%|percent|percentage|சதவீதம்)', search_text, re.IGNORECASE)
                    if pct_m:
                        res["numeric_value"] = float(pct_m.group(1))
                        res["unit"] = "percent"
                    else:
                        # Check Currency (e.g. Rs 1000, ₹1000, ரூ.1000)
                        curr_m = re.search(r'(?:Rs\.?|INR|₹|ரூ\.?|ரூபாய்)\s*(\d+(?:,\d+)*(?:\.\d+)?)', search_text, re.IGNORECASE)
                        if curr_m:
                            res["numeric_value"] = float(curr_m.group(1).replace(",", ""))
                            res["unit"] = "INR"
                        else:
                            # Plain Number with thousands/commas first
                            comma_m = re.search(r'\b(\d{1,3}(?:,\d{3})+)\b', search_text)
                            if comma_m:
                                res["numeric_value"] = float(comma_m.group(1).replace(",", ""))
                                res["unit"] = "units"
                            else:
                                plain_m = re.search(r'\b(\d+(?:\.\d+)?)\b', search_text)
                                if plain_m:
                                    raw_str = plain_m.group(1).replace(",", "")
                                    if not (len(raw_str) == 4 and raw_str.startswith("20")):
                                        res["numeric_value"] = float(raw_str)
                                        res["unit"] = "units"

        return res


# ---------------------------------------------------------------------------
# 6. Pipeline Stage 5: Entity Extractor & Negation Detector
# ---------------------------------------------------------------------------
class EntityAndNegationExtractor:
    """
    Extracts named political entities, schemes, and flags explicit negation.
    """
    NEGATION_PATTERNS = [
        r'\b(?:not|did not|does not|failed to|never|without|denied|no)\b',
        r'(?:இல்லை|வழங்கப்படவில்லை|நிறைவேற்றப்படவில்லை|செயல்படுத்தவில்லை|கிடையாது|மறுத்துள்ளது|தவறிவிட்டது|விடவில்லை)'
    ]

    @classmethod
    def detect_negation(cls, text: str) -> bool:
        for pat in cls.NEGATION_PATTERNS:
            if re.search(pat, text, re.IGNORECASE):
                return True
        return False

    @classmethod
    def extract_entities(cls, text: str) -> Dict[str, Any]:
        found = {
            "leaders": [],
            "parties": [],
            "schemes": [],
            "departments": [],
            "geographic_scope": "Tamil Nadu"
        }
        lower = text.lower()

        # Match Leaders
        for canonical, aliases in KNOWN_ENTITIES["LEADERS"].items():
            if any(alias in lower for alias in aliases):
                found["leaders"].append(canonical)

        # Match Parties
        for canonical, aliases in KNOWN_ENTITIES["PARTIES"].items():
            if any(alias in lower for alias in aliases):
                found["parties"].append(canonical)

        # Match Schemes
        for canonical, aliases in KNOWN_ENTITIES["SCHEMES"].items():
            if any(alias in lower for alias in aliases):
                found["schemes"].append(canonical)

        # Match Departments
        for canonical, aliases in KNOWN_ENTITIES["DEPARTMENTS"].items():
            if any(alias in lower for alias in aliases):
                found["departments"].append(canonical)

        # Match Geographic Scope
        for canonical, aliases in KNOWN_ENTITIES["GEOGRAPHIC_REGIONS"].items():
            if any(alias in lower for alias in aliases):
                found["geographic_scope"] = canonical
                break

        return found


# ---------------------------------------------------------------------------
# 7. Pipeline Stage 6: Atomic Claim Decomposition Engine
# ---------------------------------------------------------------------------
class AtomicClaimDecomposer:
    """
    Splits compound or multi-part statements into atomic verifiable claims,
    resolves subject inheritance across clauses, and forms SPO semantic frames.
    """
    # Conjunctions for compound sentence splitting
    CONJUNCTION_PATTERN = re.compile(
        r'(?:\s+(?:and|but|while|whereas|moreover|furthermore|as well as)\s+|'
        r'\s+(?:மற்றும்|மேலும்|ஆனால்|அதே நேரத்தில்|எனினும்|ஆயினும்)\s+|'
        r'[;]\s*)',
        re.IGNORECASE
    )

    @classmethod
    def split_clauses(cls, text: str) -> List[str]:
        clauses = [c.strip() for c in cls.CONJUNCTION_PATTERN.split(text) if len(c.strip()) > 10]
        return clauses if clauses else [text.strip()]

    @classmethod
    def extract_spo_frame(
        cls,
        clause: str,
        entities: Dict[str, Any],
        inherited_subject: Optional[str] = None
    ) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        """
        Extracts (subject, predicate/action, object).
        Inherits preceding subject if current clause has no explicit subject.
        """
        # Determine Subject
        subject = None
        if entities["schemes"]:
            subject = entities["schemes"][0]
        elif entities["leaders"]:
            subject = entities["leaders"][0]
        elif entities["parties"]:
            subject = entities["parties"][0]
        elif entities["departments"]:
            subject = entities["departments"][0]
        elif inherited_subject:
            subject = inherited_subject
        else:
            subject = entities.get("geographic_scope", "Tamil Nadu")

        # Determine Action / Predicate
        action = "asserts"
        predicate_patterns = [
            (r'\b(?:allocated|allocated budget|earmarked)\b', "allocated"),
            (r'\b(?:disbursed|distributed|provided|transferred)\b', "disbursed"),
            (r'\b(?:failed to fulfill|did not disburse|broken promise)\b', "failed_to_fulfill"),
            (r'\b(?:achieved|completed|constructed|built)\b', "achieved"),
            (r'\b(?:increased|hiked|raised)\b', "increased"),
            (r'\b(?:decreased|reduced|fell)\b', "decreased"),
            (r'(?:ஒதுக்கீடு\s*செய்துள்ளது|ஒதுக்கியுள்ளது)', "allocated"),
            (r'(?:வழங்கியுள்ளது|வழங்கப்பட்டது)', "disbursed"),
            (r'(?:நிறைவேற்றவில்லை|வழங்கவில்லை)', "failed_to_fulfill"),
            (r'(?:கட்டப்பட்டுள்ளது|நிறைவடைந்துள்ளது)', "completed"),
            (r'(?:உயர்த்தப்பட்டுள்ளது|அதிகரித்துள்ளது)', "increased")
        ]
        for pat, act in predicate_patterns:
            if re.search(pat, clause, re.IGNORECASE):
                action = act
                break

        # Object is the core proposition target (e.g. quantity or scheme outcome)
        obj = clause
        return subject, action, obj

    @classmethod
    def determine_claim_type(
        cls,
        verifiability: VerifiabilityStatus,
        entities: Dict[str, Any],
        quant: Dict[str, Any]
    ) -> AtomicClaimType:
        if verifiability != VerifiabilityStatus.VERIFIABLE_FACTUAL:
            return AtomicClaimType.NON_FACTUAL

        if entities["schemes"]:
            return AtomicClaimType.SCHEME_BENEFIT

        if quant.get("unit") == "crore" or "budget" in str(quant.get("time_period", "")).lower():
            return AtomicClaimType.BUDGET_ALLOCATION

        if quant.get("numeric_value") is not None:
            return AtomicClaimType.NUMERICAL_STATISTIC

        return AtomicClaimType.POLICY_DECISION


# ---------------------------------------------------------------------------
# 8. Full Multilingual Claim Processing Pipeline
# ---------------------------------------------------------------------------
class MultilingualClaimPipeline:
    """
    End-to-end Pipeline:
    ORIGINAL CLAIM
    → LANGUAGE DETECTION
    → TEXT NORMALIZATION
    → CLAIM TYPE CLASSIFICATION
    → ATOMIC CLAIM DECOMPOSITION
    → ENTITY EXTRACTION
    → DATE/NUMBER EXTRACTION
    → VERIFIABILITY ASSESSMENT
    """
    def __init__(self, db: Optional[Session] = None):
        self.db = db

    def process_claim(
        self,
        claim_id: str,
        original_text: str,
        geographic_scope: Optional[str] = "Tamil Nadu",
        persist_to_db: bool = True
    ) -> Dict[str, Any]:
        """
        Executes claim processing and returns decomposed atomic claims.
        Preserves original_text verbatim.
        """
        if not original_text or not original_text.strip():
            raise ValueError("original_text cannot be empty.")

        # 1. Language Detection
        detected_lang = LanguageDetector.detect(original_text)

        # 2. Text Normalization (original_text remains untouched)
        normalized = TextNormalizer.normalize(original_text)

        # 3. Overall Verifiability Assessment
        overall_status, overall_conf, overall_rationale = VerifiabilityClassifier.evaluate(normalized)

        # 4. Atomic Claim Decomposition
        clauses = AtomicClaimDecomposer.split_clauses(normalized)

        atomic_results: List[Dict[str, Any]] = []
        inherited_subject = None

        for idx, clause in enumerate(clauses):
            atomic_id = f"ACM-{claim_id}-{idx+1:02d}"

            # Clause-level language detection
            clause_lang = LanguageDetector.detect(clause)

            # Clause-level verifiability
            clause_status, clause_conf, clause_rationale = VerifiabilityClassifier.evaluate(clause)

            # Entity & Negation extraction
            entities = EntityAndNegationExtractor.extract_entities(clause)
            is_negated = EntityAndNegationExtractor.detect_negation(clause)

            # Quantitative extraction
            quant = QuantitativeExtractor.extract(clause)

            # SPO Extraction
            subject, action, obj = AtomicClaimDecomposer.extract_spo_frame(
                clause=clause,
                entities=entities,
                inherited_subject=inherited_subject
            )
            if subject:
                inherited_subject = subject

            # Claim Type Classification
            claim_type = AtomicClaimDecomposer.determine_claim_type(
                verifiability=clause_status,
                entities=entities,
                quant=quant
            )

            # Cross-Lingual Translation helper for Tamil retrieval
            translation_helper = None
            if clause_lang in ["ta", "mixed"]:
                # Preserves original Tamil intact; generates structured English query representation
                subj_str = subject or "Tamil Nadu Government"
                act_str = action or "announced"
                val_str = f"{quant.get('numeric_value')} {quant.get('unit') or ''}".strip()
                translation_helper = f"{subj_str} {act_str} {val_str}".strip()

            atomic_item = {
                "atomic_claim_id": atomic_id,
                "claim_id": claim_id,
                "atomic_claim_text": clause,  # Exact substring preserved
                "language": clause_lang,
                "subject": subject,
                "predicate": action,
                "action": action,
                "object": obj,
                "time_period": quant.get("time_period"),
                "geographic_scope": entities.get("geographic_scope") or geographic_scope,
                "numeric_value": quant.get("numeric_value"),
                "unit": quant.get("unit"),
                "denominator": quant.get("denominator"),
                "comparison_operator": quant.get("comparison_operator"),
                "baseline_value": quant.get("baseline_value"),
                "claim_type": claim_type.value,
                "verifiability_status": clause_status.value,
                "is_verifiable": (clause_status == VerifiabilityStatus.VERIFIABLE_FACTUAL),
                "is_negated": is_negated,
                "decomposition_method": "MULTILINGUAL_NLP_V1",
                "confidence": clause_conf,
                "translation_text": translation_helper,
                "metadata_json": {
                    "entities": entities,
                    "rationale": clause_rationale
                }
            }
            atomic_results.append(atomic_item)

            # Save to Database if session provided
            if self.db and persist_to_db:
                # Check for existing record
                existing = self.db.query(AtomicClaim).filter(
                    AtomicClaim.atomic_claim_id == atomic_id
                ).first()
                if not existing:
                    db_atomic = AtomicClaim(
                        atomic_claim_id=atomic_id,
                        claim_id=claim_id,
                        atomic_claim_text=clause,
                        language=clause_lang,
                        subject=subject,
                        predicate=action,
                        action=action,
                        object=obj,
                        time_period=quant.get("time_period"),
                        geographic_scope=entities.get("geographic_scope") or geographic_scope,
                        numeric_value=quant.get("numeric_value"),
                        unit=quant.get("unit"),
                        denominator=quant.get("denominator"),
                        comparison_operator=quant.get("comparison_operator"),
                        baseline_value=quant.get("baseline_value"),
                        claim_type=claim_type.value,
                        verifiability_status=clause_status.value,
                        is_verifiable=(clause_status == VerifiabilityStatus.VERIFIABLE_FACTUAL),
                        is_negated=is_negated,
                        decomposition_method="MULTILINGUAL_NLP_V1",
                        confidence=clause_conf,
                        translation_text=translation_helper,
                        metadata_json=atomic_item["metadata_json"]
                    )
                    self.db.add(db_atomic)

        if self.db and persist_to_db:
            self.db.commit()

        logger.info(
            f"Processed claim {claim_id} [{detected_lang}]: {len(atomic_results)} atomic propositions decomposed."
        )

        return {
            "claim_id": claim_id,
            "original_text": original_text,  # Verbatim preserved
            "detected_language": detected_lang,
            "normalized_text": normalized,
            "overall_verifiability": overall_status.value,
            "overall_confidence": overall_conf,
            "atomic_claims_count": len(atomic_results),
            "atomic_claims": atomic_results
        }
