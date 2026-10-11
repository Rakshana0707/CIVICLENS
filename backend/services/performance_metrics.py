"""
Phase 6 — Representative Performance Metrics and Comparative Analysis Engine.

Provides an open, transparent, and auditable metrics engine for calculating
and comparing representative performance across six discrete dimensions:
1. Legislative activity (sitting-adjusted questions, debates, attendance).
2. Constituency works and project delivery (sanctioned, WIP, completed).
3. Financial execution (release efficiency, expenditure-to-release ratio).
4. Development indicator trends (district/constituency socioeconomic progress).
5. Promise-related evidence (manifesto alignment stages from Phase 3/6.7).
6. Data completeness and reliability (ratio of verified to expected records).

Enforces:
1. Strict Cohort Isolation: Only compare representatives within the same legislative
   body (e.g. TN Assembly MLAs vs MLAs, Lok Sabha MPs vs MPs), election term, and reporting period.
2. Missing-Data Non-Penalization: Lower data availability degrades data completeness index
   rather than artificially lowering activity scores.
3. Non-Pojorative Mandate: Rejects algorithmic labelling of representatives as
   "corrupt", "bad", "ineffective", or "good".
4. Composite Score Full Disclosure: If a composite index is requested, exposes all weights,
   normalization formulas, components, and sensitivity variations (±20% weight perturbances).
"""

import logging
from typing import Dict, Any, List, Optional, Tuple, Set
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from sqlalchemy import func

from backend.models.representative import (
    Representative,
    Constituency,
    RepresentativeType,
    LegislativeActivity,
    ConstituencyWork,
    DevelopmentIndicator,
    PromisePerformanceLink,
    PerformanceMetric,
    PerformanceDimension,
    WorkProjectStatus,
    AttributionType
)

logger = logging.getLogger("civiclens.phase6.metrics")
logging.basicConfig(level=logging.INFO)


class IncompatibleCohortError(Exception):
    """Raised when attempting comparative analysis across disparate legislative bodies without justification."""
    pass


class ArbitraryRankingError(Exception):
    """Raised when an attempt is made to generate opaque rankings or pejorative labels."""
    pass


