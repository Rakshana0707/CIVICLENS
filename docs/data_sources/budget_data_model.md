# Relational Budget Database Schema

**Status:** IMPLEMENTED
**Date:** 2026-09-27

## 1. Overview and Relationships
The budget data follows a normalized relational structure to efficiently store hierarchical taxonomy (`Department -> Scheme -> Budget Record`) and traceability metadata.

### Core Entities:
*   **BudgetDepartment**: Represents a government administrative body (e.g., "School Education").
*   **BudgetScheme**: Represents a specific program/policy under a department. Not all have a `head_of_account`. 
*   **BudgetRecord**: The core transactional record. A single scheme can have multiple `BudgetRecord` rows across different `financial_year` and `budget_stage` combinations.
*   **BudgetSourceDocument**: Maps to a physical file in the `manifest.json`. Guarantees traceability.
*   **BudgetImportBatch**: Tracks ingestion pipeline runs for auditing.

### ER Diagram Overview
`BudgetDepartment (1) --- (*) BudgetScheme`
`BudgetScheme (1) --- (*) BudgetRecord`
`BudgetSourceDocument (1) --- (*) BudgetRecord`
`BudgetImportBatch (1) --- (*) BudgetRecord`

## 2. Table Definitions

### `budget_departments`
| Column | Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `id` | Integer | PK | Auto-increment ID. |
| `name` | String | UNIQUE, NOT NULL | Official department name. |
| `code` | String | NULL | Demand Number (if available). |

### `budget_schemes`
| Column | Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `id` | Integer | PK | Auto-increment ID. |
| `department_id` | Integer | FK | Reference to `budget_departments.id`. |
| `name` | String | NOT NULL | Scheme name. |
| `head_of_account` | String | NULL | Accounting code. |
| `normalized_category` | String | NULL | Mapped high-level category. |
*(Constraint: `department_id` + `name` + `head_of_account` must be Unique)*

### `budget_records`
| Column | Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `id` | Integer | PK | Auto-increment ID. |
| `scheme_id` | Integer | FK, NOT NULL | Reference to `budget_schemes.id`. |
| `source_document_id`| Integer | FK, NOT NULL | Reference to `budget_source_documents.id`. |
| `import_batch_id` | Integer | FK | Reference to `budget_import_batches.id`. |
| `financial_year` | String | NOT NULL | Fiscal year (e.g., "2024-25"). |
| `budget_stage` | Enum | NOT NULL | `budget_estimate`, `revised_estimate`, `actual_expenditure`. |
| `amount` | Float | NULL | Monetary allocation. Missing values are NULL. |
| `currency_unit` | String | NOT NULL | E.g., `INR_Absolute`. |
| `source_page_number`| Integer | NULL | Exact page in PDF. |
| `original_category_text` | String | NULL | Exact string payload from the raw source. |
*(Constraint: `scheme_id` + `financial_year` + `budget_stage` + `source_document_id` must be Unique to prevent duplication)*

### `budget_source_documents`
| Column | Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `id` | Integer | PK | Auto-increment ID. |
| `manifest_dataset_id` | String | UNIQUE, NOT NULL | The ID defined in `manifest.json`. |
| `title` | String | NOT NULL | Document title. |
