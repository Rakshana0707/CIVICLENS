# Phase 10.4 — Policy Indicator Registry and Baseline Construction Methodology

## 1. Overview
The **Policy Indicator Registry** (`policy_indicators` and `indicator_observations` tables, managed by `PolicyIndicatorRegistryService` in `backend/services/policy_indicator_service.py`) provides a rigorous, provenance-backed framework for measuring documented policy implementation and outcome changes across Tamil Nadu schemes and public policies.

It enforces three core methodological guarantees:
1. **Compatibility Enforcement**: Cross-period and cross-geography comparisons are strictly validated for compatible units, indicator definitions, geographic administrative boundaries, and reporting frequencies before any calculation is performed. Incompatible observations are never silently combined.
2. **Non-Zero Missing-Data Integrity**: Missing or unpublished values are stored and propagated as `None` (`NULL`), never coerced to `0.0`. A genuine observed zero (`0.0`) is explicitly distinguished from unavailable data.
3. **Explicit Baseline Provenance**: Every indicator baseline explicitly records whether its value is `OFFICIAL_PUBLISHED`, `CALCULATED_FROM_SOURCE_DATA`, or `UNAVAILABLE`.

---

## 2. Supported Indicator Domains
The Indicator Registry classifies indicators across 10 functional domains (`IndicatorDomain` enum in `backend/models/policy_evaluation.py`) alongside the 5-tier Results Chain (`INPUT`, `ACTIVITY`, `OUTPUT`, `OUTCOME`, `IMPACT`):

| Domain Enum (`IndicatorDomain`) | Typical Results Chain Tier | Example Indicator |
| :--- | :--- | :--- |
| `BUDGET_EXPENDITURE` | `INPUT` | Actual Revenue Expenditure on Chief Minister's Breakfast Scheme (`RUPEES_CRORE`) |
| `BENEFICIARY_COUNT` | `OUTPUT` | Enrolled women heads of households receiving monthly transfer (`COUNT`) |
| `FACILITIES_CONSTRUCTED_UPGRADED` | `OUTPUT` | Primary Health Centres upgraded with diagnostic equipment (`COUNT`) |
| `SERVICE_DELIVERY_COUNT` | `OUTPUT` | Hot nutritious breakfasts served across government primary schools (`COUNT`) |
| `TARGET_ACHIEVEMENT` | `OUTPUT` / `OUTCOME` | Percentage of sanctioned smart classrooms commissioned (`PERCENTAGE`) |
| `SERVICE_ACCESS` | `OUTCOME` | Share of rural habitations with functional 55 LPCD piped water supply (`PERCENTAGE`) |
| `EDUCATION_INDICATOR` | `OUTCOME` / `IMPACT` | Government school higher-education transition rate (`PERCENTAGE`) |
| `HEALTH_INDICATOR` | `OUTCOME` / `IMPACT` | Institutional delivery rate / Maternal Mortality Ratio (`PER_100000_LIVE_BIRTHS`) |
| `INFRASTRUCTURE_DEVELOPMENT` | `OUTPUT` / `OUTCOME` | All-weather rural road connectivity length constructed (`KM`) |
| `COMPLAINT_OR_RESOLUTION` | `OUTCOME` | Verified civic service-delivery grievances resolved within SLA (`PERCENTAGE`) |

> **Methodological Caution on Complaint & Resolution Measures**: Grievance counts and complaint resolution rates (`COMPLAINT_OR_RESOLUTION`) are only used when methodologically suitable—specifically when reporting channels, registration accessibility, and closure verification rules remain consistent between baseline and comparison periods. Raw increases in complaint volume may reflect improved reporting awareness rather than deteriorating service quality.

---

## 3. Mandatory 12 Attributes per Registered Indicator
Every `PolicyIndicator` record stores the following 12 required attributes:

1. **Canonical Indicator ID (`indicator_id`)**: Deterministic identifier (e.g., `IND-CMBS-ATTENDANCE-01`, or `-TEST-` suffixed IDs for fixtures).
2. **Definition (`definition` & `definition_code`)**: Exact operational definition of numerator, denominator, inclusion criteria, and canonical `definition_code` used to block silent combination of incompatible definitions.
3. **Unit (`unit`)**: Standardized measurement unit (`RUPEES_CRORE`, `RUPEES_LAKH`, `COUNT`, `PERCENTAGE`, `KM`, `RATIO`, etc.).
4. **Source (`source`)**: Authoritative publishing agency or dataset series (e.g., `TN Finance Dept Demand No. 43`, `UDISE+ State Flash Statistics`, `CAG Audit Report`).
5. **Reporting Frequency (`reporting_frequency`)**: Standardized cadence (`ANNUAL`, `QUARTERLY`, `MONTHLY`, `DECENNIAL_CENSUS`, `MULTI_YEAR_SURVEY`, `AD_HOC_AUDIT`).
6. **Geographic Level (`geographic_level` & `boundary_reference`)**: Administrative resolution (`STATE`, `DISTRICT`, `CONSTITUENCY`, `BLOCK`, `ULB`) plus explicit boundary vintage (e.g., `TN_38_DISTRICTS_2020` vs `TN_32_DISTRICTS_PRE_2019`).
7. **Baseline Period & Value (`baseline_period`, `baseline_value`, `baseline_construction_status`)**: Reference period prior to intervention and its nullable numeric value (`None` if unavailable).
8. **Comparison Period & Value (`comparison_period`, `comparison_value`)**: Follow-up evaluation period and its nullable numeric value (`None` if unavailable).
9. **Collection Method (`collection_method`)**: Data capture mechanism (`ADMIN_REGISTRY`, `SAMPLE_SURVEY`, `STATUTORY_AUDIT`, `CENSUS`, `GIS_REMOTE_SENSING`).
10. **Missing-Data Status (`missing_data_status`)**: Explicit completeness state (`COMPLETE`, `MISSING_BASELINE`, `MISSING_COMPARISON`, `MISSING_BOTH`, `PARTIAL_GEOGRAPHIC_COVERAGE`, `NOT_PUBLISHED_BY_SOURCE`).
11. **Calculation Formula (`calculation_formula`)**: Mathematical formula used to derive or aggregate the indicator (e.g., `(Actual_Expenditure / Budget_Estimate) * 100`, `SUM(District_Beneficiaries_i)`).
12. **Known Limitations (`known_limitations`)**: Documented caveats, reporting lags, coverage exclusions, or confounding factors.

