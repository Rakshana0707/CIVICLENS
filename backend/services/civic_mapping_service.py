"""
Civic Geographic Mapping & Department Jurisdiction Service (CIVICLENS TN - Phase 8.5)
=====================================================================================
Connects civic issues to administrative areas and responsible government departments
where supported by official information.

Covers:
  - State (ADM-TN-STATE)
  - 38 Districts (e.g. ADM-TN-DIST-003-CHENNAI, ADM-TN-DIST-013-MADURAI)
  - Municipal Corporations / ULBs (e.g. GCC Zones 1 to 15, Madurai Corporation)
  - Wards and Local Areas (e.g. GCC Ward 1 to 200)
  - Relevant Government Departments & Responsible Local Authorities

Core Directives & Safeguards:
  - Uses official administrative boundaries and source records.
  - Never infers a precise location from vague descriptions.
  - Never assigns ward-level details when only district-level information is available.
  - Detects ambiguous place name homonyms (e.g. 'Anna Nagar', 'Gandhi Nagar') without
    district context, routing to human review rather than guessing.
  - Resolves historical boundary reorganizations (e.g. Chengalpattu split from
    Kancheepuram in Nov 2019, Ranipet from Vellore in Nov 2019).
  - Handles shared or unclear department responsibilities (e.g. state highways inside
    corporation limits) with candidate departments and unresolved statuses.

For each mapping, records:
  - issue_id
  - administrative_area_id
  - geographic_level
  - department_id where known
  - mapping_method
  - source_reference
  - confidence
  - review_status
"""

import math
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Tuple, Any
from sqlalchemy.orm import Session

from backend.models.civic_issue import (
    CivicIssue,
    GrievanceRecord,
    AdministrativeArea,
    AdministrativeLevel,
    CivicDepartment,
    ServiceStandard,
    IssueCategory,
    IssueCategoryEnum,
    DataQualityIssue,
    DataQualitySeverity
)


# ---------------------------------------------------------------------------
# Data Containers
# ---------------------------------------------------------------------------
@dataclass
class GeographicResolutionResult:
    """Resolved administrative area details."""
    area_code: str
    area_name_en: str
    area_name_ta: str
    administrative_level: AdministrativeLevel
    confidence: float
    is_imprecise: bool = False
    warning_flag: Optional[str] = None  # COARSE_GEOGRAPHY, MISSING_LOCATION, AMBIGUOUS_PLACE_NAME, HISTORICAL_BOUNDARY_SPLIT
    matched_via: str = "EXACT_CODE"     # EXACT_CODE, BILINGUAL_NAME, GPS_COORDINATE, TEXT_EXTRACTION, HISTORICAL_CROSS_REFERENCE, FALLBACK_CONTAINER
    historical_context: Optional[str] = None
    candidate_areas: List[str] = field(default_factory=list)


@dataclass
class DepartmentJurisdictionResult:
    """Resolved department jurisdiction and Citizen's Charter SLA."""
    department_code: Optional[str]
    department_name_en: str
    jurisdiction_level: str
    service_standard_code: Optional[str] = None
    sla_hours: int = 72
    designated_officer: str = "Assistant Engineer / Zonal Officer"
    target_resolution_date: Optional[datetime] = None
    confidence: float = 1.0
    jurisdiction_notes: str = ""
    candidate_departments: List[str] = field(default_factory=list)
    responsible_local_authority: Optional[str] = None
    is_shared_responsibility: bool = False
    department_status: str = "RESOLVED"  # RESOLVED, SHARED, UNRESOLVED
    review_status: str = "AUTOMATED_VERIFIED"  # AUTOMATED_VERIFIED, PENDING_HUMAN_REVIEW


@dataclass
class CivicMappingRecord:
    """Canonical mapping audit record matching Phase 8.5 specifications."""
    issue_id: Optional[int]
    administrative_area_id: str
    geographic_level: str
    department_id: Optional[str]
    mapping_method: str
    source_reference: Optional[str]
    confidence: float
    review_status: str
    candidate_departments: List[str] = field(default_factory=list)
    responsible_local_authority: Optional[str] = None
    is_shared_responsibility: bool = False
    warning_flag: Optional[str] = None
    historical_context: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "issue_id": self.issue_id,
            "administrative_area_id": self.administrative_area_id,
            "geographic_level": self.geographic_level,
            "department_id": self.department_id,
            "mapping_method": self.mapping_method,
            "source_reference": self.source_reference,
            "confidence": round(self.confidence, 4),
            "review_status": self.review_status,
            "candidate_departments": self.candidate_departments,
            "responsible_local_authority": self.responsible_local_authority,
            "is_shared_responsibility": self.is_shared_responsibility,
            "warning_flag": self.warning_flag,
            "historical_context": self.historical_context
        }


