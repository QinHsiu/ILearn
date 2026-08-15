"""Dynamic three-level hint ladder from error tags and fail streaks."""

from __future__ import annotations

from ilearn.core.pedagogical_kb import default_kb
from ilearn.core.schemas import HintLevel

_STREAK_ESCALATION_SUFFIX = "先对照例题步骤，不要直接看答案"
_STREAK_ESCALATION_THRESHOLD = 3

_TAG_HINTS: dict[str, tuple[HintLevel, str]] = {
    "calc_error": ("low", "检查运算过程中的进位/通分"),
    "misread": ("low", "再读一遍题目条件"),
    "concept_gap": ("medium", "回顾相关定义与例题结构"),
    "method_wrong": ("high", "换一种列式思路，先写已知再求未知"),
    "incomplete": ("medium", "补全中间步骤后再写结论"),
}

_DEFAULT_HINT: tuple[HintLevel, str] = ("medium", "回顾相关定义与例题结构")


def hint_for_error(error_tag: str | None, fail_streak: int = 0) -> tuple[HintLevel, str]:
    """Return (level, hint_text). Level escalates with fail_streak; never includes final answer."""
    level, text = _TAG_HINTS.get(error_tag or "", _DEFAULT_HINT)
    kb_text = default_kb().retrieve(error_tag, fail_streak)
    if kb_text:
        text = kb_text
    if fail_streak >= _STREAK_ESCALATION_THRESHOLD:
        level = "high"
        if _STREAK_ESCALATION_SUFFIX not in text:
            text = f"{text}；{_STREAK_ESCALATION_SUFFIX}"
    return level, text


def fail_streak_for_item(prior_grades: list, item_id: str) -> int:
    """Count consecutive incorrect grades for item_id from most recent backward."""
    streak = 0
    for grade in reversed(prior_grades):
        if grade.item_id != item_id:
            continue
        if grade.final_correct:
            break
        streak += 1
    return streak
