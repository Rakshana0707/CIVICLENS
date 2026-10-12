"""
Phase 8.3 — Grievance Data Ingestion and Normalization Pipeline.

Converts diverse, heterogenous public civic grievance records from various sources
(DARPG CPGRAMS, Greater Chennai Corporation GCC, Mudhalvarin Mugavari TNeGA CM Helpline,
and generic civic CSV/JSON dumps) into a canonical normalized format.

Canonical Schema:
- grievance_id (str)
- source_id (str)
- issue_category (Optional[str])
- description_or_permitted_summary (str)
- submission_date (datetime)
- department_id (Optional[str])
- administrative_area_id (Optional[str])
- status (str: OPEN, IN_PROGRESS, RESOLVED, REJECTED, PENDING, UNKNOWN)
- acknowledgement_date (Optional[datetime])
- resolution_date (Optional[datetime])
- source_document_id (Optional[int])
- source_record_reference (Optional[str])
- ingestion_timestamp (datetime)
- data_quality_status (str)

Key Principles:
- Include fields only when supported by source.
- Never invent individual complaints.
- Never fill unknown statuses with 'resolved'.
- Strip/redact PII (DPDPA 2023 compliance).
- Keep restricted raw reference for auditing.
- Robust date, category, department, area, and status normalizers.
- Deduplication and comprehensive import logging.
"""

import re
import hashlib
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass, field, asdict
from typing import Dict, Any, List, Optional, Tuple, Set, Union

from backend.models.civic_issue import (
    IssueCategoryEnum,
    sanitize_pii,
    GrievanceRecord
)
from backend.core.logger import setup_logger

logger = setup_logger("civiclens.phase8.ingestion")


# ---------------------------------------------------------------------------
# 1. Canonical Grievance Record Data Container
# ---------------------------------------------------------------------------
@dataclass
class CanonicalGrievanceRecord:
    """Canonical normalized public grievance record."""
    grievance_id: str
    source_id: str
    issue_category: Optional[str]
    description_or_permitted_summary: str
    submission_date: datetime
    department_id: Optional[str]
    administrative_area_id: Optional[str]
    status: str
    acknowledgement_date: Optional[datetime]
    resolution_date: Optional[datetime]
    source_document_id: Optional[int]
    source_record_reference: Optional[str]
    ingestion_timestamp: datetime
    data_quality_status: str
    raw_record_reference: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        if self.submission_date:
            d["submission_date"] = self.submission_date.isoformat()
        if self.acknowledgement_date:
            d["acknowledgement_date"] = self.acknowledgement_date.isoformat()
        if self.resolution_date:
            d["resolution_date"] = self.resolution_date.isoformat()
        if self.ingestion_timestamp:
            d["ingestion_timestamp"] = self.ingestion_timestamp.isoformat()
        return d

    def to_orm(self, is_test_fixture: bool = False) -> GrievanceRecord:
        """Converts to database ORM entity."""
        category_enum = None
        if self.issue_category:
            try:
                category_enum = IssueCategoryEnum(self.issue_category)
            except ValueError:
                category_enum = None

        return GrievanceRecord(
            grievance_id=self.grievance_id,
            source_id=self.source_id,
            issue_category=category_enum,
            description_or_permitted_summary=self.description_or_permitted_summary,
            submission_date=self.submission_date,
            department_id=self.department_id,
            administrative_area_id=self.administrative_area_id,
            status=self.status,
            acknowledgement_date=self.acknowledgement_date,
            resolution_date=self.resolution_date,
            source_document_id=self.source_document_id,
            source_record_reference=self.source_record_reference,
            ingestion_timestamp=self.ingestion_timestamp,
            data_quality_status=self.data_quality_status,
            raw_metadata=self.raw_record_reference,
            is_anonymized=True,
            is_test_fixture=is_test_fixture
        )


