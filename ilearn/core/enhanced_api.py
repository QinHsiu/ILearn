"""API helpers for edition_0909 enhanced responses (PR03)."""

from __future__ import annotations

from typing import Any

from ilearn.agents.enhanced.recommend import RecommendAgent
from ilearn.core.enhanced_flags import is_enhanced_enabled
from ilearn.core.enhanced_session import get_enhanced_blob, get_enhanced_profile
from ilearn.core.schemas import SessionState


def enhanced_api_active(enhanced: bool) -> bool:
    """Query opt-in AND ENABLE_ENHANCED_API flag."""
    return bool(enhanced) and is_enhanced_enabled("ENABLE_ENHANCED_API")


def build_suggestions(session: SessionState) -> list[dict[str, str]]:
    """Prefer stored recommendations; else stub RecommendAgent from profile."""
    blob = get_enhanced_blob(session) or {}
    stored = blob.get("recommendations")
    if isinstance(stored, list) and stored:
        return [row for row in stored if isinstance(row, dict)]

    profile = get_enhanced_profile(session)
    if profile is None:
        return []
    return RecommendAgent(llm=None, stub_mode=True).recommend_from_profile(profile)


def build_enhanced_overlay(session: SessionState) -> dict[str, Any]:
    """Five-dim profile + personalized suggestions for API consumers."""
    profile = get_enhanced_profile(session)
    return {
        "enhanced_profile": (
            profile.model_dump(mode="json") if profile is not None else None
        ),
        "suggestions": build_suggestions(session),
        "schema_version": (get_enhanced_blob(session) or {}).get("schema_version", 1),
    }


def attach_enhanced_fields(payload: dict[str, Any], session: SessionState) -> dict[str, Any]:
    """Merge enhanced overlay into an existing summary/dict payload."""
    out = dict(payload)
    out.update(build_enhanced_overlay(session))
    return out


def render_enhanced_report_markdown(session: SessionState) -> str:
    """Markdown report focusing on five-dim profile and suggestions."""
    overlay = build_enhanced_overlay(session)
    profile = overlay.get("enhanced_profile") or {}
    cognitive = profile.get("cognitive") or {}
    emotional = profile.get("emotional") or {}
    behavioral = profile.get("behavioral") or {}
    metacognitive = profile.get("metacognitive") or {}
    contextual = profile.get("contextual") or {}
    suggestions = overlay.get("suggestions") or []

    lines = [
        "# ILearn 增强学习报告",
        "",
        "## 基本信息",
        "",
        f"- **会话：** {session.session_id}",
        f"- **地区：** {session.profile.region}",
        f"- **年级：** {session.profile.grade}",
        f"- **情境年级：** {contextual.get('grade') or session.profile.grade}",
        "",
        "## 五维画像摘要",
        "",
        "### 认知",
        f"- **整体薄弱点：** {', '.join(cognitive.get('weak_concepts') or []) or '暂无'}",
        f"- **优势点：** {', '.join(cognitive.get('strong_concepts') or []) or '暂无'}",
        "",
        "### 情感 / 行为 / 元认知",
        f"- **当前情绪：** {emotional.get('current_emotion') or 'neutral'}",
        f"- **参与度：** {behavioral.get('engagement_score', 0.5)}",
        f"- **学习风格：** {metacognitive.get('learning_style') or 'guided'}",
        "",
        "## 个性化建议",
        "",
    ]
    if not suggestions:
        lines.append("- 暂无增强建议（可先完成诊断并开启增强 Flag）")
    else:
        for row in suggestions:
            kp = row.get("kp") or "知识点"
            reason = row.get("reason") or ""
            lines.append(f"- **{kp}**：{reason}")
    lines.append("")
    return "\n".join(lines)
