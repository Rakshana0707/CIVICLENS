# Budget Data Provenance Framework

## Overview
This document establishes the data provenance and tracking framework for the Phase 1 Budget & Scheme Analyzer of the CivicLens TN project. It defines the standard operating procedure for identifying, documenting, and verifying official Tamil Nadu budget datasets while maintaining strict adherence to project constraints (no synthetic data, strict official sourcing).

## Dataset Manifest Configuration
The authoritative record of all targeted and acquired budget datasets is maintained in the JSON manifest located at `data/raw/budget/manifest.json`.

Every dataset added to the project must be documented in this manifest using the exact schema below:

*   **dataset_id:** A unique, standardized identifier (e.g., `TN_BUDGET_DDG_43_2024_25`).
*   **source_organization:** The official government body publishing the data.
*   **dataset_title:** The official title of the document or dataset.
*   **official_source_url:** The confirmed, working URL where the dataset is officially hosted.
*   **financial_year:** The fiscal year covered by the data (e.g., `2024-25`).
*   **original_filename:** The exact filename as downloaded from the official source.
*   **file_format:** The format of the file (e.g., `PDF`, `CSV`).
*   **collection_date:** The date (YYYY-MM-DD) the file was actually downloaded (leave as `null` or empty string if not collected).
*   **coverage:** A concise description of the data scope (e.g., "Demand for Grants for School Education").
*   **limitations:** Known issues or preprocessing constraints (e.g., "Locked in PDF format, lacks explicit scheme descriptions").
*   **collection_status:** Must strictly be one of the following enumerations:
    *   `identified`: Dataset existence is confirmed in principle, but the exact valid URL/file is pending confirmation.
    *   `pending_collection`: Exact URL and filename are known and documented, but the physical file is not yet downloaded.
    *   `collected`: File is successfully downloaded and placed in the raw data directory.
    *   `verified`: File checksum is generated, and structural integrity/relevance is confirmed.
*   **checksum:** SHA-256 hash of the collected file to ensure data integrity (leave as `null` or empty string until the file is collected and verified).

## Standard Procedure for Future Datasets

To maintain data provenance, all future additions must follow this strict workflow:

1.  **Identification Phase:**
    *   Identify target official budget datasets via the Tamil Nadu Government Budget Portal (`http://www.tnbudget.tn.gov.in/`).
    *   Add a new JSON object to `data/raw/budget/manifest.json`. 
    *   Set the `collection_status` to `identified` or `pending_collection`.
    *   **CRITICAL:** Record only confirmed URLs and filenames. Do not fabricate or predict URLs.

2.  **Collection Phase:**
    *   Acquire the file from the `official_source_url`.
    *   Save the file directly into `data/raw/budget/` without altering the original file extension or contents.
    *   Update the manifest: insert the current date into `collection_date` and update `collection_status` to `collected`.

3.  **Verification Phase:**
    *   Compute the SHA-256 checksum of the downloaded file.
    *   Record the resulting hash in the `checksum` field of the manifest.
    *   Update `collection_status` to `verified`.
    *   Commit the updated `manifest.json` to Git. (Note: Raw datasets themselves may remain git-ignored depending on repository policy, but their metadata is fully tracked).
