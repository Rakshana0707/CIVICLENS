# Phase 10 — Policy Evaluation Data Acquisition Pipeline

## 1. Executive Summary & Purpose

Phase 10.2 of **CIVICLENS TN** implements the **Policy Evaluation Data Acquisition Pipeline**. 

Its purpose is to provide a robust, multi-format, respectful ingestion engine capable of acquiring and processing the empirical evidence required for policy evaluation:
- State Budget Books, Detailed Demands for Grants (DDG), and Appropriation Accounts
- Department Policy Notes, Citizens' Charters, and Government Orders (GOs)
- Comptroller and Auditor General (CAG) State Finances and Performance Audit Reports
- Structured survey datasets (NFHS, UDISE+, AISHE, Census PCA) in CSV, JSON, and Excel
- Digital Sansad (Parliament Q&A) and state assembly debates
- Independent policy evaluation reports and academic evaluations

```
[Raw Sources: Portals / Local Storage]
        |
        v
+--------------------------------------------------------------------------+
| 1. SOURCE REGISTRY & POLICIES                                            |
|    Domain whitelisting, rate limiting, robots & disallowed path checks   |
+--------------------------------------------------------------------------+
        |
        +----------------------------+
        |                            |
        v                            v
[Automated Downloader]     [Manual Document Importer]
(Polite backoff retry)      (For OTP / CAPTCHA gates)
        |                            |
        +----------------------------+
        |
        v
+--------------------------------------------------------------------------+
| 2. PAYLOAD VALIDATION & DEDUPLICATION                                    |
|    SHA-256 hashing, duplicate detection, payload preservation            |
+--------------------------------------------------------------------------+
        |
        v
+--------------------------------------------------------------------------+
| 3. FILE TYPE DETECTION & MULTI-FORMAT EXTRACTION                         |
|    - PDF: Text & table extraction (pdfplumber) + OCR fallback            |
|    - HTML: HTMLTableParser + plain text extraction                       |
|    - Structured: CSV, JSON, Excel (xlsx) tabular parser                  |
+--------------------------------------------------------------------------+
        |
        v
+--------------------------------------------------------------------------+
| 4. METADATA ENRICHMENT & PRIVACY                                         |
|    - ISO-8601 UTC retrieval timestamps                                   |
|    - Publication date extraction (GO dates, CAG years, fiscal years)     |
|    - Automated PII scrubbing (DPDPA 2023 compliance)                     |
+--------------------------------------------------------------------------+
        |
        v
[PolicyAcquisitionResult + Storage Sidecar (.meta.json)]
        |
        v
[Phase 9 Unified Evidence Graph: CivicGraphNode & CivicEvidenceEdge]
```

---

## 2. Core Functional Modules

