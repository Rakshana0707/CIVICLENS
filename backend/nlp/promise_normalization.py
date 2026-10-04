"""
Promise Normalization and Categorization Pipeline (Phase 3.6).

Transforms raw extracted PromiseRecord objects into structured, normalized promise records
enriched with detailed metadata (target population, sector, department, geography, proposed action,
numeric/monetary targets, time horizon, implementation mechanism) and categorized against a configurable
taxonomy (Education, Healthcare, Agriculture, Welfare, Women, Youth, etc.).

Design rules:
- ``original_text`` is ALWAYS strictly preserved without modification.
- Ambiguous or low-confidence promises are assigned to 'Uncategorized' rather than forced into categories.
- Taxonomy is fully configurable via JSON/YAML config.
"""
import os
import json
import re
import logging
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Optional, Tuple

from backend.nlp.promise_extraction import PromiseRecord, PromiseClassification
from backend.nlp.preprocessing import normalize_unicode, normalize_whitespace

logger = logging.getLogger(__name__)

DEFAULT_TAXONOMY_PATH = os.path.join("config", "promise_taxonomy.json")


@dataclass
class PromiseMetadata:
    """Extracted metadata attributes from political promises."""
    target_population: Optional[str] = None
    sector: Optional[str] = None
    department: Optional[str] = None
    geography: Optional[str] = None
    proposed_action: Optional[str] = None
    numeric_target: Optional[str] = None
    monetary_target: Optional[str] = None
    time_horizon: Optional[str] = None
    implementation_mechanism: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class NormalizedPromise:
    """Structured representation of a political promise with metadata and categorization."""
    promise_id: str
    manifesto_id: str
    original_text: str
    normalized_text: str
    primary_category: str
    categories: List[str]
    metadata: PromiseMetadata
    page_number: Optional[int] = None
    section: Optional[str] = None
    language: str = "Unknown"
    classification: str = "general_policy"
    categorization_confidence: float = 0.0
    is_ambiguous: bool = False
    is_test_fixture: bool = False

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["metadata"] = self.metadata.to_dict()
        return d


