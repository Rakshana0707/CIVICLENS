# Real News Dataset Inspection Report (Multi-Dataset Audit)

**Project**: CIVICLENS TN — Phase 4 Tamil News Bias & Political Coverage Analyzer  
**Date**: October 10, 2026  
**Status**: Multi-Dataset Verification, Inspection & Extraction Complete  

---

## 1. Dataset Provenance & Archive Metadata

Three real Phase 4 news datasets were located within `E:\Downloads 🔄`, inspected, and extracted into `data/raw/news/`.

| Dataset Name | File Format | File Size | SHA-256 Checksum | Target Directory |
| :--- | :--- | :--- | :--- | :--- |
| **News CivicLens** | ZIP Archive | 38,678 bytes | `12e4fea737d27495423e03da9e26c189d4f585fcb9fd8524ff7006638c58d30b` | `data/raw/news/` |
| **News CivicLens DS** | ZIP Archive | 151,757 bytes | `0b85b2c353fce22b0bbc230656d422ecebae41086a26a6787748f6258d63bbeb` | `data/raw/news/ds1/` |
| **News CivicLens DS 2** | ZIP Archive | 222,216 bytes | `3038de5cc125e52d8b653e0bd75595852a9a5994d33a677dae22285f5f0cae3b` | `data/raw/news/ds2/` |

All original archives remain preserved while extracted contents are registered under `data/raw/news/`.

---

## 2. Archive Structure & Inventory

### Archive 1: `News CivicLens` (Batch 1 Initial Release)
- `dataset_A_news_articles_batch1.csv`: 72 articles (37 Tamil, 35 English)
- `dataset_B_political_events_batch1.csv`: 13 political events
- `dataset_E_source_metadata_batch1.csv`: 44 news sources
- `dataset_D_official_references_batch1.csv`: 1 official reference
- `source_verification_log_batch1.csv`: 72 verification logs (12 verified, 47 partially verified, 7 unverified, 6 rejected)

### Archive 2: `News CivicLens DS` (Batch 1 + Batch 2 Iteration)
- Contains `civiclens_step1_step2partial.zip` with `data/batch1/` and `data/batch2/`
- `dataset_A_news_articles_batch2.csv`: 72 articles with updated verification logs (15 verified, 44 partially verified, 7 unverified, 6 rejected)
- `dataset_A_strict_verified_batch2.csv`: 15 strictly verified articles
- `dataset_B_political_events_batch2.csv`: 13 political events

### Archive 3: `News CivicLens DS 2` (Phase 2 Consolidated Release & Dataset C)
- Contains `civiclens_phase2.zip` with consolidated ground-truth datasets:
  - `dataset_A_news_articles.csv`: 72 articles (17 verified, 42 partially verified, 7 unverified, 6 rejected)
  - `dataset_B_political_events.csv`: 13 political events
  - `dataset_C_political_entities.csv`: **47 ground-truth political entities** (TVK, DMK, AIADMK, BJP, Congress, etc., with Tamil and English names and party codes)
  - `dataset_C_aliases.csv`: **19 entity alias mappings** (e.g. Vijay, M.K. Stalin, Edappadi K. Palaniswami, K. Annamalai)
  - `dataset_C_evidence_notes.csv`: **47 evidence notes**
  - `dataset_D_official_references.csv`: **4 official government references** (PRS TN Budget Analysis, Finance Minister Budget Speech 5 Aug 2026, ECI Madurantakam Bye-Election Notification, TN Home Dept Police Duty G.O.)
  - `dataset_E_source_metadata.csv`: 44 news sources

---

## 3. Dataset Verification Progression

Across the dataset iterations, the verification pipeline yielded progressive audit enhancements:

| Dataset Iteration | Total Articles | Verified | Partially Verified | Unverified | Rejected | Strictly Verified Subset |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Batch 1 (`News CivicLens`)** | 72 | 12 | 47 | 7 | 6 | 12 |
| **Batch 2 (`News CivicLens DS`)** | 72 | 15 | 44 | 7 | 6 | 15 |
| **Phase 2 (`News CivicLens DS 2`)** | 72 | 17 | 42 | 7 | 6 | 17 |

---

## 4. Ground-Truth Entities & Official References

- **Political Entities (Dataset C)**: 47 entities spanning:
  - `party`: TVK (Tamilaga Vettri Kazhagam), DMK, AIADMK, BJP, Congress, NTK, VCK, PMK, MDMK, CPI(M), CPI
  - `person`: M.K. Stalin, Vijay, Edappadi K. Palaniswami, K. Annamalai, Seeman, Thol. Thirumavalavan, Dr. S. Ramadoss, Udhayanidhi Stalin, Kanimozhi, Nirmala Sitharaman, Dr. N. Marie Wilson
  - `department`: Finance Dept, School Education Dept, Agriculture Dept, Health Dept, Municipal Administration, Police Dept
  - `location / constituency`: Tamil Nadu, Chennai, Madurantakam (SC), Dharapuram (SC), Vikravandi, Coimbatore
- **Official References (Dataset D)**: 4 primary government & independent legislative documents.

---

## 5. Unicode Integrity & Character Encoding

- All Tamil text columns across `dataset_A_news_articles.csv`, `dataset_C_political_entities.csv`, and `dataset_C_aliases.csv` are fully UTF-8 encoded.
- Zero encoding glitches, lost characters, or surrogate pair breakages observed.
