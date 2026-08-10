"""Practice agent — grades text and image answers."""

from __future__ import annotations

from ilearn.agents.protocol import AgentContext, AgentResult, SessionPhase
from ilearn.core.grader import ItemGrader
from ilearn.core.ocr import OcrExtractor
from ilearn.core.schemas import GradeResult, KnowledgeEvidence
from ilearn.providers.llm import LLMClient


def evidence_from_grades(
    session_id: str, grades: list[GradeResult]
) -> list[KnowledgeEvidence]:
    """Build KnowledgeEvidence events from graded items."""
    events: list[KnowledgeEvidence] = []
    for grade in grades:
        for knowledge_id in grade.knowledge_ids:
            events.append(
                KnowledgeEvidence(
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
        answer_map = {entry.item_id: entry.answer_text for entry in ctx.answers}
        item_by_id = {item.id: item for item in ctx.paper.items}
        paper_created_at = ctx.paper.created_at
        grades_by_id = {
            item_id: self._text_grader.grade_item(
                item_by_id[item_id],
                text,
                paper_created_at=paper_created_at,
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
            )
            if ocr_result.degraded or ocr_result.confidence < 0.5:
                grade.grading_degraded = True
            elif not ocr_result.degraded:
                grade.grading_degraded = False
            grades_by_id[image_answer.item_id] = grade
        grades = list(grades_by_id.values())
        return AgentResult(
            phase=SessionPhase.DIAGNOSE,
            payload={
                "grades": grades,
                "evidence": evidence_from_grades(ctx.session_id, grades),
            },
        )
