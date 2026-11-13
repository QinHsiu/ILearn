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
from ilearn.orchestration.derivation import derive_mastery
from ilearn.orchestration.migration import (
    DerivationSpec,
    MigrationReceipt,
    SkillMapping,
    StateMigrationContract,
)
from ilearn.orchestration.migration_replay import replay_migration
from ilearn.orchestration.migrator import StateMigrator
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
    "SkillMapping",
    "DerivationSpec",
    "StateMigrationContract",
    "MigrationReceipt",
    "StateMigrator",
    "replay_migration",
    "derive_mastery",
]


