"""
CIVICLENS TN — Phase 8.9 Unit Tests: Civic Issue Intelligence Dashboard.
========================================================================

Verifies:
1. APIClient civic endpoint wrappers and error handling.
2. Fixture data integrity, DPDPA PII redaction, and non-causal caveats.
3. Epistemic status separation (marked_resolved vs independently_verified_resolved).
4. Guarded anomaly criteria (N >= 30).
5. Frontend badge renderers, search, and multi-facet filtering logic.
"""

import re
import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime

from frontend.services.api import APIClient
from frontend.pages.eight_civic_fixtures import (
    FIXTURE_CATEGORIES,
    FIXTURE_AREAS,
    FIXTURE_DEPARTMENTS,
    FIXTURE_ISSUES,
    FIXTURE_CLUSTERS,
    FIXTURE_TRENDS,
    FIXTURE_SOURCE_DOCUMENTS,
)
from frontend.pages.eight_civic_dashboard_helper import (
    render_status_badge,
    render_verification_badge,
    render_severity_badge,
    STATUS_LABELS,
    STATUS_COLORS,
)


class TestAPIClientCivicEndpoints:
    """Tests for Phase 8 APIClient methods."""

    @pytest.fixture
    def client(self):
        return APIClient(base_url="http://testserver:5000")

    @patch("requests.get")
    def test_get_civic_issues_success(self, mock_get, client):
        mock_response = MagicMock()
        mock_response.ok = True
        mock_response.json.return_value = {
            "status": "success",
            "data": {"issues": [{"id": "CIVIC-001", "title": "Potholes"}], "total": 1}
        }
        mock_get.return_value = mock_response

        ok, data = client.get_civic_issues(params={"district": "Chennai"})
        assert ok is True
        assert len(data["issues"]) == 1
        assert data["issues"][0]["id"] == "CIVIC-001"
        mock_get.assert_called_once_with(
            "http://testserver:5000/api/civic/issues",
            params={"district": "Chennai"},
            timeout=10
        )

    @patch("requests.get")
    def test_get_civic_issue_detail(self, mock_get, client):
        mock_response = MagicMock()
        mock_response.ok = True
        mock_response.json.return_value = {
            "status": "success",
            "data": {"id": "CIVIC-001", "title": "Potholes Detail"}
        }
        mock_get.return_value = mock_response

        ok, data = client.get_civic_issue_detail("CIVIC-001")
        assert ok is True
        assert data["id"] == "CIVIC-001"

    @patch("requests.get")
    def test_get_civic_categories(self, mock_get, client):
        mock_response = MagicMock()
        mock_response.ok = True
        mock_response.json.return_value = {
            "status": "success",
            "data": {"categories": [{"id": "pot_holes", "name": "Potholes"}]}
        }
        mock_get.return_value = mock_response

        ok, data = client.get_civic_categories()
        assert ok is True
        assert len(data["categories"]) == 1

    @patch("requests.get")
    def test_get_civic_areas(self, mock_get, client):
        mock_response = MagicMock()
        mock_response.ok = True
        mock_response.json.return_value = {
            "status": "success",
            "data": {"areas": [{"id": "AREA-CHN", "name": "Chennai"}]}
        }
        mock_get.return_value = mock_response

        ok, data = client.get_civic_areas()
        assert ok is True
        assert len(data["areas"]) == 1

    @patch("requests.get")
    def test_get_civic_departments(self, mock_get, client):
        mock_response = MagicMock()
        mock_response.ok = True
        mock_response.json.return_value = {
            "status": "success",
            "data": {"departments": [{"id": "DEPT-GCC", "name": "GCC Works"}]}
        }
        mock_get.return_value = mock_response

        ok, data = client.get_civic_departments()
        assert ok is True
        assert len(data["departments"]) == 1

    @patch("requests.get")
    def test_get_civic_department_summary(self, mock_get, client):
        mock_response = MagicMock()
        mock_response.ok = True
        mock_response.json.return_value = {
            "status": "success",
            "data": {"department_id": "DEPT-GCC", "sla_compliance_rate": 85.0}
        }
        mock_get.return_value = mock_response

        ok, data = client.get_civic_department_summary("DEPT-GCC")
        assert ok is True
        assert data["sla_compliance_rate"] == 85.0

    @patch("requests.get")
    def test_get_civic_responses(self, mock_get, client):
        mock_response = MagicMock()
        mock_response.ok = True
        mock_response.json.return_value = {
            "status": "success",
            "data": {"responses": [{"id": "R1", "response_type": "ACTION_TAKEN_REPORT"}]}
        }
        mock_get.return_value = mock_response

        ok, data = client.get_civic_responses("CIVIC-001")
        assert ok is True
        assert len(data["responses"]) == 1

    @patch("requests.get")
    def test_get_civic_evidence(self, mock_get, client):
        mock_response = MagicMock()
        mock_response.ok = True
        mock_response.json.return_value = {
            "status": "success",
            "data": {"evidence": [{"id": "EV1", "evidence_type": "GEOTAGGED_INSPECTION_PHOTO"}]}
        }
        mock_get.return_value = mock_response

        ok, data = client.get_civic_evidence("CIVIC-001")
        assert ok is True
        assert len(data["evidence"]) == 1

    @patch("requests.get")
    def test_get_civic_clusters(self, mock_get, client):
        mock_response = MagicMock()
        mock_response.ok = True
        mock_response.json.return_value = {
            "status": "success",
            "data": {"clusters": [{"cluster_id": "C1", "chronic_recurrence_rate": 40.0}]}
        }
        mock_get.return_value = mock_response

        ok, data = client.get_civic_clusters()
        assert ok is True
        assert len(data["clusters"]) == 1

    @patch("requests.get")
    def test_get_civic_trends(self, mock_get, client):
        mock_response = MagicMock()
        mock_response.ok = True
        mock_response.json.return_value = {
            "status": "success",
            "data": {"reporting_period": "2026", "time_series": []}
        }
        mock_get.return_value = mock_response

        ok, data = client.get_civic_trends()
        assert ok is True
        assert data["reporting_period"] == "2026"

    @patch("requests.get")
    def test_get_civic_source_documents(self, mock_get, client):
        mock_response = MagicMock()
        mock_response.ok = True
        mock_response.json.return_value = {
            "status": "success",
            "data": {"documents": [{"doc_id": "DOC-1"}]}
        }
        mock_get.return_value = mock_response

        ok, data = client.get_civic_source_documents()
        assert ok is True
        assert len(data["documents"]) == 1

    @patch("requests.get")
    def test_get_civic_cross_phase(self, mock_get, client):
        mock_response = MagicMock()
        mock_response.ok = True
        mock_response.json.return_value = {
            "status": "success",
            "data": {"cross_phase_links": [{"target_phase": "PHASE_1_2_BUDGET_SCHEME"}]}
        }
        mock_get.return_value = mock_response

        ok, data = client.get_civic_cross_phase("CIVIC-001")
        assert ok is True
        assert len(data["cross_phase_links"]) == 1

    @patch("requests.get")
    def test_civic_network_failure(self, mock_get, client):
        import requests
        mock_get.side_effect = requests.exceptions.ConnectionError("Connection refused")
        ok, res = client.get_civic_issues()
        assert ok is False
        assert "Connection refused" in res["message"]


