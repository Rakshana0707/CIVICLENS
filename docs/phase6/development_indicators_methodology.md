# Phase 6 — Constituency Development Indicators Methodology

## 1. Executive Summary & Purpose

Phase 6 of **CIVICLENS TN** establishes an empirical analysis framework for tracking long-term socioeconomic, demographic, and infrastructure indicators across Tamil Nadu constituencies:
* **Decennial Census Data:** Population, gender ratios, SC/ST percentages, literacy baselines, workforce participation (Office of the Registrar General & Census Commissioner).
* **Department of Economics and Statistics (DES TN):** District Statistical Handbooks, Gross District Domestic Product (GDDP), per-capita income, and agricultural output.
* **National & State Dashboards:** Jal Jeevan Mission (rural piped water coverage), UDISE+ (school education infrastructure), Health Management Information System (HMIS / NFHS infant mortality and maternal health), PMGSY (rural road connectivity).
* **Open Government Data Platform (data.gov.in):** Departmental open releases.

> [!IMPORTANT]
> **Core Methodological Safeguards:**
> 1. **Defensible Geographic Mapping:** District-level statistics must **never** be copied directly to individual constituencies without an explicit, documented spatial or population-weighted mapping (`ConstituencyGeographicMapping`).
> 2. **Non-Causality Principle:** A rise in literacy or drop in infant mortality over a legislative tenure is **not proof** that the elected representative caused the change. Macroeconomic trends, state-wide flagship policies, and demographic shifts drive outcomes.
> 3. **Boundary & Delimitation Awareness:** Comparing pre-2008 indicators (Census 2001) with post-2008 figures (Census 2011) must account for the 2008 Delimitation Order boundary reorganizations.
> 4. **Unit Consistency Enforcement:** Comparisons across reporting periods require identical measurement units or explicit normalization.

---

## 2. Supported Indicator Taxonomy

| Category | Primary Indicators | Standard Unit | Primary Source |
|---|---|---|---|
| **Demographics** | `TOTAL_POPULATION`, `SC_POPULATION`, `ST_POPULATION`, `SEX_RATIO` | `COUNT`, `PER_1000` | Census of India |
| **Education** | `LITERACY_RATE`, `FEMALE_LITERACY_RATE`, `PRIMARY_SCHOOLS_COUNT`, `PUPIL_TEACHER_RATIO` | `PERCENT`, `COUNT`, `RATIO` | Census / UDISE+ |
| **Healthcare** | `INFANT_MORTALITY_RATE`, `PHC_COUNT`, `INSTITUTIONAL_DELIVERY_PCT` | `PER_1000`, `COUNT`, `PERCENT` | NFHS / HMIS / DES TN |
| **Water & Sanitation** | `HOUSEHOLD_TAP_WATER_PCT`, `INDIVIDUAL_TOILET_COVERAGE_PCT` | `PERCENT` | Jal Jeevan / SBM-G |
| **Infrastructure** | `SURFACED_ROADS_KM`, `HOUSEHOLD_ELECTRIFICATION_PCT` | `KM`, `PERCENT` | PWD / RDPR TN |
| **Livelihood & Economy**| `WORKFORCE_PARTICIPATION_RATE`, `AGRICULTURAL_WORKERS_PCT` | `PERCENT` | Census PCA / DES TN |

---

## 3. Data Model & Field Specifications

