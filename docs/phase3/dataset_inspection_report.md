# CIVICLENS TN — Phase 3 Real Manifesto Dataset Inspection & Registration Report

**Date:** October 6, 2026  
**Dataset ID:** `DS-TN-MANIFESTOS-20261006`  
**Dataset Name:** CIVICLENS TN Real Political Manifesto Dataset (1996–2026)  
**Status:** **REGISTERED & INVENTORIED**  

---

## 1. Dataset Overview

- **Total Extracted Files:** 20 files
- **Total Compressed Size:** 141,621,174 bytes (135.06 MB)
- **Total Uncompressed Size:** 148,098,827 bytes (141.24 MB)
- **Election Years Covered:** 1996, 2001, 2006, 2011, 2016, 2021, 2026
- **Political Parties Covered:** DMK, AIADMK, INC (Congress), BJP, NTK, TVK, MNM, MDMK, PMK
- **Storage Location:** `data/raw/manifestos/real_manifestos_20261006/`
- **Registry Manifest:** `data/raw/manifestos/manifest.json`

---

## 2. ZIP Archive Information

- **ZIP Filename:** `Manifestos.zip`
- **Absolute Source Path:** `C:\Users\Shiv Rakshana\AppData\Local\Packages\5319275A.WhatsAppDesktop_cv1g1gvanyjgm\LocalState\sessions\41702EBA7FCF775C469AE200A92D3D74C7612B6D\transfers\2026-40\Manifestos.zip`
- **File Size:** 141,621,174 bytes (135.06 MB)
- **Modification Timestamp:** `2026-10-06T09:37:25.150951+00:00`
- **SHA-256 Checksum:** `5d61bc577f859b919277dcd347728f8c1f5fa28784b9598b87876647523c52de`
- **Archive Status:** Untouched, preserved exactly in raw original state.

---

## 3. Extracted File Count & Structure

The dataset contains 20 document files organized across 4 subdirectories:

```text
data/raw/manifestos/real_manifestos_20261006/
├── dataset_registration.json
└── Manifestos/
    ├── Tamil_Nadu_Manifesto_Archive_1996.pdf
    ├── Tamil_Nadu_Manifesto_Archive_1996_2011_Master.pdf
    ├── Tamil_Nadu_Manifesto_Archive_2001.pdf
    ├── Tamil_Nadu_Manifesto_Archive_2006.pdf
    ├── Tamil_Nadu_Manifesto_Archive_2011.pdf
    ├── 2016/
    │   ├── ADMK-Therthal-Arikkai-2016-Tamil-PDF-Tamilnadu-Election-Manifesto-2016-Full-List.pdf
    │   ├── Manifesto-Synopsis_2824129a.pdf
    │   ├── congress.docx
    │   └── dmk2016Manifesto_E_2811452a.pdf
    ├── 2021/
    │   ├── 4-AIADMK Election Manifesto - 14.03.2021.pdf
    │   ├── 501785333-DMK-Election-Manifesto-2021.pdf
    │   ├── MDMK Election Manifesto 2021.pdf
    │   ├── MNM-MANIFESTO-DOCUMENT-19th mar 2021 (1).pdf
    │   └── Tamil Nadu 2021 Assembly Election BJP Vision Document vTamil (1).pdf
    └── 2026/
        ├── DMK_Manifesto_English_2026.pdf
        ├── aiadmk-election-manifesto-assembly-general-election-2026.pdf
        ├── aiadmk-manifesto-2026-english.pdf
        ├── ntk-2026-manifesto_compressed.pdf
        ├── tnbjp_manifesto_2026_compressed.pdf
        └── tvk_manifesto_2026_compressed.pdf
```

---

## 4. File Type Distribution

| Format Extension | File Count | Percentage | Primary Tool Chain |
|---|---|---|---|
| `.pdf` | 19 | 95.0% | `pypdf` / `pdfplumber` / Tesseract OCR |
| `.docx` | 1 | 5.0% | `python-docx` |
| **Total** | **20** | **100.0%** | |

---

## 5. Party Coverage

| Political Party | Document Count | Years Represented |
|---|---|---|
| **DMK** (Dravida Munnetra Kazhagam) | 3 | 2016, 2021, 2026 |
| **AIADMK** (All India Anna Dravida Munnetra Kazhagam) | 4 | 2016, 2021, 2026 (Tamil & English) |
| **INC** (Indian National Congress) | 1 | 2016 |
| **BJP** (Bharatiya Janata Party) | 2 | 2021, 2026 |
| **NTK** (Naam Tamilar Katchi) | 1 | 2026 |
| **TVK** (Tamilaga Vettri Kazhagam) | 1 | 2026 |
| **MNM** (Makkal Needhi Maiam) | 1 | 2021 |
| **MDMK** (Marumalarchi Dravida Munnetra Kazhagam) | 1 | 2021 |
| **PMK** (Paataali Makkal Katchi) | 1 | 2016 (Synopsis) |
| **Archives & Compilations** | 5 | 1996, 2001, 2006, 2011, Master (1996–2011) |

