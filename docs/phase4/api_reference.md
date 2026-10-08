# Phase 4.8 — News Analysis Database & REST API Reference

## Overview

The **CIVICLENS TN News Analysis API** provides REST endpoints for accessing ingested news articles, political entity & topic intelligence, ground-truth events, cross-source comparisons, and multi-dimensional statistical indicators.

> [!IMPORTANT]
> All API responses expose explicit data provenance metadata (`source_id`, `url`, `canonical_url`, `retrieval_date`, `text_hash`, `raw_reference`, `document_id`, `evidence_id`, `is_test_fixture`). No response returns a single scalar "bias score" without explicit explanation of what the metric represents.

---

## Base Path
All endpoints are available under the `/api/news` (or `/news`) path prefix.

---

## API Endpoints Reference

### 1. News Sources
- **`GET /news/sources`**
  - **Query Parameters**: `language` (`ta`/`en`), `source_type` (`print_digital`, `tv_digital`, `digital_native`, `official_gov`), `active_status` (`active`, `paused`).
  - **Response**: Array of registered publishers and media outlets with article counts.
- **`POST /news/sources`**
  - **Payload**: `{"source_id": "...", "source_name": "...", "domain": "...", "language": "ta"}`

---

### 2. News Articles
- **`GET /news/articles`**
  - **Query Parameters**:
    - `source` / `source_id`: Filter by publisher ID
    - `language`: `ta`, `en`
    - `date`: Exact date `YYYY-MM-DD`
    - `date_from` / `date_to`: ISO datetime bounds
    - `topic` / `topic_id`: Policy topic code
    - `party` / `person` / `entity_id`: Filter by political party or person ID
    - `event` / `event_id`: Filter by ground-truth event ID
    - `search`: Keyword title/text search
    - `limit` (default 20), `offset` (default 0)
  - **Response**: Paginated list of articles including embedded `provenance` metadata.

- **`GET /news/articles/{id}`**
  - **Response**: Full article details, article body text, linguistic NLP features (sentiment, quote count, citation count), mentioned entities, topics, events, and explicit `provenance` object:
    ```json
    "provenance": {
      "source_id": "src_dt_next",
      "source_name": "DT Next",
      "url": "https://example.com/news/123",
      "canonical_url": "https://example.com/news/123",
      "retrieval_date": "2026-10-08T14:00:00Z",
      "text_hash": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
      "raw_reference": "raw://articles/art_123",
      "document_id": 42,
      "evidence_id": 108,
      "is_test_fixture": false
    }
    ```

---

### 3. Topics & Entities
- **`GET /news/topics`**
  - **Response**: Policy topic taxonomy (14 categories: elections, governance, budget, law & order, etc.) with article counts.
- **`GET /news/entities`**
  - **Query Parameters**: `entity_type` (`person`, `party`, `department`, `location`, `constituency`), `search`
  - **Response**: Political entities list with mention counts across articles.

---

### 4. Political Events
- **`GET /news/events`**
  - **Query Parameters**: `date`, `search`
  - **Response**: Ground-truth political and legislative events list.
- **`GET /news/events/{id}`**
  - **Response**: Event details, linked coverage articles, and multi-outlet reporting summary (`CrossSourceEventComparer`).
- **`GET /news/events/candidates`**
  - **Query Parameters**: `days_window` (default 3)
  - **Response**: Detected candidate political event clusters.
- **`GET /news/events/disparities`**
  - **Response**: Active cross-source coverage disparity records across events.

---

### 5. Source Coverage & Comparisons
- **`GET /news/coverage`** (or `/news/metrics/coverage`)
  - **Query Parameters**: `source_id`, `time_period`, `topic_id`
  - **Response**: Aggregated source-level metrics including article frequency, sentiment, and topic emphasis.
- **`GET /news/source-comparison`** (or `/news/comparisons`)
  - **Query Parameters**: `source_a`, `source_b`, `days_window`
  - **Response**: Pairwise outlet comparison metrics (`wording_similarity_score`, `topic_emphasis_divergence`, `entity_prominence_divergence`, `framing_divergence`, `coverage_difference_score`).

---

### 6. Multi-Dimensional Bias Indicators
- **`GET /news/bias-indicators`**
  - **Query Parameters**: `source_id`, `metric_type`, `min_confidence`
  - **Response**: Array of 12 independent statistical distribution indicators. Each entry contains `interpretation_label`, `explanation`, `statistical_confidence`, `methodology_version`, and `calculation_version`.
- **`POST /news/indicators/calculate`**
  - **Payload**: `{"source_id": "src_dt_next", "days_window": 30}`
  - **Response**: Triggers calculation and persistence of multi-dimensional indicators.
