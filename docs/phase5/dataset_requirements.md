# Phase 5 — Political Funding Transparency Dataset Requirements

## 1. Overview & Data Acquisition Strategy

Phase 5 of **CIVICLENS TN** relies on statutory disclosures, public filings, historical records, and verified institutional research repositories to build a comprehensive political funding transparency database.

This document defines the technical, structural, and legal requirements for all seven core datasets required for Phase 5 implementation.

> [!IMPORTANT]
> **Availability Principle:** Data availability varies significantly across political parties, election years, and reporting formats. The pipeline is designed to handle incomplete, missing, or unstandardized disclosures without making false assumptions or fabricating records.

---

## 2. Dataset Specifications

### 2.1 ECI Political Party Contribution Reports (Form 24A)

- **Purpose:** Ingest statutory annual contribution reports submitted by political parties to the Election Commission of India (ECI) for donations exceeding ₹20,000, under Section 29C of the Representation of the People Act, 1951.
- **Official Source URL:** [https://www.eci.gov.in/contribution-reports](https://www.eci.gov.in/contribution-reports)
- **Expected Format:** PDF (both scanned physical documents and native digital PDFs).
- **Fields Required:**
  - `party_name`: Name of the political party.
  - `financial_year`: Statutory financial year (e.g., `2021-2022`).
  - `donor_name`: Full name of donor (corporate entity, trust, or individual).
  - `donor_address`: Disclosed mailing/registered address of donor.
  - `amount_inr`: Monetary contribution amount in INR.
  - `payment_mode`: Method of payment (`Cheque`, `Demand Draft`, `EFT/RTGS`, `Electoral Bond`, `Cash`, `Other`).
  - `cheque_dd_number`: Instrument reference number (where disclosed).
  - `date_of_payment`: Transaction/instrument date.
  - `remarks`: Additional annotations or remarks in statutory filing.
- **Financial Years Required:** FY 2014-15 through FY 2024-25.
- **Availability Status:** Partial. Available for recognized national and state parties (including DMK, AIADMK); often filed with significant delay by unrecognized registered parties.
- **Licensing / Access Considerations:** Statutory Public Disclosures published under ECI mandate; open public domain for civic research.
- **Extraction Method:** Layout-aware PDF tabular extraction (`pdfplumber`) with Tesseract OCR fallback for low-resolution scanned image PDFs.
- **Validation Method:**
  - `Sum Check`: Aggregate sum of extracted individual entries must match total reported contribution sum in summary sheet.
  - `Date Range Check`: All transaction dates must fall within the specified financial year (April 1 to March 31).
  - `Threshold Assertion`: Flag entries below ₹20,000 included in Form 24A.
- **Known Limitations:**
  - Does not capture contributions below ₹20,000 (which constitute a major portion of unrecognized income).
  - Corporate CIN (Corporate Identification Number) and PAN are rarely provided in older filings.
  - Inconsistent spelling and non-standardized donor addresses across years.

---

### 2.2 ECI Annual Audited Accounts

- **Purpose:** Ingest complete audited financial statements (Balance Sheet, Income & Expenditure Account, and Schedules) submitted annually by political parties.
- **Official Source URL:** [https://www.eci.gov.in/annual-audit-reports](https://www.eci.gov.in/annual-audit-reports)
- **Expected Format:** PDF (Scanned chartered accountant audit statements).
- **Fields Required:**
  - `party_name`: Political party entity name.
  - `financial_year`: Reporting period.
  - `total_income`: Total gross income reported in Income & Expenditure statement.
  - `total_expenditure`: Total gross expenditure reported.
  - `grant_from_electoral_trusts`: Aggregate grants received from registered electoral trusts.
  - `contributions_above_20k`: Total donations exceeding ₹20,000.
  - `contributions_below_20k`: Total voluntary contributions below ₹20,000.
  - `electoral_bond_income`: Income declared via Electoral Bonds.
  - `other_income`: Bank interest, coupon sales, membership fee receipts.
  - `salaries_and_admin_expenditure`: Operating and administrative expenses.
  - `publicity_expenditure`: Advertising, publicity, and travel expenses.
  - `auditor_name`: Name and membership number of the Chartered Accountant / Auditing Firm.
  - `audit_date`: Date of auditor sign-off.
- **Financial Years Required:** FY 2014-15 through FY 2024-25.
- **Availability Status:** Partial/Available. High availability for national parties and major TN state parties (DMK, AIADMK); variable availability for smaller state parties.
- **Licensing / Access Considerations:** Statutory Public Disclosures (ECI guidelines).
- **Extraction Method:** Key-value structure parsing and financial statement schedule table extraction.
- **Validation Method:**
  - `Accounting Equation Check`: `Total Income - Total Expenditure = Net Surplus/Deficit`.
  - `Cross-Validation Check`: Form 24A disclosed total must be `<= Total Disclosed Contributions` in Audited Accounts.
- **Known Limitations:**
  - Non-standardized accounting line items across different political parties.
  - Scanned PDF documents frequently suffer from skew, dark margins, or illegible auditor stamps.

---

### 2.3 ADR Political Donation Analysis Reports

- **Purpose:** Ingest verified, aggregated research reports and datasets published by Association for Democratic Reforms (ADR) analyzing party donation trends, donor classifications, and unknown source ratios.
- **Official Source URL:**
  - [https://www.adrindia.org/content/donation-report](https://www.adrindia.org/content/donation-report)
  - [https://www.adrindia.org/research-and-report/political-party-watch](https://www.adrindia.org/research-and-report/political-party-watch)
- **Expected Format:** HTML summary pages, PDF research reports, and CSV/Excel tables.
- **Fields Required:**
  - `party_name`: Target political party name.
  - `financial_year`: Analysis year.
  - `total_donations_analyzed`: Aggregate analyzed donation volume.
  - `corporate_donations_total`: Total contribution amount from corporate sector.
  - `individual_donations_total`: Total contribution amount from individual donors.
  - `electoral_trust_donations_total`: Grants received via Electoral Trusts.
  - `top_donors_list`: Ranked list of top corporate/individual donors.
  - `unknown_sources_income_percentage`: Percentage of party income derived from un-itemized sources (coupons, voluntary contributions < ₹20k, bonds).
- **Financial Years Required:** FY 2014-15 through FY 2023-24.
- **Availability Status:** Available. Highly consistent annual reports covering national and major state parties.
- **Licensing / Access Considerations:** Open Academic / NGO Research Data; attribution to Association for Democratic Reforms (ADR) required.
- **Extraction Method:** Web page HTML parsing and structured table extraction from ADR report downloads.
- **Validation Method:** Cross-reference ADR summary figures against statutory ECI raw filings for matching parties and years.
- **Known Limitations:** Derived dataset (reflects ADR's cleaning and categorization rules); limited to parties selected in ADR research scope.

---

### 2.4 Electoral Trust Contribution Reports

- **Purpose:** Ingest statutory annual filings of registered Electoral Trusts detailing funds received from corporate donors and disbursed to political parties.
- **Official Source URL:** [https://www.eci.gov.in/electoral-trusts-reports](https://www.eci.gov.in/electoral-trusts-reports)
- **Expected Format:** PDF (annual statutory returns).
- **Fields Required:**
  - `electoral_trust_name`: Registered name of trust (e.g., `Prudent Electoral Trust`, `Progressive Electoral Trust`).
  - `financial_year`: Reporting year.
  - `donor_name`: Corporate entity or individual contributor name.
  - `donor_cin_or_pan`: CIN or PAN disclosed by donor to trust.
  - `amount_received`: Contribution received by trust.
  - `date_received`: Receipt date.
  - `recipient_party_name`: Political party receiving trust grant.
  - `amount_distributed`: Grant amount disbursed to political party.
  - `date_distributed`: Disbursement date.
- **Financial Years Required:** FY 2014-15 through FY 2024-25.
- **Availability Status:** Available for active registered electoral trusts.
- **Licensing / Access Considerations:** Statutory Public Disclosures (Ministry of Corporate Affairs & ECI Electoral Trusts Scheme 2013).
- **Extraction Method:** PDF table parsing and bipartite graph extraction (Donor → Trust → Party).
- **Validation Method:**
  - `Trust Distribution Balance Check`: `Total Funds Distributed + Admin Costs (max 5%) <= Total Funds Received + Carryover Balance`.
- **Known Limitations:**
  - Some trusts disaggregate incoming donor amounts and outgoing party grants into separate tables without explicit 1-to-1 donor-party mapping.

---

### 2.5 Historical Electoral Bond Disclosure Records

- **Purpose:** Ingest comprehensive historical disclosure records released by SBI per Supreme Court of India directives (March 2024), mapping bond purchases and party redemptions.
- **Official Source URL:** Official ECI Supreme Court Disclosure Portal.
- **Expected Format:** CSV datasets and PDF tabular releases.
- **Fields Required:**
  - `purchaser_name`: Name of buyer entity/individual.
  - `bond_prefix`: Alpha prefix of bond serial number (e.g., `TL`).
  - `bond_number`: Numeric serial identifier of bond.
  - `denomination_inr`: Face value of bond (e.g., ₹1,000,000 or ₹10,000,000).
  - `issue_branch`: SBI branch issuing bond.
  - `issue_date`: Date of purchase.
  - `expiry_date`: Bond validity expiration date (15 days from issue).
  - `receiver_party_name`: Political party encashing bond.
  - `encashment_branch`: SBI branch where bond was redeemed.
  - `encashment_date`: Date of encashment.
- **Financial Years Required:** FY 2019-20 through FY 2023-24 (April 2019 to February 2024).
- **Availability Status:** Static Complete Dataset (Historical dataset complete following Supreme Court ruling).
- **Licensing / Access Considerations:** Public Domain (Released per Supreme Court of India Orders).
- **Extraction Method:** Direct CSV structured ingestion and database loading.
- **Validation Method:**
  - `Prefix-Number Pair Match`: Match purchaser `(bond_prefix, bond_number)` to redemption `(bond_prefix, bond_number)`.
  - `Encashed Window Assertion`: `encashment_date` must be within 15 days of `issue_date`.
- **Known Limitations:**
  - Data covers only April 2019 to February 2024; pre-2019 purchases do not include serial prefix numbers.

---

### 2.6 Political Party Election Expenditure Statements

- **Purpose:** Ingest itemized statements of expenses incurred by political parties during state assembly and parliamentary election campaigns.
- **Official Source URL:** [https://www.eci.gov.in/candidate-politicalparty](https://www.eci.gov.in/candidate-politicalparty)
- **Expected Format:** PDF election expenditure disclosures.
- **Fields Required:**
  - `party_name`: Filing political party.
  - `election_name`: Target election (e.g., `Tamil Nadu Legislative Assembly General Election 2021`, `Lok Sabha 2024`).
  - `election_year`: Election year.
  - `state`: Target state (`Tamil Nadu`).
  - `star_campaigners_travel_expenditure`: Expenses for aircraft, helicopters, and travel of key leaders.
  - `media_publicity_expenditure`: TV, print, radio, and digital campaign advertisement spending.
  - `public_meetings_expenditure`: Rallies, processions, stages, and PA system costs.
  - `financial_assistance_to_candidates`: Lumpsum grants distributed directly to contested candidates.
  - `total_election_expenditure`: Gross election campaign expenditure.
- **Financial Years Required:** Assembly Elections 2016, 2021; Lok Sabha Elections 2019, 2024.
- **Availability Status:** Partial. Disclosed post-election within statutory timeframe; available for major contesting parties in Tamil Nadu.
- **Licensing / Access Considerations:** Statutory Public Filings under ECI guidelines.
- **Extraction Method:** PDF expenditure schedule parsing and categorical summary extraction.
- **Validation Method:**
  - `Head Summation Check`: Sum of individual expenditure heads must equal reported `total_election_expenditure`.
- **Known Limitations:** Candidate-level individual election expense accounts are filed separately from central party expenditure statements.

---

### 2.7 Official Political Party Registry

- **Purpose:** Master metadata reference table of recognized national parties, recognized state parties (Tamil Nadu), and unrecognized registered political parties.
- **Official Source URL:** [https://www.eci.gov.in/candidate-politicalparty](https://www.eci.gov.in/candidate-politicalparty)
- **Expected Format:** PDF gazette notifications, official ECI party list publications, and web HTML tables.
- **Fields Required:**
  - `party_code`: Standardized unique short string code (e.g., `DMK`, `AIADMK`, `INC`, `BJP`, `PMK`, `VCK`, `NTK`, `DMDK`).
  - `party_name`: Official full name of party.
  - `abbreviation`: Common English/Tamil abbreviation.
  - `party_type`: Classification (`NATIONAL`, `STATE_RECOGNIZED_TN`, `STATE_RECOGNIZED_OTHER`, `UNRECOGNIZED_REGISTERED`).
  - `symbol_name`: Reserved election symbol name.
  - `registration_date`: Official date of ECI registration.
  - `headquarters_address`: Registered central address.
  - `official_state`: Primary operating state (`Tamil Nadu` / `National`).
- **Financial Years Required:** Master lookup spanning historical filings (1951 - Present).
- **Availability Status:** Fully Available.
- **Licensing / Access Considerations:** Public Domain / Official Government Gazette.
- **Extraction Method:** Automated web table scraping and ECI notification parsing.
- **Validation Method:** Unique party code constraint; verification against statutory ECI notifications.
- **Known Limitations:** Slight variations in party name transliterations across English, Tamil, and Hindi ECI document headers.

---

## 3. Dataset Matrix Summary

| Dataset ID | Dataset Name | Primary Source URL | Format | Availability | Primary Extraction Method |
|---|---|---|---|---|---|
| `DS-501` | Form 24A Contribution Reports | [eci.gov.in/contribution-reports](https://www.eci.gov.in/contribution-reports) | PDF | Partial | `pdfplumber` + OCR |
| `DS-502` | Annual Audited Accounts | [eci.gov.in/annual-audit-reports](https://www.eci.gov.in/annual-audit-reports) | PDF | Available / Partial | Key-Value Table Parser |
| `DS-503` | ADR Donation Reports | [adrindia.org/content/donation-report](https://www.adrindia.org/content/donation-report) | HTML / PDF / CSV | Available | HTML Scraper + PDF Ingestion |
| `DS-504` | Electoral Trust Reports | [eci.gov.in/electoral-trusts-reports](https://www.eci.gov.in/electoral-trusts-reports) | PDF | Available | Graph / PDF Table Extraction |
| `DS-505` | Electoral Bond Disclosures | ECI SC Portal | CSV / PDF | Static Complete | CSV Direct Loader |
| `DS-506` | Election Expenditure Statements | [eci.gov.in/candidate-politicalparty](https://www.eci.gov.in/candidate-politicalparty) | PDF | Partial | PDF Schedule Parser |
| `DS-507` | Official Political Party Registry | [eci.gov.in/candidate-politicalparty](https://www.eci.gov.in/candidate-politicalparty) | HTML / PDF | Fully Available | Web Scraper |