# ---------------------------------------------------------------------------
# 2. Date Normalizer
# ---------------------------------------------------------------------------
class DateNormalizer:
    """Normalizes heterogeneous date string representations to UTC datetime."""

    DATE_FORMATS = [
        "%Y-%m-%dT%H:%M:%SZ",
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M",
        "%Y-%m-%d",
        "%d/%m/%Y %H:%M:%S",
        "%d/%m/%Y %H:%M",
        "%d/%m/%Y",
        "%d-%m-%Y %H:%M:%S",
        "%d-%m-%Y",
        "%d/%m/%y",
        "%d-%m-%y",
        "%d-%b-%Y",
        "%d %b %Y",
        "%d-%B-%Y",
        "%d %B %Y",
        "%B %d, %Y",
        "%b %d, %Y",
        "%Y/%m/%d"
    ]

    @classmethod
    def parse_date(cls, val: Any) -> Tuple[Optional[datetime], Optional[str]]:
        """
        Parses date and returns (parsed_dt, quality_warning).
        Returns (None, None) if val is empty.
        Returns (None, 'SUSPECT_DATE') if unparseable or in future.
        """
        if val is None:
            return None, None

        if isinstance(val, (int, float)):
            try:
                # Handle epoch timestamp
                dt = datetime.fromtimestamp(val, tz=timezone.utc)
                return dt, None
            except Exception:
                return None, "SUSPECT_DATE"

        val_str = str(val).strip()
        if not val_str or val_str.lower() in ("null", "none", "n/a", "na", "-"):
            return None, None

        # Clean trailing timezone Z or offset if needed
        clean_str = re.sub(r'\.\d+', '', val_str)  # Strip microseconds

        for fmt in cls.DATE_FORMATS:
            try:
                parsed = datetime.strptime(clean_str, fmt)
                if parsed.tzinfo is None:
                    parsed = parsed.replace(tzinfo=timezone.utc)
                else:
                    parsed = parsed.astimezone(timezone.utc)

                # Sanity check: cannot be in future (> tomorrow) or pre-2000
                now = datetime.now(timezone.utc)
                if parsed > now + timedelta(days=1):
                    return parsed, "SUSPECT_DATE_IN_FUTURE"
                if parsed.year < 2000:
                    return parsed, "SUSPECT_DATE_PRE_2000"

                return parsed, None
            except ValueError:
                continue

        logger.debug(f"Could not parse date format for: {val_str}")
        return None, "SUSPECT_DATE_UNPARSEABLE"


