"""Host-owned item grading facade (OPT-012)."""

from __future__ import annotations

from datetime import datetime

from ilearn.core.datetime_utils import utc_now
from ilearn.core.grading import StepGrader
from ilearn.core.schemas import AssessmentItem, EvidenceLane, GradeResult, GradingReceipt
from ilearn.providers.llm import LLMClient

GRADER_VERSION = "1.0.0"


class ItemGrader:
    """Host-owned deterministic + LLM grader. AssessmentAgent must not embed grading."""

    def __init__(self, llm: LLMClient | None = None) -> None:
        self._step_grader = StepGrader(llm)

    def grade_item(
        self,
        item: AssessmentItem,
        answer_text: str,
        *,
        paper_created_at: datetime | None = None,
        lane: EvidenceLane = "practice",
    ) -> GradeResult:
        result = self._step_grader.grade_item(item, answer_text)
        result.lane = lane
        receipt = GradingReceipt(
            paper_created_at=paper_created_at or utc_now(),
            grader_version=GRADER_VERSION,
            model_id=getattr(self._step_grader._llm, "model", None),
        )
        result.receipt = receipt
        return result
