# Phase 3.1: Political Promise Tracker Requirements

## Objective
The Political Promise Tracker aims to collect political manifesto promises and rigorously compare them against verifiable evidence from authoritative sources, including government documents, budget records, official webpages, and other permitted data sources.

## Core Conceptual Flow (Promise Lifecycle)

1. **Manifesto Document**: Raw manifesto file or webpage containing political statements.
2. **Promise**: Extracted, verbatim commitment from the manifesto document.
3. **Normalized Promise**: Standardized and categorized version of the raw promise for easier searching.
4. **Evidence Search**: Querying the system's databases (budget, historical schemes) and external sources.
5. **Evidence Records**: The raw snippets, dataset rows, or URLs providing proof regarding the promise.
6. **Matching**: Establishing the linkage between a Normalized Promise and Evidence Records.
7. **Status Assessment**: Categorizing the fulfillment status of the promise (e.g., announced, implemented).
8. **Confidence Scoring**: Assigning a confidence level to the assessment based on source tier and matching quality.
9. **User-facing Explanation**: Generating a human-readable justification distinguishing evidence from interpretation.

*Important Note*: These stages must remain separate and distinct in the architecture to maintain end-to-end traceability from manifesto to final assessment.

## Promise Status Taxonomy

Every promise is assigned a status. The strict taxonomy is as follows:

* `not_assessed`: The promise has not yet been processed or analyzed.
* `no_evidence_found`: A search was conducted, but no relevant documentation was found. (Note: Absence of evidence is not proof of non-implementation).
* `announced`: The government has publicly announced intent or preliminary planning, but no concrete action is visible.
* `policy_action`: Initial bureaucratic or legislative steps have been taken (e.g., scheme approved, budget allocated) but ground implementation is unverified.
* `partially_implemented`: Evidence shows the promise is fulfilled in part, but not fully meeting the original commitment.
* `implemented`: Substantial, conclusive evidence demonstrates the promise has been fully met as defined.
* `unclear`: Evidence is contradictory, ambiguous, or insufficient to make a definitive assessment.
* `disputed`: Conflicting evidence exists from different authoritative sources.

## Political Neutrality Rules

The system must operate with strict political neutrality. 
* Do not favor any political party.
* Avoid emotionally loaded descriptions.
* Do not infer political intent behind any action or lack thereof.
* Never label politicians or parties as dishonest.
* Distinguish allegations from facts.
* Do not present model predictions as factual accusations.
* Maintain a clear boundary: **source evidence → model interpretation → human/user conclusion**.

## Architecture & Reusability
* **Phase 1 & 2 Integration**: The Promise Tracker must seamlessly integrate with the existing DB schema (`models/common.py`, `models/budget.py`), Document models, and the provenance framework. 
* **Do Not Rebuild**: Utilize existing PDF parsers, DB ingestion pipelines, and ML matching patterns where applicable.
