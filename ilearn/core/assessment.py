"""Assessment paper assembly from curriculum templates."""

from __future__ import annotations

import random
from fractions import Fraction
from pathlib import Path

from ilearn.core.schemas import (
    AssessmentItem,
    AssessmentPaper,
    BlueprintSlot,
    Difficulty,
    ItemTemplate,
    ItemType,
    PaperBlueprint,
    LearnerPortrait,
    StudentProfile,
)
from ilearn.core.subject_quotas import (
    MIX_BLUEPRINT,
    _slots_from_quota,
    build_blueprint_for_subject,
    load_quota,
)
from ilearn.providers.curriculum import (
    CurriculumProvider,
    eval_answer_expr,
    fill_template_slots,
    render_choices,
    render_template_text,
    require_pilot_grade,
)


def build_blueprint(
    profile: StudentProfile,
    weak_ids: list[str] | None = None,
    *,
    pilot_dir: Path | str | None = None,
) -> PaperBlueprint:
    """Build a 20-slot blueprint; optionally target weak knowledge nodes."""
    if profile.subject != "math":
        if pilot_dir is None:
            pilot_dir = Path(__file__).resolve().parents[2] / "data" / "pilot"
        return build_blueprint_for_subject(profile, pilot_dir, weak_ids)
    weak_queue = list(weak_ids) if weak_ids else []
    slots: list[BlueprintSlot] = []
    for difficulty, item_type in MIX_BLUEPRINT:
        kid = weak_queue.pop(0) if weak_queue else None
        slots.append(
            BlueprintSlot(
                difficulty=difficulty,
                item_type=item_type,
                knowledge_id=kid,
            )
        )
    return PaperBlueprint(grade=require_pilot_grade(profile.grade), slots=slots)  # type: ignore[arg-type]


def fill_blueprint(
    profile: StudentProfile,
    blueprint: PaperBlueprint,
    curriculum: CurriculumProvider,
    *,
    rng: random.Random | None = None,
    portrait: LearnerPortrait | None = None,
) -> AssessmentPaper:
    """Instantiate blueprint slots into a full assessment paper."""
    builder = AssessmentBuilder(curriculum, rng=rng)
    used_template_ids: set[str] = set()
    items = [
        builder.instantiate_slot(profile, slot, index, used_template_ids, portrait=portrait)
        for index, slot in enumerate(blueprint.slots)
    ]
    return AssessmentPaper(
        items=items,
        grade=require_pilot_grade(profile.grade),  # type: ignore[arg-type]
        curriculum_label=curriculum.label,
        blueprint=blueprint,
        paper_version="1.0.0",
    )


def validate_paper(paper: AssessmentPaper) -> None:
    """Ensure paper meets fixed size and difficulty quotas."""
    if len(paper.items) != 20:
        raise AssessmentBuildError("paper must have 20 items")
    easy = sum(1 for item in paper.items if item.difficulty == "easy")
    medium = sum(1 for item in paper.items if item.difficulty == "medium")
    hard = sum(1 for item in paper.items if item.difficulty == "hard")
    if (easy, medium, hard) != (10, 8, 2):
        raise AssessmentBuildError(f"difficulty quota mismatch: {(easy, medium, hard)}")
    choice = sum(1 for item in paper.items if item.type == "choice")
    fill = sum(1 for item in paper.items if item.type == "fill")
    constructed = sum(1 for item in paper.items if item.type == "constructed")
    if (choice, fill, constructed) != (8, 8, 4):
        raise AssessmentBuildError(
            f"type quota mismatch: {(choice, fill, constructed)}"
        )


class AssessmentBuildError(Exception):
    """Raised when the fixed mix quotas cannot be satisfied."""


def _replacement_distractor(value: str, used: set[str]) -> str:
    """Create a nearby distinct distractor for a rendered duplicate."""
    for delta in range(1, 20):
        try:
            if ":" in value:
                left, right = value.split(":", 1)
                candidate = f"{left}:{int(right) + delta}"
            elif "/" in value:
                fraction = Fraction(value)
                candidate = str(fraction + delta)
            else:
                number = float(value.replace(",", ""))
                candidate_number = number + delta
                candidate = (
                    str(int(candidate_number))
                    if candidate_number.is_integer()
                    else str(round(candidate_number, 2))
                )
        except (ValueError, ZeroDivisionError):
            candidate = f"{value}（备选{delta + 1}）"
        if candidate not in used:
            return candidate
    raise AssessmentBuildError("could not create unique choice distractors")


def _unique_choices(choices: list[str]) -> list[str]:
    unique: list[str] = []
    used: set[str] = set()
    for choice in choices:
        candidate = choice
        if candidate in used:
            candidate = _replacement_distractor(choice, used)
        unique.append(candidate)
        used.add(candidate)
    return unique


