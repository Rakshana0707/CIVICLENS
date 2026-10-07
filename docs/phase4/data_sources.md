# Phase 4 — Data Sources Inventory & Acquisition Strategy

This document provides a comprehensive, prioritized catalog of external news and government data sources designated for acquisition under Phase 4.

---

## 1. Source Classification Hierarchy

Data sources are categorized into three distinct operational tiers:

1. **PRIMARY (Direct Content & Official Evidence):**
   - High-credibility news portals, regional dailies, and official government portals.
   - Authorized for direct article parsing, text normalization, and evidence extraction.
2. **SECONDARY (Archival & Research Corpora):**
   - Public web archives, open research datasets, and academic news repositories.
   - Utilized for historical baseline comparison and training NLP normalization models.
3. **DISCOVERY ONLY (Indexing & Alerting):**
   - Aggregators, search engines, and social media trend monitors.
   - **Rule:** Used solely for URL discovery and event detection; *never* treated as authoritative evidence without primary source verification.

---

## 2. Comprehensive Data Source Inventory

### 2.1 Primary News & Government Sources

| Source Name | Domain | Language | Data Type | Collection Method | Expected Fields | Access Restrictions | Robots / Terms | Priority |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **The Hindu (TN Edition)** | `thehindu.com` | English | News Articles | RSS Feed + HTML Parser | Title, Text, Date, Author, Section, URL | Standard paywall on deep archives; RSS open | `robots.txt` compliant; 2s crawl delay | P1 |
| **Dinamani** | `dinamani.com` | Tamil | News Articles | RSS Feed + HTML Parser | Title, Text, Date, Section, URL | Open Web | `robots.txt` compliant; rate-limited | P1 |
| **Daily Thanthi** | `dailythanthi.com` | Tamil | News Articles | RSS Feed + HTML Parser | Title, Text, Date, Section, URL | Open Web | `robots.txt` compliant; rate-limited | P1 |
| **Dinamalar** | `dinamalar.com` | Tamil | News Articles | RSS Feed + HTML Parser | Title, Text, Date, Section, URL | Open Web; paywall on epaper | `robots.txt` compliant; 3s delay | P1 |
| **Puthiya Thalaimurai** | `puthiyathalaimurai.com` | Tamil | News Articles / Video Text | RSS Feed + HTML Parser | Title, Text, Date, Category, URL | Open Web | `robots.txt` compliant | P1 |
| **Vikatan** | `vikatan.com` | Tamil | News & Analysis | RSS Feed + HTML Parser | Title, Text, Date, Author, URL | Subscription on premium magazines | `robots.txt` compliant; respect paywalls | P2 |
| **News18 Tamil Nadu** | `tamil.news18.com` | Tamil | News Articles | RSS Feed + HTML Parser | Title, Text, Date, Section, URL | Open Web | `robots.txt` compliant | P2 |
| **BBC News Tamil** | `bbc.com/tamil` | Tamil | News Articles | RSS Feed + HTML Parser | Title, Text, Date, URL | Open Web | Public Service broadcasting terms | P1 |
| **Times of India (Chennai)** | `timesofindia.indiatimes.com` | English | News Articles | RSS Feed + HTML Parser | Title, Text, Date, Section, URL | Open Web / Rate limited | `robots.txt` compliant | P2 |
| **TN Government Portal** | `tn.gov.in` | Tamil / English | GOs, Policy Docs, Releases | HTTP Crawl + PDF Extractor | Document Title, Text, Date, Dept, GO No | Public Domain / Open Gov | Open Public Access | P1 |
| **DIPR Tamil Nadu** | `dipr.tn.gov.in` | Tamil / English | Official Press Releases | HTML Fetcher + PDF Extractor | Release Title, Date, Text, Department | Public Domain | Open Public Access | P1 |
| **Election Commission of India** | `eci.gov.in` | English / Hindi | Election Press Notes, Data | HTTP Crawl + PDF Reader | Title, Date, Body, Circular No | Open Government Data | Open Public Access | P1 |
| **Chief Electoral Officer, TN** | `elections.tn.gov.in` | Tamil / English | Local Electoral Releases | HTTP Crawl + PDF Reader | Title, Date, Body, Electoral District | Open Government Data | Open Public Access | P1 |

---

### 2.2 Secondary Archival & Research Corpora

| Source Name | Domain | Language | Data Type | Collection Method | Expected Fields | Access Restrictions | Robots / Terms | Priority |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Wayback Machine API** | `web.archive.org` | Tamil / English | Historical Snapshots | Wayback CDX API | Raw HTML Snapshot, Timestamp, Original URL | Rate-limited API | Terms of Use for Internet Archive | P2 |
| **AI4Bharat IndicNLP** | `ai4bharat.org` | Tamil | Monolingual Text Corpora | Dataset Download | Raw Tamil Text Sentences | Open Source License (CC-BY) | Academic Attribution Required | P2 |
| **IndicCorp Corpus** | `huggingface.co/datasets/indic_corp` | Tamil | Crawled News Text | HuggingFace Datasets API | Text, Language | Open Source (CC-0 / MIT) | Dataset Attribution Required | P3 |

---

### 2.3 Discovery Only Sources

| Source Name | Domain | Purpose | Collection Method | Processing Restriction | Priority |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Google News RSS** | `news.google.com` | Emerging Topic & Article Discovery | RSS Feed Keyword Query | DISCOVERY ONLY — Extract target canonical URL and fetch primary site directly. Do not store Google News snippet as article text. | P2 |
| **Bing News Search API** | `api.bing.microsoft.com` | Event & Breaking News Indexing | REST API | DISCOVERY ONLY — Follow returned URLs to primary publisher. | P3 |

---

## 3. Compliance, Ethics & Rate Limiting Policy

1. **Robots.txt Adherence:** All crawlers and scrapers MUST parse and comply with `robots.txt` directives prior to initiating fetch cycles for any domain.
2. **Crawl Delays & Polling Intervals:**
   - Minimum delay between consecutive HTTP requests to a single domain: **2.0 seconds** (default), increasing up to **5.0 seconds** for sensitive sites.
   - Polling frequency for RSS feeds: Maximum once every **15 to 30 minutes**.
3. **User-Agent Transparency:**
   - Requests must identify themselves with an explicit User-Agent string:
     `User-Agent: CIVICLENS-TN-NewsAnalyzer/1.0 (+https://civiclens.tn.gov.in/bot; research@civiclens.org)`
4. **Copyright & Fair Use Handling:**
   - For outlets with strict copyright or paywalls, the system will store only essential metadata, lead snippets, and derived feature vectors, linking back directly to the original publisher URL for full text viewing.