# ---------------------------------------------------------------------------
# 1. Geographic Mapping Engine
# ---------------------------------------------------------------------------
class CivicGeographicMapper:
    """
    Maps heterogeneous text, bilingual names, and GPS coordinates to
    canonical AdministrativeArea records across Tamil Nadu.
    """

    # 38 Tamil Nadu Districts directory (English & Tamil with Centroids)
    TN_DISTRICTS: Dict[str, Tuple[str, str, float, float]] = {
        "ADM-TN-DIST-001-ARIYALUR": ("Ariyalur", "அரியலூர்", 11.1401, 79.0786),
        "ADM-TN-DIST-002-CHENGALPATTU": ("Chengalpattu", "செங்கல்பட்டு", 12.6937, 79.9757),
        "ADM-TN-DIST-003-CHENNAI": ("Chennai", "சென்னை", 13.0827, 80.2707),
        "ADM-TN-DIST-004-COIMBATORE": ("Coimbatore", "கோயம்புத்தூர்", 11.0168, 76.9558),
        "ADM-TN-DIST-005-CUDDALORE": ("Cuddalore", "கடலூர்", 11.7480, 79.7714),
        "ADM-TN-DIST-006-DHARMAPURI": ("Dharmapuri", "தர்மபுரி", 12.1211, 78.1582),
        "ADM-TN-DIST-007-DINDIGUL": ("Dindigul", "திண்டுக்கல்", 10.3673, 77.9803),
        "ADM-TN-DIST-008-ERODE": ("Erode", "ஈரோடு", 11.3410, 77.7172),
        "ADM-TN-DIST-009-KALLAKURICHI": ("Kallakurichi", "கள்ளக்குறிச்சி", 11.7384, 78.9639),
        "ADM-TN-DIST-010-KANCHEEPURAM": ("Kancheepuram", "காஞ்சிபுரம்", 12.8342, 79.7036),
        "ADM-TN-DIST-011-KARUR": ("Karur", "கரூர்", 10.9601, 78.0766),
        "ADM-TN-DIST-012-KRISHNAGIRI": ("Krishnagiri", "கிருஷ்ணகிரி", 12.5186, 78.2137),
        "ADM-TN-DIST-013-MADURAI": ("Madurai", "மதுரை", 9.9252, 78.1198),
        "ADM-TN-DIST-014-MAYILADUTHURAI": ("Mayiladuthurai", "மயிலாடுதுறை", 11.1075, 79.6524),
        "ADM-TN-DIST-015-NAGAPATTINAM": ("Nagapattinam", "நாகப்பட்டினம்", 10.7672, 79.8449),
        "ADM-TN-DIST-016-NAMAKKAL": ("Namakkal", "நாமக்கல்", 11.2189, 78.1674),
        "ADM-TN-DIST-017-NILGIRIS": ("Nilgiris", "நீலகிரி", 11.4102, 76.6950),
        "ADM-TN-DIST-018-PERAMBALUR": ("Perambalur", "பெரம்பலூர்", 11.2342, 78.8820),
        "ADM-TN-DIST-019-PUDUKKOTTAI": ("Pudukkottai", "புதுக்கோட்டை", 10.3833, 78.8001),
        "ADM-TN-DIST-020-RAMANATHAPURAM": ("Ramanathapuram", "ராமநாதபுரம்", 9.3639, 78.8395),
        "ADM-TN-DIST-021-RANIPET": ("Ranipet", "ராணிப்பேட்டை", 12.9229, 79.3328),
        "ADM-TN-DIST-022-SALEM": ("Salem", "சேலம்", 11.6643, 78.1460),
        "ADM-TN-DIST-023-SIVAGANGA": ("Sivaganga", "சிவகங்கை", 9.8433, 78.4809),
        "ADM-TN-DIST-024-TENKASI": ("Tenkasi", "தென்காசி", 8.9594, 77.3150),
        "ADM-TN-DIST-025-THANJAVUR": ("Thanjavur", "தஞ்சாவூர்", 10.7870, 79.1378),
        "ADM-TN-DIST-026-THENI": ("Theni", "தேனி", 10.0104, 77.4768),
        "ADM-TN-DIST-027-THOOTHUKUDI": ("Thoothukudi", "தூத்துக்குடி", 8.7642, 78.1348),
        "ADM-TN-DIST-028-TIRUCHIRAPPALLI": ("Tiruchirappalli", "திருச்சிராப்பள்ளி", 10.7905, 78.7047),
        "ADM-TN-DIST-029-TIRUNELVELI": ("Tirunelveli", "திருநெல்வேலி", 8.7139, 77.7567),
        "ADM-TN-DIST-030-TIRUPATHUR": ("Tirupathur", "திருப்பத்தூர்", 12.4965, 78.5638),
        "ADM-TN-DIST-031-TIRUPPUR": ("Tiruppur", "திருப்பூர்", 11.1085, 77.3411),
        "ADM-TN-DIST-032-TIRUVALLUR": ("Tiruvallur", "திருவள்ளூர்", 13.1432, 79.9083),
        "ADM-TN-DIST-033-TIRUVANNAMALAI": ("Tiruvannamalai", "திருவண்ணாமலை", 12.2253, 79.0747),
        "ADM-TN-DIST-034-TIRUVARUR": ("Tiruvarur", "திருவாரூர்", 10.7725, 79.6365),
        "ADM-TN-DIST-035-VELLORE": ("Vellore", "வேலூர்", 12.9165, 79.1325),
        "ADM-TN-DIST-036-VILUPPURAM": ("Viluppuram", "விழுப்புரம்", 11.9401, 79.4861),
        "ADM-TN-DIST-037-VIRUDHUNAGAR": ("Virudhunagar", "விருதுநகர்", 9.5680, 77.9624),
        "ADM-TN-DIST-038-KANNIYAKUMARI": ("Kanniyakumari", "கன்னியாகுமரி", 8.0883, 77.5385)
    }

    # Greater Chennai Corporation (GCC) 15 Zones
    GCC_ZONES: Dict[int, Tuple[str, str, str]] = {
        1: ("ADM-TN-GCC-ZONE-01-THIRUVOTTIYUR", "Zone 1 - Thiruvottiyur", "மண்டலம் 1 - திருவொற்றியூர்"),
        2: ("ADM-TN-GCC-ZONE-02-MANALI", "Zone 2 - Manali", "மண்டலம் 2 - மணலி"),
        3: ("ADM-TN-GCC-ZONE-03-MADHAVARAM", "Zone 3 - Madhavaram", "மண்டலம் 3 - மாதவரம்"),
        4: ("ADM-TN-GCC-ZONE-04-TONDIARPET", "Zone 4 - Tondiarpet", "மண்டலம் 4 - தண்டையார்பேட்டை"),
        5: ("ADM-TN-GCC-ZONE-05-ROYAPURAM", "Zone 5 - Royapuram", "மண்டலம் 5 - இராயபுரம்"),
        6: ("ADM-TN-GCC-ZONE-06-THIRU_VI_KA_NAGAR", "Zone 6 - Thiru. Vi. Ka. Nagar", "மண்டலம் 6 - திரு. வி. க. நகர்"),
        7: ("ADM-TN-GCC-ZONE-07-AMBATTUR", "Zone 7 - Ambattur", "மண்டலம் 7 - அம்பத்தூர்"),
        8: ("ADM-TN-GCC-ZONE-08-ANNA_NAGAR", "Zone 8 - Anna Nagar", "மண்டலம் 8 - அண்ணா நகர்"),
        9: ("ADM-TN-GCC-ZONE-09-TEYNAMPET", "Zone 9 - Teynampet", "மண்டலம் 9 - தேனாம்பேட்டை"),
        10: ("ADM-TN-GCC-ZONE-10-KODAMBAKKAM", "Zone 10 - Kodambakkam", "மண்டலம் 10 - கோடம்பாக்கம்"),
        11: ("ADM-TN-GCC-ZONE-11-VALASARAVAKKAM", "Zone 11 - Valasaravakkam", "மண்டலம் 11 - வளசரவாக்கம்"),
        12: ("ADM-TN-GCC-ZONE-12-ALANDUR", "Zone 12 - Alandur", "மண்டலம் 12 - ஆலந்தூர்"),
        13: ("ADM-TN-GCC-ZONE-13-ADYAR", "Zone 13 - Adyar", "மண்டலம் 13 - அடையாறு"),
        14: ("ADM-TN-GCC-ZONE-14-PERUNGUDI", "Zone 14 - Perungudi", "மண்டலம் 14 - பெருங்குடி"),
        15: ("ADM-TN-GCC-ZONE-15-SHOLINGANALLUR", "Zone 15 - Sholinganallur", "மண்டலம் 15 - சோழிங்கநல்லூர்")
    }

    # Ambiguous Homonyms across Tamil Nadu
    AMBIGUOUS_HOMONYMS: Dict[str, List[str]] = {
        "anna nagar": ["Chennai (Zone 8)", "Madurai", "Tiruchirappalli", "Salem"],
        "அண்ணா நகர்": ["சென்னை", "மதுரை", "திருச்சிராப்பள்ளி", "சேலம்"],
        "gandhi nagar": ["Vellore (Katpadi)", "Chennai (Adyar)", "Tiruppur"],
        "காந்தி நகர்": ["வேலூர்", "சென்னை", "திருப்பூர்"],
        "kottur": ["Chennai (Kotturpuram / Ward 170)", "Tiruvarur (Kottur Block)"],
        "கோட்டூர்": ["சென்னை", "திருவாரூர்"],
        "kk nagar": ["Chennai (Kodambakkam / Zone 10)", "Madurai", "Tiruchirappalli"],
        "கே.கே. நகர்": ["சென்னை", "மதுரை", "திருச்சிராப்பள்ளி"],
        "ram nagar": ["Coimbatore", "Madurai", "Chennai"],
        "ராம் நகர்": ["கோயம்புத்தூர்", "மதுரை", "சென்னை"]
    }

    # Historical District Reorganizations (Bifurcations in 2019 and 2020)
    HISTORICAL_REORGANIZATIONS: Dict[str, Dict[str, Any]] = {
        "tambaram": {
            "current_district_code": "ADM-TN-DIST-002-CHENGALPATTU",
            "historical_district_code": "ADM-TN-DIST-010-KANCHEEPURAM",
            "historical_name": "Kancheepuram",
            "current_name": "Chengalpattu",
            "split_date": "2019-11-29",
            "note": "Tambaram was historically part of Kancheepuram District prior to November 2019 reorganization."
        },
        "தாம்பரம்": {
            "current_district_code": "ADM-TN-DIST-002-CHENGALPATTU",
            "historical_district_code": "ADM-TN-DIST-010-KANCHEEPURAM",
            "historical_name": "Kancheepuram",
            "current_name": "Chengalpattu",
            "split_date": "2019-11-29",
            "note": "தாம்பரம் 2019 நவம்பருக்கு முன்பு காஞ்சிபுரம் மாவட்டத்தில் இருந்தது."
        },
        "arakkonam": {
            "current_district_code": "ADM-TN-DIST-021-RANIPET",
            "historical_district_code": "ADM-TN-DIST-035-VELLORE",
            "historical_name": "Vellore",
            "current_name": "Ranipet",
            "split_date": "2019-11-28",
            "note": "Arakkonam was historically part of Vellore District prior to November 2019 reorganization."
        },
        "அரக்கோணம்": {
            "current_district_code": "ADM-TN-DIST-021-RANIPET",
            "historical_district_code": "ADM-TN-DIST-035-VELLORE",
            "historical_name": "Vellore",
            "current_name": "Ranipet",
            "split_date": "2019-11-28",
            "note": "அரக்கோணம் 2019 நவம்பருக்கு முன்பு வேலூர் மாவட்டத்தில் இருந்தது."
        },
        "tirupathur": {
            "current_district_code": "ADM-TN-DIST-030-TIRUPATHUR",
            "historical_district_code": "ADM-TN-DIST-035-VELLORE",
            "historical_name": "Vellore",
            "current_name": "Tirupathur",
            "split_date": "2019-11-28",
            "note": "Tirupathur was bifurcated from Vellore District in November 2019."
        },
        "tenkasi": {
            "current_district_code": "ADM-TN-DIST-024-TENKASI",
            "historical_district_code": "ADM-TN-DIST-029-TIRUNELVELI",
            "historical_name": "Tirunelveli",
            "current_name": "Tenkasi",
            "split_date": "2019-11-22",
            "note": "Tenkasi was bifurcated from Tirunelveli District in November 2019."
        },
        "தென்காசி": {
            "current_district_code": "ADM-TN-DIST-024-TENKASI",
            "historical_district_code": "ADM-TN-DIST-029-TIRUNELVELI",
            "historical_name": "Tirunelveli",
            "current_name": "Tenkasi",
            "split_date": "2019-11-22",
            "note": "தென்காசி 2019 நவம்பருக்கு முன்பு திருநெல்வேலி மாவட்டத்தில் இருந்தது."
        },
        "kallakurichi": {
            "current_district_code": "ADM-TN-DIST-009-KALLAKURICHI",
            "historical_district_code": "ADM-TN-DIST-036-VILUPPURAM",
            "historical_name": "Viluppuram",
            "current_name": "Kallakurichi",
            "split_date": "2019-11-12",
            "note": "Kallakurichi was bifurcated from Viluppuram District in November 2019."
        },
        "mayiladuthurai": {
            "current_district_code": "ADM-TN-DIST-014-MAYILADUTHURAI",
            "historical_district_code": "ADM-TN-DIST-015-NAGAPATTINAM",
            "historical_name": "Nagapattinam",
            "current_name": "Mayiladuthurai",
            "split_date": "2020-12-28",
            "note": "Mayiladuthurai was bifurcated from Nagapattinam District in December 2020."
        },
        "மயிலாடுதுறை": {
            "current_district_code": "ADM-TN-DIST-014-MAYILADUTHURAI",
            "historical_district_code": "ADM-TN-DIST-015-NAGAPATTINAM",
            "historical_name": "Nagapattinam",
            "current_name": "Mayiladuthurai",
            "split_date": "2020-12-28",
            "note": "மயிலாடுதுறை 2020 டிசம்பருக்கு முன்பு நாகப்பட்டினம் மாவட்டத்தில் இருந்தது."
        }
    }

    @classmethod
    def resolve_by_code(cls, area_code: str) -> Optional[GeographicResolutionResult]:
        """Resolves known canonical area code directly."""
        code_clean = (area_code or "").strip().upper()
        if not code_clean:
            return None

        # 1. State check
        if code_clean == "ADM-TN-STATE":
            return GeographicResolutionResult(
                area_code="ADM-TN-STATE",
                area_name_en="Tamil Nadu",
                area_name_ta="தமிழ்நாடு",
                administrative_level=AdministrativeLevel.STATE,
                confidence=1.0,
                is_imprecise=True,
                warning_flag="COARSE_GEOGRAPHY",
                matched_via="EXACT_CODE"
            )

        # 2. District check
        for dist_code, (en, ta, _, _) in cls.TN_DISTRICTS.items():
            if code_clean == dist_code or code_clean == dist_code.replace("ADM-TN-DIST-", ""):
                return GeographicResolutionResult(
                    area_code=dist_code,
                    area_name_en=en,
                    area_name_ta=ta,
                    administrative_level=AdministrativeLevel.DISTRICT,
                    confidence=1.0,
                    is_imprecise=True,  # District level is coarse; ward details not assigned
                    warning_flag="COARSE_GEOGRAPHY",
                    matched_via="EXACT_CODE"
                )

        # 3. GCC Ward check
        if "WARD" in code_clean:
            m = re.search(r'WARD[-_]?(\d+)', code_clean)
            if m:
                ward_num = int(m.group(1))
                return GeographicResolutionResult(
                    area_code=f"ADM-TN-GCC-WARD-{ward_num}",
                    area_name_en=f"GCC Ward {ward_num}",
                    area_name_ta=f"சென்னை வார்டு {ward_num}",
                    administrative_level=AdministrativeLevel.WARD,
                    confidence=1.0,
                    is_imprecise=False,
                    matched_via="EXACT_CODE"
                )

        # 4. GCC Zone check
        if "ZONE" in code_clean:
            m = re.search(r'ZONE[-_]?(\d+)', code_clean)
            if m:
                zone_num = int(m.group(1))
                if zone_num in cls.GCC_ZONES:
                    z_code, en, ta = cls.GCC_ZONES[zone_num]
                    return GeographicResolutionResult(
                        area_code=z_code,
                        area_name_en=en,
                        area_name_ta=ta,
                        administrative_level=AdministrativeLevel.MUNICIPAL_CORPORATION,
                        confidence=1.0,
                        is_imprecise=False,
                        matched_via="EXACT_CODE"
                    )

        return None

    @classmethod
    def resolve_by_text(
        cls,
        district_text: Optional[str] = None,
        locality_text: Optional[str] = None,
        submission_date: Optional[datetime] = None
    ) -> GeographicResolutionResult:
        """
        Resolves administrative area by parsing district, locality, and description texts.
        Strictly guards against:
          1. Missing locations (returns State container with warning).
          2. Ambiguous homonyms without district context (avoids assuming Chennai).
          3. False ward inference from coarse descriptions.
          4. Historical boundary split resolution.
        """
        raw_combined = f"{district_text or ''} {locality_text or ''}".strip()
        lower_combined = raw_combined.lower()

        # ---------------------------------------------------------------------
        # Guard 1: Missing Location Information
        # ---------------------------------------------------------------------
        if not raw_combined or len(lower_combined) < 2:
            return GeographicResolutionResult(
                area_code="ADM-TN-STATE",
                area_name_en="Tamil Nadu",
                area_name_ta="தமிழ்நாடு",
                administrative_level=AdministrativeLevel.STATE,
                confidence=0.20,
                is_imprecise=True,
                warning_flag="MISSING_LOCATION",
                matched_via="FALLBACK_CONTAINER"
            )

        # ---------------------------------------------------------------------
        # Guard 2: Ambiguous Place Name Homonyms (Without District Context)
        # ---------------------------------------------------------------------
        for homonym, candidates in cls.AMBIGUOUS_HOMONYMS.items():
            if homonym in lower_combined:
                # Check if district context is explicitly provided
                has_explicit_district = False
                for dist_code, (en, ta, _, _) in cls.TN_DISTRICTS.items():
                    if (en.lower() in lower_combined and en.lower() not in homonym) or (ta in lower_combined and ta not in homonym):
                        has_explicit_district = True
                        break

                # Also check if explicit Ward number is specified
                has_explicit_ward = bool(re.search(r'(?:ward|வார்டு)\s*[-#:]?\s*(\d+)', lower_combined))

                if not has_explicit_district and not has_explicit_ward:
                    # STRICT RULE: Refuse to assume Chennai! Flag as ambiguous place name
                    return GeographicResolutionResult(
                        area_code="ADM-TN-STATE",
                        area_name_en="Tamil Nadu",
                        area_name_ta="தமிழ்நாடு",
                        administrative_level=AdministrativeLevel.STATE,
                        confidence=0.35,
                        is_imprecise=True,
                        warning_flag="AMBIGUOUS_PLACE_NAME",
                        matched_via="FALLBACK_CONTAINER",
                        candidate_areas=candidates
                    )

        # ---------------------------------------------------------------------
        # Guard 3: Historical Boundary Reorganizations
        # ---------------------------------------------------------------------
        for loc_key, reorg_data in cls.HISTORICAL_REORGANIZATIONS.items():
            if loc_key in lower_combined:
                curr_dist_code = reorg_data["current_district_code"]
                en, ta, _, _ = cls.TN_DISTRICTS[curr_dist_code]
                return GeographicResolutionResult(
                    area_code=curr_dist_code,
                    area_name_en=en,
                    area_name_ta=ta,
                    administrative_level=AdministrativeLevel.DISTRICT,
                    confidence=0.92,
                    is_imprecise=True,  # Coarse district container
                    warning_flag="HISTORICAL_BOUNDARY_SPLIT",
                    matched_via="HISTORICAL_CROSS_REFERENCE",
                    historical_context=reorg_data["note"]
                )

        # ---------------------------------------------------------------------
        # Step 4: Ward-Level Resolution (Only if explicitly supported by source)
        # ---------------------------------------------------------------------
        ward_match = re.search(r'(?:ward|வார்டு)\s*[-#:]?\s*(\d+)', lower_combined)
        if ward_match:
            ward_num = int(ward_match.group(1))
            return GeographicResolutionResult(
                area_code=f"ADM-TN-GCC-WARD-{ward_num}",
                area_name_en=f"GCC Ward {ward_num}",
                area_name_ta=f"சென்னை வார்டு {ward_num}",
                administrative_level=AdministrativeLevel.WARD,
                confidence=0.95,
                is_imprecise=False,
                matched_via="TEXT_EXTRACTION"
            )

        # ---------------------------------------------------------------------
        # Step 5: Zone-Level Resolution
        # ---------------------------------------------------------------------
        zone_match = re.search(r'(?:zone|மண்டலம்)\s*[-#:]?\s*(\d+)', lower_combined)
        if zone_match:
            zone_num = int(zone_match.group(1))
            if zone_num in cls.GCC_ZONES:
                z_code, en, ta = cls.GCC_ZONES[zone_num]
                return GeographicResolutionResult(
                    area_code=z_code,
                    area_name_en=en,
                    area_name_ta=ta,
                    administrative_level=AdministrativeLevel.MUNICIPAL_CORPORATION,
                    confidence=0.92,
                    is_imprecise=False,
                    matched_via="TEXT_EXTRACTION"
                )

        # ---------------------------------------------------------------------
        # Step 6: District-Level Resolution (Never infer ward!)
        # ---------------------------------------------------------------------
        for dist_code, (en, ta, _, _) in cls.TN_DISTRICTS.items():
            if en.lower() in lower_combined or ta in lower_combined:
                return GeographicResolutionResult(
                    area_code=dist_code,
                    area_name_en=en,
                    area_name_ta=ta,
                    administrative_level=AdministrativeLevel.DISTRICT,
                    confidence=0.90,
                    is_imprecise=True,  # Coarse district container
                    warning_flag="COARSE_GEOGRAPHY",
                    matched_via="BILINGUAL_NAME"
                )

        # Fallback to State container
        return GeographicResolutionResult(
            area_code="ADM-TN-STATE",
            area_name_en="Tamil Nadu",
            area_name_ta="தமிழ்நாடு",
            administrative_level=AdministrativeLevel.STATE,
            confidence=0.40,
            is_imprecise=True,
            warning_flag="COARSE_GEOGRAPHY",
            matched_via="FALLBACK_CONTAINER"
        )

    @classmethod
    def resolve_by_coordinates(cls, lat: float, lon: float) -> GeographicResolutionResult:
        """
        Resolves nearest administrative district from GPS coordinates using Haversine distance.
        """
        closest_dist_code = "ADM-TN-DIST-003-CHENNAI"
        min_distance = float('inf')

        for dist_code, (en, ta, d_lat, d_lon) in cls.TN_DISTRICTS.items():
            R = 6371.0  # km
            d_phi = math.radians(d_lat - lat)
            d_lambda = math.radians(d_lon - lon)
            a = math.sin(d_phi / 2.0)**2 + math.cos(math.radians(lat)) * math.cos(math.radians(d_lat)) * math.sin(d_lambda / 2.0)**2
            c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
            dist_km = R * c

            if dist_km < min_distance:
                min_distance = dist_km
                closest_dist_code = dist_code

        en, ta, _, _ = cls.TN_DISTRICTS[closest_dist_code]
        return GeographicResolutionResult(
            area_code=closest_dist_code,
            area_name_en=en,
            area_name_ta=ta,
            administrative_level=AdministrativeLevel.DISTRICT,
            confidence=0.85,
            is_imprecise=True,  # Coarse district container
            warning_flag="COARSE_GEOGRAPHY",
            matched_via="GPS_COORDINATE"
        )


