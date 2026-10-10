"""
Phase 5 — Political Funding Analytics Engine.

Computes 11 financial metrics using normalized statutory disclosures:
1. Total Disclosed Contributions
2. Year-on-Year Changes
3. Contribution Size Distribution (Binned brackets)
4. Donor Concentration (Gini & HHI Index)
5. Top Disclosed Contributors
6. Donor Category Share (Corporate vs Individual vs Trust)
7. Reported Income vs Expenditure (Surplus Ratio)
8. Expenditure Category Distribution
9. Electoral Trust Pass-Through Analysis
10. Election Expenditure Trends
11. Summary Discrepancy Gap (Form 24A vs Audited Accounts)
"""

import math
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple
from backend.schemas.funding import ContributionSchema, FinancialStatementSchema, ElectionExpenditureSchema

logger = logging.getLogger("civiclens.funding.analytics")


class DataQualityStatus:
    HIGH_QUALITY = "HIGH_QUALITY"
    PARTIAL_DATA = "PARTIAL_DATA"
    LIMITED_DISCLOSURE = "LIMITED_DISCLOSURE"
    SUMMARY_DISCREPANCY = "SUMMARY_DISCREPANCY"


class MetricUnit:
    INR = "INR"
    PERCENTAGE = "PERCENTAGE"
    INDEX = "INDEX"
    RATIO = "RATIO"
    COUNT = "COUNT"
    DISTRIBUTION_DICT = "DISTRIBUTION_DICT"
    RANKED_LIST = "RANKED_LIST"


