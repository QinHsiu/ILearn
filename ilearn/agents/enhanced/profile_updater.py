"""Five-dim profile updater agent (edition_0909_2 / PR02)."""

from __future__ import annotations

from typing import Any

from ilearn.agents.enhanced.base import EnhancedAgentBase
from ilearn.core.enhanced_flags import is_enhanced_enabled
from ilearn.core.enhanced_profile_adapter import ProfileAdapter
from ilearn.core.enhanced_session import get_enhanced_profile, set_enhanced_profile
from ilearn.core.models.enhanced_profile import (
    EmotionType,
    LearningStyle,
    StudentFiveDimProfile,
)
from ilearn.core.schemas import SessionState
from ilearn.providers.llm import LLMClient


class CognitiveSubAgent:
    def update(
        self, profile: StudentFiveDimProfile, signals: dict[str, Any]
    ) -> StudentFiveDimProfile:
        for kp, correct in (signals.get("knowledge_updates") or {}).items():
            old = profile.cognitive.knowledge_mastery.get(str(kp), 0.5)
            delta = 0.12 if correct else -0.12
            profile.cognitive.knowledge_mastery[str(kp)] = max(
                0.0, min(1.0, old + delta)
            )
        mastery = profile.cognitive.knowledge_mastery
        if mastery:
            profile.cognitive.weak_concepts = [
                k for k, v in mastery.items() if v < 0.6
            ]
            profile.cognitive.strong_concepts = [
                k for k, v in mastery.items() if v >= 0.8
            ]
        return profile


class EmotionalSubAgent:
    def update(
        self, profile: StudentFiveDimProfile, signals: dict[str, Any]
    ) -> StudentFiveDimProfile:
        raw = signals.get("emotion")
        if not raw:
            return profile
        try:
            profile.emotional.current_emotion = EmotionType(str(raw))
        except ValueError:
            profile.emotional.current_emotion = EmotionType.NEUTRAL
        return profile


class BehavioralSubAgent:
    def update(
        self, profile: StudentFiveDimProfile, signals: dict[str, Any]
    ) -> StudentFiveDimProfile:
        engagement = signals.get("engagement")
        if engagement is not None:
            try:
                profile.behavioral.engagement_score = max(
                    0.0, min(1.0, float(engagement))
                )
            except (TypeError, ValueError):
                pass
        return profile


class MetacognitiveSubAgent:
    def update(
        self, profile: StudentFiveDimProfile, signals: dict[str, Any]
    ) -> StudentFiveDimProfile:
        raw = signals.get("learning_style")
        if not raw:
            return profile
        try:
            profile.metacognitive.learning_style = LearningStyle(str(raw))
        except ValueError:
            profile.metacognitive.learning_style = LearningStyle.GUIDED
        return profile


class ProfileUpdaterAgent(EnhancedAgentBase):
    """Bootstrap / refresh five-dim profile on a SessionState."""

    def __init__(
        self,
        llm: LLMClient | None = None,
        *,
        stub_mode: bool = False,
    ) -> None:
        super().__init__(llm, stub_mode=stub_mode)
        self._cognitive = CognitiveSubAgent()
        self._emotional = EmotionalSubAgent()
        self._behavioral = BehavioralSubAgent()
        self._metacognitive = MetacognitiveSubAgent()

    def update_session(self, session: SessionState) -> SessionState:
        """Side-effect path used by orchestrator hooks."""
        if not is_enhanced_enabled("ENABLE_ENHANCED_AGENTS"):
            return session
        if not is_enhanced_enabled("ENABLE_ENHANCED_PROFILE"):
            return session
        profile = get_enhanced_profile(session) or ProfileAdapter.from_session(session)
        signals = self._extract_signals(session)
        profile = self._cognitive.update(profile, signals)
        profile = self._emotional.update(profile, signals)
        profile = self._behavioral.update(profile, signals)
        profile = self._metacognitive.update(profile, signals)
        profile.version = int(profile.version or 1) + 1
        return set_enhanced_profile(session, profile)

    def _execute(self, state: dict[str, Any]) -> dict[str, Any]:
        session = state.get("session")
        if not isinstance(session, SessionState):
            return {}
        updated = self.update_session(session)
        return {
            "profile_updated": get_enhanced_profile(updated) is not None,
            "session_id": updated.session_id,
        }

    def _extract_signals(self, session: SessionState) -> dict[str, Any]:
        if self.stub_mode:
            return self._stub_signals(session)
        payload = self._chat_json(
            "你是学情信号提取器，只输出 JSON。",
            (
                "从交互中提取五维信号，输出："
                '{"knowledge_updates":{"kp":true},"emotion":"neutral",'
                '"engagement":0.5,"learning_style":"guided"}\n'
                f"diagnosis={session.diagnosis.model_dump() if session.diagnosis else {}}"
            ),
        )
        if isinstance(payload, dict):
            return payload
        return self._stub_signals(session)

    @staticmethod
    def _stub_signals(session: SessionState) -> dict[str, Any]:
        updates: dict[str, bool] = {}
        if session.diagnosis and session.diagnosis.knowledge_mastery:
            for row in session.diagnosis.knowledge_mastery:
                updates[row.knowledge_id] = row.score_rate >= 0.6
        wrong = 0
        total = 0
        for grade in session.grades or []:
            total += 1
            if not grade.final_correct:
                wrong += 1
        emotion = "frustrated" if total and wrong / total >= 0.5 else "neutral"
        engagement = 0.7 if total and wrong / total < 0.5 else 0.4
        return {
            "knowledge_updates": updates,
            "emotion": emotion,
            "engagement": engagement,
            "learning_style": "guided",
        }