class AssessmentBuilder:
    """Build a 20-item assessment paper from template blueprints."""

    def __init__(
        self,
        provider: CurriculumProvider,
        *,
        rng: random.Random | None = None,
    ) -> None:
        self._provider = provider
        self._rng = rng or random.Random()

    def build(
        self,
        profile: StudentProfile,
        n: int = 20,
        *,
        portrait: LearnerPortrait | None = None,
    ) -> AssessmentPaper:
        mix = load_quota(profile.subject, Path(__file__).resolve().parents[2] / "data" / "pilot")
        blueprint_slots = _slots_from_quota(mix)
        if n != len(blueprint_slots):
            raise AssessmentBuildError(
                f"unsupported paper size n={n}; only n={len(blueprint_slots)} is supported"
            )

        grade = profile.grade
        used_template_ids: set[str] = set()
        items: list[AssessmentItem] = []

        for index, (difficulty, item_type) in enumerate(blueprint_slots):
            candidates = [
                template
                for template in self._provider.list_templates(
                    grade,
                    difficulty=difficulty,
                    item_type=item_type,
                )
                if template.id not in used_template_ids
            ]
            if not candidates:
                raise AssessmentBuildError(
                    f"no unused template for grade={grade} difficulty={difficulty} type={item_type}"
                )

            template = self._choose_template(candidates, portrait)
            used_template_ids.add(template.id)
            items.append(self._instantiate(template, index))

        return AssessmentPaper(
            items=items,
            grade=require_pilot_grade(grade),  # type: ignore[arg-type]
            curriculum_label=self._provider.label,
            paper_version="1.0.0",
        )

    def instantiate_slot(
        self,
        profile: StudentProfile,
        slot: BlueprintSlot,
        index: int,
        used_template_ids: set[str],
        portrait: LearnerPortrait | None = None,
    ) -> AssessmentItem:
        """Pick and instantiate one template matching a blueprint slot."""
        grade = profile.grade
        candidates = [
            template
            for template in self._provider.list_templates(
                grade,
                difficulty=slot.difficulty,
                item_type=slot.item_type,
            )
            if template.id not in used_template_ids
            and (
                slot.knowledge_id is None
                or slot.knowledge_id in template.knowledge_ids
            )
        ]
        if not candidates:
            candidates = [
                template
                for template in self._provider.list_templates(
                    grade,
                    difficulty=slot.difficulty,
                    item_type=slot.item_type,
                )
                if template.id not in used_template_ids
            ]
        if not candidates:
            raise AssessmentBuildError(
                f"no unused template for grade={grade} "
                f"difficulty={slot.difficulty} type={slot.item_type}"
            )
        template = self._choose_template(candidates, portrait)
        used_template_ids.add(template.id)
        return self._instantiate(template, index)

    def _choose_template(
        self,
        candidates: list[ItemTemplate],
        portrait: LearnerPortrait | None,
    ) -> ItemTemplate:
        if portrait and portrait.situation_interest:
            best = max(portrait.situation_interest.values())
            preferred_tags = {
                tag
                for tag, score in portrait.situation_interest.items()
                if score == best and score > 0.5
            }
            preferred = [
                template
                for template in candidates
                if template.situation_tag in preferred_tags
            ]
            if preferred:
                candidates = preferred
        return self._rng.choice(candidates)

    def build_followup(
        self,
        profile: StudentProfile,
        weak_knowledge_ids: list[str],
        size: int = 8,
        *,
        portrait: LearnerPortrait | None = None,
    ) -> AssessmentPaper:
        """Build a smaller practice paper targeting weak knowledge nodes."""
        templates = [
            template
            for template in self._provider.list_templates(profile.grade)
            if any(kid in weak_knowledge_ids for kid in template.knowledge_ids)
        ]
        if not templates:
            raise AssessmentBuildError("no templates for weak knowledge ids")
        if portrait and portrait.situation_interest:
            best = max(portrait.situation_interest.values())
            preferred = [
                template
                for template in templates
                if template.situation_tag in {
                    tag
                    for tag, score in portrait.situation_interest.items()
                    if score == best and score > 0.5
                }
            ]
            if preferred:
                templates = preferred
        self._rng.shuffle(templates)
        picked = templates[: min(size, len(templates))]
        items = [
            self._instantiate(template, index)
            for index, template in enumerate(picked)
        ]
        return AssessmentPaper(
            items=items,
            grade=require_pilot_grade(profile.grade),  # type: ignore[arg-type]
            curriculum_label=self._provider.label,
        )

    def _instantiate(self, template: ItemTemplate, index: int) -> AssessmentItem:
        record = self._provider.get_template_record(template.id)
        values = fill_template_slots(record, self._rng)
        answer_expr = record.get("answer_expr") or record.get("answer_key_template") or ""
        answer_key = eval_answer_expr(answer_expr, values) if answer_expr else None
        stem = render_template_text(record["stem_template"], values, answer=answer_key)

        choices_template = record.get("choices_template")
        choices = (
            render_choices(choices_template, values, answer=answer_key)
            if choices_template
            else None
        )
        if choices is not None:
            choices = _unique_choices(choices)
            self._rng.shuffle(choices)

        rubric_raw = record.get("rubric_steps") or []
        rubric_steps = [
            render_template_text(step, values, answer=answer_key) for step in rubric_raw
        ]

        return AssessmentItem(
            id=f"{template.id}__{index:02d}",
            stem=stem,
            type=template.item_type,
            difficulty=template.difficulty,
            knowledge_ids=list(template.knowledge_ids),
            answer_key=answer_key,
            rubric_steps=rubric_steps,
            choices=choices,
            situation_tag=template.situation_tag,
        )
