# Budget & Scheme Analyzer API

This module exposes REST API endpoints to retrieve, filter, and summarize budget records and metadata.
All endpoints are available under the `/api/budget` prefix.

## 1. Metadata Endpoints

### `GET /api/budget/years`
Retrieves a distinct list of all available financial years descending.
**Response**: `{"status": "success", "data": ["2024-25", "2023-24"]}`

### `GET /api/budget/departments`
Retrieves all departments.
**Query Parameters**:
- `search` (string, optional): Filter by department name.
**Response Data**: `[{"id": 1, "name": "School Education"}]`

### `GET /api/budget/schemes`
Retrieves all schemes.
**Query Parameters**:
- `department_id` (integer, optional): Filter by department.
- `search` (string, optional): Filter by scheme name.
**Response Data**: `[{"id": 1, "name": "Mid Day Meal", "department_id": 1}]`

## 2. Records Endpoint

### `GET /api/budget/records`
Retrieves raw, filtered budget records with pagination.
**Query Parameters**:
- `skip` (int, default: 0)
- `limit` (int, default: 100)
- `financial_year` (string)
- `department_id` (int)
- `scheme_id` (int)
- `budget_stage` (string, e.g., "budget_estimate")

**Response Data**:
```json
{
  "records": [
    {
      "id": 10,
      "financial_year": "2023-24",
      "budget_stage": "budget_estimate",
      "amount": 500.0,
      "currency_unit": "INR_Absolute",
      "department_name": "School Education",
      "scheme_name": "Scholarships",
      "source_document_title": "DDG 2023"
    }
  ],
  "total_count": 1,
  "skip": 0,
  "limit": 100
}
```

## 3. Summarization Endpoints

**Important**: Summarization endpoints require a specific `budget_stage` to prevent invalid statistical mixing (e.g. summing Estimates with Actuals).

### `GET /api/budget/summarize/year`
Sums budget allocations grouped by year.
**Query Parameters**:
- `budget_stage` (string, **required**)
**Response**: `{"2024-25": 1000.5, "2023-24": 900.0}`

### `GET /api/budget/summarize/department`
Sums budget allocations grouped by department.
**Query Parameters**:
- `budget_stage` (string, **required**)
- `financial_year` (string, **required**)
**Response**: `{"Health": 50000.0, "Education": 45000.0}`

### `GET /api/budget/summarize/scheme`
Sums budget allocations grouped by scheme.
**Query Parameters**:
- `budget_stage` (string, **required**)
- `financial_year` (string, **required**)
- `department_id` (int, optional)
**Response**: `{"Scholarships": 200.0, "Mid Day Meal": 500.0}`

### `GET /api/budget/analysis/trend`
Calculates year-wise totals and year-over-year percentage changes.
**Query Parameters**:
- `budget_stage` (string, **required**)
- `department_id` (int, optional)
- `scheme_id` (int, optional)

**Response Data**:
```json
{
  "2023-24": {
    "total": 900.0,
    "percentage_change": null
  },
  "2024-25": {
    "total": 1000.5,
    "percentage_change": 11.16
  }
}
```

