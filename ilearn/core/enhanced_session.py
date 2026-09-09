"""Read/write ``SessionState.metadata['enhanced']`` for five-dim profiles."""

from __future__ import annotations

from typing import Any

from ilearn.core.enhanced_flags import is_enhanced_enabled
from ilearn.core.models.enhanced_profile import StudentFiveDimProfile
from ilearn.core.schemas import SessionState

ENHANCED_SCHEMA_VERSION = 1


def get_enhanced_blob(session: SessionState) -> dict[str, Any] | None:
    raw = session.metadata.get("enhanced")
    if isinstance(raw, dict):
        return raw
    return None


def get_enhanced_profile(session: SessionState) -> StudentFiveDimProfile | None:
    blob = get_enhanced_blob(session)
    if not blob:
        return None
    profile_data = blob.get("profile")
    if not isinstance(profile_data, dict):
        return None
    return StudentFiveDimProfile.model_validate(profile_data)


def set_enhanced_profile(
    session: SessionState,
    profile: StudentFiveDimProfile,
) -> SessionState:
    """Persist five-dim profile under metadata.enhanced when PROFILE flag is on.

    When ``ENABLE_ENHANCED_PROFILE`` is false, returns ``session`` unchanged
    (no ``enhanced`` key written).
    """
    if not is_enhanced_enabled("ENABLE_ENHANCED_PROFILE"):
        return session
    session.metadata["enhanced"] = {
        "schema_version": ENHANCED_SCHEMA_VERSION,
        "profile": profile.model_dump(mode="json"),
    }
    return session
