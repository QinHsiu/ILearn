"""Phase 1 KT (BKT) unit tests."""

from __future__ import annotations

from unittest.mock import Mock

import pytest

from ilearn.agents.enhanced import profile_updater as profile_updater_mod
from ilearn.agents.enhanced.profile_updater import ProfileUpdaterAgent
from ilearn.core.enhanced_flags import clear_enhanced_flag_cache, is_enhanced_enabled
from ilearn.core.enhanced_session import (
    get_enhanced_profile,
    get_kt_state,
    set_enhanced_profile,
    set_kt_state,
)
from ilearn.core.kt.bkt import BKTKnowledgeTracing
from ilearn.core.kt.factory import create_kt_service, create_kt_service_from_session
from ilearn.core.kt.protocol import KTInteraction
from ilearn.core.models.enhanced_profile import StudentFiveDimProfile
from ilearn.core.schemas import (
    DiagnosisReport,
    KnowledgeMastery,
    SessionState,
    StudentProfile,
)


class TestBKT:
    """BKT core functionality tests."""

    def test_bkt_init(self):
        bkt = BKTKnowledgeTracing()
        assert bkt.p_l0 == 0.5
        assert bkt.p_t == 0.1
        assert bkt.p_s == 0.1
        assert bkt.p_g == 0.2
        assert len(bkt._states) == 0

    def test_bkt_add_interaction_correct(self):
        bkt = BKTKnowledgeTracing()
        bkt.add_interaction("kp_a", correct=True)

        assert "kp_a" in bkt._states
        state = bkt._states["kp_a"]
        assert state.total == 1
        assert state.success == 1
        assert state.p_known > 0.5
        assert state.p_known < 0.9

    def test_bkt_add_interaction_incorrect(self):
        bkt = BKTKnowledgeTracing()
        bkt.add_interaction("kp_a", correct=False)

        state = bkt._states["kp_a"]
        assert state.total == 1
        assert state.success == 0
        assert state.p_known < 0.5
        assert state.p_known > 0.1

    def test_bkt_multiple_correct(self):
        bkt = BKTKnowledgeTracing()
        for _ in range(5):
            bkt.add_interaction("kp_a", correct=True)

        state = bkt._states["kp_a"]
        assert state.p_known > 0.85
        assert state.total == 5
        assert state.success == 5

    def test_bkt_predict_mastery(self):
        bkt = BKTKnowledgeTracing()
        bkt.add_interaction("kp_a", correct=True)
        bkt.add_interaction("kp_b", correct=False)

        preds = bkt.predict_mastery(["kp_a", "kp_b", "kp_c"])

        assert "kp_a" in preds
        assert "kp_b" in preds
        assert "kp_c" in preds
        assert preds["kp_a"] > 0.5
        assert preds["kp_b"] < 0.5
        assert preds["kp_c"] == 0.5

    def test_bkt_get_weak_concepts(self):
        bkt = BKTKnowledgeTracing()
        for _ in range(3):
            bkt.add_interaction("kp_weak", correct=False)
        for _ in range(3):
            bkt.add_interaction("kp_strong", correct=True)

        weak = bkt.get_weak_concepts(threshold=0.6, top_n=3)
        assert "kp_weak" in weak
        assert "kp_strong" not in weak

    def test_bkt_get_state_and_load(self):
        bkt = BKTKnowledgeTracing()
        bkt.add_interaction("kp_a", correct=True)
        bkt.add_interaction("kp_b", correct=False)
        bkt.add_interaction("kp_a", correct=True)

        state = bkt.get_state()
        assert state["backend"] == "bkt"
        assert "states" in state
        assert "interactions" in state
        assert len(state["interactions"]) == 3

        bkt2 = BKTKnowledgeTracing()
        bkt2.load_state(state)

        assert "kp_a" in bkt2._states
        assert "kp_b" in bkt2._states
        assert bkt2._states["kp_a"].total == 2
        assert bkt2._states["kp_b"].total == 1
        assert len(bkt2._interactions) == 3

    def test_bkt_p_known_bounds(self):
        bkt = BKTKnowledgeTracing()

        for _ in range(20):
            bkt.add_interaction("kp_a", correct=False)

        state = bkt._states["kp_a"]
        assert 0.01 <= state.p_known <= 0.99

        for _ in range(20):
            bkt.add_interaction("kp_b", correct=True)

        state = bkt._states["kp_b"]
        assert 0.01 <= state.p_known <= 0.99

    def test_bkt_interactions_limit(self):
        bkt = BKTKnowledgeTracing(max_interactions=5)
        for i in range(10):
            bkt.add_interaction(f"kp_{i}", correct=True)

        assert len(bkt._interactions) == 5
        assert bkt._interactions[0].concept == "kp_5"


