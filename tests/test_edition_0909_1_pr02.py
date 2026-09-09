"""PR #02 acceptance: enhanced agents + orchestrator hooks (flag-gated)."""

from __future__ import annotations

from pathlib import Path

import pytest

from ilearn.agents.enhanced.diagnosis import ErrorDiagnosisAgent
from ilearn.agents.enhanced.profile_updater import ProfileUpdaterAgent
from ilearn.agents.enhanced.question import QuestionGeneratorAgent
from ilearn.agents.enhanced.recommend import RecommendAgent
from ilearn.agents.orchestrator import MultiAgentOrchestrator
from ilearn.core.enhanced_flags import clear_enhanced_flag_cache
from ilearn.core.enhanced_session import get_enhanced_profile
from ilearn.core.models.enhanced_profile import StudentFiveDimProfile
from ilearn.core.schemas import StudentProfile
from ilearn.providers.curriculum import PilotBeijingRenjiaoProvider
from ilearn.storage.sessions import SessionStore

PILOT = Path(__file__).resolve().parents[1] / "data" / "pilot"


@pytest.fixture(autouse=True)
def _reset_flag_cache(monkeypatch):
    monkeypatch.delenv("ILEARN_ENABLE_ENHANCED_PROFILE", raising=False)
    monkeypatch.delenv("ILEARN_ENABLE_ENHANCED_AGENTS", raising=False)
    monkeypatch.delenv("ILEARN_ENABLE_ENHANCED_API", raising=False)
    clear_enhanced_flag_cache()
    yield
    clear_enhanced_flag_cache()


def _run_through_diagnose(tmp_path) -> tuple[MultiAgentOrchestrator, str]:
    orch = MultiAgentOrchestrator(
        store=SessionStore(tmp_path),
        curriculum=PilotBeijingRenjiaoProvider(PILOT),
        llm=None,
    )
    sid = orch.create_session(StudentProfile(region="北京", grade=5, age=11))
    paper = orch.generate_assessment(sid)
    answers = {
        item.id: (item.answer_key or "") for item in paper.items
    }
    # Force a few wrong answers so stub signals are non-trivial.
    for item in paper.items[:3]:
        answers[item.id] = "wrong-answer"
    orch.submit(sid, answers)
    orch.grade(sid)
    orch.diagnose(sid)
    return orch, sid


def test_flag_off_diagnose_has_no_enhanced_metadata(tmp_path):
    orch, sid = _run_through_diagnose(tmp_path)
    session = orch.get_session(sid)
    assert "enhanced" not in session.metadata
    assert session.diagnosis is not None


def test_flag_on_stub_writes_enhanced_profile(monkeypatch, tmp_path):
    monkeypatch.setenv("ILEARN_ENABLE_ENHANCED_PROFILE", "1")
    monkeypatch.setenv("ILEARN_ENABLE_ENHANCED_AGENTS", "1")
    clear_enhanced_flag_cache()
    orch, sid = _run_through_diagnose(tmp_path)
    session = orch.get_session(sid)
    blob = session.metadata.get("enhanced")
    assert isinstance(blob, dict)
    assert blob.get("schema_version") == 1
    profile = get_enhanced_profile(session)
    assert profile is not None
    assert isinstance(profile, StudentFiveDimProfile)
    assert profile.student_id == sid
    assert profile.cognitive.knowledge_mastery


def test_flag_on_plan_attaches_recommendations(monkeypatch, tmp_path):
    monkeypatch.setenv("ILEARN_ENABLE_ENHANCED_PROFILE", "1")
    monkeypatch.setenv("ILEARN_ENABLE_ENHANCED_AGENTS", "1")
    clear_enhanced_flag_cache()
    orch, sid = _run_through_diagnose(tmp_path)
    orch.plan(sid)
    session = orch.get_session(sid)
    blob = session.metadata.get("enhanced")
    assert isinstance(blob, dict)
    assert isinstance(blob.get("recommendations"), list)
    assert blob["recommendations"]


def test_stub_agents_deterministic_offline():
    updater = ProfileUpdaterAgent(llm=None, stub_mode=True)
    recommender = RecommendAgent(llm=None, stub_mode=True)
    questioner = QuestionGeneratorAgent(llm=None, stub_mode=True)
    diagnoser = ErrorDiagnosisAgent(llm=None, stub_mode=True)

    profile = StudentFiveDimProfile(student_id="s1")
    profile.cognitive.knowledge_mastery = {"kp_a": 0.2, "kp_b": 0.9}
    profile.cognitive.weak_concepts = ["kp_a"]
    recs = recommender.recommend_from_profile(profile)
    assert recs and recs[0]["kp"] == "kp_a"

    item = questioner.generate(target_kp="kp_a", grade=5)
    assert item["type"] == "choice"
    assert "kp_a" in item["stem"]

    err = diagnoser.diagnose_error(
        question={"stem": "1+1"}, student_answer="3", correct_answer="2"
    )
    assert err["error_types"]
    assert updater.stub_mode is True