# ---------------------------------------------------------------------------
# 3. Category Normalizer
# ---------------------------------------------------------------------------
class CategoryNormalizer:
    """Normalizes raw complaint category text across Tamil and English."""

    CATEGORY_KEYWORDS: Dict[str, List[str]] = {
        IssueCategoryEnum.ROADS.value: [
            "road", "pothole", "asphalt", "tar road", "crater", "footpath",
            "pavement", "speed breaker", "cave in", "caved in",
            "சாலை", "குண்டு குழி", "தார் சாலை", "நடைபாதை", "வேகத்தடை", "பள்ளம்"
        ],
        IssueCategoryEnum.WATER_SUPPLY.value: [
            "drinking water", "tap water", "pipe leak", "pipeline burst",
            "water shortage", "contaminated water", "potable water", "tanker",
            "borewell", "twad", "cmwssb", "metro water",
            "குடிநீர்", "குழாய் உடைப்பு", "தண்ணீர் தட்டுப்பாடு", "குடிநீர் பற்றாக்குறை", "அசுத்த நீர்"
        ],
        IssueCategoryEnum.DRAINAGE.value: [
            "drainage", "sewage", "stormwater", "storm water", "sewer",
            "manhole", "clogged drain", "drain overflow", "sewage overflow",
            "gutter", "sullage",
            "பாதாள சாக்கடை", "கழிவுநீர்", "மழைநீர் வடிகால்", "சாக்கடை அடைப்பு", "கழிவுநீர் வழிதல்"
        ],
        IssueCategoryEnum.SANITATION.value: [
            "sanitation", "public toilet", "urinal", "unhygienic", "stench",
            "open defecation", "fogging", "mosquito", "public hygiene",
            "பொது சுகாதாரம்", "பொது கழிப்பறை", "கொசு மருந்து", "துர்நாற்றம்"
        ],
        IssueCategoryEnum.WASTE_MANAGEMENT.value: [
            "waste", "garbage", "trash", "dump", "solid waste", "bin",
            "dumper", "litter", "sweeping", "conservancy", "garbage collection",
            "குப்பை", "திடக்கழிவு", "குப்பைத் தொட்டி", "குப்பை அள்ளாமை", "குப்பை அகற்றம்"
        ],
        IssueCategoryEnum.STREETLIGHTS.value: [
            "street light", "streetlight", "lamp post", "dark street", "flickering",
            "led light", "bulb replacement", "street lamp",
            "தெருவிளக்கு", "எரியாத விளக்கு", "மின் விளக்கு", "இருள் சூழ்ந்த தெரு", "விளக்கு கம்பம்"
        ],
        IssueCategoryEnum.PUBLIC_TRANSPORT.value: [
            "bus", "bus stop", "bus shelter", "bus route", "mtc", "tnstc",
            "depot", "transport", "conductor", "bus frequency",
            "பேருந்து", "பேருந்து நிறுத்தம்", "நிழற்குடை", "அரசு பேருந்து", "பேருந்து சேவை"
        ],
        IssueCategoryEnum.HEALTHCARE_ACCESS.value: [
            "hospital", "phc", "health centre", "health center", "clinic",
            "doctor", "medicine shortage", "ambulance", "dph", "gh",
            "மருத்துவமனை", "ஆரம்ப சுகாதார நிலையம்", "மருந்து தட்டுப்பாடு", "மருத்துவர்"
        ],
        IssueCategoryEnum.EDUCATION_INFRASTRUCTURE.value: [
            "school", "classroom", "student", "desk", "blackboard",
            "school toilet", "school building", "school roof", "school water",
            "அரசு பள்ளி", "வகுப்பறை", "பள்ளி கட்டிடம்", "பள்ளி கழிப்பறை", "பள்ளி மேற்கூரை"
        ],
        IssueCategoryEnum.ELECTRICITY.value: [
            "electricity", "power cut", "power supply", "transformer", "low voltage",
            "tneb", "tangedco", "snapped wire", "electric pole", "blackout",
            "மின்சாரம்", "மின்தடை", "மின்மாற்றி", "குறைந்த மின்னழுத்தம்", "மின்கம்பி", "மின் கம்பம்"
        ],
        IssueCategoryEnum.PUBLIC_SAFETY_INFRASTRUCTURE.value: [
            "safety", "traffic light", "traffic signal", "cctv", "stray dog",
            "dog menace", "cattle menace", "blind spot", "barricade",
            "போக்குவரத்து சிக்னல்", "தெரு நாய்", "நாய்கள் தொல்லை", "மாடுகள் தொல்லை", "கண்காணிப்பு கேமரா"
        ],
        IssueCategoryEnum.ENVIRONMENTAL_CONCERNS.value: [
            "pollution", "environment", "lake", "waterbody", "encroachment",
            "chemical discharge", "tree felling", "air quality", "tnpcb",
            "ஏரி ஆக்கிரமிப்பு", "குளம் மாசு", "சுற்றுச்சூழல்", "காற்று மாசு", "மரம் வெட்டுதல்"
        ],
        IssueCategoryEnum.GOVERNMENT_SERVICE_DELAYS.value: [
            "delay", "patta", "chitta", "ration card", "smart card", "pension",
            "certificate", "oap", "community certificate", "birth certificate", "death certificate",
            "பட்டா", "பட்டா மாறுதல்", "பட்டா மாற்றம்", "ரேஷன் அட்டை", "குடும்ப அட்டை", "முதியோர் உதவித்தொகை", "சான்றிதழ் தாமதம்", "தாமதம்"
        ],
        IssueCategoryEnum.OTHER_CIVIC_ISSUES.value: [
            "other", "general", "civic problem", "public nuisance", "municipal grievance",
            "பிற பிரச்சனைகள்", "பொது தொல்லை"
        ]
    }

    @classmethod
    def normalize_category(cls, raw_val: Optional[str], description_text: Optional[str] = None) -> Tuple[Optional[str], Optional[str]]:
        """
        Normalizes raw category text. Returns (category_code, warning_flag).
        """
        candidate_text = f"{raw_val or ''} {description_text or ''}".lower().strip()
        if not candidate_text:
            return None, "MISSING_CATEGORY"

        # 1. Exact match against Enum values
        clean_raw = str(raw_val or "").strip().lower().replace(" ", "_")
        for enum_item in IssueCategoryEnum:
            if clean_raw == enum_item.value:
                return enum_item.value, None

        # 2. Keyword match
        matched_scores: Dict[str, int] = {}
        for cat_code, keywords in cls.CATEGORY_KEYWORDS.items():
            score = sum(1 for kw in keywords if kw in candidate_text)
            if score > 0:
                matched_scores[cat_code] = score

        if matched_scores:
            best_cat = max(matched_scores.items(), key=lambda x: x[1])[0]
            return best_cat, None

        # Fallback to OTHER if text is provided but doesn't match specific keyword
        if raw_val:
            return IssueCategoryEnum.OTHER_CIVIC_ISSUES.value, "AMBIGUOUS_CATEGORY"

        return None, "MISSING_CATEGORY"


