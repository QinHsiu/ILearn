"""Tests for session lock manager."""

from __future__ import annotations

from ilearn.core.session_lock import SessionLockManager, session_lock_manager


def test_hold_is_reentrant():
    mgr = SessionLockManager()
    with mgr.hold("s1"):
        with mgr.hold("s1"):
            assert True


def test_global_manager_hold():
    with session_lock_manager.hold("abc"):
        lock = session_lock_manager.lock_for("abc")
        assert lock.acquire(blocking=False) is True
        lock.release()
