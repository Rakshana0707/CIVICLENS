# Phase 4 — Dataset Requirements & Specification

This document details the target data specifications for the **Tamil News Bias & Political Coverage Analyzer**. These requirements define the schema and validation standards for future dataset collection.

---

## 1. News Articles Schema Specification

News articles represent the core corpus of unstructured and semi-structured text to be ingested and analyzed.

### A. Required Fields (Mandatory for Ingestion)

| Field Name | Data Type | Description / Constraints | Example |
| :--- | :--- | :--- | :--- |
| `article_id` | String (UUID / Hash) | Unique identifier derived from domain + SHA256(canonical URL) | `"art_9f8a7c6b5e"` |
| `source_id` | String | Foreign key matching registered `NewsSource.source_id` | `"src_hindu_en"` |
| `url` | String (URL) | Exact original web URL at retrieval time | `"https://www.thehindu.com/news/..."` |
| `title` | String | Extracted headline text (cleaned of site chrome/branding) | `"TN Budget Allocates Rs 500 Cr for Metro Expansion"` |
| `author` | String | Bylined author name(s) or agency credit (or "Staff Reporter") | `"B. Aravind"` |
| `publication_date` | ISO 8601 DateTime | Publication date and time (UTC or specified timezone) | `"2026-03-15T10:30:00Z"` |
| `section` | String | News category/section name as reported by the source | `"State - Tamil Nadu"` |
| `language` | String (ISO 639-1) | Language code (`"ta"` for Tamil, `"en"` for English) | `"ta"` |
| `article_text` | Text | Full cleaned text content of the article body | `"சென்னை..."` |
| `retrieval_date` | ISO 8601 DateTime | UTC timestamp when the article was scraped/ingested | `"2026-10-07T14:20:00Z"` |

### B. Preferred Additional Fields (Optional / High-Value Metadata)

| Field Name | Data Type | Description |
| :--- | :--- | :--- |
| `tags` | Array of Strings | Keywords/tags provided by the publisher |
| `category` | String | Standardized top-level CIVICLENS topic category |
| `image_url` | String (URL) | Lead article image URL |
| `canonical_url` | String (URL) | `rel="canonical"` URL specified in HTML head |
| `updated_date` | ISO 8601 DateTime | Timestamp of latest editorial revision |

---

## 2. News Source Registry Specification

Every article must be linked to a pre-registered news outlet with verified operational metadata.

| Field Name | Data Type | Description / Allowed Values | Example |
| :--- | :--- | :--- | :--- |
| `source_id` | String | Primary Key identifier | `"src_dinamani_ta"` |
| `source_name` | String | Full readable name of the news organization | `"Dinamani"` |
| `domain` | String | Base domain name | `"dinamani.com"` |
| `language` | String | Primary language (`"ta"`, `"en"`, `"bilingual"`) | `"ta"` |
| `source_type` | String | Outlets type (`"print_digital"`, `"tv_digital"`, `"digital_native"`, `"official_gov"`) | `"print_digital"` |
| `official_url` | String (URL) | Homepage URL | `"https://www.dinamani.com"` |
| `robots_policy_checked` | Boolean | True if robots.txt and terms have been audited | `true` |
| `collection_method` | String | Ingestion technique (`"rss"`, `"html_scraper"`, `"official_api"`) | `"rss"` |
| `active_status` | String | Status (`"active"`, `"paused"`, `"archived"`) | `"active"` |

---

## 3. Political Entities Specification

Extracted named entities representing political actors, administrative bodies, and geographies in Tamil Nadu.

### Entity Categories & Attributes

1. **Political Persons (`PoliticalPerson`)**
   - Fields: `person_id`, `name` (English & Tamil script), `alias_names`, `party_id`, `current_designation`, `constituency_id`.
   - Examples: Chief Minister, Ministers, Leaders of Opposition, MPs, MLAs.
2. **Political Parties (`PoliticalParty`)**
   - Fields: `party_id`, `party_name`, `party_code`, `symbol`, `founding_year`, `coalition_alliance`.
   - Examples: DMK, AIADMK, INC, BJP, VCK, NTK, PMK, CPI(M).
3. **Government Departments (`government_department`)**
   - Fields: `dept_id`, `dept_name_en`, `dept_name_ta`, `parent_ministry`.
   - Examples: Department of Finance, Department of School Education, Health & Family Welfare.
4. **Constituencies (`constituency`)**
   - Fields: `constituency_id`, `name`, `district`, `type` (`"assembly"`, `"parliamentary"`).
5. **Organizations & Administrative Bodies (`organization`)**
   - Fields: `org_id`, `name`, `type` (`"judiciary"`, `"commission"`, `"union"`, `"ngo"`).
6. **Geographic Locations (`location`)**
   - Fields: `location_id`, `name`, `district`, `state`, `geo_coordinates`.

---

## 4. Political Events Specification

Key ground-truth political events, elections, press conferences, budget announcements, and legislative sessions.

| Field Name | Data Type | Description | Example |
| :--- | :--- | :--- | :--- |
| `event_id` | String | Unique event identifier | `"evt_tn_budget_2026"` |
| `event_name` | String | Readable title of the event | `"Tamil Nadu State Budget Presentation 2026-27"` |
| `event_date` | Date | Primary date of occurrence | `"2026-03-14"` |
| `location` | String | Venue / City | `"Tamil Nadu Legislative Assembly, Chennai"` |
| `entities` | Array of Strings | Linked entity IDs involved | `["ent_cm_tn", "ent_fin_min_tn"]` |
| `description` | Text | Objective summary of the event | `"Annual budget presented by Finance Minister..."` |
| `official_reference` | String (URL) | Primary government or official record link | `"https://tn.gov.in/budget/2026"` |

---

## 5. Official Government Sources Specification

Official documentation providing ground-truth reference material for factual comparison and evidence validation.

- **Government Press Releases:** Daily bulletins from `dipr.tn.gov.in`.
- **Government Orders (GOs):** Gazette notifications and departmental executive orders.
- **Department Announcements & Policy Briefs:** Official policy releases, white papers, and scheme handbooks.
- **Official Statements:** Transcripts of official press briefings and legislative speeches.
- **Election Commission Documents:** Official releases, press notes, and candidate filings from ECI (`eci.gov.in`) and CEO Tamil Nadu (`elections.tn.gov.in`).

---

## 6. Optional Labeled Bias Dataset Specification

If a public academic or benchmark dataset for Tamil news bias/framing becomes available, it may be integrated using the following structure:

- **Dataset Name:** Name of the corpus (e.g., `TamilNewsBiasBench-v1`)
- **Source / Authors:** Academic institution or research group
- **License:** Open Access license (e.g., CC-BY-4.0, MIT)
- **Labels:** Stance / Framing labels (e.g., `neutral`, `favorable`, `critical`)
- **Label Definitions:** Codebook defining annotation standards
- **Language:** Tamil / English / Parallel
- **Corpus Size:** Total article/sentence count

> [!NOTE]
> No public pre-labeled bias dataset is assumed to exist. All initial Phase 4 metrics will rely on unsupervised statistical indicators and rule-based linguistic features.
