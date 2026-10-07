"""
CIVICLENS TN — Phase 3.23 Real Promise Status Assessment Pipeline

Executes the transparent, evidence-based assessment engine across all real political promises stored in civiclens.db.

Supported Status Taxonomy:
- `not_assessed`: Promise has not been evaluated against evidence sources.
- `no_evidence_found`: Zero verifiable government evidence was found. (CRITICAL: Absence of evidence != Not Implemented).
- `announced`: Verified government announcement/press release, but formal GO or budget is pending.
- `policy_action`: Official Government Order (G.O.) or policy framework issued.
- `partially_implemented`: Initial budget allocation or Phase 1 rollout verified.
- `implemented`: Full government order fulfillment, budget execution, or operational delivery verified.
- `unclear`: Matched evidence is vague or low confidence, preventing definitive classification.
- `disputed`: Conflicting official reports or disputed implementation claims.

CRITICAL ETHICAL BOUNDARIES:
- NO EVIDENCE FOUND != NOT IMPLEMENTED.
- The system MUST NEVER automatically accuse any political party, politician, or government of wrongdoing or failure.
- ML retrieves and ranks evidence; it does NOT independently make political verdicts.
"""

import os
import sys
import json
import logging
from datetime import datetime, timezone
from collections import Counter, defaultdict

# UTF-8 encoding fix for Windows console
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("Phase3PromiseAssessment")

# DB Imports
import backend.database.base as db_base
from backend.database.session import SessionLocal, engine
from backend.models.promise import (
    PoliticalPromise,
    PromiseAssessment,
    PromiseAssessmentHistory,
    PromiseEvidenceLink,
    PromiseStatus
)
from backend.services.promise_assessment_engine import PromiseAssessmentEngine, METHODOLOGY_ID


ASSESSMENT_METHODOLOGY_NAME = "transparent_rule_based_evidence_assessment_v1"


def run_real_promise_assessment():
    """Main execution pipeline for Phase 3.23 Real Promise Status Assessment."""
    logger.info("=" * 70)
    logger.info("CIVICLENS TN — Phase 3.23 Real Promise Status Assessment Pipeline")
    logger.info("=" * 70)

    output_assessments_file = "data/processed/assessments/real_promise_assessments.json"
    output_summary_file = "data/processed/assessments/assessment_summary.json"
    report_file = "docs/phase3/assessment_report.md"

    # Ensure tables exist and open DB session
    db_base.Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    try:
        engine_service = PromiseAssessmentEngine(db_session=db)

        # Retrieve all non-fixture real promises from civiclens.db
        promises = db.query(PoliticalPromise).filter(
            PoliticalPromise.is_test_fixture == False
        ).all()

        logger.info(f"Retrieved {len(promises)} real political promises from database for status evaluation.")

        if not promises:
            logger.error("No real promises found in database to evaluate.")
            return

        all_assessments = []
        status_distribution = Counter()
        party_status_distribution = defaultdict(Counter)
        election_status_distribution = defaultdict(Counter)
        category_status_distribution = defaultdict(Counter)
        language_status_distribution = defaultdict(Counter)

        samples_by_status = defaultdict(list)

        for promise in promises:
            # Execute rule-based evidence evaluation
            eval_result = engine_service.evaluate_promise(
                promise=promise,
                persist=True,
                evaluator_id=ASSESSMENT_METHODOLOGY_NAME
            )

            status_str = eval_result["status"]
            conf_score = eval_result["confidence"]
            explanation = eval_result["explanation"]
            evidence_ids = eval_result["evidence_ids"]
            tiers_map = eval_result.get("source_tiers", {})
            
            # Format source_tiers as list of unique integer tier levels e.g. [1, 2]
            source_tiers_list = sorted([int(t) for t in tiers_map.keys()]) if isinstance(tiers_map, dict) else []

            # Format assessment record containing all required 8 fields
            assessment_record = {
                "promise_id": promise.promise_id,
                "status": status_str,
                "confidence": round(float(conf_score), 4),
                "explanation": explanation,
                "evidence_ids": evidence_ids,
                "source_tiers": source_tiers_list,
                "assessment_date": eval_result["assessment_date"],
                "methodology": ASSESSMENT_METHODOLOGY_NAME,
                "party": promise.manifesto.party if promise.manifesto else "Unknown",
                "election_year": str(promise.manifesto.election_year) if promise.manifesto else "Unknown",
                "category": promise.metadata_json.get("category", "Uncategorized") if promise.metadata_json else "Uncategorized",
                "language": promise.language or "Unknown"
            }
            all_assessments.append(assessment_record)

            status_distribution[status_str] += 1
            party_status_distribution[assessment_record["party"]][status_str] += 1
            election_status_distribution[assessment_record["election_year"]][status_str] += 1
            category_status_distribution[assessment_record["category"]][status_str] += 1
            language_status_distribution[assessment_record["language"]][status_str] += 1

            if len(samples_by_status[status_str]) < 5:
                samples_by_status[status_str].append({
                    "promise_id": promise.promise_id,
                    "promise_text": (promise.normalized_text or promise.original_text)[:100],
                    "status": status_str,
                    "confidence": round(float(conf_score), 4),
                    "explanation": explanation
                })

        db.commit()
        logger.info(f"Persisted {len(all_assessments)} PromiseAssessment records to SQLite database (civiclens.db).")

        # ---------------------------------------------------------------------
        # STEP 2: Save Deliverables & Metrics
        # ---------------------------------------------------------------------
        os.makedirs(os.path.dirname(output_assessments_file), exist_ok=True)
        with open(output_assessments_file, "w", encoding="utf-8") as f:
            json.dump(all_assessments, f, indent=2, ensure_ascii=False)

        summary_data = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "total_promises_assessed": len(all_assessments),
            "methodology": ASSESSMENT_METHODOLOGY_NAME,
            "status_distribution": dict(status_distribution),
            "by_party": {p: dict(counts) for p, counts in party_status_distribution.items()},
            "by_election_year": {y: dict(counts) for y, counts in election_status_distribution.items()},
            "by_category": {c: dict(counts) for c, counts in category_status_distribution.items()},
            "by_language": {l: dict(counts) for l, counts in language_status_distribution.items()}
        }

        with open(output_summary_file, "w", encoding="utf-8") as f:
            json.dump(summary_data, f, indent=2, ensure_ascii=False)

        logger.info(f"Saved assessment records to {output_assessments_file}")
        logger.info(f"Saved summary metrics to {output_summary_file}")

        # ---------------------------------------------------------------------
        # STEP 3: Generate Markdown Report docs/phase3/assessment_report.md
        # ---------------------------------------------------------------------
        generate_assessment_report(
            filepath=report_file,
            summary=summary_data,
            samples=samples_by_status
        )
        logger.info(f"Generated assessment report at {report_file}")

        logger.info("\n--- PROMISE ASSESSMENT SUMMARY METRICS ---")
        logger.info(f"Total Promises Evaluated: {len(all_assessments)}")
        for st_name, st_count in status_distribution.most_common():
            pct = (st_count / len(all_assessments)) * 100
            logger.info(f"  {st_name:<25}: {st_count} ({pct:.1f}%)")
        logger.info("=" * 70)

    except Exception as e:
        db.rollback()
        logger.error(f"ERROR DURING PROMISE ASSESSMENT PIPELINE: {e}", exc_info=True)
        raise e
    finally:
        db.close()