def test_bkt_correct_raises_p_known():
    bkt = BKTKnowledgeTracing()
    bkt.add_interaction("kp_a", True)
    assert 0.5 < bkt._states["kp_a"].p_known < 0.99


def test_bkt_incorrect_lowers_p_known():
    bkt = BKTKnowledgeTracing()
    bkt.add_interaction("kp_a", False)
    assert 0.01 < bkt._states["kp_a"].p_known < 0.5


def test_bkt_bounds_after_many_errors():
    bkt = BKTKnowledgeTracing()
    for _ in range(20):
        bkt.add_interaction("kp_a", False)
    assert 0.01 <= bkt._states["kp_a"].p_known <= 0.99


def test_bkt_roundtrip_state():
    bkt = BKTKnowledgeTracing()
    bkt.add_interaction("kp_a", True)
    bkt2 = BKTKnowledgeTracing()
    bkt2.load_state(bkt.get_state())
    assert bkt2._states["kp_a"].total == 1
    assert abs(bkt2._states["kp_a"].p_known - bkt._states["kp_a"].p_known) < 1e-9


def test_create_kt_service_bkt():
    svc = create_kt_service("bkt")
    assert svc.get_backend_name() == "bkt"


class TestKTFactory:
    """KT factory tests."""

    def test_create_bkt(self):
        bkt = create_kt_service("bkt")
        assert isinstance(bkt, BKTKnowledgeTracing)

    def test_create_bkt_with_params(self):
        bkt = create_kt_service(
            "bkt",
            bkt_params={"p_l0": 0.6, "p_t": 0.2},
        )
        assert bkt.p_l0 == 0.6
        assert bkt.p_t == 0.2
        assert bkt.p_s == 0.1
        assert bkt.p_g == 0.2

    def test_create_pykt_fallback_to_bkt(self, caplog):
        import logging

        with caplog.at_level(logging.WARNING):
            svc = create_kt_service("pykt")
        assert isinstance(svc, BKTKnowledgeTracing)
        assert svc.get_backend_name() == "bkt"
        assert any("pyKT" in r.message for r in caplog.records)

    def test_create_kt_service_from_session_loads_state(self):
        bkt = BKTKnowledgeTracing()
        bkt.add_interaction("kp_a", correct=True)

        session = Mock()
        session.metadata = {"enhanced": {"kt": bkt.get_state()}}

        svc = create_kt_service_from_session(session, backend="bkt")
        assert svc.get_backend_name() == "bkt"
        assert svc._states["kp_a"].total == 1

    def test_create_kt_service_from_session_bad_state(self):
        session = Mock()
        session.metadata = {"enhanced": {"kt": "invalid"}}

        svc = create_kt_service_from_session(session, backend="bkt")
        assert isinstance(svc, BKTKnowledgeTracing)


class TestSessionIntegration:
    """Session integration tests for enhanced blob merge."""

    def test_set_enhanced_profile_preserves_kt(self, monkeypatch):
        monkeypatch.setenv("ILEARN_ENABLE_ENHANCED_PROFILE", "1")
        clear_enhanced_flag_cache()
        session = SessionState(
            session_id="s1",
            profile=StudentProfile(region="北京", grade=5, age=11),
            metadata={
                "enhanced": {
                    "schema_version": 1,
                    "profile": {"student_id": "s1"},
                    "kt": {"backend": "bkt", "interactions": []},
                    "recommendations": [{"id": 1}],
                }
            },
        )
        profile = StudentFiveDimProfile(student_id="s1")
        session = set_enhanced_profile(session, profile)
        assert session.metadata["enhanced"]["kt"]["backend"] == "bkt"
        assert session.metadata["enhanced"]["recommendations"] == [{"id": 1}]
        assert "profile" in session.metadata["enhanced"]

    def test_set_kt_state_preserves_profile(self, monkeypatch):
        monkeypatch.setenv("ILEARN_ENABLE_ENHANCED_PROFILE", "1")
        clear_enhanced_flag_cache()
        session = SessionState(
            session_id="s1",
            profile=StudentProfile(region="北京", grade=5, age=11),
            metadata={
                "enhanced": {
                    "schema_version": 1,
                    "profile": {"student_id": "s1"},
                }
            },
        )
        kt_state = {"backend": "bkt", "interactions": []}
        session = set_kt_state(session, kt_state)
        enhanced = session.metadata["enhanced"]
        assert "profile" in enhanced
        assert enhanced["kt"] == kt_state
        assert get_kt_state(session) == kt_state


