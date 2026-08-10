"""Curriculum citation agent backed by the local pilot syllabus pack."""

from __future__ import annotations

from pathlib import Path

from ilearn.agents.protocol import AgentContext, AgentResult
from ilearn.core.schemas import CurriculumCitation
from ilearn.providers.curriculum import load_syllabus


def _is_beijing(region: str) -> bool:
    normalized = region.strip().casefold()
    return normalized in ("北京", "beijing")


def _to_citation(entry: dict) -> CurriculumCitation:
    return CurriculumCitation(
        citation_id=entry["citation_id"],
        title=entry["title"],
        excerpt=entry["excerpt"],
        source_label=entry["source_label"],
    )


class CurriculumAgent:
    name = "curriculum"

    def __init__(self, pilot_dir: Path) -> None:
        self._syllabus = load_syllabus(pilot_dir)

    def run(self, ctx: AgentContext) -> AgentResult:
        grade = ctx.profile.grade
        entries = [e for e in self._syllabus if e["grade"] == grade]
        if not _is_beijing(ctx.profile.region):
            entries = entries[:2]
        citations = [_to_citation(e) for e in entries]
        return AgentResult(phase=ctx.phase, payload={"citations": citations})