def generate_assessment_report(filepath: str, summary: dict, samples: dict):
    """Generates docs/phase3/assessment_report.md."""
    os.makedirs(os.path.dirname(filepath), exist_ok=True)

    tot = summary["total_promises_assessed"]
    st_dist = summary["status_distribution"]

    report_content = f"""# CIVICLENS TN — Phase 3.23
## Real Promise Status Assessment Report

> **CRITICAL ETHICAL SAFEGUARD: NO EVIDENCE FOUND $\\neq$ NOT IMPLEMENTED**
> The assessment engine operates under strict non-adversarial principles:
> **1. Absence of evidence strictly evaluates to `no_evidence_found` (NEVER `not_implemented`).**
> **2. The system NEVER automatically accuses any political party, politician, or government of wrongdoing or default failure.**
> **3. Machine learning performs candidate evidence retrieval only; status decisions follow transparent, auditable rule engine logic.**

---

## 1. Overview & Assessment Execution Summary

- **Execution Date**: `{summary['timestamp']}`
- **Total Real Promises Evaluated**: `{tot}`
- **Assessment Methodology**: `{summary['methodology']}`
- **Database Table**: `promise_assessments` in `civiclens.db`

### Allowed Status Taxonomy & Distribution

| Promise Status | Assessment Count | Percentage | Definition & Rule Engine Triggers |
| :--- | :---: | :---: | :--- |
| **`no_evidence_found`** | **{st_dist.get('no_evidence_found', 0)}** | **{st_dist.get('no_evidence_found', 0)/tot*100:.1f}%** | Zero verifiable government evidence retrieved for this promise. (*Absence of evidence != Not Implemented*). |
| **`unclear`** | **{st_dist.get('unclear', 0)}** | **{st_dist.get('unclear', 0)/tot*100:.1f}%** | Retained evidence candidate scores are below threshold, or promise wording is ambiguous without linked evidence. |
| **`partially_implemented`** | **{st_dist.get('partially_implemented', 0)}** | **{st_dist.get('partially_implemented', 0)/tot*100:.1f}%** | Verified budget allocation or partial rollout established, but ongoing targets remain. |
| **`policy_action`** | **{st_dist.get('policy_action', 0)}** | **{st_dist.get('policy_action', 0)/tot*100:.1f}%** | Official Government Order (G.O.) or policy note issued sanctioning framework. |
| **`implemented`** | **{st_dist.get('implemented', 0)}** | **{st_dist.get('implemented', 0)/tot*100:.1f}%** | Full G.O. fulfillment and budget execution verified. |
| **`announced`** | **{st_dist.get('announced', 0)}** | **{st_dist.get('announced', 0)/tot*100:.1f}%** | Official press release or speech announcement verified, but formal GO is pending. |
| **`disputed`** | **{st_dist.get('disputed', 0)}** | **{st_dist.get('disputed', 0)/tot*100:.1f}%** | Conflicting official reports or disputed implementation claims. |
| **`not_assessed`** | **{st_dist.get('not_assessed', 0)}** | **{st_dist.get('not_assessed', 0)/tot*100:.1f}%** | Promise pending evidence evaluation. |
| **TOTAL** | **{tot}** | **100.0%** | Comprehensive evaluation of Phase 3 real promise dataset. |

---

## 2. Assessment Breakdown by Political Party

| Political Party | Evaluated Promises | `no_evidence_found` | `unclear` | `partially_implemented` / `implemented` |
| :--- | :---: | :---: | :---: | :---: |
"""
    for party, counts in sorted(summary["by_party"].items(), key=lambda x: sum(x[1].values()), reverse=True):
        party_total = sum(counts.values())
        ne_cnt = counts.get("no_evidence_found", 0)
        un_cnt = counts.get("unclear", 0)
        imp_cnt = counts.get("partially_implemented", 0) + counts.get("implemented", 0) + counts.get("policy_action", 0)
        report_content += f"| {party} | {party_total} | {ne_cnt} | {un_cnt} | {imp_cnt} |\n"

    report_content += """
---

## 3. Assessment Breakdown by Election Year

| Election Year | Total Promises | `no_evidence_found` | `unclear` | Implementation / Policy Actions |
| :--- | :---: | :---: | :---: | :---: |
"""
    for year_val, counts in sorted(summary["by_election_year"].items(), key=lambda x: x[0]):
        yr_total = sum(counts.values())
        ne_cnt = counts.get("no_evidence_found", 0)
        un_cnt = counts.get("unclear", 0)
        imp_cnt = counts.get("partially_implemented", 0) + counts.get("implemented", 0) + counts.get("policy_action", 0)
        report_content += f"| {year_val} | {yr_total} | {ne_cnt} | {un_cnt} | {imp_cnt} |\n"

    report_content += """
---

## 4. Sample Transparent Assessments

### Sample `no_evidence_found` Records

> [!NOTE]
> Every `no_evidence_found` assessment includes an explicit statement clarifying that absence of evidence is not proof of non-implementation.

| Promise ID | Promise Excerpt | Status | Confidence | Transparent Rationale |
| :--- | :--- | :---: | :---: | :--- |
"""
    for s in samples.get("no_evidence_found", []):
        report_content += f"| `{s['promise_id']}` | {s['promise_text']}... | `{s['status']}` | {s['confidence']:.2f} | {s['explanation']} |\n"

    report_content += """
### Sample Implementation & Policy Action Records

| Promise ID | Promise Excerpt | Status | Confidence | Transparent Rationale |
| :--- | :--- | :---: | :---: | :--- |
"""
    imp_samples = samples.get("partially_implemented", []) + samples.get("implemented", []) + samples.get("policy_action", []) + samples.get("announced", [])
    if imp_samples:
        for s in imp_samples:
            report_content += f"| `{s['promise_id']}` | {s['promise_text']}... | `{s['status']}` | {s['confidence']:.2f} | {s['explanation']} |\n"
    else:
        report_content += "| — | No implementation samples in current batch | — | — | — |\n"

    report_content += """
---

## 5. Non-Adversarial Safeguards & Methodology Rules

1. **Strict Non-Adversarial Stance**: CivicLens TN evaluates evidence, not political intent. The system does not classify promises as "failed" or "broken".
2. **Conflicting Evidence Protocol**: When evidence sources provide conflicting figures or claims, the status resolves to `disputed`.
3. **Audit Provenance**: All assessment records contain `promise_id`, `status`, `confidence`, `explanation`, `evidence_ids`, `source_tiers`, `assessment_date`, and `methodology`.
"""

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(report_content)


if __name__ == "__main__":
    run_real_promise_assessment()