Stored in `development_indicators` entity ([DevelopmentIndicator](file:///E:/CIVCLENS/backend/models/representative.py)):

| Field Name | Type | Description |
|---|---|---|
| `indicator_id` | String (PK) | Canonical identifier (e.g. `IND-AC013-LITERACY-2011`). |
| `constituency_id` | String (FK, Nullable) | Linked constituency (NULL if pure district/state observation). |
| `geographic_unit_id` | String | Geographic unit (`AC-013`, `DISTRICT-CHENNAI`, `STATE-TN`). |
| `indicator_name` | String | Standard indicator code from taxonomy. |
| `value` | Float | Measured numerical value. |
| `unit` | String | Standardized measurement unit (`PERCENT`, `COUNT`, `PER_1000`, `KM`). |
| `reference_period` | String | Reference year or financial year (`2011`, `2021`, `2023-24`). |
| `geographic_level` | String (Enum) | `CONSTITUENCY`, `DISTRICT`, `STATE`, or `BLOCK_TALUK`. |
| `source_document_id` | String (FK) | Provenance link to `backend/models/common.py` `Document`. |
| `source_reference` | String | Exact table/page citation (e.g. *Census 2011 PCA Table A-1*). |
| `calculation_method` | String (Enum) | `DIRECT_OBSERVATION`, `AREA_WEIGHTED_INTERPOLATION`, `POPULATION_WEIGHTED_AGGREGATION`, or `OFFICIAL_PUBLICATION`. |
| `data_quality_status` | String (Enum) | `VERIFIED`, `INTERPOLATED`, `PROVISIONAL`, `ESTIMATED`, `INCONSISTENT_UNIT`, `MISSING`. |

---

## 4. Defensible Geographic Mapping Engine

### 4.1 The District-to-Constituency Disaggregation Problem
Most Indian socioeconomic surveys (NFHS, NSSO, District Statistical Handbooks) publish data at the **district** level (38 districts in Tamil Nadu), whereas political representatives represent **constituencies** (234 Assembly seats).
* **Unacceptable Practice:** Copying the Salem district infant mortality rate to Edappadi constituency without documenting the geographic assumption.
* **CIVICLENS TN Protocol:**
  1. The system checks for a direct constituency-level observation (`DIRECT_OBSERVATION`).
  2. If absent, the system queries `ConstituencyGeographicMapping` for that constituency's intersection with the parent district:
     - `area_share_in_district` (fraction of district land area)
     - `population_share_in_district` (fraction of district census population)
  3. If a valid mapping exists:
     - **Intensive Rates (Percent, Ratios):** Assigned as district baseline with `POPULATION_WEIGHTED_AGGREGATION` and status `INTERPOLATED`.
     - **Extensive Counts (Totals, Kilometers):** Scaled by `population_share_in_district` or `area_share_in_district`.
  4. If **no mapping exists**, the pipeline **refuses** to fabricate or copy data, raising `GeographicMappingError`.

---

## 5. Non-Causality & Baseline Comparative Safeguards

### 5.1 Temporal Baseline Trajectories
When analyzing changes between two reporting periods ($t_1$ to $t_2$):
$$\Delta_{\text{abs}} = V_{t_2} - V_{t_1}, \quad \Delta_{\text{pct}} = \frac{V_{t_2} - V_{t_1}}{V_{t_1}} \times 100$$

### 5.2 Mandatory Safeguards
1. **Delimitation Boundary Shift Flag:** If the comparison period crosses 2008 (e.g. Census 2001 vs Census 2011), the service flags `has_delimitation_shift = True` and displays:
   > *"CAUTION: Comparison crosses 2008 Delimitation Order boundary reorganization. Geographical boundaries are not identically matched."*
2. **Inconsistent Unit Assertion:** If the start period has unit `COUNT` and the end period has unit `PERCENT`, the service raises `InconsistentUnitError`.
3. **Non-Causality Notice:** Every baseline trajectory report includes the mandatory disclaimer:
   > *"NON-CAUSALITY NOTICE: Socioeconomic indicator changes reflect multi-factor macro conditions, state/central funding, and demographic dynamics. Temporal progress is NOT proof of individual representative causality."*

---

## 6. Verification & Test Suite

The pipeline is verified in `tests/unit/test_phase6_development_indicators.py` covering:
1. **Direct Observation vs. Defensible Interpolation:** Confirming direct records take precedence and weighted interpolation requires documented mapping.
2. **Rejection of Unmapped District Assignment:** Verifying `GeographicMappingError` is raised if no mapping exists.
3. **Inconsistent Measurement Units Detection:** Verifying `InconsistentUnitError` is raised on mismatched units.
4. **Delimitation Era Warning:** Verifying that comparisons crossing 2008 trigger the delimitation warning.
5. **Non-Causality Disclaimer:** Verifying every comparative report retains the non-causality disclaimer.
