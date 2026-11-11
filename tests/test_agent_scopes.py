"""File-based agent API scope separation (offline RBAC signal)."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from ilearn.core.scopes import assert_agent_scope, load_agent_scopes, reset_scopes_cache


def test_default_scopes_separate_curriculum_and_practice(tmp_path: Path, monkeypatch):
    cfg = tmp_path / "agent_scopes.yaml"
    cfg.write_text(
        """
agents:
  curriculum:
    scopes: ["curriculum:retrieve"]
    api_key_env: ILEARN_SCOPE_CURRICULUM_KEY
  practice:
    scopes: ["practice:grade"]
    api_key_env: ILEARN_SCOPE_PRACTICE_KEY
enforcement: hard
""".strip(),
        encoding="utf-8",
    )
    monkeypatch.setenv("ILEARN_AGENT_SCOPES_PATH", str(cfg))
    reset_scopes_cache()
    scopes = load_agent_scopes()
    assert "curriculum:retrieve" in scopes["curriculum"]["scopes"]
    assert "practice:grade" in scopes["practice"]["scopes"]
    assert "practice:grade" not in scopes["curriculum"]["scopes"]
    reset_scopes_cache()


def test_assert_scope_rejects_cross_agent_scope(tmp_path: Path, monkeypatch):
    cfg = tmp_path / "agent_scopes.yaml"
    cfg.write_text(
        """
agents:
  curriculum:
    scopes: ["curriculum:retrieve"]
  practice:
    scopes: ["practice:grade"]
enforcement: hard
""".strip(),
        encoding="utf-8",
    )
    monkeypatch.setenv("ILEARN_AGENT_SCOPES_PATH", str(cfg))
    reset_scopes_cache()
    assert_agent_scope("curriculum", "curriculum:retrieve")
    with pytest.raises(PermissionError):
        assert_agent_scope("curriculum", "practice:grade")
    reset_scopes_cache()


def test_assert_scope_enforces_api_key_when_configured(tmp_path: Path, monkeypatch):
    cfg = tmp_path / "agent_scopes.yaml"
    cfg.write_text(
        """
agents:
  practice:
    scopes: ["practice:grade"]
    api_key_env: ILEARN_SCOPE_PRACTICE_KEY
enforcement: hard
""".strip(),
        encoding="utf-8",
    )
    monkeypatch.setenv("ILEARN_AGENT_SCOPES_PATH", str(cfg))
    monkeypatch.setenv("ILEARN_SCOPE_PRACTICE_KEY", "practice-secret")
    reset_scopes_cache()
    with pytest.raises(PermissionError):
        assert_agent_scope("practice", "practice:grade", api_key="wrong")
    assert_agent_scope("practice", "practice:grade", api_key="practice-secret")
    reset_scopes_cache()