# ---------------------------------------------------------------------------
# 4. Department Normalizer
# ---------------------------------------------------------------------------
class DepartmentNormalizer:
    """Normalizes departmental strings, agency codes, and transliterations."""

    DEPARTMENT_MAP = {
        "DEPT_MAWS": [
            "maws", "municipal administration", "municipal administration and water supply",
            "cmwssb", "chennai metro water", "metro water", "twad", "twad board",
            "directorate of municipal administration", "dma", "town panchayats",
            "நகராட்சி நிர்வாகம்", "குடிநீர் வழங்கல்", "சென்னை குடிநீர் வாரியம்"
        ],
        "DEPT_HIGHWAYS": [
            "highways", "highways and minor ports", "highways department",
            "state highways", "national highways", "nhai", "roads and bridges",
            "நெடுஞ்சாலைத்துறை", "நெடுஞ்சாலை மற்றும் சிறு துறைமுகங்கள்"
        ],
        "DEPT_TANGEDCO": [
            "tangedco", "tneb", "electricity board", "power", "energy department",
            "distribution corporation", "tamil nadu electricity board",
            "மின்வாரியம்", "மின் உற்பத்தி", "மின் பகிர்மானக் கழகம்"
        ],
        "DEPT_GCC": [
            "gcc", "greater chennai corporation", "chennai corporation",
            "corporation of chennai", "பெருநகர சென்னை மாநகராட்சி"
        ],
        "DEPT_HEALTH": [
            "health", "health and family welfare", "public health", "dph",
            "medical services", "family welfare", "மக்கள் நல்வாழ்வுத்துறை", "சுகாதாரத்துறை"
        ],
        "DEPT_REVENUE": [
            "revenue", "revenue and disaster management", "taluk office",
            "collectorate", "tahsildar", "revenue administration", "வருவாய்த்துறை"
        ],
        "DEPT_SCHOOL_EDU": [
            "school education", "school education department", "dse",
            "elementary education", "samagra shiksha", "பள்ளிக் கல்வித்துறை"
        ],
        "DEPT_TRANSPORT": [
            "transport", "transport department", "tnstc", "mtc", "state transport",
            "போக்குவரத்துத்துறை", "மாநகரப் போக்குவரத்து"
        ],
        "DEPT_POLICE": [
            "police", "home department", "law and order", "traffic police",
            "காவல்துறை", "போக்குவரத்து காவல்துறை"
        ],
        "DEPT_ENV_FOREST": [
            "environment", "environment and climate change", "forest",
            "tnpcb", "pollution control board", "சுற்றுச்சூழல் துறை", "வனத்துறை"
        ]
    }

    @classmethod
    def normalize_department(cls, raw_val: Optional[str]) -> Tuple[Optional[str], Optional[str]]:
        if not raw_val:
            return None, "MISSING_DEPARTMENT"

        clean_val = str(raw_val).strip().lower()
        if not clean_val or clean_val in ("null", "none", "-"):
            return None, "MISSING_DEPARTMENT"

        # Check canonical department code directly
        raw_upper = str(raw_val).strip().upper()
        if raw_upper in cls.DEPARTMENT_MAP:
            return raw_upper, None

        # Check keyword aliases
        for dept_code, aliases in cls.DEPARTMENT_MAP.items():
            for alias in aliases:
                if alias in clean_val:
                    return dept_code, None

        return None, "AMBIGUOUS_DEPARTMENT"


