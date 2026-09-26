# Canonical Budget Data Model (PROVISIONAL)

**Status:** PROVISIONAL
**Date:** 2026-09-26

> **Important Note:** This data schema is strictly PROVISIONAL. Because the official Tamil Nadu Budget dataset inspection is currently pending (due to source unavailability), this structure is based on standard Indian state budget taxonomy. It will be finalized only after the actual raw PDFs are inspected.

## 1. Overview and Relationships
The budget data follows a hierarchical taxonomy: `Department -> Sector/Category -> Scheme -> Budget Record`.

To preserve maximum flexibility and handle variations across different PDF documents, the system will use a flat, normalized transactional model for the core `BudgetRecord`, linking out to dimension tables if necessary, or just keeping it in a single wide table for analytical querying.

### Core Relationships:
*   A **Department** manages multiple **Schemes**.
*   A **Scheme** has multiple **Budget Records** (spanning different financial years and budget stages).
*   A **Budget Record** is tied to a specific **Financial Year**, **Stage** (e.g., Budget Estimate), and is derived from a specific **Source Document**.

## 2. Canonical Data Structure (Data Dictionary)

This table defines the canonical fields for every budget record extracted.

| Field Name | Data Type | Required? | Description | Handling of Missing/Ambiguous Values |
| :--- | :--- | :--- | :--- | :--- |
| `record_id` | String | Yes | Unique UUID or deterministic hash for the row. | Generated on ingestion. |
| `department_name` | String | Yes | Official name of the department (e.g., "School Education"). | Flag for manual review if missing. |
| `department_code` | String | Optional | The Demand Number (e.g., "43"). | Leave null if not explicitly in source. |
| `scheme_name` | String | Yes | The granular program or policy name. | Flag for manual review if missing. |
| `head_of_account` | String | Optional | Standard accounting code (e.g., "2202-01-101-AA"). | Leave null if extraction fails. |
| `original_category` | String | Optional | The literal Major/Minor head text from the PDF. | Leave null if not present. |
| `normalized_category`| String | Optional | High-level mapped category (e.g., "Education"). | Assigned via secondary ML/rules mapping. |
| `financial_year` | String | Yes | Fiscal year format `YYYY-YY` (e.g., "2024-25"). | Must be inherited from document metadata. |
| `budget_stage` | Enum | Yes | One of: `budget_estimate`, `revised_estimate`, `actual_expenditure`. | Row is discarded if stage cannot be determined. |
| `amount` | Decimal | Yes | The absolute monetary value allocated/spent. | If ambiguous/blank in source, store as `null` or `0.0` depending on context. |
| `currency_unit` | String | Yes | E.g., `INR_Lakhs`, `INR_Absolute`. | Default `INR_Absolute`. Convert on ingestion. |
| `source_document_id` | String | Yes | FK to the manifest (`dataset_id`). | Crucial for traceability. Cannot be null. |
| `source_page_number` | Integer | Optional | The specific PDF page number where this record was found. | Leave null for non-paginated sources (e.g. CSV). |

## 3. Field Mapping Documentation (Expected)

Since the actual files are pending, this is how we *expect* to map standard Tamil Nadu Demand for Grants column headers to our canonical fields:

| Expected Source Label (PDF) | Mapped Canonical Field | Notes |
| :--- | :--- | :--- |
| Demand Title (Header) | `department_name` & `department_code` | Extracted from the front page or header of the PDF. |
| Sub-Head / Detailed Head | `scheme_name` | Extracted from the text description column. |
| Head of Account | `head_of_account` | The numeric classification code. |
| Budget Estimate (2024-25) | `amount` (where stage=`budget_estimate`) | Generates a specific `BudgetRecord` row for BE. |
| Revised Estimate (2023-24)| `amount` (where stage=`revised_estimate`)| Generates a specific `BudgetRecord` row for RE. |
| Accounts (2022-23) | `amount` (where stage=`actual_expenditure`)| Generates a specific `BudgetRecord` row for Actuals. |

## 4. Traceability & Preservation Rules

*   **No Data Loss:** The `original_category` field ensures that even if our `normalized_category` logic fails, the exact text from the government document is preserved.
*   **Exact Lineage:** Every single monetary record (`amount`) must be tied to a `source_document_id` and a `source_page_number`. This allows an auditor to take any number in the CivicLens dashboard and click through to exactly which page of which official PDF it originated from.
*   **Gap Handling:** If a PDF table row has a blank cell for "Accounts", a record for `actual_expenditure` will either not be created or will be created with `amount = null`. We will **never** impute or create synthetic budget numbers to fill these gaps.
