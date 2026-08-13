from ilearn.core.schemas import StudentProfile
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