# ---------------------------------------------------------------------------
# 5. Administrative Area Normalizer
# ---------------------------------------------------------------------------
class AreaNormalizer:
    """Normalizes Tamil Nadu administrative boundary references (districts, zones, wards)."""

    DISTRICT_MAP = {
        "ADM-TN-DIST-013-CHENNAI": ["chennai", "madras", "சென்னை"],
        "ADM-TN-DIST-024-MADURAI": ["madurai", "மதுரை"],
        "ADM-TN-DIST-032-COIMBATORE": ["coimbatore", "kovai", "கோவை", "கோயம்புத்தூர்"],
        "ADM-TN-DIST-017-TIRUCHIRAPPALLI": ["tiruchirappalli", "trichy", "திருச்சிராப்பள்ளி", "திருச்சி"],
        "ADM-TN-DIST-008-SALEM": ["salem", "சேலம்"],
        "ADM-TN-DIST-029-TIRUNELVELI": ["tirunelveli", "nellai", "திருநெல்வேலி", "நெல்லை"],
        "ADM-TN-DIST-014-CHENGALPATTU": ["chengalpattu", "chengalpet", "செங்கல்பட்டு"],
        "ADM-TN-DIST-004-VELLORE": ["vellore", "வேலூர்"],
        "ADM-TN-DIST-019-THANJAVUR": ["thanjavur", "tanjore", "தஞ்சாவூர்"],
        "ADM-TN-DIST-010-ERODE": ["erode", "ஈரோடு"],
        "ADM-TN-DIST-012-TIRUVALLUR": ["tiruvallur", "thiruvallur", "திருவள்ளூர்"],
        "ADM-TN-DIST-015-KANCHIPURAM": ["kanchipuram", "kancheepuram", "காஞ்சிபுரம்"],
        "ADM-TN-DIST-021-DINDIGUL": ["dindigul", "திண்டுக்கல்"],
        "ADM-TN-DIST-030-THOOTHUKUDI": ["thoothukudi", "tuticorin", "தூத்துக்குடி"],
        "ADM-TN-DIST-031-KANNIYAKUMARI": ["kanniyakumari", "kanyakumari", "கன்னியாகுமரி"]
    }

    @classmethod
    def normalize_area(
        cls,
        district_val: Optional[str] = None,
        ward_val: Optional[str] = None,
        zone_val: Optional[str] = None
    ) -> Tuple[Optional[str], Optional[str]]:
        """
        Normalizes hierarchical area. Prioritizes ward -> zone -> district.
        """
        # 1. Ward match
        if ward_val:
            ward_match = re.search(r'\b(?:ward\s*)?(\d{1,3})\b', str(ward_val), re.IGNORECASE)
            if ward_match:
                ward_num = int(ward_match.group(1))
                if 1 <= ward_num <= 200:
                    return f"ADM-TN-GCC-WARD-{ward_num}", None

        # 2. Zone match
        if zone_val:
            zone_match = re.search(r'\b(?:zone\s*)?(\d{1,2})\b', str(zone_val), re.IGNORECASE)
            if zone_match:
                zone_num = int(zone_match.group(1))
                if 1 <= zone_num <= 15:
                    return f"ADM-TN-GCC-ZONE-{zone_num}", None
            # Zone by name (e.g. Adyar)
            zone_clean = str(zone_val).lower()
            if "adyar" in zone_clean:
                return "ADM-TN-GCC-ZONE-13-ADYAR", None

        # 3. District match
        if district_val:
            clean_dist = str(district_val).strip().lower()
            for area_code, aliases in cls.DISTRICT_MAP.items():
                for alias in aliases:
                    if alias in clean_dist:
                        return area_code, None

        return None, "MISSING_AREA"


# ---------------------------------------------------------------------------
# 6. Status Normalizer
# ---------------------------------------------------------------------------
class StatusNormalizer:
    """Normalizes raw status values. Strict rule: never default unknown to resolved."""

    STATUS_MAP = {
        "RESOLVED": [
            "resolved", "closed", "disposed", "completed", "action taken",
            "rectified", "redressed", "தீர்க்கப்பட்டது", "முடிக்கப்பட்டது"
        ],
        "IN_PROGRESS": [
            "in progress", "under enquiry", "under investigation", "action initiated",
            "forwarded to officer", "site inspection scheduled", "விசாரணையில்", "நடவடிக்கையில்"
        ],
        "OPEN": [
            "open", "new", "registered", "received", "admitted", "பெறப்பட்டது", "பதிவு செய்யப்பட்டது"
        ],
        "PENDING": [
            "pending", "awaiting report", "awaiting approval", "under process", "நிலுவையில்"
        ],
        "REJECTED": [
            "rejected", "closed as ineligible", "not feasible", "cancelled",
            "duplicate closed", "dropped", "நிராகரிக்கப்பட்டது"
        ],
        "ESCALATED": [
            "escalated", "appeal filed", "reopened", "மேன்முறையீடு"
        ]
    }

    @classmethod
    def normalize_status(cls, raw_val: Optional[str]) -> Tuple[str, Optional[str]]:
        if not raw_val:
            # Strictly return UNKNOWN — do not invent resolved!
            return "UNKNOWN", "MISSING_STATUS"

        clean_val = str(raw_val).strip().lower()
        if clean_val in ("null", "none", "-", ""):
            return "UNKNOWN", "MISSING_STATUS"

        # Check direct canonical matches
        raw_upper = str(raw_val).strip().upper()
        if raw_upper in cls.STATUS_MAP:
            return raw_upper, None

        # Check alias dictionary
        for canonical_status, aliases in cls.STATUS_MAP.items():
            for alias in aliases:
                if alias in clean_val:
                    return canonical_status, None

        # If unrecognized, classify as UNKNOWN and flag warning
        return "UNKNOWN", "AMBIGUOUS_STATUS"


