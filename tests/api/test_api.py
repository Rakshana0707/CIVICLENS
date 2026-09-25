def test_health_endpoint(api_client):
    response = api_client.get('/health')
    assert response.status_code == 200
    json_data = response.get_json()
    assert json_data['status'] == 'success'
    assert json_data['data']['status'] == 'healthy'

def test_version_endpoint(api_client):
    response = api_client.get('/version')
    assert response.status_code == 200
    json_data = response.get_json()
    assert json_data['data']['version'] == '0.1.0'

def test_db_health_endpoint(api_client):
    response = api_client.get('/health/db')
    assert response.status_code in [200, 503]
    json_data = response.get_json()
    assert 'db_status' in json_data.get('data', {}) or json_data['status'] == 'error'

def test_placeholder_routes(api_client):
    endpoints = [
        '/api/budget/', '/api/schemes/', '/api/promises/', '/api/news/', 
        '/api/representatives/', '/api/funding/', '/api/claims/', '/api/evidence/'
    ]
    for endpoint in endpoints:
        response = api_client.get(endpoint)
        assert response.status_code == 501
        assert response.get_json()['message'] == 'Module not implemented yet.'
