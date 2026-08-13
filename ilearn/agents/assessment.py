"""Assessment paper agent backed by template-based paper assembly."""

from __future__ import annotations

import re
from random import Random
from typing import Any

from ilearn.agents.protocol import AgentContext, AgentResult, SessionPhase
from ilearn.core.assessment import (
    AssessmentBuilder,
    build_blueprint,
    fill_blueprint,
    validate_paper,
)
from ilearn.core.schemas import AssessmentItem, CurriculumCitation, ItemSourceRef
from ilearn.providers.curriculum import CurriculumProvider, load_example_bank

_TOKEN_PATTERN = re.compile(r"[\w\u4e00-\u9fff]+")


def _tokenize(text: str) -> set[str]:
    return {token.casefold() for token in _TOKEN_PATTERN.findall(text) if token.strip()}


def _bigrams(text: str) -> set[str]:
    normalized = text.casefold().strip()
    if len(normalized) < 2:
        return set()
    return {normalized[index : index + 2] for index in range(len(normalized) - 1)}


def _score_citation(item_text: str, citation: CurriculumCitation) -> float:
    item_tokens = _tokenize(item_text)
    doc_text = " ".join(
        [citation.title, citation.excerpt, citation.source_label or ""]
    )
    doc_tokens = _tokenize(doc_text)
    token_score = (
        len(item_tokens & doc_tokens) / len(item_tokens) if item_tokens else 0.0
    )
    item_bigrams = _bigrams(item_text)
    doc_bigrams = _bigrams(doc_text)
    bigram_score = (
        len(item_bigrams & doc_bigrams) / len(item_bigrams) if item_bigrams else 0.0
    )
    return max(token_score, bigram_score)


def bind_citations_to_item(
    item: AssessmentItem,
    citations: list[CurriculumCitation],
) -> list[str]:
    """Score citations against item knowledge ids and stem; return top 1-2 source ids."""
    query_text = " ".join(item.knowledge_ids) + " " + item.stem
    scored: list[tuple[float, str]] = []
    for citation in citations:
        source_id = citation.source_id or citation.citation_id
        if not source_id:
            continue
        score = _score_citation(query_text, citation)
        scored.append((score, source_id))
    scored.sort(key=lambda pair: (-pair[0], pair[1]))

    result: list[str] = []
    for score, source_id in scored:
        if score <= 0 and result:
            break
        if source_id not in result:
            result.append(source_id)
        if len(result) >= 2:
            break
    if not result and citations:
        fallback = citations[0].source_id or citations[0].citation_id
        if fallback:
            result = [fallback]
    return result


def _pick_example(
    knowledge_ids: list[str],
    example_bank: dict[str, list[dict[str, Any]]],
) -> dict[str, Any] | None:
    for knowledge_id in knowledge_ids:
        examples = example_bank.get(knowledge_id) or []
        if examples:
            return examples[0]
    return None


def bind_source_refs_to_item(
    item: AssessmentItem,
    citations: list[CurriculumCitation],
    example_bank: dict[str, list[dict[str, Any]]],
) -> list[ItemSourceRef]:
    """Attach example-bank and curriculum provenance for traceability."""
    objective_ids = (
        bind_citations_to_item(item, citations)
        if citations
        else list(item.curriculum_objective_ids)
    )
    example = _pick_example(item.knowledge_ids, example_bank)
    if not objective_ids and example is None:
        return []

    citation_labels = {
        c.source_id or c.citation_id: c.source_label for c in citations
    }
    source_label = example.get("label") if example else None
    if not source_label and objective_ids:
        source_label = citation_labels.get(objective_ids[0])

    return [
        ItemSourceRef(
            example_id=example.get("id") if example else None,
            curriculum_objective_ids=objective_ids,
            textbook_chapter=example.get("chapter") if example else None,
            source_label=source_label,
            example_stem=example.get("stem") if example else None,
            example_answer=example.get("answer") if example else None,
            example_difficulty=example.get("difficulty") if example else None,
        )
    ]


class AssessmentAgent:
    name = "assessment"

    def __init__(self, curriculum: CurriculumProvider) -> None:
        self._curriculum = curriculum
        self._builder = AssessmentBuilder(curriculum)

    def _example_bank(self) -> dict[str, list[dict[str, Any]]]:
        pilot_dir = getattr(self._curriculum, "_data_dir", None)
        if pilot_dir is None:
            return {}
        return load_example_bank(pilot_dir)

    def run(self, ctx: AgentContext) -> AgentResult:
        paper_type = ctx.metadata.get("paper_type", "diagnostic")
        if paper_type == "followup":
            weak_ids = ctx.metadata.get("weak_knowledge_ids", [])
            paper = self._builder.build_followup(
                ctx.profile, weak_ids, portrait=ctx.portrait
            )
        else:
            weak_ids = ctx.metadata.get("weak_knowledge_ids")
            weak_list = list(weak_ids) if weak_ids else None
            blueprint = build_blueprint(ctx.profile, weak_list)
            rng_seed = ctx.metadata.get("rng_seed")
            rng = Random(rng_seed) if rng_seed is not None else None
            paper = fill_blueprint(
                ctx.profile,
                blueprint,
                self._curriculum,
                rng=rng,
                portrait=ctx.portrait,
            )
            validate_paper(paper)

        raw_citations = list(ctx.metadata.get("citations") or [])
        citation_ids = [
            c.source_id if c.source_id else c.citation_id for c in raw_citations
        ]
        example_bank = self._example_bank()
        for item in paper.items:
            if not item.curriculum_objective_ids and raw_citations:
                item.curriculum_objective_ids = bind_citations_to_item(
                    item, raw_citations
                )
            elif not item.curriculum_objective_ids and citation_ids:
                item.curriculum_objective_ids = citation_ids[:1]
            item.source_refs = bind_source_refs_to_item(
                item, raw_citations, example_bank
            )

        return AgentResult(phase=SessionPhase.PRACTICE, payload={"paper": paper})
