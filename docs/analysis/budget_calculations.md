# Budget Calculation Rules

This document outlines the rules governing the calculation and summation of monetary values within the Budget Analysis Service (`backend.services.budget`).

## Core Principles

1. **Missing Data is Not Zero**
   Records with a `null` or missing `amount` represent unknown data, not an absence of funding. When summing or comparing amounts, missing values are excluded entirely rather than treated as `0`. Treating them as zero would severely skew statistical averages and percentage changes.

2. **Stage Compatibility**
   A sum of budget records must implicitly or explicitly share the same `BudgetStage` (e.g., `budget_estimate`, `revised_estimate`, `actual_expenditure`). Adding a Budget Estimate to an Actual Expenditure yields a meaningless number.
   - The UI and API consumers should ensure they filter by a specific stage before requesting a summation.

## Aggregation Methods

*   **`summarize_by_year`**: Sums all monetary amounts across a given financial year.
*   **`summarize_by_department`**: Sums all monetary amounts grouped by department.
*   **`summarize_by_scheme`**: Sums all monetary amounts grouped by scheme.

## Comparison Rules

*   **`compare_stages(stage_a, stage_b)`**: 
    Calculates the absolute difference (`b - a`) and percentage difference (`(b - a) / a * 100`) between two stages for comparable entities (e.g., comparing the Budget Estimate of "Mid Day Meal (2024)" to its Actual Expenditure).
    
    *   **Rule 1**: Cannot compare a stage against itself.
    *   **Rule 2**: If an entity is missing data for *either* `stage_a` or `stage_b`, it is excluded from the comparison result entirely.
    *   **Rule 3**: If the base value (`stage_a`) is exactly `0`, the percentage difference is returned as `None` to prevent division-by-zero errors, while the absolute difference is still provided.
