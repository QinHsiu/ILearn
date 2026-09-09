"""Knowledge Tracing protocol — all KT backends must implement this interface."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class KTInteraction:
    """Single KT interaction record."""

    concept: str
    correct: bool
    timestamp: float


class KnowledgeTracingService(ABC):
    """Knowledge tracing service protocol."""

    @abstractmethod
    def add_interaction(self, concept: str, correct: bool) -> None:
        """Record one interaction."""

    @abstractmethod
    def predict_mastery(
        self, concept_names: list[str] | None = None
    ) -> dict[str, float]:
        """Predict current mastery probability per concept."""

    @abstractmethod
    def get_attempt_count(self, concept: str) -> int:
        """Return total attempt count for a concept."""

    @abstractmethod
    def get_interactions(self, limit: int = 200) -> list[KTInteraction]:
        """Return interaction history for persistence."""

    @abstractmethod
    def get_state(self) -> dict[str, object]:
        """Return model state for persistence."""

    @abstractmethod
    def load_state(self, state: dict[str, object]) -> None:
        """Load model state from session persistence."""

    @abstractmethod
    def get_backend_name(self) -> str:
        """Return backend name: 'bkt', 'pykt', etc."""

    @abstractmethod
    def get_weak_concepts(
        self, threshold: float = 0.6, top_n: int = 5
    ) -> list[str]:
        """Return weak concepts sorted by ascending mastery."""
