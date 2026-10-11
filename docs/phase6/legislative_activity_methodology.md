# Phase 6 — Legislative Activity Analysis Methodology

## 1. Executive Summary & Purpose

Phase 6 of **CIVICLENS TN** provides a rigorous, objective analytical pipeline for measuring legislative participation among elected representatives:
* **Members of Parliament (Lok Sabha & Rajya Sabha)** representing Tamil Nadu
* **Members of the Legislative Assembly (Tamil Nadu Legislative Assembly - TNLA)**

The pipeline is grounded in empirical, record-based calculation, rejecting speculation and artificial equivalence.

> [!IMPORTANT]
> **Core Methodological Principles:**
> 1. **Zero Activity $\ne$ Unavailable Record:** If an institution does not officially publish or maintain public individual records (e.g. MLA daily attendance registers), the metric is explicitly recorded as `UNAVAILABLE` or `NOT_RECORDED`. It is **never** assigned a value of 0%.
> 2. **No Raw Parity Across Divergent Institutions:** Lok Sabha MPs and Tamil Nadu MLAs operate under fundamentally distinct parliamentary rules, sitting days, and question balloting procedures. Comparing raw sums without institutional context is methodologically flawed.
> 3. **Volume $\ne$ Effectiveness:** High activity counts reflect procedural volume and opportunities seized, not legislative quality, policy outcomes, or representative effectiveness.

---

## 2. Institutional Frameworks & Divergences

The analyzer evaluates representatives strictly within the context of their institutional arena:

| Dimension | Tamil Nadu Legislative Assembly (TNLA) | Lok Sabha (Parliament) | Rajya Sabha (Parliament) |
|---|---|---|---|
| **Tier** | State Legislature (Unicameral) | Lower House of Parliament | Upper House of Parliament |
| **Average Sittings / Year** | ~35 to 45 Days | ~60 to 75 Days | ~60 to 75 Days |
| **Question Hour Mechanism** | Oral Starred Questions with supplementaries; unstarred replies compiled in assembly synopses. | Centralized computerized ballot; maximum 5 questions admitted per MP per day (1 Starred + 4 Unstarred). | Centralized computerized ballot; maximum 5 questions admitted per MP per day. |
| **Attendance Reporting** | Kept in internal assembly secretariat registers; **not publicly gazetted or published online**. | Electronic sign-in registers published per session on Sansad portal / PRS India. | Official session attendance records published online. |
| **Debate Formats** | Demands on Grants, Call Attention (Rule 55), Rule 110 statements, Zero Hour mentions. | Rule 193 discussions, Calling Attention, Zero Hour, Budget debates, Special Mentions. | Special Mentions, Short Duration discussions, Government Bills. |
| **Ministerial Exclusion Rule** | Ministers, Chief Minister, Speaker do not submit questions or private member bills. | Union Ministers, Speaker/Deputy Speaker do not submit questions. | Ministers, Chairman/Deputy Chairman do not submit questions. |

---

## 3. Supported Metrics & Storage Specifications

The analyzer calculates **only** metrics supported by statutory public records:

### 3.1 Itemized Activity Entity (`LegislativeActivity`)
Every individual activity entry records:
- `representative_id`: Canonical representative identifier.
- `legislative_body`: `TN_ASSEMBLY`, `LOK_SABHA`, or `RAJYA_SABHA`.
- `session`: Legislative term and session number (e.g. `16th Assembly - Session 4`, `17th Lok Sabha - Session 11`).
- `activity_type`:
  - `QUESTION_STARRED`: Oral questions requiring in-person ministerial response.
  - `QUESTION_UNSTARRED`: Written questions with tabled written replies.
  - `DEBATE`: Speeches, bill discussions, and floor interventions.
  - `ATTENDANCE`: Officially gazetted session attendance percentages.
  - `COMMITTEE`: Recorded participation in Parliamentary/Assembly Standing Committees.
  - `BILL`: Private Member Bills introduced.
  - `CALL_ATTENTION`: Urgent public importance motions.
- `activity_date`: Transaction date (where documented).
- `count` or `value`: Integer count for interventions/questions; floating percentage for attendance.
- `source_document_id`: Foreign key reference to `backend/models/common.py` `Document`.
- `source_reference`: Traceable citation (e.g. `Lok Sabha Q.No 1420`, `TNLA Hansard Vol 14, p. 52`).
- `data_quality_status`: `VERIFIED`, `PARTIAL`, `UNAVAILABLE`, or `NOT_RECORDED`.

---

## 4. Methodological Safeguards

### 4.1 Distinguishing Unavailable Records from Zero Activity
A critical failure mode in civic data analysis is treating unrecorded data as null or zero:
* **The Problem:** The Tamil Nadu Legislative Assembly Secretariat does not publish open online member-wise daily attendance records. If a system defaults missing values to zero, every MLA would falsely be shown as having "0% attendance".
* **CIVICLENS TN Solution:** When data is absent from institutional publication, the pipeline generates an explicit `UNAVAILABLE` marker. The summary displays:
  ```json
  {
    "attendance": {
      "percentage": null,
      "status": "UNAVAILABLE",
      "is_available": false,
      "note": "Attendance registers are maintained internally; daily member-wise attendance percentages are NOT publicly gazetted online."
    }
  }
  ```

### 4.2 Cross-Institutional Normalization (MPs vs. MLAs)
Direct comparisons between MPs and MLAs are prohibited unless normalized and contextualized:
* **Sitting Disparity:** A Lok Sabha MP with 50 debates over 150 sittings (0.33 debates/sitting) is participating at a lower rate than an MLA with 30 debates over 40 sittings (0.75 debates/sitting), despite having a higher raw count.
* **The Normalization Model:** The service calculates activity rates per 10 sittings:
  $$\text{Normalized Rate} = \frac{\text{Raw Activity Count}}{\text{Annual Average Sittings}} \times 10$$
* **Comparison Warning:** Any cross-institutional comparison automatically injects a mandatory institutional caveat and refuses uncontextualized raw league tables.

### 4.3 Why Volume Does Not Equal Effectiveness
The pipeline explicitly decouples participation volume from legislative impact:
1. **Ministerial Roles:** Chief Ministers, Cabinet Ministers, and party floor leaders rarely or never submit questions or Private Member Bills; their performance is executive and legislative steering, not questioning.
2. **Floor Allocation Quotas:** Backbenchers receive speech time based on strict party-strength quotas, not individual initiative.
3. **Drafting Quality vs Count:** A single well-researched intervention on coastal regulation or state autonomy carries greater legislative impact than ten templated questions.
4. **Disclaimers:** Every analytical summary report includes the mandatory standard disclaimer:
   > *"Activity counts reflect documented participation volume, not legislative quality, policy effectiveness, or constituency impact."*

---

## 5. Verification & Testing Strategy

The pipeline is verified in `tests/unit/test_phase6_legislative_activity.py` covering:
1. **Accurate Summation:** Questions (starred/unstarred), debates, and bills summed from traceable records.
2. **Unavailable Data Handling:** Ensuring missing attendance returns `None` and `UNAVAILABLE`, never `0.0%`.
3. **Provenance Traceability:** Verifying source reference citations are maintained on summaries.
4. **Cross-Institutional Caution:** Verifying that comparing an MP and an MLA triggers the cross-institutional warning and normalized metrics.