# ---------------------------------------------------------------------------
# 7. Duplicate Detector
# ---------------------------------------------------------------------------
class GrievanceDuplicateDetector:
    """Tracks seen record references and content hashes to detect duplicate records."""

    def __init__(self):
        self._seen_references: Set[str] = set()
        self._seen_content_hashes: Set[str] = set()

    @staticmethod
    def compute_content_hash(
        source_id: str,
        submission_date: Optional[datetime],
        category: Optional[str],
        description: str
    ) -> str:
        date_str = submission_date.strftime("%Y-%m-%d") if submission_date else "nodate"
        cat_str = category or "nocat"
        desc_clean = re.sub(r'\s+', ' ', description.strip().lower())
        fingerprint = f"{source_id}:{date_str}:{cat_str}:{desc_clean[:120]}"
        return hashlib.sha256(fingerprint.encode("utf-8")).hexdigest()

    def is_duplicate(
        self,
        source_id: str,
        record_reference: Optional[str],
        content_hash: str
    ) -> bool:
        if record_reference:
            ref_key = f"{source_id}:{record_reference.strip()}"
            if ref_key in self._seen_references:
                return True

        if content_hash in self._seen_content_hashes:
            return True

        return False

    def mark_seen(self, source_id: str, record_reference: Optional[str], content_hash: str):
        if record_reference:
            self._seen_references.add(f"{source_id}:{record_reference.strip()}")
        self._seen_content_hashes.add(content_hash)

    def clear(self):
        self._seen_references.clear()
        self._seen_content_hashes.clear()


# ---------------------------------------------------------------------------
# 8. Source-Specific Schema Adapters
# ---------------------------------------------------------------------------
class BaseGrievanceAdapter:
    """Abstract adapter mapping source-specific raw records into intermediate dict."""

    @classmethod
    def map_fields(cls, raw: Dict[str, Any]) -> Dict[str, Any]:
        raise NotImplementedError


class DARPGCPGRAMSAdapter(BaseGrievanceAdapter):
    """Adapter for Central CPGRAMS / DARPG public records."""

    @classmethod
    def map_fields(cls, raw: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "source_record_reference": raw.get("Registration Number") or raw.get("reg_no") or raw.get("registration_number"),
            "raw_category": raw.get("Category") or raw.get("subject") or raw.get("grievance_category"),
            "raw_description": raw.get("Grievance Description") or raw.get("description") or raw.get("details"),
            "raw_submission_date": raw.get("Received Date") or raw.get("date_of_receipt") or raw.get("receipt_date"),
            "raw_department": raw.get("Ministry/Dept") or raw.get("department") or raw.get("ministry"),
            "raw_district": raw.get("State/UT") or raw.get("district"),
            "raw_status": raw.get("Status") or raw.get("current_status"),
            "raw_resolution_date": raw.get("Resolution Date") or raw.get("closing_date") or raw.get("date_of_action"),
            "raw_acknowledgement_date": raw.get("Acknowledgement Date")
        }


class GreaterChennaiCorporationAdapter(BaseGrievanceAdapter):
    """Adapter for GCC 1913 / Namma Chennai complaint records."""

    @classmethod
    def map_fields(cls, raw: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "source_record_reference": raw.get("complaint_no") or raw.get("ticket_id") or raw.get("token"),
            "raw_category": raw.get("complaint_type") or raw.get("complaint_nature") or raw.get("category"),
            "raw_description": raw.get("details") or raw.get("description") or raw.get("landmark"),
            "raw_submission_date": raw.get("date") or raw.get("complaint_date") or raw.get("created_on"),
            "raw_department": "DEPT_GCC",  # Explicitly Corporation of Chennai
            "raw_district": "Chennai",
            "raw_ward": raw.get("ward_no") or raw.get("ward"),
            "raw_zone": raw.get("zone_no") or raw.get("zone"),
            "raw_status": raw.get("status") or raw.get("complaint_status"),
            "raw_resolution_date": raw.get("closed_date") or raw.get("resolved_on"),
            "raw_acknowledgement_date": raw.get("ack_date")
        }


class MudhalvarinMugavariAdapter(BaseGrievanceAdapter):
    """Adapter for TNeGA CM Helpline 1100 / IIPGCMS records."""

    @classmethod
    def map_fields(cls, raw: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "source_record_reference": raw.get("petition_id") or raw.get("grievance_no") or raw.get("ticket_no"),
            "raw_category": raw.get("grievance_nature") or raw.get("sub_category") or raw.get("subject"),
            "raw_description": raw.get("petition_summary") or raw.get("grievance_text") or raw.get("details"),
            "raw_submission_date": raw.get("lodged_on") or raw.get("petition_date") or raw.get("received_date"),
            "raw_department": raw.get("department_name") or raw.get("department_id"),
            "raw_district": raw.get("district") or raw.get("district_name"),
            "raw_status": raw.get("current_status") or raw.get("status"),
            "raw_resolution_date": raw.get("disposal_date") or raw.get("resolved_date"),
            "raw_acknowledgement_date": raw.get("ack_date") or raw.get("sms_sent_date")
        }