def test_kt_flag_defaults_off(monkeypatch):
    monkeypatch.delenv("ILEARN_ENABLE_ENHANCED_KT", raising=False)
    clear_enhanced_flag_cache()
    assert is_enhanced_enabled("ENABLE_ENHANCED_KT") is False


def test_kt_flag_env_on(monkeypatch):
    monkeypatch.setenv("ILEARN_ENABLE_ENHANCED_KT", "1")
    clear_enhanced_flag_cache()
    assert is_enhanced_enabled("ENABLE_ENHANCED_KT") is True


def _session_with_diagnosis() -> SessionState:
    """Session with diagnosis rows so stub knowledge_updates are non-empty."""
    return SessionState(
        session_id="s-kt-updater",
        profile=StudentProfile(region="北京", grade=5, age=11),
        diagnosis=DiagnosisReport(
            curriculum_label="北京·人教",
            knowledge_mastery=[
                KnowledgeMastery(
                    knowledge_id="kp_a",
                    score_rate=0.8,
                    level="mastered",
                ),
                KnowledgeMastery(
                    knowledge_id="kp_b",
                    score_rate=0.3,
                    level="weak",
                ),
            ],
        ),
    )


def _enable_updater_flags(monkeypatch, *, kt: bool) -> None:
    monkeypatch.setenv("ILEARN_ENABLE_ENHANCED_PROFILE", "1")
    monkeypatch.setenv("ILEARN_ENABLE_ENHANCED_AGENTS", "1")
    if kt:
        monkeypatch.setenv("ILEARN_ENABLE_ENHANCED_KT", "1")
    else:
        monkeypatch.delenv("ILEARN_ENABLE_ENHANCED_KT", raising=False)
    clear_enhanced_flag_cache()


def _expected_kt_fusion(old: float, correct: bool) -> float:
    """Independent BKT + cold-start alpha=0.2 fusion for one attempt."""
    kt = BKTKnowledgeTracing()
    kt.add_interaction("x", correct)
    kt_score = kt.predict_mastery(["x"])["x"]
    alpha = 0.2
    return max(0.05, min(0.95, alpha * kt_score + (1.0 - alpha) * old))


def test_updater_kt_off_uses_delta(monkeypatch):
    _enable_updater_flags(monkeypatch, kt=False)
    session = _session_with_diagnosis()
    updater = ProfileUpdaterAgent(llm=None, stub_mode=True)

    session = updater.update_session(session)
    profile = get_enhanced_profile(session)

    assert profile is not None
    assert profile.cognitive.knowledge_mastery["kp_a"] == pytest.approx(0.92)
    assert profile.cognitive.knowledge_mastery["kp_b"] == pytest.approx(0.18)
    assert get_kt_state(session) is None


def test_updater_kt_on_writes_kt_blob(monkeypatch):
    _enable_updater_flags(monkeypatch, kt=True)
    session = _session_with_diagnosis()
    updater = ProfileUpdaterAgent(llm=None, stub_mode=True)

    session = updater.update_session(session)
    profile = get_enhanced_profile(session)
    kt_blob = get_kt_state(session)

    assert profile is not None
    assert kt_blob is not None
    assert kt_blob.get("backend") == "bkt"
    assert kt_blob.get("interactions")
    assert "states" in kt_blob
    assert profile.cognitive.knowledge_mastery["kp_a"] == pytest.approx(
        _expected_kt_fusion(0.8, True)
    )
    assert profile.cognitive.knowledge_mastery["kp_b"] == pytest.approx(
        _expected_kt_fusion(0.3, False)
    )
    assert profile.cognitive.knowledge_mastery["kp_a"] != pytest.approx(0.92)
    assert profile.cognitive.knowledge_mastery["kp_b"] != pytest.approx(0.18)


def test_updater_kt_error_falls_back(monkeypatch):
    _enable_updater_flags(monkeypatch, kt=True)
    boom = Mock(side_effect=RuntimeError("kt boom"))
    monkeypatch.setattr(
        profile_updater_mod,
        "create_kt_service_from_session",
        boom,
        raising=False,
    )
    session = _session_with_diagnosis()
    updater = ProfileUpdaterAgent(llm=None, stub_mode=True)

    session = updater.update_session(session)
    profile = get_enhanced_profile(session)

    assert boom.called
    assert profile is not None
    assert profile.cognitive.knowledge_mastery["kp_a"] == pytest.approx(0.92)
    assert profile.cognitive.knowledge_mastery["kp_b"] == pytest.approx(0.18)


