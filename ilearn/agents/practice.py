"""Practice agent — grades text and image answers."""

from __future__ import annotations

from ilearn.agents.protocol import AgentContext, AgentResult, SessionPhase
from ilearn.core.grader import ItemGrader
from ilearn.core.ocr import OcrExtractor
from ilearn.providers.llm import LLMClient


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
        return AgentResult(
            phase=SessionPhase.DIAGNOSE,
            payload={"grades": list(grades_by_id.values())},
        )
