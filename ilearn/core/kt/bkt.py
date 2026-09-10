"""Bayesian Knowledge Tracing — default implementation, no external deps."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime

from .protocol import KTInteraction, KnowledgeTracingService

logger = logging.getLogger(__name__)


@dataclass
class BKTConceptState:
    """BKT state for a single concept."""

    p_known: float = 0.5
    success: int = 0
    total: int = 0
    last_updated: float = 0.0


class BKTKnowledgeTracing(KnowledgeTracingService):
    """Bayesian knowledge tracing — each concept modeled independently."""

    def __init__(
        self,
        p_l0: float = 0.5,
        p_t: float = 0.1,
        p_s: float = 0.1,
        p_g: float = 0.2,
        max_interactions: int = 200,
    ) -> None:
        self.p_l0 = p_l0
        self.p_t = p_t
        self.p_s = p_s
        self.p_g = p_g
        self.max_interactions = max_interactions
        self._states: dict[str, BKTConceptState] = {}
        self._interactions: list[KTInteraction] = []

    def _get_or_create_state(self, concept: str) -> BKTConceptState:
        if concept not in self._states:
            self._states[concept] = BKTConceptState(
                p_known=self.p_l0,
                last_updated=datetime.now().timestamp(),
            )
        return self._states[concept]

    def add_interaction(self, concept: str, correct: bool) -> None:
        state = self._get_or_create_state(concept)
        state.total += 1
        if correct:
            state.success += 1

        p_known_old = state.p_known

        if correct:
            p_correct_given_known = 1.0 - self.p_s
            p_correct_given_not_known = self.p_g
            p_correct = (
                p_correct_given_known * p_known_old
                + p_correct_given_not_known * (1 - p_known_old)
            )
            if p_correct > 0:
                p_known_new = (p_correct_given_known * p_known_old) / p_correct
            else:
                p_known_new = p_known_old
        else:
            p_incorrect_given_known = self.p_s
            p_incorrect_given_not_known = 1.0 - self.p_g
            p_incorrect = (
                p_incorrect_given_known * p_known_old
                + p_incorrect_given_not_known * (1 - p_known_old)
            )
            if p_incorrect > 0:
                p_known_new = (p_incorrect_given_known * p_known_old) / p_incorrect
            else:
                p_known_new = p_known_old

        p_known_after_attempt = p_known_new + (1 - p_known_new) * self.p_t
        state.p_known = max(0.01, min(0.99, p_known_after_attempt))
        state.last_updated = datetime.now().timestamp()

        self._interactions.append(
            KTInteraction(
                concept=concept,
                correct=correct,
                timestamp=state.last_updated,
            )
        )
        if len(self._interactions) > self.max_interactions:
            self._interactions = self._interactions[-self.max_interactions :]

        logger.debug(
            "BKT: %s correct=%s, p_known: %.3f -> %.3f",
            concept,
            correct,
            p_known_old,
            state.p_known,
        )

    def predict_mastery(
        self, concept_names: list[str] | None = None
    ) -> dict[str, float]:
        if concept_names is None:
            targets = list(self._states.keys())
        else:
            targets = concept_names

        result: dict[str, float] = {}
        for concept in targets:
            if concept in self._states:
                result[concept] = self._states[concept].p_known
            else:
                result[concept] = self.p_l0
        return result

    def get_attempt_count(self, concept: str) -> int:
        if concept in self._states:
            return self._states[concept].total
        return 0

    def get_interactions(self, limit: int = 200) -> list[KTInteraction]:
        if len(self._interactions) > limit:
            return self._interactions[-limit:]
        return self._interactions.copy()

    def get_state(self) -> dict[str, object]:
        return {
            "backend": "bkt",
            "params": {
                "p_l0": self.p_l0,
                "p_t": self.p_t,
                "p_s": self.p_s,
                "p_g": self.p_g,
            },
            "states": {
                concept: {
                    "p_known": state.p_known,
                    "success": state.success,
                    "total": state.total,
                    "last_updated": state.last_updated,
                }
                for concept, state in self._states.items()
            },
            "interactions": [
                {
                    "concept": i.concept,
                    "correct": i.correct,
                    "timestamp": i.timestamp,
                }
                for i in self._interactions[-self.max_interactions :]
            ],
        }

    def load_state(self, state: dict[str, object]) -> None:
        if not state:
            return

        params = state.get("params", {})
        if isinstance(params, dict):
            self.p_l0 = float(params.get("p_l0", self.p_l0))
            self.p_t = float(params.get("p_t", self.p_t))
            self.p_s = float(params.get("p_s", self.p_s))
            self.p_g = float(params.get("p_g", self.p_g))

        states_data = state.get("states", {})
        if isinstance(states_data, dict):
            for concept, s in states_data.items():
                if not isinstance(s, dict):
                    continue
                self._states[concept] = BKTConceptState(
                    p_known=float(s.get("p_known", self.p_l0)),
                    success=int(s.get("success", 0)),
                    total=int(s.get("total", 0)),
                    last_updated=float(s.get("last_updated", 0.0)),
                )

        interactions = state.get("interactions", [])
        if isinstance(interactions, list):
            for i in interactions:
                if not isinstance(i, dict):
                    continue
                self._interactions.append(
                    KTInteraction(
                        concept=str(i.get("concept", "")),
                        correct=bool(i.get("correct", False)),
                        timestamp=float(i.get("timestamp", 0.0)),
                    )
                )

        if len(self._interactions) > self.max_interactions:
            self._interactions = self._interactions[-self.max_interactions :]

        logger.info(
            "BKT: Loaded state with %d concepts, %d interactions",
            len(self._states),
            len(self._interactions),
        )

    def get_backend_name(self) -> str:
        return "bkt"

    def get_weak_concepts(
        self, threshold: float = 0.6, top_n: int = 5
    ) -> list[str]:
        if not self._states:
            return []

        filtered = [
            (concept, state.p_known)
            for concept, state in self._states.items()
            if state.total >= 2
        ]
        if not filtered:
            return []

        sorted_items = sorted(filtered, key=lambda x: x[1])
        weak = [concept for concept, score in sorted_items if score < threshold]
        return weak[:top_n]
