"""PR #03 acceptance: enhanced API query branches and report export."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from ilearn.api.app import create_app
from ilearn.core.enhanced_flags import clear_enhanced_flag_cache
from ilearn.core.enhanced_session import set_enhanced_profile
from ilearn.core.models.enhanced_profile import StudentFiveDimProfile
from ilearn.storage.sessions import SessionStore

PILOT_DATA = Path(__file__).resolve().parents[1] / "data" / "pilot"


@pytest.fixture(autouse=True)
def _reset_flags(monkeypatch):
    for name in (
        "ILEARN_ENABLE_ENHANCED_PROFILE",
        "ILEARN_ENABLE_ENHANCED_AGENTS",
        "ILEARN_ENABLE_ENHANCED_API",
    ):
        monkeypatch.delenv(name, raising=False)
    clear_enhanced_flag_cache()
    yield
    clear_enhanced_flag_cache()


def _client(tmp_path):
    return TestClient(
        create_app(
            sessions_dir=tmp_path / "sessions",
            pilot_data_dir=PILOT_DATA,
            relationships_path=tmp_path / "relationships.json",
            llm=None,
        )
    )


def _seed_enhanced_session(tmp_path, monkeypatch) -> str:
    monkeypatch.setenv("ILEARN_ENABLE_ENHANCED_PROFILE", "1")
    clear_enhanced_flag_cache()
    client = _client(tmp_path)
    session_id = client.post(
        "/sessions",
        json={"region": "北京", "grade": 5, "age": 11, "nickname": "小明"},
    ).json()["session_id"]
    store = SessionStore(tmp_path / "sessions")
    session = store.load(session_id)
    profile = StudentFiveDimProfile(student_id=session_id)
    profile.cognitive.knowledge_mastery = {"kp_frac": 0.3, "kp_dec": 0.9}
    profile.cognitive.weak_concepts = ["kp_frac"]
    session = set_enhanced_profile(session, profile)
    session.metadata["enhanced"]["recommendations"] = [
        {"kp": "kp_frac", "reason": "薄弱点优先"}
    ]
    store.save(session)
    return session_id


def test_summary_default_matches_legacy_shape(tmp_path, monkeypatch):
    session_id = _seed_enhanced_session(tmp_path, monkeypatch)
    client = _client(tmp_path)
    base = client.get(f"/sessions/{session_id}/summary/teacher").json()
    default_q = client.get(
        f"/sessions/{session_id}/summary/teacher", params={"enhanced": "false"}
    ).json()
    assert "enhanced_profile" not in base
    assert "suggestions" not in base
    assert base == default_q


def test_summary_enhanced_true_requires_api_flag(tmp_path, monkeypatch):
    session_id = _seed_enhanced_session(tmp_path, monkeypatch)
    client = _client(tmp_path)
    # API flag still off → ignore enhanced=true
    ignored = client.get(
        f"/sessions/{session_id}/summary/teacher", params={"enhanced": "true"}
    ).json()
    assert "enhanced_profile" not in ignored

    monkeypatch.setenv("ILEARN_ENABLE_ENHANCED_API", "1")
    clear_enhanced_flag_cache()
    enriched = client.get(
        f"/sessions/{session_id}/summary/teacher", params={"enhanced": "true"}
    ).json()
    assert enriched["enhanced_profile"]["cognitive"]["knowledge_mastery"]["kp_frac"] == 0.3
    assert enriched["suggestions"][0]["kp"] == "kp_frac"


def test_dashboard_student_enhanced_overlay(tmp_path, monkeypatch):
    session_id = _seed_enhanced_session(tmp_path, monkeypatch)
    client = _client(tmp_path)
    assert (
        client.post(
            "/dashboard/teacher/bind",
            json={
                "teacher_id": "t1",
                "class_id": "c1",
                "session_id": session_id,
            },
        ).status_code
        == 204
    )
    legacy = client.get(f"/dashboard/teacher/t1/student/{session_id}").json()
    assert legacy["session_id"] == session_id
    assert "enhanced_profile" not in legacy

    monkeypatch.setenv("ILEARN_ENABLE_ENHANCED_API", "1")
    clear_enhanced_flag_cache()
    enriched = client.get(
        f"/dashboard/teacher/t1/student/{session_id}",
        params={"enhanced": "true"},
    ).json()
    assert enriched["session"]["session_id"] == session_id
    assert enriched["suggestions"]

    classes = client.get(
        "/dashboard/teacher/t1/classes", params={"enhanced": "true"}
    ).json()
    assert classes["enhanced"] is True
    assert classes["overview"]


def test_enhanced_report_pdf_gated(tmp_path, monkeypatch):
    session_id = _seed_enhanced_session(tmp_path, monkeypatch)
    client = _client(tmp_path)
    assert (
        client.get(f"/sessions/{session_id}/enhanced/report.pdf").status_code
        == 404
    )
    monkeypatch.setenv("ILEARN_ENABLE_ENHANCED_API", "1")
    clear_enhanced_flag_cache()
    ok = client.get(f"/sessions/{session_id}/enhanced/report.pdf")
    assert ok.status_code == 200
    assert ok.headers["content-type"].startswith("application/pdf")
