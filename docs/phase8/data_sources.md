# Phase 8 — Public Grievance & Civic Issue Data Sources Inventory & Quality Matrix

## 1. Overview & Institutional Tiering

This document establishes the inventory, accessibility credentials, update cadences, and reliability hierarchy for datasets powering the **CIVICLENS TN** Public Grievance & Civic Issue Intelligence System.

To guarantee scientific objectivity, auditability, and non-partisanship, sources are organized across **5 Source Tiers**:

- **Tier 1 (Statutory, Gazette & Legislative Authorities):** Tamil Nadu Government Gazette (Stationery & Printing), Citizen's Charters published under statutory powers, Tamil Nadu Legislative Assembly Proceedings and Assurances Committee Reports, Local Government Directory (LGD), and Comptroller and Auditor General (CAG) performance audits.
- **Tier 2 (State & Central Executive Departments):** TNeGA ("Mudhalvarin Mugavari" / IIPGCMS), DARPG (CPGRAMS), Directorate of Information and Public Relations (DIPR), Department of Economics & Statistics (DES TN), Open Government Data India (data.gov.in).
- **Tier 3 (Urban Local Bodies & Municipal Corporations):** Greater Chennai Corporation (GCC), Coimbatore City Municipal Corporation (CCMC), Madurai City Municipal Corporation, Directorate of Municipal Administration (DMA), Tamil Nadu Water Supply and Drainage Board (TWAD), Chennai MetroWater (CMWSSB).
- **Tier 4 (Accredited Civic Journalism & Media of Record):** Leading newspapers of record (The Hindu, Dinamalar, Dinamani, Hindu Tamil Thisai, Times of India Chennai) reporting localized civic breakdowns and ground investigations.
- **Tier 5 (Public Citizen Grievances & Community Logs):** Individual citizen petitions, resident welfare association (RWA) complaints, and civic advocacy submissions (subject of classification and tracking; strictly anonymized; requires corroborating evidence before marking as verified resolution).

---

## 2. Comprehensive Source Inventory

