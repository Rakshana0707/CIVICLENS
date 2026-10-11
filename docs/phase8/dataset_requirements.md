# Phase 8 — Public Grievance & Civic Issue Intelligence Dataset Requirements

## 1. Executive Summary & Data Governance Strategy

Phase 8 of **CIVICLENS TN** establishes the data architecture for the **Public Grievance & Civic Issue Intelligence System** of Tamil Nadu.

> [!IMPORTANT]
> **Data Integrity & Non-Fabrication Rule:**
> Real Phase 8 civic datasets have **NOT** been collected or scraped yet. In strict compliance with project integrity principles, all schemas, data contracts, privacy filters, and test fixtures are established prior to live data harvesting. Under no circumstances are citizen complaints fabricated or synthesized into production tables. All mock records are isolated within `tests/fixtures/phase8_fixtures.py` and flagged with `is_test_fixture=True`.

### 1.1 Empirical Accessibility Assessment of Starting Sources

Prior to specifying dataset requirements, direct network inspection of the designated starting sources was performed:

| Starting Source URL | Institutional Entity | Real-World Accessibility & Gate Findings | Usable Civic Intelligence Artifacts |
|:---|:---|:---|:---|
| `https://pgportal.gov.in/` | DARPG, Government of India (CPGRAMS) | Accessible via HTTPS. Citizen petition filing and status tracking are behind citizen login / OTP. No public bulk grievance API exists. Monthly State Progress Reports are published as public PDF bulletins. | Monthly Public Grievance Progress Reports, state-wise receipt & disposal totals, pending age slabs. |
| `https://cmhelpline.tnega.org/portal/en/home` | TNeGA, Government of Tamil Nadu ("Mudhalvarin Mugavari" / IIPGCMS) | Accessible via HTTPS (Zoho Desk backed). Individual grievance filing and tracking are gated by **Mobile OTP authentication**. No unauthenticated bulk grievance endpoint. | Public FAQ articles, 43 mapped department IDs, Citizen's Charter timelines, DIPR press releases on aggregate disposal counts. |
| `https://www.tn.gov.in/` | State Portal of Tamil Nadu | Open public portal. Accessible. Contains department policy notes, Citizen's Charters, Government Orders (G.O.s), and DIPR press releases. | Citizen's Charters with statutory SLA service standards, department G.O.s, annual administrative reports. |
| `https://chennaicorporation.gov.in/gcc/` | Greater Chennai Corporation (GCC) | Accessible via HTTPS (Tomcat portal). Namma Chennai grievance filing requires mobile OTP. Council resolutions, tender bulletins, and ward directory are open. | Ward maps, Council meeting resolutions, works tenders, 1913 helpline procedural standards, zonal boundaries. |
| `https://www.data.gov.in/` | Open Government Data (OGD) Platform India | Open public access via REST API and CSV/XLSX downloads with registered API key. | District-level civic amenities, water supply coverage indices, solid waste management metrics. |
| `https://www.tnbudget.tn.gov.in/` | Finance Department, Tamil Nadu | Open public portal. Budget Books, Explanatory Memoranda, Detailed Demands for Grants published as PDFs. | Statutory capital outlay and maintenance allocations for MAWS, Highways, Energy, and Rural Development. |

---

## 2. Exhaustive Dataset Specifications

The system requires 10 distinct categories of datasets spanning grievance portals, municipal logs, public works, administrative boundaries, service standards, media reports, and cross-phase entities.

---

