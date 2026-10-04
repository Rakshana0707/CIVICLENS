import os
import pytest
from backend.core.config import Config

def test_config_defaults(monkeypatch):
    '''Test that default values are correctly loaded when no env vars are present.'''
    monkeypatch.delenv("APP_NAME", raising=False)
    monkeypatch.delenv("ENV", raising=False)
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("DEBUG", raising=False)

    config = Config()
    assert config.APP_NAME == "CivicLens TN"
    assert config.ENV == "development"

def test_config_overrides(monkeypatch):
    '''Test that environment variables override defaults.'''
    monkeypatch.setenv("APP_NAME", "Test App")
    monkeypatch.setenv("ENV", "production")
    monkeypatch.setenv("DEBUG", "false")

    config = Config()
    assert config.APP_NAME == "Test App"
    assert config.ENV == "production"
