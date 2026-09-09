"""Enhanced weak-first knowledge targeting for assessment blueprints (P0).

Note: lives beside ``ilearn/core/assessment.py`` (not a subpackage) to avoid
import shadowing of the existing assessment module.
"""

from __future__ import annotations

from ilearn.core.enhanced_flags import is_enhanced_enabled
from ilearn.core.enhanced_session import get_enhanced_profile
from ilearn.core.models.enhanced_profile import StudentFiveDimProfile
from ilearn.core.schemas import SessionState

_DEFAULT_TOTAL = 20
_DEFAULT_WEAK_RATIO = 0.7


def build_weak_first_knowledge_ids(
    session: SessionState,
    *,
    total: int = _DEFAULT_TOTAL,
    weak_ratio: float = _DEFAULT_WEAK_RATIO,
) -> list[str] | None:
    """Return ordered knowledge_id queue for blueprint (70% weak / 30% review).

    Returns ``None`` when enhanced profile path is inactive so callers keep
    legacy ``build_blueprint`` behaviour unchanged.
    """
    if not is_enhanced_enabled("ENABLE_ENHANCED_PROFILE"):
        return None

    profile = get_enhanced_profile(session)
    if profile is None:
        return None

    return knowledge_id_queue_from_profile(
        profile, total=total, weak_ratio=weak_ratio
    )


def knowledge_id_queue_from_profile(
    profile: StudentFiveDimProfile,
    *,
    total: int = _DEFAULT_TOTAL,
    weak_ratio: float = _DEFAULT_WEAK_RATIO,
) -> list[str]:
    """Build slot knowledge_id queue from weak/strong concept lists."""
    weak = list(profile.cognitive.weak_concepts)[:5]
    review = list(profile.cognitive.strong_concepts)[:3]

    if not weak and profile.cognitive.knowledge_mastery:
        ordered = sorted(
            profile.cognitive.knowledge_mastery.items(),
            key=lambda row: row[1],
        )
        weak = [kid for kid, _ in ordered[:5]]

    if not weak:
        weak = list(profile.cognitive.knowledge_mastery.keys())[:4] or ["basics"]

    if not review:
        ordered = sorted(
            profile.cognitive.knowledge_mastery.items(),
            key=lambda row: row[1],
            reverse=True,
        )
        review = [kid for kid, _ in ordered[:3] if kid not in weak]

    target_count = max(1, int(total * weak_ratio))
    review_count = max(1, total - target_count)
    if target_count + review_count > total:
        review_count = total - target_count

    queue: list[str] = []
    for index in range(target_count):
        queue.append(weak[index % len(weak)])
    review_source = review if review else weak
    for index in range(review_count):
        queue.append(review_source[index % len(review_source)])
    return queue