class GenericCivicAdapter(BaseGrievanceAdapter):
    """Generic fallback adapter for arbitrary civic CSV/JSON tables."""

    @classmethod
    def map_fields(cls, raw: Dict[str, Any]) -> Dict[str, Any]:
        lower_raw = {k.lower().strip(): v for k, v in raw.items()}
        return {
            "source_record_reference": (
                lower_raw.get("id") or lower_raw.get("complaint_id") or lower_raw.get("grievance_id") or
                lower_raw.get("ref_no") or lower_raw.get("reference")
            ),
            "raw_category": (
                lower_raw.get("category") or lower_raw.get("issue_category") or lower_raw.get("type") or
                lower_raw.get("nature")
            ),
            "raw_description": (
                lower_raw.get("description") or lower_raw.get("details") or lower_raw.get("summary") or
                lower_raw.get("notes") or lower_raw.get("remarks")
            ),
            "raw_submission_date": (
                lower_raw.get("submission_date") or lower_raw.get("date") or lower_raw.get("created_at") or
                lower_raw.get("received_date") or lower_raw.get("lodged_date")
            ),
            "raw_department": (
                lower_raw.get("department") or lower_raw.get("department_id") or lower_raw.get("ministry")
            ),
            "raw_district": lower_raw.get("district") or lower_raw.get("city") or lower_raw.get("area"),
            "raw_ward": lower_raw.get("ward") or lower_raw.get("ward_no"),
            "raw_zone": lower_raw.get("zone") or lower_raw.get("zone_no"),
            "raw_status": lower_raw.get("status") or lower_raw.get("resolution_status"),
            "raw_resolution_date": (
                lower_raw.get("resolution_date") or lower_raw.get("resolved_date") or lower_raw.get("closed_date")
            ),
            "raw_acknowledgement_date": lower_raw.get("acknowledgement_date") or lower_raw.get("ack_date")
        }


# ---------------------------------------------------------------------------
# 9. Ingestion Report Container
# ---------------------------------------------------------------------------
@dataclass
class IngestionReport:
    """Detailed audit metrics for a normalization run."""
    total_processed: int = 0
    valid_records: int = 0
    duplicates_detected: int = 0
    missing_required_fields: int = 0
    flagged_quality_issues: int = 0
    source_id: str = "UNKNOWN"
    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: Optional[datetime] = None
    quality_issues_breakdown: Dict[str, int] = field(default_factory=dict)

    def record_quality_issue(self, issue_code: str):
        self.quality_issues_breakdown[issue_code] = self.quality_issues_breakdown.get(issue_code, 0) + 1
        self.flagged_quality_issues += 1


