import os
from backend.core.config import Config

def test_config_defaults(monkeypatch):
    """Test that default values are correctly loaded when no env vars are present."""
    monkeypatch.delenv("APP_NAME", raising=False)
    monkeypatch.delenv("ENVIRONMENT", raising=False)
    
    config = Config()
    assert config.APP_NAME == "CivicLens TN"
    assert config.ENVIRONMENT == "development"
    assert config.DEBUG is True
    assert config.DATABASE_URL == "sqlite:///./civiclens.db"

def test_config_overrides(monkeypatch):
    """Test that environment variables successfully override defaults."""
    monkeypatch.setenv("APP_NAME", "CivicLens Production")
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("DEBUG", "False")
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@localhost/db")
    
    config = Config()
    assert config.APP_NAME == "CivicLens Production"
    assert config.ENVIRONMENT == "production"
    assert config.DEBUG is False
    assert config.DATABASE_URL == "postgresql://user:pass@localhost/db"
