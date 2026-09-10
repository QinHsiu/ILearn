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


def _ensure_metadata(session: SessionState) -> None:
    """Defensive: SessionState always has metadata; keep for non-Pydantic callers."""
    if not hasattr(session, "metadata") or session.metadata is None:
        session.metadata = {}


def set_enhanced_profile(
    session: SessionState,
    profile: StudentFiveDimProfile,
) -> SessionState:
    """Persist five-dim profile under metadata.enhanced when PROFILE flag is on.

    When ``ENABLE_ENHANCED_PROFILE`` is false, returns ``session`` unchanged
    (no ``enhanced`` key written).

    Merges into the existing ``enhanced`` blob so sibling keys (``kt``,
    ``recommendations``, etc.) are preserved.
    """
    if not is_enhanced_enabled("ENABLE_ENHANCED_PROFILE"):
        return session
    _ensure_metadata(session)
    blob = session.metadata.get("enhanced")
    if not isinstance(blob, dict):
        blob = {}
    else:
        blob = dict(blob)
    blob["schema_version"] = blob.get("schema_version", ENHANCED_SCHEMA_VERSION)
    blob["profile"] = profile.model_dump(mode="json")
    session.metadata["enhanced"] = blob
    return session


def get_kt_state(session: SessionState) -> dict[str, Any] | None:
    """Return KT state from ``metadata.enhanced.kt``, or ``None`` if absent."""
    blob = get_enhanced_blob(session)
    if not blob:
        return None
    kt = blob.get("kt")
    if isinstance(kt, dict):
        return kt
    return None


def set_kt_state(session: SessionState, kt_state: dict[str, Any]) -> SessionState:
    """Persist KT state under metadata.enhanced when PROFILE flag is on.

    Merges into the existing ``enhanced`` blob so sibling keys (``profile``,
    ``recommendations``, etc.) are preserved.
    """
    if not is_enhanced_enabled("ENABLE_ENHANCED_PROFILE"):
        return session
    _ensure_metadata(session)
    blob = session.metadata.get("enhanced")
    if not isinstance(blob, dict):
        blob = {}
    else:
        blob = dict(blob)
    blob["schema_version"] = blob.get("schema_version", ENHANCED_SCHEMA_VERSION)
    blob["kt"] = kt_state
    session.metadata["enhanced"] = blob
    return session
