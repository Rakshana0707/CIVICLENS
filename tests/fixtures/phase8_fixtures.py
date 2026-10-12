"""
Phase 8 — Synthetic Test Fixtures for Public Grievance & Civic Issue Intelligence.

Provides isolated mock records explicitly marked with `is_test_fixture = True`.
Covers:
- 14 Standard Civic Categories (bilingual Tamil & English)
- Government Departments & Municipal Agencies
- Administrative Areas (Districts, Taluks, Corporations, Wards)
- Citizen's Charter Service Standards (SLAs)
- Civic Issues (Open, In Progress, Verified Resolved, Disputed)
- Grievance Records with PII test samples for redaction verification
- Response Records & Action Taken Reports
- Resolution Evidence Artifacts
- Public Works & Capital Maintenance Projects
- Source Documents (Gazettes, Council Minutes, Bulletins)
- Statistical Issue Metrics
- Data Quality Issue Audit Records
"""

from typing import Dict, Any, List
from backend.models.civic_issue import IssueCategoryEnum

IS_TEST_FIXTURE = True
FIXTURE_VERSION = "8.0-test"

# ---------------------------------------------------------------------------
# 1. Categories Fixtures (All 14 standard civic categories)
# ---------------------------------------------------------------------------
MOCK_CATEGORIES: List[Dict[str, Any]] = [
    {
        "code": "roads",
        "name_en": "Roads & Footpaths",
        "name_ta": "சாலைகள் மற்றும் நடைபாதைகள்",
        "default_department_code": "DEPT_HIGHWAYS",
        "keywords_en": ["pothole", "tar road", "damaged road", "crater", "footpath", "speed breaker"],
        "keywords_ta": ["சாலை", "தார் சாலை", "குண்டு குழி", "நடைபாதை", "வேகத்தடை"],
        "priority_weight": 1.2
    },
    {
        "code": "water_supply",
        "name_en": "Drinking Water Supply",
        "name_ta": "குடிநீர் வழங்கல்",
        "default_department_code": "DEPT_MAWS",
        "keywords_en": ["drinking water", "pipe burst", "water shortage", "contaminated water", "tanker"],
        "keywords_ta": ["குடிநீர்", "குழாய் உடைப்பு", "தண்ணீர் தட்டுப்பாடு", "கழிவுநீர் கலந்த குடிநீர்"],
        "priority_weight": 1.5
    },
    {
        "code": "drainage",
        "name_en": "Drainage & Sewerage",
        "name_ta": "பாதாள சாக்கடை & மழைநீர் வடிகால்",
        "default_department_code": "DEPT_MAWS",
        "keywords_en": ["drainage", "sewage overflow", "stormwater drain", "clogged manhole"],
        "keywords_ta": ["கழிவுநீர்", "சாக்கடை", "மழைநீர் வடிகால்", "பாதாள சாக்கடை அடைப்பு"],
        "priority_weight": 1.4
    },
    {
        "code": "sanitation",
        "name_en": "Public Sanitation & Toilets",
        "name_ta": "பொது சுகாதாரம் & கழிப்பறைகள்",
        "default_department_code": "DEPT_HEALTH",
        "keywords_en": ["public toilet", "urinal", "stench", "unhygienic", "fogging"],
        "keywords_ta": ["பொது கழிப்பறை", "சுகாதார சீர்கேடு", "கொசு மருந்து அடித்தல்"],
        "priority_weight": 1.1
    },
    {
        "code": "waste_management",
        "name_en": "Solid Waste & Garbage Collection",
        "name_ta": "திடக்கழிவு & குப்பை அகற்றம்",
        "default_department_code": "DEPT_MAWS",
        "keywords_en": ["garbage", "trash dump", "waste collection", "overflowing bin", "dumper placer"],
        "keywords_ta": ["குப்பை", "குப்பைக் கூளம்", "குப்பைத் தொட்டி", "குப்பை அள்ளாமை"],
        "priority_weight": 1.3
    },
    {
        "code": "streetlights",
        "name_en": "Street Lighting",
        "name_ta": "தெருவிளக்குகள்",
        "default_department_code": "DEPT_MAWS",
        "keywords_en": ["street light", "lamp post", "dark street", "flickering light", "LED"],
        "keywords_ta": ["தெருவிளக்கு", "எரியாத விளக்கு", "இருள் சூழ்ந்த தெரு", "விளக்கு கம்பம்"],
        "priority_weight": 1.0
    },
    {
        "code": "public_transport",
        "name_en": "Public Transport & Bus Shelters",
        "name_ta": "பொதுப் போக்குவரத்து",
        "default_department_code": "DEPT_TRANSPORT",
        "keywords_en": ["bus shelter", "bus frequency", "MTC bus", "depot", "bus route"],
        "keywords_ta": ["பேருந்து", "பேருந்து நிறுத்தம்", "நிழற்குடை", "பேருந்து சேவை குறைவு"],
        "priority_weight": 1.0
    },
    {
        "code": "healthcare_access",
        "name_en": "Healthcare Facilities & PHCs",
        "name_ta": "மருத்துவமனை & ஆரம்ப சுகாதார வசதிகள்",
        "default_department_code": "DEPT_HEALTH",
        "keywords_en": ["PHC", "government hospital", "medicine shortage", "doctor absent", "ambulance"],
        "keywords_ta": ["ஆரம்ப சுகாதார நிலையம்", "அரசு மருத்துவமனை", "மருந்து தட்டுப்பாடு"],
        "priority_weight": 1.4
    },
    {
        "code": "education_infrastructure",
        "name_en": "Government School Infrastructure",
        "name_ta": "பள்ளி கல்வி உள்கட்டமைப்பு",
        "default_department_code": "DEPT_SCHOOL_EDU",
        "keywords_en": ["school building", "classroom roof", "school toilet", "drinking water in school"],
        "keywords_ta": ["அரசு பள்ளி", "வகுப்பறை சேதம்", "பள்ளி கழிப்பறை", "கூரை சேதம்"],
        "priority_weight": 1.2
    },
    {
        "code": "electricity",
        "name_en": "Power Supply, Transformers & Poles",
        "name_ta": "மின்சார விநியோகம் & மின்மாற்றிகள்",
        "default_department_code": "DEPT_TANGEDCO",
        "keywords_en": ["power cut", "transformer burst", "low voltage", "snapped wire", "electric pole"],
        "keywords_ta": ["மின்தடை", "மின்மாற்றி வெடிப்பு", "குறைந்த மின்னழுத்தம்", "அறுந்து விழுந்த மின்கம்பி"],
        "priority_weight": 1.3
    },
    {
        "code": "public_safety_infrastructure",
        "name_en": "Public Safety Infrastructure",
        "name_ta": "பொதுப் பாதுகாப்பு உள்கட்டமைப்பு",
        "default_department_code": "DEPT_POLICE",
        "keywords_en": ["traffic light", "CCTV", "stray dog menace", "cattle menace", "blind corner"],
        "keywords_ta": ["போக்குவரத்து சிக்னல்", "தெருநாய்கள் தொல்லை", "கண்காணிப்பு கேமரா"],
        "priority_weight": 1.1
    },
    {
        "code": "environmental_concerns",
        "name_en": "Pollution, Lakes & Waterbodies",
        "name_ta": "சுற்றுச்சூழல் & நீர்நிலைகள்",
        "default_department_code": "DEPT_ENV_FOREST",
        "keywords_en": ["lake encroachment", "waterbody pollution", "chemical discharge", "tree felling"],
        "keywords_ta": ["ஏரி ஆக்கிரமிப்பு", "நீர்நிலை மாசுபாடு", "ரசாயன கழிவு", "மரம் வெட்டுதல்"],
        "priority_weight": 1.2
    },
    {
        "code": "government_service_delays",
        "name_en": "Delays in Certificates & Welfare",
        "name_ta": "அரசு சேவை தாமதங்கள்",
        "default_department_code": "DEPT_REVENUE",
        "keywords_en": ["patta delay", "ration card delay", "pension pending", "community certificate"],
        "keywords_ta": ["பட்டா மாற்றம் தாமதம்", "ரேஷன் அட்டை", "முதியோர் உதவித்தொகை வரவில்லை"],
        "priority_weight": 1.1
    },
    {
        "code": "other_documented_civic_issues",
        "name_en": "Other Documented Civic Issues",
        "name_ta": "பிற ஆவணப்படுத்தப்பட்ட குடிமைப் பிரச்சனைகள்",
        "default_department_code": "DEPT_REVENUE",
        "keywords_en": ["public nuisance", "building violation", "encroachment"],
        "keywords_ta": ["பொது தொல்லை", "ஆக்கிரமிப்பு", "விதிமீறல்"],
        "priority_weight": 1.0
    }
]

