# Phase 7 — Political Claim Verification & Evidence Intelligence Dataset Requirements

## 1. Overview & Data Strategy

Phase 7 of **CIVICLENS TN** introduces the **Political Claim Verification & Evidence Intelligence** module. Its mission is to rigorously evaluate public statements, electoral assertions, policy announcements, and political arguments made in Tamil Nadu using empirical, multi-source evidence.

The real Phase 7 datasets have **NOT** been collected yet. In accordance with project engineering principles, the pipeline, schemas, verification methodology, and quality controls are designed and validated prior to large-scale data harvesting.

> [!IMPORTANT]
> **Data Integrity & Non-Fabrication Rule:**
> CIVICLENS TN never invents or synthesizes real-world statements as genuine historical records. All test fixtures are strictly segregated in `tests/fixtures/phase7_fixtures.py` and tagged with `is_test_fixture=True`. Real collection pipelines will only ingest verified statutory records, official transcripts, and authenticated publications.

---

## 2. Exhaustive Dataset Specifications

The claim verification pipeline requires 10 distinct categories of datasets spanning public statements, official government records, election statistics, legislative activity, financial filings, and cross-outlet media reporting.

### 2.1 Public Political Claims and Statements
- **Purpose:** Serve as primary claim intake records. Captures public political statements made in speeches, press conferences, official party manifestos, social media broadcasts, and interviews.
- **Source URL:** Speeches and press releases from recognized political parties (DMK, AIADMK, BJP TN, INC TN, PMK, VCK, NTK); verified party YouTube/X transcripts; press meet recordings; public rallies.
- **Expected Formats:** Text transcripts, JSON structured statements, timestamped audio/video transcripts, HTML press releases.
- **Relevant Fields:**
  - `claim_id`: Unique identifier (e.g. `CLM-2024-001`).
  - `speaker_name`: Identity of speaker / politician.
  - `speaker_party`: Political party affiliation at the time of utterance.
  - `statement_text`: Verbatim original text (Tamil, English, or bilingual).
  - `context_text`: Surrounding speech passage or dialogue context.
  - `statement_date`: Date and time of utterance.
  - `medium`: Medium of publication (`PRESS_MEET`, `CAMPAIGN_RALLY`, `PRESS_RELEASE`, `INTERVIEW`, `SOCIAL_POST`).
  - `primary_source_url`: Verifiable URL of video, transcript, or official party publication.
  - `archive_url`: Permanent web archive / Wayback machine snapshot.
  - `claim_category`: Categorization code (e.g. `GOVERNMENT_SCHEMES`, `BUDGET_EXPENDITURE`).
- **Language:** Tamil (ta), English (en), Code-switched (ta-en).
- **Date Coverage:** 2016 – Present (covering 15th and 16th TN Assembly cycles, 2019 and 2024 General Elections).
- **Access Restrictions:** Open public domain, press statements, and public social media broadcasts. Subject to fair use civic analysis.
- **Collection Method:** Verified party press portal scrapers, RSS ingestion, speech-to-text transcription APIs, manual editorial intake.
- **Validation Method:** Multi-source attribution verification (matching at least two independent broadcast feeds or official party release).
- **Availability Status:** High availability across public party websites and media archives.
- **Known Limitations:** Transcripts from campaign rallies may exhibit acoustic noise, dialectal variants, or unofficial editorial translation differences.

---

