"""
Civic Geographic Mapping & Department Jurisdiction Service (CIVICLENS TN - Phase 8.5)
=====================================================================================
Resolves:
  1. Multilingual Administrative Area Mapping (State, 38 Districts, Municipal
     Corporations, Zones, Wards, Assembly Constituencies).
  2. Spatial Coordinates to Administrative Area Bounding Box / Nearest Area.
  3. Department Jurisdiction Resolution (Municipal vs State Line Departments,
     resolving overlapping jurisdictions e.g. Highways vs Municipalities, CMWSSB vs TWAD).
  4. Citizen's Charter SLA Mapping (Stipulated turnaround times, target resolution dates).
  5. Imprecise / Ambiguous Geolocation Quality Auditing (Flags COARSE_GEOGRAPHY).
"""

import math
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
    warning_flag: Optional[str] = None  # e.g. COARSE_GEOGRAPHY, UNRESOLVED_WARD
    matched_via: str = "EXACT_CODE"     # EXACT_CODE, BILINGUAL_NAME, GPS_COORDINATE, TEXT_EXTRACTION


@dataclass
class DepartmentJurisdictionResult:
    """Resolved department jurisdiction and Citizen's Charter SLA."""
    department_code: str
    department_name_en: str
    jurisdiction_level: str
    service_standard_code: Optional[str] = None
    sla_hours: int = 72
    designated_officer: str = "Assistant Engineer / Zonal Officer"
    target_resolution_date: Optional[datetime] = None
    confidence: float = 1.0
    jurisdiction_notes: str = ""