---

## 4. Baseline Construction & Provenance Rules
When constructing or registering an indicator baseline via `PolicyIndicatorRegistryService.construct_baseline_from_observations()` or `register_indicator()`, the system records one of three explicit provenance states (`BaselineConstructionStatus`):

| Status | Meaning | Validation Rule |
| :--- | :--- | :--- |
| `OFFICIAL_PUBLISHED` | The baseline value was directly published as an official aggregate benchmark in a primary source document (e.g., Policy Note, NFHS-5 State Fact Sheet, CAG Report). | Requires a non-null `baseline_value` linked to a single authoritative source observation. |
| `CALCULATED_FROM_SOURCE_DATA` | No single aggregate baseline was published directly, so the baseline was computed from compatible granular source observations (e.g., summing or averaging all 38 district observations using `aggregation_method`). | Requires all constituent observations to be non-null and share identical `definition_code`, `unit`, and `boundary_reference`. Records the exact `calculation_formula`. |
| `UNAVAILABLE` | No pre-intervention baseline exists, or one or more constituent sub-observations are missing (`None`). | `baseline_value` **must** be `None`. Attempting to pass a numeric value with `UNAVAILABLE` raises a `ValueError`. |

---

## 5. Missing-Data Integrity (Never Treat Missing Data as Zero)
Public administration datasets frequently omit district rows or baseline years when reporting systems were not yet digitized. Treating missing data as `0.0` introduces severe downward bias in baselines and fabricates artificial positive growth.

- **Database Schema**: Both `PolicyIndicator.baseline_value`, `PolicyIndicator.comparison_value`, and `IndicatorObservation.value` are nullable `Float` columns.
- **Zero vs. Null Distinction**:
  - `value = 0.0` represents a verified empirical observation of zero (e.g., `0` facilities completed in Q1) and yields `MissingDataStatus.COMPLETE`.
  - `value = None` represents uncollected, redacted, or unpublished data and yields `MISSING_BASELINE`, `MISSING_COMPARISON`, `MISSING_BOTH`, or `PARTIAL_GEOGRAPHIC_COVERAGE`.
- **Sub-Observation Aggregation Safeguard**: If `construct_baseline_from_observations()` is given district observations where even a single district has `value = None`, it refuses to sum the remaining districts as if the missing district were zero. Instead, it sets `baseline_value = None`, `baseline_construction_status = UNAVAILABLE`, and `missing_data_status = PARTIAL_GEOGRAPHIC_COVERAGE`.

---

## 6. Four-Dimensional Compatibility Validation
Before `PolicyIndicatorRegistryService.compare_observations()` or `validate_observation_compatibility()` computes any change metric, it enforces compatibility across four dimensions and raises `IncompatibleIndicatorComparisonError` with a specific `error_code` if any check fails:

1. **Definition Compatibility (`DEFINITION_MISMATCH`)**:
   - Blocks comparisons when `baseline_obs.definition_code != comparison_obs.definition_code` (for example, when a department changes the definition of "functional tap connection" from 40 LPCD to 55 LPCD between baseline and follow-up).
2. **Unit Compatibility (`UNIT_MISMATCH`)**:
   - Blocks silent comparison of different units (e.g., `RUPEES_LAKH` vs `RUPEES_CRORE`, or `COUNT` vs `PERCENTAGE`).
   - Supports explicit linear scale conversion (`allow_linear_unit_conversion=True`) **only** for verified same-dimension pairs defined in `LINEAR_UNIT_CONVERSIONS` (e.g., `100 RUPEES_LAKH == 1.0 RUPEES_CRORE`). Cross-dimension pairs (`COUNT` vs `PERCENTAGE`) always raise `UNIT_MISMATCH`.
3. **Geographic Level & Boundary Compatibility (`GEOGRAPHIC_LEVEL_MISMATCH`, `GEOGRAPHIC_UNIT_MISMATCH`, `BOUNDARY_MISMATCH`)**:
   - Blocks comparing different geographic levels (`STATE` vs `DISTRICT`) or different geographic units (`TN-DIST-VILLUPURAM` vs `TN-DIST-MADURAI`).
   - Detects administrative boundary changes (`BOUNDARY_MISMATCH`): Tamil Nadu bifurcated several districts in 2019–2020 (expanding from 32 to 38 districts, e.g., splitting Kallakurichi from Villupuram, Chengalpattu from Kancheepuram, Tenkasi from Tirunelveli, Ranipet and Tirupattur from Vellore, and Mayiladuthurai from Nagapattinam). Comparing pre-bifurcation Villupuram (`TN_32_DISTRICTS_PRE_2019`) directly against post-bifurcation Villupuram (`TN_38_DISTRICTS_2020`) without boundary harmonization is blocked with `BOUNDARY_MISMATCH`.
4. **Reporting Period & Frequency Compatibility (`REPORTING_PERIOD_MISMATCH`)**:
   - Blocks comparing observations collected over incompatible reporting durations (e.g., comparing a `QUARTERLY` expenditure flow from `FY2023-24-Q1` against an `ANNUAL` expenditure flow from `FY2024-25`).
