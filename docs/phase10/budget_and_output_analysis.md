# Phase 10.5 — Policy Budget Execution and Implementation Output Analytics

## 1. Overview & Phase 1 Integration
Phase 10.5 (`PolicyBudgetExecutionAnalyticsService` in `backend/services/policy_budget_execution_service.py`) directly connects **Phase 1's budget and scheme database models** (`BudgetDepartment`, `BudgetScheme`, `BudgetRecord`, `BudgetStage`, `BudgetSourceDocument`) with **Phase 10's policy evaluation models** (`PolicyRegistryEntry`, `PolicyEvaluationPlan`, `ImplementationActivity`, `PolicyIndicator`, `IndicatorObservation`).

Rather than duplicating Phase 1's budget tables or creating a separate financial store, Phase 10.5 reads canonical `BudgetRecord` stages (`budget_estimate`, `revised_estimate`, `actual_expenditure`) linked to `BudgetSourceDocument` and cross-references them against physical implementation targets (`PolicyEvaluationPlan`) and operational deliverables (`ImplementationActivity`).

---

## 2. Explicit Metric Definitions & Formulas

Every metric computed by `PolicyBudgetExecutionAnalyticsService` returns an explicit `metric_provenance` block containing its `metric_code`, `calculation_formula`, `inputs_used`, and `source_links`. All monetary figures are normalized to **Indian Rupees in Crores (`RUPEES_CRORE`)** using documented conversion factors (`1 Crore = 100 Lakhs = 10,000,000 INR`).

### 2.1 Budget Estimate (BE) vs. Revised Estimate (RE)
- **Revision Delta ($\Delta_{\text{rev}}$)**:
  $$\Delta_{\text{rev}} = RE - BE$$
- **Revision Rate ($\text{RevRate}\%$)**:
  $$\text{RevRate}\% = \left( \frac{RE - BE}{BE} \right) \times 100 \quad (\text{when } BE > 0)$$
- **Classification Rules**:
  - `UPWARD_REVISION`: $RE > BE$
  - `DOWNWARD_REVISION`: $0 < RE < BE$
  - `UNCHANGED_ALLOCATION`: $RE = BE > 0$
  - `ALLOCATION_SURRENDERED_MIDYEAR`: $BE > 0 \land RE = 0$
  - `UNBUDGETED_MIDYEAR_INTRODUCTION`: $BE = 0 \land RE > 0$
  - `INCOMPLETE_STAGE_DATA`: $BE = \text{None} \lor RE = \text{None}$
- **Supplementary Grants & Accounting Adjustments**:
  - Handled **only** when explicitly recorded in `BudgetRecord.source_metadata` (`supplementary_grant_cr`, `accounting_adjustment_note`). The service never infers or fabricates supplementary grants when source records do not document them.

### 2.2 Allocation vs. Actual Expenditure
- **Budget Execution Rate ($BER$)**:
  $$BER = \left( \frac{\text{Actual Expenditure}}{BE} \right) \times 100 \quad (\text{when } BE > 0)$$
- **Revised Allocation Absorption Rate ($RAAR$)**:
  $$RAAR = \left( \frac{\text{Actual Expenditure}}{RE} \right) \times 100 \quad (\text{when } RE > 0)$$
- **Surrender of Funds Ratio ($SFR$)**:
  $$SFR = \max\left(0, \frac{BE - \text{Actual Expenditure}}{BE}\right) \times 100 \quad (\text{when } BE > 0)$$
- **Unspent Variance vs. BE**:
  $$\text{Unspent}_{\text{BE}} = BE - \text{Actual Expenditure}$$
- **Execution Classification**:
  - `ACTUAL_EXPENDITURE_NOT_YET_PUBLISHED`: $\text{Actual Expenditure} = \text{None}$ (never assumed spent or zero).
  - `SEVERE_UNDERUTILIZATION`: $BER < 75.0\%$
  - `NORMAL_EXECUTION`: $75.0\% \le BER \le 105.0\%$
  - `BUDGET_OVERRUN`: $BER > 105.0\%$
  - `ALLOCATION_SURRENDERED_MIDYEAR`: $RE = 0$

### 2.3 Published Implementation Targets vs. Reported Achievements
- **Physical Target Realization Ratio ($PTRR$)**:
  $$PTRR = \left( \frac{Q_{\text{actual}}}{Q_{\text{target}}} \right) \times 100 \quad (\text{when } Q_{\text{target}} > 0)$$
