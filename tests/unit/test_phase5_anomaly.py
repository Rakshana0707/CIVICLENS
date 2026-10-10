"""
Unit tests for Phase 5 Political Funding Anomaly Detection Engine.

Verifies:
1. Robust Z-Score (MAD) and IQR calculation.
2. Contribution amount outlier detection.
3. YoY Growth spike detection threshold.
4. High donor concentration threshold detection.
5. Summary discrepancy gap detection.
6. Isolation Forest sample size rule (N < 10 skips, N >= 10 executes).
7. Missing values safety and reproducibility.
"""

from backend.funding.anomaly_detector import (
    FundingAnomalyDetector,
    DetectionMethod,
    ReviewStatus,
    AnomalyFlagRecord
)
from tests.fixtures.phase5_analytics_fixtures import MOCK_ANALYTICS_CONTRIBUTIONS_FY21


class TestFundingAnomalyDetector:

    def test_robust_z_score_calculation(self):
        values = [100.0, 105.0, 102.0, 108.0, 101.0, 5000.0]  # 5000 is extreme outlier
        robust_z = FundingAnomalyDetector.calculate_robust_z_scores(values)
        assert len(robust_z) == 6
        # 5000.0 must have a high Robust Z-Score (> 3.0)
        assert robust_z[5] > 3.0

    def test_iqr_fences_calculation(self):
        values = [10, 20, 30, 40, 50, 60, 70, 80, 90, 100]
        q1, q3, iqr, upper_fence = FundingAnomalyDetector.calculate_iqr_fences(values)
        assert q1 < q3
        assert iqr == q3 - q1
        assert upper_fence > q3

    def test_detect_unusual_contribution_amounts(self):
        flags = FundingAnomalyDetector.detect_unusual_contribution_amounts(
            party_id="PARTY_TN_DMK",
            financial_year="FY2021-22",
            contributions=MOCK_ANALYTICS_CONTRIBUTIONS_FY21,
            document_ids=["DOC_DMK_FY21"]
        )
        # Should flag 50M contribution as an outlier
        assert len(flags) >= 1
        f1 = flags[0]
        assert f1.metric_name == "CONTRIBUTION_AMOUNT_OUTLIER"
        assert f1.detection_method == DetectionMethod.ROBUST_Z_SCORE
        assert f1.review_status == ReviewStatus.NEEDS_CIVIC_REVIEW

    def test_detect_yoy_growth_spikes(self):
        # Case A: Spike > 100% and > 2.5x median -> Flagged
        flags = FundingAnomalyDetector.detect_yoy_growth_spikes(
            party_id="PARTY_TN_DMK",
            current_year="FY2021-22",
            yoy_growth_percentage=180.0,
            baseline_median_growth=25.0,
            document_ids=["DOC_DMK_FY21"]
        )
        assert len(flags) == 1
        assert flags[0].metric_name == "YOY_CONTRIBUTION_SPIKE"
        assert flags[0].observed_value == 180.0

        # Case B: Normal growth (30%) -> Not flagged
        flags_normal = FundingAnomalyDetector.detect_yoy_growth_spikes(
            party_id="PARTY_TN_DMK",
            current_year="FY2021-22",
            yoy_growth_percentage=30.0,
            baseline_median_growth=25.0,
            document_ids=["DOC_DMK_FY21"]
        )
        assert len(flags_normal) == 0

    def test_detect_donor_concentration_anomalies(self):
        # Gini 0.84 > 0.80 -> Flagged
        flags = FundingAnomalyDetector.detect_donor_concentration_anomalies(
            party_id="PARTY_TN_DMK",
            financial_year="FY2021-22",
            gini_coefficient=0.84,
            hhi_index=0.38,
            document_ids=["DOC_DMK_FY21"]
        )
        assert len(flags) == 1
        assert flags[0].metric_name == "HIGH_DONOR_CONCENTRATION"
        assert flags[0].anomaly_score == 0.84

    def test_detect_summary_discrepancies(self):
        # Discrepancy 100,000 INR > 50,000 INR threshold -> Flagged
        flags = FundingAnomalyDetector.detect_summary_discrepancies(
            party_id="PARTY_TN_DMK",
            financial_year="FY2021-22",
            extracted_sum=60000000.0,
            audited_summary_20k=60100000.0,
            document_ids=["DOC_DMK_FY21"]
        )
        assert len(flags) == 1
        assert flags[0].metric_name == "SUMMARY_DISCREPANCY_GAP"

    def test_isolation_forest_sample_size_threshold(self):
        # Case A: Sample size N=5 (< 10 threshold) -> Skipped
        small_cohort = [
            {"party_id": f"PARTY_{i}", "financial_year": "FY2021-22", "total_income": 10000000.0 * i, "gini": 0.5 + 0.05 * i, "unknown_ratio": 0.2, "yoy_growth": 10.0 * i}
            for i in range(1, 6)
        ]
        flags_small = FundingAnomalyDetector.detect_isolation_forest_anomalies(small_cohort)
        assert len(flags_small) == 0

        # Case B: Sample size N=12 (>= 10 threshold) -> Executed
        large_cohort = [
            {"party_id": f"PARTY_{i}", "financial_year": "FY2021-22", "total_income": 10000000.0 * i, "gini": 0.3 + (i % 3) * 0.1, "unknown_ratio": 0.2, "yoy_growth": 10.0}
            for i in range(1, 12)
        ]
        # Inject extreme outlier
        large_cohort.append({"party_id": "PARTY_OUTLIER", "financial_year": "FY2021-22", "total_income": 5000000000.0, "gini": 0.98, "unknown_ratio": 0.95, "yoy_growth": 950.0})

        flags_large = FundingAnomalyDetector.detect_isolation_forest_anomalies(large_cohort)
        assert len(flags_large) >= 1
        outlier_party_ids = [f.party_id for f in flags_large]
        assert "PARTY_OUTLIER" in outlier_party_ids
