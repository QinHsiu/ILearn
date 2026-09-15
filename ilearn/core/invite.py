"""Short invite codes for parent/teacher bind (no raw UUID paste)."""

from __future__ import annotations

import secrets
import string

from ilearn.core.schemas import SessionState
from ilearn.storage.sessions import SessionStore

_ALPHABET = string.ascii_uppercase + string.digits


def make_invite_code(*, length: int = 6) -> str:
    return "".join(secrets.choice(_ALPHABET) for _ in range(length))


def ensure_session_invite(session: SessionState, store: SessionStore) -> str:
    meta = dict(session.metadata or {})
    code = str(meta.get("invite_code") or "").strip().upper()
    if len(code) >= 4:
        return code
    code = make_invite_code()
    # Avoid trivial collision with another open session (best-effort)
    existing = {c for c in _all_invite_codes(store) if c != code}
    while code in existing:
        code = make_invite_code()
    meta["invite_code"] = code
    session.metadata = meta
    store.save(session)
    return code


def _all_invite_codes(store: SessionStore) -> set[str]:
    codes: set[str] = set()
    for meta in store.list_all_metadata():
        try:
            session = store.load(meta.session_id)
        except FileNotFoundError:
            continue
        raw = (session.metadata or {}).get("invite_code")
        if raw:
            codes.add(str(raw).strip().upper())
    return codes


def resolve_invite_code(store: SessionStore, code: str) -> str | None:
    needle = (code or "").strip().upper()
    if len(needle) < 4:
        return None
    for meta in store.list_all_metadata():
        try:
            session = store.load(meta.session_id)
        except FileNotFoundError:
            continue
        raw = (session.metadata or {}).get("invite_code")
        if raw and str(raw).strip().upper() == needle:
            return session.session_id
        # Fallback: trailing session id fragment
        if meta.session_id[-6:].upper() == needle:
            return meta.session_id
    return None
