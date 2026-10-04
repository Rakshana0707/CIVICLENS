# Manifesto Acquisition Architecture

## Overview
The acquisition architecture is centralized under `backend/acquisition/`. It is designed to safely, respectfully, and reliably download documents across the web.

## Key Capabilities

*   **HTTP/HTML/PDF Retrieval:** Capable of fetching structured text and binary files.
*   **Metadata Extraction:** Parses filename, content type, and source server details.
*   **Content Hashing & Duplicate Detection:** Computes a SHA-256 hash (or similar) of the downloaded content. Compares against local cache to prevent redundant downloading and processing.
*   **Caching:** Preserves raw byte content locally.
*   **Retry Handling & Request Throttling:** Detects transient errors and politely delays repeated requests to the same domain.
*   **Error Logging:** Logs all HTTP failures (e.g., 404, 403) without infinite silent retrying.
*   **Source Provenance:** Maps precisely to the `SourceRecord` model, embedding the exact origin in the system's database.

## Strict Website Access Rules

The web client (`PoliteHTTPClient` or equivalent) explicitly enforces the following:
1.  **Respect `robots.txt`**: Fetches and obeys robots.txt directives.
2.  **Respect terms and restrictions**: Uses standard identification in headers.
3.  **Reasonable request rates**: Incorporates politeness delays between sequential requests.
4.  **No Bypassing Security**: Never bypasses CAPTCHAs, authentication, paywalls, or anti-bot systems.
5.  **Manual Fallback**: If automated retrieval is blocked, the acquisition layer logs a `retrieval_status` failure, allowing a human operator to manually acquire the document and supply it to the system.

## Reusability
While currently targeted for manifestos, this layer exposes generic `fetch()` or `acquire()` methods that return a standard `SourceRecord`. This allows drop-in reuse for collecting news articles, government evidence documents, and public policy records in future modules.
