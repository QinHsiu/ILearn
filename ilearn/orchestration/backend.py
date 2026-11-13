"""Swappable orchestration backends. Default is the host state machine."""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from ilearn.orchestration.k12_template import K12MathHostTemplate
from ilearn.orchestration.template import StateMachineTemplate


class UnexpectedTransition(Exception):
    """Raised when the active template has no edge for (state, event_type)."""

    def __init__(self, state: str, event_type: str) -> None:
        self.state = state
        self.event_type = event_type
        super().__init__(f"unexpected transition: state={state!r} event={event_type!r}")


@runtime_checkable
class OrchestrationBackend(Protocol):
    """Agents must not call framework-specific APIs; talk to this facade only."""

    name: str

    def require_runtime(self) -> None:
        """Raise if the optional runtime dependency is unavailable."""


class _NullEventLog:
    def append(self, event_type: str, payload: dict[str, Any], learner_id: str) -> str:
        return ""


class HostStateMachineBackend:
    """Default backend: ILearn's in-process session phase state machine.

    Consumes a StateMachineTemplate for transitions — inject a different template
    to switch lifecycle flows without rewriting agents.
    """

    name = "host_state_machine"

    def __init__(
        self,
        template: StateMachineTemplate | None = None,
        event_log: Any | None = None,
    ) -> None:
        self._template: StateMachineTemplate = template or K12MathHostTemplate()
        self._log = event_log or _NullEventLog()

    @property
    def template(self) -> StateMachineTemplate:
        return self._template

    def require_runtime(self) -> None:
        return None

    def advance(self, current: str, event_type: str) -> str:
        nxt = self._template.transitions(current, event_type)
        if nxt is None:
            self._log.append(
                "orchestration.unexpected",
                {"state": current, "event": event_type},
                "",
            )
            raise UnexpectedTransition(current, event_type)
        return nxt


class LangGraphBackend:
    """Optional stub — not a default dependency (Option A).

    Kept so documentation can name LangGraph as an isomorphic target without
    pulling it into the runtime graph. Agents must not import langgraph.
    """

    name = "langgraph"

    def require_runtime(self) -> None:
        raise NotImplementedError(
            "LangGraph is an optional orchestration adapter stub, not the "
            "default backend. Install/enable it explicitly if you add an adapter; "
            "ILearn's default is HostStateMachineBackend (state machine + event log)."
        )


def get_default_backend() -> HostStateMachineBackend:
    return HostStateMachineBackend()
