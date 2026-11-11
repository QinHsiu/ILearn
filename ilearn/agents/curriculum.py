"""Curriculum citation agent backed by keyword RAG over curriculum sources."""

from __future__ import annotations

import os
from pathlib import Path

from ilearn.agents.protocol import AgentContext, AgentResult
from ilearn.core.schemas import CurriculumCitation
from ilearn.providers.curriculum import load_syllabus
from ilearn.providers.curriculum_rag import CurriculumRagRetriever

_GRADE_DEFAULT_QUERY = {
    4: "四年级数学 加减法 乘法",
    5: "五年级数学 分数 小数",
    6: "六年级数学 比 比例 百分数",
}


def _syllabus_to_citation(entry: dict) -> CurriculumCitation:
    citation_id = entry["citation_id"]
    source_label = entry["source_label"]
    region = entry.get("region")
    edition = entry.get("edition")
    if region is None or edition is None:
        # Labels look like "北京·人教·小学数学"
        parts = [p for p in str(source_label).split("·") if p]
        if region is None and parts:
            region = parts[0]
        if edition is None and len(parts) > 1:
            edition = parts[1]
    return CurriculumCitation(
        citation_id=citation_id,
        source_id=citation_id,
        title=entry["title"],
        excerpt=entry["excerpt"],
        source_label=source_label,
        region=region,
        edition=edition,
    )


class CurriculumAgent:
    name = "curriculum"

    def __init__(self, pilot_dir: Path, *, backend: str | None = None) -> None:
        self._pilot_dir = pilot_dir
        self._syllabus = load_syllabus(pilot_dir)
        resolved_backend = backend or os.environ.get(
            "ILEARN_RETRIEVER_BACKEND", "keyword"
        )
        self._backend = resolved_backend
        self._retriever = CurriculumRagRetriever(pilot_dir, backend=resolved_backend)

    def run(self, ctx: AgentContext) -> AgentResult:
        from ilearn.core.scopes import assert_agent_scope

        assert_agent_scope(
            self.name,
            "curriculum:retrieve",
            api_key=ctx.metadata.get("scope_api_key"),
        )
        query = ctx.metadata.get("curriculum_query") or _GRADE_DEFAULT_QUERY.get(
            ctx.profile.grade, "小学数学"
        )
        citations = self._retriever.retrieve(ctx.profile, query, top_k=5)
        if len(citations) < 3:
            seen = {c.citation_id for c in citations}
            for entry in self._syllabus:
                if entry["grade"] != ctx.profile.grade:
                    continue
                cid = entry["citation_id"]
                if cid in seen:
                    continue
                citations.append(_syllabus_to_citation(entry))
                seen.add(cid)
                if len(citations) >= 3:
                    break
        return AgentResult(phase=ctx.phase, payload={"citations": citations})
