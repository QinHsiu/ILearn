"""State-machine template protocol — lifecycle workflows without hardcoding backend."""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class StateMachineTemplate(Protocol):
    template_id: str
    applicable_stages: set[str]
    goal_affinity: dict[str, float]

    def initial_state(self) -> str: ...

    def transitions(self, state: str, event_type: str) -> str | None: ...
