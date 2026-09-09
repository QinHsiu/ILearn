"""Five-dimensional student profile models (edition_0909_1 §1.1).

Note: ``CognitiveDimension`` here is a Pydantic **model**, not the Bloom
``CognitiveDimension`` Enum in ``ilearn.core.cognitive_profile``.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

from ilearn.core.datetime_utils import utc_now


class BloomLevel(str, Enum):
    REMEMBER = "remember"
    UNDERSTAND = "understand"
    APPLY = "apply"
    ANALYZE = "analyze"
    EVALUATE = "evaluate"
    CREATE = "create"


class EmotionType(str, Enum):
    NEUTRAL = "neutral"
    CONFUSED = "confused"
    FRUSTRATED = "frustrated"
    EXCITED = "excited"
    BORED = "bored"
    ENGAGED = "engaged"


class LearningStyle(str, Enum):
    GUIDED = "guided"
    EXPLORATORY = "exploratory"
    VISUAL = "visual"
    VERBAL = "verbal"


class CognitiveDimension(BaseModel):
    """Cognitive slice: mastery + Bloom level."""

    knowledge_mastery: dict[str, float] = Field(default_factory=dict)
    bloom_level: BloomLevel = BloomLevel.REMEMBER
    weak_concepts: list[str] = Field(default_factory=list)
    strong_concepts: list[str] = Field(default_factory=list)
    concept_attempts: dict[str, int] = Field(default_factory=dict)
    concept_correct: dict[str, int] = Field(default_factory=dict)


class BehavioralDimension(BaseModel):
    """Behavioral slice: engagement and habits."""

    avg_session_duration: float = 0.0
    total_sessions: int = 0
    question_frequency: float = 0.0
    engagement_score: float = 0.5
    preferred_learning_time: str = "morning"
    completion_rate: float = 0.0
    avg_response_time: float = 0.0


class EmotionalDimension(BaseModel):
    """Emotional slice: affect and motivation."""

    current_emotion: EmotionType = EmotionType.NEUTRAL
    emotion_history: list[dict[str, Any]] = Field(default_factory=list)
    motivation_level: float = 0.5
    confidence_score: float = 0.5
    frustration_triggers: list[str] = Field(default_factory=list)
    encouragement_needed: bool = False
    engagement_trend: list[float] = Field(default_factory=list)


class MetacognitiveDimension(BaseModel):
    """Metacognitive slice: strategies and reflection."""

    learning_style: LearningStyle = LearningStyle.GUIDED
    reflection_ability: float = 0.5
    strategy_preference: list[str] = Field(default_factory=list)
    self_correction_rate: float = 0.0
    help_seeking_behavior: float = 0.5


class ContextualDimension(BaseModel):
    """Contextual slice: grade, subject, goals."""

    grade: str = ""
    subject: str = ""
    region: str = ""
    school: str = ""
    syllabus_version: str = ""
    learning_goal: str = ""
    current_unit: str = ""


class StudentFiveDimProfile(BaseModel):
    """Integrated five-dimensional learner profile."""

    student_id: str
    cognitive: CognitiveDimension = Field(default_factory=CognitiveDimension)
    behavioral: BehavioralDimension = Field(default_factory=BehavioralDimension)
    emotional: EmotionalDimension = Field(default_factory=EmotionalDimension)
    metacognitive: MetacognitiveDimension = Field(
        default_factory=MetacognitiveDimension
    )
    contextual: ContextualDimension = Field(default_factory=ContextualDimension)
    last_updated: datetime = Field(default_factory=utc_now)
    update_history: list[dict[str, Any]] = Field(default_factory=list)
    version: int = 1

    def get_mastery_for_concept(self, concept: str) -> float:
        return self.cognitive.knowledge_mastery.get(concept, 0.5)

    def get_overall_mastery(self) -> float:
        if not self.cognitive.knowledge_mastery:
            return 0.5
        values = self.cognitive.knowledge_mastery.values()
        return sum(values) / len(values)

    def get_weakest_concepts(self, top_n: int = 5) -> list[tuple[str, float]]:
        sorted_concepts = sorted(
            self.cognitive.knowledge_mastery.items(),
            key=lambda x: x[1],
        )
        return sorted_concepts[:top_n]

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")
