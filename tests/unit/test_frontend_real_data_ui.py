"""
Unit tests for Phase 3.24 — Real Manifesto Promise Tracker UI.
Verifies API client integration with real dataset, non-adversarial status rendering,
structured detail flow requirements, and disclaimers.
"""
import pytest
import importlib
from unittest.mock import patch, Mock
from backend.api.app import create_app

# Dynamically import module with digit prefix in filename
promises_page = importlib.import_module("frontend.pages.2_Political_Promises")
render_status_badge = promises_page.render_status_badge
STATUS_CONFIG = promises_page.STATUS_CONFIG


def test_status_badge_non_adversarial_rendering():
    """Verify status badges render non-adversarial text and avoid 'Not Implemented' claims."""
    # Test no_evidence_found
    badge_no_ev = render_status_badge("no_evidence_found")
    assert "No Evidence Found" in badge_no_ev
    assert "Not Implemented" not in badge_no_ev

    # Test unclear
    badge_unclear = render_status_badge("unclear")
    assert "Insufficient Evidence" in badge_unclear
    assert "Not Implemented" not in badge_unclear

    # Test implemented
    badge_imp = render_status_badge("implemented")
    assert "Implemented" in badge_imp

    # Test policy_action
    badge_pol = render_status_badge("policy_action")
    assert "Policy Action" in badge_pol


def test_real_database_api_promises_integration():
    """Test Flask backend endpoints serving real promises from civiclens.db."""
    app = create_app()
    client = app.test_client()

    # 1. Get promises
    res = client.get('/api/promises/?page=1&limit=10')
    assert res.status_code == 200
    json_data = res.get_json()
    assert json_data["status"] == "success"
    data = json_data["data"]
    assert data["total"] == 1065
    assert len(data["items"]) == 10

    # Verify first promise structure
    first_p = data["items"][0]
    assert "promise_id" in first_p
    assert "party" in first_p
    assert "original_text" in first_p
    assert "current_status" in first_p
    assert "primary_category" in first_p


def test_promise_detail_and_assessment_endpoints():
    """Test detail endpoints required by the 7-step detail flow."""
    app = create_app()
    client = app.test_client()

    # Get a real promise ID
    res = client.get('/api/promises/?page=1&limit=1')
    p_id = res.get_json()["data"]["items"][0]["promise_id"]

    # 1. Detail
    res_det = client.get(f'/api/promises/{p_id}')
    assert res_det.status_code == 200
    det_data = res_det.get_json()["data"]
    assert det_data["promise_id"] == p_id
    assert "original_text" in det_data

    # 2. Scheme matches
    res_sm = client.get(f'/api/promises/{p_id}/scheme-matches')
    assert res_sm.status_code == 200
    assert "scheme_matches" in res_sm.get_json()["data"]

    # 3. Evidence matches
    res_ev = client.get(f'/api/promises/{p_id}/evidence-matches')
    assert res_ev.status_code == 200
    assert "evidence_matches" in res_ev.get_json()["data"]

    # 4. Assessment
    res_ass = client.get(f'/api/promises/{p_id}/assessment')
    assert res_ass.status_code == 200
    ass_data = res_ass.get_json()["data"]
    assert "status" in ass_data
    assert "confidence" in ass_data
    assert "explanation" in ass_data
