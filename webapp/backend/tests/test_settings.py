import logging

import pytest
from vball_app import startup
from vball_app.settings import Settings


def test_settings_from_the_environment(tmp_path):
    s = Settings.from_env(
        {"VBALL_WEBAPP_DATA": str(tmp_path), "VBALL_CORS_ORIGINS": "http://a, http://b,", "VBALL_LOG_LEVEL": "debug"}
    )
    assert s.data == tmp_path and s.cors_origins == ("http://a", "http://b") and s.log_level == "DEBUG"
    d = Settings.from_env({})
    assert d.data.name == "data" and "http://localhost:5173" in d.cors_origins and d.log_level == "INFO"
    with pytest.raises(ValueError, match="VBALL_LOG_LEVEL"):
        Settings.from_env({"VBALL_LOG_LEVEL": "loud"})


def test_startup_logs_missing_and_changed_models(monkeypatch, caplog):
    monkeypatch.setattr(startup.manifest, "check", lambda: {"court_kpt.pt": "changed", "yolo26s.pt": "missing"})
    with caplog.at_level(logging.WARNING, logger="vball_app.startup"):
        assert startup.check_models() == {"court_kpt.pt": "changed", "yolo26s.pt": "missing"}
    levels = {r.getMessage().split()[1]: r.levelname for r in caplog.records}
    assert levels == {"court_kpt.pt": "ERROR", "yolo26s.pt": "WARNING"}


def test_api_start_runs_the_model_check(monkeypatch):
    from fastapi.testclient import TestClient
    from vball_app import main

    calls = []
    monkeypatch.setattr(main, "check_models", lambda: calls.append(1) or {})
    with TestClient(main.app) as client:
        assert client.get("/health").json() == {"status": "ok"}
    assert calls == [1]
