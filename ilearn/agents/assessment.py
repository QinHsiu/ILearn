"""Assessment paper agent backed by template-based paper assembly."""

from __future__ import annotations

from ilearn.agents.protocol import AgentContext, AgentResult, SessionPhase
from ilearn.core.assessment import (
    AssessmentBuilder,
    build_blueprint,
    fill_blueprint,
    validate_paper,
)
from ilearn.providers.curriculum import CurriculumProvider


class AssessmentAgent:
    name = "assessment"

    def __init__(self, curriculum: CurriculumProvider) -> None:
        self._curriculum = curriculum
        self._builder = AssessmentBuilder(curriculum)

    def run(self, ctx: AgentContext) -> AgentResult:
        paper_type = ctx.metadata.get("paper_type", "diagnostic")
        if paper_type == "followup":
            weak_ids = ctx.metadata.get("weak_knowledge_ids", [])
            paper = self._builder.build_followup(ctx.profile, weak_ids)
        else:
            weak_ids = ctx.metadata.get("weak_knowledge_ids")
            weak_list = list(weak_ids) if weak_ids else None
            blueprint = build_blueprint(ctx.profile, weak_list)
            paper = fill_blueprint(ctx.profile, blueprint, self._curriculum)
            validate_paper(paper)
        return AgentResult(phase=SessionPhase.PRACTICE, payload={"paper": paper})