# ---------------------------------------------------------------------------
# 2. Departments Fixtures
# ---------------------------------------------------------------------------
MOCK_DEPARTMENTS: List[Dict[str, Any]] = [
    {
        "code": "DEPT_MAWS",
        "name_en": "Municipal Administration and Water Supply Department",
        "name_ta": "நகராட்சி நிர்வாகம் மற்றும் குடிநீர் வழங்கல் துறை",
        "portal_id": "35665000000010772",
        "jurisdiction_level": "STATE",
        "contact_email_public": "maws@tn.gov.in",
        "helpline_number": "1100"
    },
    {
        "code": "DEPT_HIGHWAYS",
        "name_en": "Highways and Minor Ports Department",
        "name_ta": "நெடுஞ்சாலைகள் மற்றும் சிறு துறைமுகங்கள் துறை",
        "portal_id": "356650000000138447",
        "jurisdiction_level": "STATE",
        "contact_email_public": "highways@tn.gov.in",
        "helpline_number": "1800-425-4422"
    },
    {
        "code": "DEPT_TANGEDCO",
        "name_en": "Tamil Nadu Generation and Distribution Corporation (TANGEDCO)",
        "name_ta": "தமிழ்நாடு மின் உற்பத்தி மற்றும் பகிர்மானக் கழகம்",
        "portal_id": "356650000000147330",
        "jurisdiction_level": "STATE",
        "contact_email_public": "tangedco@tn.gov.in",
        "helpline_number": "94987 94987"
    },
    {
        "code": "DEPT_HEALTH",
        "name_en": "Health and Family Welfare Department",
        "name_ta": "மக்கள் நல்வாழ்வு மற்றும் குடும்ப நலத்துறை",
        "portal_id": "356650000000187825",
        "jurisdiction_level": "STATE",
        "contact_email_public": "health@tn.gov.in",
        "helpline_number": "104"
    },
    {
        "code": "DEPT_GCC",
        "name_en": "Greater Chennai Corporation",
        "name_ta": "பெருநகர சென்னை மாநகராட்சி",
        "portal_id": "3566500000000010772",
        "jurisdiction_level": "MUNICIPAL_CORPORATION",
        "contact_email_public": "commissioner@chennaicorporation.gov.in",
        "helpline_number": "1913"
    }
]

