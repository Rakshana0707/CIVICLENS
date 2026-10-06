# CIVICLENS TN — Phase 3.19
## Real Promise Dataset Validation & Normalization Report

> **DISCLAIMER: DATA QUALITY ASSESSMENT ONLY**
> This report evaluates data quality, text integrity, provenance completeness, Tamil Unicode formatting, and duplicate detection for the extracted real manifesto promises dataset.
> **This report does NOT claim that any political promise is implemented, partially implemented, unfulfilled, or failed.** Implementation status assessments occur in separate downstream analytical modules.

---

## 1. Overview & Dataset Validation Metrics

- **Total Promises Evaluated**: `1065`
- **Validation Execution Date**: `2026-10-06T13:35:50.826727+00:00`
- **Primary Corpus File**: `data/processed/promises/extracted_promises.json`

### Validation Status Breakdown

| Validation Status | Count | Percentage | Description |
| :--- | :---: | :---: | :--- |
| **`valid`** | **380** | **35.7%** | Fully structured, non-duplicate, valid Unicode, clean text with complete provenance. |
| **`needs_review`** | **622** | **58.4%** | Valid promise content requiring minor review (e.g. Tamil diacritic alignment, uncategorized taxonomy, or fragment warning). |
| **`probable_duplicate`** | **55** | **5.2%** | High text/token similarity (>= 85%) with another extracted promise record. |
| **`duplicate`** | **8** | **0.8%** | Exact normalized text duplicate of an existing record. |
| **`invalid`** | **0** | **0.0%** | Empty text, pure header/page-number artifact, or corrupt/unreadable content. |
| **TOTAL** | **1065** | **100.0%** | Comprehensive evaluation of Phase 3.18 extracted dataset. |

---

## 2. Provenance & Required Field Completeness

Every real promise was evaluated across all 9 required schema parameters:

| Field Name | Description | Missing Count | Completeness Rate |
| :--- | :--- | :---: | :---: |
| `promise_id` | Unique primary key identifier | `0` | 100.0% |
| `manifesto_id` | Source manifesto association | `0` | 100.0% |
| `document_id` | Source document reference | `0` | 100.0% |
| `page_number` | Page provenance (>= 1) | `0` | 100.0% |
| `section` | Section header / page context | `0` | 100.0% |
| `original_text` | Exact verbatim source text | `0` | 100.0% |
| `normalized_text` | Cleaned/formatted representation | `0` | 100.0% |
| `language` | English, Tamil, or Mixed | `0` | 100.0% |
| `category` | Domain category classification | `0` | 100.0% |
| `classification` | Specific promise or general policy | `0` | 100.0% |
| `confidence` | Extraction confidence score | `0` | 100.0% |

> [!NOTE]
> All `1065` extracted records contain 100% of required identifier, provenance, and source text fields.

---

## 3. Text Quality, Formatting & Anomaly Detection

| Anomaly Detector | Flagged Records | Category & Impact | Resolution / Handling Strategy |
| :--- | :---: | :--- | :--- |
| **Broken Tamil Unicode** | `365` | Font encoding artifacts in older PDF extractions causing diacritics to follow spaces/newlines. | Flagged as `needs_review`. Original wording preserved; normalized view formatted cleanly. |
| **OCR Replacement Chars** | `42` | Replacement characters (`?`) or control chars in scanned PDF extractions. | Flagged as `needs_review`. Original text retained. |
| **Incomplete Sentences** | `90` | Sentence fragments starting with lowercase verbs or ending abruptly. | Flagged as `needs_review`. Preserved in dataset without deletion. |
| **Exact Duplicates** | `8` | Identical normalized text repeated in the document. | Classified as `duplicate`. Retained in database for audit provenance. |
| **Probable Duplicates** | `55` | High token Jaccard similarity (>= 85%) across pages. | Classified as `probable_duplicate`. Linked to reference record ID. |

---

## 4. Dataset Distribution Metrics

### Category Distribution

| Category Name | Record Count | Percentage |
| :--- | :---: | :---: |
| Uncategorized | 511 | 48.0% |
| Welfare | 76 | 7.1% |
| Education | 70 | 6.6% |
| Agriculture | 60 | 5.6% |
| Healthcare | 54 | 5.1% |
| Infrastructure | 53 | 5.0% |
| Employment | 46 | 4.3% |
| Environment | 31 | 2.9% |
| Transport | 29 | 2.7% |
| Industry | 25 | 2.3% |
| Women | 24 | 2.3% |
| Finance | 24 | 2.3% |
| Housing | 23 | 2.2% |
| Governance | 14 | 1.3% |
| Youth | 11 | 1.0% |
| Social protection | 10 | 0.9% |
| Digital services | 4 | 0.4% |

### Party Distribution

| Political Party | Record Count | Percentage |
| :--- | :---: | :---: |
| AIADMK | 386 | 36.2% |
| BJP | 338 | 31.7% |
| PMK | 311 | 29.2% |
| MNM | 30 | 2.8% |

### Election Year Distribution

| Election Year | Record Count | Percentage |
| :--- | :---: | :---: |
| 2026 | 724 | 68.0% |
| 2016 | 311 | 29.2% |
| 2021 | 30 | 2.8% |

---

## 5. Conclusion & Dataset Readiness

1. **Validation Complete**: All 1,065 extracted real manifesto promises have been thoroughly validated, scored, and categorized.
2. **Zero Missing Provenance**: 100% of records maintain complete traceability to their source manifesto, document ID, page number, and section.
3. **No Automatic Deletion**: Questionable records, duplicates, and Tamil Unicode font artifact statements have been preserved and explicitly flagged (`needs_review`, `duplicate`, `probable_duplicate`) rather than deleted.
4. **Data Quality Status**: **Phase 3 promise dataset validated and ready for matching & assessment engines.**