### 2.1 Department of Administrative Reforms and Public Grievances (DARPG) — CPGRAMS
- **Portal URL:** [https://pgportal.gov.in/](https://pgportal.gov.in/) & [https://darpg.gov.in/](https://darpg.gov.in/)
- **Source Tier:** Tier 2 (Central Executive Grievance Repository)
- **Data Types:** Monthly Public Grievance Progress Reports, state-wise receipt & disposal figures, grievance redressal index (GRI), disposal aging analysis.
- **Formats:** PDF Monthly Reports, HTML aggregate dashboard views.
- **Update Frequency:** Monthly.
- **Accessibility & Gate Status:** Verified accessible via HTTPS. Citizen petition filing and personal case status tracking are gated by citizen mobile OTP. Public monthly bulletins and aggregate state rankings are completely open.
- **Collection Strategy:** Scheduled scraper targeting `darpg.gov.in/monthly-reports` to harvest monthly state summary bulletins; automated table extraction via `pdfplumber`.
- **Privacy Safeguards:** Ingests only state-level and ministry-level aggregate numbers. Zero individual complainant information is accessed or collected.

---

### 2.2 Tamil Nadu e-Governance Agency (TNeGA) — "Mudhalvarin Mugavari" (IIPGCMS)
- **Portal URL:** [https://cmhelpline.tnega.org/portal/en/home](https://cmhelpline.tnega.org/portal/en/home) & [https://tnega.tn.gov.in/](https://tnega.tn.gov.in/)
- **Source Tier:** Tier 2 (State Executive Consolidated Grievance System)
- **Data Types:** Integrated grievance portal metadata, 43 department mapping registries, procedural escalation rules, FAQ articles, and state grievance redressal performance releases.
- **Formats:** Portal JSON configuration manifests, FAQ HTML articles, DIPR press bulletins.
- **Update Frequency:** Daily / Weekly announcements.
- **Accessibility & Gate Status:** Verified accessible via HTTPS. Front-end is backed by Zoho Desk (`cmhelpline.tnega.org`). Individual petition lodging and tracking requires citizen **Mobile OTP authentication** (`loginIdentifiers: ["MOBILE"]`). No unauthenticated bulk API exists.
- **Collection Strategy:** Static harvesting of departmental IDs, published citizen charter turnaround rules, and periodic ingestion of DIPR official press releases summarizing CM Helpline disposal volumes.
- **Privacy Safeguards:** No attempt is made to bypass OTP gates or scrape private citizen petitions. All intake is confined to statutory public documentation and official press announcements.

---

### 2.3 Government of Tamil Nadu Official Portal & DIPR
- **Portal URL:** [https://www.tn.gov.in/](https://www.tn.gov.in/) & [https://dipr.tn.gov.in/](https://dipr.tn.gov.in/)
- **Source Tier:** Tier 1 / Tier 2 (State Executive Gazettes and Orders)
- **Data Types:** Government Orders (G.O. Ms.), Department Policy Notes, Citizen's Charters, District Collectorate administrative circulars.
- **Formats:** PDF documents, searchable text PDFs, HTML releases in Tamil and English.
- **Update Frequency:** Continuous / Daily.
- **Accessibility & Gate Status:** Verified open public access.
- **Collection Strategy:** Scheduled crawler targeting `dipr.tn.gov.in/press-release` and department citizen charter repositories.
- **Privacy Safeguards:** SHA-256 fingerprinting of all source documents; sanitization of citizen petitioner references if cited in gazetted case orders.

---

### 2.4 Greater Chennai Corporation (GCC)
- **Portal URL:** [https://chennaicorporation.gov.in/gcc/](https://chennaicorporation.gov.in/gcc/)
- **Source Tier:** Tier 3 (Urban Local Body / Municipal Corporation)
- **Data Types:** Corporation Council meeting resolutions, works tenders, zonal boundaries (15 zones), ward directories (200 wards), 1913 helpline procedural standards.
- **Formats:** HTML pages, PDF council agenda papers, tender schedules.
- **Update Frequency:** Monthly council proceedings, daily tender postings.
- **Accessibility & Gate Status:** Verified accessible via HTTPS. Base URL redirects to `/gcc/`. Public sections (council resolutions, ward lists, tender notices) are open. Individual complaint filing on Namma Chennai requires mobile authentication.
- **Collection Strategy:** Scrape public council minutes, tender releases, and ward directories.
- **Privacy Safeguards:** Strictly ignore individual citizen complainant contact records; focus exclusively on ward-level civic works, resolutions, and aggregate complaint volumes.

---

### 2.5 Directorate of Municipal Administration (DMA) & Urban Local Bodies
- **Portal URL:** [https://tn.gov.in/dma/](https://tn.gov.in/dma/)
- **Source Tier:** Tier 3 (State Urban Local Body Directorate)
- **Data Types:** Performance reports for 21 Municipal Corporations, 138 Municipalities, and 490 Town Panchayats. Solid waste generation metrics, streetlighting coverage, underground drainage coverage.
- **Formats:** PDF Annual Administrative Reports, statistical tables.
- **Update Frequency:** Annual / Biannual.
- **Accessibility & Gate Status:** Open public government portal.
- **Collection Strategy:** Annual administrative report harvesting and tabular normalization.
- **Privacy Safeguards:** Municipal aggregate metrics only.

---

### 2.6 Tamil Nadu Tenders Portal (e-Procurement System)
- **Portal URL:** [https://tntenders.gov.in/](https://tntenders.gov.in/)
- **Source Tier:** Tier 1 (Statutory Public Procurement Record)
- **Data Types:** Civil works contracts, road repair tenders, stormwater drain construction, TWAD drinking water pipeline contracts, maintenance work orders.
- **Formats:** HTML tender notices, PDF bid evaluation summaries, contract award sheets.
- **Update Frequency:** Daily.
- **Accessibility & Gate Status:** Verified public domain under Tamil Nadu Transparency in Tenders Act, 1998. Public searches accessible without login.
- **Collection Strategy:** Scheduled scraper targeting civil works categories with exponential backoff and rate limiting.
- **Quality Role:** Acts as primary corroborating evidence for validating whether reported civic issues (e.g. road damage or drainage overflow) have received genuine government remediation work.

---

### 2.7 Open Government Data (OGD) Platform India & DES Tamil Nadu
- **Portal URL:** [https://www.data.gov.in/](https://www.data.gov.in/) & [https://www.tn.gov.in/des/](https://www.tn.gov.in/des/)
- **Source Tier:** Tier 2 (National & State Statistical Repositories)
- **Data Types:** District-level infrastructure benchmarks, potable drinking water coverage, rural sanitation metrics, electricity feeder metrics.
- **Formats:** REST JSON APIs, CSV and XLSX downloads.
- **Update Frequency:** Monthly to Annual.
- **Accessibility & Gate Status:** Open public access via registered API key.
- **Collection Strategy:** Automated ingestion using registered OGD API client; normalization into `backend/models/civic_issue.py` tables.
- **Privacy Safeguards:** Completely anonymized spatial census and survey data.

---

### 2.8 Local Government Directory (LGD) — Ministry of Panchayati Raj
- **Portal URL:** [https://lgd.gov.in/](https://lgd.gov.in/)
- **Source Tier:** Tier 1 (Constitutional Spatial Hierarchy Authority)
- **Data Types:** Standardized LGD codes for all 38 Tamil Nadu districts, 312 taluks, 388 revenue blocks, municipal corporations, municipalities, and village panchayats.
- **Formats:** CSV, XLSX, XML directory dumps.
- **Update Frequency:** Real-time upon state gazette re-demarcation.
- **Accessibility & Gate Status:** Open public domain directory.
- **Collection Strategy:** Ingest official Tamil Nadu LGD dump to establish immutable primary keys for `AdministrativeArea`.
- **Quality Role:** Prevents name spelling ambiguities (e.g., "Tiruchirappalli" vs. "Trichy", "Kanchipuram" vs. "Kancheepuram") across all civic models.

---

### 2.9 Accredited News Outlets (Civic & Hyperlocal Desks)
- **Outlets:** The Hindu, Dinamalar, Dinamani, Hindu Tamil Thisai.
- **Source Tier:** Tier 4 (Accredited Civic Journalism)
- **Data Types:** Field reports on civic failures, citizen protests against municipal apathy, public health notices (e.g., water contamination), and infrastructure inaugurations.
- **Formats:** HTML articles, RSS feeds.
- **Update Frequency:** Daily.
- **Accessibility & Gate Status:** Public web pages accessible via polite scraping.
- **Collection Strategy:** Reuses existing Phase 4 news acquisition pipeline (`backend/acquisition/news_scraper_framework.py`).
- **Privacy Safeguards:** PII redaction filter applied to names and personal details of citizens interviewed in news stories.

---

## 3. Source Quality & Independence Scoring Matrix

Every ingested document or civic metric is scored across 4 objective quality dimensions:

| Dimension | Description | Weight |
|:---|:---|:---:|
| **Institutional Authority ($S_{auth}$)** | Degree of statutory mandate (Tier 1 = 1.0, Tier 2 = 0.85, Tier 3 = 0.70, Tier 4 = 0.50, Tier 5 = 0.30) | 35% |
| **Direct Verifiability ($S_{verif}$)** | Presence of verifiable tender ID, G.O. number, geo-coordinates, or work order | 30% |
| **Temporal Proximity ($S_{temp}$)** | Freshness of data relative to the incident date (decay factor for obsolete reports) | 20% |
| **Source Independence ($S_{indep}$)** | Separation between reporting entity and executing agency (e.g., independent news vs self-serving departmental claim) | 15% |

$$\text{Composite Quality Score} = 0.35 S_{auth} + 0.30 S_{verif} + 0.20 S_{temp} + 0.15 S_{indep}$$

This mathematical index ensures that self-reported departmental closures that lack independent verification or tender corroboration are clearly tagged as unverified.
