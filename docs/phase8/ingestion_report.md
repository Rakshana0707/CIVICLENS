# CIVICLENS TN — Phase 8.3: Public Grievance Ingestion & Normalization Report

**Document Version:** 1.0.0  
**Phase:** 8.3 — Grievance Data Ingestion and Normalization  
**Status:** Canonical Ingestion Pipeline Operational  
**Compliance Standard:** Digital Personal Data Protection Act (DPDPA 2023), TN Open Data Norms, Zero-Fabrication Directive  

---

## 1. Executive Summary

Phase 8.3 delivers the ingestion and normalization engine for CIVICLENS TN's Public Grievance and Civic Issue Intelligence System. Public grievance datasets across Tamil Nadu are characterized by extreme structural heterogeneity, bilingual entries (Tamil and English), fragmented identifiers, inconsistent date formats, and varying lifecycle states.

The Phase 8.3 pipeline transforms heterogenous, multi-source civic grievance feeds into a standardized canonical model (`CanonicalGrievanceRecord` / ORM `GrievanceRecord`) without ever synthesizing individual complaints or fabricating resolution outcomes.

### Core Architectural Principles
1. **Zero Fabrication & Deterministic Lineage**: Every canonical record strictly maps back to an authorized raw record reference (`source_record_reference`) and cryptographic content fingerprint (`SHA-256`).
2. **Strict Status Integrity**: Unknown, missing, or blank grievance statuses **NEVER default to `RESOLVED`**. Unclassified statuses are explicitly flagged as `UNKNOWN` with quality flag `MISSING_STATUS`.
3. **Data Quality Status Auditing**: Every record carries an explicit data quality evaluation (`VALID`, `MISSING_DATE`, `SUSPECT_DATE`, `AMBIGUOUS_CATEGORY`, `UNKNOWN_DEPARTMENT`, `UNKNOWN_AREA`, `MISSING_STATUS`).
4. **Bilingual Semantic Normalization**: First-class support for English and Tamil taxonomy keywords across 14 civic categories, 7 major government departments, and 38 administrative districts.
5. **DPDPA 2023 Privacy Scrubbing**: Prior to persistence, analytics, or presentation, sensitive personal identifiers (petitioner names, phone numbers, emails, Aadhaar/identity numbers, and door numbers) are scrubbed via deterministic regular expressions while preserving civic context.

---

## 2. Canonical Grievance Schema

All ingested records are normalized into the following 14 canonical fields:

| Field Name | Type | Description | Mandatory |
| :--- | :--- | :--- | :--- |
| `grievance_id` | String(64) | Deterministic unique canonical ID (e.g., `GRV-DARPG_CPGRAMS-DARPG-TN-2024-0001`) | Yes |
| `source_id` | String(64) | Originating portal identifier (e.g., `DARPG_CPGRAMS`, `GCC_CHENNAI`, `TNEGA_CM_HELPLINE`) | Yes |
| `issue_category` | Enum | One of 14 standardized Phase 8 civic categories | Yes |
| `description_or_permitted_summary` | Text | Sanitized, anonymized civic issue description or permitted summary | No |
| `submission_date` | DateTime(UTC) | Normalized date/time when grievance was officially lodged | Yes |
| `department_id` | String(64) | Canonical department code (e.g., `DEPT_HIGHWAYS`, `DEPT_GCC`, `DEPT_TANGEDCO`) | No |
| `administrative_area_id` | String(64) | Normalized administrative area code (District, Zone, or Ward) | No |
| `status` | String(32) | Normalized status (`OPEN`, `IN_PROGRESS`, `RESOLVED`, `PENDING`, `REJECTED`, `ESCALATED`, `UNKNOWN`) | Yes |
| `acknowledgement_date` | DateTime(UTC) | Official acknowledgement or docket creation timestamp | No |
| `resolution_date` | DateTime(UTC) | Date of formal resolution/closure (strictly populated only if closed) | No |
| `source_document_id` | Integer | Foreign key linking to acquisition audit log / `SourceDocument` | No |
| `source_record_reference` | String(128) | Native petition/complaint token or docket number from source | No |
| `ingestion_timestamp` | DateTime(UTC) | UTC timestamp of ingestion processing | Yes |
| `data_quality_status` | String(32) | Validation outcome flag (`VALID`, `SUSPECT_DATE`, `AMBIGUOUS_CATEGORY`, etc.) | Yes |

---

## 3. Source-Specific Schema Adapters

CIVICLENS TN provides specialized adapter layers for the major public grievance portals in Tamil Nadu:

### 3.1 DARPG CPGRAMS Adapter (`DARPGCPGRAMSAdapter`)
- **Portal URL**: `https://pgportal.gov.in/`
- **Native Fields**: `Registration Number`, `Received Date`, `Ministry/Dept`, `Category`, `Grievance Description`, `Status`, `State/UT`, `Date of Action`.
- **Transformation Logic**:
  - `grievance_id` constructed from `Registration Number`.
  - `Ministry/Dept` mapped to Tamil Nadu state departments or nodal state counterparts.
  - `Received Date` normalized from `YYYY-MM-DD` or `DD-MM-YYYY`.
  - Statuses mapped from central CPGRAMS lifecycle states (`Case Closed` -> `RESOLVED`, `Under Enquiry` -> `IN_PROGRESS`, `Pending` -> `PENDING`).