- **Target Variance**:
  $$\Delta_{\text{target}} = Q_{\text{actual}} - Q_{\text{target}}$$
- **Distance-to-Target Metric ($DTM$)**:
  $$DTM = \left( \frac{Q_{\text{actual}} - Q_{\text{baseline}}}{Q_{\text{target}} - Q_{\text{baseline}}} \right) \times 100 \quad (\text{when } Q_{\text{target}} \neq Q_{\text{baseline}})$$
- **Target Provenance Enforcement**:
  - Distinguishes `OFFICIALLY_STATED` targets from `ANALYST_PROPOSED_BENCHMARK` and `NO_PUBLISHED_TARGET`. When `target_provenance == NO_PUBLISHED_TARGET`, $PTRR$ is `None` and `realization_classification = "NO_PUBLISHED_TARGET"`.

### 2.4 Planned Outputs vs. Completed Outputs
- **Activity Completion Rate ($ACR$)**:
  $$ACR = \left( \frac{N_{\text{completed}}}{N_{\text{total}}} \right) \times 100$$
- **Output Quantity Completion Ratio ($OQCR$)**:
  $$OQCR_u = \left( \frac{\sum_{i \in u} Q_{\text{completed}, i}}{\sum_{i \in u} Q_{\text{planned}, i}} \right) \times 100$$
  computed strictly within identical `output_unit` groups $u$ (e.g., `CLASSROOMS`, `CAMPS`, `KM`).
- **Realized Unit Cost ($RUC$)**:
  $$RUC = \frac{\text{Expenditure Incurred (₹ Cr)}}{Q_{\text{completed}}} \quad (\text{when } Q_{\text{completed}} > 0)$$

### 2.5 Year-on-Year (YoY) Changes
- **YoY Absolute Change ($\Delta_{\text{YoY}}$)**:
  $$\Delta_{\text{YoY}, t} = V_t - V_{t-1}$$
- **YoY Percentage Change ($\Delta\%_{\text{YoY}}$)**:
  $$\Delta\%_{\text{YoY}, t} = \left( \frac{V_t - V_{t-1}}{V_{t-1}} \right) \times 100 \quad (\text{when } V_{t-1} > 0)$$
- Requires consecutive **Financial Years** (`t - (t-1) == 1`) and identical `BudgetStage`. Non-consecutive years are flagged as `NON_CONSECUTIVE_YEAR_GAP`.

---

## 3. Epistemic & Methodological Guardrails

1. **Never Assume a Budget Allocation Was Spent**:
   - Until audited Accounts / Actual Expenditure figures are published in subsequent budget documents or CAG Appropriation Accounts, `actual_expenditure_cr` remains `None` (`is_actual_expenditure_published = False`).
2. **Non-Equivalence of Spending and Policy Success/Failure**:
   - Every allocation-vs-actual result includes `results_chain_tier = "INPUT"`, `can_infer_policy_success_or_failure_from_spending_alone = False`, and `epistemic_interpretation_guardrail`.
   - Underspending alone is **not** proof of policy failure (it may reflect multi-year procurement scheduling, unit-cost savings from competitive bidding, or treasury release timing).
   - Overspending or $100\%$ expenditure is **not** proof of policy success or public benefit (it measures financial input absorption only, and may reflect cost overruns or inflation without commensurate citizen outcomes).
3. **Strict Separation of Financial Years (`FY`) and Calendar Years (`CY`)**:
   - `classify_reporting_period()` enforces that Indian Financial Years (`YYYY-YY`, April 1 to March 31, e.g., `2023-24`) are never silently mixed with or compared against Calendar Years (`YYYY`, Jan 1 to Dec 31, e.g., `2023`) or Academic Years (`AY2023-24`). Passing a Calendar Year to financial year analytics raises `IncompatibleReportingPeriodError("CALENDAR_VS_FINANCIAL_YEAR_MISMATCH")`.
4. **Missing & Inconsistent Reporting Detection**:
   - `detect_reporting_anomalies_and_gaps()` flags:
     - `MISSING_ACTUAL_EXPENDITURE`
     - `OVERRUN_WITHOUT_SUPPLEMENTARY_RECORD`
     - `HIGH_EXPENDITURE_WITH_ZERO_OR_MISSING_OUTPUTS`
     - `COMPLETED_OUTPUTS_WITH_ZERO_OR_MISSING_EXPENDITURE`
     - `NEGATIVE_BUDGET_ENTRY_WITHOUT_DEDUCTION_NOTE`
