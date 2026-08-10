"""Assessment paper agent backed by template-based paper assembly."""

from __future__ import annotations

from ilearn.agents.protocol import AgentContext, AgentResult, SessionPhase
from ilearn.core.assessment import AssessmentBuilder
from ilearn.providers.curriculum import CurriculumProvider


class AssessmentAgent:
    name = "assessment"

    def __init__(self, curriculum: CurriculumProvider) -> None:
        self._builder = AssessmentBuilder(curriculum)

    def run(self, ctx: AgentContext) -> AgentResult:
        paper_type = ctx.metadata.get("paper_type", "diagnostic")
        if paper_type == "followup":
            weak_ids = ctx.metadata.get("weak_knowledge_ids", [])
            paper = self._builder.build_followup(ctx.profile, weak_ids)
        else:
            paper = self._builder.build(ctx.profile)
        return AgentResult(phase=SessionPhase.PRACTICE, payload={"paper": paper})