# ---------------------------------------------------------------------------
# 3. Administrative Areas Fixtures
# ---------------------------------------------------------------------------
MOCK_AREAS: List[Dict[str, Any]] = [
    {
        "area_code": "ADM-TN-STATE",
        "name_en": "Tamil Nadu",
        "name_ta": "தமிழ்நாடு",
        "administrative_level": "STATE",
        "parent_code": None,
        "lgd_code": "33",
        "latitude": 11.1271,
        "longitude": 78.6569,
        "population": 72147030
    },
    {
        "area_code": "ADM-TN-DIST-013-CHENNAI",
        "name_en": "Chennai District",
        "name_ta": "சென்னை மாவட்டம்",
        "administrative_level": "DISTRICT",
        "parent_code": "ADM-TN-STATE",
        "lgd_code": "603",
        "latitude": 13.0827,
        "longitude": 80.2707,
        "population": 7088403
    },
    {
        "area_code": "ADM-TN-DIST-024-MADURAI",
        "name_en": "Madurai District",
        "name_ta": "மதுரை மாவட்டம்",
        "administrative_level": "DISTRICT",
        "parent_code": "ADM-TN-STATE",
        "lgd_code": "622",
        "latitude": 9.9252,
        "longitude": 78.1198,
        "population": 3038252
    },
    {
        "area_code": "ADM-TN-GCC-ZONE-13-ADYAR",
        "name_en": "Zone 13 - Adyar",
        "name_ta": "மண்டலம் 13 - அடையாறு",
        "administrative_level": "MUNICIPAL_CORPORATION",
        "parent_code": "ADM-TN-DIST-013-CHENNAI",
        "lgd_code": "Z13-GCC",
        "latitude": 13.0012,
        "longitude": 80.2565,
        "population": 450000
    },
    {
        "area_code": "ADM-TN-GCC-WARD-174",
        "name_en": "Ward 174 (Besant Nagar / Adyar)",
        "name_ta": "வார்டு 174 (பெசன்ட் நகர்)",
        "administrative_level": "WARD",
        "parent_code": "ADM-TN-GCC-ZONE-13-ADYAR",
        "lgd_code": "W174-GCC",
        "latitude": 13.0002,
        "longitude": 80.2668,
        "population": 38000
    }
]

