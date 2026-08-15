from datetime import timezone

from ilearn.core.schemas import (
    DiagnosisReport,
    KnowledgeMastery,
    SessionMetadata,
    StudentProfile,
)
from ilearn.storage.sessions import SessionStore


def test_list_by_nickname_matches_trimmed_casefold(tmp_path):
    store = SessionStore(tmp_path)
    a = store.create(StudentProfile(region="北京", grade=5, age=11, nickname="小明"))
    store.create(StudentProfile(region="北京", grade=6, age=12, nickname="小红"))
    found = store.list_by_nickname(" 小明 ")
    assert [row.session_id for row in found] == [a.session_id]


def test_delete_removes_file(tmp_path):
    store = SessionStore(tmp_path)
    session = store.create(StudentProfile(region="北京", grade=5, age=11))
    store.delete(session.session_id)
    try:
        store.load(session.session_id)
        assert False, "expected FileNotFoundError"
    except FileNotFoundError:
        pass


def test_delete_missing_raises(tmp_path):
    store = SessionStore(tmp_path)
    try:
        store.delete("missing")
        assert False, "expected FileNotFoundError"
    except FileNotFoundError:
        pass


def test_list_all_metadata_empty(tmp_path):
    store = SessionStore(tmp_path)
    assert store.list_all_metadata() == []


def test_list_all_metadata_projects_diagnosis(tmp_path):
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

    rows = store.list_all_metadata()
    assert len(rows) == 1
    row = rows[0]
    assert isinstance(row, SessionMetadata)
    assert row.session_id == state.session_id
    assert row.nickname == "Alice"
    assert row.grade == 5
    assert row.region == "北京"
    assert row.overall_mastery == 0.6
    assert row.weak_skills == ["fraction"]
    assert row.skill_mastery == {"fraction": 0.4, "decimal": 0.8}
    assert row.phase == state.phase
    assert row.updated_at is not None
    assert row.updated_at.tzinfo is not None


def test_list_all_metadata_defaults_without_diagnosis(tmp_path):
    store = SessionStore(tmp_path)
    state = store.create(StudentProfile(region="上海", grade=4, age=10))
    rows = store.list_all_metadata()
    assert len(rows) == 1
    row = rows[0]
    assert row.session_id == state.session_id
    assert row.nickname == "未命名"
    assert row.overall_mastery == 0.0
    assert row.weak_skills == []
    assert row.skill_mastery == {}