class TestCivicFixturesIntegrity:
    """Verifies statutory compliance and integrity of Phase 8.9 fixtures."""

    def test_fixture_categories_count(self):
        assert len(FIXTURE_CATEGORIES) >= 12
        category_ids = {c["id"] for c in FIXTURE_CATEGORIES}
        assert "pot_holes_and_road_damage" in category_ids
        assert "drinking_water_contamination_or_shortage" in category_ids
        assert "sanitation_and_solid_waste" in category_ids
        assert "storm_water_drainage_and_flooding" in category_ids

    def test_fixture_issues_label_and_pii_redaction(self):
        phone_pattern = re.compile(r"\b[6-9]\d{9}\b")
        email_pattern = re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+")

        for issue in FIXTURE_ISSUES:
            # Must have [FIXTURE] label
            assert "[FIXTURE]" in issue["title"]

            # Must NOT leak 10-digit Indian mobile numbers in description
            desc = issue["description"]
            assert not phone_pattern.search(desc), f"Potential phone leak in {issue['id']}"
            assert not email_pattern.search(desc), f"Potential email leak in {issue['id']}"

    def test_distinct_epistemic_statuses(self):
        statuses = {i["status"] for i in FIXTURE_ISSUES}
        assert "marked_resolved" in statuses
        assert "independently_verified_resolved" in statuses

        # Ensure verified_resolved issues have empirical evidence attached
        for issue in FIXTURE_ISSUES:
            if issue["status"] == "independently_verified_resolved":
                assert issue["verification_status"] == "VERIFIED_RESOLVED"
                assert len(issue["evidence"]) > 0

    def test_anti_causality_and_non_defamation_notes(self):
        # Check cross phase links to constituencies
        for issue in FIXTURE_ISSUES:
            for link in issue.get("cross_phase_links", []):
                if link.get("entity_type") == "CONSTITUENCY":
                    # Must contain non-causal note in provenance
                    prov = link.get("provenance", "")
                    assert any(keyword in prov.lower() for keyword in ["non-causal", "no personal fault", "context only"]), (
                        f"Constituency link in {issue['id']} lacks non-causality disclaimer: {prov}"
                    )

    def test_guarded_anomalies_criteria(self):
        # Anomaly alerts must have sample size >= 30
        for anom in FIXTURE_TRENDS.get("guarded_anomalies", []):
            assert anom["sample_size"] >= 30
            assert anom["sample_size_valid"] is True
            assert anom["z_score"] >= 2.5
            assert "Indicator requiring administrative" in anom["interpretation"]


