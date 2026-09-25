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
