# Phase 7 — Political Claim Verification Data Sources Inventory & Quality Matrix

## 1. Overview

This document catalogs the institutional, governmental, and independent sources utilized by the **CIVICLENS TN** Claim Verification & Evidence Intelligence module.

To ensure impartiality and scientific rigor, sources are categorized into **5 Source Tiers**:
- **Tier 1 (Statutory & Constitutional Authorities):** Official gazettes, Election Commission of India returns, CAG audits, parliamentary/assembly Hansard proceedings.
- **Tier 2 (Official Government Departments & Statistical Agencies):** Press Information Bureau, Tamil Nadu DIPR releases, RBI, MoSPI, NFHS, State Budget books.
- **Tier 3 (Accredited Fact-Checkers & Reputable Primary Press):** IFCN-certified fact-checking organizations (Alt News, BOOM, Factly) and established newspapers of record.
- **Tier 4 (Secondary Analysis & Civic Portals):** Academic reports, civil society dashboards (ADR/NEW, PRS Legislative Research).
- **Tier 5 (Public Political Claims & Campaign Feeds):** Party manifestos, political rally speeches, press meet statements, social media posts (subject of verification, never truth baseline).

---

## 2. Comprehensive Source Inventory

### 2.1 Press Information Bureau (PIB)
- **Portal URL:** [https://pib.gov.in/](https://pib.gov.in/)
- **Regional Bureau:** PIB Chennai ([https://pib.gov.in/allRel.aspx](https://pib.gov.in/allRel.aspx))
- **Source Tier:** Tier 2 (Central Executive Announcements & Statistics)
- **Data Types:** Press releases, cabinet decisions, central scheme allocations for Tamil Nadu, ministerial clarifications.
- **Formats:** HTML articles, PDF releases, bilingual feeds (English/Tamil).
- **Update Frequency:** Real-time / Daily.
- **Terms of Service & Licensing:** Open Government Data License (OGDL) India. Public domain government publications.
- **Collection Strategy:** RSS feed polling (`pib.gov.in/rss.aspx`) and targeted search scraping by ministry/tag.
- **Provenance Safeguards:** Ingest publication ID, timestamp, and archive snapshot.

### 2.2 PIB Fact Check Unit
- **Portal URL:** [https://factcheck.pib.gov.in/](https://factcheck.pib.gov.in/)
- **Source Tier:** Tier 2 (Official Government Rebuttal)
- **Data Types:** Official debunk records, ministry clarifications on viral claims.
- **Formats:** HTML entries, images with embedded textual metadata, social broadcast logs.
- **Update Frequency:** Daily.
- **Terms of Service:** Public domain executive communications.
- **Collection Strategy:** Crawl factcheck archive pages, extract viral claim vs. government rejoinder.
- **Special Caution:** Official government fact-checks reflect executive positions. In the CIVICLENS pipeline, they are treated as *Official Clarifications* rather than final independent truth verdicts.

### 2.3 Government of Tamil Nadu Official Portal & DIPR
- **Portal URL:** [https://www.tn.gov.in/](https://www.tn.gov.in/) & [https://dipr.tn.gov.in/](https://dipr.tn.gov.in/)
- **Source Tier:** Tier 1 / Tier 2 (State Executive Gazettes and Orders)
- **Data Types:** Government Orders (G.O. Ms.), cabinet press releases, policy notes, citizen charters.
- **Formats:** PDF scans, searchable text PDFs, Tamil HTML press announcements.
- **Update Frequency:** Continuous / Daily.
- **Terms of Service:** Public Domain (Official Gazette and Information Directorate).
- **Collection Strategy:** Scheduled scraper targeting `dipr.tn.gov.in/press-release` and department G.O. portals.
- **Provenance Safeguards:** Calculate SHA-256 hash on all downloaded G.O. PDFs; extract G.O. number and date.

### 2.4 Election Commission of India (ECI) & Results Portal
- **Portal URL:** [https://www.eci.gov.in/](https://www.eci.gov.in/) & [https://results.eci.gov.in/](https://results.eci.gov.in/)
- **Source Tier:** Tier 1 (Constitutional Statutory Authority)
- **Data Types:** General Assembly and Parliamentary election results, Form 20 booth sheets, Form 21E returns, voter turnout figures.
- **Formats:** CSV statistical tables, HTML result pages, PDF declarations.
- **Update Frequency:** Quadrennial / Election cycle and by-elections.
- **Terms of Service:** Statutory Public Record under Representation of the People Act, 1951.
- **Collection Strategy:** Batch download of statistical reports and real-time scrape during counting cycles.
- **Cross-Phase Integration:** Seamlessly feeds Phase 6 `Election` and `RepresentativeTerm` entities.

### 2.5 Sansad Portal (Parliament of India)
- **Portal URL:** [https://sansad.in/](https://sansad.in/)
- **Source Tier:** Tier 1 (Constitutional Legislative Record)
- **Data Types:** Lok Sabha and Rajya Sabha starred/unstarred questions, debate transcripts (Hansard), private member bills, attendance logs for Tamil Nadu MPs.
- **Formats:** XML question database, HTML session transcripts, PDF debate reports.
- **Update Frequency:** Daily during parliamentary sessions.
- **Terms of Service:** Public Parliamentary Record.
- **Collection Strategy:** Ingest via Sansad question API search endpoints and session debate cataloguer.
- **Provenance Safeguards:** Link question number, ministry, session date, and member identity.

### 2.6 Tamil Nadu Legislative Assembly (TNLA)
- **Portal URL:** [https://www.assembly.tn.gov.in/](https://www.assembly.tn.gov.in/)
- **Source Tier:** Tier 1 (Constitutional Legislative Record)
- **Data Types:** TN Assembly debates, questions and answers, bills passed, committee reports, governor's addresses.
- **Formats:** PDF proceedings documents, HTML member directories.
- **Update Frequency:** Published following assembly sessions.
- **Terms of Service:** Public Legislative Record.
- **Collection Strategy:** Scrape session debate repository; apply Tamil Unicode OCR and font normalization.
- **Provenance Safeguards:** Session volume, date, page number, and speech speaker tags.

### 2.7 Open Government Data (Data.gov.in & NDAP)
- **Portal URL:** [https://www.data.gov.in/](https://www.data.gov.in/) & [https://ndap.niti.gov.in/](https://ndap.niti.gov.in/)
- **Source Tier:** Tier 2 (National Statistical Repository)
- **Data Types:** Socioeconomic datasets, census metrics, infrastructure indices, health and education indicators for Tamil Nadu districts.
- **Formats:** REST JSON APIs, CSV, XLSX downloads.
- **Update Frequency:** Varies by dataset (monthly to annual).
- **Terms of Service:** Government Open Data License - India (GODL-India).
- **Collection Strategy:** Automated API queries using registered API keys for targeted metrics.
- **Validation:** Cross-check reported state aggregates against ministry annual reports.

### 2.8 Tamil Nadu State Budget Portal
- **Portal URL:** [https://www.tnbudget.tn.gov.in/](https://www.tnbudget.tn.gov.in/)
- **Source Tier:** Tier 1 / Tier 2 (State Fiscal Authority)
- **Data Types:** Detailed Demands for Grants (DDG), Budget Speeches, Medium Term Fiscal Policy Statements, Actual Expenditure tables.
- **Formats:** PDF budget books, web tables.
- **Update Frequency:** Annual budget sessions and supplementary estimates.
- **Terms of Service:** Public State Finance Record.
- **Collection Strategy:** Phase 1 Budget Pipeline integration (`backend/services/budget.py`).
- **Provenance Safeguards:** Document checksum, demand code, 15-digit head of account matching.

### 2.9 Independent Fact-Checking Portals (Alt News, BOOM, Factly)
- **Portal URLs:**
  - Alt News: [https://www.altnews.in/](https://www.altnews.in/)
  - BOOM Live: [https://www.boomlive.in/](https://www.boomlive.in/)
  - Factly: [https://factly.in/](https://factly.in/)
  - YouTurn (Tamil): [https://youturn.in/](https://youturn.in/)
- **Source Tier:** Tier 3 (IFCN-Accredited Independent Fact-Checking)
- **Data Types:** Deep investigative fact-checks, photo/video forensic verifications, policy claim evaluations.
- **Formats:** HTML web articles with embedded schema.org `ClaimReview` JSON-LD.
- **Update Frequency:** Continuous / Daily.
- **Terms of Service:** Web public articles. Must adhere to robots.txt and fair use citation.
- **Collection Strategy:** Parse schema.org `ClaimReview` structured data tags via RSS and page inspection.
- **Quality Safeguards:** Verify that independent fact-checkers cite primary Tier 1/2 documents before importing as corroborating evidence.

---

## 3. Source Quality & Assessment Rubric

Each evidence source in the pipeline receives an objective reliability assessment across four dimensions:

$$\text{SourceQualityScore} = w_{\text{tier}} \cdot S_{\text{tier}} + w_{\text{prim}} \cdot S_{\text{prim}} + w_{\text{indep}} \cdot S_{\text{indep}} + w_{\text{verif}} \cdot S_{\text{verif}}$$

| Dimension | Description | Weight | Scoring Range (0.0 to 1.0) |
|---|---|---|---|
| **Tier Weight ($S_{\text{tier}}$)** | Institutional hierarchy (Statutory vs. Secondary) | 0.35 | Tier 1 = 1.0, Tier 2 = 0.85, Tier 3 = 0.70, Tier 4 = 0.50, Tier 5 = 0.20 |
| **Primary Status ($S_{\text{prim}}$)** | Direct first-party record vs. commentary | 0.25 | Direct Gazetted/Official = 1.0, First-party report = 0.8, Secondary commentary = 0.4 |
| **Institutional Independence ($S_{\text{indep}}$)** | Freedom from partisan/executive bias | 0.20 | Independent Constitutional Body = 1.0, IFCN Signatory = 0.85, Executive PR = 0.60, Party PR = 0.20 |
| **Verifiability ($S_{\text{verif}}$)** | Publicly auditability and persistent URL/hash | 0.20 | Cryptographically hashed public doc = 1.0, Open web link = 0.8, Non-archived = 0.3 |

---

## 4. Robots.txt Compliance & Request Polling Policies

| Source Domain | Robots.txt Policy Checked | Polling Interval | User-Agent Header | Primary Data Protocol |
|---|---|---|---|---|
| `pib.gov.in` | Yes (Permitted with delay) | Minimum 3.0s | `CivicLensTN-ResearchBot/1.0` | RSS / Web crawl |
| `factcheck.pib.gov.in` | Yes (Permitted) | Minimum 3.0s | `CivicLensTN-ResearchBot/1.0` | Web crawl |
| `tn.gov.in` / `dipr.tn.gov.in`| Yes (Permitted) | Minimum 2.5s | `CivicLensTN-ResearchBot/1.0` | Daily batch G.O. scrape |
| `eci.gov.in` / `results.eci.gov.in` | Yes (Permitted) | Minimum 2.0s | `CivicLensTN-ResearchBot/1.0` | Direct CSV / HTML extract |
| `sansad.in` | Yes (Permitted) | Minimum 3.0s | `CivicLensTN-ResearchBot/1.0` | XML query / HTML scrape |
| `assembly.tn.gov.in` | Yes (Permitted) | Minimum 3.0s | `CivicLensTN-ResearchBot/1.0` | PDF debate download |
| `data.gov.in` | Yes (Official API) | API Rate Limit (10 req/min) | `CivicLensTN-ResearchBot/1.0` | JSON REST API |
| `tnbudget.tn.gov.in` | Yes (Permitted) | Minimum 3.0s | `CivicLensTN-ResearchBot/1.0` | Annual batch PDF download |
| `altnews.in` / `boomlive.in` | Yes (Permitted) | Minimum 5.0s | `CivicLensTN-ResearchBot/1.0` | ClaimReview JSON-LD parse |
