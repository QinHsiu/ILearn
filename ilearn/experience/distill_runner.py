"""Run distillation and append experience.distilled events (auditable, idempotent)."""

from __future__ import annotations

from typing import Protocol

from ilearn.experience.distiller import distill_candidates
from ilearn.experience.store import ExperienceStore


class EventLogWriter(Protocol):
    def append(self, event_type: str, payload: dict, learner_id: str) -> str: ...


def run_distillation(
    store: ExperienceStore, event_log: EventLogWriter, learner_id: str
) -> list[str]:
    candidates = distill_candidates(list(store.records))
    created: list[str] = []
    for rec in candidates:
        if any(set(r.derived_from) == set(rec.derived_from) for r in store.records if r.form == "distilled"):
            continue
        store.add(rec)
        event_log.append(
            "experience.distilled",
            {
                "record_id": rec.record_id,
                "derived_from": rec.derived_from,
                "outcome": rec.outcome,
                "strategy": rec.strategy,
            },
            learner_id,
        )
        created.append(rec.record_id)
    return created