# ---------------------------------------------------------------------------
# 4. Service Standards (SLAs) Fixtures
# ---------------------------------------------------------------------------
MOCK_SERVICE_STANDARDS: List[Dict[str, Any]] = [
    {
        "standard_code": "SLA-MAWS-POTHOLE-48H",
        "department_code": "DEPT_MAWS",
        "category_code": "roads",
        "service_name_en": "Repair of Potholes on Municipal Roads",
        "service_name_ta": "நகராட்சி சாலைகளில் உள்ள குழிகளை சரிசெய்தல்",
        "stipulated_time_hours": 48,
        "designated_officer": "Assistant Executive Engineer (Roads)",
        "appellate_authority": "Superintending Engineer",
        "penalty_clause": "Internal disciplinary review if pendency exceeds 7 days without justification."
    },
    {
        "standard_code": "SLA-MAWS-WATERLEAK-24H",
        "department_code": "DEPT_MAWS",
        "category_code": "water_supply",
        "service_name_en": "Attending Drinking Water Pipeline Burst",
        "service_name_ta": "குடிநீர் குழாய் உடைப்பு சீரமைப்பு",
        "stipulated_time_hours": 24,
        "designated_officer": "Assistant Engineer (TWAD/CMWSSB)",
        "appellate_authority": "Executive Engineer",
        "penalty_clause": "Priority emergency escalation."
    },
    {
        "standard_code": "SLA-TNEB-TRANSFORMER-24H",
        "department_code": "DEPT_TANGEDCO",
        "category_code": "electricity",
        "service_name_en": "Replacement of Burnt Distribution Transformer (Urban)",
        "service_name_ta": "பழுதடைந்த மின்மாற்றியை மாற்றுதல் (நகர்ப்புறம்)",
        "stipulated_time_hours": 24,
        "designated_officer": "Assistant Engineer (Distribution)",
        "appellate_authority": "Executive Engineer (Operations)",
        "penalty_clause": "Compensation of ₹100 per day of delayed restoration per TNERC regulations."
    }
]

# ---------------------------------------------------------------------------
# 5. Grievance Records with Raw Text (Testing PII Scrubbing)
# ---------------------------------------------------------------------------
MOCK_RAW_GRIEVANCES_FOR_PII: List[Dict[str, Any]] = [
    {
        "raw_text": "I Thiru K. Murugesan from Door No. 42/1, 2nd Main Road, Besant Nagar submit that our street light is broken. Call me at 9840123456 or email murugan.k@gmail.com. Aadhaar: 1234 5678 9012.",
        "expected_sanitized": "I [CITIZEN] from [ADDRESS REDACTED], 2nd Main Road, Besant Nagar submit that our street light is broken. Call me at [PHONE REDACTED] or email [EMAIL REDACTED]. Aadhaar: [ID REDACTED]."
    },
    {
        "raw_text": "Complaint from Tmt Lakshmi, D.No. 15, North Car Street, Madurai. Electric wire snapped near house. Contact 044-24567890 or 8765432109.",
        "expected_sanitized": "Complaint from [CITIZEN], [ADDRESS REDACTED], North Car Street, Madurai. Electric wire snapped near house. Contact [PHONE REDACTED] or [PHONE REDACTED]."
    }
]

# ---------------------------------------------------------------------------
# 6. Civic Issues Fixtures
# ---------------------------------------------------------------------------
MOCK_CIVIC_ISSUES: List[Dict[str, Any]] = [
    {
        "issue_code": "CIV-FIX-001-POTHOLE-ADYAR",
        "title": "Severe pothole cluster on 2nd Avenue Besant Nagar",
        "title_ta": "பெசன்ட் நகர் 2வது அவென்யூவில் தொடர் சாலை பள்ளங்கள்",
        "description": "Multiple large potholes causing accidents near bus stop on 2nd Avenue Besant Nagar.",
        "category_code": "roads",
        "department_code": "DEPT_GCC",
        "area_code": "ADM-TN-GCC-WARD-174",
        "status": "OPEN",
        "severity": "HIGH",
        "latitude": 13.0015,
        "longitude": 80.2672,
        "reported_date": "2024-03-01T10:00:00Z",
        "target_resolution_date": "2024-03-03T10:00:00Z",
        "actual_resolution_date": None,
        "repeat_count": 3,
        "resolution_verification_status": "PENDING_VERIFICATION",
        "is_test_fixture": True
    },
    {
        "issue_code": "CIV-FIX-002-WATERLEAK-RESOLVED",
        "title": "Major potable water pipe burst on MG Road",
        "title_ta": "எம்.ஜி. சாலையில் பிரதான குடிநீர் குழாய் உடைப்பு",
        "description": "Continuous drinking water leakage flooding street and causing water shortage in block.",
        "category_code": "water_supply",
        "department_code": "DEPT_MAWS",
        "area_code": "ADM-TN-GCC-ZONE-13-ADYAR",
        "status": "VERIFIED_RESOLVED",
        "severity": "CRITICAL",
        "latitude": 13.0040,
        "longitude": 80.2580,
        "reported_date": "2024-02-15T08:00:00Z",
        "target_resolution_date": "2024-02-16T08:00:00Z",
        "actual_resolution_date": "2024-02-16T04:00:00Z",
        "repeat_count": 1,
        "resolution_verification_status": "VERIFIED",
        "is_test_fixture": True
    },
    {
        "issue_code": "CIV-FIX-003-DELAYED-TRANSFORMER",
        "title": "Burnt 250kVA distribution transformer causing blackout",
        "title_ta": "250 kVA மின்மாற்றி பழுது காரணமாக மின்வெட்டு",
        "description": "Transformer damaged after short circuit; residential area without electricity for 72 hours.",
        "category_code": "electricity",
        "department_code": "DEPT_TANGEDCO",
        "area_code": "ADM-TN-DIST-024-MADURAI",
        "status": "ESCALATED",
        "severity": "CRITICAL",
        "latitude": 9.9280,
        "longitude": 78.1210,
        "reported_date": "2024-01-10T12:00:00Z",
        "target_resolution_date": "2024-01-11T12:00:00Z",
        "actual_resolution_date": None,
        "repeat_count": 5,
        "resolution_verification_status": "PENDING_VERIFICATION",
        "is_test_fixture": True
    }
]