class TestDashboardHelpersAndFiltering:
    """Verifies UI formatting helpers and filtering mechanics."""

    def test_render_status_badge(self):
        html_verified = render_status_badge("independently_verified_resolved")
        assert "Independently Verified Resolved" in html_verified
        assert STATUS_COLORS["independently_verified_resolved"] in html_verified

        html_marked = render_status_badge("marked_resolved")
        assert "Administratively Closed by Department" in html_marked
        assert STATUS_COLORS["marked_resolved"] in html_marked

    def test_render_verification_badge(self):
        html = render_verification_badge("VERIFIED_RESOLVED")
        assert "Verified Resolved" in html

        html_def = render_verification_badge("DEFICIENCY_OBSERVED")
        assert "Deficiency Observed" in html_def

    def test_render_severity_badge(self):
        html_crit = render_severity_badge("CRITICAL")
        assert "CRITICAL" in html_crit

    def test_filter_by_category(self):
        target_cat = "Potholes & Road Damage"
        filtered = [i for i in FIXTURE_ISSUES if i.get("category_name") == target_cat]
        assert len(filtered) >= 1
        assert all(i.get("category_name") == target_cat for i in filtered)

    def test_filter_by_district(self):
        filtered = [i for i in FIXTURE_ISSUES if i.get("district") == "Chennai"]
        assert len(filtered) >= 1
        assert all(i.get("district") == "Chennai" for i in filtered)

    def test_filter_by_status(self):
        filtered = [i for i in FIXTURE_ISSUES if i.get("status") == "independently_verified_resolved"]
        assert len(filtered) >= 1
        assert all(i.get("status") == "independently_verified_resolved" for i in filtered)

    def test_filter_by_date_range(self):
        start = datetime(2026, 8, 1).date()
        end = datetime(2026, 8, 31).date()
        filtered = []
        for i in FIXTURE_ISSUES:
            sub = datetime.strptime(i["submission_date"], "%Y-%m-%d").date()
            if start <= sub <= end:
                filtered.append(i)
        assert len(filtered) >= 1

    def test_filter_by_search_query(self):
        q = "anna salai"
        filtered = [i for i in FIXTURE_ISSUES if q in i["title"].lower() or q in i["description"].lower()]
        assert len(filtered) == 1
        assert filtered[0]["id"] == "CIVIC-2026-CHN-001"
