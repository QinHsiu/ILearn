"""JSON persistence for ILearn session state."""

from __future__ import annotations

import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from ilearn.core.schemas import SessionMetadata, SessionState, StudentProfile

_WEAK_SKILL_THRESHOLD = 0.6
_DEFAULT_CACHE_TTL = 300.0


def _to_metadata(state: SessionState, path: Path) -> SessionMetadata:
    nickname = (state.profile.nickname or "").strip() or "未命名"
    skill_mastery: dict[str, float] = {}
    weak_skills: list[str] = []
    overall_mastery = 0.0

    if state.diagnosis and state.diagnosis.knowledge_mastery:
        rows = state.diagnosis.knowledge_mastery
        skill_mastery = {row.knowledge_id: row.score_rate for row in rows}
        weak_skills = [
            row.knowledge_id
            for row in rows
            if row.score_rate < _WEAK_SKILL_THRESHOLD
        ]
        overall_mastery = sum(row.score_rate for row in rows) / len(rows)

    updated_at = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)

    return SessionMetadata(
        session_id=state.session_id,
        nickname=nickname,
        grade=state.profile.grade,
        region=state.profile.region,
        overall_mastery=overall_mastery,
        weak_skills=weak_skills,
        skill_mastery=skill_mastery,
        updated_at=updated_at,
        phase=state.phase,
    )


class SessionStore:
    """Persist one validated ``SessionState`` per JSON file (per-session locks)."""

    def __init__(
        self,
        root: str | Path,
        *,
        cache_ttl: float = _DEFAULT_CACHE_TTL,
    ) -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self._lock_guard = threading.Lock()
        self._session_locks: dict[str, threading.RLock] = {}
        self._list_lock = threading.RLock()
        self._cache_ttl = cache_ttl
        self._cache: dict[str, SessionState] = {}
        self._cache_expires: dict[str, float] = {}

    def _lock_for(self, session_id: str) -> threading.RLock:
        with self._lock_guard:
            if session_id not in self._session_locks:
                self._session_locks[session_id] = threading.RLock()
            return self._session_locks[session_id]

    def create(self, profile: StudentProfile) -> SessionState:
        state = SessionState(session_id=uuid4().hex, profile=profile)
        return self.save(state)

    def save(self, state: SessionState) -> SessionState:
        with self._lock_for(state.session_id):
            path = self._path(state.session_id)
            path.write_text(state.model_dump_json(indent=2), encoding="utf-8")
            self._cache_put(state)
            return state

    def load(self, session_id: str) -> SessionState:
        with self._lock_for(session_id):
            cached = self._cache_get(session_id)
            if cached is not None:
                return cached.model_copy(deep=True)
            path = self._path(session_id)
            if not path.is_file():
                raise FileNotFoundError(f"session not found: {session_id}")
            state = SessionState.model_validate_json(path.read_text(encoding="utf-8"))
            self._cache_put(state)
            return state.model_copy(deep=True)

    def list_all(self) -> list[SessionState]:
        with self._list_lock:
            rows: list[SessionState] = []
            for path in sorted(self.root.glob("*.json")):
                rows.append(
                    SessionState.model_validate_json(path.read_text(encoding="utf-8"))
                )
            return rows

    def list_all_metadata(self) -> list[SessionMetadata]:
        with self._list_lock:
            rows: list[SessionMetadata] = []
            for path in sorted(self.root.glob("*.json")):
                state = SessionState.model_validate_json(path.read_text(encoding="utf-8"))
                rows.append(_to_metadata(state, path))
            return rows

    def list_by_nickname(self, nickname: str) -> list[SessionState]:
        needle = (nickname or "").strip().casefold()
        if not needle:
            return []
        return [
            row
            for row in self.list_all()
            if (row.profile.nickname or "").strip().casefold() == needle
        ]

    def delete(self, session_id: str) -> None:
        with self._lock_for(session_id):
            path = self._path(session_id)
            if not path.is_file():
                raise FileNotFoundError(f"session not found: {session_id}")
            path.unlink()
            self._cache.pop(session_id, None)
            self._cache_expires.pop(session_id, None)

    def clear_cache(self) -> None:
        with self._list_lock:
            self._cache.clear()
            self._cache_expires.clear()

    def _cache_get(self, session_id: str) -> SessionState | None:
        expires = self._cache_expires.get(session_id)
        if expires is None or session_id not in self._cache:
            return None
        if time.time() > expires:
            self._cache.pop(session_id, None)
            self._cache_expires.pop(session_id, None)
            return None
        return self._cache[session_id]

    def _cache_put(self, state: SessionState) -> None:
        self._cache[state.session_id] = state.model_copy(deep=True)
        self._cache_expires[state.session_id] = time.time() + self._cache_ttl

    def _path(self, session_id: str) -> Path:
        if not session_id or Path(session_id).name != session_id:
            raise ValueError("session_id must be a non-empty file-safe identifier")
        return self.root / f"{session_id}.json"