### 3.2 Greater Chennai Corporation 1913 Adapter (`GreaterChennaiCorporationAdapter`)
- **Portal URL**: `https://chennaicorporation.gov.in/` / GCC 1913 Helpline
- **Native Fields**: `complaint_no`, `date`, `complaint_type`, `details`, `ward_no`, `zone`, `status`, `closed_date`.
- **Transformation Logic**:
  - Ward numbers normalized to canonical GCC format: `ADM-TN-GCC-WARD-{ward}`.
  - Zone numbers normalized to canonical zone format: `ADM-TN-GCC-ZONE-{zone}`.
  - Municipal statuses mapped (`Completed`/`Closed` -> `RESOLVED`, `In Progress` -> `IN_PROGRESS`, `Registered`/`Assigned` -> `OPEN`).
  - Default department assigned as `DEPT_GCC`.

### 3.3 Mudhalvarin Mugavari TNeGA CM Helpline Adapter (`MudhalvarinMugavariAdapter`)
- **Portal URL**: `https://cmhelpline.tnega.org/`
- **Native Fields**: `petition_id` / `petition_number`, `lodged_on` / `petition_date`, `department_name` (Tamil/English), `grievance_nature`, `petition_summary`, `district`, `taluk`, `current_status`, `disposal_date`.
- **Transformation Logic**:
  - Full Tamil string tokenization and lexicon mapping (`தீர்க்கப்பட்டது` -> `RESOLVED`, `நடைமுறையில் உள்ளது` / `பரிசீலனையில்` -> `IN_PROGRESS`, `நிலுவையில்` -> `PENDING`, `நிராகரிக்கப்பட்டது` -> `REJECTED`).
  - Administrative mapping parses all 38 Tamil Nadu districts in Tamil script (e.g., `செங்கல்பட்டு` -> `ADM-TN-DIST-014-CHENGALPATTU`, `மதுரை` -> `ADM-TN-DIST-024-MADURAI`).

### 3.4 Generic Civic Adapter (`GenericCivicAdapter`)
- Fallback schema mapper supporting dynamic key discovery for ad-hoc open datasets (Data.gov.in, RTI releases, municipal CSVs).
- Evaluates candidate key aliases (`id`/`token`/`docket`, `date`/`created_at`, `details`/`body`, `category`/`subject`, `status`/`state`).

---

## 4. Normalization Subsystems

### 4.1 Date Normalization (`DateNormalizer`)
- Supports 20 heterogeneous date formats (ISO-8601 UTC, Indian `DD/MM/YYYY`, `DD-Mon-YYYY`, `YYYY/MM/DD`, UNIX timestamps).
- Enforces temporal sanity checks:
  - Dates preceding year 2000 are flagged `SUSPECT_DATE`.
  - Future dates (timestamp > current UTC + 24 hours) are rejected and flagged `SUSPECT_DATE`.

### 4.2 Category Normalization (`CategoryNormalizer`)
- Maps unstructured grievance categories into 14 standardized Phase 8 taxonomies:
  1. `roads` (சாலை, குண்டு குழி, potholes, pavement)
  2. `water_supply` (குடிநீர், pipe leak, contaminated water, metro water)
  3. `drainage` (சாக்கடை, கழிவுநீர், stormwater drain, sewer overflow)
  4. `sanitation` (பொது சுகாதாரம், toilet, mosquito fogging, unhygienic)
  5. `waste_management` (குப்பை, garbage, dump bin, solid waste)
  6. `streetlights` (தெருவிளக்கு, dark street, lamp post, broken LED)
  7. `public_transport` (பேருந்து, bus stop shelter, frequency, MTC/TNSTC)
  8. `healthcare_access` (மருத்துவமனை, PHC clinic, doctor, medicine shortage)
  9. `education_infrastructure` (அரசு பள்ளி, classroom, desk, school toilet)
  10. `electricity` (மின்சாரம், power cut, transformer, low voltage, TANGEDCO)
  11. `public_safety_infrastructure` (போக்குவரத்து சிக்னல், stray dog menace, CCTV, blind spot)
  12. `environmental_concerns` (ஏரி ஆக்கிரமிப்பு, pollution, waterbody, tree felling)
  13. `government_service_delays` (பட்டா மாறுதல் தாமதம், ration card, pension, certificate delay)
  14. `other_civic_issues` (Unclassified civic complaints)

