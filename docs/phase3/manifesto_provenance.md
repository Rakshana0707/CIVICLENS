# Manifesto Provenance Framework

## Objective
To ensure end-to-end traceability of political promises, CIVICLENS TN employs a rigid provenance framework for manifesto documents. This model ensures that any extracted political promise can be traced back to its exact origin, verified against a downloaded file hash, and evaluated within the context of the source's reliability tier.

## Data Dictionary

### 1. ManifestoSource (`manifesto_sources`)
Captures the origin metadata before any document is downloaded.
*   `source_id` (PK, String): Unique identifier for the source record.
*   `organization` (String): The entity publishing the document (e.g., Election Commission, Party Name).
*   `source_url` (String): The original URL where the document was discovered.
*   `source_type` (String): Indicates the origin type (`primary`, `archive`, `discovery_only`).
*   `source_tier` (Integer): Reliability tier (1-5), where 1 is the official primary source.
*   `publication_date` (DateTime): Stated date of the manifesto publication.
*   `collection_date` (DateTime): Timestamp of when the system logged the source.
*   `retrieval_method` (String): How it was accessed (e.g., `PoliteHTTPClient`, `manual`).
*   `retrieval_status` (String): The current acquisition state (`identified`, `pending_collection`, `collected`, `failed`).
*   `content_hash` / `checksum` (String): Verification hashes to ensure integrity.
*   `notes` (Text): Any context regarding the discovery (e.g., 404 workarounds).

### 2. ManifestoDocument (`manifesto_documents`)
Represents the actual physical/digital file stored on disk.
*   `document_id` (PK, String): Unique identifier for the stored file.
*   `source_id` (FK): Links back to the `ManifestoSource`.
*   `original_filename` (String): The filename as retrieved from the server.
*   `file_format` (String): e.g., PDF, HTML.
*   `file_size` (Integer): Size in bytes.
*   `storage_path` (String): Relative path in `data/raw/manifestos/`.
*   `checksum` (String): Post-download SHA-256 hash.
*   `page_count` (Integer): Number of pages (if PDF).
*   `extraction_method` (String): How text will be parsed (e.g., `pdfplumber_ocr`).
*   `extraction_status` (String): State of text processing (`pending`, `extracted`).

### 3. Manifesto (`manifestos`)
Represents the logical political manifesto, tying the source, document, and election metadata together.
*   `manifesto_id` (PK, String): Unique logical ID (e.g., `DMK_2026_Assembly`).
*   `party` (String): The political party.
*   `election` (String): Election name (e.g., `Tamil Nadu Legislative Assembly Election`).
*   `election_year` (Integer): The year of the election.
*   `language` (String): Language of the document (e.g., `Tamil`).
*   `title` (String): Display title.
*   `source_id` (FK): Links to the primary source of discovery.
*   `document_id` (FK): Links to the acquired document file.
*   `extraction_status` (String): Rollup status of text extraction.
*   `verification_status` (String): Rollup status indicating human or automated verification of the manifesto (`identified`, `verified`).

## Manifest Structure
The system tracks planned and actual acquisitions in `data/raw/manifestos/manifest.json`. This file acts as the configuration and state tracker for the acquisition layer, utilizing statuses like `identified`, `pending_collection`, `collected`, `verified`, and `failed`. Crucially, it does not invent documents; it only lists sources that have been strictly identified or verified in reality.
