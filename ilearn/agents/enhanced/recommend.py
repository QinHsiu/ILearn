"""Personalized recommendation agent (edition_0909_2 / PR02)."""

from __future__ import annotations

from typing import Any

from ilearn.agents.enhanced.base import EnhancedAgentBase
from ilearn.core.models.enhanced_profile import StudentFiveDimProfile
from ilearn.providers.llm import LLMClient


class RecommendAgent(EnhancedAgentBase):
    """Recommend up to 5 knowledge points from five-dim cognitive slice."""

    def __init__(
        self,
        llm: LLMClient | None = None,
        *,
        stub_mode: bool = False,
    ) -> None:
        super().__init__(llm, stub_mode=stub_mode)

    def recommend_from_profile(
        self,
        profile: StudentFiveDimProfile | dict[str, Any],
        *,
        syllabus: dict[str, Any] | None = None,
        history: list[Any] | None = None,
    ) -> list[dict[str, str]]:
        if isinstance(profile, StudentFiveDimProfile):
            payload = profile.model_dump(mode="json")
        else:
            payload = dict(profile)
        # Public helper bypasses the Flag gate in ``run()``; orchestrator
        # already gates before calling this method.
        result = self._execute(
            {
                "enhanced_profile": payload,
                "syllabus": syllabus or {},
                "history": history or [],
            }
        )
        rows = result.get("recommendations") or []
        return [row for row in rows if isinstance(row, dict)]

    def _execute(self, state: dict[str, Any]) -> dict[str, Any]:
        profile = state.get("enhanced_profile") or {}
        cognitive = profile.get("cognitive") or {}
        mastery = cognitive.get("knowledge_mastery") or {}
        weak = list(cognitive.get("weak_concepts") or [])
        if self.stub_mode:
            return {"recommendations": self._stub_recommendations(mastery, weak)}
        user = (
            f"学生掌握度：{mastery}\n薄弱点：{weak}\n"
            f"课标：{state.get('syllabus') or {}}\n"
            f"历史：{(state.get('history') or [])[-5:]}\n"
            '推荐5个知识点，输出 JSON 对象：'
            '{"recommendations":[{"kp":"...","reason":"..."}]}'
        )
        payload = self._chat_json("你是个性化推荐器，只输出 JSON 对象。", user)
        raw = (payload or {}).get("recommendations") if isinstance(payload, dict) else None
        if not isinstance(raw, list):
            return {"recommendations": self._stub_recommendations(mastery, weak)}
        cleaned: list[dict[str, str]] = []
        for item in raw:
            if not isinstance(item, dict):
                continue
            kp = item.get("kp")
            if not kp:
                continue
            cleaned.append(
                {"kp": str(kp), "reason": str(item.get("reason") or "个性化推荐")}
            )
        return {"recommendations": cleaned[:5]}

    @staticmethod
    def _stub_recommendations(
        mastery: dict[str, Any], weak: list[Any]
    ) -> list[dict[str, str]]:
        ordered = sorted(
            ((str(k), float(v)) for k, v in mastery.items()),
            key=lambda kv: kv[1],
        )
        picks = [k for k, _ in ordered[:5]]
        for item in weak:
            key = str(item)
            if key not in picks:
                picks.append(key)
            if len(picks) >= 5:
                break
        if not picks:
            picks = ["review_basics"]
        return [
            {"kp": kp, "reason": "基于掌握度薄弱点的离线推荐"} for kp in picks[:5]
        ]
