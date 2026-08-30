"""Rule-based four-dimension validators for assessment items."""

from __future__ import annotations

import re
from dataclasses import dataclass
from random import Random
from typing import Literal

from ilearn.core.assessment import AssessmentBuilder
from ilearn.core.schemas import AssessmentItem, AssessmentPaper, StudentProfile
from ilearn.providers.curriculum import CurriculumProvider

ValidationDimension = Literal[
    "solvability", "realism", "readability", "authenticity"
]

_NUMBER_PATTERN = re.compile(r"\d[\d,]*\.?\d*")

# Grade-band stem length ceilings (characters).
_READABILITY_MAX_LEN: dict[int, int] = {
    4: 120,
    5: 150,
    6: 180,
}

# Upper bound for numeric literals appearing in stems.
_REALISM_MAX_NUMBER: dict[int, float] = {
    4: 50_000,
    5: 100_000,
    6: 500_000,
}

_LIFE_CONTEXT_KEYWORDS = (
    "生活",
    "商店",
    "超市",
    "学校",
    "班级",
    "体育",
    "比赛",
    "足球",
    "篮球",
    "游戏",
    "购物",
    "水果",
    "同学",
    "家庭",
    "家里",
    "旅行",
    "科学",
    "实验",
    "动物",
    "公园",
    "小明",
    "小红",
    "买了",
    "分给",
    "操场",
    "教室",
    "果汁",
    "文具",
    "蛋糕",
    "门票",
    "课桌",
)


@dataclass(frozen=True)
class ValidationIssue:
    item_id: str
    dimension: ValidationDimension
    message: str


def _readability_limit(grade: int) -> int:
    return _READABILITY_MAX_LEN.get(grade, 150)


def _realism_ceiling(grade: int) -> float:
    return _REALISM_MAX_NUMBER.get(grade, 100_000)


def _parse_numbers(stem: str) -> list[float]:
    values: list[float] = []
    for match in _NUMBER_PATTERN.findall(stem):
        try:
            values.append(float(match.replace(",", "")))
        except ValueError:
            continue
    return values


def _has_life_context(item: AssessmentItem) -> bool:
    return any(keyword in item.stem for keyword in _LIFE_CONTEXT_KEYWORDS)


def _validate_item(item: AssessmentItem, *, grade: int) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []

    if item.type in ("choice", "fill"):
        if not item.answer_key or not str(item.answer_key).strip():
            issues.append(
                ValidationIssue(
                    item_id=item.id,
                    dimension="solvability",
                    message="missing or empty answer_key",
                )
            )
    elif item.type == "constructed":
        if not item.rubric_steps:
            issues.append(
                ValidationIssue(
                    item_id=item.id,
                    dimension="solvability",
                    message="constructed item requires rubric_steps",
                )
            )

    ceiling = _realism_ceiling(grade)
    for value in _parse_numbers(item.stem):
        if value > ceiling:
            issues.append(
                ValidationIssue(
                    item_id=item.id,
                    dimension="realism",
                    message=f"number {value:g} exceeds grade-{grade} ceiling {ceiling:g}",
                )
            )
            break

    max_len = _readability_limit(grade)
    if len(item.stem) > max_len:
        issues.append(
            ValidationIssue(
                item_id=item.id,
                dimension="readability",
                message=f"stem length {len(item.stem)} exceeds limit {max_len}",
            )
        )

    if not _has_life_context(item):
        issues.append(
            ValidationIssue(
                item_id=item.id,
                dimension="authenticity",
                message="missing life-context keywords in stem",
            )
        )

    return issues


def validate_paper(paper: AssessmentPaper, *, grade: int) -> list[ValidationIssue]:
    """Return all validation issues for items in a paper."""
    issues: list[ValidationIssue] = []
    for item in paper.items:
        issues.extend(_validate_item(item, grade=grade))
    return issues


def _template_id_from_item_id(item_id: str) -> str:
    if "__" in item_id:
        return item_id.rsplit("__", 1)[0]
    return item_id


