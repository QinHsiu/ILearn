"""P11: trajectory build + hash-chain replay."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from ilearn.audit.replay import replay_trajectory
from ilearn.audit.trajectory import build_trajectory


@pytest.fixture
def events_factory():
    now = datetime(2026, 11, 13, tzinfo=timezone.utc)

    def _make(triples: list[tuple[str, str, str]]):
        events = []
        for i, (etype, before, after) in enumerate(triples):
            events.append(
                {
                    "event_id": f"e{i}",
                    "event_type": etype,
                    "learner_id": "L1",
                    "occurred_at": now.replace(minute=i),
                    "prev_state_hash": before,
                    "state_hash": after,
                    "payload": {},
                }
            )
        return events

    return _make


def test_trajectory_detects_hash_chain_break(events_factory):
    events = events_factory(
        [
            ("mastery.update", "h0", "h1"),
            ("scheduler.dispatch", "h1", "h2"),
            ("scheduler.consumed", "XX", "h3"),
        ]
    )
    traj = build_trajectory(events, "L1")
    assert traj.is_contiguous is False


def test_trajectory_replay_passes_on_clean_chain(events_factory):
    events = events_factory(
        [
            ("mastery.update", "h0", "h1"),
            ("scheduler.dispatch", "h1", "h2"),
        ]
    )
    traj = build_trajectory(events, "L1")
    assert replay_trajectory(traj) is True
