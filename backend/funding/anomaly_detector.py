"""
Phase 5 — Political Funding Anomaly Detection Engine.

Provides transparent, interpretable statistical anomaly detection across political funding records:
1. Robust Z-Score (using Median Absolute Deviation - MAD)
2. Interquartile Range (IQR) Outliers
3. Year-on-Year Spike Thresholds
4. Donor Concentration Thresholds (Gini / HHI)
5. Summary Discrepancy Gap Detector
6. Isolation Forest (for cohort sizes N >= 10)

ETHICAL DIRECTIVE:
An anomaly score is NOT a probability of corruption or illegality.
Flags represent mathematical patterns selected for human civic review.
"""

import math
import numpy as np
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple

from backend.funding.processor import AmountStatus
from backend.schemas.funding import ContributionSchema, FinancialStatementSchema

logger = logging.getLogger("civiclens.funding.anomaly")


class ReviewStatus:
    NEEDS_CIVIC_REVIEW = "NEEDS_CIVIC_REVIEW"
    UNDER_AUDIT = "UNDER_AUDIT"
    VERIFIED_EXPLAINABLE = "VERIFIED_EXPLAINABLE"
    DISMISSED = "DISMISSED"


class DetectionMethod:
    ROBUST_Z_SCORE = "ROBUST_Z_SCORE"
    IQR_OUTLIER = "IQR_OUTLIER"
    YOY_SPIKE_THRESHOLD = "YOY_SPIKE_THRESHOLD"
    DONOR_CONCENTRATION_THRESHOLD = "DONOR_CONCENTRATION_THRESHOLD"
    SUMMARY_DISCREPANCY = "SUMMARY_DISCREPANCY"
    ISOLATION_FOREST = "ISOLATION_FOREST"


