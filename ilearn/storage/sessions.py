"""JSON persistence for ILearn session state."""

from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from ilearn.core.schemas import SessionState, StudentProfile


class SessionStore:
    """Persist one validated ``SessionState`` per JSON file."""

    def __init__(self, root: str | Path) -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def create(self, profile: StudentProfile) -> SessionState:
        state = SessionState(session_id=uuid4().hex, profile=profile)
        return self.save(state)

    def save(self, state: SessionState) -> SessionState:
        path = self._path(state.session_id)
        path.write_text(state.model_dump_json(indent=2), encoding="utf-8")
        return state

    def load(self, session_id: str) -> SessionState:
        path = self._path(session_id)
        if not path.is_file():
            raise FileNotFoundError(f"session not found: {session_id}")
        return SessionState.model_validate_json(path.read_text(encoding="utf-8"))

    def _path(self, session_id: str) -> Path:
        if not session_id or Path(session_id).name != session_id:
            raise ValueError("session_id must be a non-empty file-safe identifier")
        return self.root / f"{session_id}.json"
