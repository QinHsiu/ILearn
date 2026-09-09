"""Edition 0909_4 PR04: P0 prompt/grouping + P1 cold start."""

from __future__ import annotations

from pathlib import Path

import pytest

from ilearn.agents.orchestrator import MultiAgentOrchestrator
from ilearn.core.assessment_paper_builder import knowledge_id_queue_from_profile
from ilearn.core.enhanced_context import build_enhanced_context_hint, ensure_cold_start_profile
from ilearn.core.enhanced_flags import clear_enhanced_flag_cache
from ilearn.core.enhanced_session import get_enhanced_profile
from ilearn.core.models.enhanced_profile import (
    EmotionType,
    EmotionalDimension,
    LearningStyle,
    MetacognitiveDimension,
    StudentFiveDimProfile,
)
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


def test_build_context_hint_from_profile():
    profile = StudentFiveDimProfile(student_id="s1")
    profile.emotional.current_emotion = EmotionType.FRUSTRATED
    profile.cognitive.weak_concepts = ["kp_a", "kp_b"]
    profile.metacognitive.learning_style = LearningStyle.VISUAL
    hint = build_enhanced_context_hint(profile)
    assert "挫败感" in hint
    assert "kp_a" in hint
    assert "视觉" in hint


def test_knowledge_queue_70_30_split():
    profile = StudentFiveDimProfile(student_id="s1")
    profile.cognitive.weak_concepts = ["w1", "w2"]
    profile.cognitive.strong_concepts = ["s1"]
    profile.cognitive.knowledge_mastery = {"w1": 0.2, "w2": 0.3, "s1": 0.9}
    queue = knowledge_id_queue_from_profile(profile, total=10, weak_ratio=0.7)
    assert len(queue) == 10
    weak_slots = sum(1 for kid in queue if kid in {"w1", "w2"})
    assert weak_slots >= 7


def test_cold_start_seeds_profile(monkeypatch, tmp_path):
    monkeypatch.setenv("ILEARN_ENABLE_ENHANCED_PROFILE", "1")
    clear_enhanced_flag_cache()
    store = SessionStore(tmp_path)
    session = store.create(StudentProfile(region="北京", grade=5, age=11))
    curriculum = PilotBeijingRenjiaoProvider(PILOT)
    session = ensure_cold_start_profile(session, curriculum)
    profile = get_enhanced_profile(session)
    assert profile is not None
    assert profile.cognitive.knowledge_mastery
    assert session.metadata.get("enhanced_context_hint")


def test_flag_off_generate_assessment_no_enhanced_side_effects(tmp_path):
    store = SessionStore(tmp_path)
    orch = MultiAgentOrchestrator(
        store=store,
        curriculum=PilotBeijingRenjiaoProvider(PILOT),
        llm=None,
    )
    sid = orch.create_session(StudentProfile(region="北京", grade=5, age=11))
    orch.generate_assessment(sid)
    session = orch.get_session(sid)
    assert "enhanced" not in session.metadata
    assert "enhanced_context_hint" not in session.metadata


def test_flag_on_cold_start_before_assessment(monkeypatch, tmp_path):
    monkeypatch.setenv("ILEARN_ENABLE_ENHANCED_PROFILE", "1")
    clear_enhanced_flag_cache()
    store = SessionStore(tmp_path)
    orch = MultiAgentOrchestrator(
        store=store,
        curriculum=PilotBeijingRenjiaoProvider(PILOT),
        llm=None,
    )
    sid = orch.create_session(StudentProfile(region="北京", grade=5, age=11))
    orch.generate_assessment(sid)
    session = orch.get_session(sid)
    assert get_enhanced_profile(session) is not None
    assert session.metadata.get("enhanced_context_hint")
