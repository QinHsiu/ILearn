"""Shared base for edition_0909 enhanced agents (offline-safe)."""

from __future__ import annotations

import json
import re
from typing import Any

from ilearn.core.enhanced_flags import is_enhanced_enabled
from ilearn.providers.llm import LLMClient


def _extract_json_object(text: str) -> dict[str, Any] | None:
    match = re.search(r"\{[\s\S]*\}", text)
    if not match:
        return None
    try:
        data = json.loads(match.group())
    except json.JSONDecodeError:
        return None
    return data if isinstance(data, dict) else None


def _extract_json_array(text: str) -> list[Any] | None:
    match = re.search(r"\[[\s\S]*\]", text)
    if not match:
        return None
    try:
        data = json.loads(match.group())
    except json.JSONDecodeError:
        return None
    return data if isinstance(data, list) else None


class SyllabusValidator:
    """Syllabus gate — LLM when available, otherwise accept-all stub."""

    def __init__(
        self,
        llm: LLMClient | None = None,
        *,
        stub_mode: bool = False,
    ) -> None:
        self.llm = llm
        self.stub_mode = stub_mode or llm is None or not llm.available()

    def validate(
        self, output: dict[str, Any], syllabus: dict[str, Any]
    ) -> dict[str, Any]:
        if not is_enhanced_enabled("ENABLE_ENHANCED_AGENTS"):
            return {"valid": True, "issues": [], "suggestions": []}
        if self.stub_mode:
            return {"valid": True, "issues": [], "suggestions": []}
        assert self.llm is not None
        user = (
            "校验以下内容是否符合课标要求，输出 JSON："
            '{"valid": bool, "issues": [], "suggestions": []}\n'
            f"课标：{json.dumps(syllabus, ensure_ascii=False)}\n"
            f"待校验：{json.dumps(output, ensure_ascii=False)}"
        )
        try:
            return self.llm.chat_json(
                "你是课标校验器，只输出 JSON。",
                user,
                fallback=True,
            )
        except Exception:
            return {"valid": True, "issues": [], "suggestions": []}


class EnhancedAgentBase:
    """Base class: flag gate + optional syllabus validation."""

    def __init__(
        self,
        llm: LLMClient | None = None,
        *,
        stub_mode: bool = False,
    ) -> None:
        self.llm = llm
        self.stub_mode = stub_mode or llm is None or not (
            llm.available() if llm is not None else False
        )
        self.validator = SyllabusValidator(llm, stub_mode=self.stub_mode)

    def run(self, state: dict[str, Any]) -> dict[str, Any]:
        if not is_enhanced_enabled("ENABLE_ENHANCED_AGENTS"):
            return {}
        result = self._execute(state)
        if not result:
            return result
        validation = self.validator.validate(result, state.get("syllabus") or {})
        if not validation.get("valid", True):
            result = self._auto_correct(result, validation)
        return result

    def _execute(self, state: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError

    def _auto_correct(
        self, result: dict[str, Any], validation: dict[str, Any]
    ) -> dict[str, Any]:
        if self.stub_mode or self.llm is None:
            return result
        user = (
            f"修正输出为合规 JSON。原输出：{json.dumps(result, ensure_ascii=False)}；"
            f"问题：{validation.get('issues')}；建议：{validation.get('suggestions')}"
        )
        try:
            fixed = self.llm.chat_json(
                "你是输出修正器，只输出 JSON 对象。",
                user,
                fallback=True,
            )
            return fixed if isinstance(fixed, dict) else result
        except Exception:
            return result

    def _chat_json(self, system: str, user: str) -> dict[str, Any] | None:
        if self.stub_mode or self.llm is None:
            return None
        try:
            return self.llm.chat_json(system, user, fallback=True)
        except Exception:
            return None
