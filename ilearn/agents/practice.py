"""Practice agent — grades student text answers via StepGrader."""

from __future__ import annotations

from ilearn.agents.protocol import AgentContext, AgentResult, SessionPhase
from ilearn.core.grading import StepGrader
from ilearn.providers.llm import LLMClient


class PracticeAgent:
    name = "practice"

    def __init__(self, llm: LLMClient | None = None) -> None:
        self._grader = StepGrader(llm)

    def run(self, ctx: AgentContext) -> AgentResult:
        if ctx.paper is None:
            raise ValueError("PracticeAgent requires paper in context")
        answer_map = {entry.item_id: entry.answer_text for entry in ctx.answers}
        item_by_id = {item.id: item for item in ctx.paper.items}
        grades = [
            self._grader.grade_item(item_by_id[item_id], text)
            for item_id, text in answer_map.items()
            if item_id in item_by_id
        ]
        return AgentResult(phase=SessionPhase.DIAGNOSE, payload={"grades": grades})
