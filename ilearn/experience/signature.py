"""Structural signatures — abstract action sequences for coarse retrieval (no embeddings)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

# 事件类型 → 签名 token。只取教学动作，忽略噪声；缺失字段时跳过而非报错。
_ACTION_TOKENS: dict[str, Callable[[dict[str, Any]], str]] = {
    "diagnosis.completed": lambda e: f"diagnose:{e.get('confidence_band', 'mid')}",
    "tutoring.hint": lambda e: f"hint:{e.get('hint_level', 0)}",
    "grade.completed": lambda e: f"grade:{'pass' if float(e.get('score') or 0) >= 0.6 else 'fail'}",
    "practice.completed": lambda e: (
        f"practice:{'high' if float(e.get('accuracy') or 0) >= 0.75 else 'low'}"
    ),
    "learner.dismissed": lambda e: "dismiss",
    "practice.abandoned": lambda e: "abandon",
}


@dataclass(frozen=True)
class StructuralSignature:
    """抽象操作序列。与语义描述分离，用于结构粗筛。"""

    tokens: tuple[str, ...]

    def __str__(self) -> str:
        return " → ".join(self.tokens)

    @property
    def key(self) -> str:
        return "|".join(self.tokens)


def extract_signature(
    events: list[dict[str, Any]], max_events: int = 6
) -> StructuralSignature:
    """从一段事件序列抽取结构签名，取最后 max_events 个教学动作事件。"""
    tokens: list[str] = []
    for ev in events:
        etype = ev.get("event_type") or ev.get("kind") or ""
        if str(etype).startswith("noise"):
            continue
        fn = _ACTION_TOKENS.get(str(etype))
        if fn:
            try:
                tokens.append(fn(ev))
            except Exception:
                continue
    return StructuralSignature(tuple(tokens[-max_events:]))
