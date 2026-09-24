import pytest
from backend.api.app import create_app
from backend.core.config import config
from sqlalchemy.exc import SQLAlchemyError

def test_api_unexpected_error_debug(monkeypatch):
    monkeypatch.setattr(config, "DEBUG", True)
    app = create_app()
    app.config['TESTING'] = True
    
    @app.route("/crash")
    def crash():
        raise ValueError("Oops!")
        
    with app.test_client() as client:
        res = client.get("/crash")
        assert res.status_code == 500
        data = res.get_json()
        assert "Oops!" in data["details"] # Stack trace included

def test_api_unexpected_error_prod(monkeypatch):
    monkeypatch.setattr(config, "DEBUG", False)
    app = create_app()
    app.config['TESTING'] = True
    
    @app.route("/crash")
    def crash():
        raise ValueError("Oops!")
        
    with app.test_client() as client:
        res = client.get("/crash")
        assert res.status_code == 500
        data = res.get_json()
        assert data.get("details") is None # Stack trace hidden for safety

def test_api_database_error(monkeypatch):
    monkeypatch.setattr(config, "DEBUG", False)
    app = create_app()
    app.config['TESTING'] = True
    
    @app.route("/db_crash")
    def db_crash():
        raise SQLAlchemyError("DB connection dropped randomly")
        
    with app.test_client() as client:
        res = client.get("/db_crash")
        assert res.status_code == 503
        data = res.get_json()
        assert data["message"] == "A database error occurred."
        assert data.get("details") is None # Safe database logging
