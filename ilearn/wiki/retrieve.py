"""Hybrid wiki retrieve: BM25 + L1 skill_id boost + 1-hop graph expand."""

from __future__ import annotations

from ilearn.core.learner_state import LearnerState
from ilearn.core.schemas import CurriculumCitation
from ilearn.wiki.models import WikiHit, WikiPage
from ilearn.wiki.store import WikiStore


def _weak_skills(state: LearnerState | None, *, threshold: float = 0.6) -> set[str]:
    if state is None:
        return set()
    weak: set[str] = set()
    for skill_id, est in state.mastery.items():
        if est.mastery < threshold:
            weak.add(skill_id)
            # Also allow bare id without prefixes for overlap
            if ":" in skill_id:
                weak.add(skill_id.split(":", 1)[-1])
    return weak


def _skill_overlap(page: WikiPage, skills: set[str]) -> list[str]:
    matched: list[str] = []
    page_skills = set(page.skill_ids)
    page_bare = {s.split(":", 1)[-1] for s in page.skill_ids}
    for s in skills:
        if s in page_skills or s in page_bare or s.split(":", 1)[-1] in page_bare:
            matched.append(s)
    return matched


def retrieve_wiki(
    store: WikiStore,
    query: str,
    *,
    learner_state: LearnerState | None = None,
    top_k: int = 5,
    graph_expand: bool = True,
) -> list[WikiHit]:
    weak = _weak_skills(learner_state)
    ranked = store.search_bm25(query, top_k=max(top_k * 2, 8))
    hits: list[WikiHit] = []
    seen: set[str] = set()
    for page, score in ranked:
        matched = _skill_overlap(page, weak)
        boost = 0.35 * len(matched)
        hits.append(
            WikiHit(
                page=page,
                score=score + boost,
                matched_skills=matched,
                via_graph=False,
            )
        )
        seen.add(page.page_id)

    # L1 skill prior: surface weak-skill pages even when BM25 miss.
    if weak:
        for page in store.list_pages():
            if page.page_id in seen:
                continue
            matched = _skill_overlap(page, weak)
            if not matched:
                continue
            hits.append(
                WikiHit(
                    page=page,
                    score=0.5 + 0.35 * len(matched),
                    matched_skills=matched,
                    via_graph=False,
                )
            )
            seen.add(page.page_id)

    if graph_expand:
        seed_ids = [h.page.page_id for h in hits[:3]]
        for pid in seed_ids:
            for nb in store.neighbors(pid):
                if nb in seen:
                    continue
                page = store.get(nb)
                if page is None:
                    continue
                matched = _skill_overlap(page, weak)
                hits.append(
                    WikiHit(
                        page=page,
                        score=0.15 + 0.25 * len(matched),
                        matched_skills=matched,
                        via_graph=True,
                    )
                )
                seen.add(nb)

    hits.sort(key=lambda h: (-h.score, h.page.page_id))
    return hits[:top_k]


def hits_to_citations(hits: list[WikiHit]) -> list[CurriculumCitation]:
    citations: list[CurriculumCitation] = []
    for hit in hits:
        page = hit.page
        excerpt = page.body.strip().replace("\n", " ")
        if len(excerpt) > 160:
            excerpt = excerpt[:160] + "…"
        label = "ILearn·wiki"
        if hit.matched_skills:
            label = f"ILearn·wiki·skill:{hit.matched_skills[0]}"
        elif hit.via_graph:
            label = "ILearn·wiki·graph"
        citations.append(
            CurriculumCitation(
                citation_id=page.page_id,
                source_id=page.page_id,
                title=page.title,
                excerpt=excerpt,
                source_label=label,
                region=(page.metadata or {}).get("region"),
            )
        )
    return citations
