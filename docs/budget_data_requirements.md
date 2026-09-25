# Budget Data Requirements

## Overview
This document defines the data requirements for the Phase 1: Budget & Scheme Analyzer module of the CivicLens TN project. It specifies the fields required from Tamil Nadu government budget data covering multiple years, including department-level and scheme-level information, prior to any data collection.

## General Standards
- **Expected Unit for Monetary Values:** INR (Indian Rupees) in actuals (absolute values). If the source data is presented in Lakhs or Crores, it must be converted to absolute INR during the ingestion phase to maintain consistency and simplify downstream calculations.
- **Expected Financial-Year Format:** `YYYY-YY` (e.g., `2023-24`).

## Field Definitions

| Field Name | Classification | Why the field is needed | Which later feature uses it | Acceptable missing-data behavior |
| :--- | :--- | :--- | :--- | :--- |
| **department name** | Required | Essential for grouping budgets and categorizing schemes by administrative body. | Budget Explorer, Anomaly detection | Cannot be missing. Row must be dropped or flagged for manual review if missing. |
| **department identifier** | Preferred | Provides a stable, unique reference for departments, avoiding issues with name changes or typos. | Budget Explorer | If missing, use slugified `department name` as a fallback. |
| **scheme name** | Required | Core entity for tracking specific initiatives, policies, and their funding. | Budget Explorer, Scheme trends, Scheme clustering | Cannot be missing. |
| **scheme identifier** | Preferred | Crucial for tracking the exact same scheme across multiple financial years reliably. | Scheme trends, Scheme clustering | If missing, system must fallback to exact or fuzzy text matching on `scheme name`. |
| **sector/category** | Preferred | Enables macro-level aggregation (e.g., Health, Education, Infrastructure) beyond departmental silos. | Budget Explorer, Scheme clustering | Fill with "Uncategorized" or attempt to infer from the department name. |
| **financial year** | Required | The fundamental temporal dimension for all budgetary time-series data. | Budget Explorer, Year-wise comparison, Scheme trends | Cannot be missing. |
| **budget allocation** | Required | The primary initial Budget Estimate (BE) proposed for the scheme/department. | Budget Explorer, Year-wise comparison, Scheme trends, Anomaly detection | Cannot be missing for core budget rows. Represent as `0` if explicitly stated as such, otherwise flag row. |
| **revised allocation** | Preferred | The Revised Estimate (RE), showing adjustments made to the budget mid-year. | Year-wise comparison, Scheme trends, Anomaly detection | Leave as `null`. Features will fallback to comparing against `budget allocation` only. |
| **actual expenditure** | Preferred | The final, audited amount actually spent (Actuals), crucial for measuring utilization. | Year-wise comparison, Scheme trends, Anomaly detection | Leave as `null`. Features will exclude the scheme from actuals-based metrics. |
| **scheme description/objective** | Optional | Provides textual context on what the scheme aims to achieve, useful for NLP analysis. | Scheme clustering | Leave as `null` or empty string. Exclude scheme from text-based similarity clustering. |
| **source document** | Required | Ensures data provenance, transparency, and auditability. | Budget Explorer (metadata) | Must be provided (e.g., "Demand for Grants 2023-24"). |
| **source URL/reference** | Preferred | Allows end-users or verifiers to quickly access the original public document. | Budget Explorer (metadata) | Leave as `null` or empty string. |
| **page/section reference** | Optional | Granular traceability to the exact location of the data point within large PDFs. | Budget Explorer (metadata) | Leave as `null` or empty string. |

## Feature Mapping

The collected data fields directly enable the following planned features:

### Budget Explorer
*   department name
*   department identifier
*   scheme name
*   sector/category
*   financial year
*   budget allocation
*   source document
*   source URL/reference
*   page/section reference

### Year-wise Comparison
*   financial year
*   budget allocation
*   revised allocation
*   actual expenditure

### Scheme Trends
*   scheme name
*   scheme identifier
*   financial year
*   budget allocation
*   revised allocation
*   actual expenditure

### Scheme Clustering
*   scheme name
*   scheme identifier
*   sector/category
*   scheme description/objective

### Anomaly Detection
*   department name
*   budget allocation
*   revised allocation
*   actual expenditure