# ---------------------------------------------------------------------------
# 2. Department Jurisdiction & Citizen's Charter SLA Engine
# ---------------------------------------------------------------------------
class CivicDepartmentResolver:
    """
    Resolves operational departmental jurisdiction, responsible local authorities,
    shared responsibilities, and statutory Citizen's Charter SLA deadlines.
    """

    SERVICE_STANDARDS: Dict[str, Dict[str, Any]] = {
        "STD-STREETLIGHT-REPAIR": {
            "department_code": "DEPT_GCC",
            "category_code": IssueCategoryEnum.STREETLIGHTS.value,
            "service_name_en": "Street Light Defect Repair / Replacement",
            "service_name_ta": "தெருவிளக்கு பழுது நீக்குதல்",
            "stipulated_time_hours": 24,
            "designated_officer": "Assistant Engineer (Electrical), GCC / Line Agency",
            "penalty_clause": "Fine of INR 50 per day of unexcused delay"
        },
        "STD-POTHOLE-RESTORE": {
            "department_code": "DEPT_GCC",
            "category_code": IssueCategoryEnum.ROADS.value,
            "service_name_en": "Pothole Patchwork and Road Restoration",
            "service_name_ta": "குண்டு குழி மற்றும் சாலை சீரமைப்பு",
            "stipulated_time_hours": 48,
            "designated_officer": "Assistant Executive Engineer (Works), GCC / Line Agency",
            "penalty_clause": "Departmental disciplinary notation"
        },
        "STD-GARBAGE-CLEARANCE": {
            "department_code": "DEPT_GCC",
            "category_code": IssueCategoryEnum.WASTE_MANAGEMENT.value,
            "service_name_en": "Overflowing Dumper Placer Bin Conservancy",
            "service_name_ta": "திடக்கழிவு அகற்றுதல் மற்றும் தூய்மை பணி",
            "stipulated_time_hours": 24,
            "designated_officer": "Sanitary Inspector / Zonal Conservancy Officer",
            "penalty_clause": "Penalty assessed to conservancy concessionaire"
        },
        "STD-DRAINAGE-OVERFLOW": {
            "department_code": "DEPT_MAWS",
            "category_code": IssueCategoryEnum.DRAINAGE.value,
            "service_name_en": "Sewer / Drainage Overflow Remediation",
            "service_name_ta": "கழிவுநீர் வழிதல் மற்றும் அடைப்பு நீக்குதல்",
            "stipulated_time_hours": 24,
            "designated_officer": "Area Engineer, CMWSSB / Municipal Commissioner",
            "penalty_clause": "Priority escalation to Superintending Engineer"
        },
        "STD-WATER-CONTAMINATION": {
            "department_code": "DEPT_MAWS",
            "category_code": IssueCategoryEnum.WATER_SUPPLY.value,
            "service_name_en": "Drinking Water Contamination / Supply Disruption",
            "service_name_ta": "குடிநீர் வழங்கல் சீரமைப்பு",
            "stipulated_time_hours": 12,
            "designated_officer": "Executive Engineer (Water Supply), CMWSSB / TWAD",
            "penalty_clause": "Immediate alternate tanker deployment"
        },
        "STD-TRANSFORMER-REPLACE": {
            "department_code": "DEPT_TANGEDCO",
            "category_code": IssueCategoryEnum.ELECTRICITY.value,
            "service_name_en": "Distribution Transformer Failure Replacement",
            "service_name_ta": "மின்மாற்றி பழுது மற்றும் மின் விநியோகம்",
            "stipulated_time_hours": 24,
            "designated_officer": "Assistant Engineer (Operation & Maintenance), TANGEDCO",
            "penalty_clause": "Statutory TNERC compensation"
        },
        "STD-PATTA-TRANSFER": {
            "department_code": "DEPT_REVENUE",
            "category_code": IssueCategoryEnum.GOVERNMENT_SERVICE_DELAYS.value,
            "service_name_en": "Online Patta Transfer (Without Subdivision)",
            "service_name_ta": "பட்டா மாறுதல் (உட்பிரிவு இல்லாதது)",
            "stipulated_time_hours": 360,  # 15 days
            "designated_officer": "Zonal Deputy Tahsildar / Revenue Inspector",
            "penalty_clause": "Right to Services Act appeal"
        }
    }

    @classmethod
    def resolve_jurisdiction(
        cls,
        category_code: str,
        area_code: Optional[str] = None,
        source_id: Optional[str] = None,
        description_text: Optional[str] = None,
        submission_date: Optional[datetime] = None
    ) -> DepartmentJurisdictionResult:
        """
        Determines line department and local authority, resolving shared and
        unclear jurisdictions where applicable.
        """
        cat_clean = category_code.lower()
        area_clean = (area_code or "").upper()
        desc_clean = (description_text or "").lower()
        is_chennai = ("GCC" in area_clean or "CHENNAI" in area_clean or source_id == "GCC_CHENNAI")

        # ---------------------------------------------------------------------
        # Shared Jurisdiction: State Highway inside Municipal Limits
        # ---------------------------------------------------------------------
        is_highway_keyword = any(kw in desc_clean for kw in ["state highway", "arterial road", "gst road", "anna salai", "bypass", "highways"])
        if cat_clean == IssueCategoryEnum.ROADS.value and is_highway_keyword and is_chennai:
            # Overlapping responsibility: Highways Department (carriageway) & GCC (drains & lighting)
            std = cls.SERVICE_STANDARDS["STD-POTHOLE-RESTORE"]
            target_date = (submission_date + timedelta(hours=48)) if submission_date else None
            return DepartmentJurisdictionResult(
                department_code="DEPT_HIGHWAYS",
                department_name_en="Highways and Minor Ports Department (Shared with GCC)",
                jurisdiction_level="STATE",
                service_standard_code="STD-POTHOLE-RESTORE",
                sla_hours=48,
                designated_officer="Divisional Engineer (Highways) & Zonal Officer (GCC)",
                target_resolution_date=target_date,
                confidence=0.80,
                jurisdiction_notes="Shared jurisdiction: Arterial highway corridor within GCC municipal boundaries.",
                candidate_departments=["DEPT_HIGHWAYS", "DEPT_GCC"],
                responsible_local_authority="Highways Department (Carriageway) & Greater Chennai Corporation (Lighting & Footpaths)",
                is_shared_responsibility=True,
                department_status="SHARED",
                review_status="AUTOMATED_VERIFIED"
            )

        # ---------------------------------------------------------------------
        # Unclear / Disputed Jurisdiction (Encroachments & Other Civic Issues)
        # ---------------------------------------------------------------------
        if cat_clean == IssueCategoryEnum.OTHER_CIVIC_ISSUES.value or "disputed" in desc_clean or "boundary dispute" in desc_clean:
            return DepartmentJurisdictionResult(
                department_code=None,
                department_name_en="Unresolved Line Department Jurisdiction",
                jurisdiction_level="UNRESOLVED",
                service_standard_code=None,
                sla_hours=72,
                designated_officer="Designated Revenue Divisional Officer / Municipal Commissioner",
                target_resolution_date=None,
                confidence=0.40,
                jurisdiction_notes="Unclear or disputed operational jurisdiction across departments.",
                candidate_departments=["DEPT_REVENUE", "DEPT_MAWS"],
                responsible_local_authority="Joint Inspection Committee (Revenue & Local Body)",
                is_shared_responsibility=True,
                department_status="UNRESOLVED",
                review_status="PENDING_HUMAN_REVIEW"
            )

        # ---------------------------------------------------------------------
        # Standard Domain Jurisdictions
        # ---------------------------------------------------------------------
        # 1. Electricity -> Statewide TANGEDCO
        if cat_clean == IssueCategoryEnum.ELECTRICITY.value:
            dept_code = "DEPT_TANGEDCO"
            dept_name = "Tamil Nadu Generation and Distribution Corporation (TANGEDCO)"
            std_key = "STD-TRANSFORMER-REPLACE"
            local_authority = "Superintending Engineer (Distribution), TANGEDCO"
            notes = "Statewide electricity infrastructure governed exclusively by TANGEDCO."

        # 2. Government Service Delays -> Revenue Department
        elif cat_clean == IssueCategoryEnum.GOVERNMENT_SERVICE_DELAYS.value:
            dept_code = "DEPT_REVENUE"
            dept_name = "Revenue and Disaster Management Department"
            std_key = "STD-PATTA-TRANSFER"
            local_authority = "District Collectorate / Taluk Tahsildar"
            notes = "Citizen services and land records governed by Revenue Administration."

        # 3. Roads / Footpaths
        elif cat_clean == IssueCategoryEnum.ROADS.value:
            if is_chennai:
                dept_code = "DEPT_GCC"
                dept_name = "Greater Chennai Corporation (Works Department)"
                std_key = "STD-POTHOLE-RESTORE"
                local_authority = "Commissioner, Greater Chennai Corporation"
                notes = "Interior and bus route municipal roads maintained by GCC."
            else:
                dept_code = "DEPT_HIGHWAYS"
                dept_name = "Highways and Minor Ports Department"
                std_key = "STD-POTHOLE-RESTORE"
                local_authority = "Divisional Engineer (Highways & Minor Ports)"
                notes = "State highways, major district roads, and municipal corridors."

        # 4. Solid Waste Management
        elif cat_clean == IssueCategoryEnum.WASTE_MANAGEMENT.value:
            if is_chennai:
                dept_code = "DEPT_GCC"
                dept_name = "Greater Chennai Corporation (Solid Waste Management)"
                std_key = "STD-GARBAGE-CLEARANCE"
                local_authority = "Zonal Officer, Greater Chennai Corporation"
                notes = "Urban local body conservancy and solid waste management."
            else:
                dept_code = "DEPT_MAWS"
                dept_name = "Municipal Administration & Water Supply Department"
                std_key = "STD-GARBAGE-CLEARANCE"
                local_authority = "Municipal Commissioner / Executive Officer"
                notes = "Local body conservancy and solid waste management."

        # 5. Streetlights
        elif cat_clean == IssueCategoryEnum.STREETLIGHTS.value:
            if is_chennai:
                dept_code = "DEPT_GCC"
                dept_name = "Greater Chennai Corporation (Electrical Department)"
                std_key = "STD-STREETLIGHT-REPAIR"
                local_authority = "Executive Engineer (Electrical), GCC"
                notes = "Street lighting assets maintained by municipal electrical wing."
            else:
                dept_code = "DEPT_MAWS"
                dept_name = "Municipal Administration & Water Supply Department"
                std_key = "STD-STREETLIGHT-REPAIR"
                local_authority = "Municipal Commissioner / Block Development Officer"
                notes = "Municipal and rural street lighting maintenance."

        # 6. Water Supply
        elif cat_clean == IssueCategoryEnum.WATER_SUPPLY.value:
            if is_chennai:
                dept_code = "DEPT_MAWS"
                dept_name = "Chennai Metropolitan Water Supply and Sewerage Board (CMWSSB)"
                std_key = "STD-WATER-CONTAMINATION"
                local_authority = "Managing Director, CMWSSB (Metro Water)"
                notes = "Chennai metropolitan drinking water supply managed by CMWSSB under MAWS."
            else:
                dept_code = "DEPT_MAWS"
                dept_name = "Tamil Nadu Water Supply and Drainage Board (TWAD Board)"
                std_key = "STD-WATER-CONTAMINATION"
                local_authority = "Managing Director, TWAD Board"
                notes = "Tamil Nadu statewide water supply managed by TWAD Board under MAWS."

        # 7. Drainage & Sewerage
        elif cat_clean == IssueCategoryEnum.DRAINAGE.value:
            dept_code = "DEPT_MAWS"
            dept_name = "Municipal Administration and Water Supply Department (Drainage Wing)"
            std_key = "STD-DRAINAGE-OVERFLOW"
            local_authority = "CMWSSB Area Engineer (Chennai) / Municipal Commissioner"
            notes = "Stormwater drains and underground sewerage network."

        # 8. Healthcare Facilities
        elif cat_clean == IssueCategoryEnum.HEALTHCARE_ACCESS.value:
            dept_code = "DEPT_HEALTH"
            dept_name = "Health and Family Welfare Department"
            std_key = None
            local_authority = "Directorate of Public Health and Preventive Medicine (DPH)"
            notes = "Primary Health Centres, taluk hospitals, and government medical facilities."

        # 9. School Infrastructure
        elif cat_clean == IssueCategoryEnum.EDUCATION_INFRASTRUCTURE.value:
            dept_code = "DEPT_EDUCATION"
            dept_name = "School Education Department"
            std_key = None
            local_authority = "Chief Educational Officer (CEO) & PWD (Buildings)"
            notes = "Government school buildings and educational infrastructure."

        # Fallback
        else:
            dept_code = "DEPT_GCC" if is_chennai else "DEPT_MAWS"
            dept_name = "Greater Chennai Corporation" if is_chennai else "Municipal Administration Department"
            std_key = None
            local_authority = "Municipal Local Body Commissioner"
            notes = "General municipal line agency jurisdiction."

        # Retrieve standard SLA
        std = cls.SERVICE_STANDARDS.get(std_key) if std_key else None
        sla_hours = std["stipulated_time_hours"] if std else 72
        officer = std["designated_officer"] if std else "Assistant Engineer / Zonal Officer"

        target_date = None
        if submission_date:
            target_date = submission_date + timedelta(hours=sla_hours)

        return DepartmentJurisdictionResult(
            department_code=dept_code,
            department_name_en=dept_name,
            jurisdiction_level="MUNICIPAL_CORPORATION" if "GCC" in dept_code else "STATE",
            service_standard_code=std_key,
            sla_hours=sla_hours,
            designated_officer=officer,
            target_resolution_date=target_date,
            confidence=0.95,
            jurisdiction_notes=notes,
            candidate_departments=[dept_code],
            responsible_local_authority=local_authority,
            is_shared_responsibility=False,
            department_status="RESOLVED",
            review_status="AUTOMATED_VERIFIED"
        )