@dataclass
class ComputedMetricRecord:
    """Standardized schema for storing computed financial analytics."""
    metric_name: str
    party_id: str
    financial_year: str
    value: Any
    unit: str
    source_document_ids: List[str]
    calculation_method: str
    calculation_version: str = "v1.0"
    data_quality_status: str = DataQualityStatus.HIGH_QUALITY
    computed_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class FundingAnalyticsEngine:
    """Core calculation engine for political funding transparency analytics."""

    CALCULATION_VERSION = "v1.0"

    @classmethod
    def calculate_total_disclosed_contributions(
        cls,
        party_id: str,
        financial_year: str,
        contributions: List[ContributionSchema],
        document_ids: List[str]
    ) -> ComputedMetricRecord:
        """Metric 1: Total disclosed contributions (> ₹20,000)."""
        valid_amounts = [c.amount for c in contributions if c.amount is not None and c.amount > 0]
        total_sum = sum(valid_amounts)

        status = DataQualityStatus.HIGH_QUALITY
        if not contributions:
            status = DataQualityStatus.LIMITED_DISCLOSURE
        elif any(c.extraction_confidence < 0.70 for c in contributions):
            status = DataQualityStatus.PARTIAL_DATA

        return ComputedMetricRecord(
            metric_name="TOTAL_DISCLOSED_CONTRIBUTIONS",
            party_id=party_id,
            financial_year=financial_year,
            value=round(total_sum, 2),
            unit=MetricUnit.INR,
            source_document_ids=document_ids,
            calculation_method="Sum of itemized Form 24A disclosures where amount > 0",
            calculation_version=cls.CALCULATION_VERSION,
            data_quality_status=status
        )

    @classmethod
    def calculate_yoy_growth(
        cls,
        party_id: str,
        current_year: str,
        current_total: Optional[float],
        previous_year: str,
        previous_total: Optional[float],
        document_ids: List[str]
    ) -> Optional[ComputedMetricRecord]:
        """
        Metric 2: Year-on-Year percentage change.
        ONLY computed when BOTH periods have valid, non-zero comparable values.
        """
        if current_total is None or previous_total is None or previous_total <= 0:
            logger.info(f"Skipping YoY growth calculation for {party_id} between {previous_year} and {current_year}: Insufficient/invalid baseline data.")
            return None

        growth_pct = ((current_total - previous_total) / previous_total) * 100.0

        return ComputedMetricRecord(
            metric_name="YOY_CONTRIBUTION_GROWTH",
            party_id=party_id,
            financial_year=current_year,
            value=round(growth_pct, 2),
            unit=MetricUnit.PERCENTAGE,
            source_document_ids=document_ids,
            calculation_method=f"Percentage change from {previous_year} (INR {previous_total:,.0f}) to {current_year} (INR {current_total:,.0f})",
            calculation_version=cls.CALCULATION_VERSION,
            data_quality_status=DataQualityStatus.HIGH_QUALITY
        )

    @classmethod
    def calculate_contribution_size_distribution(
        cls,
        party_id: str,
        financial_year: str,
        contributions: List[ContributionSchema],
        document_ids: List[str]
    ) -> ComputedMetricRecord:
        """Metric 3: Contribution size distribution across binned brackets."""
        brackets = {
            "BELOW_50K": {"count": 0, "total_inr": 0.0},
            "50K_TO_2L": {"count": 0, "total_inr": 0.0},
            "2L_TO_10L": {"count": 0, "total_inr": 0.0},
            "10L_TO_1CR": {"count": 0, "total_inr": 0.0},
            "ABOVE_1CR": {"count": 0, "total_inr": 0.0}
        }

        for c in contributions:
            amt = c.amount or 0.0
            if amt <= 0:
                continue

            if amt < 50000.0:
                brackets["BELOW_50K"]["count"] += 1
                brackets["BELOW_50K"]["total_inr"] += amt
            elif amt < 200000.0:
                brackets["50K_TO_2L"]["count"] += 1
                brackets["50K_TO_2L"]["total_inr"] += amt
            elif amt < 1000000.0:
                brackets["2L_TO_10L"]["count"] += 1
                brackets["2L_TO_10L"]["total_inr"] += amt
            elif amt < 10000000.0:
                brackets["10L_TO_1CR"]["count"] += 1
                brackets["10L_TO_1CR"]["total_inr"] += amt
            else:
                brackets["ABOVE_1CR"]["count"] += 1
                brackets["ABOVE_1CR"]["total_inr"] += amt

        return ComputedMetricRecord(
            metric_name="CONTRIBUTION_SIZE_DISTRIBUTION",
            party_id=party_id,
            financial_year=financial_year,
            value=brackets,
            unit=MetricUnit.DISTRIBUTION_DICT,
            source_document_ids=document_ids,
            calculation_method="Binned frequency distribution into 5 standard monetary brackets",
            calculation_version=cls.CALCULATION_VERSION,
            data_quality_status=DataQualityStatus.HIGH_QUALITY
        )

    @classmethod
    def calculate_donor_concentration(
        cls,
        party_id: str,
        financial_year: str,
        contributions: List[ContributionSchema],
        document_ids: List[str]
    ) -> ComputedMetricRecord:
        """Metric 4: Gini Coefficient & Herfindahl-Hirschman Index (HHI)."""
        valid_amounts = sorted([c.amount for c in contributions if c.amount is not None and c.amount > 0])
        n = len(valid_amounts)

        if n == 0:
            gini = 0.0
            hhi = 0.0
        else:
            total_sum = sum(valid_amounts)
            mean_val = total_sum / n
            # Gini formula
            diff_sum = sum(abs(x - y) for x in valid_amounts for y in valid_amounts)
            gini = diff_sum / (2 * n * n * mean_val) if mean_val > 0 else 0.0

            # HHI formula
            hhi = sum((amt / total_sum) ** 2 for amt in valid_amounts) if total_sum > 0 else 0.0

        return ComputedMetricRecord(
            metric_name="DONOR_CONCENTRATION_INDEX",
            party_id=party_id,
            financial_year=financial_year,
            value={
                "gini_coefficient": round(gini, 4),
                "hhi_index": round(hhi, 4),
                "total_donors_count": n
            },
            unit=MetricUnit.INDEX,
            source_document_ids=document_ids,
            calculation_method="Gini coefficient and Herfindahl-Hirschman Index computed on disclosed contributions",
            calculation_version=cls.CALCULATION_VERSION,
            data_quality_status=DataQualityStatus.HIGH_QUALITY if n >= 5 else DataQualityStatus.PARTIAL_DATA
        )

    @classmethod
    def calculate_top_contributors(
        cls,
        party_id: str,
        financial_year: str,
        contributions: List[ContributionSchema],
        document_ids: List[str],
        top_n: int = 5
    ) -> ComputedMetricRecord:
        """Metric 5: Top N disclosed contributors by aggregate contribution amount."""
        donor_totals: Dict[str, float] = {}
        for c in contributions:
            amt = c.amount or 0.0
            if amt <= 0:
                continue
            donor_name = c.donor_name_as_reported or "UNDISCLOSED"
            donor_totals[donor_name] = donor_totals.get(donor_name, 0.0) + amt

        total_disclosed = sum(donor_totals.values())
        sorted_donors = sorted(donor_totals.items(), key=lambda x: x[1], reverse=True)[:top_n]

        top_list = []
        for rank, (d_name, d_amt) in enumerate(sorted_donors, start=1):
            top_list.append({
                "rank": rank,
                "donor_name": d_name,
                "total_amount_inr": round(d_amt, 2),
                "share_percentage": round((d_amt / total_disclosed) * 100.0, 2) if total_disclosed > 0 else 0.0
            })

        return ComputedMetricRecord(
            metric_name="TOP_DISCLOSED_CONTRIBUTORS",
            party_id=party_id,
            financial_year=financial_year,
            value=top_list,
            unit=MetricUnit.RANKED_LIST,
            source_document_ids=document_ids,
            calculation_method=f"Ranked top-{top_n} donor entities by total disclosed contribution volume",
            calculation_version=cls.CALCULATION_VERSION,
            data_quality_status=DataQualityStatus.HIGH_QUALITY
        )

    @classmethod
    def calculate_donor_category_share(
        cls,
        party_id: str,
        financial_year: str,
        contributions: List[ContributionSchema],
        document_ids: List[str]
    ) -> ComputedMetricRecord:
        """Metric 6: Share of contributions by donor category (Corporate vs Individual vs Trust)."""
        categories = {
            "CORPORATE": 0.0,
            "INDIVIDUAL": 0.0,
            "ELECTORAL_TRUST": 0.0,
            "OTHER_UNKNOWN": 0.0
        }

        total_sum = 0.0

        for c in contributions:
            amt = c.amount or 0.0
            if amt <= 0:
                continue
            total_sum += amt
            name_lowered = (c.donor_name_as_reported or "").lower()
            mode_lowered = (c.contribution_type or "").lower()

            if "electoral trust" in name_lowered or "trust" in name_lowered or mode_lowered == "electoraltrust":
                categories["ELECTORAL_TRUST"] += amt
            elif any(corp_tag in name_lowered for corp_tag in ["ltd", "pvt", "limited", "private", "inc", "corp", "company", "infra", "industries"]):
                categories["CORPORATE"] += amt
            elif any(ind_tag in name_lowered for ind_tag in ["mr", "mrs", "ms", "dr", "shri", "smt"]):
                categories["INDIVIDUAL"] += amt
            else:
                categories["OTHER_UNKNOWN"] += amt

        shares = {}
        for cat, amt in categories.items():
            shares[cat] = {
                "total_inr": round(amt, 2),
                "percentage": round((amt / total_sum) * 100.0, 2) if total_sum > 0 else 0.0
            }

        return ComputedMetricRecord(
            metric_name="DONOR_CATEGORY_SHARE",
            party_id=party_id,
            financial_year=financial_year,
            value=shares,
            unit=MetricUnit.DISTRIBUTION_DICT,
            source_document_ids=document_ids,
            calculation_method="Classification of contributions into Corporate, Individual, Electoral Trust, and Unknown categories",
            calculation_version=cls.CALCULATION_VERSION,
            data_quality_status=DataQualityStatus.HIGH_QUALITY
        )

    @classmethod
    def calculate_income_vs_expenditure_surplus(
        cls,
        party_id: str,
        financial_year: str,
        statement: FinancialStatementSchema,
        document_ids: List[str]
    ) -> ComputedMetricRecord:
        """Metric 7: Audited Income vs Expenditure Surplus/Deficit Ratio."""
        income = statement.total_income_reported or 0.0
        expenditure = statement.total_expenditure_reported or 0.0
        surplus = income - expenditure

        surplus_ratio = (surplus / income) * 100.0 if income > 0 else 0.0

        return ComputedMetricRecord(
            metric_name="INCOME_EXPENDITURE_SURPLUS_RATIO",
            party_id=party_id,
            financial_year=financial_year,
            value={
                "total_income_inr": round(income, 2),
                "total_expenditure_inr": round(expenditure, 2),
                "net_surplus_deficit_inr": round(surplus, 2),
                "surplus_ratio_percentage": round(surplus_ratio, 2)
            },
            unit=MetricUnit.RATIO,
            source_document_ids=document_ids,
            calculation_method="Audited Net Surplus/Deficit expressed as percentage of total audited party income",
            calculation_version=cls.CALCULATION_VERSION,
            data_quality_status=DataQualityStatus.HIGH_QUALITY if income > 0 else DataQualityStatus.LIMITED_DISCLOSURE
        )

    @classmethod
    def calculate_expenditure_category_distribution(
        cls,
        party_id: str,
        financial_year: str,
        expenditure_dict: Dict[str, float],
        document_ids: List[str]
    ) -> ComputedMetricRecord:
        """Metric 8: Distribution of expenditure across campaign/operating categories."""
        total_exp = sum(expenditure_dict.values())
        distribution = {}
        for cat, amt in expenditure_dict.items():
            distribution[cat] = {
                "total_inr": round(amt, 2),
                "percentage": round((amt / total_exp) * 100.0, 2) if total_exp > 0 else 0.0
            }

        return ComputedMetricRecord(
            metric_name="EXPENDITURE_CATEGORY_DISTRIBUTION",
            party_id=party_id,
            financial_year=financial_year,
            value=distribution,
            unit=MetricUnit.DISTRIBUTION_DICT,
            source_document_ids=document_ids,
            calculation_method="Percentage breakdown of operating and campaign expenditure heads",
            calculation_version=cls.CALCULATION_VERSION,
            data_quality_status=DataQualityStatus.HIGH_QUALITY
        )

    @classmethod
    def calculate_electoral_trust_pass_through(
        cls,
        party_id: str,
        financial_year: str,
        contributions: List[ContributionSchema],
        statement: Optional[FinancialStatementSchema],
        document_ids: List[str]
    ) -> ComputedMetricRecord:
        """Metric 9: Electoral Trust grants share relative to disclosed and total party income."""
        trust_grants_disclosed = sum(c.amount for c in contributions if c.amount and ("trust" in (c.donor_name_as_reported or "").lower() or c.contribution_type == "ElectoralTrust"))

        total_income = statement.total_income_reported if statement else None
        share_of_total = (trust_grants_disclosed / total_income) * 100.0 if (total_income and total_income > 0) else None

        return ComputedMetricRecord(
            metric_name="ELECTORAL_TRUST_PASS_THROUGH",
            party_id=party_id,
            financial_year=financial_year,
            value={
                "disclosed_trust_grants_inr": round(trust_grants_disclosed, 2),
                "total_audited_income_inr": round(total_income, 2) if total_income else None,
                "share_of_total_income_percentage": round(share_of_total, 2) if share_of_total is not None else None
            },
            unit=MetricUnit.RATIO,
            source_document_ids=document_ids,
            calculation_method="Ratio of Electoral Trust grants to total audited party income",
            calculation_version=cls.CALCULATION_VERSION,
            data_quality_status=DataQualityStatus.HIGH_QUALITY if total_income else DataQualityStatus.PARTIAL_DATA
        )

    @classmethod
    def calculate_election_expenditure_trend(
        cls,
        party_id: str,
        election_name: str,
        reporting_period: str,
        election_exp: ElectionExpenditureSchema,
        statement: Optional[FinancialStatementSchema],
        document_ids: List[str]
    ) -> ComputedMetricRecord:
        """Metric 10: Campaign expenditure intensity during election cycles."""
        campaign_total = election_exp.reported_totals or sum(election_exp.expenditure_categories.values())
        total_income = statement.total_income_reported if statement else None

        intensity = (campaign_total / total_income) * 100.0 if (total_income and total_income > 0) else None

        return ComputedMetricRecord(
            metric_name="ELECTION_EXPENDITURE_TREND",
            party_id=party_id,
            financial_year=reporting_period,
            value={
                "election_name": election_name,
                "campaign_expenditure_inr": round(campaign_total, 2),
                "total_annual_income_inr": round(total_income, 2) if total_income else None,
                "campaign_intensity_percentage": round(intensity, 2) if intensity is not None else None
            },
            unit=MetricUnit.RATIO,
            source_document_ids=document_ids,
            calculation_method="Campaign expenditure intensity expressed as percentage of annual party income",
            calculation_version=cls.CALCULATION_VERSION,
            data_quality_status=DataQualityStatus.HIGH_QUALITY
        )

    @classmethod
    def calculate_summary_discrepancy_gap(
        cls,
        party_id: str,
        financial_year: str,
        contributions: List[ContributionSchema],
        statement: Optional[FinancialStatementSchema],
        document_ids: List[str]
    ) -> ComputedMetricRecord:
        """Metric 11: Difference between Form 24A extracted row sum and Audited Statement reported 20k schedule."""
        extracted_sum = sum(c.amount for c in contributions if c.amount and c.amount > 0)
        reported_20k = None

        if statement and statement.income_categories:
            reported_20k = (
                statement.income_categories.get("donations_above_20k") or
                statement.income_categories.get("contributions_above_20k")
            )

        discrepancy_gap = abs(extracted_sum - reported_20k) if reported_20k is not None else 0.0
        discrepancy_pct = (discrepancy_gap / reported_20k) * 100.0 if (reported_20k and reported_20k > 0) else 0.0

        status = DataQualityStatus.HIGH_QUALITY
        if discrepancy_gap > 50000.0:
            status = DataQualityStatus.SUMMARY_DISCREPANCY

        return ComputedMetricRecord(
            metric_name="SUMMARY_DISCREPANCY_GAP",
            party_id=party_id,
            financial_year=financial_year,
            value={
                "extracted_form24a_sum_inr": round(extracted_sum, 2),
                "audited_reported_20k_inr": round(reported_20k, 2) if reported_20k is not None else None,
                "discrepancy_gap_inr": round(discrepancy_gap, 2),
                "discrepancy_percentage": round(discrepancy_pct, 2)
            },
            unit=MetricUnit.INR,
            source_document_ids=document_ids,
            calculation_method="Absolute difference between itemized Form 24A extracted sum and Audited Account reported 20k schedule",
            calculation_version=cls.CALCULATION_VERSION,
            data_quality_status=status
        )
