"""P2: background profile update service + orchestrator deferral."""

from __future__ import annotations

from datetime import timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from ilearn.agents.orchestrator import MultiAgentOrchestrator
from ilearn.api.app import create_app
from ilearn.core.datetime_utils import utc_now
from ilearn.core.enhanced_flags import clear_enhanced_flag_cache
from ilearn.core.enhanced_session import get_enhanced_profile, set_enhanced_profile
from ilearn.core.models.enhanced_profile import StudentFiveDimProfile
from ilearn.core.schemas import StudentProfile
from ilearn.providers.curriculum import PilotBeijingRenjiaoProvider
from ilearn.services.profile_update_service import update_profile_background
from ilearn.storage.sessions import SessionStore

PILOT = Path(__file__).resolve().parents[1] / "data" / "pilot"


@pytest.fixture(autouse=True)
def _reset_flags(monkeypatch):
    for name in (
        "ILEARN_ENABLE_ENHANCED_PROFILE",
        "ILEARN_ENABLE_ENHANCED_AGENTS",
        "ILEARN_ENABLE_ENHANCED_API",
        "ILEARN_ENABLE_ENHANCED_BACKGROUND",
    ):
        monkeypatch.delenv(name, raising=False)
    clear_enhanced_flag_cache()
    yield
    clear_enhanced_flag_cache()


def _through_grade(tmp_path):
    orch = MultiAgentOrchestrator(
        store=SessionStore(tmp_path),
        curriculum=PilotBeijingRenjiaoProvider(PILOT),
        llm=None,
    )
    sid = orch.create_session(StudentProfile(region="北京", grade=5, age=11))
    paper = orch.generate_assessment(sid)
    answers = {item.id: (item.answer_key or "") for item in paper.items}
    for item in paper.items[:2]:
        answers[item.id] = "wrong-answer"
    orch.submit(sid, answers)
    orch.grade(sid)
    return orch, sid


def test_background_flag_defers_sync_profile_update(monkeypatch, tmp_path):
    monkeypatch.setenv("ILEARN_ENABLE_ENHANCED_PROFILE", "1")
    monkeypatch.setenv("ILEARN_ENABLE_ENHANCED_AGENTS", "1")
    monkeypatch.setenv("ILEARN_ENABLE_ENHANCED_BACKGROUND", "1")
    clear_enhanced_flag_cache()
    orch, sid = _through_grade(tmp_path)
    orch.diagnose(sid)
    session = orch.get_session(sid)
    # Cold start may exist; version bump from updater should not happen synchronously
    profile = get_enhanced_profile(session)
    if profile is not None:
        assert profile.version == 1


def test_update_profile_background_writes(monkeypatch, tmp_path):
    monkeypatch.setenv("ILEARN_ENABLE_ENHANCED_PROFILE", "1")
    monkeypatch.setenv("ILEARN_ENABLE_ENHANCED_AGENTS", "1")
    monkeypatch.setenv("ILEARN_ENABLE_ENHANCED_BACKGROUND", "1")
    clear_enhanced_flag_cache()
    store = SessionStore(tmp_path)
    session = store.create(StudentProfile(region="北京", grade=5, age=11))
    profile = StudentFiveDimProfile(student_id=session.session_id)
    profile.cognitive.knowledge_mastery = {"kp_a": 0.5}
    profile.last_updated = utc_now() - timedelta(minutes=10)
    session = set_enhanced_profile(session, profile)
    store.save(session)

    update_profile_background(store, session.session_id, llm=None)
    loaded = get_enhanced_profile(store.load(session.session_id))
    assert loaded is not None
    assert loaded.version >= 2


def test_api_diagnose_schedules_background(monkeypatch, tmp_path):
    monkeypatch.setenv("ILEARN_ENABLE_ENHANCED_PROFILE", "1")
    monkeypatch.setenv("ILEARN_ENABLE_ENHANCED_AGENTS", "1")
    monkeypatch.setenv("ILEARN_ENABLE_ENHANCED_BACKGROUND", "1")
    clear_enhanced_flag_cache()
    client = TestClient(
        create_app(
            sessions_dir=tmp_path,
            pilot_data_dir=PILOT,
            llm=None,
        )
    )
    sid = client.post(
        "/sessions",
        json={"region": "北京", "grade": 5, "age": 11},
    ).json()["session_id"]
    paper = client.post(f"/sessions/{sid}/assessment").json()
    answers = {item["id"]: item.get("answer_key") or "" for item in paper["items"]}
    client.post(f"/sessions/{sid}/submit", json={"answers": answers})
    client.post(f"/sessions/{sid}/grade")
    resp = client.post(f"/sessions/{sid}/diagnose")
    assert resp.status_code == 200
