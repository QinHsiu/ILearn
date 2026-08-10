"""Assessment paper assembly from curriculum templates."""

from __future__ import annotations

import random
from fractions import Fraction

from ilearn.core.schemas import (
    AssessmentItem,
    AssessmentPaper,
    BlueprintSlot,
    Difficulty,
    ItemTemplate,
    ItemType,
    PaperBlueprint,
    StudentProfile,
)
from ilearn.providers.curriculum import (
    CurriculumProvider,
    eval_answer_expr,
    fill_template_slots,
    render_choices,
    render_template_text,
)

# Joint (difficulty, type) blueprint: 10 easy / 8 medium / 2 hard and 8 choice / 8 fill / 4 constructed.
MIX_BLUEPRINT: list[tuple[Difficulty, ItemType]] = [
    ("easy", "choice"),
    ("easy", "fill"),
    ("easy", "choice"),
    ("easy", "fill"),
    ("easy", "constructed"),
    ("easy", "choice"),
    ("easy", "fill"),
    ("easy", "choice"),
    ("easy", "fill"),
    ("easy", "constructed"),
    ("medium", "choice"),
    ("medium", "fill"),
    ("medium", "choice"),
    ("medium", "fill"),
    ("medium", "constructed"),
    ("medium", "choice"),
    ("medium", "fill"),
    ("medium", "constructed"),
    ("hard", "choice"),
    ("hard", "fill"),
]


def build_blueprint(
    profile: StudentProfile,
    weak_ids: list[str] | None = None,
) -> PaperBlueprint:
    """Build a 20-slot blueprint; optionally target weak knowledge nodes."""
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
    return PaperBlueprint(grade=profile.grade, slots=slots)


def fill_blueprint(
    profile: StudentProfile,
    blueprint: PaperBlueprint,
    curriculum: CurriculumProvider,
    *,
    rng: random.Random | None = None,
) -> AssessmentPaper:
    """Instantiate blueprint slots into a full assessment paper."""
    builder = AssessmentBuilder(curriculum, rng=rng)
    used_template_ids: set[str] = set()
    items = [
        builder.instantiate_slot(profile, slot, index, used_template_ids)
        for index, slot in enumerate(blueprint.slots)
    ]
    return AssessmentPaper(
        items=items,
        grade=profile.grade,
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

    def build(self, profile: StudentProfile, n: int = 20) -> AssessmentPaper:
        if n != len(MIX_BLUEPRINT):
            raise AssessmentBuildError(
                f"unsupported paper size n={n}; only n={len(MIX_BLUEPRINT)} is supported"
            )

        grade = profile.grade
        used_template_ids: set[str] = set()
        items: list[AssessmentItem] = []

        for index, (difficulty, item_type) in enumerate(MIX_BLUEPRINT):
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

            template = self._rng.choice(candidates)
            used_template_ids.add(template.id)
            items.append(self._instantiate(template, index))

        return AssessmentPaper(
            items=items,
            grade=grade,
            curriculum_label=self._provider.label,
            paper_version="1.0.0",
        )

    def instantiate_slot(
        self,
        profile: StudentProfile,
        slot: BlueprintSlot,
        index: int,
        used_template_ids: set[str],
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
        template = self._rng.choice(candidates)
        used_template_ids.add(template.id)
        return self._instantiate(template, index)

    def build_followup(
        self,
        profile: StudentProfile,
        weak_knowledge_ids: list[str],
        size: int = 8,
    ) -> AssessmentPaper:
        """Build a smaller practice paper targeting weak knowledge nodes."""
        templates = [
            template
            for template in self._provider.list_templates(profile.grade)
            if any(kid in weak_knowledge_ids for kid in template.knowledge_ids)
        ]
        if not templates:
            raise AssessmentBuildError("no templates for weak knowledge ids")
        self._rng.shuffle(templates)
        picked = templates[: min(size, len(templates))]
        items = [
            self._instantiate(template, index)
            for index, template in enumerate(picked)
        ]
        return AssessmentPaper(
            items=items,
            grade=profile.grade,
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
        )
