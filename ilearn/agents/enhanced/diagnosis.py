"""Error diagnosis agent (edition_0909_2 / PR02)."""

from __future__ import annotations

from typing import Any

from ilearn.agents.enhanced.base import EnhancedAgentBase
from ilearn.providers.llm import LLMClient


class ErrorDiagnosisAgent(EnhancedAgentBase):
    """Lightweight wrong-answer attribution."""

    def __init__(
        self,
        llm: LLMClient | None = None,
        *,
        stub_mode: bool = False,
    ) -> None:
        super().__init__(llm, stub_mode=stub_mode)

    def diagnose_error(
        self,
        *,
        question: dict[str, Any],
        student_answer: str,
        correct_answer: str,
    ) -> dict[str, Any]:
        return self._execute(
            {
                "question": question,
                "student_answer": student_answer,
                "correct_answer": correct_answer,
            }
        )

    def _execute(self, state: dict[str, Any]) -> dict[str, Any]:
        question = state.get("question") or {}
        student_ans = str(state.get("student_answer") or "")
        correct_ans = str(state.get("correct_answer") or "")
        if self.stub_mode:
            return self._stub(student_ans, correct_ans)
        user = (
            f"诊断错因：题目{question}，学生答'{student_ans}'，正确答案'{correct_ans}'。\n"
            '输出 JSON：{"error_types":["..."],"suggestions":["..."],'
            '"review_plan":{"day1":"..."}}'
        )
        payload = self._chat_json("你是错因诊断器，只输出 JSON 对象。", user)
        if isinstance(payload, dict) and payload.get("error_types"):
            return payload
        return self._stub(student_ans, correct_ans)

    @staticmethod
    def _stub(student_ans: str, correct_ans: str) -> dict[str, Any]:
        error_type = "计算失误" if student_ans and correct_ans else "概念混淆"
        return {
            "error_types": [error_type],
            "suggestions": ["回顾本题相关例题，并重做一道同类题"],
            "review_plan": {"day1": "复习核心概念", "day3": "巩固练习"},
        }
