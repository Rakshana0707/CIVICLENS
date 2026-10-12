"""
CIVICLENS TN — Civic Issue Analytics and Trend Detection Engine (Phase 8.7)
===========================================================================
Computes validated statistical metrics, temporal trends, and empirical indicators
from public grievance records and civic issue intelligence data.

Adheres strictly to the following core principles:
1. COMPLAINTS != PREVALENCE: Recorded complaint volume reflects reporting propensity,
   portal accessibility, civic literacy, and digital infrastructure; it does NOT equate
   to the true prevalence or severity of physical civic problems.
2. NO UNCONTEXTUALIZED AREA COMPARISONS: Direct comparisons between administrative areas
   without explaining population disparities, digital coverage gaps, and reporting channels
   are methodologically invalid.
3. SMALL SAMPLE GUARDS: Statistical anomaly detection is strictly guarded by minimum
   sample size thresholds (N >= 30, baseline periods >= 3).
4. EXPLORATORY LABELS: Unusual statistical patterns are labeled as
   "INVESTIGATION_INDICATOR_UNUSUAL_VOLUME", never as proof of negligence or misconduct.
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Union

from sqlalchemy.orm import Session

from backend.models.civic_issue import (
    AdministrativeArea,
    CivicDepartment,
    CivicIssue,
    CivicIssueStatus,
    CivicTrackingState,
    GrievanceRecord,
    IssueCategoryEnum,
    IssueMetric,
    ResolutionVerificationStatus,
    ResponseRecord,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Methodological Constants & Mandatory Disclaimers
# ---------------------------------------------------------------------------

GENERAL_ANALYTICS_DISCLAIMER: str = (
    "COMPLAINTS DO NOT EQUAL PREVALENCE: Recorded grievance volume reflects citizen reporting "
    "propensity, mobile helpline access, civic awareness, and administrative portal availability. "
    "It does NOT measure the true physical prevalence or failure rate of civic infrastructure. "
    "Areas or categories with high complaint counts frequently reflect high civic engagement "
    "and accessible digital reporting rather than worse public administration."
)

AREA_COMPARISON_CAVEAT: str = (
    "POPULATION & ACCESS DISPARITY: Direct comparisons between administrative areas without "
    "adjusting for population size, smartphone adoption, and reporting portal accessibility "
    "are methodologically invalid. Urban municipal corporations with dedicated helplines (e.g. GCC 1913) "
    "naturally report higher volumes per capita than rural panchayat unions relying on physical petitions."
)

ANOMALY_INVESTIGATION_NOTICE: str = (
    "EXPLORATORY INDICATOR: Unusual statistical patterns are flagged as indicators requiring "
    "administrative field investigation. They do NOT constitute proof of negligence, malfeasance, "
    "or misconduct. External phenomena such as monsoon downpours, public awareness campaigns, "
    "ward reorganizations, or batch data synchronization routinely produce volume spikes."
)

MIN_ANOMALY_SAMPLE_SIZE: int = 30
MIN_ANOMALY_BASELINE_PERIODS: int = 3


# ---------------------------------------------------------------------------
# Data Structures
# ---------------------------------------------------------------------------

@dataclass
class MetricResult:
    """Standardized metric calculation result with reporting period and source."""
    metric_code: str
    metric_name: str
    period: str
    data_source: str
    sample_size: int
    metric_value: float
    unit: str
    distribution: Dict[str, Any] = field(default_factory=dict)
    caveats: str = ""
    extra_metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AnomalyItem:
    """Individual detected statistical anomaly."""
    period: str
    observed_count: int
    expected_mean: float
    z_score: float
    indicator_label: str
    interpretation_note: str


@dataclass
class AnomalyDetectionResult:
    """Result of statistical volume anomaly detection."""
    status: str  # "SUFFICIENT_DATA" or "INSUFFICIENT_DATA"
    sample_size: int
    baseline_periods_count: int
    anomalies: List[AnomalyItem] = field(default_factory=list)
    interpretative_notice: str = ANOMALY_INVESTIGATION_NOTICE
    reason: Optional[str] = None


@dataclass
class AreaComparisonResult:
    """Standardized comparative result between two administrative areas."""
    area_a_code: str
    area_a_name: str
    area_a_count: int
    area_a_population: Optional[int]
    area_a_rate_per_100k: Optional[float]
    area_b_code: str
    area_b_name: str
    area_b_count: int
    area_b_population: Optional[int]
    area_b_rate_per_100k: Optional[float]
    per_capita_ratio: Optional[float]
    comparison_valid: bool
    required_context: str
    interpretative_caveat: str = AREA_COMPARISON_CAVEAT


@dataclass
class CivicAnalyticsReport:
    """Consolidated analytics report across all 10 core civic metrics."""
    reporting_period: str
    data_source: str
    total_records: int
    metrics: Dict[str, MetricResult] = field(default_factory=dict)
    anomaly_detection: Optional[AnomalyDetectionResult] = None
    general_disclaimer: str = GENERAL_ANALYTICS_DISCLAIMER


# ---------------------------------------------------------------------------
# Civic Analytics Engine
# ---------------------------------------------------------------------------

class CivicAnalyticsEngine:
    """
    Analytics and trend detection engine for validated civic issue records.
    Computes 10 core civic metrics with strict methodological safety guards.
    """

    def __init__(self, default_source: str = "VALIDATED_CIVIC_RECORDS"):
        self.default_source = default_source

    # -----------------------------------------------------------------------
    # Helper: Record Normalization
    # -----------------------------------------------------------------------
    @staticmethod
    def _extract_date(record: Any, field_name: str) -> Optional[datetime]:
        """Extract datetime from ORM entity, dict, or object."""
        val = None
        if isinstance(record, dict):
            val = record.get(field_name)
        else:
            val = getattr(record, field_name, None)

        if isinstance(val, datetime):
            return val
        if isinstance(val, str):
            try:
                return datetime.fromisoformat(val.replace("Z", "+00:00"))
            except Exception:
                return None
        return None

    @staticmethod
    def _extract_attr(record: Any, field_name: str, default: Any = None) -> Any:
        """Extract generic attribute from ORM entity or dict."""
        if isinstance(record, dict):
            return record.get(field_name, default)
        return getattr(record, field_name, default)

    # -----------------------------------------------------------------------
    # 1. Issue Counts by Category
    # -----------------------------------------------------------------------
    def calculate_category_counts(
        self,
        records: List[Any],
        period: str = "ALL_TIME",
        data_source: Optional[str] = None,
    ) -> MetricResult:
        """
        Metric 1: Issue counts aggregated per canonical infrastructure category.
        """
        source = data_source or self.default_source
        n = len(records)
        counts: Dict[str, int] = {}

        for rec in records:
            cat = self._extract_attr(rec, "issue_category") or self._extract_attr(rec, "category")
            if hasattr(cat, "value"):
                cat_str = cat.value
            elif hasattr(cat, "name_en"):
                cat_str = cat.name_en
            elif isinstance(cat, str):
                cat_str = cat.lower()
            else:
                cat_str = "uncategorized"

            counts[cat_str] = counts.get(cat_str, 0) + 1

        percentages = {k: round((v / n) * 100, 2) if n > 0 else 0.0 for k, v in counts.items()}

        return MetricResult(
            metric_code="ISSUE_COUNT_BY_CATEGORY",
            metric_name="Issue Counts by Category",
            period=period,
            data_source=source,
            sample_size=n,
            metric_value=float(n),
            unit="COUNT",
            distribution={"counts": counts, "percentages": percentages},
            caveats=(
                "Category counts reflect citizen reporting propensity and visibility. Visible issues "
                "(e.g., streetlights, waste collection) generate higher complaint volumes than "
                "subterranean issues (e.g., storm drainage) irrespective of true defect rates."
            ),
        )

    # -----------------------------------------------------------------------
    # 2. Issue Counts by Administrative Area
    # -----------------------------------------------------------------------
    def calculate_area_counts(
        self,
        records: List[Any],
        period: str = "ALL_TIME",
        data_source: Optional[str] = None,
        population_map: Optional[Dict[str, int]] = None,
    ) -> MetricResult:
        """
        Metric 2: Issue counts aggregated per administrative area with population context.
        """
        source = data_source or self.default_source
        pop_map = population_map or {}
        n = len(records)
        counts: Dict[str, int] = {}

        for rec in records:
            area = self._extract_attr(rec, "administrative_area_id") or self._extract_attr(rec, "administrative_area")
            if hasattr(area, "area_code"):
                area_str = area.area_code
            elif isinstance(area, str):
                area_str = area
            elif isinstance(area, int):
                area_str = f"AREA-{area}"
            else:
                area_str = "UNKNOWN_AREA"

            counts[area_str] = counts.get(area_str, 0) + 1

        # Calculate per-capita rates where population is known
        per_100k: Dict[str, Optional[float]] = {}
        for area_code, count in counts.items():
            pop = pop_map.get(area_code)
            if pop and pop > 0:
                per_100k[area_code] = round((count / pop) * 100_000, 2)
            else:
                per_100k[area_code] = None

        return MetricResult(
            metric_code="ISSUE_COUNT_BY_AREA",
            metric_name="Issue Counts by Administrative Area",
            period=period,
            data_source=source,
            sample_size=n,
            metric_value=float(len(counts)),
            unit="AREAS_COUNTED",
            distribution={"counts": counts, "rate_per_100k_population": per_100k},
            caveats=AREA_COMPARISON_CAVEAT,
        )

    # -----------------------------------------------------------------------
    # 3. Issue Counts by Department
    # -----------------------------------------------------------------------
    def calculate_department_counts(
        self,
        records: List[Any],
        period: str = "ALL_TIME",
        data_source: Optional[str] = None,
    ) -> MetricResult:
        """
        Metric 3: Issue counts routed to departments and local authorities.
        """
        source = data_source or self.default_source
        n = len(records)
        counts: Dict[str, int] = {}
        unassigned_count = 0

        for rec in records:
            dept = self._extract_attr(rec, "department_id") or self._extract_attr(rec, "department")
            if hasattr(dept, "code"):
                dept_str = dept.code
            elif isinstance(dept, str) and dept.strip():
                dept_str = dept.strip()
            elif isinstance(dept, int):
                dept_str = f"DEPT-{dept}"
            else:
                dept_str = "UNASSIGNED"
                unassigned_count += 1

            counts[dept_str] = counts.get(dept_str, 0) + 1

        return MetricResult(
            metric_code="ISSUE_COUNT_BY_DEPARTMENT",
            metric_name="Issue Counts by Department",
            period=period,
            data_source=source,
            sample_size=n,
            metric_value=float(len(counts)),
            unit="DEPARTMENTS_COUNTED",
            distribution={
                "counts": counts,
                "unassigned_count": unassigned_count,
                "unassigned_percentage": round((unassigned_count / n) * 100, 2) if n > 0 else 0.0,
            },
            caveats=(
                "Departmental counts reflect automated portal routing and administrative assignment. "
                "Shared and contested jurisdictions between urban local bodies (ULBs) and state "
                "line departments can result in misrouted or unassigned dockets."
            ),
        )

    # -----------------------------------------------------------------------
    # 4. Monthly and Yearly Trends
    # -----------------------------------------------------------------------
    def calculate_temporal_trends(
        self,
        records: List[Any],
        period: str = "ALL_TIME",
        data_source: Optional[str] = None,
    ) -> MetricResult:
        """
        Metric 4: Time series aggregation across monthly (YYYY-MM) and yearly (YYYY) intervals.
        """
        source = data_source or self.default_source
        n = len(records)
        monthly_counts: Dict[str, int] = {}
        yearly_counts: Dict[str, int] = {}

        for rec in records:
            dt = (
                self._extract_date(rec, "submission_date")
                or self._extract_date(rec, "reported_date")
                or self._extract_date(rec, "lodged_date")
                or self._extract_date(rec, "created_at")
            )
            if dt:
                m_key = dt.strftime("%Y-%m")
                y_key = dt.strftime("%Y")
                monthly_counts[m_key] = monthly_counts.get(m_key, 0) + 1
                yearly_counts[y_key] = yearly_counts.get(y_key, 0) + 1
            else:
                monthly_counts["UNKNOWN_DATE"] = monthly_counts.get("UNKNOWN_DATE", 0) + 1
                yearly_counts["UNKNOWN_DATE"] = yearly_counts.get("UNKNOWN_DATE", 0) + 1

        # Sorted chronology
        sorted_months = dict(sorted(monthly_counts.items()))
        sorted_years = dict(sorted(yearly_counts.items()))

        # Calculate month-over-month percentage changes where valid
        mom_changes: Dict[str, Optional[float]] = {}
        prev_month: Optional[int] = None
        for m, count in sorted_months.items():
            if m == "UNKNOWN_DATE":
                continue
            if prev_month is not None and prev_month > 0:
                pct = round(((count - prev_month) / prev_month) * 100, 2)
                mom_changes[m] = pct
            else:
                mom_changes[m] = None
            prev_month = count

        return MetricResult(
            metric_code="TEMPORAL_TRENDS_MONTHLY_YEARLY",
            metric_name="Monthly and Yearly Civic Issue Trends",
            period=period,
            data_source=source,
            sample_size=n,
            metric_value=float(len(sorted_months)),
            unit="PERIODS_AGGREGATED",
            distribution={
                "monthly_counts": sorted_months,
                "yearly_counts": sorted_years,
                "month_over_month_change_pct": mom_changes,
            },
            caveats=(
                "Temporal trends are heavily impacted by seasonal phenomena (e.g. monsoon spikes), "
                "administrative campaigns, and portal server availability. Month-over-month changes "
                "must be interpreted alongside weather and portal operational logs."
            ),
        )

    # -----------------------------------------------------------------------
    # 5. Acknowledgement and Reported Resolution Times
    # -----------------------------------------------------------------------
    def calculate_turnaround_times(
        self,
        records: List[Any],
        period: str = "ALL_TIME",
        data_source: Optional[str] = None,
    ) -> MetricResult:
        """
        Metric 5: Mean, median (p50), and 90th percentile (p90) turnaround times
        for acknowledgement (hours) and reported resolution (days).
        """
        source = data_source or self.default_source
        ack_hours_list: List[float] = []
        res_days_list: List[float] = []

        for rec in records:
            sub_dt = (
                self._extract_date(rec, "submission_date")
                or self._extract_date(rec, "reported_date")
                or self._extract_date(rec, "lodged_date")
            )
            ack_dt = self._extract_date(rec, "acknowledgement_date")
            res_dt = (
                self._extract_date(rec, "resolution_date")
                or self._extract_date(rec, "actual_resolution_date")
            )

            # Check acknowledgement time
            if sub_dt and ack_dt and ack_dt >= sub_dt:
                hours = (ack_dt - sub_dt).total_seconds() / 3600.0
                ack_hours_list.append(round(hours, 2))

            # Check resolution time
            if sub_dt and res_dt and res_dt >= sub_dt:
                days = (res_dt - sub_dt).total_seconds() / 86400.0
                res_days_list.append(round(days, 2))

        def _stats(arr: List[float]) -> Dict[str, Optional[float]]:
            if not arr:
                return {"mean": None, "median": None, "p90": None, "min": None, "max": None, "count": 0}
            sorted_arr = sorted(arr)
            cnt = len(sorted_arr)
            mean_val = round(sum(sorted_arr) / cnt, 2)
            med_val = round(sorted_arr[cnt // 2], 2)
            p90_idx = min(int(math.ceil(0.90 * cnt)) - 1, cnt - 1)
            p90_val = round(sorted_arr[max(0, p90_idx)], 2)
            return {
                "mean": mean_val,
                "median": med_val,
                "p90": p90_val,
                "min": sorted_arr[0],
                "max": sorted_arr[-1],
                "count": cnt,
            }

        ack_stats = _stats(ack_hours_list)
        res_stats = _stats(res_days_list)

        median_res_days = res_stats["median"] or 0.0

        return MetricResult(
            metric_code="ACKNOWLEDGEMENT_AND_RESOLUTION_TIME",
            metric_name="Acknowledgement and Reported Resolution Turnaround Times",
            period=period,
            data_source=source,
            sample_size=len(records),
            metric_value=float(median_res_days),
            unit="MEDIAN_RESOLUTION_DAYS",
            distribution={
                "acknowledgement_hours": ack_stats,
                "reported_resolution_days": res_stats,
            },
            caveats=(
                "Reported resolution time measures administrative docket closure on government "
                "software portals. It does not measure physical on-site work completion unless "
                "corroborated by independent empirical evidence."
            ),
        )

    # -----------------------------------------------------------------------
    # 6. Percentage of Records with Known Status
    # -----------------------------------------------------------------------
    def calculate_known_status_percentage(
        self,
        records: List[Any],
        period: str = "ALL_TIME",
        data_source: Optional[str] = None,
    ) -> MetricResult:
        """
        Metric 6: Share of records with a definitive, known lifecycle status.
        """
        source = data_source or self.default_source
        n = len(records)
        known_count = 0
        status_breakdown: Dict[str, int] = {}

        unknown_tokens = {"unknown", "none", "", "unspecified", "pending_review"}

        for rec in records:
            status = self._extract_attr(rec, "status")
            status_str = "unknown"
            if hasattr(status, "value"):
                status_str = status.value.lower()
            elif isinstance(status, str):
                status_str = status.strip().lower()

            status_breakdown[status_str] = status_breakdown.get(status_str, 0) + 1

            if status_str not in unknown_tokens:
                known_count += 1

        known_pct = round((known_count / n) * 100, 2) if n > 0 else 0.0

        return MetricResult(
            metric_code="KNOWN_STATUS_PERCENTAGE",
            metric_name="Percentage of Records with Known Status",
            period=period,
            data_source=source,
            sample_size=n,
            metric_value=known_pct,
            unit="PERCENTAGE",
            distribution={
                "known_count": known_count,
                "unknown_count": n - known_count,
                "status_breakdown": status_breakdown,
            },
            caveats=(
                "Known status percentage evaluates portal data completeness and disclosure quality. "
                "Low percentages indicate missing or redacted administrative fields."
            ),
        )

    # -----------------------------------------------------------------------
    # 7. Recurring Issue Clusters
    # -----------------------------------------------------------------------
    def calculate_recurring_clusters(
        self,
        records: List[Any],
        period: str = "ALL_TIME",
        data_source: Optional[str] = None,
    ) -> MetricResult:
        """
        Metric 7: Identification and volume of recurring issues or spatial hotspots.
        """
        source = data_source or self.default_source
        n = len(records)
        recurring_count = 0
        clusters_map: Dict[str, int] = {}

        for rec in records:
            repeat_count = self._extract_attr(rec, "repeat_count", 1) or 1
            is_recurring = self._extract_attr(rec, "is_recurring", False)

            # Spatial-category composite key for clustering
            cat = self._extract_attr(rec, "issue_category") or self._extract_attr(rec, "category", "general")
            cat_str = cat.value if hasattr(cat, "value") else str(cat).lower()
            area = self._extract_attr(rec, "administrative_area_id") or "unspecified_area"
            cluster_key = f"{area}:{cat_str}"

            clusters_map[cluster_key] = clusters_map.get(cluster_key, 0) + 1

            if repeat_count > 1 or is_recurring:
                recurring_count += 1

        # Hotspots with 2 or more reports in the cluster
        multi_issue_hotspots = {k: v for k, v in clusters_map.items() if v > 1}
        recurrence_rate = round((recurring_count / n) * 100, 2) if n > 0 else 0.0

        return MetricResult(
            metric_code="RECURRING_ISSUE_CLUSTERS",
            metric_name="Recurring Issue Clusters and Hotspots",
            period=period,
            data_source=source,
            sample_size=n,
            metric_value=float(recurring_count),
            unit="RECURRING_COUNT",
            distribution={
                "recurring_records_count": recurring_count,
                "recurrence_rate_pct": recurrence_rate,
                "hotspot_clusters_count": len(multi_issue_hotspots),
                "top_hotspots": dict(sorted(multi_issue_hotspots.items(), key=lambda item: item[1], reverse=True)[:10]),
            },
            caveats=(
                "Recurring issues indicate potential chronic infrastructure failure or persistent "
                "citizen follow-up. Repeated complaints must not be treated as proof of malfeasance "
                "without verifying whether underlying works require multi-year capital sanctions."
            ),
        )

    # -----------------------------------------------------------------------
    # 8. Reopened Issue Counts
    # -----------------------------------------------------------------------
    def calculate_reopened_issues(
        self,
        records: List[Any],
        period: str = "ALL_TIME",
        data_source: Optional[str] = None,
    ) -> MetricResult:
        """
        Metric 8: Volume and rate of previously closed complaints reopened by citizens.
        """
        source = data_source or self.default_source
        n = len(records)
        reopened_count = 0
        resolved_count = 0

        for rec in records:
            status = self._extract_attr(rec, "status")
            status_str = status.value.lower() if hasattr(status, "value") else str(status).strip().lower()

            if status_str in {"reopened", "disputed"}:
                reopened_count += 1
            if status_str in {"resolved", "marked_resolved", "independently_verified_resolved", "closed"}:
                resolved_count += 1

        reopen_rate = round((reopened_count / n) * 100, 2) if n > 0 else 0.0
        reopen_vs_resolved_rate = (
            round((reopened_count / (resolved_count + reopened_count)) * 100, 2)
            if (resolved_count + reopened_count) > 0
            else 0.0
        )

        return MetricResult(
            metric_code="REOPENED_ISSUE_METRICS",
            metric_name="Reopened Issue Counts and Escalation Rate",
            period=period,
            data_source=source,
            sample_size=n,
            metric_value=float(reopened_count),
            unit="COUNT",
            distribution={
                "reopened_count": reopened_count,
                "resolved_count": resolved_count,
                "reopen_rate_of_total_pct": reopen_rate,
                "reopen_rate_of_closed_pct": reopen_vs_resolved_rate,
            },
            caveats=(
                "Reopening counts depend heavily on portal functionality. Portals lacking an online "
                "reopen or appeal button will show 0% reopening regardless of petitioner dissatisfaction. "
                "This metric is meaningful only for portals with an active citizen dispute workflow."
            ),
        )

    # -----------------------------------------------------------------------
    # 9. Documented Response Rates
    # -----------------------------------------------------------------------
    def calculate_documented_response_rate(
        self,
        records: List[Any],
        period: str = "ALL_TIME",
        data_source: Optional[str] = None,
    ) -> MetricResult:
        """
        Metric 9: Percentage of registered grievances with at least one documented
        Action-Taken Report or official response record.
        """
        source = data_source or self.default_source
        n = len(records)
        with_response = 0

        for rec in records:
            responses = self._extract_attr(rec, "responses") or []
            if responses and len(responses) > 0:
                with_response += 1
            else:
                # Also check if grievance itself has acknowledgement or resolution date logged
                ack = self._extract_date(rec, "acknowledgement_date")
                res = self._extract_date(rec, "resolution_date") or self._extract_date(rec, "actual_resolution_date")
                if ack or res:
                    with_response += 1

        response_rate = round((with_response / n) * 100, 2) if n > 0 else 0.0

        return MetricResult(
            metric_code="DOCUMENTED_RESPONSE_RATE",
            metric_name="Documented Departmental Response Rate",
            period=period,
            data_source=source,
            sample_size=n,
            metric_value=response_rate,
            unit="PERCENTAGE",
            distribution={
                "records_with_documented_response": with_response,
                "records_without_documented_response": n - with_response,
            },
            caveats=(
                "Documented response rate evaluates administrative record completeness. "
                "It measures whether an official response was published or recorded; "
                "it does not evaluate citizen satisfaction or on-site quality."
            ),
        )

    # -----------------------------------------------------------------------
    # 10. Resolution Evidence Coverage
    # -----------------------------------------------------------------------
    def calculate_resolution_evidence_coverage(
        self,
        records: List[Any],
        period: str = "ALL_TIME",
        data_source: Optional[str] = None,
    ) -> MetricResult:
        """
        Metric 10: Percentage of administratively resolved records corroborated
        by empirical evidence (e.g. work orders, completion certificates, site verification).
        """
        source = data_source or self.default_source
        marked_resolved_count = 0
        verified_resolved_count = 0

        for rec in records:
            status = self._extract_attr(rec, "status")
            status_str = status.value.lower() if hasattr(status, "value") else str(status).strip().lower()

            ver_status = self._extract_attr(rec, "resolution_verification_status")
            ver_status_str = ver_status.value.lower() if hasattr(ver_status, "value") else str(ver_status).strip().lower()

            is_verified = (
                ver_status_str in {"verified", "corroborated"}
                or status_str == "independently_verified_resolved"
                or bool(self._extract_attr(rec, "is_evidence_supported", False))
            )

            if status_str in {"marked_resolved", "resolved", "closed", "independently_verified_resolved"}:
                marked_resolved_count += 1
                if is_verified:
                    verified_resolved_count += 1

        coverage_rate = (
            round((verified_resolved_count / marked_resolved_count) * 100, 2)
            if marked_resolved_count > 0
            else 0.0
        )
        evidence_gap = round(100.0 - coverage_rate, 2) if marked_resolved_count > 0 else 0.0

        return MetricResult(
            metric_code="RESOLUTION_EVIDENCE_COVERAGE",
            metric_name="Resolution Evidence Coverage Rate",
            period=period,
            data_source=source,
            sample_size=marked_resolved_count,
            metric_value=coverage_rate,
            unit="PERCENTAGE",
            distribution={
                "total_marked_resolved": marked_resolved_count,
                "verified_with_evidence": verified_resolved_count,
                "unverified_closures": marked_resolved_count - verified_resolved_count,
                "evidence_gap_pct": evidence_gap,
            },
            caveats=(
                "Evidence coverage measures the presence of external empirical verification "
                "(work orders, completion certificates, field photos) backing official disposal claims. "
                "An unverified closure does not imply falsehood; it signifies an evidentiary gap."
            ),
        )

    # -----------------------------------------------------------------------
    # Statistical Anomaly Detection (with Small Sample Protection)
    # -----------------------------------------------------------------------
    def detect_volume_anomalies(
        self,
        records: List[Any],
        min_sample_size: int = MIN_ANOMALY_SAMPLE_SIZE,
        min_periods: int = MIN_ANOMALY_BASELINE_PERIODS,
        z_threshold: float = 2.0,
    ) -> AnomalyDetectionResult:
        """
        Detects statistical volume outliers across monthly intervals.
        Enforces strict small sample protection: returns INSUFFICIENT_DATA
        if sample size < min_sample_size or baseline periods < min_periods.
        """
        n = len(records)
        if n < min_sample_size:
            return AnomalyDetectionResult(
                status="INSUFFICIENT_DATA",
                sample_size=n,
                baseline_periods_count=0,
                interpretative_notice=ANOMALY_INVESTIGATION_NOTICE,
                reason=(
                    f"Sample size (N={n}) is below the minimum threshold (N >= {min_sample_size}) "
                    "required for reliable statistical anomaly detection. Anomaly calculation skipped."
                ),
            )

        # Compute monthly counts
        monthly_counts: Dict[str, int] = {}
        for rec in records:
            dt = (
                self._extract_date(rec, "submission_date")
                or self._extract_date(rec, "reported_date")
                or self._extract_date(rec, "lodged_date")
            )
            if dt:
                m_key = dt.strftime("%Y-%m")
                monthly_counts[m_key] = monthly_counts.get(m_key, 0) + 1

        periods_count = len(monthly_counts)
        if periods_count < min_periods:
            return AnomalyDetectionResult(
                status="INSUFFICIENT_DATA",
                sample_size=n,
                baseline_periods_count=periods_count,
                interpretative_notice=ANOMALY_INVESTIGATION_NOTICE,
                reason=(
                    f"Baseline periods count ({periods_count}) is below minimum requirement "
                    f"({min_periods} periods). Temporal baseline cannot be reliably established."
                ),
            )

        counts = list(monthly_counts.values())
        mean_val = sum(counts) / float(periods_count)
        variance = sum((x - mean_val) ** 2 for x in counts) / float(periods_count)
        std_val = math.sqrt(variance)

        if std_val < 1e-4:
            # Completely uniform counts across periods
            return AnomalyDetectionResult(
                status="SUFFICIENT_DATA",
                sample_size=n,
                baseline_periods_count=periods_count,
                anomalies=[],
                interpretative_notice=ANOMALY_INVESTIGATION_NOTICE,
            )

        detected_anomalies: List[AnomalyItem] = []
        for period_key, cnt in sorted(monthly_counts.items()):
            z = (cnt - mean_val) / std_val
            if abs(z) >= z_threshold:
                direction = "SPIKE" if z > 0 else "DROP"
                detected_anomalies.append(
                    AnomalyItem(
                        period=period_key,
                        observed_count=cnt,
                        expected_mean=round(mean_val, 2),
                        z_score=round(z, 2),
                        indicator_label="INVESTIGATION_INDICATOR_UNUSUAL_VOLUME",
                        interpretation_note=(
                            f"Unusual {direction.lower()} detected in {period_key} (|Z| = {abs(round(z, 2))} >= {z_threshold}). "
                            "This is an indicator requiring field investigation, NOT proof of administrative negligence."
                        ),
                    )
                )

        return AnomalyDetectionResult(
            status="SUFFICIENT_DATA",
            sample_size=n,
            baseline_periods_count=periods_count,
            anomalies=detected_anomalies,
            interpretative_notice=ANOMALY_INVESTIGATION_NOTICE,
        )

    # -----------------------------------------------------------------------
    # Comparative Area Analysis (with Strict Context Controls)
    # -----------------------------------------------------------------------
    def compare_areas(
        self,
        area_a_code: str,
        area_a_name: str,
        records_a: List[Any],
        area_b_code: str,
        area_b_name: str,
        records_b: List[Any],
        area_a_pop: Optional[int] = None,
        area_b_pop: Optional[int] = None,
    ) -> AreaComparisonResult:
        """
        Compares grievance metrics between two administrative areas.
        Attaches mandatory population normalization and explanatory context.
        """
        cnt_a = len(records_a)
        cnt_b = len(records_b)

        rate_a = round((cnt_a / area_a_pop) * 100_000, 2) if area_a_pop and area_a_pop > 0 else None
        rate_b = round((cnt_b / area_b_pop) * 100_000, 2) if area_b_pop and area_b_pop > 0 else None

        ratio = None
        if rate_a is not None and rate_b is not None and rate_b > 0:
            ratio = round(rate_a / rate_b, 2)

        has_pop = (area_a_pop is not None and area_b_pop is not None)

        context_notes = [
            f"Comparing {area_a_name} ({cnt_a} complaints) with {area_b_name} ({cnt_b} complaints)."
        ]
        if not has_pop:
            context_notes.append(
                "CRITICAL WARNING: Population data is missing for one or both areas. "
                "Raw count comparison is methodologically flawed and cannot be used to assess performance."
            )
        else:
            context_notes.append(
                f"Per-100k rates: {area_a_name} = {rate_a}, {area_b_name} = {rate_b}. "
                "Disparities reflect differences in portal literacy, helpline availability, "
                "and mobile connectivity rather than infrastructure condition alone."
            )

        return AreaComparisonResult(
            area_a_code=area_a_code,
            area_a_name=area_a_name,
            area_a_count=cnt_a,
            area_a_population=area_a_pop,
            area_a_rate_per_100k=rate_a,
            area_b_code=area_b_code,
            area_b_name=area_b_name,
            area_b_count=cnt_b,
            area_b_population=area_b_pop,
            area_b_rate_per_100k=rate_b,
            per_capita_ratio=ratio,
            comparison_valid=has_pop,
            required_context=" ".join(context_notes),
            interpretative_caveat=AREA_COMPARISON_CAVEAT,
        )

    # -----------------------------------------------------------------------
    # Comprehensive Report Generation
    # -----------------------------------------------------------------------
    def generate_comprehensive_report(
        self,
        records: List[Any],
        period: str = "ALL_TIME",
        data_source: Optional[str] = None,
        population_map: Optional[Dict[str, int]] = None,
    ) -> CivicAnalyticsReport:
        """
        Executes all 10 core civic metrics and runs guarded anomaly detection.
        Returns an auditable, self-documenting CivicAnalyticsReport.
        """
        src = data_source or self.default_source

        m1 = self.calculate_category_counts(records, period=period, data_source=src)
        m2 = self.calculate_area_counts(records, period=period, data_source=src, population_map=population_map)
        m3 = self.calculate_department_counts(records, period=period, data_source=src)
        m4 = self.calculate_temporal_trends(records, period=period, data_source=src)
        m5 = self.calculate_turnaround_times(records, period=period, data_source=src)
        m6 = self.calculate_known_status_percentage(records, period=period, data_source=src)
        m7 = self.calculate_recurring_clusters(records, period=period, data_source=src)
        m8 = self.calculate_reopened_issues(records, period=period, data_source=src)
        m9 = self.calculate_documented_response_rate(records, period=period, data_source=src)
        m10 = self.calculate_resolution_evidence_coverage(records, period=period, data_source=src)

        anomalies = self.detect_volume_anomalies(records)

        metrics_dict: Dict[str, MetricResult] = {
            m1.metric_code: m1,
            m2.metric_code: m2,
            m3.metric_code: m3,
            m4.metric_code: m4,
            m5.metric_code: m5,
            m6.metric_code: m6,
            m7.metric_code: m7,
            m8.metric_code: m8,
            m9.metric_code: m9,
            m10.metric_code: m10,
        }

        return CivicAnalyticsReport(
            reporting_period=period,
            data_source=src,
            total_records=len(records),
            metrics=metrics_dict,
            anomaly_detection=anomalies,
            general_disclaimer=GENERAL_ANALYTICS_DISCLAIMER,
        )

    # -----------------------------------------------------------------------
    # Database Persistence
    # -----------------------------------------------------------------------
    def persist_report_to_db(
        self,
        db: Session,
        report: CivicAnalyticsReport,
        is_test_fixture: bool = False,
    ) -> List[IssueMetric]:
        """
        Persists report metrics as IssueMetric entities in the database.
        """
        created_metrics: List[IssueMetric] = []

        for code, res in report.metrics.items():
            db_metric = IssueMetric(
                metric_code=res.metric_code,
                period=res.period,
                metric_name=res.metric_name,
                metric_value=res.metric_value,
                unit=res.unit,
                data_source=res.data_source,
                sample_size=res.sample_size,
                caveats=res.caveats,
                extra_metadata=res.distribution,
                is_test_fixture=is_test_fixture,
            )
            db.add(db_metric)
            created_metrics.append(db_metric)

        db.commit()
        for m in created_metrics:
            db.refresh(m)

        return created_metrics
