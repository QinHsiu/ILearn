"""Edition 0903_7: safe summary fallbacks and resilient exports."""

from __future__ import annotations

from fastapi.testclient import TestClient

from ilearn.api.app import create_app
from ilearn.core.audience_summary import (
    build_parent_summary_safe,
    build_teacher_summary_safe,
    default_parent_summary,
)


def test_build_parent_summary_safe_returns_default_when_session_missing():
    summary = build_parent_summary_safe(None)
    assert summary.child_name == "孩子"
    assert summary.weak_skills == ["暂未检测到薄弱点"]
    assert "测评" in summary.daily_practice_tips[0]


def test_build_teacher_summary_safe_returns_default_when_session_missing():
    summary = build_teacher_summary_safe(None)
    assert summary.class_name == "当前班级"
    assert summary.student_count == 0


def test_parent_summary_api_degrades_for_missing_session(tmp_path):
    client = TestClient(create_app(sessions_dir=tmp_path, llm=None))
    response = client.get("/sessions/missing-id/summary/parent")
    assert response.status_code == 200
    payload = response.json()
    assert payload["child_name"] == default_parent_summary().child_name
    assert payload["weak_skills"] == default_parent_summary().weak_skills
