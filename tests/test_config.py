import os
from pathlib import Path
from backend.core.config import Config

def test_configuration_defaults():
    """Test that default values are correctly assigned when env vars are missing."""
    config = Config()
    
    assert config.APP_NAME == "CivicLens TN"
    assert config.ENV == "development"
    assert config.DEBUG is True
    assert config.API_HOST == "0.0.0.0"
    assert config.API_PORT == 5000
    assert config.FRONTEND_URL == "http://localhost:3000"
    assert config.LOG_LEVEL == "INFO"
    
    # Path validations
    assert isinstance(config.DATA_DIR, Path)
    assert isinstance(config.RAW_DATA_DIR, Path)
    assert isinstance(config.PROCESSED_DATA_DIR, Path)
    assert isinstance(config.MODEL_DIR, Path)

def test_configuration_env_override(monkeypatch):
    """Test that configuration properly prioritizes environment variables."""
    monkeypatch.setenv("APP_NAME", "Test CivicLens")
    monkeypatch.setenv("ENV", "testing")
    monkeypatch.setenv("DEBUG", "False")
    monkeypatch.setenv("API_PORT", "8080")
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")
    
    # Instantiate a new Config to capture the monkeypatched environment
    config = Config()
    
    assert config.APP_NAME == "Test CivicLens"
    assert config.ENV == "testing"
    assert config.DEBUG is False
    assert config.API_PORT == 8080
    assert config.LOG_LEVEL == "DEBUG"