# ---------------------------------------------------------------------------
# 7. Response Records Fixtures
# ---------------------------------------------------------------------------
MOCK_RESPONSES: List[Dict[str, Any]] = [
    {
        "response_code": "RSP-FIX-001-WATERLEAK",
        "issue_code": "CIV-FIX-002-WATERLEAK-RESOLVED",
        "department_code": "DEPT_MAWS",
        "action_type": "RESOLVED",
        "official_remark": "300mm CI main pipeline joint re-welded and valve replaced. Potable water supply restored successfully.",
        "action_taken_date": "2024-02-16T04:00:00Z",
        "sla_breached": False,
        "delay_hours": 0.0,
        "is_test_fixture": True
    },
    {
        "response_code": "RSP-FIX-002-TRANSFORMER-DELAYED",
        "issue_code": "CIV-FIX-003-DELAYED-TRANSFORMER",
        "department_code": "DEPT_TANGEDCO",
        "action_type": "ACKNOWLEDGED",
        "official_remark": "Replacement transformer indented from Central Stores Pasumalai; awaiting crane arrival.",
        "action_taken_date": "2024-01-12T16:00:00Z",
        "sla_breached": True,
        "delay_hours": 52.0,
        "is_test_fixture": True
    }
]

# ---------------------------------------------------------------------------
# 8. Resolution Evidence Fixtures
# ---------------------------------------------------------------------------
MOCK_EVIDENCE: List[Dict[str, Any]] = [
    {
        "response_code": "RSP-FIX-001-WATERLEAK",
        "evidence_type": "FIELD_INSPECTION_REPORT",
        "title": "CMWSSB Field Completion Certificate No. 441/2024",
        "description": "Inspected by Assistant Executive Engineer; pressure test confirmed normal 1.5 bar flow with zero leak.",
        "evidence_url": "https://chennaicorporation.gov.in/gcc/reports/leak_repair_441.pdf",
        "sha256_hash": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        "is_verified": True,
        "verified_by": "CivicLens Evidence Engine",
        "is_test_fixture": True
    }
]

# ---------------------------------------------------------------------------
# 9. Public Works Fixtures
# ---------------------------------------------------------------------------
MOCK_PUBLIC_WORKS: List[Dict[str, Any]] = [
    {
        "work_code": "WRK-FIX-001-ROAD-PATCH",
        "issue_code": "CIV-FIX-001-POTHOLE-ADYAR",
        "work_title": "Emergency Cold Mix Bitumen Patchwork in Zone 13 Wards 174-176",
        "executing_agency": "Greater Chennai Corporation Engineering Dept",
        "sanctioned_amount_inr": 250000.0,
        "tender_ref": "TNTENDERS/GCC/2024/0981",
        "status": "SANCTIONED",
        "is_test_fixture": True
    }
]

