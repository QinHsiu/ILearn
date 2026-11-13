"""Backward-compatible re-exports for orchestration templates."""

from ilearn.orchestration.k12_template import (
    AdultCompanionTemplate,
    K12MathHostTemplate,
    K12Template,
)
from ilearn.orchestration.registry import TemplateRegistry
from ilearn.orchestration.template import StateMachineTemplate

__all__ = [
    "StateMachineTemplate",
    "K12Template",
    "K12MathHostTemplate",
    "AdultCompanionTemplate",
    "TemplateRegistry",
]
