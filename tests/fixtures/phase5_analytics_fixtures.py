"""
Phase 5 Financial Analytics Test Fixtures.

Contains explicitly labelled mock contributions, multi-year contribution histories,
financial statements, and election expenditure reports used strictly for testing
all 11 financial analytics functions.
"""

from typing import Dict, Any, List
from backend.schemas.funding import ContributionSchema, FinancialStatementSchema, ElectionExpenditureSchema

MOCK_ANALYTICS_CONTRIBUTIONS_FY21: List[ContributionSchema] = [
    ContributionSchema(
        contribution_id="CONT_AN_001",
        party_id="PARTY_TN_DMK",
        donor_name_as_reported="Mega Corp Infrastructure Pvt Ltd",
        donor_name_normalized="MEGA CORP INFRASTRUCTURE PVT LTD",
        amount=10000000.0,  # 1 Crore (Corporate)
        financial_year="FY2021-22",
        contribution_type="EFT",
        document_id="DOC_DMK_FY21"
    ),
    ContributionSchema(
        contribution_id="CONT_AN_002",
        party_id="PARTY_TN_DMK",
        donor_name_as_reported="Prudent Electoral Trust",
        donor_name_normalized="PRUDENT ELECTORAL TRUST",
        amount=50000000.0,  # 5 Crore (Electoral Trust)
        financial_year="FY2021-22",
        contribution_type="ElectoralTrust",
        document_id="DOC_DMK_FY21"
    ),
    ContributionSchema(
        contribution_id="CONT_AN_003",
        party_id="PARTY_TN_DMK",
        donor_name_as_reported="Dr. K. Swaminathan",
        donor_name_normalized="DR. K. SWAMINATHAN",
        amount=100000.0,  # 1 Lakh (Individual)
        financial_year="FY2021-22",
        contribution_type="Cheque",
        document_id="DOC_DMK_FY21"
    ),
    ContributionSchema(
        contribution_id="CONT_AN_004",
        party_id="PARTY_TN_DMK",
        donor_name_as_reported="Small Retailer Store",
        donor_name_normalized="SMALL RETAILER STORE",
        amount=30000.0,  # 30k (Below 50k bracket)
        financial_year="FY2021-22",
        contribution_type="Cheque",
        document_id="DOC_DMK_FY21"
    )
]

MOCK_ANALYTICS_STATEMENT_FY21 = FinancialStatementSchema(
    statement_id="STMT_DMK_FY21",
    party_id="PARTY_TN_DMK",
    financial_year="FY2021-22",
    total_income_reported=300000000.0,  # 30 Crore
    total_expenditure_reported=220000000.0,  # 22 Crore
    net_surplus_deficit=80000000.0,  # 8 Crore surplus
    income_categories={
        "donations_above_20k": 60130000.0,  # Matches sum of items above (6.013 Crore)
        "electoral_bond_income": 150000000.0,
        "other_income": 89870000.0
    },
    expenditure_categories={
        "publicity_and_media": 120000000.0,
        "star_campaigner_travel": 50000000.0,
        "salaries_and_admin": 30000000.0,
        "candidate_assistance": 20000000.0
    },
    document_id="DOC_STMT_DMK_FY21"
)

MOCK_ANALYTICS_EXPENDITURE_TN2021 = ElectionExpenditureSchema(
    expenditure_id="EXP_DMK_TN2021",
    party_id="PARTY_TN_DMK",
    election="TN Legislative Assembly 2021",
    reporting_period="FY2021-22",
    expenditure_categories={
        "publicity_and_media": 120000000.0,
        "star_campaigner_travel": 50000000.0,
        "candidate_assistance": 20000000.0
    },
    reported_totals=190000000.0,
    document_id="DOC_EXP_DMK_TN2021"
)
