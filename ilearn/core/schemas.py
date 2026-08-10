"""Pydantic models shared across the ILearn MVP pipeline."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

ERROR_TAGS = ("concept_gap", "calc_error", "misread", "method_wrong", "incomplete")

ErrorTag = Literal["concept_gap", "calc_error", "misread", "method_wrong", "incomplete"]
GradeLevel = Literal[4, 5, 6]
ItemType = Literal["choice", "fill", "constructed"]
Difficulty = Literal["easy", "medium", "hard"]
MasteryLevel = Literal["mastered", "unstable", "weak"]
StepStatus = Literal["correct", "incorrect", "partial"]
HintLevel = Literal["none", "low", "medium", "high"]


class StudentProfile(BaseModel):
    """Learner context collected at session start."""

    region: str
    grade: Literal[4, 5, 6]
    age: int = Field(ge=6, le=18)


class KnowledgeNode(BaseModel):
    """Curriculum knowledge unit from the pilot pack."""

    id: str
    grade: Literal[4, 5, 6]
    name: str
    ability_tags: list[str] = Field(default_factory=list)


class ItemTemplate(BaseModel):
    """Parameterized item blueprint with optional slot placeholders."""

    id: str
    knowledge_ids: list[str]
    grade: Literal[4, 5, 6]
    item_type: ItemType
    difficulty: Difficulty
    stem_template: str
    answer_template: str | None = None
    rubric_steps: list[str] = Field(default_factory=list)
    choices_template: list[str] | None = None
    slot_names: list[str] = Field(default_factory=list)


class AssessmentItem(BaseModel):
    """Instantiated assessment question ready for delivery."""

    id: str
    stem: str
    type: ItemType
    difficulty: Difficulty
    knowledge_ids: list[str]
    answer_key: str | None = None
    rubric_steps: list[str] = Field(default_factory=list)
    choices: list[str] | None = None


class AssessmentPaper(BaseModel):
    """Fixed-size assessment paper assembled from pilot templates."""

    items: list[AssessmentItem]
    grade: Literal[4, 5, 6]
    curriculum_label: str
    created_at: datetime = Field(default_factory=datetime.utcnow)


class StudentAnswer(BaseModel):
    """Text answer submitted for a single item."""

    item_id: str
    answer_text: str


class StepResult(BaseModel):
    """Per-step grading outcome aligned to rubric_steps."""

    step_index: int = Field(ge=0)
    step_text: str
    status: StepStatus
    comment: str = ""


class GradeResult(BaseModel):
    """Step-level grading output for one assessment item (spec §5.1)."""

    item_id: str
    final_correct: bool
    steps: list[str] = Field(default_factory=list)
    step_results: list[StepResult] = Field(default_factory=list)
    error_tags: list[ErrorTag] = Field(default_factory=list)
    knowledge_ids: list[str] = Field(default_factory=list)
    hint_level_suggestion: HintLevel = "none"
    grading_degraded: bool = False


class KnowledgeMastery(BaseModel):
    """Aggregated mastery for one knowledge node."""

    knowledge_id: str
    score_rate: float = Field(ge=0.0, le=1.0)
    error_tag_counts: dict[str, int] = Field(default_factory=dict)
    level: MasteryLevel
    item_ids: list[str] = Field(default_factory=list)


class Intervention(BaseModel):
    """Prioritized remediation target (Top-5 cap applied downstream)."""

    knowledge_id: str
    title: str
    why: str
    what_to_fix_first: str
    priority: int = Field(ge=1)


class DiagnosisReport(BaseModel):
    """Learning-situation diagnosis after grading."""

    knowledge_mastery: list[KnowledgeMastery] = Field(default_factory=list)
    interventions: list[Intervention] = Field(default_factory=list)
    ability_scores: dict[str, float] = Field(default_factory=dict)
    curriculum_label: str
    region_mismatch_disclaimer: str | None = None


class PlanDay(BaseModel):
    """Single day entry in a learning plan."""

    day: int = Field(ge=1)
    focus_knowledge_ids: list[str] = Field(default_factory=list)
    tasks: list[str] = Field(default_factory=list)
    minutes: int = Field(ge=5, le=180)


class LearningPlanReport(BaseModel):
    """Structured and narrative learning plan after diagnosis."""

    goal: str
    milestones: list[str] = Field(default_factory=list)
    days: list[PlanDay] = Field(default_factory=list)
    markdown: str
    disclaimer: str = "本计划为智能助手建议，不能替代教师专业评价。"


class SessionState(BaseModel):
    """Persisted session artifact spanning the full MVP loop."""

    session_id: str
    profile: StudentProfile
    paper: AssessmentPaper | None = None
    answers: list[StudentAnswer] = Field(default_factory=list)
    grades: list[GradeResult] = Field(default_factory=list)
    diagnosis: DiagnosisReport | None = None
    plan: LearningPlanReport | None = None
