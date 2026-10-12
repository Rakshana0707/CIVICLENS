# Phase 10 — Policy Outcome & Impact Evaluation Metric Definitions

## 1. Overview & Mathematical Standards

This specification defines the formal mathematical equations, boundary conditions, input lineages, and edge-case handling for all quantitative metrics computed in **Phase 10: Public Policy Outcome & Impact Evaluation**.

All metrics adhere to standard mathematical notations:
- Currency amounts are evaluated in **Indian Rupees (₹ in Crores)**.
- Ratios are expressed in **Percentages ($0.0\%$ to $100.0\%$)** or normalized decimals ($0.00$ to $1.00$).
- Division by zero is protected via defined fallback constants and explicit validity flags (`is_valid=False`, `reason="ZERO_DENOMINATOR"`).

---

## 2. Fiscal & Budget Execution Metrics

### 2.1 Budget Execution Rate ($BER$)
- **Purpose:** Measures the extent to which budgeted funds were actually expended by the implementing department.
- **Formula:**
  $$BER = \left( \frac{\text{Actual Expenditure}}{\text{Budget Estimate (BE)}} \right) \times 100$$
- **Input Variables:**
  - `Actual Expenditure`: Realized audited disbursements under the scheme's accounting head from CAG Appropriation Accounts ($A \ge 0$).
  - `Budget Estimate (BE)`: Legislative budgetary allocation approved in the annual budget ($BE > 0$).
- **Boundary Conditions:**
  - If $BE = 0$, $BER$ is undefined; flagged as `UNBUDGETED_EXPENDITURE`.
  - If $BER < 75.0\%$, classified as `SEVERE_UNDERUTILIZATION`.
  - If $75.0\% \le BER \le 105.0\%$, classified as `NORMAL_EXECUTION`.
  - If $BER > 105.0\%$, classified as `BUDGET_OVERRUN` (requires supplementary grant verification).

### 2.2 Revised Allocation Absorption Rate ($RAAR$)
- **Purpose:** Measures execution against the mid-year revised estimate.
- **Formula:**
  $$RAAR = \left( \frac{\text{Actual Expenditure}}{\text{Revised Estimate (RE)}} \right) \times 100$$
- **Boundary Conditions:**
  - If $RE = 0$, flagged as `ALLOCATION_SURRENDERED_MIDYEAR`.

### 2.3 Surrender of Funds Ratio ($SFR$)
- **Purpose:** Quantifies the proportion of approved budget returned to the treasury unspent.
- **Formula:**
  $$SFR = \max\left(0, \frac{BE - \text{Actual Expenditure}}{BE}\right) \times 100$$

### 2.4 March Rush Expenditure Index ($MREI$)
- **Purpose:** Detects lumpy, rushed year-end spending aimed at exhausting budget ceilings before fiscal year close (March 31).
- **Formula:**
  $$MREI = \left( \frac{\text{Expenditure in Month of March}}{\text{Total Annual Expenditure}} \right) \times 100$$
- **Benchmark:** An $MREI > 30.0\%$ triggers an `ANOMALOUS_YEAR_END_RUSH` advisory flag.

---

## 3. Output Delivery Metrics

### 3.1 Physical Target Realization Ratio ($PTRR$)
- **Purpose:** Assesses delivery fidelity of tangible physical goods, infrastructure, or services against stated policy targets.
- **Formula:**
  $$PTRR = \left( \frac{Q_{\text{actual}}}{Q_{\text{target}}} \right) \times 100$$
- **Input Variables:**
  - $Q_{\text{actual}}$: Verified physical count of delivered outputs (e.g., classrooms built, tablets distributed).
  - $Q_{\text{target}}$: Targeted output quantity announced in Department Policy Note or Budget Speech.
- **Boundary Conditions:**
  - If $Q_{\text{target}} \le 0$, flagged as `NO_QUANTITATIVE_TARGET_SPECIFIED`.
  - If $PTRR < 50.0\%$, classified as `CRITICAL_DELIVERY_SHORTFALL`.
  - If $PTRR > 120.0\%$, flagged for `TARGET_UNDERESTIMATION_CHECK`.

