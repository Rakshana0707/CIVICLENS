# Phase 3: Political Promise Tracker - Requirements

## Objective
The goal is to collect political manifesto promises and rigorously compare them against verifiable evidence of government action. 

## Architectural Scope
This phase defines a reusable acquisition architecture capable of obtaining manifesto documents from various sources:
- PDF URLs
- HTML pages
- Official party websites
- Public archives
- Permitted public datasets

This architecture is designed to be reusable for future modules like:
- Government evidence
- News collection
- Public policy documents

## Data Models
We are introducing two primary metadata models:
1. **Source Record**: Tracks the exact provenance, source tier, caching details, and retrieval status.
2. **Manifesto Model**: Represents the core manifesto document context and links back to the Source Record.

## Rules of Engagement
- Never bypass authentication, CAPTCHA, or paywalls.
- Respect `robots.txt` and polite request rates.
- No synthetic records.
- Strict adherence to the `manifesto_source_policy.md` hierarchy.
