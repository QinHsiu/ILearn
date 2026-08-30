"""Tests for rate limiter middleware."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from ilearn.api.app import create_app
from ilearn.core.settings import clear_settings_cache

PILOT = Path(__file__).resolve().parents[1] / "data" / "pilot"


def test_rate_limit_returns_429(tmp_path, monkeypatch):
    monkeypatch.setenv("ILEARN_RATE_LIMIT_ENABLED", "1")
    monkeypatch.setenv("ILEARN_RATE_LIMIT_MAX_REQUESTS", "3")
    monkeypatch.setenv("ILEARN_RATE_LIMIT_WINDOW_SECONDS", "60")
    clear_settings_cache()
    client = TestClient(
        create_app(sessions_dir=tmp_path, pilot_data_dir=PILOT, llm=None)
    )
    ok = 0
    blocked = 0
    for _ in range(5):
        response = client.get("/docs")
        if response.status_code == 429:
            blocked += 1
        else:
            ok += 1
            assert "X-RateLimit-Remaining" in response.headers
    assert ok == 3
    assert blocked == 2
    clear_settings_cache()


def test_rate_limit_can_disable(tmp_path, monkeypatch):
    monkeypatch.setenv("ILEARN_RATE_LIMIT_ENABLED", "0")
    monkeypatch.setenv("ILEARN_RATE_LIMIT_MAX_REQUESTS", "1")
    clear_settings_cache()
    client = TestClient(
        create_app(sessions_dir=tmp_path, pilot_data_dir=PILOT, llm=None)
    )
    for _ in range(3):
        assert client.get("/docs").status_code != 429
    clear_settings_cache()