---

## 6. Election Year Coverage

- **1996:** 1 archive document (+ Master summary)
- **2001:** 1 archive document (+ Master summary)
- **2006:** 1 archive document (+ Master summary)
- **2011:** 1 archive document (+ Master summary)
- **2016:** 4 documents (AIADMK, DMK English, INC DOCX, PMK Synopsis)
- **2021:** 5 documents (AIADMK, DMK, MDMK, MNM, BJP)
- **2026:** 6 documents (AIADMK Tamil, AIADMK English, DMK English, NTK, BJP, TVK)

---

## 7. Language Coverage

- **Tamil (`ta`):** 11 documents
- **English (`en`):** 8 documents
- **Bilingual / Research Compilations (`ta`/`en`):** 1 document

---

## 8. Source Coverage

- All 20 files are extracted directly from official political party publications, election releases, and academic/archival manifesto compilations.
- *Note:* Source URLs are not embedded within filenames or archive headers and are initialized as `null` in `manifest.json` until linked in the provenance enrichment stage.

---

## 9. Duplicate Analysis

No files were automatically deleted. All 20 records were evaluated and classified:

| Classification | Count | Description / Affected Files |
|---|---|---|
| **`unique`** | 17 | Distinct manifesto documents representing unique parties, years, and languages. |
| **`different_version`** | 2 | `aiadmk-election-manifesto-assembly-general-election-2026.pdf` (Tamil) & `aiadmk-manifesto-2026-english.pdf` (English) represent language translation versions of the same 2026 manifesto. |
| **`probable_duplicate`** | 1 | `Tamil_Nadu_Manifesto_Archive_1996_2011_Master.pdf` consolidates content present in individual yearly archives (1996, 2001, 2006, 2011). |
| **`exact_duplicate`** | 0 | Zero exact byte-for-byte or SHA-256 collisions found. |

---

## 10. Missing Metadata

- `source_url`: Set to `null` for offline archive files (will be enriched via online registry).
- `party` / `election_year`: Set to `null` for multi-party research archive compilations (`Master.pdf`).

---

## 11. Corrupt or Unreadable Files

- **0 corrupt files:** All 19 `.pdf` files and 1 `.docx` file parsed cleanly without stream corruption errors.

---

## 12. Unsupported Formats

- **0 unsupported formats:** All files are standard PDF and DOCX formats compatible with Python dependencies (`pypdf`, `pdfplumber`, `python-docx`, `pytesseract`).

---

## 13. Potential OCR Requirements

Direct text extraction succeeded for 16 documents. **4 documents require OCR / layout image extraction**:

1. `dmk2016Manifesto_E_2811452a.pdf` (144 pages, rasterized PDF)
2. `501785333-DMK-Election-Manifesto-2021.pdf` (128 pages, rasterized PDF)
3. `tvk_manifesto_2026_compressed.pdf` (96 pages, scanned PDF)
4. `congress.docx` (7.6 MB, formatted layout requiring XML/image parsing)

---

## 14. Potential Parsing Issues

- **Legacy Font Encodings:** Older Tamil PDFs (e.g. 2016 AIADMK manifesto) use custom legacy font encodings (Baamini / TAB / TAM) requiring font mapping prior to Unicode NFC normalization.
- **Large Page Counts:** `ntk-2026-manifesto_compressed.pdf` contains 462 pages requiring chunked batch processing to prevent memory spikes.

---

## 15. Recommended Processing Path

```text
data/raw/manifestos/real_manifestos_20261006/
                    │
                    ▼
       data/raw/manifestos/manifest.json
                    │
                    ├───────────────────────────┐
                    ▼                           ▼
          Direct Text PDFs (16)       Scanned PDFs & DOCX (4)
                    │                           │
                    │                   Tesseract OCR / XML
                    │                           │
                    └─────────────┬─────────────┘
                                  ▼
                      Phase 3 Ingestion Pipeline
                   (Processor -> PromiseExtractor)
                                  │
                                  ▼
                   Promise Normalization & Taxonomy
                                  │
                                  ▼
                 PoliticalPromise Database (Phase 3.7)
```

---

## Conclusion & Integration Point

The real manifesto dataset is fully extracted, inventoried, hashed, and registered in `data/raw/manifestos/manifest.json`.

**Pipeline Entry Point Verified:**  
`data/raw/manifestos/manifest.json` $\rightarrow$ `backend.ingestion.processor` $\rightarrow$ `PromiseExtractor`.
