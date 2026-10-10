"""
Unit tests for Phase 5 Political Funding Analytics Engine.

Verifies calculation of all 11 financial metrics:
1. Total Disclosed Contributions
2. Year-on-Year Changes (with baseline validity check)
3. Contribution Size Distribution (Binned brackets)
4. Donor Concentration (Gini & HHI)
5. Top Disclosed Contributors
6. Donor Category Share
7. Reported Income vs Expenditure Surplus Ratio
8. Expenditure Category Distribution
9. Electoral Trust Pass-Through
10. Election Expenditure Trends
11. Summary Discrepancy Gap
"""

from backend.funding.analytics import FundingAnalyticsEngine, MetricUnit, DataQualityStatus
from tests.fixtures.phase5_analytics_fixtures import (
    MOCK_ANALYTICS_CONTRIBUTIONS_FY21,
    MOCK_ANALYTICS_STATEMENT_FY21,
    MOCK_ANALYTICS_EXPENDITURE_TN2021
)


class TestFundingAnalyticsEngine:

    def test_metric1_total_disclosed_contributions(self):
        m1 = FundingAnalyticsEngine.calculate_total_disclosed_contributions(
            party_id="PARTY_TN_DMK",
            financial_year="FY2021-22",
            contributions=MOCK_ANALYTICS_CONTRIBUTIONS_FY21,
            document_ids=["DOC_DMK_FY21"]
        )
        assert m1.metric_name == "TOTAL_DISCLOSED_CONTRIBUTIONS"
        # Sum: 10M + 50M + 100k + 30k = 60,130,000 INR
        assert m1.value == 60130000.0
        assert m1.unit == MetricUnit.INR

    def test_metric2_yoy_growth_calculation_and_skipping(self):
        # Case A: Valid baseline YoY calculation
        m2 = FundingAnalyticsEngine.calculate_yoy_growth(
            party_id="PARTY_TN_DMK",
            current_year="FY2021-22",
            current_total=60130000.0,
            previous_year="FY2020-21",
            previous_total=40000000.0,
            document_ids=["DOC_DMK_FY21"]
        )
        assert m2 is not None
        assert m2.metric_name == "YOY_CONTRIBUTION_GROWTH"
        # ((60.13M - 40M) / 40M) * 100 = 50.325% -> rounds to 50.32 in python
        assert m2.value == 50.32
        assert m2.unit == MetricUnit.PERCENTAGE

        # Case B: Missing baseline year -> Must return None (No calculation)
        m2_none = FundingAnalyticsEngine.calculate_yoy_growth(
            party_id="PARTY_TN_DMK",
            current_year="FY2021-22",
            current_total=60130000.0,
            previous_year="FY2020-21",
            previous_total=None,
            document_ids=["DOC_DMK_FY21"]
        )
        assert m2_none is None

    def test_metric3_contribution_size_distribution(self):
        m3 = FundingAnalyticsEngine.calculate_contribution_size_distribution(
            party_id="PARTY_TN_DMK",
            financial_year="FY2021-22",
            contributions=MOCK_ANALYTICS_CONTRIBUTIONS_FY21,
            document_ids=["DOC_DMK_FY21"]
        )
        assert m3.metric_name == "CONTRIBUTION_SIZE_DISTRIBUTION"
        val = m3.value
        assert val["BELOW_50K"]["count"] == 1  # 30k
        assert val["50K_TO_2L"]["count"] == 1  # 1 Lakh (100k)
        assert val["2L_TO_10L"]["count"] == 0
        assert val["10L_TO_1CR"]["count"] == 0
        assert val["ABOVE_1CR"]["count"] == 2  # 1 Crore + 5 Crore

    def test_metric4_donor_concentration(self):
        m4 = FundingAnalyticsEngine.calculate_donor_concentration(
            party_id="PARTY_TN_DMK",
            financial_year="FY2021-22",
            contributions=MOCK_ANALYTICS_CONTRIBUTIONS_FY21,
            document_ids=["DOC_DMK_FY21"]
        )
        assert m4.metric_name == "DONOR_CONCENTRATION_INDEX"
        val = m4.value
        assert "gini_coefficient" in val
        assert "hhi_index" in val
        assert val["gini_coefficient"] > 0.50  # Concentrated due to 5 Crore trust grant

    def test_metric5_top_contributors(self):
        m5 = FundingAnalyticsEngine.calculate_top_contributors(
            party_id="PARTY_TN_DMK",
            financial_year="FY2021-22",
            contributions=MOCK_ANALYTICS_CONTRIBUTIONS_FY21,
            document_ids=["DOC_DMK_FY21"],
            top_n=3
        )
        assert m5.metric_name == "TOP_DISCLOSED_CONTRIBUTORS"
        top_list = m5.value
        assert len(top_list) == 3
        # Rank 1 must be Prudent Electoral Trust (5 Crore)
        assert top_list[0]["donor_name"] == "Prudent Electoral Trust"
        assert top_list[0]["total_amount_inr"] == 50000000.0

    def test_metric6_donor_category_share(self):
        m6 = FundingAnalyticsEngine.calculate_donor_category_share(
            party_id="PARTY_TN_DMK",
            financial_year="FY2021-22",
            contributions=MOCK_ANALYTICS_CONTRIBUTIONS_FY21,
            document_ids=["DOC_DMK_FY21"]
        )
        assert m6.metric_name == "DONOR_CATEGORY_SHARE"
        val = m6.value
        assert val["ELECTORAL_TRUST"]["total_inr"] == 50000000.0
        assert val["CORPORATE"]["total_inr"] == 10000000.0
        assert val["INDIVIDUAL"]["total_inr"] == 100000.0

    def test_metric7_income_vs_expenditure_surplus(self):
        m7 = FundingAnalyticsEngine.calculate_income_vs_expenditure_surplus(
            party_id="PARTY_TN_DMK",
            financial_year="FY2021-22",
            statement=MOCK_ANALYTICS_STATEMENT_FY21,
            document_ids=["DOC_STMT_DMK_FY21"]
        )
        assert m7.metric_name == "INCOME_EXPENDITURE_SURPLUS_RATIO"
        val = m7.value
        # Income 30 Cr, Expenditure 22 Cr, Surplus 8 Cr -> (8 / 30) * 100 = 26.67%
        assert val["net_surplus_deficit_inr"] == 80000000.0
        assert val["surplus_ratio_percentage"] == 26.67

    def test_metric8_expenditure_category_distribution(self):
        m8 = FundingAnalyticsEngine.calculate_expenditure_category_distribution(
            party_id="PARTY_TN_DMK",
            financial_year="FY2021-22",
            expenditure_dict=MOCK_ANALYTICS_STATEMENT_FY21.expenditure_categories,
            document_ids=["DOC_STMT_DMK_FY21"]
        )
        assert m8.metric_name == "EXPENDITURE_CATEGORY_DISTRIBUTION"
        val = m8.value
        assert "publicity_and_media" in val
        assert val["publicity_and_media"]["total_inr"] == 120000000.0

    def test_metric9_electoral_trust_pass_through(self):
        m9 = FundingAnalyticsEngine.calculate_electoral_trust_pass_through(
            party_id="PARTY_TN_DMK",
            financial_year="FY2021-22",
            contributions=MOCK_ANALYTICS_CONTRIBUTIONS_FY21,
            statement=MOCK_ANALYTICS_STATEMENT_FY21,
            document_ids=["DOC_DMK_FY21"]
        )
        assert m9.metric_name == "ELECTORAL_TRUST_PASS_THROUGH"
        val = m9.value
        assert val["disclosed_trust_grants_inr"] == 50000000.0
        # (5 Cr / 30 Cr) * 100 = 16.67%
        assert val["share_of_total_income_percentage"] == 16.67

    def test_metric10_election_expenditure_trend(self):
        m10 = FundingAnalyticsEngine.calculate_election_expenditure_trend(
            party_id="PARTY_TN_DMK",
            election_name="TN Legislative Assembly 2021",
            reporting_period="FY2021-22",
            election_exp=MOCK_ANALYTICS_EXPENDITURE_TN2021,
            statement=MOCK_ANALYTICS_STATEMENT_FY21,
            document_ids=["DOC_EXP_DMK_TN2021"]
        )
        assert m10.metric_name == "ELECTION_EXPENDITURE_TREND"
        val = m10.value
        assert val["campaign_expenditure_inr"] == 190000000.0
        # (19 Cr / 30 Cr) * 100 = 63.33%
        assert val["campaign_intensity_percentage"] == 63.33

    def test_metric11_summary_discrepancy_gap(self):
        m11 = FundingAnalyticsEngine.calculate_summary_discrepancy_gap(
            party_id="PARTY_TN_DMK",
            financial_year="FY2021-22",
            contributions=MOCK_ANALYTICS_CONTRIBUTIONS_FY21,
            statement=MOCK_ANALYTICS_STATEMENT_FY21,
            document_ids=["DOC_DMK_FY21"]
        )
        assert m11.metric_name == "SUMMARY_DISCREPANCY_GAP"
        val = m11.value
        # Extracted 24A sum = 60,130,000 INR; Audited schedule 20k reported = 60,130,000 INR -> Discrepancy = 0
        assert val["discrepancy_gap_inr"] == 0.0
        assert m11.data_quality_status == DataQualityStatus.HIGH_QUALITY
