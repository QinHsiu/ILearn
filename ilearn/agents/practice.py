"""Practice agent — grades text and image answers."""

from __future__ import annotations

from ilearn.agents.protocol import AgentContext, AgentResult, SessionPhase
from ilearn.core.grader import ItemGrader
from ilearn.core.grading import VisionGrader
from ilearn.providers.llm import LLMClient


class PracticeAgent:
    name = "practice"

    def __init__(self, llm: LLMClient | None = None) -> None:
        self._text_grader = ItemGrader(llm)
        self._vision_grader = VisionGrader(llm)

    def run(self, ctx: AgentContext) -> AgentResult:
        if ctx.paper is None:
            raise ValueError("PracticeAgent requires paper in context")
        answer_map = {entry.item_id: entry.answer_text for entry in ctx.answers}
        item_by_id = {item.id: item for item in ctx.paper.items}
        grades_by_id = {
            item_id: self._text_grader.grade_item(item_by_id[item_id], text)
            for item_id, text in answer_map.items()
            if item_id in item_by_id
        }
        for image_answer in ctx.image_answers:
            item = item_by_id.get(image_answer.item_id)
            if item is None:
                continue
            grades_by_id[image_answer.item_id] = self._vision_grader.grade_image(
                item,
                image_answer.image_base64,
                image_answer.mime_type,
            )
        return AgentResult(
            phase=SessionPhase.DIAGNOSE,
            payload={"grades": list(grades_by_id.values())},
        )
