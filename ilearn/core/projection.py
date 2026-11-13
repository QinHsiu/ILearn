"""Fold append-only StateEvents into current LearnerState (audit-replay shared)."""

from __future__ import annotations

from pathlib import Path

from ilearn.core.learner_state import LearnerState
from ilearn.core.state_event import StateEvent


def project(events: list[StateEvent], initial: LearnerState) -> LearnerState:
    state = initial if initial.state_hash else initial.seal_initial()
    for ev in events:
        if ev.prev_state_hash != state.state_hash:
            raise AssertionError(
                f"hash chain broken at {ev.event_id}: "
                f"expected prev={state.state_hash}, got={ev.prev_state_hash}"
            )
        state = state.apply(ev)
    return state


def verify_chain(events: list[StateEvent], initial: LearnerState) -> bool:
    try:
        project(events, initial)
        return True
    except (AssertionError, ValueError):
        return False


def load_latest_state(
    learner_id: str,
    *,
    learners_root: str | Path | None = None,
) -> LearnerState:
    """Load projected LearnerState from disk (CLI / scheduler entry)."""
    from ilearn.storage.learner_state_store import LearnerStateStore

    root = Path(learners_root) if learners_root else Path("data/learners")
    return LearnerStateStore(root).load(learner_id)


def load_state_at(
    learner_id: str,
    version: int,
    *,
    learners_root: str | Path | None = None,
) -> LearnerState:
    """Project events only up to the given state version."""
    from ilearn.storage.learner_state_store import LearnerStateStore

    root = Path(learners_root) if learners_root else Path("data/learners")
    store = LearnerStateStore(root)
    initial = LearnerState(learner_id=learner_id).seal_initial()
    events = store.load_events(learner_id)
    state = initial
    for ev in events:
        state = state.apply(ev)
        if state.version == version:
            return state
    raise LookupError(f"version {version} not found for learner={learner_id}")
