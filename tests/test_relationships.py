import pytest

from ilearn.core.schemas import StudentProfile
from ilearn.storage.relationships import RelationshipStore
from ilearn.storage.sessions import SessionStore


def test_parent_binding_is_idempotent_and_explicit(tmp_path):
    sessions = SessionStore(tmp_path / "sessions")
    session = sessions.create(StudentProfile(region="北京", grade=5, age=11))
    store = RelationshipStore(tmp_path / "relationships.json", sessions)
    store.bind_parent("p1", session.session_id)
    store.bind_parent("p1", session.session_id)
    assert store.children_for_parent("p1") == [session.session_id]
    assert store.children_for_parent("p2") == []


def test_teacher_binding_isolated_by_teacher_and_class(tmp_path):
    sessions = SessionStore(tmp_path / "sessions")
    a = sessions.create(StudentProfile(region="北京", grade=5, age=11))
    b = sessions.create(StudentProfile(region="北京", grade=5, age=11))
    store = RelationshipStore(tmp_path / "relationships.json", sessions)
    store.bind_teacher("t1", "c1", a.session_id)
    store.bind_teacher("t1", "c2", b.session_id)
    assert store.classes_for_teacher("t1") == ["c1", "c2"]
    assert store.students_for_class("t1", "c1") == [a.session_id]
    assert store.students_for_class("t2", "c1") == []


def test_binding_unknown_session_fails(tmp_path):
    store = RelationshipStore(
        tmp_path / "relationships.json",
        SessionStore(tmp_path / "sessions"),
    )
    with pytest.raises(FileNotFoundError):
        store.bind_parent("p1", "missing")