# ---------------------------------------------------------------------------
# 10. Acquisition Test Fixtures (HTML, CSV, JSON, Mock Content)
# ---------------------------------------------------------------------------
MOCK_HTML_PAGE_WITH_TABLE: str = """<!DOCTYPE html>
<html>
<head><title>Tamil Nadu Municipal Grievance Report 2024</title></head>
<body>
  <h1>Monthly Redressal Bulletin - March 2024</h1>
  <p>Official report published by Directorate of Municipal Administration.</p>
  <div class="links">
    <a href="/reports/march_2024.pdf">Download March PDF Report</a>
    <a href="/data/grievances_2024.csv">Download CSV Dataset</a>
    <a href="/admin/dashboard">Restricted Admin Panel</a>
    <a href="https://external-unauthorized.com/leak">External Link</a>
  </div>
  <table id="grievance_summary">
    <thead>
      <tr>
        <th>District</th>
        <th>Category</th>
        <th>Total Received</th>
        <th>Disposed</th>
        <th>Officer Contact</th>
      </tr>
    </thead>
    <tbody>
      <tr>
        <td>Chennai</td>
        <td>roads</td>
        <td>1420</td>
        <td>1280</td>
        <td>Thiru S. Raman, Ph: 9840112233</td>
      </tr>
      <tr>
        <td>Madurai</td>
        <td>water_supply</td>
        <td>850</td>
        <td>790</td>
        <td>Tmt K. Valli, Email: valli.k@tn.gov.in</td>
      </tr>
      <tr>
        <td>Coimbatore</td>
        <td>waste_management</td>
        <td>960</td>
        <td>940</td>
        <td>Office D.No. 4, Town Hall</td>
      </tr>
    </tbody>
  </table>
</body>
</html>"""

MOCK_CSV_DATA: str = """district,category,received_count,disposed_count,sla_compliance_pct,officer_notes
Chennai,roads,1420,1280,90.1,Contact Thiru Ramesh at 9876543210
Madurai,water_supply,850,790,92.9,Supervised by Tmt Geetha
Coimbatore,electricity,640,610,95.3,Main transformer restored on time
Tiruchirappalli,drainage,530,480,90.5,Stormwater desilting completed
Salem,streetlights,410,400,97.5,LED replacement drive completed
"""

MOCK_JSON_DATA: str = """[
  {
    "portal": "CM_HELPLINE_1100",
    "department": "Municipal Administration",
    "total_receipts": 15420,
    "total_disposed": 14100,
    "pending_over_30_days": 180,
    "officer_in_charge": "Thiru K. Balasubramanian",
    "contact_phone": "9444012345"
  },
  {
    "portal": "GCC_1913",
    "department": "Greater Chennai Corporation",
    "total_receipts": 8900,
    "total_disposed": 8450,
    "pending_over_30_days": 95,
    "officer_in_charge": "Tmt Priya",
    "contact_email": "priya.gcc@gmail.com"
  }
]"""

# ---------------------------------------------------------------------------
# 11. Heterogeneous Grievance Ingestion Test Fixtures (Phase 8.3)
# ---------------------------------------------------------------------------
MOCK_DARPG_RECORDS: List[Dict[str, Any]] = [
    {
        "Registration Number": "DARPG/TN/2024/0001",
        "Received Date": "14/03/2024",
        "Ministry/Dept": "Municipal Administration and Water Supply",
        "Category": "Drinking water contamination",
        "Grievance Description": "Water coming through pipeline in Adyar has foul smell. Complainant Thiru R. Mani, Phone: 9840234567.",
        "Status": "Closed",
        "Resolution Date": "20/03/2024",
        "State/UT": "Chennai"
    },
    {
        "Registration Number": "DARPG/TN/2024/0002",
        "Received Date": "2024-03-16",
        "Ministry/Dept": "TANGEDCO",
        "Category": "Electricity Transformer Burnt",
        "Grievance Description": "Residential transformer exploded near temple. Madurai district.",
        "Status": "Under Enquiry",
        "State/UT": "Madurai"
    }
]

MOCK_GCC_RECORDS: List[Dict[str, Any]] = [
    {
        "complaint_no": "GCC/2024/1913/0101",
        "date": "10-Mar-2024",
        "complaint_type": "Potholes on Road",
        "details": "Huge pothole on 4th Main Road, Ward 174 Besant Nagar. Please contact Tmt Revathi at 9444123456.",
        "ward_no": "174",
        "zone": "13",
        "status": "Completed",
        "closed_date": "12-Mar-2024"
    },
    {
        "complaint_no": "GCC/2024/1913/0102",
        "date": "12/03/2024",
        "complaint_type": "Garbage Not Cleared",
        "details": "Overflowing dumper placer bin outside school.",
        "ward_no": "45",
        "zone": "4",
        "status": "In Progress"
    }
]

