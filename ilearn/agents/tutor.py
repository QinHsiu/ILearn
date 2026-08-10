"""Socratic TutorAgent — offline rule-based hint escalation."""

from __future__ import annotations

from ilearn.core.hints import hint_for_error
from ilearn.core.schemas import AssessmentItem, ErrorTag, TutorPhase, TutorTurn

_WRONG_KEYWORDS = ("不对", "不会", "还是错", "错了", "不知道", "不懂", "还是不对")


class TutorAgent:
    name = "tutor"

    def __init__(self) -> None:
        self._error_tag: ErrorTag | None = None

    def start(self, item: AssessmentItem, error_tag: str | None) -> TutorTurn:
        self._error_tag = error_tag  # type: ignore[assignment]
        steps_hint = ""
        if item.rubric_steps:
            steps_hint = f"（共 {len(item.rubric_steps)} 步：{' → '.join(item.rubric_steps)}）"
        message = (
            f"我们一起来看看这道题{steps_hint}。"
            "你觉得哪一步最不清楚？请告诉我是第几步或描述你的困惑。"
        )
        return TutorTurn(phase="locate_gap", message=message, error_tag=self._error_tag)

    def step(
        self,
        state: TutorPhase,
        user_message: str,
        item: AssessmentItem,
    ) -> TutorTurn:
        tag = self._error_tag
        if state == "locate_gap":
            _, hint_text = hint_for_error(tag, fail_streak=0)
            message = f"好的，我们先从这个方向入手：{hint_text}。你可以再想想这一步。"
            return TutorTurn(phase="hint_1", message=message, error_tag=tag)

        if state == "hint_1":
            _, hint_text = hint_for_error(tag, fail_streak=1)
            message = f"再给你一点提示：{hint_text}。试着按这个思路检查一下。"
            return TutorTurn(phase="hint_2", message=message, error_tag=tag)

        if state == "hint_2":
            message = "现在请你重新尝试完成那一步，写出你的计算或推理过程。"
            return TutorTurn(phase="retry", message=message, error_tag=tag)

        if state == "retry":
            if self._retry_failed(user_message):
                message = self._build_explanation(item)
                return TutorTurn(phase="explain", message=message, error_tag=tag)
            message = "很好！你已经找到了关键步骤，继续完成后面的部分吧。"
            return TutorTurn(phase="done", message=message, error_tag=tag)

        if state == "explain":
            message = "希望这次的讲解对你有帮助。下次遇到类似题目，可以先回顾解题步骤再动手。"
            return TutorTurn(phase="done", message=message, error_tag=tag)

        message = "辅导已结束。如有疑问可以继续提问。"
        return TutorTurn(phase="done", message=message, error_tag=tag)

    @staticmethod
    def _retry_failed(user_message: str) -> bool:
        msg = user_message.strip()
        if not msg:
            return True
        return any(kw in msg for kw in _WRONG_KEYWORDS)

    @staticmethod
    def _build_explanation(item: AssessmentItem) -> str:
        parts = ["让我帮你梳理一下思路："]
        if item.rubric_steps:
            for index, step in enumerate(item.rubric_steps, start=1):
                parts.append(f"{index}. {step}")
        else:
            parts.append("先读清题目条件，再选择合适的运算方法，逐步计算并检验。")
        parts.append("按以上步骤重新做一遍，不要直接抄答案。")
        text = " ".join(parts)
        if item.answer_key:
            text = text.replace(item.answer_key, "□")
        return text
