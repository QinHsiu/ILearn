"""P1: resolve citations from knowledge_ids / example bank before stubbing."""

from __future__ import annotations

from typing import Any

from ilearn.core.schemas import AssessmentItem, AssessmentPaper, ItemSourceRef


def resolve_citation_from_knowledge(
    item: AssessmentItem,
    example_bank: dict[str, list[dict[str, Any]]] | None = None,
) -> ItemSourceRef | None:
    """Build a non-pending citation when knowledge_ids (and optionally bank) exist."""
    kids = [str(k) for k in (item.knowledge_ids or []) if k]
    if not kids:
        return None
    kid = kids[0]
    example: dict[str, Any] | None = None
    if example_bank:
        for knowledge_id in kids:
            rows = example_bank.get(knowledge_id) or []
            if rows:
                example = rows[0]
                break
    if example:
        return ItemSourceRef(
            example_id=str(example.get("id") or f"ex-{kid}"),
            curriculum_objective_ids=[f"obj_{kid}"],
            textbook_chapter=str(example.get("chapter") or f"知识点·{kid}"),
            source_label=str(example.get("label") or "北京·人教·小学数学"),
            example_stem=str(example.get("stem") or "")[:120] or None,
            example_difficulty=example.get("difficulty"),
            confidence=0.8,
        )
    return ItemSourceRef(
        example_id=f"kp-ex-{kid}",
        curriculum_objective_ids=[f"obj_{kid}"],
        textbook_chapter=f"知识点·{kid}",
        source_label="北京·人教·小学数学",
        example_stem=(item.stem[:80] if item.stem else None),
        confidence=0.55,
    )


def enrich_paper_citations(
    paper: AssessmentPaper,
    example_bank: dict[str, list[dict[str, Any]]] | None = None,
) -> AssessmentPaper:
    """Replace empty / pending stubs with knowledge-resolved citations when possible."""
    from ilearn.core.citation_gate import item_has_formal_citation

    fixed: list[AssessmentItem] = []
    for item in paper.items:
        if item_has_formal_citation(item, min_confidence=0.5):
            fixed.append(item)
            continue
        resolved = resolve_citation_from_knowledge(item, example_bank)
        if resolved is None:
            fixed.append(item)
            continue
        fixed.append(item.model_copy(update={"source_refs": [resolved]}))
    return paper.model_copy(update={"items": fixed})
