# Phase 2: Historical Scheme Intelligence Data Requirements

## 1. Overview and Scope
The goal of Phase 2 (Historical Scheme Intelligence) is to transition beyond purely quantitative budget analysis by building a structured, intelligent knowledge base of historical and active government schemes in Tamil Nadu. The scope involves defining the qualitative and contextual attributes of these schemes, allowing for cross-scheme comparison, historical tracing (how schemes evolve, merge, or change names over time), and aligning semantic information with the financial data gathered in Phase 1. 

## 2. Information Required for Each Scheme
To accurately profile a scheme and differentiate it from similar initiatives, the following attributes must be collected. 
**Note:** It is not assumed that every scheme will have all fields available in historical texts.

### Identification and Administration
*   **Scheme Name and Aliases:** The official name of the scheme, along with acronyms, localized names (Tamil variations), and previous names.
*   **Department and Implementing Agency:** The primary budget department (linking to Phase 1 `budget_departments`) and the specific agency or directorate responsible for execution.
*   **Official Scheme Description:** The narrative description of the scheme as stated in official government policy notes or budget speeches.

### Timeline and Scope
*   **Launch Year and Duration:** The year the scheme was inaugurated. If it was a temporary or closed scheme, the termination year (if documented).
*   **Implementation Area:** The geographic scope of the scheme (e.g., Statewide, specific districts, rural-only, urban-only).

### Objectives and Delivery
*   **Scheme Objectives:** The explicit goals and intended outcomes of the policy.
*   **Target Beneficiaries:** The specific demographic, socioeconomic, or occupational groups the scheme intends to serve (e.g., women, farmers, students, MSMEs).
*   **Eligibility Criteria:** The quantifiable or qualifying conditions required to access the scheme's benefits (e.g., income limits, age brackets, land-holding size).
*   **Benefits Provided:** The nature of the intervention (e.g., direct cash transfer, subsidy, infrastructural provision, training).

### Financials and Source Tracking
*   **Funding and Expenditure (When Available):** Historical financial markers (allocations vs. actuals), enabling a link to Phase 1's `budget_records` entities where applicable.
*   **Source Document and Publication Date:** Precise citations linking the scheme details to official policy notes, G.O.s (Government Orders), or budget publications.

## 3. Data Certainty: Verified Facts vs. Missing/Uncertain Information
Because historical government records can be fragmented or vague, the system must distinguish between verified facts and uncertain/missing information.
*   **Missing Data:** Null or explicitly marked "Unknown" fields must be preserved as such rather than imputed with assumptions. 
*   **Uncertain/Unverified Information:** Heuristic extractions (e.g., an NLP model extracting eligibility criteria from a dense paragraph) must be flagged with a confidence score or marked as "Unverified" until manually reviewed.
*   **Success Claims:** Descriptions of a scheme's "success" or "impact" derived purely from its own introductory text must be treated as administrative claims, not verified outcomes. The system will not assert that a scheme was successful based solely on its policy description.

## 4. Minimum Requirements for the Matching System
For a scheme to be registered and active within the NLP matching and comparison engine, it must meet the following minimum data thresholds:
1.  **Primary Scheme Name**
2.  **Department or Implementing Agency**
3.  **Source Document Reference** (proving its existence in the public record)

If a scheme lacks these three fundamental attributes, it cannot be reliably disambiguated from other similarly named initiatives and will be placed in a quarantine state for manual review.

## 5. Intended Matching and Comparison Use Cases
The structured scheme intelligence will power several advanced analytical use cases:
*   **Cross-Scheme Deduplication and Alias Resolution:** Identifying when two differently named budget entries actually refer to the same scheme (e.g., recognizing a scheme that was renamed by a subsequent administration).
*   **Beneficiary Overlap Analysis:** Comparing the "Target Beneficiaries" and "Eligibility Criteria" of multiple active schemes to identify overlapping safety nets or service gaps.
*   **Policy Evolution Tracking:** Analyzing how a scheme's stated objectives or benefit structures have mutated across different launch years or budget cycles.
*   **Financial-to-Semantic Mapping:** Correlating a scheme's textual intent (Phase 2) with its actual fiscal trajectory (Phase 1 financial variances) to provide contextual budget insights.
