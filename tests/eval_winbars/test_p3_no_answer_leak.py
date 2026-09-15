"""P3 win-bar: tutor messages must never leak answer_key."""

from __future__ import annotations

import re

from ilearn.agents.tutor import TutorAgent
from ilearn.core.schemas import AssessmentItem


def _normalize(text: str) -> str:
    return re.sub(r"\s+", "", text or "")


def assert_no_answer_leak(message: str, answer_key: str | None) -> None:
    if not answer_key:
        return
    msg = _normalize(message)
    key = _normalize(answer_key)
    assert key not in msg, f"answer leaked: {answer_key!r} in {message!r}"
    if re.fullmatch(r"[0-9]+(\.[0-9]+)?", key):
        compact_msg = re.sub(r"[^\d.]", "", message or "")
        assert key not in compact_msg, f"numeric answer leaked in {message!r}"


def _item() -> AssessmentItem:
    return AssessmentItem(
        id="leak-q1",
        stem="计算 1.2×3",
        type="fill",
        difficulty="easy",
        knowledge_ids=["kp_decimal"],
        answer_key="3.6",
        rubric_steps=["对齐小数位", "相乘", "点小数点"],
    )


def test_p3_full_path_never_leaks_answer_key():
    agent = TutorAgent()
    item = _item()
    messages: list[str] = []

    turn = agent.start(item, "calc_error")
    messages.append(turn.message)
    phase = turn.phase

    for user_msg in ("第二步不清楚", "还是不会", "试一下", "还是不对，不会", "好的"):
        turn = agent.step(phase, user_msg, item, "calc_error")
        messages.append(turn.message)
        phase = turn.phase
        if phase == "done":
            break

    assert any("□" in m or "最终答案" in m or "概念" in m for m in messages)
    for msg in messages:
        assert_no_answer_leak(msg, item.answer_key)


def test_p3_rubric_steps_do_not_embed_answer():
    item = _item()
    item.rubric_steps = ["对齐小数位", "算出 3.6", "检验"]
    turn = TutorAgent().start(item, "calc_error")
    assert_no_answer_leak(turn.message, "3.6")
    assert "3.6" not in turn.message