class PromiseCategorizer:
    """Configurable taxonomy categorizer for political promises."""

    def __init__(self, taxonomy_path: str = DEFAULT_TAXONOMY_PATH):
        self.taxonomy_path = taxonomy_path
        self.categories: List[Dict[str, Any]] = []
        self._load_taxonomy()

    def _load_taxonomy(self):
        if not os.path.exists(self.taxonomy_path):
            logger.warning(f"Taxonomy file not found at {self.taxonomy_path}. Using fallback categories.")
            self.categories = [
                {"id": "Uncategorized", "name": "Uncategorized", "keywords_en": [], "keywords_ta": []},
                {"id": "Other", "name": "Other", "keywords_en": [], "keywords_ta": []}
            ]
            return

        with open(self.taxonomy_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            self.categories = data.get("categories", [])

    def categorize(self, text: str, is_ambiguous: bool = False) -> Tuple[str, List[str], float]:
        """
        Categorizes promise text against configured taxonomy keywords.
        Returns (primary_category, list_of_matched_categories, confidence).
        If ambiguous or no keywords match, returns ("Uncategorized", ["Uncategorized"], 0.0).
        """
        if is_ambiguous or not text or not text.strip():
            return "Uncategorized", ["Uncategorized"], 0.0

        text_lower = text.lower()
        matched_scores: Dict[str, int] = {}

        for cat in self.categories:
            cat_id = cat.get("id", "Uncategorized")
            if cat_id in ("Uncategorized", "Other"):
                continue

            score = 0
            # Check English keywords (allowing simple plural matches)
            for kw in cat.get("keywords_en", []):
                pattern = r'\b' + re.escape(kw.lower()) + r'(?:s|es)?\b'
                matches = re.findall(pattern, text_lower)
                score += len(matches)

            # Check Tamil keywords
            for kw in cat.get("keywords_ta", []):
                if kw in text:
                    score += 1

            if score > 0:
                matched_scores[cat_id] = score

        if not matched_scores:
            return "Uncategorized", ["Uncategorized"], 0.0

        # Sort categories by match score
        sorted_cats = sorted(matched_scores.items(), key=lambda x: x[1], reverse=True)
        matched_category_ids = [c[0] for c in sorted_cats]
        primary_category = matched_category_ids[0]

        top_score = sorted_cats[0][1]
        confidence = min(1.0, round(0.4 + (top_score * 0.2), 2))

        return primary_category, matched_category_ids, confidence


class PromiseMetadataExtractor:
    """Rule-based extractor for metadata fields in political promises."""

    # Target population patterns
    _TARGET_POPULATION_PATTERNS = [
        (r'\b(women|woman|mother|mothers|girl|girls|female|magalir)\b|பெண்கள்|மகளிர்|தாய்', "Women"),
        (r'\b(farmer|farmers|agriculture workers|cultivators)\b|விவசாயி|விவசாயிகள்', "Farmers"),
        (r'\b(student|students|school children|youth|graduates)\b|மாணவர்|மாணவர்கள்|இளைஞர்', "Students / Youth"),
        (r'\b(senior citizens|elderly|pensioners|aged)\b|முதியோர்|ஓய்வூதியதாரர்', "Senior Citizens"),
        (r'\b(fishermen|fisherfolk|fisherman)\b|மீனவர்|மீனவர்கள்', "Fisherfolk"),
        (r'\b(differently abled|disabled|handicapped)\b|மாற்றுத்திறனாளி|மாற்றுத்திறனாளிகள்', "Differently Abled"),
        (r'\b(sc/st|tribal|scheduled caste|scheduled tribe|dalit)\b|பழங்குடியினர்|ஆதிதிராவிடர்', "SC/ST & Tribal Communities"),
        (r'\b(teachers|government employees|staff)\b|ஆசிரியர்கள்|அரசு ஊழியர்கள்', "Government Employees / Teachers"),
        (r'\b(unemployed|job seekers)\b|வேலையற்றோர்', "Unemployed Youth"),
        (r'\b(all households|every family|poor families|bpl)\b|அனைத்து குடும்பங்கள்|ஏழை எளியோர்', "Low-Income Families")
    ]

    # Proposed Action patterns
    _ACTION_PATTERNS = [
        (r'\b(provide|given|grant|distribute|offer)\b|வழங்கப்படும்|தரப்படும்', "Provide / Distribute"),
        (r'\b(construct|build|establish|set up|create|inaugurate)\b|அமைக்கப்படும்|கட்டப்படும்|உருவாக்கப்படும்', "Construct / Establish"),
        (r'\b(waive|cancel|write off)\b|தள்ளுபடி செய்யப்படும்|ரத்து செய்யப்படும்', "Waive / Cancel"),
        (r'\b(increase|raise|enhance|double|boost)\b|உயர்த்தப்படும்|அதிகரிக்கப்படும்|இரட்டிப்பாக்கப்படும்', "Increase / Enhance"),
        (r'\b(introduce|launch|implement|start|enact)\b|அறிமுகப்படுத்தப்படும்|செயல்படுத்தப்படும்', "Introduce / Launch"),
        (r'\b(reduce|lower|cut|decrease)\b|குறைக்கப்படும்', "Reduce / Lower"),
        (r'\b(abolish|remove|eliminate)\b|ஒழிக்கப்படும்|நீக்கப்படும்', "Abolish / Eliminate")
    ]

    # Monetary target pattern
    _MONETARY_PATTERN = re.compile(
        r'(\b(?:rs\.?|rupees?|₹)\s*\d+(?:,\d+)*(?:\.\d+)?(?:\s*(?:lakh|crore|thousand|million|billion))?\b|'
        r'\b\d+(?:,\d+)*(?:\.\d+)?\s*(?:lakh|crore)\s*(?:rupees?|rs\.?|₹)?\b|'
        r'ரூ\.?\s*\d+(?:,\d+)*(?:\s*(?:லட்சம்|கோடி))?|'
        r'\d+(?:,\d+)*\s*(?:லட்சம்|கோடி)\s*ரூபாய்)',
        re.IGNORECASE
    )

    # Numeric target pattern (percentages, counts, non-monetary quantities)
    _NUMERIC_PATTERN = re.compile(
        r'(\b\d+(?:,\d+)*(?:\.\d+)?\s*(?:%|percent|per cent|km|kms|hospitals|schools|jobs|vacancies|laptops|buses|houses|acres|mw|units)\b|'
        r'\b\d+(?:,\d+)*(?:\.\d+)?%|'
        r'\b\d+(?:,\d+)*\s*(?:சதவீதம்|கி\.மீ|பள்ளிகள்|மருத்துவமனைகள்|பேருந்துகள்|வீடுகள்|யூனிட்)\b)',
        re.IGNORECASE
    )

    # Time Horizon pattern
    _TIME_HORIZON_PATTERN = re.compile(
        r'(\b(?:within|in)\s*(?:\d+|one|two|three|four|five)\s*(?:years?|months?|days?)\b|'
        r'\b(?:every|per)\s*(?:month|year|annum)\b|'
        r'\b(?:by|in)\s*20\d{2}\b|'
        r'\b(?:annual|monthly|quarterly)\b|'
        r'ஆண்டுதோறும்|மாதந்தோறும்|ஒவ்வொரு மாதமும்|\d+\s*ஆண்டுகளில்)',
        re.IGNORECASE
    )

    # Implementation Mechanism pattern
    _MECHANISM_PATTERN = re.compile(
        r'(\b(?:direct benefit transfer|dbt|special board|commission|authority|portal|scheme|welfare board|single window|corporation)\b|'
        r'நேரடி பணப்பரிமாற்றம்|வாரியம்|ஆணையம்|திட்டம்|கார்ப்பரேஷன்)',
        re.IGNORECASE
    )

    # Geography pattern
    _GEOGRAPHY_PATTERN = re.compile(
        r'(\b(?:tamil nadu|chennai|coimbatore|madurai|trichy|salem|tirunelveli|rural areas|urban areas|coastal areas|delta region)\b|'
        r'தமிழ்நாடு|சென்னையில்|கிராமப்புறங்களில்|நகர்ப்புறங்களில்|டெல்டா பகுதி)',
        re.IGNORECASE
    )

    # Department hints
    _DEPARTMENT_PATTERN = [
        (r'\b(school|higher education|university|college|literacy)\b|கல்வித்துறை', "School & Higher Education"),
        (r'\b(health|hospital|medical|sanitation)\b|சுகாதாரத்துறை', "Health & Family Welfare"),
        (r'\b(agriculture|farmer|crop|irrigation)\b|வேளாண்மைத்துறை', "Agriculture & Farmers Welfare"),
        (r'\b(transport|bus|metro|railway)\b|போக்குவரத்துத்துறை', "Transport Department"),
        (r'\b(police|safety|law and order|security)\b|காவல்துறை', "Home, Prohibition & Excise (Police)"),
        (r'\b(revenue|patta|land)\b|வருவாய்த்துறை', "Revenue & Disaster Management"),
        (r'\b(rural development|panchayat)\b|ஊரக வளர்ச்சி', "Rural Development & Panchayat Raj"),
        (r'\b(pwd|public works|bridge|road)\b|பொதுப்பணித்துறை', "Public Works Department (PWD)")
    ]

    def extract_metadata(self, text: str, primary_category: str = "Uncategorized") -> PromiseMetadata:
        """Extracts metadata attributes from promise text."""
        if not text:
            return PromiseMetadata()

        # Target Population
        target_pop = None
        for pattern, pop_label in self._TARGET_POPULATION_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                target_pop = pop_label
                break

        # Proposed Action
        proposed_action = None
        for pattern, action_label in self._ACTION_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                proposed_action = action_label
                break

        # Monetary Target
        monetary_match = self._MONETARY_PATTERN.search(text)
        monetary_target = monetary_match.group(0).strip() if monetary_match else None

        # Numeric Target
        numeric_match = self._NUMERIC_PATTERN.search(text)
        numeric_target = numeric_match.group(0).strip() if numeric_match else None

        # Time Horizon
        time_match = self._TIME_HORIZON_PATTERN.search(text)
        time_horizon = time_match.group(0).strip() if time_match else None

        # Implementation Mechanism
        mech_match = self._MECHANISM_PATTERN.search(text)
        impl_mechanism = mech_match.group(0).strip() if mech_match else None

        # Geography
        geo_match = self._GEOGRAPHY_PATTERN.search(text)
        geography = geo_match.group(0).strip() if geo_match else None

        # Department
        department = None
        for pattern, dept_name in self._DEPARTMENT_PATTERN:
            if re.search(pattern, text, re.IGNORECASE):
                department = dept_name
                break

        sector = primary_category if primary_category not in ("Uncategorized", "Other") else None

        return PromiseMetadata(
            target_population=target_pop,
            sector=sector,
            department=department,
            geography=geography,
            proposed_action=proposed_action,
            numeric_target=numeric_target,
            monetary_target=monetary_target,
            time_horizon=time_horizon,
            implementation_mechanism=impl_mechanism
        )


class PromiseNormalizationService:
    """
    Main service orchestrating promise normalization, metadata extraction, and categorization.
    """

    def __init__(self, taxonomy_path: str = DEFAULT_TAXONOMY_PATH):
        self.categorizer = PromiseCategorizer(taxonomy_path=taxonomy_path)
        self.metadata_extractor = PromiseMetadataExtractor()

    def normalize_promise(self, promise_record: Any) -> NormalizedPromise:
        """
        Normalizes a PromiseRecord (or dictionary) into a NormalizedPromise.
        """
        if isinstance(promise_record, dict):
            promise_id = promise_record.get("promise_id", "")
            manifesto_id = promise_record.get("manifesto_id", "")
            original_text = promise_record.get("original_text", "")
            page_number = promise_record.get("page_number")
            section = promise_record.get("section")
            language = promise_record.get("language", "Unknown")
            classification = promise_record.get("classification", "general_policy")
            is_test_fixture = promise_record.get("is_test_fixture", False)
        else:
            promise_id = getattr(promise_record, "promise_id", "")
            manifesto_id = getattr(promise_record, "manifesto_id", "")
            original_text = getattr(promise_record, "original_text", "")
            page_number = getattr(promise_record, "page_number", None)
            section = getattr(promise_record, "section", None)
            language = getattr(promise_record, "language", "Unknown")
            classification = getattr(promise_record, "classification", "general_policy")
            if hasattr(classification, "value"):
                classification = classification.value
            is_test_fixture = getattr(promise_record, "is_test_fixture", False)

        # Preserve exact original wording for original_text
        # Apply conservative unicode NFC and whitespace normalization for normalized_text
        normalized_text = normalize_whitespace(normalize_unicode(original_text))

        is_ambiguous = (classification in ("ambiguous", PromiseClassification.AMBIGUOUS.value))

        # Categorize
        primary_category, categories, conf = self.categorizer.categorize(
            text=normalized_text,
            is_ambiguous=is_ambiguous
        )

        # Extract metadata
        metadata = self.metadata_extractor.extract_metadata(
            text=normalized_text,
            primary_category=primary_category
        )

        return NormalizedPromise(
            promise_id=promise_id,
            manifesto_id=manifesto_id,
            original_text=original_text, # Exact original wording preserved!
            normalized_text=normalized_text,
            primary_category=primary_category,
            categories=categories,
            metadata=metadata,
            page_number=page_number,
            section=section,
            language=language,
            classification=str(classification),
            categorization_confidence=conf,
            is_ambiguous=is_ambiguous,
            is_test_fixture=is_test_fixture
        )

    def normalize_batch(self, promise_records: List[Any]) -> List[NormalizedPromise]:
        """Normalizes a list of promise records."""
        return [self.normalize_promise(rec) for rec in promise_records]
