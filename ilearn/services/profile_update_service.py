"""Background profile refresh for FastAPI BackgroundTasks (edition_0909 P2)."""

from __future__ import annotations

import logging
from ilearn.agents.enhanced.profile_updater import ProfileUpdaterAgent
from ilearn.agents.enhanced.recommend import RecommendAgent
from ilearn.core.datetime_utils import utc_now
from ilearn.core.enhanced_flags import is_enhanced_enabled
from ilearn.core.enhanced_session import get_enhanced_profile
from ilearn.providers.llm import LLMClient
from ilearn.storage.sessions import SessionStore

logger = logging.getLogger(__name__)

PROFILE_UPDATE_COOLDOWN_SECONDS = 300


def _cooldown_active(session_id: str, store: SessionStore) -> bool:
    try:
        session = store.load(session_id)
    except FileNotFoundError:
        return True
    profile = get_enhanced_profile(session)
    if profile is None or profile.last_updated is None:
        return False
    elapsed = (utc_now() - profile.last_updated).total_seconds()
    if elapsed < PROFILE_UPDATE_COOLDOWN_SECONDS:
        logger.debug(
            "skip background profile update for %s (cooldown %.0fs)",
            session_id,
            elapsed,
        )
        return True
    return False


def update_profile_background(
    store: SessionStore,
    session_id: str,
    llm: LLMClient | None = None,
    *,
    attach_recommendations: bool = False,
) -> None:
    """Reload session, refresh five-dim profile, optionally attach recommendations.

    Intended for ``BackgroundTasks.add_task`` — sync function. Pass the same
    ``SessionStore`` instance used by the API/orchestrator so in-process cache
    stays consistent after save.
    """
    if not (
        is_enhanced_enabled("ENABLE_ENHANCED_PROFILE")
        and is_enhanced_enabled("ENABLE_ENHANCED_AGENTS")
        and is_enhanced_enabled("ENABLE_ENHANCED_BACKGROUND")
    ):
        return

    if _cooldown_active(session_id, store):
        return

    stub_mode = llm is None or not getattr(llm, "available", lambda: False)()
    agent = ProfileUpdaterAgent(llm, stub_mode=stub_mode)
    try:
        session = store.load(session_id)
        session = agent.update_session(session)
        if attach_recommendations:
            profile = get_enhanced_profile(session)
            if profile is not None:
                recs = RecommendAgent(llm, stub_mode=stub_mode).recommend_from_profile(
                    profile
                )
                blob = session.metadata.get("enhanced")
                if isinstance(blob, dict):
                    blob = dict(blob)
                    blob["recommendations"] = recs
                    session.metadata["enhanced"] = blob
        store.save(session)
        logger.info("Background profile update succeeded for session %s", session_id)
    except FileNotFoundError:
        logger.warning(
            "Background profile update skipped; session not found: %s", session_id
        )
    except Exception:
        logger.exception(
            "Background profile update failed for session %s", session_id
        )
