"""Assessment paper agent backed by template-based paper assembly."""

from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path
from random import Random
from typing import Any

from ilearn.agents.protocol import AgentContext, AgentResult, SessionPhase
from ilearn.core.assessment import (
    AssessmentBuilder,
    build_blueprint,
    fill_blueprint,
    validate_paper,
)
from ilearn.core.curriculum_gate import CurriculumGate
from ilearn.core.knowledge_graph import KnowledgeGraph
from ilearn.core.progress_mapper import ProgressMapper, infer_semester
from ilearn.core.schemas import (
    AssessmentItem,
    AssessmentPaper,
    BlueprintSlot,
    CurriculumCitation,
    ItemSourceRef,
    PaperBlueprint,
    StudentProfile,
)
from ilearn.providers.curriculum import (
    CurriculumProvider,
    load_example_bank,
    load_multimodal_bank,
)
from ilearn.providers.llm import LLMClient, LLMError

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


def _bind_multimodal_source_refs(
    item: AssessmentItem,
    raw: dict[str, Any],
) -> list[ItemSourceRef]:
    """Attach provenance from a multimodal bank record's curriculum_ref."""
    curriculum_ref = raw.get("curriculum_ref") or {}
    objective_ids = list(curriculum_ref.get("objective_ids") or item.curriculum_objective_ids)
    if not objective_ids and not curriculum_ref:
        return []
    return [
        ItemSourceRef(
            example_id=raw.get("id"),
            curriculum_objective_ids=objective_ids,
            textbook_chapter=curriculum_ref.get("chapter"),
            source_label=curriculum_ref.get("source_label"),
            example_stem=raw.get("stem"),
            example_answer=raw.get("answer"),
            example_difficulty=raw.get("difficulty"),
        )
    ]


def bind_source_refs_to_item(
    item: AssessmentItem,
    citations: list[CurriculumCitation],
    example_bank: dict[str, list[dict[str, Any]]],
    *,
    multimodal_raw: dict[str, Any] | None = None,
) -> list[ItemSourceRef]:
    """Attach example-bank and curriculum provenance for traceability."""
    if multimodal_raw is not None:
        return _bind_multimodal_source_refs(item, multimodal_raw)

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


def _pilot_asset_url(rel_path: str) -> str:
    """Map pilot-relative asset path to /pilot-assets URL."""
    normalized = rel_path.replace("\\", "/")
    if normalized.startswith("assets/"):
        return f"/pilot-assets/{normalized[7:]}"
    return f"/pilot-assets/{normalized}"


def _multimodal_to_assessment_item(raw: dict[str, Any], index: int) -> AssessmentItem:
    """Map a multimodal bank record to an AssessmentItem with pilot-assets URLs."""
    curriculum_ref = raw.get("curriculum_ref") or {}
    answer_type = str(raw.get("answer_type") or "free-form")
    if answer_type == "choice":
        item_type = "choice"
    else:
        item_type = "fill"
    difficulty = raw.get("difficulty") or "medium"
    if difficulty not in ("easy", "medium", "hard"):
        difficulty = "medium"
    image_paths = [
        _pilot_asset_url(path) for path in (raw.get("image_paths") or [])
    ]
    return AssessmentItem(
        id=f"mm-{raw['id']}__{index:02d}",
        stem=str(raw.get("stem") or ""),
        type=item_type,  # type: ignore[arg-type]
        difficulty=difficulty,  # type: ignore[arg-type]
        knowledge_ids=list(raw.get("knowledge_ids") or []),
        answer_key=str(raw.get("answer") or ""),
        curriculum_objective_ids=list(curriculum_ref.get("objective_ids") or []),
        image_paths=image_paths,
        is_multimodal=bool(image_paths),
    )


