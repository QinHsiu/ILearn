"""SessionStore cache/lock smoke."""

from __future__ import annotations

from ilearn.core.schemas import StudentProfile
from ilearn.storage.sessions import SessionStore


def test_load_uses_cache(tmp_path):
    store = SessionStore(tmp_path, cache_ttl=60)
    created = store.create(StudentProfile(region="北京", grade=5, age=11))
    path = store._path(created.session_id)
    path.write_text("CORRUPT", encoding="utf-8")
    # Cached copy should still load
    loaded = store.load(created.session_id)
    assert loaded.session_id == created.session_id
