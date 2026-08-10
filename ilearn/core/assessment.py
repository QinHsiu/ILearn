"""Assessment paper assembly from curriculum templates."""

from __future__ import annotations

import random
from fractions import Fraction

from ilearn.core.schemas import (
    AssessmentItem,
    AssessmentPaper,
    Difficulty,
    ItemTemplate,
    ItemType,
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