The acquisition pipeline is located at [`backend/acquisition/policy_evaluation_acquisition.py`](file:///e:/CIVCLENS/backend/acquisition/policy_evaluation_acquisition.py) and consists of 9 integrated components:

### 2.1 Source Registry Integration (`PolicyEvaluationSourceRegistry`)
Maintains source-specific profiles specifying access conditions, domain whitelists, rate limits, and supported formats:
1. `TN_BUDGET`: `https://tnbudget.tn.gov.in/` (Tier 1 Statutory; 2.0s rate limit)
2. `TN_GOV_POLICY`: `https://www.tn.gov.in/` (Tier 1 Statutory; 2.0s rate limit)
3. `CAG_AUDIT`: `https://cag.gov.in/` (Tier 1 Statutory; 2.5s rate limit)
4. `DATA_GOV_IN`: `https://data.gov.in/` (Tier 2 Official Agency; 2.0s rate limit)
5. `CENSUS_SRS`: `https://censusindia.gov.in/` (Tier 2 Official Agency; 2.0s rate limit)
6. `SANSAD_PARLIAMENT`: `https://sansad.in/` (Tier 1 Statutory; 2.0s rate limit)
7. `TN_SPC`: `https://spc.tn.gov.in/` (Tier 2 Official Agency; 2.0s rate limit)
8. `LOCAL_FIXTURE`: `http://test-fixture.civiclens.internal/` (Tier 1 Test Environment)

### 2.2 Download and Manual-Import Support
- **Automated Download:** Implemented via standard HTTP client with configurable timeouts (15s default), exponential backoff retries (3 attempts), domain rate limiting, and polite bot identification (`CIVICLENS-TN-PolicyEvaluation/1.0`).
- **Manual Import Interface:** A dedicated workflow for offline documents from portals protected by technical access controls (e.g., OTP-protected citizen portals, intranet evaluations). The pipeline computes checksums, validates file signatures, and processes offline files identically to downloaded items.

### 2.3 File Type Detection (`FileTypeDetector`)
Employs a multi-tiered identification strategy:
1. **Magic Bytes:**
   - PDF: `%PDF-` (`0x25 0x50 0x44 0x46`)
   - Excel (XLSX): `PK\x03\x04` (Zip archive container)
   - Excel (Legacy XLS): `\xD0\xCF\x11\xE0\xA1\xB1\x1A\xE1` (OLE2 Compound Document)
2. **Text Sniffing:**
   - HTML: `<!DOCTYPE html`, `<html>`, `<body>`
   - JSON: Leading `{` or `[` validated by `json.loads`
   - CSV: Delimiter sniffing (comma, tab, semicolon) across lines
3. **Extension & MIME Fallback:** Mappings for `.pdf`, `.csv`, `.tsv`, `.json`, `.xlsx`, `.xls`, `.html`.

### 2.4 PDF Text and Table Extraction (`PolicyPDFExtractor`)
- Utilizes `pdfplumber` for layout-aware text extraction and table identification.
- Normalizes multi-line table headers and converts tabular matrices into structured lists of dictionaries.
- Tracks page numbers and character counts for every page to detect scanned or raster content.

### 2.5 OCR Fallback Protocol (`PolicyOCRFallbackHandler`)
- If a page has fewer than 30 extracted characters, it is classified as a scanned/raster page.
- If `pytesseract` is installed and functioning, OCR is attempted with bilingual English and Tamil dictionaries (`eng+tam`).
- If OCR is unavailable or fails, the pipeline generates a structured fallback record:
  - `ocr_status = "OCR_REQUIRED_FALLBACK"`
  - `ocr_used = False`
  - Explicit warning text embedded with page indices, instructing human reviewers or flagging the document for external OCR preprocessing.

### 2.6 Structured Dataset Ingestion (`StructuredDatasetIngestor`)
- **CSV Ingestion:** Parses comma, tab, and semicolon delimited files into row dictionaries, with automated whitespace stripping and PII scrubbing.
- **JSON Ingestion:** Ingests arrays of objects or nested structures into tabular matrices.
- **Excel (XLSX) Ingestion:** Inspects worksheets using standard XML container extraction, extracting tabular rows and column headers.
- **HTML Table Ingestion:** Uses zero-dependency `PolicyHTMLTableParser` to convert HTML `<table>`, `<tr>`, `<th>`, `<td>` structures into normalized record dictionaries.

### 2.7 Cryptographic Checksums & Duplicate Detection (`PolicyStorageManager`)
- Calculates SHA-256 digests over raw byte streams.
- Preserves raw payloads under `data/raw/policy_evaluation/<sha256>.<ext>`.
- Generates sidecar metadata files `<sha256>.meta.json` containing URL, timestamp, format, size, and source tier.
- Detects duplicates in-memory and on-disk, setting `is_duplicate = True` and `status = "DUPLICATE"` to prevent redundant downstream processing.

### 2.8 ISO-8601 UTC Retrieval Timestamps
- Every acquired document records an exact UTC timestamp (`retrieved_at = datetime.now(timezone.utc)`), ensuring complete temporal provenance.

### 2.9 Publication Date Extraction (`PublicationDateExtractor`)
Extracts formal publication dates from document headers and text:
- **Government Orders:** `Dated: DD.MM.YYYY` or `DD/MM/YYYY`
- **Spelled-Out Dates:** `DD Month YYYY` (e.g., `20 March 2024`)
- **ISO Dates:** `YYYY-MM-DD`
- **CAG Reports:** `Report No. X of YYYY` -> standardized to `YYYY-03-31`
- **Fiscal Years:** `YYYY-YYYY` or `YYYY-YY` (e.g., `2023-2024`)

### 2.10 Processing & Error Logs (`PolicyAcquisitionLogger`)
- Captures all failures with structured error classifications:
  - `DOMAIN_NOT_WHITELISTED`
  - `DISALLOWED_PATH`
  - `DOWNLOAD_ERROR`
  - `FILE_READ_ERROR`
  - `PDF_CORRUPT_OR_UNREADABLE`
- Retains HTTP status codes, retry counts, timestamps, and error messages.

---

## 3. Ethical Acquisition & Legal Compliance

1. **Non-Invasive Collection:**
   - Scrapers enforce per-domain rate limiting (minimum 2.0s per request).
   - All HTTP requests carry transparent User-Agent headers declaring research intent and contact endpoints.
   - Respects robots policies and disallowed administrative/login paths.
2. **Technical Controls Integrity:**
   - **No authentication bypass:** The pipeline does not attempt to circumvent logins, OTP verifications, or CAPTCHA challenges.
   - Protected or session-gated reports are acquired strictly through the authorized `ManualDocumentImporter`.
3. **Citizen Privacy (DPDPA 2023):**
   - All extracted text and tabular cell values pass through `sanitize_pii()`, redacting mobile numbers, Aadhaar numbers, private emails, and personal address markers before persistence.
4. **Zero Fabrication:**
   - Missing reports are recorded as `FAILED` or `NOT_FOUND` in the error log.
   - The pipeline never generates synthetic text or assumes a report exists simply because a URL structure is known.

---

## 4. Local Fixture Testing & Failure Handling Strategy

The acquisition pipeline is thoroughly tested using offline fixtures in `tests/fixtures/phase10_acquisition_fixtures.py` and `tests/unit/test_phase10_acquisition_pipeline.py`:
- Synthetic Government Order PDF (`.pdf`)
- Detailed Demand for Grants tabular CSV (`.csv`)
- Department Scheme Beneficiaries JSON (`.json`)
- State Assembly Web Page with HTML Tables (`.html`)
- Scanned Raster PDF triggering OCR fallback (`.pdf`)
- Corrupted / Malformed PDF testing graceful parse error handling
- Restricted Path testing robots policy enforcement
- Duplicate payload testing SHA-256 deduplication
