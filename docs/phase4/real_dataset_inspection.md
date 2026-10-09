# Real News Dataset Inspection Report

**Project**: CIVICLENS TN — Phase 4 Tamil News Bias & Political Coverage Analyzer  
**Date**: October 9, 2026  
**Status**: Dataset Verified & Extracted  

---

## 1. Dataset Provenance & Archive Metadata

The real Phase 4 news dataset was located within the local environment and inspected prior to extraction.

- **Source Location**: `E:\Downloads 🔄\News CivicLens`
- **Archive Format**: ZIP Archive (PK magic bytes `b'PK\x03\x04'`)
- **File Size**: 38,678 bytes (37.77 KB)
- **SHA-256 Checksum**: `12e4fea737d27495423e03da9e26c189d4f585fcb9fd8524ff7006638c58d30b`
- **Extraction Target Directory**: `data/raw/news/`

The original ZIP archive remains preserved in its location while all extracted files are safely registered under `data/raw/news/`.

---

## 2. Extracted File Inventory

The archive was extracted into `data/raw/news/` containing 9 files:

| File Name | File Size | Description |
| :--- | :--- | :--- |
| `README_batch1.md` | 1,614 bytes | Batch overview, dataset scope, and verification methodology |
| `data_dictionary_batch1.csv` | 3,311 bytes | Definitive data dictionary and field definitions |
| `dataset_A_news_articles_batch1.csv` | 64,006 bytes | Core news articles dataset (72 records) |
| `dataset_A_strict_verified_batch1.csv` | 14,635 bytes | Strictly verified article subset (15 records) |
| `dataset_B_political_events_batch1.csv` | 7,189 bytes | Political events dataset (13 records) |
| `dataset_D_official_references_batch1.csv` | 1,056 bytes | Official state references / independent analysis (1 record) |
| `dataset_E_source_metadata_batch1.csv` | 13,886 bytes | News source registry metadata (44 sources) |
| `duplicate_check_report_batch1.csv` | 2,132 bytes | Cross-publisher near-duplicate headline checks (23 checks) |
| `source_verification_log_batch1.csv` | 22,298 bytes | Line-by-line article verification audit log (72 logs) |

---

## 3. Dataset Schemas & Column Mappings

### Dataset A — News Articles (`dataset_A_news_articles_batch1.csv`)
Contains 29 columns:
- **Identifiers**: `article_id`, `source_id`, `source_name`, `article_url`
- **Headlines & Text**: `headline_original`, `headline_english_translation`, `article_text`, `article_summary`
- **Metadata**: `language`, `author`, `published_date`, `collected_date`, `category`, `subcategory`
- **Entities & Location**: `political_parties_mentioned`, `political_leaders_mentioned`, `other_entities`, `location_mentioned`, `event_id`
- **Framing & Sentiment**: `framing_label`, `sentiment_label`, `bias_evidence`, `evidence_quote`
- **Verification & Provenance**: `fact_check_status`, `text_availability`, `verification_status`, `verification_method`, `verification_notes`, `duplicate_flag`

### Dataset B — Political Events (`dataset_B_political_events_batch1.csv`)
Columns: `event_id`, `event_title`, `event_date`, `event_type`, `event_description`, `location`, `political_parties_involved`, `political_leaders_involved`, `related_policy_or_issue`, `official_reference_url`, `related_article_ids`, `verification_status`.

### Dataset E — News Sources (`dataset_E_source_metadata_batch1.csv`)
Columns: `source_id`, `source_name`, `website_url`, `language`, `publisher_or_organization`, `source_type`, `geographic_focus`, `editorial_policy_url`, `ownership_reference_url`, `known_corrections_policy_url`, `metadata_reference_url`, `verification_status`, `notes`.

---

## 4. Dataset Breakdown & Statistical Summary

- **Total Articles**: 72 articles
  - **Tamil Language Articles**: 37 (51.4%)
  - **English Language Articles**: 35 (48.6%)
- **Unique News Sources**: 44 distinct media outlets (including Nakkheeran, ETV Bharat, DT Next, Deccan Herald, Dinamalar, Minnambalam, Vikatan, Daily Thanthi, Zee News Tamil, Oneindia Tamil, The News Minute, etc.)
- **Political Events Covered**: 13 major TN political events (e.g. Union Budget 2026-27 reactions, TN Interim Budget 2026-27, party launch rallies, infrastructure policy debates)
- **Strictly Verified Subset**: 15 fully verified articles (`verification_status = 'verified'`)

---

## 5. Unicode Integrity & Text Quality

- **Tamil Script Encoding**: Full UTF-8 compliance verified. Tamil headlines (e.g., `பட்ஜெட் 2026 : கவனம் பெற்ற முக்கிய அறிவிப்புகள்!`) and Tamil author bylines (e.g., `நக்கீரன் செய்திப்பிரிவு`) render cleanly without corruption.
- **Text Availability**: Articles carry `article_summary` alongside headlines and metadata. `text_availability` tracks `full_text_accessible_not_stored` or `metadata_only_text_not_retrieved` in compliance with copyright guidelines.
- **Quality Audit**: Zero corrupted characters or unparseable lines encountered during CSV validation.
