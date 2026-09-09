"""Edition 0909_3 Phase 4: hook isolation + activation verify."""

from __future__ import annotations

from pathlib import Path

import pytest

from ilearn.agents.orchestrator import MultiAgentOrchestrator
from ilearn.core.enhanced_flags import clear_enhanced_flag_cache
from ilearn.core.enhanced_session import get_enhanced_profile
from ilearn.core.schemas import StudentProfile
from ilearn.providers.curriculum import PilotBeijingRenjiaoProvider
from ilearn.storage.sessions import SessionStore

PILOT = Path(__file__).resolve().parents[1] / "data" / "pilot"


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


def test_enhanced_hook_exception_does_not_break_diagnose(monkeypatch, tmp_path):
    monkeypatch.setenv("ILEARN_ENABLE_ENHANCED_PROFILE", "1")
    monkeypatch.setenv("ILEARN_ENABLE_ENHANCED_AGENTS", "1")
    clear_enhanced_flag_cache()
    orch, sid = _through_grade(tmp_path)

    def _boom(session):
        raise RuntimeError("simulated enhanced failure")

    monkeypatch.setattr(orch._enhanced_profile_updater, "update_session", _boom)
    diagnosis = orch.diagnose(sid)
    assert diagnosis is not None
    assert diagnosis.knowledge_mastery
    session = orch.get_session(sid)
    # Failure swallowed: no enhanced blob required
    assert session.diagnosis is not None


def test_phase4_diagnose_writes_enhanced_when_flags_on(monkeypatch, tmp_path):
    monkeypatch.setenv("ILEARN_ENABLE_ENHANCED_PROFILE", "1")
    monkeypatch.setenv("ILEARN_ENABLE_ENHANCED_AGENTS", "1")
    clear_enhanced_flag_cache()
    orch, sid = _through_grade(tmp_path)
    orch.diagnose(sid)
    profile = get_enhanced_profile(orch.get_session(sid))
    assert profile is not None
    assert profile.cognitive.knowledge_mastery