MOCK_CM_HELPLINE_RECORDS: List[Dict[str, Any]] = [
    {
        "petition_id": "MM-2024-88901",
        "lodged_on": "15/02/2024",
        "department_name": "நெடுஞ்சாலைத்துறை",
        "grievance_nature": "சாலை சேதம் மற்றும் நடைபாதை ஆக்கிரமிப்பு",
        "petition_summary": "மாநில நெடுஞ்சாலையில் பெரிய பள்ளங்கள் ஏற்பட்டு விபத்து ஏற்படுகிறது. தாம்பரம் பகுதி.",
        "district": "செங்கல்பட்டு",
        "current_status": "தீர்க்கப்பட்டது",
        "disposal_date": "25/02/2024"
    },
    {
        "petition_id": "MM-2024-88902",
        "lodged_on": "01/03/2024",
        "department_name": "வருவாய்த்துறை",
        "grievance_nature": "பட்டா மாறுதல் தாமதம்",
        "petition_summary": "6 மாதங்களாக பட்டா மாறுதல் விண்ணப்பம் நிலுவையில் உள்ளது.",
        "district": "திருச்சிராப்பள்ளி",
        "current_status": None  # Unknown status test
    }
]


# ---------------------------------------------------------------------------
# 11. Phase 8.4 Issue Classification & Relationship Fixtures
# ---------------------------------------------------------------------------
MOCK_CLASSIFICATION_RECORDS: List[Dict[str, Any]] = [
    {
        "id": "TC-TAMIL-01",
        "raw_category": "குடிநீர் விநியோகம்",
        "description": "குடிநீர் குழாய் உடைந்து வீணாகிறது, குடிநீர் பற்றாக்குறை ஏற்பட்டுள்ளது.",
        "expected_category": "water_supply",
        "expected_language": "ta"
    },
    {
        "id": "TC-TAMIL-02",
        "raw_category": "மின்தடை",
        "description": "மின்மாற்றி வெடித்து மின்தடை ஏற்பட்டுள்ளது. தாழ்வாக செல்லும் மின்கம்பிகள் ஆபத்தை ஏற்படுத்துகின்றன.",
        "expected_category": "electricity",
        "expected_language": "ta"
    },
    {
        "id": "TC-ENGLISH-01",
        "raw_category": "Streetlight Issue",
        "description": "Broken streetlight and dark street on 4th Avenue near park. Lamp post is defunct.",
        "expected_category": "streetlights",
        "expected_language": "en"
    },
    {
        "id": "TC-ENGLISH-02",
        "raw_category": "Solid Waste",
        "description": "Overflowing compactor bin and garbage dumped on road outside government school.",
        "expected_category": "waste_management",
        "expected_language": "en"
    },
    {
        "id": "TC-MIXED-01",
        "raw_category": "Road damage",
        "description": "Road-la periya pothole irukku, tar saalai damaged and accidents are happening.",
        "expected_category": "roads",
        "expected_language": "mixed"
    },
    {
        "id": "TC-MIXED-02",
        "raw_category": "Electricity complaint",
        "description": "EB transformer burst aagi current illa for 2 days. Low voltage problem.",
        "expected_category": "electricity",
        "expected_language": "mixed"
    },
    {
        "id": "TC-MIXED-03",
        "raw_category": "Patta delay",
        "description": "Patta maathal application submit panni 4 months aachu, revenue department delay.",
        "expected_category": "government_service_delays",
        "expected_language": "mixed"
    },
    {
        "id": "TC-UNCERTAIN-01",
        "raw_category": "General civic grievance",
        "description": "General disturbance and some unspecified public nuisance.",
        "expected_category": "other_civic_issues",
        "expected_review": "PENDING_HUMAN_REVIEW"
    }
]