### 2.1 Public Grievance Records (Aggregate & Disclosed)
- **Purpose:** Provide baseline volume, temporal intake trends, department distribution, and geographic distribution of citizen grievances across Tamil Nadu.
- **Source URL:** 
  - DARPG CPGRAMS Monthly Reports: [https://darpg.gov.in/](https://darpg.gov.in/) & [https://pgportal.gov.in/](https://pgportal.gov.in/)
  - TNeGA / IIPGCMS Annual Performance Bulletins: [https://tnega.tn.gov.in/](https://tnega.tn.gov.in/)
- **Expected Format:** PDF monthly grievance disposal reports, aggregate HTML tables, gazetted departmental annual reports.
- **Required Fields:**
  - `report_period`: Month and financial year (e.g. `2024-03`).
  - `department_name`: Target administrative department.
  - `receipts_count`: Total petitions received in period.
  - `disposals_count`: Total petitions resolved or disposed.
  - `pending_count`: Total active unresolved backlog.
  - `pending_over_30_days`: Petitions pending beyond statutory Citizen's Charter threshold.
  - `satisfaction_rating`: Aggregate feedback score (where published).
- **Geographic and Date Coverage:** Tamil Nadu statewide (38 districts); FY 2019-20 to Present.
- **Access Restrictions:** Open public access to aggregate documents. Individual petitions protected by DPDPA 2023.
- **Availability Status:** High availability for aggregate monthly totals; individual case files are private.
- **Collection Method:** Monthly scheduled scraper of DARPG portal publications and TNeGA press releases; PDF tabular parsing via `pdfplumber`.
- **Validation Method:** Cross-check monthly opening balance + receipts - disposals = closing balance.
- **Known Limitations:** Does not reveal micro-location (ward/street level) in central reports; limited to state-level and department-level aggregates.

---

### 2.2 Tamil Nadu Grievance Portal Documentation & Aggregate Reports
- **Purpose:** Understand departmental routing hierarchy, escalation pathways, category taxonomy, and official closure criteria used by "Mudhalvarin Mugavari" (CM Helpline 1100).
- **Source URL:** [https://cmhelpline.tnega.org/portal/en/home](https://cmhelpline.tnega.org/portal/en/home) & DIPR releases.
- **Expected Format:** Portal JSON configuration manifests, FAQ documentation, G.O. Ms. No. 5 Information Technology Department (2021), official circulars.
- **Required Fields:**
  - `portal_department_id`: Canonical internal ID (e.g. `35665000000010772`).
  - `department_name_en`: English title (e.g. `Municipal Administration and Water Supply`).
  - `department_name_ta`: Tamil title (e.g. `நகராட்சி நிர்வாகம் மற்றும் குடிநீர் வழங்கல் துறை`).
  - `nodal_officer_designation`: District Collectorate / Directorate grievance officer title.
  - `escalation_levels`: Hierarchy levels (L1: Field Officer, L2: Divisional Head, L3: District Collector, L4: Head of Department).
  - `disposal_turnaround_days`: Standard statutory resolution limit.
- **Geographic and Date Coverage:** All 38 Tamil Nadu districts; May 2021 (launch of consolidated Mudhalvarin Mugavari) to Present.
- **Access Restrictions:** Open public portal documentation and published Government Orders.
- **Availability Status:** Available and active.
- **Collection Method:** Static extraction of published portal metadata, terms of reference, and state gazette orders.
- **Validation Method:** Cross-reference departmental IDs against Secretariat department codes.
- **Known Limitations:** Dynamic changes to internal routing rules are not always publicly gazetted immediately.

---

### 2.3 Municipal Complaint Records
- **Purpose:** Track hyperlocal civic issues (potholes, garbage, sewage overflow, broken streetlights, stray animals) at urban local body (ULB), corporation zone, and ward levels.
- **Source URL:**
  - Greater Chennai Corporation (GCC): [https://chennaicorporation.gov.in/gcc/](https://chennaicorporation.gov.in/gcc/)
  - Coimbatore City Municipal Corporation: [https://www.ccmc.gov.in/](https://www.ccmc.gov.in/)
  - Madurai City Municipal Corporation: [https://maduraicorporation.co.in/](https://maduraicorporation.co.in/)
  - Directorate of Municipal Administration (DMA): [https://tn.gov.in/dma/](https://tn.gov.in/dma/)
- **Expected Format:** Corporation Council meeting agenda and action notes (PDF), public municipal dashboard disclosures, RTI civic summary releases.
- **Required Fields:**
  - `municipality_name`: Corporation or Municipality name (e.g., `Greater Chennai Corporation`).
  - `zone_number`: Administrative zone (e.g., `Zone 13 - Adyar`).
  - `ward_number`: Municipal ward (e.g., `Ward 174`).
  - `issue_category`: Category (`STREETLIGHTS`, `WASTE_MANAGEMENT`, `DRAINAGE`, etc.).
  - `incident_description`: Anonymized summary of issue.
  - `reported_date`: Date lodged.
  - `status`: Current municipal status (`PENDING`, `IN_PROGRESS`, `RESOLVED`).
  - `resolution_timestamp`: Timestamp when department logged completion.
- **Geographic and Date Coverage:** 21 Municipal Corporations, 138 Municipalities across Tamil Nadu; 2021 – Present.
- **Access Restrictions:** Ward summaries and council resolutions are public domain. Direct individual citizen complainant identities must be scrubbed.
- **Availability Status:** Moderate availability; GCC council minutes are published monthly; smaller municipalities publish irregularly.
- **Collection Method:** Council resolution PDF scrapers, public RTI disclosure ingesters, municipal open portal parsers.
- **Validation Method:** Spatial validation ensuring ward numbers map validly to their declared zones and ULB boundaries.
- **Known Limitations:** Lack of standardized schemas across different municipal corporations in Tamil Nadu.

---

### 2.4 Department Response & Action-Taken Reports (ATRs)
- **Purpose:** Capture the formal government response, administrative action taken, work sanction, or rejection justification for public civic issues.
- **Source URL:**
  - Tamil Nadu Legislative Assembly Assurances Committee Reports: [https://www.assembly.tn.gov.in/](https://www.assembly.tn.gov.in/)
  - Department Performance Budget Books: [https://www.tn.gov.in/](https://www.tn.gov.in/)
  - Public Petitions Committee Proceedings.
- **Expected Format:** Assembly committee reports (PDF), department gazette orders, public RTI compliance responses.
- **Required Fields:**
  - `response_id`: Unique tracking reference (e.g. `ATR-MAWS-2023-042`).
  - `department_id`: Answering government department.
  - `civic_issue_id`: Reference to associated civic problem.
  - `action_type`: `INSPECTION_CONDUCTED`, `WORK_SANCTIONED`, `CONTRACT_AWARDED`, `REJECTED_UNFEASIBLE`, `RESOLVED`.
  - `action_summary`: Verbatim official explanation of administrative action.
  - `officer_designation`: Designation of certifying officer (e.g., `Superintending Engineer, Highways`).
  - `response_date`: Date of formal communication.
  - `sanction_order_ref`: Official G.O. or work sanction number (if applicable).
- **Geographic and Date Coverage:** Tamil Nadu statewide; 2016 – Present.
- **Access Restrictions:** Public Legislative Records and Official Gazettes.
- **Availability Status:** High availability for assembly assurances and committee reports.
- **Collection Method:** Legislative assembly assurance crawler, department policy note parser.
- **Validation Method:** Cross-validation of referenced G.O. numbers against Tamil Nadu State Gazette.
- **Known Limitations:** Assembly assurance ATRs operate on a multi-month reporting cycle rather than real-time daily streaming.

---

### 2.5 Public Works and Infrastructure Records
- **Purpose:** Corroborate whether reported civic infrastructure failures (e.g. dilapidated roads, broken water mains) have been addressed through actual budgetary sanctions, tenders, and civil works contracts.
- **Source URL:**
  - Tamil Nadu Tenders Portal: [https://tntenders.gov.in/](https://tntenders.gov.in/)
  - CMDA / Highways Project Tracking: [https://www.cmdachennai.gov.in/](https://www.cmdachennai.gov.in/)
  - MLACDS / MPLADS Constituency Works Registry (from Phase 6).
- **Expected Format:** XML/HTML tender notices, contract award PDFs, bid evaluation summaries.
- **Required Fields:**
  - `tender_id`: Statutory Tender Reference Number.
  - `work_name`: Description of civil work or maintenance project.
  - `department_name`: Executing department / executing agency.
  - `sanctioned_amount_inr`: Contract value in Indian Rupees.
  - `administrative_area_id`: District / Constituency / Ward of execution.
  - `contractor_name`: Awarded engineering entity.
  - `start_date`: Scheduled date of commencement.
  - `completion_date`: Certified or target completion date.
  - `status`: `TENDER_FLOATED`, `AWARDED`, `UNDER_EXECUTION`, `COMPLETED`.
- **Geographic and Date Coverage:** All 38 districts of Tamil Nadu; 2018 – Present.
- **Access Restrictions:** Open public procurement records under Tamil Nadu Transparency in Tenders Act, 1998.
- **Availability Status:** Available and actively published on `tntenders.gov.in`.
- **Collection Method:** Daily automated tender crawl of civil works categories (Roads, Water Works, Drainage, Buildings).
- **Validation Method:** Verify tender ID format, work valuation reasonableness, and executing department validity.
- **Known Limitations:** Completion certificates and defect liability notices are often published separately from initial award notices.

---

### 2.6 Development Statistics & Civic Amenities Indices
- **Purpose:** Establish baseline infrastructure benchmarks (tap water coverage, paved road density, waste processing capacity, primary healthcare centers) across Tamil Nadu's districts and taluks.
- **Source URL:**
  - Department of Economics and Statistics (DES) Tamil Nadu: [https://www.tn.gov.in/des/](https://www.tn.gov.in/des/)
  - Open Government Data India: [https://www.data.gov.in/](https://www.data.gov.in/)
  - Jal Jeevan Mission TN Dashboard: [https://ejalshakti.gov.in/jjmreport/](https://ejalshakti.gov.in/jjmreport/)
  - Swachh Bharat Urban Dashboard: [https://sbmurban.org/](https://sbmurban.org/)
- **Expected Format:** CSV tables, REST API JSON feeds, Statistical Handbooks of Tamil Nadu (PDF).
- **Required Fields:**
  - `indicator_code`: Unique indicator code (e.g., `WATER_TAP_CONN_PCT`, `ROADS_SURFACED_KM_PER_SQKM`).
  - `district_name`: District of measurement.
  - `year`: Reporting year.
  - `metric_value`: Numerical benchmark value.
  - `unit_of_measure`: Percentage, count, kilometers, metric tonnes.
- **Geographic and Date Coverage:** 38 districts of Tamil Nadu; 2011 Census to 2024 annual surveys.
- **Access Restrictions:** Public domain government open data.
- **Availability Status:** High availability across state statistical handbooks and OGD India.
- **Collection Method:** OGD API client, manual ingestion of annual DES statistical handbooks.
- **Validation Method:** Range validation and longitudinal anomaly detection against state totals.
- **Known Limitations:** District-level data is published annually; rural-urban segregation varies by ministry.

---

### 2.7 Administrative Boundaries & Spatial Hierarchy
- **Purpose:** Standardize spatial mapping and prevent jurisdiction confusion across Tamil Nadu's complex multi-tiered administrative structure.
- **Source URL:**
  - Survey of India / Tamil Nadu State Spatial Data Infrastructure: [https://tnssdi.tn.gov.in/](https://tnssdi.tn.gov.in/)
  - Election Commission of India Delimitation Orders.
  - Tamil Nadu Local Bodies Directory (LGD - Local Government Directory): [https://lgd.gov.in/](https://lgd.gov.in/)
- **Expected Format:** GeoJSON spatial boundaries, Shapefiles, LGD CSV mapping tables.
- **Required Fields:**
  - `area_id`: Canonical spatial ID (e.g. `ADM-TN-DIST-013-CHENNAI`).
  - `area_name_en`: English name.
  - `area_name_ta`: Tamil name.
  - `administrative_level`: `STATE`, `DISTRICT`, `TALUK`, `BLOCK`, `MUNICIPAL_CORPORATION`, `WARD`, `ASSEMBLY_CONSTITUENCY`.
  - `parent_area_id`: Foreign key to parent unit (e.g., Ward -> Corporation -> District).
  - `lgd_code`: Local Government Directory standard government code.
  - `census_code_2011`: Census enumeration code.
  - `latitude`: Centroid latitude.
  - `longitude`: Centroid longitude.
- **Geographic and Date Coverage:** Entire territory of Tamil Nadu; current administrative boundaries (including post-2019 newly bifurcated districts: Chengalpattu, Tenkasi, Ranipet, Tirupathur, Kallakurichi, Mayiladuthurai).
- **Access Restrictions:** Open government data.
- **Availability Status:** Available and stable via LGD and Survey of India portals.
- **Collection Method:** Ingest LGD standardized dumps, compile bilingual GIS hierarchy table.
- **Validation Method:** Hierarchical integrity check (ensure every ward points to a valid ULB and district).
- **Known Limitations:** Ward boundary delimitations for urban local bodies occasionally undergo revision after decennial municipal elections.

---

### 2.8 Government Orders & Service Standards (Citizen's Charters)
- **Purpose:** Serve as the legal and statutory benchmark for Service Level Agreements (SLAs), turnaround times, and designated grievance officers under Tamil Nadu citizen charters.
- **Source URL:**
  - Tamil Nadu Citizen's Charters: [https://www.tn.gov.in/charters/](https://www.tn.gov.in/charters/)
  - Department Gazette Orders: [https://www.stationeryprinting.tn.gov.in/](https://www.stationeryprinting.tn.gov.in/)
- **Expected Format:** Citizen Charter booklets (PDF), statutory G.O. notifications.
- **Required Fields:**
  - `standard_id`: Standard code (e.g. `SLA-MAWS-POTHOLE-48H`).
  - `department_id`: Responsible government department.
  - `service_name_en`: Description of service / grievance redressal.
  - `service_name_ta`: Tamil service description.
  - `stipulated_time_limit_hours`: Statutory maximum allowable turnaround time in hours/days.
  - `designated_officer`: Official responsible for service delivery.
  - `appellate_authority`: Official designated for Level 1 escalation if breached.
  - `penalty_provisions`: Statutory compensation / fine if non-compliant.
- **Geographic and Date Coverage:** Tamil Nadu statewide; 2018 – Present.
- **Access Restrictions:** Public domain statutory publications.
- **Availability Status:** High availability on state portal and municipal portals.
- **Collection Method:** PDF ingestion and structured table extraction of department Citizen Charters.
- **Validation Method:** Cross-reference officer titles against current departmental organizational structures.
- **Known Limitations:** Citizen's Charters are updated quadrennially or biannually; minor procedural revisions occur via separate circulars.

---

### 2.9 News Articles About Civic Issues
- **Purpose:** Ingest independent contemporaneous reporting on civic breakdowns, protests, municipal negligence, public health emergencies, and infrastructure repairs.
- **Source URL:**
  - Major Tamil Dailies: Dinamalar ([https://www.dinamalar.com/](https://www.dinamalar.com/)), Dinamani ([https://www.dinamani.com/](https://www.dinamani.com/)), Hindu Tamil Thisai ([https://www.hindutamil.in/](https://www.hindutamil.in/)).
  - Major English Dailies: The Hindu ([https://www.thehindu.com/](https://www.thehindu.com/)), Times of India Chennai, DT Next.
- **Expected Format:** HTML articles, RSS news feeds, structured JSON payloads.
- **Required Fields:**
  - `article_id`: Unique article ID from Phase 4 news pipeline.
  - `headline`: Article title.
  - `publication_name`: Media outlet.
  - `published_date`: Timestamp of reporting.
  - `district_name`: Mentioned district.
  - `civic_category`: Extracted category (`ROADS`, `WATER_SUPPLY`, `DRAINAGE`, etc.).
  - `content_snippet`: Verbatim passage describing the civic failure or repair work.
  - `url`: Canonical article URL.
- **Geographic and Date Coverage:** Tamil Nadu statewide; 2021 – Present.
- **Access Restrictions:** Public news websites subject to fair-use civic analysis and web scraper etiquette.
- **Availability Status:** High daily availability.
- **Collection Method:** Ingested via existing Phase 4 news scraping framework (`backend/acquisition/news_scraper_framework.py`).
- **Validation Method:** Outlet cross-referencing and bilingual Named Entity Recognition.
- **Known Limitations:** Media coverage is naturally skewed toward urban centers (Chennai, Coimbatore) compared to rural panchayats.

---

### 2.10 Existing Scheme, Promise, Representative, and Claim Records
- **Purpose:** Provide relational cross-linkages to ground-truth entities from Phases 1 through 7, anchoring civic issues into broad democratic accountability.
- **Source Entities:**
  - `Scheme` (Phase 1 & 2): Welfare and basic amenity schemes (e.g., Jal Jeevan Mission, Singara Chennai 2.0).
  - `Promise` (Phase 3): Manifesto commitments related to civic infrastructure.
  - `Representative` & `ConstituencyWork` (Phase 6): MLACDS / MPLADS works in the affected jurisdiction.
  - `Claim` (Phase 7): Political statements asserting infrastructure delivery or denying civic crises.
- **Expected Format:** Internal PostgreSQL / SQLite ORM relational queries.
- **Required Fields:**
  - `linked_entity_type`: `SCHEME`, `PROMISE`, `CONSTITUENCY_WORK`, `CLAIM`.
  - `linked_entity_id`: Foreign key reference.
  - `relationship_nature`: `DIRECT_MATCH`, `REMEDIATING_PROJECT`, `EVIDENCE_SOURCE`.
- **Geographic and Date Coverage:** Internal database records spanning 2011 to Present.
- **Access Restrictions:** Internal database access.
- **Availability Status:** Fully available and active within CIVICLENS repository.
- **Collection Method:** SQLAlchemy foreign key bindings and semantic search queries.
- **Validation Method:** Relational integrity checks and foreign key constraints.
- **Known Limitations:** None; internal schema is fully typed and validated.

---

## 3. Data Governance & Privacy Checklist

1. **No PII Persistence:** Citizen telephone numbers, Aadhaar/EPIC tokens, email addresses, and residential door numbers are rigorously stripped by `sanitize_pii()` prior to insertion.
2. **Provenance Traceability:** Every `SourceDocument` and record retains source URLs, acquisition dates, and SHA-256 cryptographic hashes.
3. **Audit Readiness:** All test fixtures are marked with `is_test_fixture=True` and segregated into `tests/fixtures/phase8_fixtures.py`.
