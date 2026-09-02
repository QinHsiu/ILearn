"""Explicit parent and teacher relationship bindings."""

from __future__ import annotations

import json
from pathlib import Path

from ilearn.storage.sessions import SessionStore


class RelationshipStore:
    """Persist parent-child and teacher-class-student bindings in one JSON file."""

    def __init__(self, root: str | Path, sessions: SessionStore) -> None:
        self._path = Path(root)
        self._sessions = sessions

    def bind_parent(self, parent_id: str, session_id: str) -> None:
        parent_id = self._require_id(parent_id, "parent_id")
        session_id = self._require_session(session_id)
        data = self._load()
        children = data["parents"].setdefault(parent_id, [])
        if session_id not in children:
            children.append(session_id)
        self._save(data)

    def bind_teacher(self, teacher_id: str, class_id: str, session_id: str) -> None:
        teacher_id = self._require_id(teacher_id, "teacher_id")
        class_id = self._require_id(class_id, "class_id")
        session_id = self._require_session(session_id)
        data = self._load()
        classes = data["teachers"].setdefault(teacher_id, {})
        students = classes.setdefault(class_id, [])
        if session_id not in students:
            students.append(session_id)
        self._save(data)

    def children_for_parent(self, parent_id: str) -> list[str]:
        parent_id = self._require_id(parent_id, "parent_id")
        data = self._load()
        return list(data["parents"].get(parent_id, []))

    def classes_for_teacher(self, teacher_id: str) -> list[str]:
        teacher_id = self._require_id(teacher_id, "teacher_id")
        data = self._load()
        return list(data["teachers"].get(teacher_id, {}).keys())

    def students_for_class(self, teacher_id: str, class_id: str) -> list[str]:
        teacher_id = self._require_id(teacher_id, "teacher_id")
        class_id = self._require_id(class_id, "class_id")
        data = self._load()
        return list(data["teachers"].get(teacher_id, {}).get(class_id, []))

    def reconcile(self) -> list[str]:
        """Drop bindings whose session JSON files no longer exist."""
        data = self._load()
        removed: list[str] = []

        for parent_id, children in data["parents"].items():
            kept = [sid for sid in children if self._sessions.exists(sid)]
            for sid in children:
                if sid not in kept:
                    removed.append(sid)
            data["parents"][parent_id] = kept

        for teacher_id, classes in data["teachers"].items():
            for class_id, students in list(classes.items()):
                kept = [sid for sid in students if self._sessions.exists(sid)]
                for sid in students:
                    if sid not in kept:
                        removed.append(sid)
                classes[class_id] = kept

        if removed:
            self._save(data)
        return list(dict.fromkeys(removed))

    def _require_id(self, value: str, field: str) -> str:
        trimmed = (value or "").strip()
        if not trimmed:
            raise ValueError(f"{field} must be non-empty")
        return trimmed

    def _require_session(self, session_id: str) -> str:
        session_id = self._require_id(session_id, "session_id")
        self._sessions.load(session_id)
        return session_id

    def _load(self) -> dict:
        if not self._path.is_file():
            return {"parents": {}, "teachers": {}}
        payload = json.loads(self._path.read_text(encoding="utf-8"))
        payload.setdefault("parents", {})
        payload.setdefault("teachers", {})
        return payload

    def _save(self, data: dict) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self._path.with_name(f"{self._path.name}.tmp")
        tmp.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        tmp.replace(self._path)