@dataclass
class AnomalyFlagRecord:
    """Standardized schema for recording detected funding anomalies and civic review flags."""
    anomaly_id: str
    party_id: str
    financial_year: str
    metric_name: str
    observed_value: Any
    comparison_baseline: Any
    anomaly_score: float
    detection_method: str
    methodology_version: str = "v1.0"
    source_document_ids: List[str] = field(default_factory=list)
    explanation: str = ""
    review_status: str = ReviewStatus.NEEDS_CIVIC_REVIEW
    flagged_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class FundingAnomalyDetector:
    """Core transparent anomaly detection engine."""

    METHODOLOGY_VERSION = "v1.0"

    @staticmethod
    def calculate_robust_z_scores(values: List[float]) -> List[float]:
        """Calculates Robust Z-Scores using Median Absolute Deviation (MAD)."""
        if not values or len(values) < 3:
            return [0.0] * len(values)

        arr = np.array(values, dtype=float)
        median = np.median(arr)
        mad = np.median(np.abs(arr - median))

        if mad == 0:
            # Fallback to standard deviation if MAD is zero
            std = np.std(arr)
            if std == 0:
                return [0.0] * len(values)
            return [float(round((x - median) / std, 2)) for x in arr]

        # 0.6745 is the consistency constant for normal distribution
        robust_z = 0.6745 * (arr - median) / mad
        return [float(round(z, 2)) for z in robust_z]

    @staticmethod
    def calculate_iqr_fences(values: List[float]) -> Tuple[float, float, float, float]:
        """Calculates Q1, Q3, IQR, and Upper Fence (Q3 + 1.5*IQR)."""
        if not values or len(values) < 4:
            return 0.0, 0.0, 0.0, 0.0

        arr = np.array(values, dtype=float)
        q1 = float(np.percentile(arr, 25))
        q3 = float(np.percentile(arr, 75))
        iqr = q3 - q1
        upper_fence = q3 + 1.5 * iqr
        return q1, q3, iqr, upper_fence

    @classmethod
    def detect_unusual_contribution_amounts(
        cls,
        party_id: str,
        financial_year: str,
        contributions: List[ContributionSchema],
        document_ids: List[str]
    ) -> List[AnomalyFlagRecord]:
        """
        Detects unusually large contribution amounts using Robust Z-Score and IQR upper fences.
        """
        flags: List[AnomalyFlagRecord] = []
        valid_contribs = [c for c in contributions if c.amount is not None and c.amount > 0]
        if len(valid_contribs) < 3:
            return flags

        amounts = [c.amount for c in valid_contribs]
        robust_z = cls.calculate_robust_z_scores(amounts)
        _, q3, iqr, upper_fence = cls.calculate_iqr_fences(amounts)

        median_amt = float(np.median(amounts))

        for idx, (c, z_score) in enumerate(zip(valid_contribs, robust_z)):
            if z_score > 3.0 or (upper_fence > 0 and c.amount > upper_fence):
                anomaly_id = f"ANOM_{party_id}_{financial_year}_OUTLIER_CONT_{c.contribution_id}"
                exp = (
                    f"Contribution amount of INR {c.amount:,.2f} from '{c.donor_name_as_reported}' "
                    f"exceeds cohort median (INR {median_amt:,.2f}) with a Robust Z-Score of +{z_score:.2f} "
                    f"(IQR Upper Fence: INR {upper_fence:,.2f}). Selected for civic verification of donor profile."
                )

                flags.append(AnomalyFlagRecord(
                    anomaly_id=anomaly_id,
                    party_id=party_id,
                    financial_year=financial_year,
                    metric_name="CONTRIBUTION_AMOUNT_OUTLIER",
                    observed_value=c.amount,
                    comparison_baseline={
                        "cohort_median_inr": round(median_amt, 2),
                        "iqr_upper_fence_inr": round(upper_fence, 2),
                        "robust_z_score": z_score
                    },
                    anomaly_score=min(1.0, round(z_score / 10.0, 2)),
                    detection_method=DetectionMethod.ROBUST_Z_SCORE,
                    methodology_version=cls.METHODOLOGY_VERSION,
                    source_document_ids=document_ids,
                    explanation=exp,
                    review_status=ReviewStatus.NEEDS_CIVIC_REVIEW
                ))

        return flags

    @classmethod
    def detect_yoy_growth_spikes(
        cls,
        party_id: str,
        current_year: str,
        yoy_growth_percentage: Optional[float],
        baseline_median_growth: float,
        document_ids: List[str]
    ) -> List[AnomalyFlagRecord]:
        """Detects substantial, unusual year-on-year contribution surges (> 100% and > 2.5x median)."""
        flags: List[AnomalyFlagRecord] = []
        if yoy_growth_percentage is None:
            return flags

        # Threshold check: Growth > 100% AND > 2.5x median
        if yoy_growth_percentage > 100.0 and (baseline_median_growth == 0 or yoy_growth_percentage > 2.5 * abs(baseline_median_growth)):
            anomaly_id = f"ANOM_{party_id}_{current_year}_YOY_SPIKE"
            exp = (
                f"Party {party_id} declared a Year-on-Year contribution surge of +{yoy_growth_percentage:.2f}% "
                f"in {current_year}, substantially exceeding baseline growth trends (Median: {baseline_median_growth:.2f}%). "
                f"Selected for civic review of election cycle timing and donor influx."
            )

            flags.append(AnomalyFlagRecord(
                anomaly_id=anomaly_id,
                party_id=party_id,
                financial_year=current_year,
                metric_name="YOY_CONTRIBUTION_SPIKE",
                observed_value=yoy_growth_percentage,
                comparison_baseline={"baseline_median_growth_pct": baseline_median_growth},
                anomaly_score=min(1.0, round(yoy_growth_percentage / 300.0, 2)),
                detection_method=DetectionMethod.YOY_SPIKE_THRESHOLD,
                methodology_version=cls.METHODOLOGY_VERSION,
                source_document_ids=document_ids,
                explanation=exp,
                review_status=ReviewStatus.NEEDS_CIVIC_REVIEW
            ))

        return flags

    @classmethod
    def detect_donor_concentration_anomalies(
        cls,
        party_id: str,
        financial_year: str,
        gini_coefficient: float,
        hhi_index: float,
        document_ids: List[str]
    ) -> List[AnomalyFlagRecord]:
        """Detects extreme donor concentration (Gini > 0.80 or HHI > 0.35)."""
        flags: List[AnomalyFlagRecord] = []

        if gini_coefficient > 0.80 or hhi_index > 0.35:
            anomaly_id = f"ANOM_{party_id}_{financial_year}_CONCENTRATION"
            exp = (
                f"Disclosed funding for {party_id} exhibits extreme donor concentration in {financial_year} "
                f"(Gini Coefficient: {gini_coefficient:.2f}, HHI: {hhi_index:.2f}). "
                f"Indicates that a small minority of donors contribute the vast majority of disclosed funds."
            )

            flags.append(AnomalyFlagRecord(
                anomaly_id=anomaly_id,
                party_id=party_id,
                financial_year=financial_year,
                metric_name="HIGH_DONOR_CONCENTRATION",
                observed_value={"gini": gini_coefficient, "hhi": hhi_index},
                comparison_baseline={"gini_threshold": 0.80, "hhi_threshold": 0.35},
                anomaly_score=round(max(gini_coefficient, hhi_index), 2),
                detection_method=DetectionMethod.DONOR_CONCENTRATION_THRESHOLD,
                methodology_version=cls.METHODOLOGY_VERSION,
                source_document_ids=document_ids,
                explanation=exp,
                review_status=ReviewStatus.NEEDS_CIVIC_REVIEW
            ))

        return flags

    @classmethod
    def detect_summary_discrepancies(
        cls,
        party_id: str,
        financial_year: str,
        extracted_sum: float,
        audited_summary_20k: Optional[float],
        document_ids: List[str]
    ) -> List[AnomalyFlagRecord]:
        """Detects discrepancy gap between Form 24A extracted row sum and Audited Statement reported summary."""
        flags: List[AnomalyFlagRecord] = []
        if audited_summary_20k is None:
            return flags

        discrepancy = abs(extracted_sum - audited_summary_20k)
        if discrepancy > 50000.0:
            anomaly_id = f"ANOM_{party_id}_{financial_year}_SUMMARY_DISCREPANCY"
            exp = (
                f"Discrepancy gap of INR {discrepancy:,.2f} detected between itemized Form 24A extracted sum "
                f"(INR {extracted_sum:,.2f}) and Audited Statement reported 20k schedule (INR {audited_summary_20k:,.2f}). "
                f"Selected for document audit to verify missing schedule pages or summary typos."
            )

            flags.append(AnomalyFlagRecord(
                anomaly_id=anomaly_id,
                party_id=party_id,
                financial_year=financial_year,
                metric_name="SUMMARY_DISCREPANCY_GAP",
                observed_value={"extracted_sum": extracted_sum, "audited_summary": audited_summary_20k},
                comparison_baseline={"discrepancy_gap_inr": discrepancy},
                anomaly_score=min(1.0, round(discrepancy / (audited_summary_20k + 1.0), 2)),
                detection_method=DetectionMethod.SUMMARY_DISCREPANCY,
                methodology_version=cls.METHODOLOGY_VERSION,
                source_document_ids=document_ids,
                explanation=exp,
                review_status=ReviewStatus.NEEDS_CIVIC_REVIEW
            ))

        return flags

    @classmethod
    def detect_isolation_forest_anomalies(
        cls,
        feature_matrix: List[Dict[str, Any]],
        contamination: float = 0.10
    ) -> List[AnomalyFlagRecord]:
        """
        Executes Isolation Forest anomaly detection when cohort sample size N >= 10.
        Feature vector: [log(total_income), gini, unknown_ratio, yoy_growth]
        """
        flags: List[AnomalyFlagRecord] = []
        if len(feature_matrix) < 10:
            logger.info(f"Skipping Isolation Forest detection: Cohort sample size N={len(feature_matrix)} is < 10 threshold.")
            return flags

        try:
            from sklearn.ensemble import IsolationForest

            X = []
            records_ref = []
            for item in feature_matrix:
                inc = max(1.0, item.get("total_income", 1.0))
                gini = item.get("gini", 0.0)
                unk = item.get("unknown_ratio", 0.0)
                yoy = item.get("yoy_growth", 0.0)

                vec = [math.log10(inc), gini, unk, yoy]
                X.append(vec)
                records_ref.append(item)

            X_arr = np.array(X, dtype=float)
            clf = IsolationForest(contamination=contamination, random_state=42)
            preds = clf.fit_predict(X_arr)
            scores = clf.decision_function(X_arr)

            for idx, pred in enumerate(preds):
                if pred == -1:  # Outlier detected
                    item = records_ref[idx]
                    p_id = item["party_id"]
                    fy = item["financial_year"]
                    raw_score = float(-scores[idx])

                    anomaly_id = f"ANOM_{p_id}_{fy}_ISOLATION_FOREST"
                    exp = (
                        f"Multi-variate statistical outlier detected by Isolation Forest model for {p_id} in {fy} "
                        f"(Decision Score: {raw_score:.3f}). Features [Log Income: {X[idx][0]:.2f}, Gini: {X[idx][1]:.2f}, "
                        f"Unknown Ratio: {X[idx][2]:.2f}, YoY Growth: {X[idx][3]:.1f}%] deviate from cohort norms."
                    )

                    flags.append(AnomalyFlagRecord(
                        anomaly_id=anomaly_id,
                        party_id=p_id,
                        financial_year=fy,
                        metric_name="MULTIVARIATE_FUNDING_OUTLIER",
                        observed_value=item,
                        comparison_baseline={"cohort_size_N": len(feature_matrix), "isolation_score": raw_score},
                        anomaly_score=min(1.0, round(raw_score * 2.0, 2)),
                        detection_method=DetectionMethod.ISOLATION_FOREST,
                        methodology_version=cls.METHODOLOGY_VERSION,
                        source_document_ids=item.get("document_ids", []),
                        explanation=exp,
                        review_status=ReviewStatus.NEEDS_CIVIC_REVIEW
                    ))
        except Exception as e:
            logger.warning(f"Isolation Forest detection encountered an error: {e}")

        return flags
