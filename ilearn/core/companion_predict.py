"""Companion Predict — probe-gap / derailment risk (Phase-1 offline)."""

from __future__ import annotations

from typing import Any, Literal

from ilearn.core.mastery_public import build_mastery_public_view
from ilearn.core.schemas import SessionState

RiskLevel = Literal["low", "medium", "high"]


def build_risk_forecast(session: SessionState) -> dict[str, Any]:
    view = build_mastery_public_view(session)
    probe = int(view.probe_gap_count or 0)
    evidence = int(view.evidence_count or 0)
    mastery = view.mastery_percent
    loop = int(session.loop_count or 0)

    score = 0
    reasons: list[str] = []
    if evidence == 0 and session.paper is None:
        score += 2
        reasons.append("还没有测评证据，掌握情况不确定")
    if probe >= 3:
        score += 3
        reasons.append(f"探针缺口偏多（{probe}）")
    elif probe >= 1:
        score += 2
        reasons.append(f"存在探针缺口（{probe}）")
    if mastery is not None and mastery < 60:
        score += 2
        reasons.append(f"公开掌握度偏低（{mastery}%）")
    elif mastery is not None and mastery < 75:
        score += 1
        reasons.append(f"掌握度仍有提升空间（{mastery}%）")
    if loop >= 2:
        score += 1
        reasons.append(f"已进入巩固轮次 {loop}，需防疲劳掉队")

    if score >= 4:
        level: RiskLevel = "high"
    elif score >= 2:
        level = "medium"
    else:
        level = "low"

    if not reasons:
        reasons.append("当前证据平稳，保持节奏即可")

    return {
        "level": level,
        "score": score,
        "probe_gap_count": probe,
        "evidence_count": evidence,
        "mastery_percent": mastery,
        "loop_count": loop,
        "reasons": reasons,
    }


def format_risk_reply(forecast: dict[str, Any]) -> str:
    level = forecast.get("level", "medium")
    label = {"low": "较低", "medium": "中等", "high": "偏高"}.get(level, "中等")
    lines = [f"学习掉队/未掌握风险：**{label}**（score={forecast.get('score', 0)}）。"]
    for r in forecast.get("reasons") or []:
        lines.append(f"- {r}")
    if level in {"medium", "high"}:
        lines.append("建议：先做一轮短测评或针对薄弱点练习，再让我更新预测。")
    else:
        lines.append("建议：按本周计划推进，周末用小测复核一次即可。")
    return "\n".join(lines)