def _pick_multimodal_items(
    eligible: list[dict[str, Any]],
    count_min: int,
    count_max: int,
    rng: Random,
) -> list[dict[str, Any]]:
    """Pick distinct-kp multimodal items with an easy/medium/hard mix."""
    if not eligible or count_max <= 0:
        return []

    pool = list(eligible)
    rng.shuffle(pool)
    by_diff: dict[str, list[dict[str, Any]]] = {
        "easy": [],
        "medium": [],
        "hard": [],
    }
    for row in pool:
        diff = row.get("difficulty") or "medium"
        if diff not in by_diff:
            diff = "medium"
        by_diff[diff].append(row)

    picked: list[dict[str, Any]] = []
    used_ids: set[str] = set()
    used_kps: set[str] = set()

    for diff in ("easy", "medium", "hard"):
        for row in by_diff.get(diff, []):
            row_id = str(row.get("id") or "")
            if not row_id or row_id in used_ids:
                continue
            kp = str((row.get("knowledge_ids") or [""])[0])
            if kp in used_kps:
                continue
            picked.append(row)
            used_ids.add(row_id)
            used_kps.add(kp)
            break
        if len(picked) >= count_max:
            break

    for row in pool:
        if len(picked) >= count_max:
            break
        row_id = str(row.get("id") or "")
        if not row_id or row_id in used_ids:
            continue
        kp = str((row.get("knowledge_ids") or [""])[0])
        if kp in used_kps:
            continue
        picked.append(row)
        used_ids.add(row_id)
        used_kps.add(kp)

    if len(picked) < count_min:
        for row in pool:
            if len(picked) >= count_min:
                break
            row_id = str(row.get("id") or "")
            if row_id and row_id not in used_ids:
                picked.append(row)
                used_ids.add(row_id)

    return picked[:count_max]


def _parse_multimodal_bank_id(item_id: str) -> str | None:
    if not item_id.startswith("mm-"):
        return None
    rest = item_id[3:]
    if "__" in rest:
        return rest.split("__", 1)[0]
    return rest


def _curriculum_ref_summary(profile: StudentProfile) -> dict[str, Any]:
    return {
        "region": profile.region,
        "edition": "人教版",
        "grade": profile.grade,
    }


def _multimodal_count(paper: AssessmentPaper) -> int:
    return sum(1 for item in paper.items if item.is_multimodal)


