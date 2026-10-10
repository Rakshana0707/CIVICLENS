# Phase 6 — Representative Performance & Constituency Development Dataset Requirements

## 1. Overview & Data Strategy

Phase 6 of **CIVICLENS TN** requires 11 distinct datasets to evaluate Members of the Legislative Assembly (MLAs) and Members of Parliament (MPs representing Tamil Nadu).

The data strategy encompasses state assembly proceedings, parliamentary logs, statutory election returns, local area development expenditure portals (MPLADS/MLACDS), district statistical handbooks, census figures, and cross-phase integrated data (Phase 3 political promises, Phase 4 news coverage, Phase 5 political finance).

> [!IMPORTANT]
> **Data Availability Principle:** Data availability varies across institutional portals and election terms. The pipeline is designed to handle missing or delayed data without imputing fake values or guessing metrics. Availability status, access restrictions, and known limitations must be recorded for every dataset.

---

## 2. Exhaustive Dataset Specifications

### 2.1 Representative Profiles & Constituency Mapping
- **Purpose:** Establish master profiles for all elected representatives (MLAs, Lok Sabha MPs, Rajya Sabha MPs from TN) and map Assembly Constituencies (234) and Parliamentary Constituencies (39) with delimitation boundaries.
- **Official Source URL:** [https://www.eci.gov.in/](https://www.eci.gov.in/) & [https://www.assembly.tn.gov.in/](https://www.assembly.tn.gov.in/)
- **Expected Format:** HTML web tables, PDF official handbooks, and GeoJSON boundaries.
- **Fields Required:**
  - `representative_id`: Unique identifier (e.g. `REP-TN-001`).
  - `full_name_en`: Representative name in English.
  - `full_name_ta`: Representative name in Tamil.
  - `constituency_id`: Foreign key to `Constituency` (e.g. `AC-025`, `PC-12`).
  - `party_code`: Party abbreviation (`DMK`, `AIADMK`, `INC`, `BJP`, `PMK`, `VCK`, `NTK`, `IND`).
  - `house_type`: `TN_ASSEMBLY`, `LOK_SABHA`, `RAJYA_SABHA`.
  - `reservation_status`: `GENERAL`, `SC`, `ST`.
  - `educational_qualification`: Disclosed educational attainment.
  - `profession`: Main occupation/profession.
  - `contact_details`: Public office address and email.
- **Geographic Coverage:** State of Tamil Nadu (234 Assembly Constituencies, 39 Lok Sabha Constituencies, 18 Rajya Sabha seats).
- **Reporting Period:** 2011 – Present (covering 14th, 15th, and 16th TN Assembly; 16th, 17th, and 18th Lok Sabha).
- **Availability Status:** Available. Complete official profiles published on Assembly and ECI websites.
- **Access Restrictions:** Open public web pages; requires HTML parsing and PDF text extraction.
- **Known Limitations:** Discrepancies in Tamil to English name spellings across different official releases.

---

### 2.2 Election Results & Representative Terms
- **Purpose:** Ingest statutory election results, voter turnouts, candidate vote totals, win margins, and tenure start/end dates.
- **Official Source URL:** [https://results.eci.gov.in/](https://results.eci.gov.in/) & [https://www.eci.gov.in/statistical-report](https://www.eci.gov.in/statistical-report)
- **Expected Format:** CSV datasets, HTML result sheets, and PDF statistical reports.
- **Fields Required:**
  - `election_id`: Unique election code (e.g. `TN_ASSEMBLY_2021`).
  - `constituency_id`: Target constituency.
  - `candidate_name`: Name of candidate.
  - `party_code`: Contesting party.
  - `votes_polled`: Absolute number of votes received.
  - `vote_share_percent`: Percentage of total valid votes polled.
  - `win_margin_votes`: Vote difference between 1st and 2nd position candidates.
  - `win_margin_percent`: Margin percentage over runner-up.
  - `total_electors`: Total registered voters in constituency.
  - `voter_turnout_percent`: Constituency voter turnout percentage.
  - `term_start_date`: Swearing-in / election date.
  - `term_end_date`: Dissolution / tenure end date.
- **Geographic Coverage:** All 234 Assembly and 39 Parliamentary Constituencies in Tamil Nadu.
- **Reporting Period:** Tamil Nadu Assembly Elections (2011, 2016, 2021); Lok Sabha Elections (2014, 2019, 2024).
- **Availability Status:** Available. ECI publishes full statistical returns for all past general elections.
- **Access Restrictions:** Open Public Access (ECI Public Domain).
- **Known Limitations:** By-election result tables are published separately from general election statistical returns.

---

### 2.3 Parliamentary Questions & Participation (MPs)
- **Purpose:** Track Lok Sabha and Rajya Sabha participation for Tamil Nadu MPs, including questions asked, debate interventions, private member bills, and session attendance.
- **Official Source URL:** [https://sansad.in/](https://sansad.in/) & [https://prsindia.org/](https://prsindia.org/)
- **Expected Format:** XML feeds, HTML detail pages, and CSV exports from PRS India / Sansad portal.
- **Fields Required:**
  - `activity_id`: Unique activity identifier.
  - `mp_name`: Name of MP.
  - `constituency_name`: Parliamentary constituency.
  - `house`: `LOK_SABHA` or `RAJYA_SABHA`.
  - `activity_type`: `QUESTION_STARRED`, `QUESTION_UNSTARRED`, `DEBATE`, `BILL_INTRODUCED`, `ATTENDANCE`.
  - `session_number`: Parliament session number.
  - `date`: Activity date.
  - `subject`: Question or debate title.
  - `ministry`: Target central ministry.
  - `text_content`: Text of question and official reply / speech transcript.
  - `attendance_percent`: Aggregate session attendance percentage.
- **Geographic Coverage:** 39 Lok Sabha Constituencies and 18 Rajya Sabha Seats from Tamil Nadu.
- **Reporting Period:** 16th Lok Sabha (2014–2019), 17th Lok Sabha (2019–2024), 18th Lok Sabha (2024–Present).
- **Availability Status:** Available. Sansad portal and PRS India maintain structured logs of parliamentary activity.
- **Access Restrictions:** Public Web Access; Sansad portal applies Cloudflare rate-limiting requiring polite scraping intervals.
- **Known Limitations:** Attendance records are not signed when MPs are on official committee tours or parliamentary delegations.

---

### 2.4 Tamil Nadu Assembly Proceedings (MLAs)
- **Purpose:** Capture Tamil Nadu Legislative Assembly (TNLA) proceedings, questions raised during Question Hour, call attention motions, budget debate speeches, and attendance logs for MLAs.
- **Official Source URL:** [https://www.assembly.tn.gov.in/](https://www.assembly.tn.gov.in/)
- **Expected Format:** PDF Official Assembly Proceedings (Hansard/Synopsis in Tamil and English).
- **Fields Required:**
  - `activity_id`: Unique assembly activity code.
  - `mla_name`: Name of MLA.
  - `constituency_id`: Assembly constituency.
  - `assembly_term`: e.g., `16th Assembly`.
  - `session_number`: Session and meeting number.
  - `activity_date`: Date of sitting.
  - `activity_type`: `QUESTION_STARRED`, `QUESTION_UNSTARRED`, `CALL_ATTENTION`, `BUDGET_SPEECH`, `ZERO_HOUR_MENTION`.
  - `department_target`: State government department targeted.
  - `subject_ta`: Tamil title of speech or question.
  - `transcript_ta`: Tamil text of question/speech.
- **Geographic Coverage:** 234 Assembly Constituencies in Tamil Nadu.
- **Reporting Period:** 14th Assembly (2011–2016), 15th Assembly (2016–2021), 16th Assembly (2021–Present).
- **Availability Status:** Partial / Requires Extraction. Daily proceedings published as PDF files; unstructured layout requires NLP segmentation.
- **Access Restrictions:** Statutory Public Records on Assembly web server.
- **Known Limitations:** Scanned Tamil PDF transcripts require layout-aware OCR and Tamil NLP processing.

---

### 2.5 MPLADS & MLACDS Works, Releases, & Expenditure
- **Purpose:** Record fund allocations, releases, sanctioned projects, financial expenditure, and project completion status under MPLADS (₹5 Crore/year per MP) and MLACDS (₹3 Crore/year per MLA).
- **Official Source URL:** [https://mplads.gov.in/](https://mplads.gov.in/) & TN Rural Development Department MLACDS Guidelines.
- **Expected Format:** HTML table reports, CSV project releases, and PDF district collector expenditure returns.
- **Fields Required:**
  - `work_id`: Unique project identifier.
  - `representative_id`: MP or MLA code.
  - `constituency_id`: Target constituency.
  - `scheme_type`: `MPLADS` or `MLACDS`.
  - `financial_year`: Financial year (e.g. `2022-23`).
  - `entitlement_inr`: Total entitlement amount.
  - `released_amount_inr`: Funds released by Ministry / State Finance.
  - `sanctioned_amount_inr`: Amount sanctioned by District Nodal Authority.
  - `expenditure_inr`: Actual expenditure incurred.
  - `unspent_balance_inr`: Available unspent funds.
  - `work_description`: Name and category of physical asset (school, road, water tank).
  - `work_status`: `RECOMMENDED`, `SANCTIONED`, `IN_PROGRESS`, `COMPLETED`, `CANCELLED`.
  - `completion_date`: Date of physical completion.
- **Geographic Coverage:** All 39 Parliamentary Constituencies and 234 Assembly Constituencies in Tamil Nadu.
- **Reporting Period:** FY 2014-15 through FY 2024-25.
- **Availability Status:** Partial / Dynamic Portal. MPLADS portal provides online constituency reports; MLACDS data requires district-level aggregation.
- **Access Restrictions:** Public Portal Access; portal updates periodically.
- **Known Limitations:** MPLADS funding was suspended during FY 2020-21 due to COVID-19 pandemic reallocation.

---

### 2.6 Government Schemes & Budget Allocations
- **Purpose:** Ingest district and constituency disaggregated state budget allocations and flagship government scheme implementation metrics (reused from Phase 1 and Phase 2).
- **Official Source URL:** [https://www.tnbudget.tn.gov.in/](https://www.tnbudget.tn.gov.in/) & [https://www.data.gov.in/](https://www.data.gov.in/)
- **Expected Format:** PDF Budget Documents (Detailed Demands for Grants), CSV open datasets, and JSON API payloads.
- **Fields Required:**
  - `scheme_id`: Foreign key to `BudgetScheme` / `GovernmentScheme`.
  - `department_id`: Foreign key to `BudgetDepartment`.
  - `district_id`: Target district / constituency.
  - `financial_year`: Budget financial year.
  - `budget_estimate_inr`: Allocated budget amount.
  - `revised_estimate_inr`: Revised allocation.
  - `actual_expenditure_inr`: Actual financial spending.
  - `beneficiaries_count`: Targeted or reached beneficiary count.
- **Geographic Coverage:** 38 Districts of Tamil Nadu.
- **Reporting Period:** FY 2011-12 through FY 2024-25.
- **Availability Status:** Available. Integrated from Phase 1 State Budget Database (`backend/models/budget.py`).
- **Access Restrictions:** Open Government Data (Public Domain).
- **Known Limitations:** State budget line items are primary reported at department/district level rather than individual assembly constituency level.

---

### 2.7 Constituency & District Development Indicators
- **Purpose:** Track socioeconomic development indicators (literacy rate, healthcare infrastructure, water supply coverage, rural road density, female labor participation, electricity access) to evaluate constituency developmental trajectories.
- **Official Source URL:** [https://www.data.gov.in/](https://www.data.gov.in/), Tamil Nadu Department of Economics & Statistics (DES), and NITI Aayog Aspirational Districts.
- **Expected Format:** Excel files, CSV tables, and PDF District Statistical Handbooks.
- **Fields Required:**
  - `indicator_id`: Primary key identifier.
  - `district_name`: Target district name.
  - `constituency_id`: Linked constituency (where mapping exists).
  - `indicator_code`: e.g. `LITERACY_RATE`, `INFANT_MORTALITY`, `TAP_WATER_PCT`, `ROAD_DENSITY`.
  - `category`: `EDUCATION`, `HEALTH`, `INFRASTRUCTURE`, `WATER_SANITATION`, `POVERTY`.
  - `baseline_value`: Value at start of reference term.
  - `current_value`: Latest recorded indicator value.
  - `unit`: Percent, Ratio, Count, Kilometers.
  - `reference_year`: Data collection year.
- **Geographic Coverage:** All 38 Districts and 234 Constituencies in Tamil Nadu.
- **Reporting Period:** 2011 – 2024.
- **Availability Status:** Available / Disaggregated. Available at district level; requires constituency proportion weighting for constituency-level estimation.
- **Access Restrictions:** Open Public Data (DES TN & Data.gov.in).
- **Known Limitations:** Socioeconomic indicators are officially published at district and taluk levels, requiring spatial interpolation for assembly constituencies.

---

### 2.8 Census & Demographic Data
- **Purpose:** Establish baseline demographic figures, population counts, SC/ST percentages, gender ratios, literacy baseline, and urban/rural distribution per constituency.
- **Official Source URL:** [https://censusindia.gov.in/](https://censusindia.gov.in/)
- **Expected Format:** Excel spreadsheets, CSV files, and Delimitation Commission 2008 gazette notifications.
- **Fields Required:**
  - `constituency_id`: Foreign key to `Constituency`.
  - `total_population`: Total census population.
  - `male_population`: Male population count.
  - `female_population`: Female population count.
  - `sc_population`: Scheduled Caste population.
  - `st_population`: Scheduled Tribe population.
  - `rural_population_pct`: Percentage of rural population.
  - `urban_population_pct`: Percentage of urban population.
  - `baseline_literacy_rate`: Census 2011 literacy rate.
  - `working_population`: Total main and marginal workers count.
- **Geographic Coverage:** All 234 Assembly and 39 Parliamentary Constituencies in Tamil Nadu.
- **Reporting Period:** Census 2011 (with official projected demographic updates for 2021-2024).
- **Availability Status:** Available. Benchmark census data is complete.
- **Access Restrictions:** Open Public Access (Registrar General of India).
- **Known Limitations:** Decennial Census 2021 was delayed; projections are based on official Registrar General population estimation models.

---

### 2.9 Existing Phase 3 Political Promises
- **Purpose:** Ingest structured political manifesto promises from Phase 3 (`backend/models/promise.py`) to measure alignment between representative questions/works and their party's declared commitments.
- **Official Source URL:** Integrated Internal Phase 3 Module (`backend/models/promise.py`).
- **Expected Format:** SQLAlchemy ORM database queries / JSON internal schema.
- **Fields Required:**
  - `promise_id`: Foreign key to `PoliticalPromise`.
  - `party_id`: Foreign key to `PoliticalParty`.
  - `promise_text_en`: Promise statement in English.
  - `promise_text_ta`: Promise statement in Tamil.
  - `category_id`: Promise theme category (`AGRICULTURE`, `EDUCATION`, `HEALTH`, `INFRASTRUCTURE`, `JOBS`).
  - `target_region`: Specific district/constituency or statewide.
  - `fulfillment_status`: Evaluated status (`FULFILLED`, `IN_PROGRESS`, `BROKEN`, `UNASSESSED`).
- **Geographic Coverage:** State of Tamil Nadu.
- **Reporting Period:** 2016 TN Election Manifestos, 2021 TN Election Manifestos, 2024 Lok Sabha Manifestos.
- **Availability Status:** Fully Available (Integrated Phase 3 Database).
- **Access Restrictions:** Internal Database Access.
- **Known Limitations:** Manifesto promises are frequently stated at state level rather than assigned to specific local representatives.

---

### 2.10 Existing Phase 4 News Coverage & Sentiment
- **Purpose:** Ingest news articles, media mentions, topic distributions, and sentiment indicators from Phase 4 (`backend/models/news.py`) to assess representative constituency issue visibility.
- **Official Source URL:** Integrated Internal Phase 4 Module (`backend/models/news.py`).
- **Expected Format:** SQLAlchemy ORM database queries (`Article`, `ArticleEntity`, `CoverageMetric`, `BiasIndicator`).
- **Fields Required:**
  - `article_id`: Foreign key to `Article`.
  - `person_id`: Foreign key to `PoliticalPerson` / `Representative`.
  - `party_id`: Foreign key to `PoliticalParty`.
  - `constituency_mention`: Detected constituency name.
  - `topic_code`: Identified news topic code.
  - `mentions_count`: Number of entity mentions in article.
  - `sentiment_score`: Extracted sentiment (-1.0 to +1.0).
  - `publication_date`: Article date.
- **Geographic Coverage:** Tamil Nadu media publications (English and Tamil news outlets).
- **Reporting Period:** 2021 – Present.
- **Availability Status:** Fully Available (Integrated Phase 4 Database).
- **Access Restrictions:** Internal Database Access.
- **Known Limitations:** Media coverage favors high-profile ministers and party leaders over backbench MLAs from rural constituencies.

---

### 2.11 Existing Phase 5 Financial Transparency Indicators
- **Purpose:** Cross-reference representative financial affidavits, campaign expenditures, and party donation patterns from Phase 5 (`backend/models/funding.py`) against constituency development fund utilization.
- **Official Source URL:** Integrated Internal Phase 5 Module (`backend/models/funding.py`).
- **Expected Format:** SQLAlchemy ORM database queries (`ElectionExpenditure`, `Contribution`, `PartyFinancialStatement`).
- **Fields Required:**
  - `expenditure_id`: Foreign key to `ElectionExpenditure`.
  - `party_id`: Contesting party.
  - `candidate_name`: Representative candidate name.
  - `election_name`: Target election cycle.
  - `publicity_expenditure`: Declared advertising spending.
  - `travel_expenditure`: Star campaigner travel spending.
  - `total_election_expenditure`: Gross declared campaign spending.
- **Geographic Coverage:** Tamil Nadu.
- **Reporting Period:** Assembly Elections 2016, 2021; Lok Sabha 2019, 2024.
- **Availability Status:** Fully Available (Integrated Phase 5 Database).
- **Access Restrictions:** Internal Database Access.
- **Known Limitations:** Candidate individual expenditure disclosures are capped by ECI statutory limits, whereas party central expenditures are reported separately.

---

## 3. Dataset Summary Matrix

| Dataset ID | Dataset Name | Official Source URL | Format | Availability Status | Primary Access Method |
|---|---|---|---|---|---|
| `DS-601` | Representative Profiles & Mapping | [eci.gov.in](https://www.eci.gov.in/) / [assembly.tn.gov.in](https://www.assembly.tn.gov.in/) | HTML / PDF / GeoJSON | Available | Web Scraper & GeoJSON Loader |
| `DS-602` | Election Results & Terms | [results.eci.gov.in](https://results.eci.gov.in/) | CSV / HTML | Available | CSV Ingestion Engine |
| `DS-603` | Parliamentary Questions (MPs) | [sansad.in](https://sansad.in/) / [prsindia.org](https://prsindia.org/) | XML / CSV / HTML | Available | API & XML Parser |
| `DS-604` | TN Assembly Proceedings (MLAs) | [assembly.tn.gov.in](https://www.assembly.tn.gov.in/) | PDF | Partial / Extraction | PDF Layout & Tamil OCR Parser |
| `DS-605` | MPLADS / MLACDS Works | [mplads.gov.in](https://mplads.gov.in/) | HTML / CSV / PDF | Partial / Dynamic Portal | Web Scraper & PDF Schedule Parser |
| `DS-606` | Govt Schemes & Budget | [tnbudget.tn.gov.in](https://www.tnbudget.tn.gov.in/) | PDF / CSV | Available | Integrated Phase 1 & 2 DB |
| `DS-607` | Constituency Development Indicators | [data.gov.in](https://www.data.gov.in/) / DES TN | CSV / Excel / PDF | Available / Disaggregated | Table Parser & District Mapping |
| `DS-608` | Census & Demographic Data | [censusindia.gov.in](https://censusindia.gov.in/) | Excel / CSV | Available | Direct CSV Importer |
| `DS-609` | Political Promises (Phase 3) | Internal Phase 3 Module | ORM DB | Fully Available | Internal DB Query |
| `DS-610` | News Coverage & Sentiment (Phase 4) | Internal Phase 4 Module | ORM DB | Fully Available | Internal DB Query |
| `DS-611` | Financial Transparency (Phase 5) | Internal Phase 5 Module | ORM DB | Fully Available | Internal DB Query |