def test_updater_kt_empty_updates_does_not_mutate_mastery(monkeypatch):
    _enable_updater_flags(monkeypatch, kt=True)
    session = SessionState(
        session_id="s-kt-empty",
        profile=StudentProfile(region="北京", grade=5, age=11),
    )
    seeded = StudentFiveDimProfile(student_id="s-kt-empty")
    seeded.cognitive.knowledge_mastery = {"kp_keep": 0.75, "kp_other": 0.4}
    session = set_enhanced_profile(session, seeded)
    factory = Mock(side_effect=AssertionError("KT factory must not run"))
    monkeypatch.setattr(
        profile_updater_mod,
        "create_kt_service_from_session",
        factory,
    )
    updater = ProfileUpdaterAgent(llm=None, stub_mode=True)

    session = updater.update_session(session)
    profile = get_enhanced_profile(session)

    assert factory.called is False
    assert profile is not None
    assert profile.cognitive.knowledge_mastery["kp_keep"] == pytest.approx(0.75)
    assert profile.cognitive.knowledge_mastery["kp_other"] == pytest.approx(0.4)
    assert get_kt_state(session) is None


def test_updater_kt_on_skips_untouched_mastery(monkeypatch):
    _enable_updater_flags(monkeypatch, kt=True)
    session = SessionState(
        session_id="s-kt-untouched",
        profile=StudentProfile(region="北京", grade=5, age=11),
        diagnosis=DiagnosisReport(
            curriculum_label="北京·人教",
            knowledge_mastery=[
                KnowledgeMastery(
                    knowledge_id="kp_a",
                    score_rate=0.8,
                    level="mastered",
                ),
            ],
        ),
    )
    seeded = StudentFiveDimProfile(student_id="s-kt-untouched")
    seeded.cognitive.knowledge_mastery = {"kp_a": 0.8, "kp_untouched": 0.7}
    session = set_enhanced_profile(session, seeded)
    updater = ProfileUpdaterAgent(llm=None, stub_mode=True)

    session = updater.update_session(session)
    profile = get_enhanced_profile(session)

    assert profile is not None
    assert profile.cognitive.knowledge_mastery["kp_untouched"] == pytest.approx(0.7)
    assert profile.cognitive.knowledge_mastery["kp_a"] == pytest.approx(
        _expected_kt_fusion(0.8, True)
    )


def test_updater_kt_uses_full_alpha_after_three_attempts(monkeypatch):
    _enable_updater_flags(monkeypatch, kt=True)
    prior = BKTKnowledgeTracing()
    prior.add_interaction("kp_a", True)
    prior.add_interaction("kp_a", True)
    session = SessionState(
        session_id="s-kt-alpha",
        profile=StudentProfile(region="北京", grade=5, age=11),
        diagnosis=DiagnosisReport(
            curriculum_label="北京·人教",
            knowledge_mastery=[
                KnowledgeMastery(
                    knowledge_id="kp_a",
                    score_rate=0.9,
                    level="mastered",
                ),
            ],
        ),
    )
    seeded = StudentFiveDimProfile(student_id="s-kt-alpha")
    seeded.cognitive.knowledge_mastery = {"kp_a": 0.6}
    session = set_enhanced_profile(session, seeded)
    session = set_kt_state(session, prior.get_state())
    updater = ProfileUpdaterAgent(llm=None, stub_mode=True)

    session = updater.update_session(session)
    profile = get_enhanced_profile(session)

    replay = BKTKnowledgeTracing()
    replay.load_state(prior.get_state())
    replay.add_interaction("kp_a", True)
    kt_score = replay.predict_mastery(["kp_a"])["kp_a"]
    expected_full = max(0.05, min(0.95, 0.4 * kt_score + 0.6 * 0.6))
    expected_cold = max(0.05, min(0.95, 0.2 * kt_score + 0.8 * 0.6))

    assert profile is not None
    assert replay.get_attempt_count("kp_a") == 3
    assert profile.cognitive.knowledge_mastery["kp_a"] == pytest.approx(expected_full)
    assert profile.cognitive.knowledge_mastery["kp_a"] != pytest.approx(expected_cold)


def test_updater_kt_persist_error_does_not_double_apply(monkeypatch):
    _enable_updater_flags(monkeypatch, kt=True)
    monkeypatch.setattr(
        profile_updater_mod,
        "set_kt_state",
        Mock(side_effect=RuntimeError("persist boom")),
    )
    session = _session_with_diagnosis()
    updater = ProfileUpdaterAgent(llm=None, stub_mode=True)

    session = updater.update_session(session)
    profile = get_enhanced_profile(session)

    assert profile is not None
    assert profile.cognitive.knowledge_mastery["kp_a"] == pytest.approx(0.92)
    assert profile.cognitive.knowledge_mastery["kp_b"] == pytest.approx(0.18)