# ---------------------------------------------------------------------------
# 10. Central Grievance Normalization Pipeline
# ---------------------------------------------------------------------------
class GrievanceNormalizer:
    """
    Central pipeline converting heterogeneous source records into canonical format.
    """

    ADAPTER_REGISTRY = {
        "DARPG_CPGRAMS": DARPGCPGRAMSAdapter,
        "GCC_CHENNAI": GreaterChennaiCorporationAdapter,
        "TNEGA_CM_HELPLINE": MudhalvarinMugavariAdapter,
        "GENERIC": GenericCivicAdapter
    }

    def __init__(self):
        self.duplicate_detector = GrievanceDuplicateDetector()

    def _get_adapter(self, source_id: str) -> type:
        return self.ADAPTER_REGISTRY.get(source_id, GenericCivicAdapter)

    def normalize_single_record(
        self,
        raw_record: Dict[str, Any],
        source_id: str,
        source_document_id: Optional[int] = None,
        ingestion_timestamp: Optional[datetime] = None
    ) -> Tuple[Optional[CanonicalGrievanceRecord], str]:
        """
        Normalizes a single dictionary record.
        Returns (canonical_record, result_status).
        result_status in: 'VALID', 'DUPLICATE', 'INVALID_MISSING_REQUIRED'
        """
        ingest_ts = ingestion_timestamp or datetime.now(timezone.utc)
        adapter = self._get_adapter(source_id)
        mapped = adapter.map_fields(raw_record)

        # 1. PII Redaction on raw text description
        raw_desc = str(mapped.get("raw_description") or mapped.get("raw_category") or "Public civic grievance").strip()
        sanitized_desc = sanitize_pii(raw_desc)

        # 2. Date Normalization
        sub_dt, date_warn = DateNormalizer.parse_date(mapped.get("raw_submission_date"))
        if sub_dt is None:
            # Submission date is mandatory for canonical record
            return None, "INVALID_MISSING_REQUIRED"

        res_dt, res_warn = DateNormalizer.parse_date(mapped.get("raw_resolution_date"))
        ack_dt, _ = DateNormalizer.parse_date(mapped.get("raw_acknowledgement_date"))

        # Check resolution date not earlier than submission date
        if sub_dt and res_dt and res_dt < sub_dt:
            res_warn = "SUSPECT_DATE_RESOLUTION_PRECEDES_SUBMISSION"

        # 3. Category Normalization
        cat_code, cat_warn = CategoryNormalizer.normalize_category(
            raw_val=mapped.get("raw_category"),
            description_text=sanitized_desc
        )

        # 4. Department Normalization
        dept_code, dept_warn = DepartmentNormalizer.normalize_department(mapped.get("raw_department"))

        # 5. Administrative Area Normalization
        area_code, area_warn = AreaNormalizer.normalize_area(
            district_val=mapped.get("raw_district"),
            ward_val=mapped.get("raw_ward"),
            zone_val=mapped.get("raw_zone")
        )

        # 6. Status Normalization (Never default unknown to resolved!)
        canonical_status, status_warn = StatusNormalizer.normalize_status(mapped.get("raw_status"))

        # 7. Source Reference & Canonical Grievance ID
        raw_ref = mapped.get("source_record_reference")
        content_hash = GrievanceDuplicateDetector.compute_content_hash(
            source_id=source_id,
            submission_date=sub_dt,
            category=cat_code,
            description=sanitized_desc
        )

        # 8. Duplicate Detection
        if self.duplicate_detector.is_duplicate(
            source_id=source_id,
            record_reference=str(raw_ref) if raw_ref else None,
            content_hash=content_hash
        ):
            return None, "DUPLICATE"

        self.duplicate_detector.mark_seen(
            source_id=source_id,
            record_reference=str(raw_ref) if raw_ref else None,
            content_hash=content_hash
        )

        # Generate deterministic canonical grievance_id
        ref_slug = re.sub(r'[^A-Za-z0-9]', '-', str(raw_ref or content_hash[:12])).strip('-')
        canonical_id = f"GRV-{source_id}-{ref_slug}"

        # 9. Compile Data Quality Status
        warnings = [w for w in (date_warn, res_warn, cat_warn, dept_warn, area_warn, status_warn) if w]
        if warnings:
            quality_status = warnings[0]  # Record primary warning flag
        else:
            quality_status = "VALID"

        # 10. Audit Record (Retain restricted raw reference safely)
        restricted_raw = {
            "source_record_reference": raw_ref,
            "raw_category": mapped.get("raw_category"),
            "raw_status": mapped.get("raw_status"),
            "fingerprint": content_hash
        }

        record = CanonicalGrievanceRecord(
            grievance_id=canonical_id,
            source_id=source_id,
            issue_category=cat_code,
            description_or_permitted_summary=sanitized_desc,
            submission_date=sub_dt,
            department_id=dept_code,
            administrative_area_id=area_code,
            status=canonical_status,
            acknowledgement_date=ack_dt,
            resolution_date=res_dt,
            source_document_id=source_document_id,
            source_record_reference=str(raw_ref) if raw_ref else None,
            ingestion_timestamp=ingest_ts,
            data_quality_status=quality_status,
            raw_record_reference=restricted_raw
        )

        return record, "VALID"

    def normalize_batch(
        self,
        raw_records: List[Dict[str, Any]],
        source_id: str,
        source_document_id: Optional[int] = None
    ) -> Tuple[List[CanonicalGrievanceRecord], IngestionReport]:
        """
        Normalizes a batch of records and generates an audit IngestionReport.
        """
        report = IngestionReport(source_id=source_id)
        canonical_records: List[CanonicalGrievanceRecord] = []
        ingest_ts = datetime.now(timezone.utc)

        for raw_item in raw_records:
            report.total_processed += 1
            record, outcome = self.normalize_single_record(
                raw_record=raw_item,
                source_id=source_id,
                source_document_id=source_document_id,
                ingestion_timestamp=ingest_ts
            )

            if outcome == "VALID" and record:
                report.valid_records += 1
                if record.data_quality_status != "VALID":
                    report.record_quality_issue(record.data_quality_status)
                canonical_records.append(record)
            elif outcome == "DUPLICATE":
                report.duplicates_detected += 1
            elif outcome == "INVALID_MISSING_REQUIRED":
                report.missing_required_fields += 1

        report.completed_at = datetime.now(timezone.utc)
        return canonical_records, report