### 2.2 Official Government Announcements and Press Releases
- **Purpose:** Provide primary statutory ground-truth for government policy launches, executive orders, Cabinet decisions, and official state releases.
- **Source URL:** 
  - Tamil Nadu Government Portal: [https://www.tn.gov.in/](https://www.tn.gov.in/)
  - Press Information Bureau (PIB Chennai / Delhi): [https://pib.gov.in/](https://pib.gov.in/)
  - Tamil Nadu DIPR (Directorate of Information and Public Relations): [https://dipr.tn.gov.in/](https://dipr.tn.gov.in/)
- **Expected Formats:** PDF government orders (G.O. Ms.), HTML press releases, bilingual press bulletins.
- **Relevant Fields:**
  - `announcement_id`: Unique government release ID (e.g. `GO-TN-FIN-2023-112`).
  - `issuing_department`: Department of Government (e.g., Finance, School Education).
  - `title`: Official title of order or release.
  - `order_number`: Formal G.O. Number (if executive order).
  - `release_date`: Date of gazetting or issuance.
  - `language`: `ta` or `en`.
  - `summary_content`: Extracted text of announcement.
  - `monetary_sanction_inr`: Exact sanctioned sum (if financial allocation).
  - `effective_date`: Date from which policy takes legal force.
  - `document_url`: Direct official portal URL.
  - `sha256_checksum`: Cryptographic fingerprint of source PDF.
- **Language:** Tamil and English (many G.O.s published bilingual or in English/Tamil).
- **Date Coverage:** 2011 – Present.
- **Access Restrictions:** Public Domain (Official Gazette and State Portal).
- **Collection Method:** Automated daily crawl of DIPR press releases and e-Gazette repository using polite rate limiting.
- **Validation Method:** Digital signature validation on PDFs, G.O. registry number format verification against departmental gazette.
- **Availability Status:** Available and actively published.
- **Known Limitations:** Older G.O. PDFs (pre-2016) are frequently scanned raster images requiring high-fidelity OCR.

---

### 2.3 Official Fact-Check Records
- **Purpose:** Monitor claims already addressed or clarified by official state and central fact-checking units to prevent redundant verification and detect official government rebuttals.
- **Source URL:**
  - PIB Fact Check: [https://factcheck.pib.gov.in/](https://factcheck.pib.gov.in/)
  - Tamil Nadu Fact Check Unit (FCU DIPR TN): Official state releases and verified channels.
- **Expected Formats:** HTML debunk articles, JSON API feeds, infographics with metadata.
- **Relevant Fields:**
  - `factcheck_id`: Identifier (e.g. `FC-PIB-2024-089`).
  - `claim_reviewed`: Exact viral assertion reviewed.
  - `official_verdict`: Government classification (`FAKE`, `MISLEADING`, `TRUE`, `UNOFFICIAL`).
  - `rebuttal_explanation`: Official clarification and cited government authority.
  - `publication_date`: Date fact-check published.
  - `evidence_sources`: Cited circulars, G.O. numbers, or ministry clarifications.
  - `source_url`: Official URL of fact-check post.
- **Language:** English, Tamil, Hindi.
- **Date Coverage:** 2019 – Present.
- **Access Restrictions:** Open public access.
- **Collection Method:** Scraper targeting factcheck.pib.gov.in archive and state FCU channels.
- **Validation Method:** Cross-validation of referenced government order against official state gazette.
- **Availability Status:** Moderately available; PIB archives are accessible, state unit archives fluctuate.
- **Known Limitations:** Official fact-checks exclusively address viral rumors or executive misrepresentations; they rarely verify broad political or statistical assertions made during parliamentary debates.

---

### 2.4 Election-Related Records
- **Purpose:** Serve as ground-truth for electoral claims regarding voter turnout, victory margins, rejected votes, candidate affidavits, and booth-level results.
- **Source URL:**
  - Election Commission of India: [https://www.eci.gov.in/](https://www.eci.gov.in/)
  - ECI Results Portal: [https://results.eci.gov.in/](https://results.eci.gov.in/)
  - CEO Tamil Nadu: [https://www.elections.tn.gov.in/](https://www.elections.tn.gov.in/)
- **Expected Formats:** CSV election tables, Form 20 booth-level Excel sheets, Form 21E declaration PDFs, statistical reports.
- **Relevant Fields:**
  - `election_id`: Code (e.g. `ECI-TN-2021-ASSEMBLY`).
  - `constituency_code`: Official AC/PC number.
  - `candidate_name`: Registered candidate name.
  - `party_name`: Party nomination.
  - `evm_votes`: Votes polled via EVM.
  - `postal_votes`: Postal ballot count.
  - `total_votes`: Total valid votes polled.
  - `margin_votes`: Difference between winner and runner-up.
  - `turnout_percent`: Official polled percentage.
  - `elector_count`: Registered electorate size.
  - `declaration_date`: Counting / declaration date.
- **Language:** English and Tamil.
- **Date Coverage:** General Elections 2011, 2014, 2016, 2019, 2021, 2024.
- **Access Restrictions:** Open Public Access (ECI Public Domain).
- **Collection Method:** Direct CSV download of statutory returns and OCR/parsing of Form 21E declaration returns.
- **Validation Method:** Integrity check ensuring EVM + Postal = Total; sum of candidate votes + NOTA = Total valid votes.
- **Availability Status:** Highly available. Complete historical results exist on ECI portal.
- **Known Limitations:** Form 20 polling station-level data is published as disparate scanned PDFs by District Election Officers (DEOs), requiring custom tabular parsing.

---

### 2.5 Legislative Documents
- **Purpose:** Verify claims concerning legislative attendance, questions raised, private member bills, assembly walkouts, and floor speeches in Parliament and the State Assembly.
- **Source URL:**
  - Sansad Portal (Lok Sabha & Rajya Sabha): [https://sansad.in/](https://sansad.in/)
  - Tamil Nadu Legislative Assembly: [https://www.assembly.tn.gov.in/](https://www.assembly.tn.gov.in/)
  - Digital Sansad Repository: Parliamentary debates and question databases.
- **Expected Formats:** XML question answers, PDF debate proceedings (Hansard), HTML synopsis.
- **Relevant Fields:**
  - `document_id`: Legislative record identifier (e.g. `TNLA-S16-2023-D14`).
  - `legislative_body`: `TN_ASSEMBLY`, `LOK_SABHA`, `RAJYA_SABHA`.
  - `session_id`: Session title / number.
  - `record_type`: `STARRED_QUESTION`, `UNSTARRED_QUESTION`, `DEBATE_TRANSCRIPT`, `BILL_TEXT`.
  - `question_number`: Formal question identifier (e.g. `Q.No 1402`).
  - `member_name`: Member asking or speaking.
  - `minister_responding`: Minister providing official answer.
  - `subject`: Parliamentary question title.
  - `question_text`: Verbatim text of question asked.
  - `answer_text`: Formal written/spoken government answer.
  - `activity_date`: Date entered into official record.
- **Language:** Tamil (Assembly proceedings) and English/Hindi (Sansad proceedings).
- **Date Coverage:** 2014 – Present.
- **Access Restrictions:** Public Domain.
- **Collection Method:** Ingestion via Sansad question search APIs and TN Assembly debate PDF download scripts.
- **Validation Method:** Reconciliation of question numbers against official session bulletin index.
- **Availability Status:** Lok Sabha/Rajya Sabha data is fully indexed; TN Assembly debates are available as scanned or text PDFs.
- **Known Limitations:** TN Assembly daily proceedings PDFs use specialized Tamil font encodings (Bilingual TAM/TAB or legacy fonts) requiring Unicode normalization.

---

### 2.6 Scheme, Budget, and Expenditure Documents
- **Purpose:** Verify quantitative and qualitative claims regarding government budgetary allocations, scheme funding, revised estimates, and actual disbursements.
- **Source URL:**
  - Tamil Nadu Budget Portal: [https://www.tnbudget.tn.gov.in/](https://www.tnbudget.tn.gov.in/)
  - Finance Department TN: [https://www.tn.gov.in/department/10](https://www.tn.gov.in/department/10)
  - CAG Audit Reports on State Finances: [https://cag.gov.in/](https://cag.gov.in/)
- **Expected Formats:** PDF Detailed Demands for Grants (DDG), Budget Speech PDFs, Financial Statement tables, CSV extracts.
- **Relevant Fields:**
  - `record_id`: Financial line item identifier.
  - `demand_number`: Demand for Grants code (e.g. `Demand 19`).
  - `department_name`: Administrative department.
  - `scheme_name`: Exact named scheme.
  - `head_of_account`: 15-digit accounting classification (Major, Minor, Sub-head).
  - `financial_year`: Budget year (e.g. `2023-2024`).
  - `budget_stage`: `BUDGET_ESTIMATE`, `REVISED_ESTIMATE`, `ACTUAL_EXPENDITURE`.
  - `amount_crores_inr`: Monetary amount normalized to ₹ Crores.
  - `source_document_id`: Reference to ingested DDG PDF.
- **Language:** English and Tamil.
- **Date Coverage:** FY 2016-17 to FY 2024-25.
- **Access Restrictions:** Open Public Access (State Government Budget Portal).
- **Collection Method:** Automated harvest of Demands for Grants PDFs, layout-aware tabular parsing, and cross-reference with Phase 1 repository.
- **Validation Method:** Reconcile demand-level totals against Annual Financial Statement aggregate totals.
- **Availability Status:** High availability; all budget books since 2018 are published online.
- **Known Limitations:** Actual expenditure numbers are published with a two-year statutory lag (e.g., FY 2024-25 budget contains actuals only up to FY 2022-23).

---

### 2.7 Public Statistical Datasets
- **Purpose:** Verify claims concerning demographic statistics, infant mortality, literacy, per capita income, electrification, road length, and health infrastructure.
- **Source URL:**
  - National Data and Analytics Platform (NDAP) / Data.gov.in: [https://www.data.gov.in/](https://www.data.gov.in/)
  - Tamil Nadu Department of Economics and Statistics (DES): [https://www.tn.gov.in/deptst/](https://www.tn.gov.in/deptst/)
  - RBI Handbook of Statistics on Indian States: [https://www.rbi.org.in/](https://www.rbi.org.in/)
  - NFHS (National Family Health Survey 4 & 5): [https://rchiips.org/nfhs/](https://rchiips.org/nfhs/)
- **Expected Formats:** CSV, XLSX, JSON datasets, statistical bulletin PDFs.
- **Relevant Fields:**
  - `indicator_code`: Statistical indicator code (e.g. `IMR_PER_1000`, `GSDP_GROWTH_PCT`).
  - `indicator_name`: Full descriptive indicator title.
  - `state_or_district`: Geographic unit (`Tamil Nadu` or specific district).
  - `reference_year`: Statistical reporting period.
  - `metric_value`: Numerical value.
  - `unit_of_measurement`: Units (`percent`, `per_lakh`, `inr_crores`).
  - `survey_agency`: Source organization (NSSO, NFHS, MoSPI, RBI).
  - `methodology_notes`: Data collection sampling framework.
- **Language:** English.
- **Date Coverage:** 2011 – Present.
- **Access Restrictions:** Open Data license (Government Open Data License - India).
- **Collection Method:** Direct API downloads from data.gov.in / NDAP and CSV dumps from RBI/MoSPI portals.
- **Validation Method:** Check against official survey sample size thresholds and confidence intervals.
- **Availability Status:** Widely available across national and state statistics portals.
- **Known Limitations:** Decennial Census 2021 has not been conducted; demographic indicators post-2011 rely on survey projections (SRS, NFHS-5) rather than universal enumeration.

---

### 2.8 Independent Fact-Check Articles
- **Purpose:** Ingest structured evaluations, evidence links, and contextual research from accredited independent fact-checking organizations.
- **Source URL:**
  - Alt News: [https://www.altnews.in/](https://www.altnews.in/)
  - BOOM Live: [https://www.boomlive.in/](https://www.boomlive.in/)
  - Factly: [https://factly.in/](https://factly.in/)
  - YouTurn (Tamil Fact-Checker): Verified Tamil independent debunking portal.
- **Expected Formats:** HTML web articles, ClaimReview JSON-LD schema metadata.
- **Relevant Fields:**
  - `factcheck_id`: Entity identifier.
  - `publisher_name`: Fact-checking outlet name.
  - `ifcn_signatory`: Boolean flag confirming IFCN accreditation status.
  - `claim_reviewed`: Verbatim claim reviewed.
  - `claim_date`: Date claim was initially circulated.
  - `rating`: Rating assigned (`True`, `False`, `Misleading`, `Unproven`, etc.).
  - `evidence_sources_cited`: Array of primary documents, links, and archived proofs.
  - `analysis_text`: Narrative breakdown and method.
  - `article_url`: Canonical URL of published fact-check.
- **Language:** English and Tamil.
- **Date Coverage:** 2018 – Present.
- **Access Restrictions:** Public web articles. Must follow robots.txt policies, citation etiquette, and avoid automated commercial scraping.
- **Collection Method:** Structured ingestion of `ClaimReview` schema markup via JSON-LD parser and RSS feeds.
- **Validation Method:** Ensure cited primary sources are independently fetchable and verify rating against IFCN code of principles.
- **Availability Status:** Readily accessible on web portals.
- **Known Limitations:** Independent fact-checkers focus heavily on viral digital disinformation; policy and budget claims are reviewed selectively rather than exhaustively.

---

### 2.9 Tamil and English News Articles
- **Purpose:** Trace the chronology of political claims, capture reactions, identify contradicting counter-claims, and observe media framing.
- **Source URL:**
  - Tamil Outlets: Daily Thanthi, Dinamalar, Dinamani, The Hindu Tamil Thisai.
  - English Outlets: The Hindu, DT Next, The New Indian Express, Times of India Chennai.
  - Official Feeds: PIB Chennai releases.
- **Expected Formats:** HTML articles, RSS feeds, article text extracts.
- **Relevant Fields:**
  - `article_id`: Primary key linked to Phase 4 `news_articles`.
  - `source_id`: Reference to `news_sources`.
  - `title`: Headline.
  - `published_date`: Datetime of reporting.
  - `article_text`: Body copy.
  - `entities_detected`: Named entities identified by Phase 2/4 NLP.
  - `quoted_claims`: Extracted direct quotes and political assertions.
  - `url`: Canonical source URL.
- **Language:** Tamil and English.
- **Date Coverage:** 2021 – Present.
- **Access Restrictions:** Public articles crawled in adherence with Phase 4 scraping policies and robots.txt.
- **Collection Method:** Reuses Phase 4 News Ingestion Pipeline (`backend/services/news_service.py`).
- **Validation Method:** De-duplication via SHA-256 text hashing and cross-outlet event comparison (`backend/services/event_comparison_service.py`).
- **Availability Status:** Fully active in repository via Phase 4.
- **Known Limitations:** News articles often quote politician claims without independently verifying figures; direct quotes must be distinguished from journalistic findings.

---

### 2.10 Existing Promises, Funding Records, and Representative Records (Phases 3–6)
- **Purpose:** Tap internal CIVICLENS TN ground-truth database to instantly verify claims concerning manifesto pledges, political financing, and representative performance.
- **Source URL:** Internal Repository SQLite/PostgreSQL Database (`civiclens.db`):
  - Phase 3: `political_promises`, `manifestos`, `promise_assessments`
  - Phase 5: `contributions`, `donors`, `financial_documents`, `election_expenditures`
  - Phase 6: `representatives`, `constituencies`, `legislative_activities`, `constituency_works`
- **Expected Formats:** Internal SQLAlchemy ORM models and JSON API responses.
- **Relevant Fields:**
  - Phase 3: `promise_id`, `original_text`, `status`, `rationale`, `evidence_links`.
  - Phase 5: `contribution_id`, `donor_name_normalized`, `amount_inr`, `party_id`, `financial_year`.
  - Phase 6: `representative_id`, `official_name`, `constituency_id`, `legislative_activities`, `constituency_works`.
- **Language:** English and Tamil.
- **Date Coverage:** Complete historical database (2011 – 2024).
- **Access Restrictions:** Fully accessible within repository environment.
- **Collection Method:** Direct SQL queries and service calls via Phase 3, 5, and 6 service modules.
- **Validation Method:** Database foreign-key constraints, provenance linkage, and unit test suite verification.
- **Availability Status:** Ready and active in existing codebase.
- **Known Limitations:** Constrained to the parties, terms, and financial years currently indexed in CIVICLENS TN.

---

## 3. Dataset Summary Matrix

| Dataset Category | Primary Source Starting Points | Expected Formats | Language | Coverage Period | Access Terms | Availability |
|---|---|---|---|---|---|---|
| **1. Public Political Claims** | Party Portals, Speeches, Manifestos | Text, JSON, Audio/Video | ta, en | 2016–Present | Public Fair Use | Available |
| **2. Government Announcements** | [tn.gov.in](https://www.tn.gov.in/), [pib.gov.in](https://pib.gov.in/) | PDF (G.O.), HTML | ta, en | 2011–Present | Public Domain | Available |
| **3. Official Fact-Checks** | [factcheck.pib.gov.in](https://factcheck.pib.gov.in/) | HTML, JSON | en, ta, hi | 2019–Present | Public Domain | Available |
| **4. Election Records** | [eci.gov.in](https://www.eci.gov.in/), [results.eci.gov.in](https://results.eci.gov.in/) | CSV, Form 21E PDF | en, ta | 2011–2024 | Statutory Public | Available |
| **5. Legislative Documents** | [sansad.in](https://sansad.in/), [assembly.tn.gov.in](https://www.assembly.tn.gov.in/) | XML, PDF (Hansard) | ta, en, hi | 2014–Present | Public Domain | Available |
| **6. Budget & Expenditure** | [tnbudget.tn.gov.in](https://www.tnbudget.tn.gov.in/), CAG | PDF (DDG), CSV | en, ta | FY16–FY25 | Public Domain | Available |
| **7. Public Statistical Datasets**| [data.gov.in](https://www.data.gov.in/), RBI, NFHS | CSV, JSON | en | 2011–Present | Open Gov License | Available |
| **8. Independent Fact-Checks** | [altnews.in](https://www.altnews.in/), [boomlive.in](https://www.boomlive.in/), [factly.in](https://factly.in/) | HTML, ClaimReview | en, ta | 2018–Present | Fair Use / Web | Available |
| **9. Tamil & English News** | Daily Thanthi, Dinamalar, The Hindu | HTML, RSS | ta, en | 2021–Present | Polite Crawl | Active (Phase 4) |
| **10. Cross-Phase Internal Data**| CIVICLENS Database (Phases 3–6) | SQL / JSON | ta, en | 2011–2024 | Internal DB | Active (Phases 1–6) |

---

## 4. Source Terms, Scraping Policies, and Automated Harvesting Rules

Before deploying automated scrapers in Phase 7.2:
1. **Robots.txt & Rate Limiting:** All institutional web scrapers (`pib.gov.in`, `sansad.in`, `tn.gov.in`) must respect `robots.txt`, utilize minimum 2.5-second request throttling, and set descriptive User-Agents (`CIVICLENS-TN-Academic-Research/1.0`).
2. **Downloadable Format First:** Whenever structured downloadable CSVs or APIs exist (e.g. data.gov.in, results.eci.gov.in), scrapers MUST prioritize raw data over HTML scraping.
3. **No Dynamic Bypass of Authentication:** Only openly published public data will be crawled. No login bypass, CAPTCHA defeat, or paywall circumvention will be implemented.
4. **Permanent Cryptographic Provenance:** Every ingested document must record SHA-256 hash, HTTP retrieval status, collection timestamp, and canonical source URL.
