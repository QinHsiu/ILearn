"""P1 win-bar: citation fail-closed + confidence for formal papers."""

from __future__ import annotations

from ilearn.core.schemas import AssessmentItem, AssessmentPaper, ItemSourceRef

_PENDING = {"pending_curriculum", "待绑定", "待绑定章节"}


class CitationGateError(ValueError):
    """Raised when a formal paper still lacks citations after repair."""


def _ref_confidence(ref: ItemSourceRef | dict) -> float:
    if isinstance(ref, ItemSourceRef):
        if ref.confidence is not None:
            return float(ref.confidence)
        if ref.example_id and ref.curriculum_objective_ids:
            objs = [str(x) for x in ref.curriculum_objective_ids]
            if objs and not any(o in _PENDING or o.startswith("pending") for o in objs):
                return 0.85
        if ref.example_id or (
            ref.curriculum_objective_ids
            and not any(
                str(o) in _PENDING or str(o).startswith("pending")
                for o in ref.curriculum_objective_ids
            )
        ):
            return 0.7
        if ref.source_label == "pilot-stub":
            return 0.2
        return 0.4
    conf = ref.get("confidence")
    if conf is not None:
        return float(conf)
    return 0.4


def item_has_citation(item: AssessmentItem) -> bool:
    refs = item.source_refs or []
    if not refs:
        return False
    for ref in refs:
        if isinstance(ref, ItemSourceRef):
            if ref.example_id or ref.curriculum_objective_ids or ref.textbook_chapter:
                return True
            if ref.example_stem or ref.source_label:
                return True
        elif isinstance(ref, dict):
            if any(
                ref.get(k)
                for k in (
                    "example_id",
                    "curriculum_objective_ids",
                    "textbook_chapter",
                    "example_stem",
                    "source_label",
                )
            ):
                return True
    return False


def item_has_formal_citation(item: AssessmentItem, *, min_confidence: float = 0.5) -> bool:
    """Formal = non-stub provenance with confidence above threshold."""
    for ref in item.source_refs or []:
        if not isinstance(ref, ItemSourceRef):
            continue
        objs = [str(x) for x in (ref.curriculum_objective_ids or [])]
        if any(o in _PENDING or o.startswith("pending") for o in objs):
            continue
        if ref.source_label == "pilot-stub":
            continue
        if _ref_confidence(ref) < min_confidence:
            continue
        if ref.example_id or objs or ref.textbook_chapter:
            return True
    return False


def ensure_citations_or_stub(
    paper: AssessmentPaper,
    *,
    fail_closed: bool = True,
    formal_strict: bool = False,
    min_confidence: float = 0.5,
    example_bank: dict | None = None,
) -> AssessmentPaper:
    """Attach citations; prefer knowledge-resolved refs over pending stubs."""
    from ilearn.core.curriculum_bind import enrich_paper_citations, resolve_citation_from_knowledge

    paper = enrich_paper_citations(paper, example_bank)

    fixed_items: list[AssessmentItem] = []
    for item in paper.items:
        if item_has_citation(item):
            # Fill missing confidence on existing refs
            new_refs: list[ItemSourceRef] = []
            for ref in item.source_refs or []:
                if isinstance(ref, ItemSourceRef) and ref.confidence is None:
                    new_refs.append(
                        ref.model_copy(update={"confidence": _ref_confidence(ref)})
                    )
                elif isinstance(ref, ItemSourceRef):
                    new_refs.append(ref)
                else:
                    new_refs.append(ItemSourceRef.model_validate(ref))
            # Upgrade pending stubs if knowledge_ids allow
            if not item_has_formal_citation(
                item.model_copy(update={"source_refs": new_refs}),
                min_confidence=min_confidence,
            ):
                resolved = resolve_citation_from_knowledge(item, example_bank)
                if resolved is not None:
                    new_refs = [resolved]
            fixed_items.append(item.model_copy(update={"source_refs": new_refs}))
            continue
        resolved = resolve_citation_from_knowledge(item, example_bank)
        if resolved is not None:
            fixed_items.append(item.model_copy(update={"source_refs": [resolved]}))
            continue
        stub = ItemSourceRef(
            source_label="pilot-stub",
            textbook_chapter="待绑定章节",
            curriculum_objective_ids=["pending_curriculum"],
            example_stem=(item.stem[:80] if item.stem else None),
            confidence=0.2,
        )
        fixed = item.model_copy(update={"source_refs": [stub]})
        fixed_items.append(fixed)

    out = paper.model_copy(update={"items": fixed_items})
    if fail_closed:
        bare = [it.id for it in out.items if not item_has_citation(it)]
        if bare:
            raise CitationGateError(f"items missing citation after stub: {bare}")
    if formal_strict:
        weak = [
            it.id
            for it in out.items
            if not item_has_formal_citation(it, min_confidence=min_confidence)
        ]
        if weak:
            raise CitationGateError(
                f"formal paper requires non-stub citations (confidence>={min_confidence}): {weak}"
            )
    return out
