# Phase 10.6 — Policy Outcome Analysis and Comparison Methodology

## 1. Overview
`PolicyOutcomeAnalysisService` (`backend/services/policy_outcome_analysis_service.py`) implements evidence-based outcome analysis and comparison methods across validated Phase 10 indicators (`PolicyIndicator`, `IndicatorObservation`, `BeneficiaryGroup`, `EvaluationStudy`, `EvaluationFinding`, `EvaluationLimitation`).

It enforces three core methodological rules:
1. **Non-Causality of Simple Pre-Post Comparisons**: A baseline-versus-follow-up comparison or cross-sectional difference is **never** treated as proof of causal impact. Unless supported by a verified counterfactual evaluation design (`GRADE_A_EXPERIMENTAL` or `GRADE_B_QUASI_EXPERIMENTAL` with an explicit identification strategy such as `RCT`, `DID`, `RDD`, or `IV`), every result is explicitly labelled `DESCRIPTIVE_ASSOCIATION_OR_OBSERVED_CHANGE` with `causal_claim_permitted = False`.
2. **Contextualized Geographic & Population Comparisons**: Districts or beneficiary groups are never compared in isolation without documenting differences in coverage, baseline demographics, eligibility rules, and data quality (`comparability_context`).
3. **Privacy-Safe & Mathematically Valid Reporting**: Small beneficiary sub-group cells ($n < 5$) are automatically suppressed (`PRIVACY_SUPPRESSED_SMALL_CELL`), small samples ($n < 30$) carry `SMALL_SAMPLE_HIGH_VARIANCE_WARNING`, and division by zero on zero baselines ($Y_{\text{baseline}} = 0.0$) is prevented by reporting `percentage_change = None` (`percentage_change_validity = "UNDEFINED_ZERO_BASELINE"`).

---

## 2. Mandatory 9 Result Fields
Every analysis method in `PolicyOutcomeAnalysisService` returns a standardized payload containing:

1. **`indicator_definition`**: Canonical `indicator_id`, `indicator_name`, `indicator_type`, `indicator_domain`, `definition`, `definition_code`, `unit`, `direction_of_improvement`, and `calculation_formula`.
2. **`baseline_value` and `followup_value`**: Nullable numeric observations in standardized units (`None` when missing, never coerced to `0.0`).
3. **`absolute_change`**: Exact difference $\Delta = Y_{\text{followup}} - Y_{\text{baseline}}$ (`None` if either period is missing).
4. **`percentage_change`**: Relative change $\Delta\% = \left(\frac{Y_{\text{followup}} - Y_{\text{baseline}}}{Y_{\text{baseline}}}\right) \times 100$, computed **only** when mathematically valid ($Y_{\text{baseline}} > 0$), paired with `percentage_change_validity` (`MATHEMATICALLY_VALID`, `UNDEFINED_ZERO_BASELINE`, `UNDEFINED_NEGATIVE_BASELINE`, or `MISSING_INPUT_VALUE`).
5. **`time_period`**: Reference periods (`baseline_period`, `followup_period`, `reporting_frequency`).
6. **`geographic_scope`**: Administrative level (`STATE`, `DISTRICT`, `CONSTITUENCY`), unit ID, and `boundary_reference` (e.g., `TN_38_DISTRICTS_2020`).
7. **`source_references`**: Structured citations (`observation_id`, `source_document_id`, `source_reference`, `source_url`, `document_hash`, `data_quality_status`).
8. **`missing_data_info`**: Completeness status (`COMPLETE`, `MISSING_BASELINE`, `MISSING_COMPARISON`, `PARTIAL_GEOGRAPHIC_COVERAGE`, `missing_periods`, `missing_units`, `suppressed_group_ids`).
9. **`interpretation_limitations`**: Explicit list of methodological caveats, non-causal warnings, small-sample advisories, and context differences.

---

## 3. Supported Analysis & Comparison Methods

### 3.1 Baseline vs. Follow-Up & Changes in Indicator Values (`analyze_baseline_vs_followup`)
- Validates indicator identity (`INDICATOR_ID_MISMATCH`), definition compatibility (`DEFINITION_MISMATCH`), unit compatibility (`UNIT_MISMATCH`), administrative boundary consistency (`BOUNDARY_MISMATCH`), and reporting frequency (`REPORTING_PERIOD_MISMATCH`).
- Evaluates qualitative trajectory (`normative_trajectory`) relative to `indicator.direction_of_improvement`:
  - If `direction_of_improvement == "INCREASE"` (e.g., Higher Education Gross Enrollment Ratio), $\Delta > 0 \implies$ `FAVORABLE_OBSERVED_CHANGE`, $\Delta < 0 \implies$ `ADVERSE_OBSERVED_CHANGE`.
  - If `direction_of_improvement == "DECREASE"` (e.g., Maternal Mortality Ratio, school dropout rate), $\Delta < 0 \implies$ `FAVORABLE_OBSERVED_CHANGE`, $\Delta > 0 \implies$ `ADVERSE_OBSERVED_CHANGE`.

