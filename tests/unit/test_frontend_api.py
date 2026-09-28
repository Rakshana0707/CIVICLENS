import pytest
import requests
from unittest.mock import patch, Mock
from frontend.services.api import APIClient

@patch("frontend.services.api.requests.get")
def test_api_client_health_success(mock_get):
    mock_response = Mock()
    mock_response.ok = True
    mock_response.json.return_value = {"status": "success", "data": {"status": "healthy"}}
    mock_get.return_value = mock_response
    
    client = APIClient(base_url="http://test-server")
    success, data = client.get_health()
    
    assert success is True
    assert data["status"] == "healthy"
    mock_get.assert_called_once_with("http://test-server/health", timeout=5)

@patch("frontend.services.api.requests.get")
def test_api_client_health_failure(mock_get):
    mock_get.side_effect = requests.exceptions.ConnectionError("Failed to connect to localhost:5000")
    
    client = APIClient(base_url="http://test-server")
    success, data = client.get_health()
    
    assert success is False
    assert "Connection failed" in data["message"]

@patch("frontend.services.api.requests.get")
def test_api_client_bad_json(mock_get):
    mock_response = Mock()
    mock_response.ok = False
    mock_response.json.side_effect = ValueError("No JSON object could be decoded")
    mock_get.return_value = mock_response
    
    client = APIClient(base_url="http://test-server")
    success, data = client.get_health()
    
    assert success is False
    assert "Invalid JSON response" in data["message"]

@patch("frontend.services.api.requests.get")
def test_api_client_budget_years(mock_get):
    mock_response = Mock()
    mock_response.ok = True
    mock_response.json.return_value = {"status": "success", "data": ["2024-25"]}
    mock_get.return_value = mock_response
    
    client = APIClient(base_url="http://test-server")
    success, data = client.get_budget_years()
    
    assert success is True
    assert "2024-25" in data

@patch("frontend.services.api.requests.get")
def test_api_client_budget_records(mock_get):
    mock_response = Mock()
    mock_response.ok = True
    mock_response.json.return_value = {"status": "success", "data": {"records": [], "total_count": 0}}
    mock_get.return_value = mock_response
    
    client = APIClient(base_url="http://test-server")
    success, data = client.get_budget_records(filters={"financial_year": "2024-25"})
    
    assert success is True
    assert data["total_count"] == 0
    mock_get.assert_called_once_with("http://test-server/api/budget/records", params={"skip": 0, "limit": 50, "financial_year": "2024-25"}, timeout=10)

@patch("frontend.services.api.requests.get")
def test_api_client_budget_trend(mock_get):
    mock_response = Mock()
    mock_response.ok = True
    mock_response.json.return_value = {"status": "success", "data": {"2024-25": {"total": 1000, "percentage_change": 10.5}}}
    mock_get.return_value = mock_response
    
    client = APIClient(base_url="http://test-server")
    success, data = client.get_budget_trend(budget_stage="budget_estimate", department_id=1)
    
    assert success is True
    assert "2024-25" in data
    mock_get.assert_called_once_with("http://test-server/api/budget/analysis/trend", params={"budget_stage": "budget_estimate", "department_id": 1}, timeout=10)

@patch("frontend.services.api.requests.get")
def test_api_client_scheme_trends(mock_get):
    mock_response = Mock()
    mock_response.ok = True
    mock_response.json.return_value = {"status": "success", "data": {"Scholarships": {"available_stages": [], "yearly_trend": {}}}}
    mock_get.return_value = mock_response
    
    client = APIClient(base_url="http://test-server")
    success, data = client.get_scheme_trends(budget_stage="budget_estimate", department_id=1)
    
    assert success is True
    assert "Scholarships" in data
    mock_get.assert_called_once_with("http://test-server/api/budget/analysis/scheme-trends", params={"budget_stage": "budget_estimate", "department_id": 1}, timeout=10)
