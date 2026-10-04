# Web Acquisition Strategy

## Introduction
This document defines the strategy for acquiring web-based documents (manifestos, government announcements, reports) for the CIVICLENS TN project. To ensure traceability, reliability, and respectful crawling, all web acquisition must occur through a reusable acquisition layer located in `backend/acquisition/`.

## Reusable Web Acquisition Layer

The acquisition layer provides a unified interface for gathering external resources. It handles:

* **URL Collection**: Ingesting target URLs from queues or user inputs.
* **Content Retrieval**: Fetching HTML pages, discovering linked PDFs, and downloading documents.
* **Extraction**: Metadata and structural content extraction.
* **Resilience**: Retry handling, rate limiting, and failure logging (avoiding silent infinite retries).
* **Integrity**: Checksums, content hashes, and caching to detect duplicates and avoid unnecessary requests.
* **Provenance**: Capturing collection timestamps, HTTP status codes, and original source URLs.

## Strict Acquisition Rules

The web acquisition system must rigidly adhere to the following rules:

1. **Respect `robots.txt`**: Always parse and honor `robots.txt` directives before requesting URLs.
2. **Respect Terms of Service**: Honor website access restrictions and terms of use.
3. **Reasonable Request Rates**: Implement rate limiting and delays between requests to prevent overwhelming target servers.
4. **No Aggressive Crawling**: Scrape only targeted, necessary pages rather than deep, uncontrolled crawling.
5. **Client Identification**: Use a distinct User-Agent string identifying the "CIVICLENS TN" project with contact information where appropriate.
6. **Caching**: Always cache previously downloaded content to avoid redundant network calls.
7. **No Bypassing Controls**: Never bypass authentication mechanisms, CAPTCHAs, paywalls, or access control systems.
8. **No Anti-Bot Evasion**: Never attempt to evade or spoof anti-bot mechanisms.
9. **Store Provenance**: Always retain source URLs, retrieval timestamps, HTTP status codes, and exact original filenames.
10. **Preserve Originals**: Keep the raw downloaded source documents intact in local storage where permitted.
11. **Log Failures**: Record failures explicitly instead of retrying indefinitely.
12. **Prefer APIs/Structured Data**: Always prefer official government APIs or structured data endpoints over HTML scraping when available. Prefer official government sources overall.

## Implementation Guidelines
* The layer should employ an asynchronous fetching mechanism with strict concurrency limits.
* All downloaded files should map to the centralized database provenance schema (e.g., `DataSource`, `Source`, `Document`).
