"""Swappable orchestration backends. Default is the host state machine."""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class OrchestrationBackend(Protocol):
    """Agents must not call framework-specific APIs; talk to this facade only."""

    name: str

    def require_runtime(self) -> None:
        """Raise if the optional runtime dependency is unavailable."""


class HostStateMachineBackend:
    """Default backend: ILearn's in-process session phase state machine."""

    name = "host_state_machine"

    def require_runtime(self) -> None:
        return None


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
