"""Implicit learning-style inference from behavior features."""

from __future__ import annotations

from typing import Any


class LearningStyleInferer:
    """Bayesian-lite style inference without external ML deps."""

    PRIOR: dict[str, float] = {
        "visual": 0.35,
        "auditory": 0.25,
        "kinesthetic": 0.20,
        "reading": 0.20,
    }

    def infer(self, behavior: dict[str, Any]) -> str:
        posterior = self.posterior(behavior)
        return max(posterior, key=posterior.get)

    def posterior(self, behavior: dict[str, Any]) -> dict[str, float]:
        features = self._features(behavior)
        scores: dict[str, float] = {}
        for style, prior in self.PRIOR.items():
            scores[style] = prior * self._likelihood(features, style)
        total = sum(scores.values()) or 1.0
        return {k: v / total for k, v in scores.items()}

    @staticmethod
    def _features(behavior: dict[str, Any]) -> dict[str, float]:
        total_q = max(float(behavior.get("total_questions", 1) or 1), 1.0)
        visual_total = max(float(behavior.get("visual_question_total", 1) or 1), 1.0)
        return {
            "diagram_expand_rate": float(behavior.get("diagram_expand_count", 0) or 0)
            / total_q,
            "audio_play_rate": float(behavior.get("audio_play_count", 0) or 0) / total_q,
            "avg_response_time": float(behavior.get("avg_response_time", 0) or 0),
            "visual_question_correct_rate": float(
                behavior.get("visual_question_correct", 0) or 0
            )
            / visual_total,
        }

    @staticmethod
    def _likelihood(features: dict[str, float], style: str) -> float:
        diagram = features["diagram_expand_rate"]
        audio = features["audio_play_rate"]
        visual_acc = features["visual_question_correct_rate"]
        rt = features["avg_response_time"]
        if style == "visual":
            return 0.2 + 2.0 * diagram + 1.5 * visual_acc
        if style == "auditory":
            return 0.2 + 2.5 * audio
        if style == "kinesthetic":
            interaction = diagram + audio
            speed_boost = 1.0 if 0 < rt < 15 else 0.3
            return 0.2 + 1.2 * interaction + speed_boost
        # reading
        return 0.4 + (0.5 if diagram < 0.2 and audio < 0.2 else 0.1)
