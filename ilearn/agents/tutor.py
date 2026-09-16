"""Socratic TutorAgent — offline rule-based hint escalation."""

from __future__ import annotations

import re
from typing import Any

from ilearn.core.hints import hint_for_error
from ilearn.core.intervention_library import (
    get_tiered_intervention,
    intervention_hint_for_item,
    lookup_intervention,
)
from ilearn.core.replan import FRUSTRATION_THRESHOLD
from ilearn.core.schemas import AssessmentItem, ErrorTag, TutorPhase, TutorTurn

_WRONG_KEYWORDS = ("不对", "不会", "还是错", "错了", "不知道", "不懂", "还是不对")

_ERROR_STRATEGIES: dict[str, str] = {
    "concept_gap": "概念澄清：请先回顾这个概念的准确定义。",
    "calc_error": "步骤引导：请检查你的计算步骤，看看哪一步可能出了问题。",
    "misread": "元认知检查：请再仔细检查一遍题目和你的答案。",
    "method_wrong": "方法提示：请想想这道题更合适用哪种解题方法。",
    "incomplete": "过程补全：请把解题步骤写完整，再检查结论。",
}

_CALM_PREFIX = (
    "先别着急，我们放慢一步。答错很正常，我们一起把卡住的地方找出来。"
)


class TutorAgent:
    name = "tutor"

    def __init__(self, llm: Any | None = None) -> None:
        """Optional free-LLM client (``available`` / ``chat_text``); else rule engine."""
        self._llm = llm

    @staticmethod
    def _redact_answer(message: str, item: AssessmentItem) -> str:
        key = (item.answer_key or "").strip()
        if not key:
            return message
        text = message.replace(key, "□")
        compact = re.sub(r"\s+", "", key)
        if re.fullmatch(r"[0-9]+(\.[0-9]+)?", compact):
            if "." in compact:
                left, right = compact.split(".", 1)
                pat = re.compile(
                    rf"{re.escape(left)}\s*[.\.．。]\s*{re.escape(right)}"
                )
                text = pat.sub("□", text)
            else:
                pat = re.compile(rf"(?<!\d){re.escape(compact)}(?!\d)")
                text = pat.sub("□", text)
        return text

    def start(
        self,
        item: AssessmentItem,
        error_tag: str | None,
        *,
        frustration: float = 0.0,
    ) -> TutorTurn:
        steps = []
        for step in item.rubric_steps or []:
            steps.append(self._redact_answer(step, item))
        steps_hint = ""
        if steps:
            steps_hint = f"（共 {len(steps)} 步：{' → '.join(steps)}）"
        message = (
            f"我们一起来看看这道题{steps_hint}。"
            "你觉得哪一步最不清楚？请告诉我是第几步或描述你的困惑。"
        )
        message = self._with_calm_tone(message, frustration)
        message = self._redact_answer(message, item)
        return TutorTurn(phase="locate_gap", message=message, error_tag=error_tag)

    def step(
        self,
        state: TutorPhase,
        user_message: str,
        item: AssessmentItem,
        error_tag: str | None = None,
        *,
        frustration: float = 0.0,
    ) -> TutorTurn:
        tag: ErrorTag | None = error_tag  # type: ignore[assignment]
        llm_turn = self._try_llm_step(state, user_message, item, tag, frustration=frustration)
        if llm_turn is not None:
            return llm_turn
        if state == "locate_gap":
            _, hint_text = hint_for_error(tag, fail_streak=0)
            skill_hint = intervention_hint_for_item(item, tag)
            if skill_hint:
                hint_text = f"{hint_text}；{skill_hint}"
            message = f"好的，我们先从这个方向入手：{hint_text}。你可以再想想这一步。"
            message = self._with_calm_tone(message, frustration)
            message = self._redact_answer(message, item)
            return TutorTurn(phase="hint_1", message=message, error_tag=tag)

        if state == "hint_1":
            _, hint_text = hint_for_error(tag, fail_streak=1)
            message = f"再给你一点提示：{hint_text}。试着按这个思路检查一下。"
            message = self._with_calm_tone(message, frustration)
            message = self._redact_answer(message, item)
            return TutorTurn(phase="hint_2", message=message, error_tag=tag)

        if state == "hint_2":
            message = "现在请你重新尝试完成那一步，写出你的计算或推理过程。"
            message = self._with_calm_tone(message, frustration)
            message = self._redact_answer(message, item)
            return TutorTurn(phase="retry", message=message, error_tag=tag)

        if state == "retry":
            if self._retry_failed(user_message):
                message = self._build_explanation(item)
                message = self._with_calm_tone(message, frustration)
                message = self._redact_answer(message, item)
                return TutorTurn(
                    phase="explain",
                    message=message,
                    error_tag=tag,
                    action="suggest_review",
                )
            message = "很好！你已经找到了关键步骤，继续完成后面的部分吧。"
            message = self._redact_answer(message, item)
            return TutorTurn(phase="done", message=message, error_tag=tag)

        if state == "explain":
            message = (
                "希望思路梳理对你有帮助。先回顾概念再动手；"
                "我们不会直接给出最终答案——卡住时可以请教老师，或稍后再试。"
            )
            message = self._redact_answer(message, item)
            return TutorTurn(
                phase="done",
                message=message,
                error_tag=tag,
                action="suggest_review",
            )

        message = self._redact_answer("辅导已结束。如有疑问可以继续提问。", item)
        return TutorTurn(phase="done", message=message, error_tag=tag)

    def _try_llm_step(
        self,
        state: TutorPhase,
        user_message: str,
        item: AssessmentItem,
        error_tag: ErrorTag | None,
        *,
        frustration: float,
    ) -> TutorTurn | None:
        """Ask the free LLM for a Socratic hint; never put answer_key in the prompt."""
        if state not in {"locate_gap", "hint_1"}:
            return None
        llm = self._llm
        if llm is None or not getattr(llm, "available", lambda: False)():
            return None
        next_phase: TutorPhase = "hint_1" if state == "locate_gap" else "hint_2"
        system = (
            "你是小学数学苏格拉底助教。只用提问引导学生，"
            "禁止给出最终数值答案或可直接抄写的结论。中文简短回复。"
        )
        steps = " → ".join(item.rubric_steps or []) or "（无分步）"
        user = (
            f"题目：{item.stem}\n"
            f"评分步骤：{steps}\n"
            f"学生说：{user_message}\n"
            f"可能错因：{error_tag or '未知'}\n"
            "请只给一句引导性问题，不要写出最终答案。"
        )
        try:
            raw = llm.chat_text(system, user)
        except Exception:
            return None
        message = self._redact_answer(str(raw or "").strip(), item)
        if not message:
            return None
        message = self._with_calm_tone(message, frustration)
        return TutorTurn(phase=next_phase, message=message, error_tag=error_tag)

    def get_socratic_hint_with_diagnosis(
        self,
        item: AssessmentItem,
        student_input: str,
        diagnosis: dict[str, Any] | None,
        *,
        phase: TutorPhase = "locate_gap",
        error_tag: str | None = None,
        max_hint_level: int = 2,
        skill_id: str | None = None,
        frustration: float = 0.0,
    ) -> TutorTurn:
        """Prefix strategy from diagnosis/error type, then run normal Socratic step."""
        del max_hint_level
        tag = error_tag
        if not tag and diagnosis:
            error_types = list(diagnosis.get("error_types") or [])
            if error_types:
                tag = str(error_types[0])
            attribution = diagnosis.get("error_attribution") or {}
            top = list(attribution.get("top_tags") or [])
            if not tag and top:
                tag = str(top[0])
        strategy = self._strategy_for_error(tag)
        kids = list(item.knowledge_ids or [])
        mastery = self._mastery_for_skill(diagnosis, skill_id, kids)
        tiered = get_tiered_intervention(skill_id or (kids[0] if kids else None), mastery)
        intervention = lookup_intervention(skill_id, *kids)
        turn = self.step(
            phase, student_input, item, tag, frustration=frustration
        )
        hint = (tiered or {}).get("hint") or (intervention or {}).get("hint")
        prefix_parts = [p for p in (strategy, hint) if p]
        if tiered and tiered.get("content"):
            prefix_parts.insert(0, f"【分层干预·{tiered.get('tier')}】{tiered['content']}")
        if prefix_parts:
            turn = turn.model_copy(
                update={"message": "\n\n".join(prefix_parts) + f"\n\n{turn.message}"}
            )
        turn = turn.model_copy(
            update={"message": self._redact_answer(turn.message, item)}
        )
        return turn

    @staticmethod
    def _with_calm_tone(message: str, frustration: float) -> str:
        if frustration < FRUSTRATION_THRESHOLD:
            return message
        if _CALM_PREFIX in message:
            return message
        return f"{_CALM_PREFIX}\n\n{message}"

    @staticmethod
    def _mastery_for_skill(
        diagnosis: dict[str, Any] | None,
        skill_id: str | None,
        knowledge_ids: list[str],
    ) -> float:
        if not diagnosis:
            return 0.5
        mastery_map = dict(diagnosis.get("skill_mastery") or {})
        if skill_id and skill_id in mastery_map:
            return float(mastery_map[skill_id])
        for kid in knowledge_ids:
            if kid in mastery_map:
                return float(mastery_map[kid])
        rows = diagnosis.get("knowledge_mastery") or []
        for row in rows:
            if isinstance(row, dict):
                kid = row.get("knowledge_id")
                score = row.get("score_rate")
            else:
                kid = getattr(row, "knowledge_id", None)
                score = getattr(row, "score_rate", None)
            if kid in {skill_id, *knowledge_ids} and score is not None:
                return float(score)
        return 0.5

    @staticmethod
    def _strategy_for_error(error_tag: str | None) -> str:
        if not error_tag:
            return "请重新审题，找出关键信息。"
        return _ERROR_STRATEGIES.get(error_tag, "请重新审题，找出关键信息。")

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
