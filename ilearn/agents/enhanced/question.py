"""Question generation agent (edition_0909_2 / PR02)."""

from __future__ import annotations

from typing import Any

from ilearn.agents.enhanced.base import EnhancedAgentBase
from ilearn.providers.llm import LLMClient


class QuestionGeneratorAgent(EnhancedAgentBase):
    """Generate one syllabus-constrained practice item."""

    def __init__(
        self,
        llm: LLMClient | None = None,
        *,
        stub_mode: bool = False,
    ) -> None:
        super().__init__(llm, stub_mode=stub_mode)

    def generate(
        self,
        *,
        target_kp: str,
        grade: str | int = "5",
        difficulty: str = "medium",
        syllabus: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        return self._execute(
            {
                "target_kp": target_kp,
                "grade": str(grade),
                "difficulty": difficulty,
                "syllabus": syllabus or {},
            }
        )

    def _execute(self, state: dict[str, Any]) -> dict[str, Any]:
        kp = str(state.get("target_kp") or "basics")
        grade = str(state.get("grade") or "5")
        difficulty = str(state.get("difficulty") or "medium")
        if self.stub_mode:
            return self._stub_item(kp, grade, difficulty)
        user = (
            f"为{grade}年级出1道{difficulty}难度题目，考查：{kp}。\n"
            f"课标：{state.get('syllabus') or {}}\n"
            '输出 JSON：{"type":"choice","stem":"...","options":["A","B","C","D"],'
            '"answer":"A","explanation":"..."}'
        )
        payload = self._chat_json("你是出题器，只输出 JSON 对象。", user)
        if isinstance(payload, dict) and payload.get("stem"):
            return payload
        return self._stub_item(kp, grade, difficulty)

    @staticmethod
    def _stub_item(kp: str, grade: str, difficulty: str) -> dict[str, Any]:
        return {
            "type": "choice",
            "stem": f"（离线桩）{grade}年级·{difficulty}：关于「{kp}」的练习题",
            "options": ["A. 选项一", "B. 选项二", "C. 选项三", "D. 选项四"],
            "answer": "A",
            "explanation": f"离线桩题，目标知识点：{kp}",
            "knowledge_point": kp,
        }
