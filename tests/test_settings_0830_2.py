"""Tests for ILearnSettings."""

from __future__ import annotations

import os

from ilearn.core.settings import clear_settings_cache, get_settings, load_settings


def test_load_settings_defaults(monkeypatch):
    for key in list(os.environ):
        if key.startswith("ILEARN_"):
            monkeypatch.delenv(key, raising=False)
    clear_settings_cache()
    settings = load_settings()
    assert settings.mastery_threshold == 0.7
    assert settings.rate_limit_max_requests == 100
    assert settings.llm_model == "gpt-4o-mini"


def test_get_settings_reads_env(monkeypatch):
    monkeypatch.setenv("ILEARN_MASTERY_THRESHOLD", "0.55")
    monkeypatch.setenv("ILEARN_RATE_LIMIT_ENABLED", "0")
    clear_settings_cache()
    settings = get_settings()
    assert settings.mastery_threshold == 0.55
    assert settings.rate_limit_enabled is False
    clear_settings_cache()
