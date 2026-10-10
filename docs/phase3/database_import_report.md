# CIVICLENS TN — Phase 3.20
## Real Manifesto & Promise Database Import Report

> **IMPORT AUDIT STATUS: SUCCESSFUL & VERIFIED**
> All validated real manifesto documents, sources, political parties, election metadata, category taxonomies, and political promises have been imported into the Phase 3 SQLite database (`civiclens.db`).
> **Count Verification**: Database total records match the source dataset exactly (`1065` == `1065`).

---

## 1. Import Overview & Execution Metrics

- **Execution Date**: `2026-10-10T12:05:28.764256+00:00`
- **Target Database**: `civiclens.db`
- **Source Corpus File**: `data/processed/promises/validated_promises.json`
- **Source Manifest File**: `data/raw/manifestos/manifest.json`

### Record Execution Summary

| Metric Name | Count | Description |
| :--- | :---: | :--- |
| **Total Records Discovered** | **1065** | Extracted & validated promise records in source dataset. |
| **Total Records Imported** | **1065** | Successfully inserted into SQLite `political_promises` table. |
| **Records Skipped / Updated** | **0** | Existing records preserved via idempotent upsert logic. |
| **Records Rejected** | **0** | Invalid records rejected from primary dataset. |
| **Exact Duplicates** | **8** | Identical normalized text records preserved with `duplicate` status. |
| **Probable Duplicates** | **55** | High token similarity records preserved with `probable_duplicate` status. |
| **Database Errors** | **0** | Transactional errors encountered during import. |

---

## 2. Relational Hierarchy & Table Counts

Every imported promise maintains 100% foreign key lineage:
`Promise` $\rightarrow$ `Manifesto` $\rightarrow$ `Document` $\rightarrow$ `Source` $\rightarrow$ `Original File`

| Database Entity Table | Model Class | Verified DB Record Count |
| :--- | :--- | :---: |
| `manifesto_sources` | `ManifestoSource` | `20` |
| `manifesto_documents` | `ManifestoDocument` | `20` |
| `manifestos` | `Manifesto` | `19` |
| `promise_categories` | `PromiseCategory` | `17` |
| `political_promises` | `PoliticalPromise` | `1065` |

---

## 3. Imported Dataset Distributions

### Distribution by Party

| Political Party | Imported Promises | Percentage |
| :--- | :---: | :---: |
| AIADMK | 386 | 36.2% |
| BJP | 338 | 31.7% |
| PMK | 311 | 29.2% |
| MNM | 30 | 2.8% |

### Distribution by Election Year

| Election Year | Imported Promises | Percentage |
| :--- | :---: | :---: |
| 2026 | 724 | 68.0% |
| 2016 | 311 | 29.2% |
| 2021 | 30 | 2.8% |

### Distribution by Domain Category

| Category Name | Imported Promises | Percentage |
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

### Distribution by Language

| Language | Imported Promises | Percentage |
| :--- | :---: | :---: |
| English | 697 | 65.4% |
| Tamil | 357 | 33.5% |
| Mixed | 11 | 1.0% |

---

## 4. Lineage & Foreign-Key Integrity Verification

1. **Idempotent Import**: Re-running the import script executes cleanly without corrupting keys or duplicating rows.
2. **Transactional Integrity**: All writes are committed inside single transactional sessions with automatic rollback on error.
3. **Traceability**: All 1,065 imported promises maintain valid `manifesto_id` foreign keys pointing to verified `manifestos` records, which link to physical `manifesto_documents` and `manifesto_sources`.
4. **Audit Status**: **Phase 3 SQLite database fully populated with real Tamil Nadu manifesto dataset and ready for Phase 3 API/Frontend integration.**
