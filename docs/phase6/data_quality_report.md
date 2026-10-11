# Phase 6: Data Quality and Provenance Audit Report

**CIVICLENS TN — Phase 6 Public Representative Performance Analyzer**  
**Audit Status:** Complete  
**Date:** 2026-10-11

---

## 1. Statutory Data Quality Framework

CIVICLENS enforces a four-tiered data quality taxonomy:
1. **Verified Primary Records:** Data directly extracted from official gazettes, Sansad attendance rolls, Election Commission of India Form-20 returns, and CAG audit reports.
2. **Reputable Research Aggregations:** Parliamentary monitoring by non-partisan research bodies (e.g., PRS Legislative Research, Ashoka University TCPD).
3. **Provisional / Located Records:** Official public URLs cataloged where direct bulk machine extraction is pending.
4. **Data Gaps / Unavailable Data:** Systematically cataloged under the Data Completeness Index.

---

## 2. Ingestion & Quality Audit Metrics

| Dimension | Records Evaluated | Accepted & Ingested | Rejected / Withheld | Primary Reason for Withholding |
|---|---|---|---|---|
| **Representative Registry** | 42 Canonical Profiles | 42 (39 PCs + 3 Sample ACs) | 0 | None. Verified against ECI Delimitation Orders. |
| **Parliamentary Representatives** | 3 Detailed Profiles | 3 (Perambalur, Arani, Coimbatore) | 0 | None. Verified via PRS MP Track & Sansad Rolls. |
| **Legislative Activity Records** | 9 Activity Observations | 9 (Questions, Debates, Attendance) | 0 | None. Documented floor activity with source references. |
| **Constituency Works (MPLADS)** | 2 State-Level Audits | 2 (Q.1683, AU4517) | Unlinked local works | MPLADS online portal lacks work-level MP exports. |
| **Development Indicators** | 6 District Indicators | 6 (Census 2011 & DES TN 2021) | Unmapped taluks | Rejection of unmapped district-to-AC extrapolations. |
| **Cataloged Public Datasets** | 64 Total Sources | 64 Preserved in Catalog | 0 | Preserved in Raw Phase 6 Inventory. |

---

## 3. Specific Data Quality Issues Identified & Resolved

### Issue 1: State Assembly Daily Attendance Publication Gap
- **Finding:** Tamil Nadu Legislative Assembly maintains internal daily attendance rolls, but individual member attendance percentages are **not gazetted online**.
- **Resolution:** Rather than assigning 0% attendance to TN MLAs, the system tags attendance as `NOT_GAZETTED_ONLINE` and tracks administrative transparency in the Data Completeness Index.

### Issue 2: MPLADS "Utilisation" Definition Divergence
- **Finding:** In Parliament Answer AU4517 (`D8-002`), the Ministry defines *utilization* as "funds recommended by the MP out of entitlement", whereas standard financial accounting defines utilization as *actual expenditure supported by utilization certificates*.
- **Resolution:** The system enforces strict field separation between `sanctioned_amount`, `released_amount`, and `reported_expenditure`, preventing misleading expenditure claims.

### Issue 3: Micro-Constituency Demographic Extrapolations
- **Finding:** Census 2011 reports literacy and demographic data at District, Taluk, and Ward levels, whereas electoral constituencies cross taluk lines.
- **Resolution:** As established in Phase 6.6, district data is **never arbitrarily assigned** to Assembly Constituencies without a mathematically defensible geographic mapping (`ConstituencyGeographicMapping`).

### Issue 4: Ministerial Question Hour Exemption
- **Finding:** State and Central Ministers do not submit private member questions or balloted queries.
- **Resolution:** System marks ministerial tenure, preventing biased comparisons against non-ministerial backbenchers.