### 4.3 Department Normalization (`DepartmentNormalizer`)
- Maps multi-lingual department nomenclatures to canonical department identifiers:
  - `DEPT_MAWS`: Municipal Administration and Water Supply (நகராட்சி நிர்வாகம்)
  - `DEPT_HIGHWAYS`: Highways and Minor Ports (நெடுஞ்சாலைத்துறை)
  - `DEPT_TANGEDCO`: Generation and Distribution Corporation (மின்சார வாரியம்)
  - `DEPT_GCC`: Greater Chennai Corporation (பெருநகர சென்னை மாநகராட்சி)
  - `DEPT_HEALTH`: Health and Family Welfare (மக்கள் நல்வாழ்வுத்துறை)
  - `DEPT_REVENUE`: Revenue and Disaster Management (வருவாய்த்துறை)
  - `DEPT_EDUCATION`: School Education Department (பள்ளிக் கல்வித்துறை)

### 4.4 Status Normalization (`StatusNormalizer`) & Non-Resolution Rule
- **Guaranteed Policy**: Unrecognized or missing statuses return `("UNKNOWN", "MISSING_STATUS")`.
- Under no circumstances is an unresolved or missing grievance marked as `RESOLVED`.
- Mappings:
  - `RESOLVED`: `resolved`, `closed`, `completed`, `disposed`, `தீர்க்கப்பட்டது`, `முடிவுற்றது`
  - `IN_PROGRESS`: `in progress`, `under enquiry`, `investigating`, `action taken`, `பரிசீலனையில்`, `நடவடிக்கை`
  - `OPEN`: `open`, `registered`, `lodged`, `admitted`, `பதிவு செய்யப்பட்டது`
  - `PENDING`: `pending`, `awaiting`, `நிலுவையில்`
  - `REJECTED`: `rejected`, `dropped`, `ineligible`, `நிராகரிக்கப்பட்டது`
  - `ESCALATED`: `escalated`, `transferred`, `மேல்முறையீடு`

---

## 5. Duplicate Detection & Audit Lineage

The pipeline employs a two-tier duplicate detection framework (`GrievanceDuplicateDetector`):

1. **Deterministic Primary Index**: Checks `(source_id, source_record_reference)`. If the exact docket ID already exists within the dataset, the record is flagged `DUPLICATE` and excluded from double-counting.
2. **Content Hash Fingerprinting**: For sources lacking unique tokens, an SHA-256 hash is computed over `source_id | submission_date | category | normalized_text`. Exact identical grievances lodged at identical dates are flagged as duplicates.
3. **Auditing & Raw Data Retainage**: The canonical record preserves `raw_record_reference` holding the original docket ID, unparsed category, unparsed status, and content hash, ensuring full reverse-auditability.

---

## 6. Privacy Preservation (DPDPA 2023)

In strict adherence to the Digital Personal Data Protection Act (DPDPA 2023):
- **Citizen Names**: Indian salutations (`Thiru`, `Tmt`, `Selvi`, `Shri`, `Smt`, `Mr`, `Mrs`) combined with citizen names are stripped from descriptions.
- **Phone Numbers**: 10-digit mobile numbers with optional `+91` or `0` prefixes are redacted to `[REDACTED_PHONE]`.
- **Email Addresses**: All email formats are redacted to `[REDACTED_EMAIL]`.
- **Identity Credentials**: 12-digit Aadhaar sequences, PAN cards, and voter identity tokens are detected and excised.
- **Residential Specifics**: Specific door/flat numbers (`Door No. 12/A`, `Flat 4B`) are redacted to `[REDACTED_DOOR_NO]` while preserving street, ward, and district civic context.

---

## 7. Batch Ingestion & Quality Metrics Report

Batch operations return an `IngestionReport` encapsulating validation statistics:

```json
{
  "total_records_processed": 4,
  "successful_normalizations": 2,
  "duplicates_discarded": 1,
  "rejected_records": 1,
  "data_quality_issues_detected": 0,
  "breakdown_by_category": {
    "roads": 1,
    "electricity": 1
  },
  "breakdown_by_status": {
    "RESOLVED": 1,
    "IN_PROGRESS": 1
  },
  "breakdown_by_quality_status": {
    "VALID": 2
  }
}
```

---

## 8. Verification & Test Suite

The ingestion pipeline is verified through automated test suites in `tests/unit/test_phase8_ingestion.py`:
- `test_1_darpg_cpgrams_adapter`: CPGRAMS docket mapping, status, and PII redaction.
- `test_2_gcc_adapter_ward_zone_mapping`: GCC 1913 ward and zone normalization.
- `test_3_cm_helpline_adapter_tamil_support`: Mudhalvarin Mugavari Tamil script translation and district extraction.
- `test_4_missing_status_never_defaults_to_resolved`: Non-resolution assertion for null statuses (`status == "UNKNOWN"`).
- `test_5_date_normalization_variations_and_anomalies`: Evaluation of 20 date formats and future date rejection.
- `test_6_bilingual_category_normalization`: Dual-language taxonomy matching across all 14 categories.
- `test_7_department_normalization`: Government department normalization and nodal routing.
- `test_8_duplicate_detection`: Exact token duplicate and content hash collision handling.
- `test_9_database_orm_persistence`: SQLAlchemy ORM serialization and database roundtrip.
- `test_10_batch_ingestion_and_report`: Batch throughput, duplicate filtering, and audit metrics.

**Full Phase 8 Test Suite Status**: 29/29 passing tests across architecture, acquisition, and ingestion.