### 3.2 Target-versus-Actual Outcome Comparisons (`analyze_target_vs_actual_outcome`)
- Compares observed follow-up outcomes against documented `TARGET` stage observations:
  - $\text{Target Gap} = Y_{\text{followup}} - Y_{\text{target}}$
  - $\text{Target Realization (\%)} = \left(\frac{Y_{\text{followup}}}{Y_{\text{target}}}\right) \times 100$
  - $\text{Distance-to-Target (DTM \%)} = \left(\frac{Y_{\text{followup}} - Y_{\text{baseline}}}{Y_{\text{target}} - Y_{\text{baseline}}}\right) \times 100$
- If no target is published (`target_obs is None`), sets `target_status = "NO_PUBLISHED_TARGET"` without inventing a target.

### 3.3 Geographic Comparisons (`analyze_geographic_comparison`)
- Evaluates baseline-to-follow-up changes across districts sharing an identical `boundary_reference` and computes the spatial **Coefficient of Variation ($CV_{\text{geo}}$)**:
  $$CV_{\text{geo}} = \left(\frac{\sigma_{\text{districts}}}{\mu_{\text{districts}}}\right) \times 100$$
- Requires `comparability_context` per unit (`coverage_note`, `demographic_context`, `data_quality_note`). Any unit lacking complete context metadata is flagged with `UNEXPLAINED_CONTEXT_DIFFERENCE` and `has_complete_comparability_context = False`.

### 3.4 Beneficiary-Group Comparisons (`analyze_beneficiary_group_comparison`)
- Evaluates outcomes and **Demographic Parity Index ($DPI$)** across `BeneficiaryGroup` strata:
  $$DPI_G = \frac{\text{Share of Beneficiaries in Group } G}{\text{Share of Group } G \text{ in Eligible Population}}$$
- **Privacy Protection**: Any sub-group with `sample_or_cell_count < 5` (`PRIVACY_MIN_CELL_SIZE`) has its values and exact cell count masked (`privacy_status = "PRIVACY_SUPPRESSED_SMALL_CELL"`).
- **Small Sample Advisory**: Any sub-group with $5 \le n < 30$ carries `SMALL_SAMPLE_HIGH_VARIANCE_WARNING`.

### 3.5 Trends Across Compatible Reporting Periods (`analyze_outcome_trend_series`)
- Evaluates multi-period time series (`expected_periods`).
- When an intermediate or terminal period is missing (`None`), records `status = "MISSING_PERIOD_OBSERVATION"` and marks the subsequent period `OBSERVED_AFTER_MISSING_GAP` rather than interpolating or fabricating period-over-period growth across the gap.

### 3.6 Documented Evaluation Findings & Causal Identification Check (`evaluate_finding_epistemic_status`)
- Checks whether an `EvaluationStudy` and `EvaluationFinding` meet all four criteria for `CAUSAL_IMPACT_ESTIMATE`:
  1. `evaluation_type == CAUSAL_EVALUATION`
  2. `causal_rigor_grade in {GRADE_A_EXPERIMENTAL, GRADE_B_QUASI_EXPERIMENTAL}`
  3. `is_causally_identified is True`
  4. `identification_strategy in {RCT, DID, RDD, IV, SYNTHETIC_CONTROL}`
- If any criterion fails, automatically downgrades the finding to `DESCRIPTIVE_ASSOCIATION_OR_OBSERVED_CHANGE` (`was_causal_claim_downgraded = True`, `causal_claim_permitted = False`).

### 3.7 Sensitivity Checks (`run_outcome_sensitivity_checks`)
- Requires $n \ge 4$ observations (`MIN_OBSERVATIONS_FOR_SENSITIVITY`); returns `INSUFFICIENT_DATA_FOR_SENSITIVITY_CHECK` for smaller samples.
- Computes full-sample mean/median change and **leave-one-out (jackknife)** min/max mean bounds (`leave_one_out_min_mean`, `leave_one_out_max_mean`) and `is_sign_stable_under_leave_one_out` to test whether a single outlier district drives the aggregate finding.