### 3.2 Realized Unit Cost ($RUC$)
- **Purpose:** Evaluates financial efficiency per unit of physical output delivered.
- **Formula:**
  $$RUC = \frac{\text{Actual Financial Expenditure}}{Q_{\text{actual}}}$$
- **Units:** ₹ per delivered unit (e.g., ₹ per km of rural road constructed, ₹ per school renovated).

### 3.3 Output Delivery Velocity ($ODV$)
- **Purpose:** Measures the average monthly pace of physical delivery relative to the planned project timeline.
- **Formula:**
  $$ODV = \frac{Q_{\text{actual}}}{\Delta t_{\text{months}}}$$

---

## 4. Beneficiary Coverage & Equity Metrics

### 4.1 Beneficiary Inclusion Rate ($BIR$)
- **Purpose:** Computes the proportion of the eligible target universe that actually received scheme benefits.
- **Formula:**
  $$BIR = \left( \frac{N_{\text{enrolled}} \cap N_{\text{eligible}}}{N_{\text{eligible}}} \right) \times 100$$
- **Input Variables:**
  - $N_{\text{eligible}}$: Estimated eligible population based on Census demographic projections or survey microdata.
  - $N_{\text{enrolled}}$: Verified active beneficiaries enrolled and receiving benefits.
- **Boundary Conditions:**
  - If $N_{\text{eligible}} \le 0$, flagged as `UNKNOWN_ELIGIBLE_UNIVERSE`.
  - $BIR$ is capped at $100.0\%$; an administrative figure exceeding $100\%$ indicates population denominator obsolescence or duplicate enrollment.

### 4.2 Exclusion Error Rate ($EER$)
- **Purpose:** Measures the percentage of eligible citizens wrongly excluded from benefits.
- **Formula:**
  $$EER = \left( \frac{N_{\text{eligible}} \setminus N_{\text{enrolled}}}{N_{\text{eligible}}} \right) \times 100 = 100\% - BIR$$

### 4.3 Demographic Parity Index ($DPI$)
- **Purpose:** Assesses equity of benefit delivery across marginalized groups (e.g., Scheduled Castes, Scheduled Tribes, Rural Women).
- **Formula:**
  $$DPI = \frac{\text{Share of Beneficiaries from Group } G}{\text{Share of Group } G \text{ in Total Population}} = \frac{B_G / B_{\text{total}}}{P_G / P_{\text{total}}}$$
- **Interpretation:**
  - $DPI = 1.0$: Exact demographic parity.
  - $DPI < 0.8$: Under-representation / potential systemic exclusion.
  - $DPI > 1.2$: Positive affirmative targeting.

---

## 5. Outcome & Impact Trajectory Metrics

### 5.1 Percentage Change in Outcome ($\Delta\%_{\text{outcome}}$)
- **Purpose:** Quantifies descriptive indicator movement between baseline and post-rollout periods.
- **Formula:**
  $$\Delta\%_{\text{outcome}} = \left( \frac{Y_{\text{follow-up}} - Y_{\text{baseline}}}{Y_{\text{baseline}}} \right) \times 100$$
- **Input Variables:**
  - $Y_{\text{baseline}}$: Verified baseline value at reference period $T_0$.
  - $Y_{\text{follow-up}}$: Measured value at evaluation period $T_1$.
- **Directional Interpretation:**
  - If indicator goal is *increase* (e.g., literacy rate, institutional delivery), positive change indicates favorable progress.
  - If indicator goal is *decrease* (e.g., infant mortality, drop-out rate), negative change indicates favorable progress.

### 5.2 Compound Annual Improvement Rate ($CAIR$)
- **Purpose:** Annualizes outcome progress over multi-year evaluation windows.
- **Formula:**
  $$CAIR = \left[ \left( \frac{Y_{\text{follow-up}}}{Y_{\text{baseline}}} \right)^{\frac{1}{n}} - 1 \right] \times 100$$
  where $n$ is the elapsed duration in years between $T_0$ and $T_1$.

### 5.3 Distance-to-Target Metric ($DTM$)
- **Purpose:** Measures how close the observed follow-up value is to the officially announced policy goal.
- **Formula:**
  $$DTM = \left( \frac{Y_{\text{follow-up}} - Y_{\text{baseline}}}{Y_{\text{target}} - Y_{\text{baseline}}} \right) \times 100$$
