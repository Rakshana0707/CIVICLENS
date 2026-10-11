# Representative Performance Metrics & Comparative Analysis Methodology

**CIVICLENS TN — Phase 6.8 Analytical Specification**

---

## 1. Executive Overview & Ethical Principles

The CIVICLENS Performance Metrics Engine provides an open, transparent, and auditable methodology for analyzing the empirical track record of Members of the Legislative Assembly (MLAs) in Tamil Nadu and Members of Parliament (MPs) in the Lok Sabha.

### Core Ethical Safeguards

1. **Anti-Pejorative Mandate:**
   - Under no circumstances does CIVICLENS apply normative or pejorative labels (e.g., *"corrupt"*, *"ineffective"*, *"bad"*, or *"ideal"*) to elected representatives based on numerical indicators.
   - All scores reflect **documented public records** and do not capture informal dispute resolutions, unminuted constituent meetings, floor interventions not documented in digital Hansards, or executive administration responsibilities.

2. **Missing Data Non-Penalization:**
   - Where public authorities have failed to publish data (such as MLA-wise daily digital attendance registers in the Tamil Nadu Legislative Assembly), representatives are **never assigned a zero score**.
   - Instead, the system computes an independent **Data Completeness Index**, isolating public administration transparency from legislative performance.

3. **Strict Cohort Isolation:**
   - Representatives are compared strictly within homogeneous cohorts sharing identical institutional rules, sitting frequencies, and constitutional remits (e.g., TN Assembly MLAs vs. TN Assembly MLAs; Lok Sabha MPs vs. Lok Sabha MPs).
   - Direct cross-body ranking between MLAs and MPs without institutional normalization is strictly prohibited.

4. **Composite Index Full Disclosure:**
   - Any multi-dimensional composite index exposes its constituent parts, individual raw values, normalization algorithms, weighting schemes, missing data treatments, and empirical sensitivity margins ($\pm 20\%$).

---

## 2. Six Discrete Performance Dimensions

Metrics are tracked independently across six distinct operational dimensions:

```
┌────────────────────────────────────────────────────────────────────────┐
│                   CIVICLENS PERFORMANCE DIMENSIONS                     │
└────────────────────────────────────────────────────────────────────────┘
     │
     ├── 1. Legislative Activity (Floor questions, debates, attendance)
     ├── 2. Constituency Works (MPLADS/MLACDS sanctions, WIP, completions)
     ├── 3. Financial Execution (Sanctions, releases, unspent balances, ratios)
     ├── 4. Development Indicator Trends (Socioeconomic deltas over baselines)
     ├── 5. Promise-Related Evidence (Phase 3 & 6.7 manifesto alignment links)
     └── 6. Data Completeness & Reliability (Documented vs. expected records)
```

---

### Dimension 1: Legislative Activity

Tracks representative participation in floor proceedings, adjusted by sitting baselines.

- **Sitting-Adjusted Question Rate:**
  $$\text{Questions Per Sitting} = \frac{\text{Total Starred} + \text{Total Unstarred Questions}}{\text{Annual Assembly / Parliamentary Sittings}}$$
  - Lok Sabha Annual Sitting Baseline: ~65 sittings.
  - Tamil Nadu Legislative Assembly Baseline: ~38 sittings.
- **Debate Interventions:**
  $$\text{Total Debates} = \sum \text{Speeches, Zero Hour Mentions, Calling Attention Interventions}$$
- **Attendance Percentage:**
  - Tracked as verified percentage only when gazetted online (Lok Sabha).
  - Explicitly marked as `NOT_GAZETTED_ONLINE` for TN MLAs without imputation penalty.
- **Ministerial Exception:** Ministers do not balloted questions or submit private member bills by parliamentary convention; this exclusion is marked without scoring degradation.

---

### Dimension 2: Constituency Works and Project Status

Tracks physical projects sanctioned under local area development funds (MLACDS for MLAs, MPLADS for MPs).

- **Project Status Distribution:**
  - $\text{Total Works} = \text{Proposed} + \text{Sanctioned} + \text{WIP} + \text{Reported Completed} + \text{Independently Verified Completed}$.
- **Completion Rate Percentage:**
  $$\text{Completion Rate (\%)} = \frac{\text{Reported Completed} + \text{Independently Verified Completed}}{\text{Total Works}} \times 100$$
- **Attribution Separation:**
  - Separates representative-sponsored works (MPLADS / MLACDS) from general executive state/central schemes in the constituency to prevent false attribution.

---

