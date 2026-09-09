"""Phase 1 KT (BKT) unit tests."""

from __future__ import annotations

from unittest.mock import Mock

import pytest

from ilearn.core.enhanced_flags import clear_enhanced_flag_cache
from ilearn.core.enhanced_session import get_kt_state, set_enhanced_profile, set_kt_state
from ilearn.core.kt.bkt import BKTKnowledgeTracing
from ilearn.core.kt.factory import create_kt_service, create_kt_service_from_session
from ilearn.core.kt.protocol import KTInteraction
from ilearn.core.models.enhanced_profile import StudentFiveDimProfile
from ilearn.core.schemas import SessionState, StudentProfile


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
