# Phase 6: Real Dataset Inspection & Audit Report

**CIVICLENS TN — Phase 6.10 Ingestion Audit**  
**Audit Date:** 2026-10-11  
**Target Location:** `E:\Downloads` (located on disk as `E:\Downloads ??`)  
**Preservation Target:** `data/raw/phase6/`

---

## 1. Directory Audit & Discovered Files

An exhaustive inspection of the user's storage drive identified the following two target datasets provided for Phase 6:

| Dataset Identifier | File Name on Disk | Original Format | Preserved Format | Size (Bytes) | SHA-256 Checksum |
|---|---|---|---|---|---|
| **Phase 6 DS 1** | `Phase 6 DS 1` | ZIP Archive | `data/raw/phase6/Phase_6_DS_1.zip` | 8,110 bytes | `a6a27570050492d190282ca6d01894264154205b9c37a4db4cbbd5ea70b008ee` |
| **Phase 6 DS 2** | `Phase 6 DS 2` | RFC 4180 CSV | `data/raw/phase6/Phase_6_DS_2.csv` | 6,802 bytes | `da9d17abf47f4bfbe12b6a5bab4813c101c92ee3a84c835c82573bdd1c145b01` |

---

## 2. Archive Inspection: Phase 6 DS 1

Inspection of the ZIP archive `Phase_6_DS_1.zip` revealed three canonical tracking and provenance documents:

1. **`master_dataset_inventory.csv` (17,776 bytes, 45 records):**
   - Comprehensive statutory catalog mapping 45 official datasets across Parliament, Tamil Nadu Legislative Assembly, MPLADS, State Budget, Census 2011, and Department of Economics and Statistics (DES TN).
   - **Download Status Breakdown:**
     - `located_only`: 40 records (official government URLs identified, sandbox network boundaries prevent unauthenticated downloading).
     - `not_found`: 2 records (`D8-006` MPLADS portal work-level export, `D12-004` data.gov.in district resources).
     - `inaccessible`: 3 records (`D13-001`, `D14-001`, `D15-001` representing Phase 3, 4, 5 files).
2. **`integration_manifest.md` (1,545 bytes):**
   - Enforces the non-fabrication rule: confirms no synthetic records are to be manufactured. Outlines the schema dependencies for manifesto promises, news coverage, and political funding.
3. **`batch2_source_coverage_report.md` (1,400 bytes):**
   - Documents available statutory sources: TN Legislature digital archive (1921–present), PRS MP Track & MLA Track, NeVA TN notices, Parliament Unstarred questions, Census 2011 digital library, and DES Handbooks.

---

## 3. CSV Inspection: Phase 6 DS 2

`Phase_6_DS_2.csv` contains 19 election, candidate, and parliamentary datasets:
- **Election Results:** ECI May 2026 Assembly results pages (`D2-001`), Lok Sabha 2024 results portal covering 39 TN PCs (`D3-001`), TCPD Indian Elections Data (`D3-004`), and 2016 Narrative Report (`D2-006`).
- **Incumbency & Representatives:** TCPD Individual Incumbency Dataset (`D1-001`), PRS MP Track 17th Lok Sabha (`D1-002`).
- **Verified MP Performance Observations:**
  - `D4-001`: Dr. T.R. Paarivendhar (Perambalur PC) — 62% attendance, 40 debates, 268 questions.
  - `D4-002`: Dr. M.K. Vishnu Prasad (Arani PC) — 78% attendance, 29 debates, 254 questions.
  - `D4-003`: P.R. Natarajan (Coimbatore PC) — 86% attendance, 56 debates, 253 questions.
- **Parliamentary Questions:** TCPD Lok Sabha Questions 1999–2019 (`D3Q-001`), Lok Sabha community repository (`D3Q-002`).
- **Honors & Awards:** Sansad Ratna 16th Lok Sabha partial report (`D5-001`).

---

## 4. Preservation & Storage Layout

Original files were extracted and preserved into the project repository without overwriting existing fixtures:
```
data/raw/phase6/
├── Phase_6_DS_1.zip
├── Phase_6_DS_2.csv
└── Phase_6_DS_1/
    ├── batch2_source_coverage_report.md
    ├── integration_manifest.md
    └── master_dataset_inventory.csv
```
All original SHA-256 signatures are recorded and validated.
