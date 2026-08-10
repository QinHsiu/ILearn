"""Host-owned item grading facade (OPT-012)."""

from __future__ import annotations

from ilearn.core.grading import StepGrader
from ilearn.core.schemas import AssessmentItem, GradeResult
from ilearn.providers.llm import LLMClient

GRADER_VERSION = "1.0.0"


class ItemGrader:
    """Host-owned deterministic + LLM grader. AssessmentAgent must not embed grading."""

    def __init__(self, llm: LLMClient | None = None) -> None:
        self._step_grader = StepGrader(llm)

    def grade_item(self, item: AssessmentItem, answer_text: str) -> GradeResult:
        return self._step_grader.grade_item(item, answer_text)
