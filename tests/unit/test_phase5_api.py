"""
Unit tests for Phase 5.9 Political Funding REST API Endpoints.

Verifies:
1. List parties endpoint (`/api/funding/parties`).
2. Party financial profile endpoint (`/api/funding/parties/<party_id>/profile`).
3. Contribution summary endpoint (`/api/funding/contributions/summary`).
4. Income and expenditure endpoint (`/api/funding/metrics/income-expenditure`).
5. Electoral trust filings endpoint (`/api/funding/electoral-trusts`).
6. Election campaign expenditure endpoint (`/api/funding/election-expenditure`).
7. Anomaly flags endpoint (`/api/funding/anomalies`).
8. Cross-validation discrepancies endpoint (`/api/funding/cross-validation`).
9. Source documents registry endpoint (`/api/funding/documents`).
10. Official sources list endpoint (`/api/funding/sources`).
"""

import pytest
from backend.api.app import create_app


@pytest.fixture
def client():
    app = create_app()
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


class TestFundingAPI:

    def test_list_parties(self, client):
        res = client.get("/api/funding/parties")
        assert res.status_code == 200
        json_data = res.get_json()
        assert json_data["status"] == "success"
        data = json_data["data"]
        assert "parties" in data
        assert "available_financial_years" in data
        assert len(data["parties"]) > 0

    def test_get_party_profile(self, client):
        res = client.get("/api/funding/parties/PARTY_TN_DMK/profile?financial_year=FY2021-22")
        assert res.status_code == 200
        json_data = res.get_json()
        assert json_data["status"] == "success"
        data = json_data["data"]
        assert data["party_id"] == "PARTY_TN_DMK"
        assert "total_income_reported" in data
        assert "total_disclosed_contributions" in data
        assert "metadata" in data

    def test_get_contribution_summary(self, client):
        res = client.get("/api/funding/contributions/summary?party_id=PARTY_TN_DMK&financial_year=FY2021-22")
        assert res.status_code == 200
        json_data = res.get_json()
        assert json_data["status"] == "success"
        data = json_data["data"]
        assert "total_disclosed_inr" in data
        assert "size_distribution" in data
        assert "concentration" in data
        assert "top_contributors" in data

    def test_get_income_expenditure_metrics(self, client):
        res = client.get("/api/funding/metrics/income-expenditure?party_id=PARTY_TN_DMK&financial_year=FY2021-22")
        assert res.status_code == 200
        json_data = res.get_json()
        assert json_data["status"] == "success"
        data = json_data["data"]
        assert "total_income_inr" in data
        assert "total_expenditure_inr" in data
        assert "surplus_ratio_percentage" in data

    def test_get_electoral_trusts(self, client):
        res = client.get("/api/funding/electoral-trusts?party_id=PARTY_TN_DMK&financial_year=FY2021-22")
        assert res.status_code == 200
        json_data = res.get_json()
        assert json_data["status"] == "success"
        data = json_data["data"]
        assert "total_trust_grants_inr" in data
        assert "reports" in data

    def test_get_election_expenditure(self, client):
        res = client.get("/api/funding/election-expenditure?party_id=PARTY_TN_DMK&election_name=TN%20Legislative%20Assembly%202021")
        assert res.status_code == 200
        json_data = res.get_json()
        assert json_data["status"] == "success"
        data = json_data["data"]
        assert "campaign_expenditure_inr" in data
        assert "expenditure_categories" in data

    def test_get_anomalies(self, client):
        res = client.get("/api/funding/anomalies?party_id=PARTY_TN_DMK&financial_year=FY2021-22")
        assert res.status_code == 200
        json_data = res.get_json()
        assert json_data["status"] == "success"
        data = json_data["data"]
        assert "anomalies" in data
        assert len(data["anomalies"]) > 0

    def test_get_cross_validation(self, client):
        res = client.get("/api/funding/cross-validation?party_id=PARTY_TN_DMK&financial_year=FY2021-22")
        assert res.status_code == 200
        json_data = res.get_json()
        assert json_data["status"] == "success"
        data = json_data["data"]
        assert "comparison_records" in data
        assert len(data["comparison_records"]) > 0

    def test_get_documents(self, client):
        res = client.get("/api/funding/documents?party_id=PARTY_TN_DMK&financial_year=FY2021-22")
        assert res.status_code == 200
        json_data = res.get_json()
        assert json_data["status"] == "success"
        data = json_data["data"]
        assert "documents" in data
        assert len(data["documents"]) > 0

    def test_get_sources(self, client):
        res = client.get("/api/funding/sources")
        assert res.status_code == 200
        json_data = res.get_json()
        assert json_data["status"] == "success"
        data = json_data["data"]
        assert "sources" in data
        assert len(data["sources"]) > 0
