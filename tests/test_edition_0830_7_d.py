"""Edition 0830_7 D — PhaseGuard, feature tiers, friendly errors."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from ilearn.api.app import create_app
from ilearn.core.feature_flags import FeatureRegistry, FeatureTier
from ilearn.core.phase_guard import PhaseGuard
from ilearn.core.schemas import SessionPhase, SessionState, StudentProfile
from ilearn.core.user_errors import UserFriendlyError, map_exception_message
from ilearn.agents.orchestrator import MultiAgentOrchestrator
from ilearn.providers.curriculum import PilotBeijingRenjiaoProvider
from ilearn.storage.sessions import SessionStore

PILOT = Path(__file__).resolve().parents[1] / "data" / "pilot"


def test_phase_guard_allows_happy_path():
    assert PhaseGuard.can_transition(SessionPhase.ONBOARD, SessionPhase.PRACTICE)
    assert PhaseGuard.can_transition(SessionPhase.PRACTICE, SessionPhase.GRADE)
    assert PhaseGuard.can_transition(SessionPhase.GRADE, SessionPhase.DIAGNOSE)
    assert PhaseGuard.can_transition(SessionPhase.DIAGNOSE, SessionPhase.PLAN)


def test_phase_guard_rejects_illegal():
    with pytest.raises(UserFriendlyError) as exc:
        PhaseGuard.assert_transition(SessionPhase.ONBOARD, SessionPhase.GRADE)
    assert exc.value.code == "E-010"


def test_phase_history_recorded():
    session = SessionState(
        session_id="s1",
        profile=StudentProfile(region="北京", grade=5, age=11),
    )
    PhaseGuard.transition(session, SessionPhase.PRACTICE)
    history = session.metadata.get("phase_history") or []
    assert history
    assert history[-1]["to"] == "practice"


def test_feature_registry_tiers():
    assert FeatureRegistry.get_tier("diagnosis") == FeatureTier.OFFLINE
    assert FeatureRegistry.get_tier("llm_enhanced_diagnosis") == FeatureTier.ONLINE
    payload = FeatureRegistry.capabilities_payload(llm_available=False)
    online = [f for f in payload["features"] if f["name"] == "llm_enhanced_diagnosis"][0]
    assert online["available"] is False


def test_map_exception_message():
    mapped = map_exception_message("session must be graded before diagnosis")
    assert mapped is not None
    assert mapped.code == "E-002"


def test_capabilities_endpoint(tmp_path: Path):
    client = TestClient(
        create_app(sessions_dir=tmp_path, pilot_data_dir=PILOT, llm=None)
    )
    r = client.get("/capabilities")
    assert r.status_code == 200
    body = r.json()
    assert "features" in body
    assert body["llm_available"] is False
    assert "diagnosis" in body["tiers"]


def test_friendly_error_on_diagnose_without_grades(tmp_path: Path):
    client = TestClient(
        create_app(sessions_dir=tmp_path, pilot_data_dir=PILOT, llm=None)
    )
    sid = client.post(
        "/sessions", json={"region": "北京", "grade": 5, "age": 11}
    ).json()["session_id"]
    client.post(f"/sessions/{sid}/assessment")
    r = client.post(f"/sessions/{sid}/diagnose")
    assert r.status_code == 400
    body = r.json()
    assert body.get("error_code") == "E-002"
    assert "诊断" in body.get("message", "")


def test_orchestrator_records_phase_history(tmp_path: Path):
    orch = MultiAgentOrchestrator(
        store=SessionStore(tmp_path),
        curriculum=PilotBeijingRenjiaoProvider(PILOT),
        llm=None,
    )
    sid = orch.create_session(StudentProfile(region="北京", grade=5, age=11))
    paper = orch.generate_assessment(sid)
    session = orch._store.load(sid)
    assert session.phase == SessionPhase.PRACTICE
    history = session.metadata.get("phase_history") or []
    assert any(row.get("to") == "practice" for row in history)
    answers = {item.id: (item.answer_key or "") for item in paper.items}
    orch.submit(sid, answers)
    session = orch._store.load(sid)
    assert session.phase == SessionPhase.GRADE
