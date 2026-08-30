"""Per-session threading locks for load-modify-save critical sections."""

from __future__ import annotations

import threading
from collections.abc import Iterator
from contextlib import contextmanager
from functools import wraps
from typing import Any, Callable, TypeVar

F = TypeVar("F", bound=Callable[..., Any])


class SessionLockManager:
    """Manage one RLock per session_id."""

    def __init__(self) -> None:
        self._guard = threading.Lock()
        self._locks: dict[str, threading.RLock] = {}

    def lock_for(self, session_id: str) -> threading.RLock:
        with self._guard:
            if session_id not in self._locks:
                self._locks[session_id] = threading.RLock()
            return self._locks[session_id]

    @contextmanager
    def hold(self, session_id: str) -> Iterator[None]:
        lock = self.lock_for(session_id)
        with lock:
            yield

    def clear(self) -> None:
        with self._guard:
            self._locks.clear()


session_lock_manager = SessionLockManager()


def with_session_lock(func: F) -> F:
    """Decorator for methods whose first arg after self is session_id."""

    @wraps(func)
    def wrapper(self: Any, session_id: str, *args: Any, **kwargs: Any) -> Any:
        with session_lock_manager.hold(session_id):
            return func(self, session_id, *args, **kwargs)

    return wrapper  # type: ignore[return-value]
