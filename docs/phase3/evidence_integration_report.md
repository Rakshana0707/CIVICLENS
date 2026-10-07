# CIVICLENS TN — Phase 3.22
## Real Government Evidence Integration Report

> **CRITICAL RULE: CANDIDATE RETRIEVAL & EVIDENCE LINKING ONLY**
> This report details official government evidence collection and candidate matching.
> **It does NOT conclude whether any promise is implemented, partially implemented, or failed.**
> **Absence of evidence strictly evaluates to `no_evidence_found` — NEVER `not_implemented`.**

---

## 1. Executive Summary & Acquisition Metrics

- **Execution Timestamp**: `2026-10-07T10:35:04.596949+00:00`
- **Total Valid Promises Evaluated**: `1065`
- **Official Government Evidence Items**: `12`
- **Promises Linked to Candidate Evidence**: `10` (0.9%)
- **Promises Evaluated as `no_evidence_found`**: `1055` (99.1%)
- **Total Candidate Evidence Links Created**: `10`
- **Retrieval Methodology**: `multi_signal_hybrid_retrieval`

---

## 2. Source Hierarchy & Evidence Tier Distribution

Evidence items were retrieved strictly from whitelisted Tamil Nadu government domains (`tn.gov.in`, `cms.tn.gov.in`, `budget.tn.gov.in`, `tnsocialwelfare.tn.gov.in`, `assembly.tn.gov.in`, `dipr.tn.gov.in`):

| Source Tier | Evidence Category | Domain Sources | Candidate Links | Weight |
| :--- | :--- | :--- | :---: | :---: |
| **Tier 1** | Primary Government Orders (G.O.s), Legislative Acts | `cms.tn.gov.in`, `tn.gov.in`, `assembly.tn.gov.in` | `7` | **1.00** |
| **Tier 2** | Department Policy Notes, State Budget Demand Books | `budget.tn.gov.in`, `tnsocialwelfare.tn.gov.in` | `3` | **0.90** |
| **Tier 3** | Official Press Releases (DIPR), Department Bulletins | `dipr.tn.gov.in` | `0` | **0.80** |

---

## 3. Registered Official Government Evidence Corpus

Summary of registered official Tamil Nadu government evidence items:

| Ev ID | Source Title & Reference | Source Type | Publisher | Tier |
| :---: | :--- | :--- | :--- | :---: |
| `1` | **G.O.(Ms) No. 104 — Implementation of Free Laptop Distribution Scheme for High School Students**<br>`G.O.(Ms) No. 104, School Education (SE4(2)) Dept, dated 15.09.2021` | Government Order | School Education Department, Government of Tamil Nadu | Tier 1 |
| `2` | **G.O.(Ms) No. 116 — Moovalur Ramamirtham Ammaiyar Higher Education Assurance Scheme (Pudhumai Penn)**<br>`G.O.(Ms) No. 116, Social Welfare & Women Empowerment Dept, dated 05.09.2022` | Government Order | Social Welfare & Women Empowerment Department, Government of Tamil Nadu | Tier 1 |
| `3` | **G.O.(Ms) No. 58 — Kalaignar Magalir Urimai Thogai Scheme Guidelines & Monthly Grant Disbursement**<br>`G.O.(Ms) No. 58, Special Programme Implementation Dept, dated 12.08.2023` | Government Order | Special Programme Implementation Department, Government of Tamil Nadu | Tier 1 |
| `4` | **G.O.(Ms) No. 280 — Chief Minister Comprehensive Health Insurance Scheme (CMCHIS) Renewal & Medical Coverage Expansion**<br>`G.O.(Ms) No. 280, Health and Family Welfare (P1) Dept, dated 20.12.2021` | Government Order | Health & Family Welfare Department, Government of Tamil Nadu | Tier 1 |
| `5` | **TN Agriculture Budget Speech 2023-2024 — Free Electricity & Farmer Relief Sanctions**<br>`Demand Book 2023-24, Agriculture & Farmers Welfare Dept` | Budget Document | Finance Department, Government of Tamil Nadu | Tier 2 |
| `6` | **G.O.(Ms) No. 240 — Athikadavu-Avinashi Groundwater Recharge & Irrigation Project Administrative Sanction**<br>`G.O.(Ms) No. 240, Water Resources (ISW2) Dept, dated 18.07.2022` | Government Order | Water Resources Department, Government of Tamil Nadu | Tier 1 |
| `7` | **G.O.(Ms) No. 42 — Free Bus Fare Travel Scheme for Women in Town Buses**<br>`G.O.(Ms) No. 42, Transport (C1) Dept, dated 08.05.2021` | Government Order | Transport Department, Government of Tamil Nadu | Tier 1 |
| `8` | **DIPR Official Press Release — Statewide Expansion of Primary School Breakfast Scheme**<br>`DIPR Press Release No. 1420 dated 25.08.2023` | Official Press Release | Department of Information and Public Relations (DIPR), Tamil Nadu | Tier 3 |
| `9` | **Naan Mudhalvan Youth Skill Enhancement & Career Guidance Policy Guidelines**<br>`Policy Note 2022-23, Skill Development Dept` | Policy Note | Skill Development & Employment Department, Tamil Nadu | Tier 2 |
| `10` | **G.O.(Ms) No. 312 — Makkalai Thedi Maruthuvam (Healthcare at Doorstep) Launch**<br>`G.O.(Ms) No. 312, Health & Family Welfare Dept, dated 05.08.2021` | Government Order | Health & Family Welfare Department, Government of Tamil Nadu | Tier 1 |
| `11` | **Tamil Nadu Legislative Assembly Act — Cauvery Delta Special Agricultural Protection Zone Act 2020**<br>`Tamil Nadu Act No. 11 of 2020, Legislative Assembly` | Legislative Document | Tamil Nadu Legislative Assembly | Tier 1 |
| `12` | **TN State Budget 2023-2024 — Sanction for Coimbatore & Madurai Metro Rail Phase 1**<br>`Budget Speech 2023-24, Transport & Urban Infrastructure` | Budget Document | Finance Department, Government of Tamil Nadu | Tier 2 |