MOCK_RELATIONSHIP_SCENARIOS = {
    # Scenario A: Exact duplicate records
    "duplicate_pair": [
        {
            "grievance_id": "GRV-GCC-TEST-001",
            "source_id": "GCC_CHENNAI",
            "source_record_reference": "GCC/2024/DUP/101",
            "issue_category": IssueCategoryEnum.ROADS,
            "description_or_permitted_summary": "Potholes on 4th Main Road, Ward 174 Besant Nagar.",
            "administrative_area_id": "ADM-TN-GCC-WARD-174",
            "submission_date": "2024-03-01T10:00:00Z"
        },
        {
            "grievance_id": "GRV-GCC-TEST-001-DUP",
            "source_id": "GCC_CHENNAI",
            "source_record_reference": "GCC/2024/DUP/101",
            "issue_category": IssueCategoryEnum.ROADS,
            "description_or_permitted_summary": "Potholes on 4th Main Road, Ward 174 Besant Nagar.",
            "administrative_area_id": "ADM-TN-GCC-WARD-174",
            "submission_date": "2024-03-01T10:00:00Z"
        }
    ],

    # Scenario B: Multiple complaints about the same active issue
    "multiple_complaints_same_issue": [
        {
            "grievance_id": "GRV-GCC-ACTIVE-01",
            "source_id": "GCC_CHENNAI",
            "source_record_reference": "GCC/2024/ACT/01",
            "issue_category": IssueCategoryEnum.ROADS,
            "description_or_permitted_summary": "Dangerous deep pothole on 4th Main Road, Ward 174 Besant Nagar.",
            "administrative_area_id": "ADM-TN-GCC-WARD-174",
            "submission_date": "2024-03-10T09:00:00Z"
        },
        {
            "grievance_id": "GRV-GCC-ACTIVE-02",
            "source_id": "GCC_CHENNAI",
            "source_record_reference": "GCC/2024/ACT/02",
            "issue_category": IssueCategoryEnum.ROADS,
            "description_or_permitted_summary": "Large crater and damaged road on 4th Main Road, Ward 174 Besant Nagar causing accidents.",
            "administrative_area_id": "ADM-TN-GCC-WARD-174",
            "submission_date": "2024-03-14T11:00:00Z"
        }
    ],

    # Scenario C: Recurring issue at the same location (prior resolved, returns months later)
    "recurring_issue_pair": [
        {
            "grievance_id": "GRV-GCC-REC-HISTORIC",
            "source_id": "GCC_CHENNAI",
            "source_record_reference": "GCC/2024/HIST/01",
            "issue_category": IssueCategoryEnum.ROADS,
            "description_or_permitted_summary": "Damaged asphalt on 4th Main Road, Ward 174 Besant Nagar.",
            "administrative_area_id": "ADM-TN-GCC-WARD-174",
            "submission_date": "2024-01-05T09:00:00Z",
            "status": "RESOLVED"
        },
        {
            "grievance_id": "GRV-GCC-REC-NEW",
            "source_id": "GCC_CHENNAI",
            "source_record_reference": "GCC/2024/HIST/02",
            "issue_category": IssueCategoryEnum.ROADS,
            "description_or_permitted_summary": "Monsoon washaway and recurring pothole on 4th Main Road, Ward 174 Besant Nagar.",
            "administrative_area_id": "ADM-TN-GCC-WARD-174",
            "submission_date": "2024-10-15T10:00:00Z",
            "status": "OPEN"
        }
    ],

    # Scenario D: Separate issues in the same area
    "separate_issues_same_area": [
        {
            "grievance_id": "GRV-GCC-SEP-01",
            "source_id": "GCC_CHENNAI",
            "source_record_reference": "GCC/2024/SEP/01",
            "issue_category": IssueCategoryEnum.ROADS,
            "description_or_permitted_summary": "Damaged road on 4th Main Road, Ward 174 Besant Nagar.",
            "administrative_area_id": "ADM-TN-GCC-WARD-174",
            "submission_date": "2024-03-10T10:00:00Z"
        },
        {
            "grievance_id": "GRV-GCC-SEP-02",
            "source_id": "GCC_CHENNAI",
            "source_record_reference": "GCC/2024/SEP/02",
            "issue_category": IssueCategoryEnum.STREETLIGHTS,
            "description_or_permitted_summary": "Broken street light on 4th Main Road, Ward 174 Besant Nagar.",
            "administrative_area_id": "ADM-TN-GCC-WARD-174",
            "submission_date": "2024-03-11T10:00:00Z"
        }
    ],

    # Scenario E: Unrelated reports with identical text in different districts/areas
    "unrelated_similar_reports": [
        {
            "grievance_id": "GRV-CHENNAI-SIMILAR",
            "source_id": "GCC_CHENNAI",
            "source_record_reference": "GCC/2024/SIM/01",
            "issue_category": IssueCategoryEnum.WATER_SUPPLY,
            "description_or_permitted_summary": "Contaminated drinking water and pipeline leakage outside primary school.",
            "administrative_area_id": "ADM-TN-GCC-WARD-174",
            "submission_date": "2024-03-10T10:00:00Z"
        },
        {
            "grievance_id": "GRV-MADURAI-SIMILAR",
            "source_id": "TNEGA_CM_HELPLINE",
            "source_record_reference": "MM/2024/SIM/02",
            "issue_category": IssueCategoryEnum.WATER_SUPPLY,
            "description_or_permitted_summary": "Contaminated drinking water and pipeline leakage outside primary school.",
            "administrative_area_id": "ADM-TN-DIST-024-MADURAI",
            "submission_date": "2024-03-10T10:00:00Z"
        }
    ]
}