# ---------------------------------------------------------------------------
# 1. Geographic Mapping Engine
# ---------------------------------------------------------------------------
class CivicGeographicMapper:
    """
    Maps heterogeneous text, bilingual names, and GPS coordinates to
    canonical AdministrativeArea records across Tamil Nadu.
    """

    # 38 Tamil Nadu Districts directory (English & Tamil)
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

    @classmethod
    def resolve_by_code(cls, area_code: str) -> Optional[GeographicResolutionResult]:
        """Resolves known area code directly."""
        code_clean = (area_code or "").strip().upper()

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
                    is_imprecise=True,  # District level is coarse for municipal issues
                    warning_flag="COARSE_GEOGRAPHY",
                    matched_via="EXACT_CODE"
                )

        # 3. GCC Ward check
        if "WARD" in code_clean:
            import re
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
            import re
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
    def resolve_by_text(cls, district_text: Optional[str] = None, locality_text: Optional[str] = None) -> GeographicResolutionResult:
        """
        Resolves administrative area by matching district and locality strings.
        """
        combined = f"{district_text or ''} {locality_text or ''}".strip().lower()

        # Check for Ward specification in text
        import re
        ward_match = re.search(r'(?:ward|வார்டு)\s*[-#:]?\s*(\d+)', combined)
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

        # Check for GCC Zone specification in text
        zone_match = re.search(r'(?:zone|மண்டலம்)\s*[-#:]?\s*(\d+)', combined)
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

        # Match Districts
        for dist_code, (en, ta, _, _) in cls.TN_DISTRICTS.items():
            if en.lower() in combined or ta in combined:
                return GeographicResolutionResult(
                    area_code=dist_code,
                    area_name_en=en,
                    area_name_ta=ta,
                    administrative_level=AdministrativeLevel.DISTRICT,
                    confidence=0.90,
                    is_imprecise=True,
                    warning_flag="COARSE_GEOGRAPHY",
                    matched_via="BILINGUAL_NAME"
                )

        # Fallback to State container
        return GeographicResolutionResult(
            area_code="ADM-TN-STATE",
            area_name_en="Tamil Nadu",
            area_name_ta="தமிழ்நாடு",
            administrative_level=AdministrativeLevel.STATE,
            confidence=0.50,
            is_imprecise=True,
            warning_flag="COARSE_GEOGRAPHY",
            matched_via="FALLBACK"
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
    Resolves operational departmental jurisdiction, Citizen's Charter service standards,
    and statutory SLA deadlines across Tamil Nadu.
    """

    # Citizen's Charter Statutory SLAs
    SERVICE_STANDARDS: Dict[str, Dict[str, Any]] = {
        "STD-STREETLIGHT-REPAIR": {
            "department_code": "DEPT_GCC",
            "category_code": IssueCategoryEnum.STREETLIGHTS.value,
            "service_name_en": "Street Light Defect Repair / Replacement",
            "service_name_ta": "தெருவிளக்கு பழுது நீக்குதல்",
            "stipulated_time_hours": 24,
            "designated_officer": "Assistant Engineer (Electrical), GCC / TANGEDCO",
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
        submission_date: Optional[datetime] = None
    ) -> DepartmentJurisdictionResult:
        """
        Determines the appropriate line department or local body,
        resolves overlapping jurisdictions, and assigns Citizen's Charter SLA.
        """
        cat_clean = category_code.lower()
        area_clean = (area_code or "").upper()
        is_chennai = ("GCC" in area_clean or "CHENNAI" in area_clean or source_id == "GCC_CHENNAI")

        # ---------------------------------------------------------------------
        # Jurisdiction Routing Rules
        # ---------------------------------------------------------------------
        # Rule 1: Electricity -> Always TANGEDCO statewide
        if cat_clean == IssueCategoryEnum.ELECTRICITY.value:
            dept_code = "DEPT_TANGEDCO"
            dept_name = "Tamil Nadu Generation and Distribution Corporation (TANGEDCO)"
            std_key = "STD-TRANSFORMER-REPLACE"
            notes = "Statewide electricity infrastructure governed exclusively by TANGEDCO."

        # Rule 2: Government Service Delays (Patta, Pension, Certificates) -> Revenue Department
        elif cat_clean == IssueCategoryEnum.GOVERNMENT_SERVICE_DELAYS.value:
            dept_code = "DEPT_REVENUE"
            dept_name = "Revenue and Disaster Management Department"
            std_key = "STD-PATTA-TRANSFER"
            notes = "Citizen services and land records governed by Revenue Administration."

        # Rule 3: Roads / Footpaths
        elif cat_clean == IssueCategoryEnum.ROADS.value:
            if is_chennai:
                dept_code = "DEPT_GCC"
                dept_name = "Greater Chennai Corporation (Works Department)"
                std_key = "STD-POTHOLE-RESTORE"
                notes = "Municipal corporation roads maintained by GCC Bus Route Roads / Interior Roads division."
            else:
                dept_code = "DEPT_HIGHWAYS"
                dept_name = "Highways and Minor Ports Department"
                std_key = "STD-POTHOLE-RESTORE"
                notes = "State highways, major district roads, and municipal corridors."

        # Rule 4: Solid Waste Management
        elif cat_clean == IssueCategoryEnum.WASTE_MANAGEMENT.value:
            dept_code = "DEPT_GCC" if is_chennai else "DEPT_MAWS"
            dept_name = "Greater Chennai Corporation (Solid Waste Management)" if is_chennai else "Municipal Administration & Water Supply Department"
            std_key = "STD-GARBAGE-CLEARANCE"
            notes = "Local body conservancy and solid waste management."

        # Rule 5: Streetlights
        elif cat_clean == IssueCategoryEnum.STREETLIGHTS.value:
            dept_code = "DEPT_GCC" if is_chennai else "DEPT_MAWS"
            dept_name = "Greater Chennai Corporation (Electrical Department)" if is_chennai else "Municipal Administration & Water Supply Department"
            std_key = "STD-STREETLIGHT-REPAIR"
            notes = "Street lighting assets maintained by municipal electrical wing."

        # Rule 6: Water Supply
        elif cat_clean == IssueCategoryEnum.WATER_SUPPLY.value:
            if is_chennai:
                dept_code = "DEPT_MAWS"
                dept_name = "Chennai Metropolitan Water Supply and Sewerage Board (CMWSSB)"
                std_key = "STD-WATER-CONTAMINATION"
                notes = "Chennai metropolitan drinking water supply managed by CMWSSB under MAWS."
            else:
                dept_code = "DEPT_MAWS"
                dept_name = "Tamil Nadu Water Supply and Drainage Board (TWAD Board)"
                std_key = "STD-WATER-CONTAMINATION"
                notes = "Tamil Nadu statewide water supply managed by TWAD Board under MAWS."

        # Rule 7: Drainage & Sewerage
        elif cat_clean == IssueCategoryEnum.DRAINAGE.value:
            dept_code = "DEPT_MAWS"
            dept_name = "Municipal Administration and Water Supply Department (Drainage Wing)"
            std_key = "STD-DRAINAGE-OVERFLOW"
            notes = "Stormwater drains and underground sewerage network."

        # Rule 8: Healthcare Facilities
        elif cat_clean == IssueCategoryEnum.HEALTHCARE_ACCESS.value:
            dept_code = "DEPT_HEALTH"
            dept_name = "Health and Family Welfare Department"
            std_key = None
            notes = "Primary Health Centres, taluk hospitals, and government medical facilities."

        # Rule 9: School Infrastructure
        elif cat_clean == IssueCategoryEnum.EDUCATION_INFRASTRUCTURE.value:
            dept_code = "DEPT_EDUCATION"
            dept_name = "School Education Department"
            std_key = None
            notes = "Government school buildings and educational infrastructure."

        # Default fallback
        else:
            dept_code = "DEPT_GCC" if is_chennai else "DEPT_MAWS"
            dept_name = "Greater Chennai Corporation" if is_chennai else "Municipal Administration Department"
            std_key = None
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
            jurisdiction_notes=notes
        )


# ---------------------------------------------------------------------------
# 3. Unified Integration Service
# ---------------------------------------------------------------------------
class CivicMappingIntegrationService:
    """
    Applies geographic resolution and department jurisdiction to GrievanceRecord
    and CivicIssue database entities.
    """

    @classmethod
    def map_and_enrich_issue(
        cls,
        db_session: Session,
        civic_issue: CivicIssue,
        grievance: Optional[GrievanceRecord] = None
    ) -> Tuple[GeographicResolutionResult, DepartmentJurisdictionResult]:
        """
        Enriches a CivicIssue with resolved administrative area, department,
        and statutory Citizen's Charter SLA.
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
            geo_res = CivicGeographicMapper.resolve_by_text(locality_text=text_desc)

        # Sync administrative area on CivicIssue
        area_entity = db_session.query(AdministrativeArea).filter_by(area_code=geo_res.area_code).first()
        if area_entity:
            civic_issue.administrative_area_id = area_entity.id

        # Flag coarse geography data quality issue if applicable
        if geo_res.is_imprecise and geo_res.warning_flag == "COARSE_GEOGRAPHY":
            dq_issue = DataQualityIssue(
                civic_issue_id=civic_issue.id,
                severity=DataQualitySeverity.WARNING,
                issue_type="COARSE_GEOGRAPHY",
                description=(
                    f"Civic issue mapped to coarse administrative container '{geo_res.area_code}' "
                    f"({geo_res.administrative_level.value}) without ward-level granularity."
                )
            )
            db_session.add(dq_issue)

        # 2. Department & SLA Resolution
        cat_val = civic_issue.category.code.value if (civic_issue.category and hasattr(civic_issue.category.code, 'value')) else (civic_issue.category.code if civic_issue.category else IssueCategoryEnum.OTHER_CIVIC_ISSUES.value)
        source_id = grievance.source_id if grievance else None
        sub_dt = civic_issue.reported_date

        dept_res = CivicDepartmentResolver.resolve_jurisdiction(
            category_code=cat_val,
            area_code=geo_res.area_code,
            source_id=source_id,
            submission_date=sub_dt
        )

        dept_entity = db_session.query(CivicDepartment).filter_by(code=dept_res.department_code).first()
        if dept_entity:
            civic_issue.department_id = dept_entity.id

        # Set target resolution date from Citizen's Charter SLA
        if dept_res.target_resolution_date:
            civic_issue.target_resolution_date = dept_res.target_resolution_date

        return geo_res, dept_res