def _item_index_from_item_id(item_id: str) -> int:
    if "__" in item_id:
        suffix = item_id.rsplit("__", 1)[1]
        try:
            return int(suffix)
        except ValueError:
            return 0
    return 0


def _alternate_templates(
    item: AssessmentItem,
    *,
    grade: int,
    curriculum: CurriculumProvider,
    exclude_ids: set[str],
) -> list:
    current_template_id = _template_id_from_item_id(item.id)
    exclude_ids = set(exclude_ids) | {current_template_id}
    candidates = [
        template
        for template in curriculum.list_templates(
            grade,
            difficulty=item.difficulty,
            item_type=item.type,
        )
        if template.id not in exclude_ids
        and (
            not item.knowledge_ids
            or any(kid in template.knowledge_ids for kid in item.knowledge_ids)
        )
    ]
    if not candidates:
        candidates = [
            template
            for template in curriculum.list_templates(
                grade,
                difficulty=item.difficulty,
                item_type=item.type,
            )
            if template.id not in exclude_ids
        ]
    return candidates


def revise_paper_once(
    paper: AssessmentPaper,
    issues: list[ValidationIssue],
    *,
    profile: StudentProfile,
    curriculum: CurriculumProvider,
    rng: Random | None = None,
) -> AssessmentPaper:
    """Replace failing items once using alternate templates when available."""
    if not issues:
        return paper

    failing_ids = {issue.item_id for issue in issues}
    builder = AssessmentBuilder(curriculum, rng=rng)
    used_template_ids = {
        _template_id_from_item_id(item.id) for item in paper.items
    }
    revised_items: list[AssessmentItem] = []

    for item in paper.items:
        if item.id not in failing_ids:
            revised_items.append(item)
            continue

        candidates = _alternate_templates(
            item,
            grade=profile.grade,
            curriculum=curriculum,
            exclude_ids=used_template_ids,
        )
        if not candidates:
            revised_items.append(item)
            continue

        template = builder._rng.choice(candidates)
        used_template_ids.add(template.id)
        index = _item_index_from_item_id(item.id)
        revised_items.append(builder._instantiate(template, index))

    return paper.model_copy(update={"items": revised_items})


@dataclass(frozen=True)
class RevisedPaperResult:
    paper: AssessmentPaper
    attempts: int
    fallback_used: bool


def make_fallback_item(
    *,
    index: int = 0,
    knowledge_id: str = "frac_meaning",
) -> AssessmentItem:
    return AssessmentItem(
        id=f"fallback_{index:02d}",
        stem="一个苹果分给2个人，每人分到多少？",
        type="choice",
        difficulty="easy",
        knowledge_ids=[knowledge_id],
        answer_key="1/2",
        choices=["1", "1/2", "2", "1/4"],
        situation_tag="life",
    )


def revise_paper(
    paper: AssessmentPaper,
    issues: list[ValidationIssue],
    *,
    profile: StudentProfile,
    curriculum: CurriculumProvider,
    max_attempts: int = 3,
    rng: Random | None = None,
) -> RevisedPaperResult:
    current = paper
    pending = issues
    attempts = 0
    for _ in range(max(1, max_attempts)):
        if not pending:
            return RevisedPaperResult(
                paper=current, attempts=attempts, fallback_used=False
            )
        attempts += 1
        nxt = revise_paper_once(
            current,
            pending,
            profile=profile,
            curriculum=curriculum,
            rng=rng,
        )
        current = nxt
        pending = validate_paper(current, grade=profile.grade)
    if not pending:
        return RevisedPaperResult(
            paper=current, attempts=attempts, fallback_used=False
        )
    failing = {issue.item_id for issue in pending}
    replaced: list[AssessmentItem] = []
    fb_i = 0
    for item in current.items:
        if item.id in failing:
            replaced.append(make_fallback_item(index=fb_i))
            fb_i += 1
        else:
            replaced.append(item)
    return RevisedPaperResult(
        paper=current.model_copy(update={"items": replaced}),
        attempts=attempts,
        fallback_used=True,
    )