class AssessmentAgent:
    name = "assessment"

    def __init__(
        self,
        curriculum: CurriculumProvider,
        *,
        progress_mapper: ProgressMapper | None = None,
        knowledge_graph: KnowledgeGraph | None = None,
        llm: LLMClient | None = None,
        curriculum_gate: CurriculumGate | None = None,
    ) -> None:
        self._curriculum = curriculum
        self._builder = AssessmentBuilder(curriculum)
        self._progress_mapper = progress_mapper or ProgressMapper()
        self._knowledge_graph = knowledge_graph or KnowledgeGraph()
        self._llm = llm
        self._curriculum_gate = curriculum_gate or CurriculumGate(
            graph=self._knowledge_graph,
            progress_mapper=self._progress_mapper,
        )
        self._multimodal_raw_by_id: dict[str, dict[str, Any]] = {}

    def _pilot_dir(self) -> Path | None:
        data_dir = getattr(self._curriculum, "_data_dir", None)
        return Path(data_dir) if data_dir is not None else None

    def _example_bank(self) -> dict[str, list[dict[str, Any]]]:
        pilot_dir = self._pilot_dir()
        if pilot_dir is None:
            return {}
        return load_example_bank(pilot_dir)

    def _multimodal_bank(self) -> list[dict[str, Any]]:
        pilot_dir = self._pilot_dir()
        if pilot_dir is None:
            return []
        return load_multimodal_bank(pilot_dir)

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

    def generate_adaptive_assessment(
        self,
        profile: StudentProfile,
        *,
        is_first_time: bool = True,
        anchor_results: list[dict[str, Any]] | None = None,
        semester: str | None = None,
        now: datetime | None = None,
        portrait=None,
    ) -> dict[str, Any]:
        """Cold-start adaptive paper: anchor (variable) then full diagnostic (20)."""
        current = now or datetime.now()
        semester_label = semester or infer_semester(current)
        current_chapter, current_kps = self._progress_mapper.infer_current_progress(
            profile.region,
            int(profile.grade),
            semester_label,
            current,
        )

        if is_first_time or not anchor_results:
            return self._build_anchor_payload(
                profile,
                current_chapter=current_chapter,
                current_kps=current_kps,
                semester=semester_label,
                portrait=portrait,
                now=current,
            )

        diagnosis = self._diagnose_from_anchor(anchor_results)
        weak_kps = list(diagnosis.get("weak_knowledge_points", []))
        target_kps = list(dict.fromkeys(weak_kps + list(current_kps)))
        blueprint = build_blueprint(profile, target_kps or None)
        rng = Random()
        paper = fill_blueprint(
            profile,
            blueprint,
            self._curriculum,
            rng=rng,
            portrait=portrait,
        )
        eligible = self._curriculum_gate.filter_bank(
            self._multimodal_bank(),
            profile,
            semester=semester_label,
            now=current,
            knowledge_ids=target_kps or None,
        )
        paper = self._inject_multimodal_into_paper(
            paper,
            blueprint,
            eligible,
            rng,
            max_count=4,
        )
        validate_paper(paper)
        self._attach_source_refs(paper, citations=[])
        return {
            "is_anchor": False,
            "paper": paper,
            "diagnosis": diagnosis,
            "inferred_chapter": current_chapter,
            "inferred_kps": current_kps,
            "target_kps": target_kps,
            "semester": semester_label,
            "requested": 20,
            "delivered": len(paper.items),
            "shortfall": 0,
            "multimodal_count": _multimodal_count(paper),
            "curriculum_ref_summary": _curriculum_ref_summary(profile),
        }

    def _build_anchor_payload(
        self,
        profile: StudentProfile,
        *,
        current_chapter: str,
        current_kps: list[str],
        semester: str,
        portrait=None,
        now: datetime | None = None,
    ) -> dict[str, Any]:
        current = now or datetime.now()
        prerequisite_kps: list[str] = []
        for kp in current_kps:
            prerequisite_kps.extend(self._knowledge_graph.get_prerequisites(kp))
        anchor_kps = list(dict.fromkeys(list(current_kps) + prerequisite_kps))[:6]
        requested = min(max(len(anchor_kps) * 2, 1), 8)
        if anchor_kps:
            requested = max(requested, min(5, requested))

        rng = Random()
        eligible = self._curriculum_gate.filter_bank(
            self._multimodal_bank(),
            profile,
            semester=semester,
            now=current,
            knowledge_ids=anchor_kps,
        )
        multimodal_raws = _pick_multimodal_items(eligible, 2, 4, rng)
        multimodal_count = len(multimodal_raws)
        text_size = max(0, requested - multimodal_count)

        paper = self._builder.build_by_knowledge_ids(
            profile,
            anchor_kps,
            size=text_size,
            portrait=portrait,
            require_nonempty=False,
            difficulty_targets={"easy": 0.5, "medium": 0.3, "hard": 0.2},
        )
        layer2_used = False
        layer2_source = "none"
        shortfall = max(0, requested - len(paper.items) - multimodal_count)
        if shortfall > 0 and anchor_kps:
            extra, layer2_source = self._layer2_fill(
                profile,
                knowledge_points=anchor_kps,
                need=shortfall,
                start_index=len(paper.items) + multimodal_count,
            )
            if extra:
                layer2_used = True
                paper = AssessmentPaper(
                    items=list(paper.items) + extra,
                    grade=paper.grade,
                    curriculum_label=paper.curriculum_label,
                    blueprint=paper.blueprint,
                    paper_version=paper.paper_version,
                )

        multimodal_items: list[AssessmentItem] = []
        for index, raw in enumerate(multimodal_raws):
            bank_id = str(raw.get("id") or "")
            if bank_id:
                self._multimodal_raw_by_id[bank_id] = raw
            multimodal_items.append(
                _multimodal_to_assessment_item(raw, len(paper.items) + index)
            )

        if multimodal_items:
            paper = AssessmentPaper(
                items=multimodal_items + list(paper.items),
                grade=paper.grade,
                curriculum_label=paper.curriculum_label,
                blueprint=paper.blueprint,
                paper_version=paper.paper_version,
            )

        self._attach_source_refs(paper, citations=[])
        delivered = len(paper.items)
        return {
            "is_anchor": True,
            "paper": paper,
            "inferred_chapter": current_chapter,
            "inferred_kps": current_kps,
            "anchor_kps": anchor_kps,
            "semester": semester,
            "requested": requested,
            "delivered": delivered,
            "shortfall": max(0, requested - delivered),
            "layer2_used": layer2_used,
            "layer2_source": layer2_source,
            "multimodal_count": _multimodal_count(paper),
            "curriculum_ref_summary": _curriculum_ref_summary(profile),
        }

    def _inject_multimodal_into_paper(
        self,
        paper: AssessmentPaper,
        blueprint: PaperBlueprint,
        eligible: list[dict[str, Any]],
        rng: Random,
        *,
        max_count: int,
    ) -> AssessmentPaper:
        """Replace up to max_count blueprint slots with gated multimodal items."""
        if not eligible or max_count <= 0 or not paper.blueprint:
            return paper

        picks = _pick_multimodal_items(eligible, 1, max_count, rng)
        if not picks:
            return paper

        items = list(paper.items)
        replaced: set[int] = set()

        for raw in picks:
            bank_id = str(raw.get("id") or "")
            if bank_id:
                self._multimodal_raw_by_id[bank_id] = raw
            mm_kps = set(raw.get("knowledge_ids") or [])
            mm_diff = raw.get("difficulty")

            match_index: int | None = None
            for idx, slot in enumerate(blueprint.slots):
                if idx in replaced:
                    continue
                if slot.item_type != "fill":
                    continue
                if slot.knowledge_id and slot.knowledge_id not in mm_kps:
                    continue
                if slot.difficulty != mm_diff:
                    continue
                match_index = idx
                break

            if match_index is None:
                for idx, slot in enumerate(blueprint.slots):
                    if idx in replaced:
                        continue
                    if slot.item_type != "fill":
                        continue
                    if slot.knowledge_id and slot.knowledge_id not in mm_kps:
                        continue
                    match_index = idx
                    break

            if match_index is None:
                continue

            items[match_index] = _multimodal_to_assessment_item(raw, match_index)
            replaced.add(match_index)

        return AssessmentPaper(
            items=items,
            grade=paper.grade,
            curriculum_label=paper.curriculum_label,
            blueprint=paper.blueprint,
            paper_version=paper.paper_version,
        )

    def _layer2_fill(
        self,
        profile: StudentProfile,
        *,
        knowledge_points: list[str],
        need: int,
        start_index: int,
    ) -> tuple[list[AssessmentItem], str]:
        """Second-layer fill: LLM when available, else deterministic stubs."""
        if need <= 0 or not knowledge_points:
            return [], "none"
        if self._llm is not None and self._llm.available():
            try:
                items = self._generate_llm_items(
                    profile,
                    knowledge_points=knowledge_points,
                    need=need,
                    start_index=start_index,
                )
                if items:
                    return items, "llm"
            except (LLMError, ValueError, TypeError, KeyError):
                pass
        stubs = self._generate_stub_items(
            profile,
            knowledge_points=knowledge_points,
            need=need,
            start_index=start_index,
        )
        return stubs, "stub" if stubs else "none"

    def _generate_stub_items(
        self,
        profile: StudentProfile,
        *,
        knowledge_points: list[str],
        need: int,
        start_index: int,
    ) -> list[AssessmentItem]:
        items: list[AssessmentItem] = []
        for offset in range(need):
            kp = knowledge_points[offset % len(knowledge_points)]
            index = start_index + offset
            items.append(
                AssessmentItem(
                    id=f"stub-{kp}__{index:02d}",
                    stem=f"[stub] Review {kp}: what is 1+{offset}? Write the sum.",
                    type="fill",
                    difficulty="easy",
                    knowledge_ids=[kp],
                    answer_key=str(1 + offset),
                    rubric_steps=["Compute the sum carefully."],
                )
            )
        del profile
        return items

    def _generate_llm_items(
        self,
        profile: StudentProfile,
        *,
        knowledge_points: list[str],
        need: int,
        start_index: int,
    ) -> list[AssessmentItem]:
        assert self._llm is not None
        allowed = set(knowledge_points)
        system = (
            "You generate primary-school math assessment items as JSON. "
            'Return {"items":[{"stem":str,"type":"fill|choice|constructed",'
            '"difficulty":"easy|medium|hard","knowledge_ids":[str],'
            '"answer_key":str,"choices":[str]|null}]} . '
            "knowledge_ids must be chosen only from the provided allow-list."
        )
        user = (
            f"grade={profile.grade}; need={need}; "
            f"allow_knowledge_ids={list(knowledge_points)}"
        )
        payload = self._llm.chat_json(system, user, fallback=True)
        raw_items = payload.get("items") or []
        if not isinstance(raw_items, list):
            raise ValueError("items must be a list")
        validated: list[AssessmentItem] = []
        for offset, raw in enumerate(raw_items[:need]):
            if not isinstance(raw, dict):
                continue
            kids = [str(k) for k in (raw.get("knowledge_ids") or []) if str(k) in allowed]
            if not kids:
                continue
            item_type = raw.get("type") or "fill"
            if item_type not in ("fill", "choice", "constructed"):
                item_type = "fill"
            difficulty = raw.get("difficulty") or "easy"
            if difficulty not in ("easy", "medium", "hard"):
                difficulty = "easy"
            stem = str(raw.get("stem") or "").strip()
            answer = str(raw.get("answer_key") or "").strip()
            if not stem or not answer:
                continue
            choices = raw.get("choices")
            if choices is not None and not isinstance(choices, list):
                choices = None
            validated.append(
                AssessmentItem(
                    id=f"llm-{kids[0]}__{start_index + offset:02d}",
                    stem=stem,
                    type=item_type,  # type: ignore[arg-type]
                    difficulty=difficulty,  # type: ignore[arg-type]
                    knowledge_ids=kids,
                    answer_key=answer,
                    choices=[str(c) for c in choices] if choices else None,
                )
            )
        return validated

    def _attach_source_refs(
        self,
        paper: AssessmentPaper,
        *,
        citations: list[CurriculumCitation],
    ) -> None:
        example_bank = self._example_bank()
        bank_by_id = {str(row.get("id") or ""): row for row in self._multimodal_bank()}
        for item in paper.items:
            bank_id = _parse_multimodal_bank_id(item.id)
            multimodal_raw = None
            if bank_id:
                multimodal_raw = self._multimodal_raw_by_id.get(bank_id) or bank_by_id.get(
                    bank_id
                )
            item.source_refs = bind_source_refs_to_item(
                item,
                citations,
                example_bank,
                multimodal_raw=multimodal_raw if item.is_multimodal else None,
            )

    @staticmethod
    def _diagnose_from_anchor(anchor_results: list[dict[str, Any]]) -> dict[str, Any]:
        """Aggregate anchor answers into weak knowledge points (rate < 0.7)."""
        stats: dict[str, list[bool]] = {}
        for row in anchor_results:
            knowledge_ids = list(row.get("knowledge_ids") or [])
            if not knowledge_ids:
                continue
            is_correct = bool(row.get("is_correct"))
            for kid in knowledge_ids:
                stats.setdefault(kid, []).append(is_correct)

        rates: dict[str, float] = {}
        weak: list[str] = []
        for kid, outcomes in stats.items():
            rate = sum(1 for ok in outcomes if ok) / len(outcomes)
            rates[kid] = rate
            if rate < 0.7:
                weak.append(kid)

        return {
            "weak_knowledge_points": weak,
            "knowledge_rates": rates,
            "answered_items": len(anchor_results),
        }
