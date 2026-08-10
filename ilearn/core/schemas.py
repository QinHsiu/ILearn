"""Pydantic models shared across the ILearn MVP pipeline."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, Field

from ilearn.core.datetime_utils import utc_now


def _new_evidence_id() -> str:
    return uuid4().hex

ERROR_TAGS = ("concept_gap", "calc_error", "misread", "method_wrong", "incomplete")

ErrorTag = Literal["concept_gap", "calc_error", "misread", "method_wrong", "incomplete"]
GradeLevel = Literal[4, 5, 6]
ItemType = Literal["choice", "fill", "constructed"]
Difficulty = Literal["easy", "medium", "hard"]
MasteryLevel = Literal["mastered", "unstable", "weak"]
StepStatus = Literal["correct", "incorrect", "partial"]
HintLevel = Literal["none", "low", "medium", "high"]
EvidenceLane = Literal["practice", "probe"]
PlanStatus = Literal["draft", "approved", "superseded"]
TutorPhase = Literal["locate_gap", "hint_1", "hint_2", "retry", "explain", "done"]


class SessionPhase(str, Enum):
    ONBOARD = "onboard"
    ASSESS = "assess"
    PRACTICE = "practice"
    GRADE = "grade"
    DIAGNOSE = "diagnose"
    PLAN = "plan"
    PRACTICE_LOOP = "practice_loop"


class StudentProfile(BaseModel):
    """Learner context collected at session start."""

    region: str
    grade: Literal[4, 5, 6]
    age: int = Field(ge=6, le=18)


KcType = Literal["fact", "skill", "principle"]


class KnowledgeNode(BaseModel):
    """Curriculum knowledge unit from the pilot pack."""

    id: str
    grade: Literal[4, 5, 6]
    name: str
    ability_tags: list[str] = Field(default_factory=list)
    kc_type: KcType | None = None


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
    curriculum_objective_ids: list[str] = Field(default_factory=list)


class BlueprintSlot(BaseModel):
    """Single slot in a fixed 20-item paper blueprint."""

    difficulty: Difficulty
    item_type: ItemType
    knowledge_id: str | None = None


class PaperBlueprint(BaseModel):
    """Two-phase paper assembly plan matching MIX_BLUEPRINT quotas."""

    grade: Literal[4, 5, 6]
    slots: list[BlueprintSlot]


class AssessmentPaper(BaseModel):
    """Fixed-size assessment paper assembled from pilot templates."""

    items: list[AssessmentItem]
    grade: Literal[4, 5, 6]
    curriculum_label: str
    created_at: datetime = Field(default_factory=utc_now)
    blueprint: PaperBlueprint | None = None
    paper_version: str = "1.0.0"


class StudentAnswer(BaseModel):
    """Text answer submitted for a single item."""

    item_id: str
    answer_text: str


class ImageAnswer(BaseModel):
    item_id: str
    image_base64: str
    mime_type: Literal["image/png", "image/jpeg", "image/webp"] = "image/png"


class StepResult(BaseModel):
    """Per-step grading outcome aligned to rubric_steps."""

    step_index: int = Field(ge=0)
    step_text: str
    status: StepStatus
    comment: str = ""


class StepAttempt(BaseModel):
    """Student work on a single rubric step before grading."""

    item_id: str
    step_index: int = Field(ge=0)
    step_text: str
    student_expression: str
    lane: EvidenceLane = "practice"
    hint_level: HintLevel = "none"


class StepVerdict(BaseModel):
    """Grader verdict for one rubric step."""

    step_index: int = Field(ge=0)
    status: StepStatus
    comment: str = ""


class KnowledgeEvidence(BaseModel):
    """Observed evidence linking an item attempt to a knowledge node."""

    evidence_id: str = Field(default_factory=_new_evidence_id)
    session_id: str
    item_id: str
    knowledge_id: str
    lane: EvidenceLane
    correct: bool
    error_tag: ErrorTag | None = None
    hint_level: HintLevel = "none"
    confidence: float = Field(ge=0.0, le=1.0, default=1.0)
    step_index: int | None = None
    created_at: datetime = Field(default_factory=utc_now)


class GradingReceipt(BaseModel):
    """Provenance metadata binding a grade to its source paper and grader."""

    paper_created_at: datetime
    grader_version: str
    model_id: str | None = None
    graded_at: datetime = Field(default_factory=utc_now)
    ocr_confidence: float | None = None
    ocr_degraded: bool | None = None


class MasteryRecord(BaseModel):
    """Dual-lane mastery tracking: practice vs unassisted probe."""

    practice_score: float = Field(ge=0.0, le=1.0, default=0.0)
    probe_mastery: float = Field(ge=0.0, le=1.0, default=0.0)
    evidence_count: int = 0
    last_probe_at: datetime | None = None


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
    lane: EvidenceLane = "practice"
    receipt: GradingReceipt | None = None


class KnowledgeMastery(BaseModel):
    """Aggregated mastery for one knowledge node."""

    knowledge_id: str
    knowledge_name: str | None = None
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
    leech: bool = False
    evidence_ids: list[str] = Field(default_factory=list)
    curriculum_objective_ids: list[str] = Field(default_factory=list)


class DiagnosisReport(BaseModel):
    """Learning-situation diagnosis after grading."""

    knowledge_mastery: list[KnowledgeMastery] = Field(default_factory=list)
    interventions: list[Intervention] = Field(default_factory=list)
    ability_scores: dict[str, float] = Field(default_factory=dict)
    curriculum_label: str
    region_mismatch_disclaimer: str | None = None
    evidence_refs: list[str] = Field(default_factory=list)
    flags: list[str] = Field(default_factory=list)


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
    version: int = 1
    status: PlanStatus = "draft"


class PlanVersion(BaseModel):
    """Historical snapshot of a learning plan with lifecycle status."""

    version: int = 1
    status: PlanStatus = "draft"
    plan: LearningPlanReport
    created_at: datetime = Field(default_factory=utc_now)


class TutorTurn(BaseModel):
    """Single turn in the Socratic tutor dialogue."""

    phase: TutorPhase
    message: str
    error_tag: ErrorTag | None = None


class WeaknessEntry(BaseModel):
    knowledge_id: str
    topic: str
    logic_gap: str
    session_id: str
    created_at: datetime = Field(default_factory=utc_now)


class WeaknessEvent(BaseModel):
    knowledge_id: str
    step_index: int | None = None
    error_tag: ErrorTag | None = None
    confidence: float = 1.0
    evidence_id: str | None = None
    session_id: str = ""
    created_at: datetime = Field(default_factory=utc_now)


class PortraitDimensions(BaseModel):
    """Five-dimension learner portrait extension (OPT-022)."""

    cognitive: dict[str, float] = Field(default_factory=dict)
    behavioral: dict[str, float] = Field(default_factory=dict)
    emotional: dict[str, float] = Field(default_factory=dict)
    metacognitive: dict[str, float] = Field(default_factory=dict)
    contextual: dict[str, float] = Field(default_factory=dict)


class LearnerPortrait(BaseModel):
    student_key: str
    knowledge_state: dict[str, float] = Field(default_factory=dict)
    mastery_records: dict[str, MasteryRecord] = Field(default_factory=dict)
    review_states: dict[str, "ReviewState"] = Field(default_factory=dict)
    ability_ema: dict[str, float] = Field(default_factory=dict)
    weakness_log: list[WeaknessEntry] = Field(default_factory=list)
    weakness_events: list[WeaknessEvent] = Field(default_factory=list)
    dimensions: PortraitDimensions = Field(default_factory=PortraitDimensions)
    updated_at: datetime = Field(default_factory=utc_now)


class CurriculumCitation(BaseModel):
    citation_id: str
    title: str
    excerpt: str
    source_label: str
    source_id: str | None = None


class SessionState(BaseModel):
    """Persisted session artifact spanning the full MVP loop."""

    session_id: str
    profile: StudentProfile
    phase: SessionPhase = SessionPhase.ONBOARD
    curriculum_citations: list[CurriculumCitation] = Field(default_factory=list)
    paper: AssessmentPaper | None = None
    answers: list[StudentAnswer] = Field(default_factory=list)
    image_answers: list[ImageAnswer] = Field(default_factory=list)
    grades: list[GradeResult] = Field(default_factory=list)
    diagnosis: DiagnosisReport | None = None
    plan: LearningPlanReport | None = None
    plan_history: list[PlanVersion] = Field(default_factory=list)
    portrait: LearnerPortrait | None = None
    loop_count: int = 0
    evidence_log: list[KnowledgeEvidence] = Field(default_factory=list)


from ilearn.core.review import ReviewState  # noqa: E402

LearnerPortrait.model_rebuild()
