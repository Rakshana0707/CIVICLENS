# CIVICLENS TN — Phase 3 Real Manifesto Promise Extraction Report

**Date:** October 6, 2026  
**Module:** Phase 3.18 — Real Manifesto Promise Extraction  
**Dataset ID:** `DS-TN-MANIFESTOS-20261006`  
**Database:** `civiclens.db` (`political_promises` table)  
**Processed Promises Output:** `data/processed/promises/extracted_promises.json`  

---

## Executive Summary

This report documents the extraction, classification, normalization, taxonomy mapping, and database persistence of real political promises from the **CIVICLENS TN Real Manifesto Dataset**.

All extracted candidate statements originate strictly from the actual manifesto documents processed in Phase 3.17. No synthetic promises or manually invented data were introduced.

---

## 1. Candidate Statement Classification Summary

A total of **14,105 candidate statements** were segmented and evaluated across the 20 manifesto documents using `rule_based_v1` classification heuristics.

| Classification | Count | Percentage | Dataset Action |
|---|---|---|---|
| **`specific_promise`** | 266 | 1.89% | **Accepted into Primary DB** |
| **`general_policy`** | 799 | 5.66% | **Accepted into Primary DB** |
| **`slogan`** | 3,870 | 27.44% | Filtered / Excluded from DB |
| **`vision`** | 43 | 0.30% | Filtered / Excluded from DB |
| **`ambiguous`** | 9,127 | 64.71% | Preserved as raw context / Excluded from DB |
| **Extraction Failures** | 0 | 0.00% | None |
| **Total Candidates** | **14,105** | **100.0%** | **1,065 Accepted Promises & Policies** |

---

## 2. Accepted Promises Breakdown

### A. Promises by Political Party

| Political Party | Accepted Promises | Specific Promises | General Policies |
|---|---|---|---|
| **AIADMK** (All India Anna Dravida Munnetra Kazhagam) | 386 | 98 | 288 |
| **BJP** (Bharatiya Janata Party) | 338 | 84 | 254 |
| **PMK** (Paataali Makkal Katchi - 2016 Synopsis) | 311 | 79 | 232 |
| **MNM** (Makkal Needhi Maiam) | 30 | 5 | 25 |
| **Total** | **1,065** | **266** | **799** |

---

### B. Promises by Election Year

| Election Year | Document Count | Accepted Promises |
|---|---|---|
| **2016** | 4 | 311 |
| **2021** | 5 | 30 |
| **2026** | 6 | 724 |
| **Total** | **15** | **1,065** |

---

### C. Promises by Language

| Language | Extracted Promises | Tamil Text Preservation Status |
|---|---|---|
| **English (`en`)** | 697 | Standard English text |
| **Tamil (`ta`)** | 357 | **Original Tamil Script Strictly Preserved** |
| **Mixed / Bilingual (`ta`/`en`)** | 11 | Both language scripts preserved |
| **Total** | **1,065** | **Zero translation loss** |

---

### D. Promises by Category Taxonomy

Promises were mapped against the 18-category taxonomy configured in `config/promise_taxonomy.json`. Ambiguous or un-keyworded promises are assigned to `Uncategorized` rather than forced into rigid categories.

| Category Taxonomy | Accepted Promises | Percentage |
|---|---|---|
| **Uncategorized** (Conservative Rule) | 511 | 47.98% |
| **Welfare** | 76 | 7.14% |
| **Education** | 70 | 6.57% |
| **Agriculture** | 60 | 5.63% |
| **Healthcare** | 54 | 5.07% |
| **Infrastructure** | 53 | 4.98% |
| **Employment** | 46 | 4.32% |
| **Environment** | 31 | 2.91% |
| **Transport** | 29 | 2.72% |
| **Industry** | 25 | 2.35% |
| **Women** | 24 | 2.25% |
| **Finance** | 24 | 2.25% |
| **Housing** | 23 | 2.16% |
| **Governance** | 14 | 1.31% |
| **Youth** | 11 | 1.03% |
| **Social Protection** | 10 | 0.94% |
| **Digital Services** | 4 | 0.38% |
| **Total** | **1,065** | **100.0%** |

---

## 3. Metadata Normalization Rules

For every accepted promise, metadata attributes were extracted where present:

- `target_population`: e.g. "women heads of households", "small farmers", "college students"
- `sector` / `department`: e.g. "School Education", "Health & Family Welfare", "Agriculture"
- `proposed_action`: e.g. "Construct / Establish", "Transfer", "Waive", "Provide"
- `numeric_target`: e.g. "50 new primary health centres", "50,000 jobs", "100 units"
- `monetary_target`: e.g. "₹500 crore", "₹1,000 per month", "₹50,000"
- `time_horizon`: e.g. "within 3 years", "annually", "in 2 years"
- `implementation_mechanism`: e.g. "Direct Bank Transfer", "Government Order"

*Rule Enforced:* Unspecified metadata fields default to `null` / `unknown`. Unsupported details are never inferred.

---

## 4. Provenance & Database Record Structure

Every extracted promise record persists complete provenance traceability:

```json
{
  "promise_id": "MF-AIADMK-2026:p1:8301f92e4a",
  "manifesto_id": "MF-AIADMK-2026",
  "document_id": "DOC-MANIFESTO-FILE-016",
  "source_file_id": "MANIFESTO-FILE-016",
  "original_text": "மகளிர் மேம்பாட்டிற்காக மாதம் ₹1,000 நேரடியாக வழங்கப் படும்.",
  "normalized_text": "மகளிர் மேம்பாட்டிற்காக மாதம் ₹1,000 நேரடியாக வழங்கப் படும்.",
  "page_number": 1,
  "section": "Welfare & Women",
  "language": "Tamil",
  "category": "Welfare",
  "classification": "specific_promise",
  "extraction_method": "rule_based_v1",
  "confidence": 0.8,
  "created_at": "2026-10-06T15:54:41.610Z"
}
```

---

## Conclusion

The Real Manifesto Promise Extraction pipeline is complete. **1,065 accepted political promises and policies** have been extracted from real manifesto documents, normalized, and saved into the primary `PoliticalPromise` database (`civiclens.db`).
