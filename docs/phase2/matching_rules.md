# Historical Scheme Integration & Matching Rules

## Overview
Phase 2.7 introduces the integration of semantic, historical scheme intelligence (descriptions, beneficiaries, objectives) with the quantitative budget pipeline established in Phase 1. 

To maintain database integrity, Phase 2 textual records must be carefully mapped to `budget_schemes.id` without overwriting the original financial entries.

## 1. Internal Identifiers and Linking
A new table, `historical_schemes`, has been created. It links the Phase 2 intelligence to the Phase 1 backbone:
*   **Primary Internal Identifier:** `historical_schemes.id` (Stable UUID/Integer).
*   **Phase 1 Scheme Link:** `historical_schemes.budget_scheme_id` (Foreign Key). Nullable for completely new historical schemes that have no quantitative Phase 1 equivalent.
*   **Phase 1 Department Link:** `historical_schemes.department_id` (Foreign Key). Required.
*   **Original Source Identifier:** Preserved as `historical_schemes.original_source_identifier` to trace back to external datasets.

## 2. Rule 1: Strict Non-Destruction
*   **No Overwrites:** No Phase 1 `budget_schemes` or `budget_records` are ever mutated or deleted by the Historical Scheme Integrator.
*   **Multiple Financial Years:** A single Phase 1 `budget_scheme` can have multiple `historical_schemes` records linked to it, representing the narrative evolution of the scheme across different financial years.

## 3. Rule 2: Exact Matching
*   **Criteria:** A Phase 2 historical scheme is linked to a Phase 1 budget scheme ONLY if the `department_id` matches exactly AND the `scheme_name` strings match exactly (case-insensitive, whitespace stripped).
*   **Action:** `budget_scheme_id` is populated, `is_uncertain_match` is set to `False` (0), and `match_confidence` is `1.0`.

## 4. Rule 3: Handling Uncertain Matches
*   **Constraint:** Fuzzy matching (e.g., Levenshtein distance, Jaro-Winkler) is strictly **forbidden** from making automatic, assumed merges.
*   **Criteria:** If an exact match fails, a subset string match (e.g., "Muthulakshmi Scheme" vs "Muthulakshmi Reddy Maternity Scheme") is evaluated. 
*   **Action:** If a potential subset match is found, the link `budget_scheme_id` is made, BUT it must be explicitly flagged with `is_uncertain_match = True` (1). This segregates the data for manual review and ensures frontend UIs don't blindly aggregate their data.

## 5. Match-Quality Report
The `SchemeIntegrator` generates a real-time mapping report during ingestion, tracking:
*   `total_records`: Total historical records parsed.
*   `exact_matches`: Safe, verified links.
*   `uncertain_matches`: Needs review.
*   `unmatched_new_schemes`: Schemes completely unknown to Phase 1.
*   `failed_department_lookup`: Critical error requiring department alias mapping.
