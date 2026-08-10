"""Practice agent — grades text and image answers."""

from __future__ import annotations

from ilearn.agents.protocol import AgentContext, AgentResult, SessionPhase
from ilearn.core.evidence import make_evidence_id
from ilearn.core.grader import ItemGrader
from ilearn.core.ocr import OcrExtractor
from ilearn.core.schemas import (
    AssessmentItem,
    EvidenceLane,
    GradeResult,
    KnowledgeEvidence,
    StepAttempt,
)
from ilearn.providers.llm import LLMClient


def _attempts_for_grade(
    item: AssessmentItem, grade: GradeResult, lane: EvidenceLane
) -> list[StepAttempt]:
    attempts: list[StepAttempt] = []
    rubric = item.rubric_steps or []
    if grade.step_results:
        for sr in grade.step_results:
            attempts.append(
                StepAttempt(
                    item_id=item.id,
                    step_index=sr.step_index,
                    step_text=rubric[sr.step_index]
                    if sr.step_index < len(rubric)
                    else sr.step_text,
                    student_expression=sr.step_text,
                    lane=lane,
                    hint_level=grade.hint_level_suggestion,
                )
            )
    elif rubric:
        for idx, label in enumerate(rubric):
            attempts.append(
                StepAttempt(
                    item_id=item.id,
                    step_index=idx,
                    step_text=label,
                    student_expression=grade.steps[idx] if idx < len(grade.steps) else "",
                    lane=lane,
                    hint_level=grade.hint_level_suggestion,
                )
            )
    return attempts


def evidence_from_grades(
    session_id: str, grades: list[GradeResult]
) -> list[KnowledgeEvidence]:
    """Build KnowledgeEvidence events from graded items."""
    events: list[KnowledgeEvidence] = []
    for grade in grades:
        for knowledge_id in grade.knowledge_ids:
            events.append(
                KnowledgeEvidence(
                    evidence_id=make_evidence_id(),
                    session_id=session_id,
                    item_id=grade.item_id,
                    knowledge_id=knowledge_id,
                    lane=grade.lane,
                    correct=grade.final_correct,
                    error_tag=grade.error_tags[0] if grade.error_tags else None,
                    hint_level=grade.hint_level_suggestion,
                    confidence=0.5 if grade.grading_degraded else 1.0,
                )
            )
    return events


class PracticeAgent:
    name = "practice"

    def __init__(self, llm: LLMClient | None = None) -> None:
        self._text_grader = ItemGrader(llm)
        self._ocr = OcrExtractor(llm)

    def run(self, ctx: AgentContext) -> AgentResult:
        if ctx.paper is None:
            raise ValueError("PracticeAgent requires paper in context")
        # First-pass grading of the diagnostic paper (loop_count == 0) is unassisted
        # evidence ("probe"); grading of follow-up practice_loop papers is "practice".
        lane = "probe" if ctx.loop_count == 0 else "practice"
        answer_map = {entry.item_id: entry.answer_text for entry in ctx.answers}
        item_by_id = {item.id: item for item in ctx.paper.items}
        paper_created_at = ctx.paper.created_at
        grades_by_id = {
            item_id: self._text_grader.grade_item(
                item_by_id[item_id],
                text,
                paper_created_at=paper_created_at,
                lane=lane,
            )
            for item_id, text in answer_map.items()
            if item_id in item_by_id
        }
        for image_answer in ctx.image_answers:
            item = item_by_id.get(image_answer.item_id)
            if item is None:
                continue
            ocr_result = self._ocr.extract(
                item,
                image_answer.image_base64,
                image_answer.mime_type,
            )
            answer_text = "\n".join(ocr_result.steps) if ocr_result.steps else ""
            grade = self._text_grader.grade_item(
                item,
                answer_text,
                paper_created_at=paper_created_at,
                lane=lane,
            )
            if grade.receipt is not None:
                grade.receipt.ocr_confidence = ocr_result.confidence
                grade.receipt.ocr_degraded = ocr_result.degraded
            if ocr_result.degraded or ocr_result.confidence < 0.5:
                grade.grading_degraded = True
            # Do not clear grading_degraded based on OCR success alone: the text
            # grading step below may have degraded independently of OCR quality.
            grades_by_id[image_answer.item_id] = grade
        grades = list(grades_by_id.values())
        all_attempts: list[StepAttempt] = []
        for item_id, grade in grades_by_id.items():
            item = item_by_id.get(item_id)
            if item is None:
                continue
            all_attempts.extend(_attempts_for_grade(item, grade, lane))
        return AgentResult(
            phase=SessionPhase.DIAGNOSE,
            payload={
                "grades": grades,
                "step_attempts": all_attempts,
                "evidence": evidence_from_grades(ctx.session_id, grades),
            },
        )
