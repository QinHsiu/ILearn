"""Enhanced profile context hints and cold-start bootstrap (edition_0909_4 P0/P1)."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from ilearn.core.enhanced_flags import is_enhanced_enabled
from ilearn.core.enhanced_profile_adapter import ProfileAdapter
from ilearn.core.enhanced_session import get_enhanced_profile, set_enhanced_profile
from ilearn.core.models.enhanced_profile import (
    EmotionType,
    LearningStyle,
    StudentFiveDimProfile,
)
from ilearn.core.schemas import SessionState

if TYPE_CHECKING:
    from ilearn.providers.curriculum import CurriculumProvider

logger = logging.getLogger(__name__)

_COLD_START_KP_LIMIT = 20
_DEFAULT_MASTERY = 0.5


def build_enhanced_context_hint(profile: StudentFiveDimProfile | None) -> str:
    """Build a teaching context block from five-dim profile (P0)."""
    if profile is None:
        return ""
    parts: list[str] = []

    emotion = profile.emotional.current_emotion
    if emotion == EmotionType.FRUSTRATED:
        parts.append(
            "【学情警报】学生当前有挫败感，回答请务必先给予鼓励，再拆解步骤。"
        )
    elif emotion == EmotionType.CONFUSED:
        parts.append("【学情警报】学生当前感到困惑，请用更通俗的语言重新解释。")
    elif emotion == EmotionType.EXCITED:
        parts.append("【学情积极】学生状态很好，可以适当增加挑战性追问。")

    weak = profile.cognitive.weak_concepts
    if weak:
        weak_str = "、".join(weak[:3])
        parts.append(
            f"该生目前薄弱知识点为：{weak_str}。讲解时请着重这些点，并避免假设他们已经掌握。"
        )

    style = profile.metacognitive.learning_style
    if style == LearningStyle.VISUAL:
        parts.append("该生偏向视觉型学习，建议多使用类比或图像化描述。")
    elif style == LearningStyle.EXPLORATORY:
        parts.append("该生偏向探究型学习，可以引导他们自己发现规律。")
    elif style == LearningStyle.VERBAL:
        parts.append("该生偏向语言型学习，建议多用口头解释与复述。")

    return "\n".join(parts)


def _seed_knowledge_mastery(
    profile: StudentFiveDimProfile,
    curriculum: CurriculumProvider | None,
    grade: int,
) -> None:
    """Fill default 0.5 mastery for pilot knowledge nodes (P1 cold start)."""
    if profile.cognitive.knowledge_mastery:
        return
    ids: list[str] = []
    if curriculum is not None:
        try:
            nodes = curriculum.list_knowledge(grade)
            ids = [node.id for node in nodes[:_COLD_START_KP_LIMIT]]
        except Exception:
            logger.warning("cold start: failed to list knowledge for grade %s", grade)
    if not ids:
        ids = ["basics"]
    profile.cognitive.knowledge_mastery = {kid: _DEFAULT_MASTERY for kid in ids}
    profile.cognitive.weak_concepts = []
    profile.cognitive.strong_concepts = []


def ensure_cold_start_profile(
    session: SessionState,
    curriculum: CurriculumProvider | None = None,
) -> SessionState:
    """Ensure ``metadata.enhanced`` exists when PROFILE flag is on (P1)."""
    if not is_enhanced_enabled("ENABLE_ENHANCED_PROFILE"):
        return session

    existing = get_enhanced_profile(session)
    if existing is not None:
        hint = build_enhanced_context_hint(existing)
        if hint:
            session.metadata["enhanced_context_hint"] = hint
        return session

    logger.info(
        "Cold start: initializing enhanced profile for session %s",
        session.session_id,
    )
    profile = ProfileAdapter.from_session(session)
    if not profile.cognitive.knowledge_mastery:
        _seed_knowledge_mastery(profile, curriculum, int(session.profile.grade))

    session = set_enhanced_profile(session, profile)
    session.metadata["enhanced_context_hint"] = (
        build_enhanced_context_hint(profile)
        or "【系统提示】学生为新用户，尚未建立完整画像，请从基础概念开始引导。"
    )
    return session