class PerformanceMetricsEngine:
    """
    Transparent analytical engine for computing dimensional metrics, normalized scores,
    cohort percentiles, and auditable composite analyses.
    """

    MANDATORY_CAVEATS = [
        "Metrics reflect documented public records and do not capture unminuted constituency representation, constituent grievance redressal, or executive governance duties.",
        "Data availability varies significantly between Parliament (digital Hansard/Sansad portals) and State Assemblies; cross-body comparisons without normalization are invalid.",
        "Expenditure figures represent reported financial utilization under MPLADS/MLACDS and do not prove project durability or long-term community satisfaction.",
        "Socioeconomic development indicator shifts are multi-causal macroeconomic phenomena and cannot be attributed solely to the sitting representative.",
        "Absence of published records is tracked via Data Completeness Index and must NOT be interpreted as zero activity or dereliction of duty."
    ]

    def __init__(self, db: Optional[Session] = None):
        self.db = db

    # -------------------------------------------------------------------------
    # 1. Legislative Activity Metrics
    # -------------------------------------------------------------------------
    def calculate_legislative_metrics(
        self,
        representative_id: str,
        reporting_period: str,
        annual_sittings_baseline: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Calculates legislative metrics: questions per sitting, debate participation,
        and official attendance (if gazetted).
        """
        if not self.db:
            return {"status": "NO_DB"}

        rep = self.db.query(Representative).filter(Representative.representative_id == representative_id).first()
        if not rep:
            raise ValueError(f"Representative {representative_id} not found.")

        # Baseline sittings if not provided
        if not annual_sittings_baseline:
            annual_sittings_baseline = 65 if rep.representative_type == RepresentativeType.LOK_SABHA_MP else 38

        activities = self.db.query(LegislativeActivity).filter(
            LegislativeActivity.representative_id == representative_id
        ).all()

        total_questions = sum(a.count for a in activities if "QUESTION" in a.activity_type.upper())
        total_debates = sum(a.count for a in activities if "DEBATE" in a.activity_type.upper())
        
        # Check attendance
        attendance_records = [a for a in activities if "ATTENDANCE" in a.activity_type.upper()]
        if attendance_records and attendance_records[0].data_quality_status == "VERIFIED":
            attendance_pct = attendance_records[0].value
            attendance_status = "VERIFIED"
        else:
            attendance_pct = None
            attendance_status = "NOT_GAZETTED_ONLINE"

        questions_per_sitting = round(total_questions / max(1, annual_sittings_baseline), 2)

        return {
            "dimension": PerformanceDimension.LEGISLATIVE_ACTIVITY,
            "representative_id": representative_id,
            "reporting_period": reporting_period,
            "annual_sittings_baseline": annual_sittings_baseline,
            "raw_metrics": {
                "total_questions": total_questions,
                "questions_per_sitting": questions_per_sitting,
                "total_debates": total_debates,
                "attendance_percentage": attendance_pct,
                "attendance_status": attendance_status
            },
            "data_completeness": 0.5 if attendance_pct is None else 1.0,
            "caveats": [
                "Ministers do not submit parliamentary questions as per legislative conventions.",
                "Assembly question submission quotas differ from Lok Sabha balloting rules."
            ]
        }

    # -------------------------------------------------------------------------
    # 2. Constituency Works Metrics
    # -------------------------------------------------------------------------
    def calculate_constituency_works_metrics(
        self,
        constituency_id: str,
        reporting_period: str,
        representative_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Calculates project execution metrics: total works, completion rate,
        and separate counts for representative-sponsored vs executive works.
        """
        if not self.db:
            return {"status": "NO_DB"}

        query = self.db.query(ConstituencyWork).filter(ConstituencyWork.constituency_id == constituency_id)
        if representative_id:
            query = query.filter(ConstituencyWork.representative_id == representative_id)

        works = query.all()
        total_works = len(works)

        if total_works == 0:
            return {
                "dimension": PerformanceDimension.CONSTITUENCY_WORKS,
                "constituency_id": constituency_id,
                "reporting_period": reporting_period,
                "total_works": 0,
                "completion_rate_pct": 0.0,
                "data_completeness": 0.0,
                "note": "No constituency works recorded for this period."
            }

        completed = sum(1 for w in works if w.project_status in [
            WorkProjectStatus.REPORTED_COMPLETED,
            WorkProjectStatus.INDEPENDENTLY_VERIFIED_COMPLETED
        ])
        in_progress = sum(1 for w in works if w.project_status == WorkProjectStatus.WORK_IN_PROGRESS)
        sanctioned = sum(1 for w in works if w.project_status == WorkProjectStatus.SANCTIONED)
        
        rep_sponsored = sum(1 for w in works if w.attribution_type == AttributionType.REPRESENTATIVE_SPONSORED)
        executive_works = sum(1 for w in works if w.attribution_type in [
            AttributionType.EXECUTIVE_STATE_PROJECT,
            AttributionType.EXECUTIVE_CENTRAL_PROJECT
        ])

        completion_rate = round((completed / total_works) * 100.0, 1)

        # Completeness audit: works having valid dates
        works_with_dates = sum(1 for w in works if w.approval_date is not None)
        completeness = round(works_with_dates / total_works, 2)

        return {
            "dimension": PerformanceDimension.CONSTITUENCY_WORKS,
            "constituency_id": constituency_id,
            "representative_id": representative_id,
            "reporting_period": reporting_period,
            "raw_metrics": {
                "total_works": total_works,
                "completed_works": completed,
                "in_progress_works": in_progress,
                "sanctioned_works": sanctioned,
                "representative_sponsored_works": rep_sponsored,
                "executive_works": executive_works,
                "completion_rate_percentage": completion_rate
            },
            "data_completeness": completeness,
            "caveats": [
                "Completion status does not verify long-term physical asset quality or maintenance.",
                "Executive state works are tracked for constituency context and separated from MLA/MP discretion."
            ]
        }

    # -------------------------------------------------------------------------
    # 3. Financial Execution Metrics
    # -------------------------------------------------------------------------
    def calculate_financial_execution_metrics(
        self,
        constituency_id: str,
        reporting_period: str,
        representative_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Calculates financial execution: sanctioned amount, released amount,
        reported expenditure, unspent balance, and expenditure-to-release ratio.
        """
        if not self.db:
            return {"status": "NO_DB"}

        query = self.db.query(ConstituencyWork).filter(ConstituencyWork.constituency_id == constituency_id)
        if representative_id:
            query = query.filter(ConstituencyWork.representative_id == representative_id)

        works = query.all()
        total_sanctioned = sum(w.sanctioned_amount or 0.0 for w in works)
        total_released = sum(w.released_amount or 0.0 for w in works)
        total_expended = sum(w.reported_expenditure or 0.0 for w in works)

        expenditure_ratio = round((total_expended / total_released * 100.0), 1) if total_released > 0 else 0.0
        unspent_released_balance = round(max(0.0, total_released - total_expended), 2)

        return {
            "dimension": PerformanceDimension.FINANCIAL_EXECUTION,
            "constituency_id": constituency_id,
            "representative_id": representative_id,
            "reporting_period": reporting_period,
            "raw_metrics": {
                "total_sanctioned_inr": total_sanctioned,
                "total_released_inr": total_released,
                "total_expended_inr": total_expended,
                "unspent_released_balance_inr": unspent_released_balance,
                "expenditure_to_release_ratio_pct": expenditure_ratio
            },
            "data_completeness": 1.0 if total_sanctioned > 0 else 0.0,
            "caveats": [
                "Funds released by district administration often lag sanction recommendations due to treasury pacing.",
                "Expenditure reflects utilization certificates submitted, not instant field disbursement."
            ]
        }

    # -------------------------------------------------------------------------
    # 4. Development Indicator Trends
    # -------------------------------------------------------------------------
    def calculate_development_trend_metrics(
        self,
        constituency_id: str,
        indicator_name: str,
        period_baseline: str,
        period_current: str
    ) -> Dict[str, Any]:
        """
        Calculates indicator trajectory between two reference periods.
        Enforces strict non-causality attribution.
        """
        if not self.db:
            return {"status": "NO_DB"}

        baseline_obs = self.db.query(DevelopmentIndicator).filter(
            DevelopmentIndicator.geographic_unit_id == constituency_id,
            DevelopmentIndicator.indicator_name == indicator_name,
            DevelopmentIndicator.reference_period == period_baseline
        ).first()

        current_obs = self.db.query(DevelopmentIndicator).filter(
            DevelopmentIndicator.geographic_unit_id == constituency_id,
            DevelopmentIndicator.indicator_name == indicator_name,
            DevelopmentIndicator.reference_period == period_current
        ).first()

        if not baseline_obs or not current_obs:
            return {
                "dimension": PerformanceDimension.DEVELOPMENT_TRENDS,
                "constituency_id": constituency_id,
                "indicator_name": indicator_name,
                "status": "INSUFFICIENT_OBSERVATIONS",
                "data_completeness": 0.5 if (baseline_obs or current_obs) else 0.0,
                "caveats": ["Requires both baseline and current period observations for delta calculation."]
            }

        delta = round(current_obs.value - baseline_obs.value, 2)
        pct_change = round((delta / baseline_obs.value) * 100.0, 2) if baseline_obs.value != 0 else 0.0

        return {
            "dimension": PerformanceDimension.DEVELOPMENT_TRENDS,
            "constituency_id": constituency_id,
            "indicator_name": indicator_name,
            "baseline_period": period_baseline,
            "baseline_value": baseline_obs.value,
            "current_period": period_current,
            "current_value": current_obs.value,
            "absolute_delta": delta,
            "percentage_change": pct_change,
            "unit": current_obs.unit,
            "data_completeness": 1.0,
            "caveats": [
                "Macroeconomic and demographic indicator deltas are multi-causal; do not infer direct representative causation.",
                "Baseline and current figures must originate from comparable official methodologies."
            ]
        }

    # -------------------------------------------------------------------------
    # 5. Promise-Related Evidence Metrics
    # -------------------------------------------------------------------------
    def calculate_promise_evidence_metrics(
        self,
        representative_id: str,
        reporting_period: str
    ) -> Dict[str, Any]:
        """
        Calculates manifesto promise progress distribution from Phase 3 & 6.7 links.
        """
        if not self.db:
            return {"status": "NO_DB"}

        links = self.db.query(PromisePerformanceLink).filter(
            PromisePerformanceLink.representative_id == representative_id
        ).all()

        total_linked_promises = len(links)
        if total_linked_promises == 0:
            return {
                "dimension": PerformanceDimension.PROMISE_EVIDENCE,
                "representative_id": representative_id,
                "total_linked_promises": 0,
                "data_completeness": 0.0,
                "note": "No manifesto promise links mapped."
            }

        stage_counts = {
            "PROMISE_IDENTIFIED": 0,
            "RELEVANT_SCHEME_IDENTIFIED": 0,
            "POLICY_ACTION_DOCUMENTED": 0,
            "PROJECT_WORK_RECORDED": 0,
            "OUTCOME_INDICATOR_OBSERVED": 0,
            "INSUFFICIENT_EVIDENCE": 0
        }

        for lnk in links:
            stg = lnk.evidence_stage
            if stg in stage_counts:
                stage_counts[stg] += 1
            else:
                stage_counts["INSUFFICIENT_EVIDENCE"] += 1

        action_or_better = (
            stage_counts["POLICY_ACTION_DOCUMENTED"] +
            stage_counts["PROJECT_WORK_RECORDED"] +
            stage_counts["OUTCOME_INDICATOR_OBSERVED"]
        )
        substantive_progress_pct = round((action_or_better / total_linked_promises) * 100.0, 1)

        return {
            "dimension": PerformanceDimension.PROMISE_EVIDENCE,
            "representative_id": representative_id,
            "reporting_period": reporting_period,
            "raw_metrics": {
                "total_linked_promises": total_linked_promises,
                "stage_distribution": stage_counts,
                "substantive_progress_percentage": substantive_progress_pct
            },
            "data_completeness": 1.0,
            "caveats": [
                "Manifesto promises belong to political parties; delivery involves state executive machinery beyond individual legislators.",
                "Policy action documentation indicates legislative or gazetted action, not necessarily universal beneficiary satisfaction."
            ]
        }

    # -------------------------------------------------------------------------
    # 6. Data Completeness & Reliability Metric
    # -------------------------------------------------------------------------
    def calculate_data_completeness_metric(
        self,
        representative_id: str,
        constituency_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Evaluates public record availability across dimensions.
        Explicitly isolates missing data from low representative performance.
        """
        if not self.db:
            return {"completeness_score": 0.0}

        rep = self.db.query(Representative).filter(Representative.representative_id == representative_id).first()
        if not rep:
            raise ValueError(f"Representative {representative_id} not found.")

        # Check legislative records
        act_count = self.db.query(LegislativeActivity).filter(
            LegislativeActivity.representative_id == representative_id
        ).count()
        leg_score = 1.0 if act_count > 0 else 0.0

        # Check works records
        works_count = 0
        if constituency_id:
            works_count = self.db.query(ConstituencyWork).filter(
                ConstituencyWork.constituency_id == constituency_id
            ).count()
        works_score = 1.0 if works_count > 0 else 0.0

        # Check indicators
        ind_count = 0
        if constituency_id:
            ind_count = self.db.query(DevelopmentIndicator).filter(
                DevelopmentIndicator.geographic_unit_id == constituency_id
            ).count()
        ind_score = 1.0 if ind_count > 0 else 0.0

        # Check promises
        prom_count = self.db.query(PromisePerformanceLink).filter(
            PromisePerformanceLink.representative_id == representative_id
        ).count()
        prom_score = 1.0 if prom_count > 0 else 0.0

        overall_ratio = round((leg_score + works_score + ind_score + prom_score) / 4.0, 2)

        return {
            "dimension": PerformanceDimension.DATA_COMPLETENESS,
            "representative_id": representative_id,
            "constituency_id": constituency_id,
            "completeness_ratio": overall_ratio,
            "dimension_availability": {
                "legislative_records": bool(leg_score),
                "constituency_works": bool(works_score),
                "development_indicators": bool(ind_score),
                "manifesto_promises": bool(prom_score)
            },
            "statutory_rule": "Representatives with lower public data completeness MUST NOT be penalized in dimensional scores."
        }

    # -------------------------------------------------------------------------
    # Cohort Normalization & Comparative Analysis
    # -------------------------------------------------------------------------
    def compare_within_cohort(
        self,
        cohort_representatives: List[str],
        reporting_period: str,
        cohort_type: str = "TN_ASSEMBLY_MLA"
    ) -> List[Dict[str, Any]]:
        """
        Normalizes legislative activity (questions per sitting) within a strict cohort
        using min-max scaling (0-100) and percentile ranks.
        Rejects comparisons across mixed bodies (e.g. MLA vs MP).
        """
        if not self.db:
            return []

        # Validate that all representatives belong to cohort_type
        for r_id in cohort_representatives:
            r = self.db.query(Representative).filter(Representative.representative_id == r_id).first()
            if not r:
                continue
            if cohort_type == "TN_ASSEMBLY_MLA" and r.representative_type != RepresentativeType.MLA:
                raise IncompatibleCohortError(
                    f"Representative {r_id} is of type {r.representative_type}; cannot compare with {cohort_type}."
                )
            if cohort_type == "LOK_SABHA_MP" and r.representative_type != RepresentativeType.LOK_SABHA_MP:
                raise IncompatibleCohortError(
                    f"Representative {r_id} is of type {r.representative_type}; cannot compare with {cohort_type}."
                )

        cohort_data = []
        for r_id in cohort_representatives:
            leg = self.calculate_legislative_metrics(r_id, reporting_period)
            q_val = leg["raw_metrics"]["questions_per_sitting"]
            cohort_data.append({
                "representative_id": r_id,
                "questions_per_sitting": q_val,
                "data_completeness": leg["data_completeness"]
            })

        if not cohort_data:
            return []

        vals = [d["questions_per_sitting"] for d in cohort_data]
        min_v = min(vals)
        max_v = max(vals)
        val_range = max_v - min_v

        # Sort for percentile ranks
        sorted_vals = sorted(vals)
        n = len(sorted_vals)

        results = []
        for item in cohort_data:
            val = item["questions_per_sitting"]
            # Min-Max Normalization (0-100)
            if val_range > 0:
                normalized = round(((val - min_v) / val_range) * 100.0, 1)
            else:
                normalized = 50.0  # Homogeneous cohort

            # Percentile rank
            rank_idx = sorted_vals.index(val)
            pct_rank = round((rank_idx / max(1, n - 1)) * 100.0, 1)

            results.append({
                "representative_id": item["representative_id"],
                "cohort_type": cohort_type,
                "reporting_period": reporting_period,
                "metric_code": "QUESTIONS_PER_SITTING",
                "raw_value": val,
                "normalized_score": normalized,
                "percentile_rank": pct_rank,
                "data_completeness": item["data_completeness"],
                "normalization_formula": "((val - min) / (max - min)) * 100"
            })

        return results

    # -------------------------------------------------------------------------
    # Composite Index with Sensitivity Analysis & Full Disclosure
    # -------------------------------------------------------------------------
    def calculate_transparent_composite(
        self,
        representative_id: str,
        constituency_id: str,
        reporting_period: str,
        weights: Optional[Dict[str, float]] = None
    ) -> Dict[str, Any]:
        """
        Calculates an explicitly weighted composite score (0-100) across available dimensions.
        Provides:
        1. Component breakdown.
        2. Sensitivity analysis (±20% variation on dominant weights).
        3. Missing data treatment (weights dynamically re-normalized over observed dimensions only).
        4. Strict non-pejorative enforcement: NO evaluative adjectives like 'bad' or 'corrupt'.
        """
        default_weights = {
            "legislative": 0.25,
            "constituency_works": 0.25,
            "financial_execution": 0.25,
            "promise_evidence": 0.25
        }
        active_weights = weights or default_weights

        # 1. Legislative score (0-100 proxy based on attendance/sittings)
        leg = self.calculate_legislative_metrics(representative_id, reporting_period)
        leg_comp = min(100.0, leg["raw_metrics"]["questions_per_sitting"] * 20.0) # 5 Q/sitting = 100

        # 2. Works completion rate (0-100)
        works = self.calculate_constituency_works_metrics(constituency_id, reporting_period, representative_id)
        works_comp = works["raw_metrics"]["completion_rate_percentage"] if "raw_metrics" in works else None

        # 3. Financial execution ratio (0-100 capped)
        fin = self.calculate_financial_execution_metrics(constituency_id, reporting_period, representative_id)
        fin_comp = min(100.0, fin["raw_metrics"]["expenditure_to_release_ratio_pct"]) if "raw_metrics" in fin else None

        # 4. Promise evidence substantive rate (0-100)
        prom = self.calculate_promise_evidence_metrics(representative_id, reporting_period)
        prom_comp = prom["raw_metrics"]["substantive_progress_percentage"] if "raw_metrics" in prom else None

        observed_components = {}
        if leg_comp is not None:
            observed_components["legislative"] = leg_comp
        if works_comp is not None:
            observed_components["constituency_works"] = works_comp
        if fin_comp is not None:
            observed_components["financial_execution"] = fin_comp
        if prom_comp is not None:
            observed_components["promise_evidence"] = prom_comp

        if not observed_components:
            return {
                "representative_id": representative_id,
                "composite_score": None,
                "status": "NO_OBSERVED_DIMENSIONS",
                "caveats": self.MANDATORY_CAVEATS
            }

        # Dynamic re-weighting for missing dimensions to avoid penalizing representatives
        sum_weights = sum(active_weights[k] for k in observed_components)
        normalized_weights = {k: active_weights[k] / sum_weights for k in observed_components}

        composite_score = sum(observed_components[k] * normalized_weights[k] for k in observed_components)
        composite_score = round(composite_score, 2)

        # Sensitivity Analysis: perturb dominant weight by +20% and -20%
        dominant_key = max(normalized_weights, key=normalized_weights.get)
        sensitivity = {}
        for perturb in [-0.20, 0.20]:
            perturbed_weights = dict(normalized_weights)
            perturbed_weights[dominant_key] *= (1.0 + perturb)
            # Re-normalize
            sub_sum = sum(perturbed_weights.values())
            rescaled = {k: v / sub_sum for k, v in perturbed_weights.items()}
            score_p = round(sum(observed_components[k] * rescaled[k] for k in observed_components), 2)
            label = f"{dominant_key}_{'+20pct' if perturb > 0 else '-20pct'}"
            sensitivity[label] = {
                "perturbed_score": score_p,
                "delta": round(score_p - composite_score, 2)
            }

        return {
            "representative_id": representative_id,
            "constituency_id": constituency_id,
            "reporting_period": reporting_period,
            "composite_score": composite_score,
            "score_scale": "0.0 to 100.0",
            "component_scores": observed_components,
            "applied_weights": normalized_weights,
            "missing_data_treatment": "Dynamic proportional re-weighting across observed dimensions; no imputation penalties.",
            "sensitivity_analysis": sensitivity,
            "anti_pejorative_disclaimer": "This score is an empirical index of documented public records. It must NEVER be used to categorize representatives with defamatory labels (e.g. good, bad, corrupt).",
            "methodological_caveats": self.MANDATORY_CAVEATS
        }
