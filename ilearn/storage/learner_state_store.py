"""Persist versioned LearnerState + append-only StateEvent log per learner."""

from __future__ import annotations

import json
import threading
from pathlib import Path

from ilearn.core.learner_state import LearnerState
from ilearn.core.projection import project
from ilearn.core.state_event import StateEvent


class LearnerStateStore:
    """Single-writer store: events.jsonl is source of truth; state.json is cache."""

    def __init__(self, root: str | Path) -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self._locks: dict[str, threading.RLock] = {}
        self._guard = threading.Lock()

    def _lock(self, learner_id: str) -> threading.RLock:
        with self._guard:
            if learner_id not in self._locks:
                self._locks[learner_id] = threading.RLock()
            return self._locks[learner_id]

    def _dir(self, learner_id: str) -> Path:
        safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in learner_id)
        path = self.root / safe
        path.mkdir(parents=True, exist_ok=True)
        return path

    def load_events(self, learner_id: str) -> list[StateEvent]:
        path = self._dir(learner_id) / "events.jsonl"
        if not path.exists():
            return []
        events: list[StateEvent] = []
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line:
                events.append(StateEvent.model_validate_json(line))
        return events

    def load(self, learner_id: str) -> LearnerState:
        with self._lock(learner_id):
            initial = LearnerState(learner_id=learner_id).seal_initial()
            events = self.load_events(learner_id)
            if not events:
                return initial
            return project(events, initial)

    def append(self, learner_id: str, event: StateEvent) -> LearnerState:
        """Append sealed event under single-writer lock; return new state."""
        with self._lock(learner_id):
            state = self.load(learner_id)
            if not event.prev_state_hash:
                event = event.model_copy(update={"prev_state_hash": state.state_hash})
            sealed = event.seal()
            new_state = state.apply(sealed)
            events_path = self._dir(learner_id) / "events.jsonl"
            with events_path.open("a", encoding="utf-8") as fh:
                fh.write(sealed.model_dump_json() + "\n")
            state_path = self._dir(learner_id) / "state.json"
            state_path.write_text(
                new_state.model_dump_json(indent=2), encoding="utf-8"
            )
            return new_state

    def append_many(self, learner_id: str, events: list[StateEvent]) -> LearnerState:
        state = self.load(learner_id)
        for ev in events:
            payload = ev.model_copy(update={"learner_id": learner_id})
            if not payload.prev_state_hash:
                payload = payload.model_copy(update={"prev_state_hash": state.state_hash})
            state = self.append(learner_id, payload)
        return state
