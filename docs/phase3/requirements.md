# Phase 3: Political Promise Tracker - Requirements

## Objective
The objective of Phase 3 is to build the complete pipeline and infrastructure required to collect political manifesto promises, normalize and categorize them, and ultimately compare them against verifiable evidence of government action (from budgets, schemes, and official datasets).

## Important Current Status
At this stage, **actual manifesto documents have NOT yet been collected**. 
The system strictly enforces the following rules:
- Do NOT assume manifesto files currently exist in the environment.
- Do NOT fabricate or hallucinate manifesto data.
- Do NOT claim real manifesto coverage.
- Do NOT perform real promise analysis until actual documents are ingested.
- Temporary fixtures may only be used for testing pipeline mechanics and must be explicitly labeled as `test fixtures`.

## The Promise Pipeline
The system must be designed to eventually support the following end-to-end lifecycle:
1. **Acquire** manifesto documents.
2. **Store** raw documents securely without modification.
3. **Extract** manifesto text while preserving original language, section, and page boundaries.
4. **Extract** individual political promises from the raw text blocks.
5. **Normalize** promise information into standard terminology.
6. **Categorize** promises by sector/domain.
7. **Store** promises securely in the database.
8. **Match** promises with historical schemes extracted during Phase 2.
9. **Collect** implementation evidence from government sources.
10. **Match** promises with the collected evidence.
11. **Assess** implementation status rigorously.
12. **Expose** the final results and traceability through APIs.
13. **Display** the results interactively in the frontend dashboard.

## Source Principle and Hierarchy
When real documents are eventually collected, the system will adhere to a strict source tier hierarchy to ensure political neutrality and maximum reliability:
1. **Tier 1**: Official party source (e.g., official website, party release).
2. **Tier 2**: Official/public institutional source (e.g., Election Commission).
3. **Tier 3**: Reputable archive (e.g., OpenCity, TN234).
4. **Tier 4**: Reputable secondary source (news/research - used for discovery only).

The source tier must be explicitly recorded for every ingested manifesto document.