### Dimension 3: Financial Execution

Evaluates financial velocity and treasury utilization under constituency development funds.

- **Total Sanctioned, Released, and Expended:**
  $$\text{Unspent Released Balance} = \max(0, \text{Total Released Funds} - \text{Reported Expenditure})$$
- **Expenditure-to-Release Ratio:**
  $$\text{Expenditure Ratio (\%)} = \frac{\text{Reported Expenditure}}{\text{Total Released Funds}} \times 100$$
- **Treasury Pacing Note:** Funds released by the District Collectorate frequently experience administrative lag; unspent balances do not imply representative negligence.

---

### Dimension 4: Development Indicator Trends

Tracks socioeconomic and demographic indicators (literacy rates, water access, healthcare facilities) across reference periods.

- **Baseline vs. Current Trajectory:**
  $$\Delta = \text{Value}_{\text{current}} - \text{Value}_{\text{baseline}}$$
  $$\% \text{ Change} = \frac{\text{Value}_{\text{current}} - \text{Value}_{\text{baseline}}}{\text{Value}_{\text{baseline}}} \times 100$$
- **Non-Causality Rule:** Macroeconomic indicator shifts are multi-causal; CIVICLENS explicitly displays a statutory disclaimer that representative tenure cannot be inferred as the sole cause of district socioeconomic shifts.

---

### Dimension 5: Promise-Related Evidence

Evaluates alignment between party manifesto commitments (Phase 3) and empirical government delivery (Phase 6.7).

- **Evidence Stage Breakdown:**
  1. `PROMISE_IDENTIFIED`
  2. `RELEVANT_SCHEME_IDENTIFIED`
  3. `POLICY_ACTION_DOCUMENTED`
  4. `PROJECT_WORK_RECORDED`
  5. `OUTCOME_INDICATOR_OBSERVED`
  6. `INSUFFICIENT_EVIDENCE`
- **Substantive Progress Percentage:**
  $$\text{Substantive Progress (\%)} = \frac{\text{Policy Action} + \text{Project Recorded} + \text{Outcome Observed}}{\text{Total Linked Promises}} \times 100$$

---

### Dimension 6: Data Completeness and Reliability

Quantifies public document availability across all operational domains.

- **Completeness Ratio:**
  $$\text{Data Completeness Ratio} = \frac{\sum_{i=1}^{4} \mathbb{I}(\text{Dimension } i \text{ Available})}{4}$$
  - $\mathbb{I} = 1$ if at least one verified record exists, $0$ otherwise.
- **Fairness Guarantee:** High completeness implies robust public oversight; low completeness isolates departmental data gaps rather than penalizing the elected representative.

---

## 3. Cohort Normalization & Comparative Analysis

When comparative analysis within a cohort (e.g., all 234 Tamil Nadu MLAs during the 16th Assembly) is requested:

1. **Min-Max Normalization (0–100 Scale):**
   $$\text{Score}_{\text{norm}} = \frac{x_i - \min(X)}{\max(X) - \min(X)} \times 100$$
2. **Percentile Rank:**
   $$\text{Percentile Rank} = \frac{\text{Rank}(x_i) - 1}{N - 1} \times 100$$
3. **Cohort Homogeneity Requirement:**
   - Any attempt to compare an MLA against an MP without cohort adjustment raises an `IncompatibleCohortError`.

---

## 4. Transparent Composite Index & Sensitivity Analysis

Where a consolidated summary index is requested, the system computes an explicitly weighted composite score:

### Default Base Weights
- Legislative Activity: $w_{\text{leg}} = 0.25$
- Constituency Works: $w_{\text{works}} = 0.25$
- Financial Execution: $w_{\text{fin}} = 0.25$
- Promise Evidence: $w_{\text{prom}} = 0.25$

### Dynamic Missing-Data Treatment
If dimension $k$ has no public records, its weight is **not set to zero with a penalty**. Instead, the remaining observed dimensions are dynamically re-normalized:
$$w'_j = \frac{w_j}{\sum_{m \in \text{Observed}} w_m}$$
$$\text{Composite Score} = \sum_{j \in \text{Observed}} S_j \times w'_j$$

### Sensitivity Analysis
The system automatically perturbs the dominant dimension weight by $\pm 20\%$ and recomputes the score to report sensitivity margins:
$$\Delta_{\text{sensitivity}} = \text{Score}_{\text{perturbed}} - \text{Score}_{\text{base}}$$
This ensures users can verify whether small methodological weight variations change relative assessments.
