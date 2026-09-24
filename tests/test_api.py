import pytest
from backend.api.app import create_app

@pytest.fixture
def client():
    app = create_app()
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

def test_health_endpoint(client):
    response = client.get('/health')
    assert response.status_code == 200
    json_data = response.get_json()
    assert json_data['status'] == 'success'
    assert json_data['data']['status'] == 'healthy'

def test_version_endpoint(client):
    response = client.get('/version')
    assert response.status_code == 200
    json_data = response.get_json()
    assert json_data['data']['version'] == '0.1.0'

def test_db_health_endpoint(client):
    response = client.get('/health/db')
    # Can be 200 or 503 depending if the DB is initialized in test environment
    # Since sqlite creates a file dynamically, this usually succeeds.
    assert response.status_code in [200, 503]
    json_data = response.get_json()
    assert 'db_status' in json_data.get('data', {}) or json_data['status'] == 'error'

def test_placeholder_routes(client):
    # Verify that future namespaces are correctly returning 501 Not Implemented
    endpoints = [
        '/api/budget/', '/api/schemes/', '/api/promises/', '/api/news/', 
        '/api/representatives/', '/api/funding/', '/api/claims/', '/api/evidence/'
    ]
    for endpoint in endpoints:
        response = client.get(endpoint)
        assert response.status_code == 501
        assert response.get_json()['message'] == 'Module not implemented yet.'