---

## 4. Top High-Relevance Candidate Evidence Links

Sample candidate evidence matches demonstrating strong domain & keyword alignment:

| Promise ID | Promise Excerpt | Matched Government Evidence | Relevance Score | Tier |
| :--- | :--- | :--- | :---: | :---: |
| `MF-PMK-2016:p12:eefaefa6e20c` | Chennai Metro Rail service will be extended.... | **TN State Budget 2023-2024 — Sanction for Coimbatore & Madurai Metro Rail Phase 1** | **0.2802** | Tier 2 |
| `MF-AIADMK-2026:p5:74e5b5322e3b` | Free bus travel scheme for men, similar to women: A free bus travel scheme will be implemented for m... | **G.O.(Ms) No. 42 — Free Bus Fare Travel Scheme for Women in Town Buses** | **0.3794** | Tier 1 |
| `MF-AIADMK-2026:p22:55af8cd2287b` | Furthermore, free IVF treatment will be provided in hospitals under the Chief Minister's Comprehensi... | **G.O.(Ms) No. 280 — Chief Minister Comprehensive Health Insurance Scheme (CMCHIS) Renewal & Medical Coverage Expansion** | **0.3995** | Tier 1 |
| `MF-AIADMK-2026:p32:2b480d45f426` | Steps will be taken to implement the Coimbatore and Madurai Metro rail projects.... | **TN State Budget 2023-2024 — Sanction for Coimbatore & Madurai Metro Rail Phase 1** | **0.4373** | Tier 2 |

---

## 5. Summary of Promises Evaluated as `no_evidence_found`

Promises for which no candidate evidence was retrieved above the relevance threshold (0.15) are categorized strictly as `no_evidence_found`:

| Promise ID | Promise Excerpt | Domain Category | Status Evaluation |
| :--- | :--- | :--- | :--- |
| `MF-PMK-2016:p1:d0b3dfcfabd7` | In other words, the present allocation will be doubled... | Uncategorized | `no_evidence_found` |
| `MF-PMK-2016:p1:0fbd0757e3ad` | will prescribe fees for students studying in private schools and the fee will be paid by the Govt.... | Education | `no_evidence_found` |
| `MF-PMK-2016:p1:054273286e48` | schools will be raised and made on a par with Central Govt.... | Education | `no_evidence_found` |
| `MF-PMK-2016:p1:a089a5e10a74` | To ensure the school’s quality standards are maintained, a ‘Director of School Standards’ will be ap... | Education | `no_evidence_found` |
| `MF-PMK-2016:p1:d5251b06ff76` | A New Education Policy will be framed incorporating the salient features of the Central Board of Sch... | Education | `no_evidence_found` |
| `MF-PMK-2016:p1:266a1de17e04` | This policy will be implemented from the academic year 2017-18... | Uncategorized | `no_evidence_found` |
| `MF-PMK-2016:p1:a2247edf8efe` | Each student will be given a ‘tablet’ and through the concept of “e-bag”- an online platform, lesson... | Education | `no_evidence_found` |
| `MF-PMK-2016:p1:a59a3fb60515` | To make school travel hassle free for students, special ‘ STUDENT ONLY BUSSES’ will be introduced... | Education | `no_evidence_found` |
| `MF-PMK-2016:p1:2a8e42b9ffcf` | To enable students crack nationa l level entrance examinations with ease, s pecial coaching classes ... | Education | `no_evidence_found` |
| `MF-PMK-2016:p1:c72d36e2d49f` | Teachers currently working in Government schools on contractual basis or on a consolidated pay basis... | Education | `no_evidence_found` |

---

## 6. Analytical & Ethical Constraints

1. **Domain Whitelisting**: Candidate evidence is collected exclusively from official government websites (`.gov.in`, `.tn.gov.in`). Arbitrary third-party websites or blogs are blocked.
2. **Candidate Retrieval Only**: Linking a promise to evidence provides supporting documents for downstream assessment. It does **not** assert implementation status.
3. **Absence of Evidence Handling**: Absence of evidence indicates an evidence gap (`no_evidence_found`) and must **never** be interpreted as non-implementation.
