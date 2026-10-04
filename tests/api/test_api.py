import pytest

def test_health_endpoint(api_client):
    response = api_client.get('/api/health')
    assert response.status_code == 200
    data = response.get_json()
    assert data['status'] == 'success'
    assert data['data']['status'] == 'healthy'

def test_placeholder_routes(api_client):
    # Removed /api/schemes/ since we built real endpoints in Phase 2
    endpoints = [
        '/api/promises/', '/api/news/',
        '/api/representatives/', '/api/funding/', '/api/claims/', '/api/evidence/'
    ]
    for endpoint in endpoints:
        response = api_client.get(endpoint)
        assert response.status_code == 501