- **Interpretation:** $100\%$ indicates the stated target was fully achieved; $< 100\%$ indicates partial progress.

---

## 6. Geographic Disparity & Concentration Metrics

### 6.1 Spatial Disparity Ratio ($SDR$)
- **Purpose:** Measures the gap in per capita allocation or output density between the most favored and least favored districts.
- **Formula:**
  $$SDR = \frac{\text{Mean of Top 20\% Districts (Quintile 5)}}{\text{Mean of Bottom 20\% Districts (Quintile 1)}}$$
- **Boundary Conditions:**
  - If Bottom Quintile $= 0$, $SDR = \infty$; flagged as `EXTREME_REGIONAL_DEPRIVATION`.

### 6.2 Coefficient of Variation Across Districts ($CV_{\text{geo}}$)
- **Purpose:** Quantifies spatial dispersion of outputs or outcome indicators across Tamil Nadu's 38 districts.
- **Formula:**
  $$CV_{\text{geo}} = \frac{\sigma_{\text{districts}}}{\mu_{\text{districts}}} \times 100$$
  where $\mu$ is the statewide district mean and $\sigma$ is the standard deviation.

---

## 7. Audit Severity & Irregularity Metrics

### 7.1 CAG Irregularity Exposure Ratio ($CIER$)
- **Purpose:** Measures the share of scheme expenditure subjected to adverse statutory audit findings.
- **Formula:**
  $$CIER = \left( \frac{\sum \text{Quantified Audit Irregularities in CAG Reports}}{\text{Total Scheme Expenditure Audited}} \right) \times 100$$

### 7.2 Idle Capital Ratio ($ICR$)
- **Purpose:** Quantifies the proportion of capital investments sitting unutilized or non-operational due to lack of staff, equipment, or delays.
- **Formula:**
  $$ICR = \left( \frac{\text{Value of Assets Declared Idle by CAG / PWD}}{\text{Total Capital Outlay of Scheme}} \right) \times 100$$

---

## 8. Evidence Triangulation & Epistemic Metrics

### 8.1 Outcome Evidence Corroboration Score ($OECS$)
- **Purpose:** Synthesizes multi-source corroboration across statutory audits, surveys, news reports, and citizen grievances.
- **Formula:**
  $$OECS = \frac{\sum_{i \in \text{SUPPORTS}} w_i - \sum_{j \in \text{CONTRADICTS}} w_j}{\sum_{k \in \text{ALL}} w_k}$$
- **Weights by Source Tier:**
  - Tier 1 (Statutory / CAG / Gazette): $w = 1.0$
  - Tier 2 (Official Departmental / NFHS / MoSPI): $w = 0.8$
  - Tier 3 (Accredited Media of Record / Factcheck): $w = 0.6$
  - Tier 4 (Citizen Grievances / Academic Research): $w = 0.4$
  - Tier 5 (Uncorroborated Claims): $w = 0.1$
- **Scale:** Ranges continuously from $-1.0$ (complete contradiction) to $+1.0$ (complete corroboration).

### 8.2 Contradiction Ratio ($CR$)
- **Purpose:** Quantifies the prevalence of conflicting empirical evidence relative to total evidence items.
- **Formula:**
  $$CR = \frac{N_{\text{CONTRADICTS}}}{N_{\text{SUPPORTS}} + N_{\text{CONTRADICTS}}}$$
- **Interpretation:** $CR > 0.30$ triggers an `EMPIRICAL_CONTROVERSY` label in the Evaluation Explorer.

### 8.3 Causal Rigor Index ($CRI$)
- **Purpose:** Classifies the methodological strength of an evaluation study on a standardized scale from 0 to 100.
- **Rubric:**
  - Experimental RCT with verified compliance: $90 - 100$
  - Quasi-Experimental DiD with verified parallel trends: $75 - 89$
  - Regression Discontinuity with continuous density: $70 - 85$
  - Matched Observational (PSM / IPTW): $50 - 69$
  - Descriptive Before-and-After (No control group): $25 - 49$
  - Anecdotal / Unstructured Narrative: $0 - 24$
