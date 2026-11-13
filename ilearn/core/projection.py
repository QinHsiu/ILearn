"""Fold append-only StateEvents into current LearnerState (audit-replay shared)."""

from __future__ import annotations

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