# ---------------------------------------------------------------------------
# 3. Unified Integration Service
# ---------------------------------------------------------------------------
class CivicMappingIntegrationService:
    """
    Applies geographic resolution and department jurisdiction to GrievanceRecord
    and CivicIssue database entities, emitting canonical CivicMappingRecords.
    """

    @classmethod
    def map_and_enrich_issue(
        cls,
        db_session: Session,
        civic_issue: CivicIssue,
        grievance: Optional[GrievanceRecord] = None
    ) -> Tuple[GeographicResolutionResult, DepartmentJurisdictionResult, CivicMappingRecord]:
        """
        Enriches a CivicIssue with resolved administrative area, department,
        and statutory Citizen's Charter SLA, returning a canonical CivicMappingRecord.
        """
        # 1. Geographic Resolution
        raw_area = grievance.administrative_area_id if grievance else None
        geo_res = None

        if raw_area:
            geo_res = CivicGeographicMapper.resolve_by_code(raw_area)

        if not geo_res and civic_issue.latitude and civic_issue.longitude:
            geo_res = CivicGeographicMapper.resolve_by_coordinates(civic_issue.latitude, civic_issue.longitude)

        if not geo_res:
            text_desc = grievance.description_or_permitted_summary if grievance else civic_issue.description
            sub_dt = grievance.submission_date if grievance else civic_issue.reported_date
            geo_res = CivicGeographicMapper.resolve_by_text(locality_text=text_desc, submission_date=sub_dt)

        # Sync administrative area on CivicIssue
        area_entity = db_session.query(AdministrativeArea).filter_by(area_code=geo_res.area_code).first()
        if area_entity:
            civic_issue.administrative_area_id = area_entity.id

        # Flag data quality issues if applicable
        if geo_res.is_imprecise and geo_res.warning_flag:
            dq_issue = DataQualityIssue(
                civic_issue_id=civic_issue.id,
                severity=DataQualitySeverity.WARNING,
                issue_type=geo_res.warning_flag,
                description=(
                    f"Geographic mapping notice: '{geo_res.warning_flag}' for area '{geo_res.area_code}' "
                    f"({geo_res.administrative_level.value}). Context: {geo_res.historical_context or 'Coarse mapping'}."
                )
            )
            db_session.add(dq_issue)

        # 2. Department & SLA Resolution
        cat_val = civic_issue.category.code.value if (civic_issue.category and hasattr(civic_issue.category.code, 'value')) else (civic_issue.category.code if civic_issue.category else IssueCategoryEnum.OTHER_CIVIC_ISSUES.value)
        source_id = grievance.source_id if grievance else None
        desc_text = grievance.description_or_permitted_summary if grievance else civic_issue.description
        sub_dt = civic_issue.reported_date

        dept_res = CivicDepartmentResolver.resolve_jurisdiction(
            category_code=cat_val,
            area_code=geo_res.area_code,
            source_id=source_id,
            description_text=desc_text,
            submission_date=sub_dt
        )

        if dept_res.department_code:
            dept_entity = db_session.query(CivicDepartment).filter_by(code=dept_res.department_code).first()
            if dept_entity:
                civic_issue.department_id = dept_entity.id

        # Set target resolution date from Citizen's Charter SLA
        if dept_res.target_resolution_date:
            civic_issue.target_resolution_date = dept_res.target_resolution_date

        # 3. Create Canonical CivicMappingRecord
        overall_confidence = min(geo_res.confidence, dept_res.confidence)
        review_status = "AUTOMATED_VERIFIED"
        if geo_res.warning_flag in ("MISSING_LOCATION", "AMBIGUOUS_PLACE_NAME") or dept_res.department_status == "UNRESOLVED" or overall_confidence < 0.70:
            review_status = "PENDING_HUMAN_REVIEW"

        mapping_record = CivicMappingRecord(
            issue_id=civic_issue.id,
            administrative_area_id=geo_res.area_code,
            geographic_level=geo_res.administrative_level.value,
            department_id=dept_res.department_code,
            mapping_method=geo_res.matched_via,
            source_reference=grievance.source_record_reference if grievance else None,
            confidence=overall_confidence,
            review_status=review_status,
            candidate_departments=dept_res.candidate_departments,
            responsible_local_authority=dept_res.responsible_local_authority,
            is_shared_responsibility=dept_res.is_shared_responsibility,
            warning_flag=geo_res.warning_flag,
            historical_context=geo_res.historical_context
        )

        return geo_res, dept_res, mapping_record
