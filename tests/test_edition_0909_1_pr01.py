"""PR #01 acceptance: enhanced profile model + metadata.enhanced storage."""

from __future__ import annotations

import pytest

from ilearn.core.enhanced_flags import clear_enhanced_flag_cache, is_enhanced_enabled
from ilearn.core.enhanced_profile_adapter import ProfileAdapter
from ilearn.core.enhanced_session import get_enhanced_profile, set_enhanced_profile
from ilearn.core.models.enhanced_profile import StudentFiveDimProfile
from ilearn.core.schemas import DiagnosisReport, KnowledgeMastery, StudentProfile
from ilearn.storage.sessions import SessionStore


@pytest.fixture(autouse=True)
def _reset_flag_cache():
    clear_enhanced_flag_cache()
    yield
    clear_enhanced_flag_cache()


def test_flags_default_false():
    assert is_enhanced_enabled("ENABLE_ENHANCED_PROFILE") is False
    assert is_enhanced_enabled("ENABLE_ENHANCED_AGENTS") is False
    assert is_enhanced_enabled("ENABLE_ENHANCED_API") is False


def test_flag_env_override(monkeypatch):
    monkeypatch.setenv("ILEARN_ENABLE_ENHANCED_PROFILE", "1")
    clear_enhanced_flag_cache()
    assert is_enhanced_enabled("ENABLE_ENHANCED_PROFILE") is True


def test_five_dim_round_trip():
    profile = StudentFiveDimProfile(student_id="s1")
    profile.cognitive.knowledge_mastery["kp_a"] = 0.8
    data = profile.model_dump(mode="json")
    restored = StudentFiveDimProfile.model_validate(data)
    assert restored.get_mastery_for_concept("kp_a") == 0.8
    assert restored.get_overall_mastery() == 0.8


def test_set_enhanced_writes_metadata(monkeypatch, tmp_path):
    monkeypatch.setenv("ILEARN_ENABLE_ENHANCED_PROFILE", "1")
    clear_enhanced_flag_cache()
    store = SessionStore(tmp_path)
    session = store.create(StudentProfile(region="北京", grade=5, age=11))
    profile = StudentFiveDimProfile(student_id=session.session_id)
    profile.cognitive.knowledge_mastery["kp_1"] = 0.3
    session = set_enhanced_profile(session, profile)
    store.save(session)
    loaded = store.load(session.session_id)
    blob = loaded.metadata.get("enhanced")
    assert isinstance(blob, dict)
    assert blob["schema_version"] == 1
    assert blob["profile"]["cognitive"]["knowledge_mastery"]["kp_1"] == 0.3
    restored = get_enhanced_profile(loaded)
    assert restored is not None
    assert restored.get_mastery_for_concept("kp_1") == 0.3


def test_flag_off_set_is_noop(monkeypatch, tmp_path):
    monkeypatch.delenv("ILEARN_ENABLE_ENHANCED_PROFILE", raising=False)
    clear_enhanced_flag_cache()
    store = SessionStore(tmp_path)
    session = store.create(StudentProfile(region="北京", grade=5, age=11))
    session = set_enhanced_profile(
        session, StudentFiveDimProfile(student_id=session.session_id)
    )
    assert "enhanced" not in session.metadata


def test_legacy_metadata_mastery_unaffected(monkeypatch, tmp_path):
    monkeypatch.setenv("ILEARN_ENABLE_ENHANCED_PROFILE", "1")
    clear_enhanced_flag_cache()
    store = SessionStore(tmp_path)
    state = store.create(
        StudentProfile(region="北京", grade=5, age=11, nickname="Alice")
    )
    state.diagnosis = DiagnosisReport(
        curriculum_label="pilot",
        knowledge_mastery=[
            KnowledgeMastery(
                knowledge_id="fraction",
                score_rate=0.4,
                level="weak",
            ),
            KnowledgeMastery(
                knowledge_id="decimal",
                score_rate=0.8,
                level="mastered",
            ),
        ],
    )
    store.save(state)
    before = store.list_all_metadata()[0]

    state = store.load(state.session_id)
    boot = ProfileAdapter.from_session(state)
    boot.cognitive.knowledge_mastery["fraction"] = 0.99
    state = set_enhanced_profile(state, boot)
    store.save(state)

    after = store.list_all_metadata()[0]
    assert after.overall_mastery == pytest.approx(before.overall_mastery)
    assert after.skill_mastery == before.skill_mastery
    assert after.weak_skills == before.weak_skills


def test_adapter_from_diagnosis(tmp_path):
    store = SessionStore(tmp_path)
    state = store.create(StudentProfile(region="北京", grade=5, age=11))
    state.diagnosis = DiagnosisReport(
        curriculum_label="pilot",
        knowledge_mastery=[
            KnowledgeMastery(knowledge_id="kp_x", score_rate=0.2, level="weak"),
        ],
    )
    five = ProfileAdapter.from_session(state)
    assert five.contextual.grade == "5"
    assert five.contextual.region == "北京"
    assert five.get_mastery_for_concept("kp_x") == 0.2
    assert "kp_x" in five.cognitive.weak_concepts
