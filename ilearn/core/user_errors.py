"""User-facing error codes for API / orchestrator failures."""

from __future__ import annotations

from typing import Any


ERROR_REGISTRY: dict[str, dict[str, str]] = {
    "E-001": {
        "user_action": "当前年级暂未开放，请选择 4–6 年级，或关注后续更新。",
        "technical_prefix": "GradeNotSupported",
    },
    "E-002": {
        "user_action": "诊断数据不足，请先完成批改后再试。",
        "technical_prefix": "must be graded before diagnosis",
    },
    "E-003": {
        "user_action": "报告生成较慢，请稍后刷新查看。",
        "technical_prefix": "PDF",
    },
    "E-004": {
        "user_action": "当前地区课标数据暂未覆盖，请切换至北京或上海地区。",
        "technical_prefix": "RegionNotSupported",
    },
    "E-010": {
        "user_action": "操作顺序不正确，请按测评流程继续。",
        "technical_prefix": "illegal phase transition",
    },
    "E-011": {
        "user_action": "请先生成测评卷，再继续作答或辅导。",
        "technical_prefix": "must have an assessment paper",
    },
    "E-012": {
        "user_action": "请先提交答案，再进行批改。",
        "technical_prefix": "missing answers",
    },
    "E-013": {
        "user_action": "请先完成诊断，再生成或调整学习计划。",
        "technical_prefix": "must be diagnosed",
    },
    "E-014": {
        "user_action": "本题提示次数已用完，请先自行作答或查看讲解。",
        "technical_prefix": "hints exhausted",
    },
    "E-015": {
        "user_action": "巩固练习需要薄弱知识点，当前诊断未发现可巩固项。",
        "technical_prefix": "practice loop requires weak",
    },
}


class UserFriendlyError(Exception):
    """Structured error that APIs can render as actionable guidance."""

    def __init__(
        self,
        code: str,
        *,
        technical_detail: str,
        user_action: str | None = None,
    ) -> None:
        self.code = code
        reg = ERROR_REGISTRY.get(code) or {}
        self.user_action = user_action or reg.get("user_action") or technical_detail
        self.technical_detail = technical_detail
        super().__init__(self.user_action)

    def to_response(self, *, include_detail: bool = True) -> dict[str, Any]:
        body: dict[str, Any] = {
            "error_code": self.code,
            "message": self.user_action,
            "detail": self.user_action,
        }
        if include_detail:
            body["technical_detail"] = self.technical_detail
        return body


def map_exception_message(message: str) -> UserFriendlyError | None:
    """Best-effort map of legacy ValueError text → UserFriendlyError."""
    text = message or ""
    lowered = text.lower()
    for code, meta in ERROR_REGISTRY.items():
        prefix = meta.get("technical_prefix") or ""
        if prefix and prefix.lower() in lowered:
            return UserFriendlyError(
                code,
                technical_detail=text,
                user_action=meta.get("user_action"),
            )
    if "region" in lowered and (
        "unsupported" in lowered
        or "不支持" in text
        or "暂未覆盖" in text
        or "regionnotsupported" in lowered
    ):
        return UserFriendlyError("E-004", technical_detail=text)
    # Curriculum / grade fail-closed
    if "grade" in lowered and ("not" in lowered or "unsupported" in lowered or "支持" in text):
        return UserFriendlyError("E-001", technical_detail=text)
    return None
