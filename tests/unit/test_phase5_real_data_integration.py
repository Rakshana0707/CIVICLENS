"""
End-to-End Integration Tests for Phase 5 Real Datasets.

Verifies:
1. Real database record counts across all Phase 5 tables.
2. Foreign-key provenance links (Contribution -> Donor -> Document -> Party).
3. Real analytical metrics on imported DMK records.
4. API response consistency against the populated database.
"""

import pytest
from backend.database.session import SessionLocal
from backend.models.news import PoliticalParty
from backend.models.funding import (
    FinancialDocument,
    Donor,
    ElectoralTrust,
    Contribution,
    PartyFinancialStatement,
    ValidationIssue
)
from backend.schemas.funding import ContributionSchema
from backend.funding.analytics import FundingAnalyticsEngine
from backend.api.app import create_app


@pytest.fixture
def db_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def client():
    app = create_app()
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


class TestPhase5RealDataIntegration:

    def test_database_record_counts(self, db_session):
        parties_count = db_session.query(PoliticalParty).count()
        docs_count = db_session.query(FinancialDocument).count()
        donors_count = db_session.query(Donor).count()
        contribs_count = db_session.query(Contribution).count()
        stmts_count = db_session.query(PartyFinancialStatement).count()
        trusts_count = db_session.query(ElectoralTrust).count()
        issues_count = db_session.query(ValidationIssue).count()

        assert parties_count >= 80, f"Expected >= 80 parties, got {parties_count}"
        assert docs_count >= 18, f"Expected >= 18 documents, got {docs_count}"
        assert donors_count >= 25, f"Expected >= 25 donors, got {donors_count}"
        assert contribs_count == 28, f"Expected 28 contributions, got {contribs_count}"
        assert stmts_count >= 20, f"Expected >= 20 statements, got {stmts_count}"
        assert trusts_count >= 15, f"Expected >= 15 trusts, got {trusts_count}"
        assert issues_count >= 15, f"Expected >= 15 issues, got {issues_count}"

    def test_provenance_and_foreign_keys(self, db_session):
        contribs = db_session.query(Contribution).all()
        assert len(contribs) == 28

        for c in contribs:
            assert c.party_id in ("PARTY_TN_DMK", "CLTN-P010")
            assert c.donor_id is not None
            assert c.document_id is not None
            if c.amount_inr is not None:
                assert c.amount_inr > 0

            # Trace donor
            donor = db_session.query(Donor).filter(Donor.donor_id == c.donor_id).first()
            assert donor is not None
            assert donor.legal_name == c.donor_name_as_reported

            # Trace document
            doc = db_session.query(FinancialDocument).filter(FinancialDocument.document_id == c.document_id).first()
            assert doc is not None

    def test_real_data_analytics(self, db_session):
        contribs = db_session.query(Contribution).filter(Contribution.party_id == "PARTY_TN_DMK").all()
        c_schemas = [
            ContributionSchema(
                contribution_id=c.contribution_id,
                party_id=c.party_id,
                donor_name_as_reported=c.donor_name_as_reported,
                donor_name_normalized=c.donor_name_normalized,
                amount=c.amount_inr,
                financial_year=c.financial_year,
                contribution_type=c.payment_mode or "EFT",
                document_id=c.document_id
            ) for c in contribs
        ]

        total_metric = FundingAnalyticsEngine.calculate_total_disclosed_contributions(
            "PARTY_TN_DMK", "FY2024-25", c_schemas, ["DOC_MYNETA_DMK_P1"]
        )
        assert total_metric.value == 4324967713.0  # ₹432.50 Cr across all sample rows

        concentration = FundingAnalyticsEngine.calculate_donor_concentration(
            "PARTY_TN_DMK", "FY2024-25", c_schemas, ["DOC_MYNETA_DMK_P1"]
        )
        assert concentration.value["gini_coefficient"] > 0.30
        assert concentration.value["hhi_index"] > 0.40
        assert concentration.value["total_donors_count"] == 27

        top_donors = FundingAnalyticsEngine.calculate_top_contributors(
            "PARTY_TN_DMK", "FY2024-25", c_schemas, ["DOC_MYNETA_DMK_P1"], top_n=3
        )
        assert len(top_donors.value) == 3
        assert "Collection through Distribution of Donation Tickets" in top_donors.value[0]["donor_name"]

    def test_api_serving_real_data(self, client):
        # 1. Parties endpoint serves registered parties
        res = client.get("/api/funding/parties")
        assert res.status_code == 200
        parties = res.get_json()["data"]["parties"]
        assert len(parties) >= 80

        # 2. Real contribution summary
        res_summary = client.get("/api/funding/contributions/summary?party_id=PARTY_TN_DMK")
        assert res_summary.status_code == 200
        data = res_summary.get_json()["data"]
        assert data["total_records"] == 28
        assert data["total_disclosed_inr"] == 4324967713.0

        # 3. Documents endpoint
        res_docs = client.get("/api/funding/documents")
        assert res_docs.status_code == 200
        docs = res_docs.get_json()["data"]["documents"]
        assert len(docs) >= 18
