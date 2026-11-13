"""Swappable orchestration backends + event-sourced decision log."""

from ilearn.orchestration.backend import (
    HostStateMachineBackend,
    LangGraphBackend,
    OrchestrationBackend,
    UnexpectedTransition,
    get_default_backend,
)
from ilearn.orchestration.k12_template import (
    AdultCompanionTemplate,
    K12MathHostTemplate,
    K12Template,
)
from ilearn.orchestration.registry import TemplateRegistry
from ilearn.orchestration.template import StateMachineTemplate

__all__ = [
    "HostStateMachineBackend",
    "LangGraphBackend",
    "OrchestrationBackend",
    "UnexpectedTransition",
    "get_default_backend",
    "StateMachineTemplate",
    "K12Template",
    "K12MathHostTemplate",
    "AdultCompanionTemplate",
    "TemplateRegistry",
]
