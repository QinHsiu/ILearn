"""One-click demo teaching-unit session API."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from ilearn.demo.seed import seed_demo_session
from ilearn.demo.units import load_demo_unit
from ilearn.storage.relationships import RelationshipStore
from ilearn.storage.sessions import SessionStore

_DEMO_PARENT = "demo_parent"
_DEMO_TEACHER = "demo_teacher"
_DEMO_CLASS = "demo_class_5a"


def create_demo_session(
    unit_id: str,
    store: SessionStore,
    relationships: RelationshipStore,
) -> dict:
    """Seed, persist, and bind a demo unit session; return ids and role links."""
    unit = load_demo_unit(unit_id)
    session = seed_demo_session(unit)
    store.save(session)
    sid = session.session_id
    relationships.bind_parent(_DEMO_PARENT, sid)
    relationships.bind_teacher(_DEMO_TEACHER, _DEMO_CLASS, sid)
    return {
        "session_id": sid,
        "unit_name": unit.get("name") or unit_id,
        "links": {
            "student": f"?student=1&session_id={sid}",
            "teacher": (
                f"?login=1&role=teacher&user={_DEMO_TEACHER}"
                f"&class_id={_DEMO_CLASS}&student_id={sid}"
            ),
            "parent": (
                f"?login=1&role=parent&user={_DEMO_PARENT}&student_id={sid}"
            ),
        },
    }


def create_demo_router(
    store: SessionStore,
    relationships: RelationshipStore,
) -> APIRouter:
    router = APIRouter(prefix="/demo", tags=["demo"])

    @router.post("/units/{unit_id}/session")
    def post_demo_session(unit_id: str) -> dict:
        try:
            return create_demo_session(unit_id, store, relationships)
        except FileNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    return router
