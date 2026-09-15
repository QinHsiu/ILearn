"""Parent and teacher dashboard endpoints."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ilearn.core.enhanced_api import (
    build_enhanced_overlay,
    enhanced_api_active,
)
from ilearn.core.schemas import SessionMetadata, SessionState
from ilearn.storage.relationships import RelationshipStore
from ilearn.storage.sessions import SessionStore


class ParentBinding(BaseModel):
    parent_id: str
    session_id: str


class ParentBindByCode(BaseModel):
    parent_id: str
    code: str


class TeacherBinding(BaseModel):
    teacher_id: str
    class_id: str
    session_id: str


class TeacherBindByCode(BaseModel):
    teacher_id: str
    class_id: str
    code: str


class TeacherClass(BaseModel):
    class_id: str
    students: list[SessionMetadata]


def create_dashboard_router(
    sessions: SessionStore,
    relationships: RelationshipStore,
) -> APIRouter:
    router = APIRouter(prefix="/dashboard")

    def metadata_index() -> dict[str, SessionMetadata]:
        return {
            metadata.session_id: metadata
            for metadata in sessions.list_all_metadata()
        }

    def _load_or_404(session_id: str) -> SessionState:
        try:
            return sessions.load(session_id)
        except FileNotFoundError:
            relationships.reconcile()
            raise HTTPException(
                status_code=404,
                detail="学习会话不存在或已过期，请重新绑定或创建新会话",
            ) from None

    def _session_payload(session: SessionState, *, enhanced: bool) -> Any:
        if not enhanced_api_active(enhanced):
            return session
        payload = {"session": session.model_dump(mode="json")}
        payload.update(build_enhanced_overlay(session))
        return payload

    @router.post("/parent/bind", status_code=204)
    def bind_parent(binding: ParentBinding) -> None:
        relationships.bind_parent(binding.parent_id, binding.session_id)

    @router.post("/parent/bind-by-code", status_code=204)
    def bind_parent_by_code(body: ParentBindByCode) -> None:
        from ilearn.core.invite import resolve_invite_code

        session_id = resolve_invite_code(sessions, body.code)
        if not session_id:
            raise HTTPException(status_code=404, detail="绑定码无效或已过期")
        relationships.bind_parent(body.parent_id, session_id)

    @router.post("/teacher/bind", status_code=204)
    def bind_teacher(binding: TeacherBinding) -> None:
        relationships.bind_teacher(
            binding.teacher_id, binding.class_id, binding.session_id
        )

    @router.post("/teacher/bind-by-code", status_code=204)
    def bind_teacher_by_code(body: TeacherBindByCode) -> None:
        from ilearn.core.invite import resolve_invite_code

        session_id = resolve_invite_code(sessions, body.code)
        if not session_id:
            raise HTTPException(status_code=404, detail="绑定码无效或已过期")
        relationships.bind_teacher(body.teacher_id, body.class_id, session_id)

    @router.get(
        "/parent/{parent_id}/children",
        response_model=list[SessionMetadata],
    )
    def parent_children(parent_id: str) -> list[SessionMetadata]:
        session_ids = relationships.children_for_parent(parent_id)
        if not session_ids:
            return []
        index = metadata_index()
        return [
            index[session_id]
            for session_id in session_ids
            if session_id in index
        ]

    @router.get("/parent/{parent_id}/child/{session_id}")
    def parent_child(
        parent_id: str, session_id: str, enhanced: bool = False
    ) -> Any:
        if session_id not in relationships.children_for_parent(parent_id):
            raise HTTPException(status_code=404, detail="child not found")
        return _session_payload(_load_or_404(session_id), enhanced=enhanced)

    @router.get(
        "/teacher/{teacher_id}/classes",
    )
    def teacher_classes(teacher_id: str, enhanced: bool = False) -> Any:
        index = metadata_index()
        result: list[TeacherClass] = []
        for class_id in relationships.classes_for_teacher(teacher_id):
            students = [
                index[session_id]
                for session_id in relationships.students_for_class(
                    teacher_id, class_id
                )
                if session_id in index
            ]
            result.append(TeacherClass(class_id=class_id, students=students))
        if not enhanced_api_active(enhanced):
            return result
        overview_rows: list[dict[str, Any]] = []
        for row in result:
            for student in row.students:
                try:
                    session = sessions.load(student.session_id)
                except FileNotFoundError:
                    continue
                overview_rows.append(
                    {
                        "session_id": student.session_id,
                        "class_id": row.class_id,
                        "nickname": student.nickname,
                        **build_enhanced_overlay(session),
                    }
                )
        return {
            "classes": [item.model_dump(mode="json") for item in result],
            "enhanced": True,
            "overview": overview_rows,
        }

    @router.get(
        "/teacher/{teacher_id}/class/{class_id}/students",
        response_model=list[SessionMetadata],
    )
    def teacher_students(
        teacher_id: str, class_id: str
    ) -> list[SessionMetadata]:
        index = metadata_index()
        return [
            index[session_id]
            for session_id in relationships.students_for_class(
                teacher_id, class_id
            )
            if session_id in index
        ]

    @router.get("/teacher/{teacher_id}/class/{class_id}/student/{session_id}")
    def teacher_student(
        teacher_id: str,
        class_id: str,
        session_id: str,
        enhanced: bool = False,
    ) -> Any:
        if session_id not in relationships.students_for_class(teacher_id, class_id):
            raise HTTPException(status_code=404, detail="student not found")
        return _session_payload(_load_or_404(session_id), enhanced=enhanced)

    @router.get("/teacher/{teacher_id}/class/{class_id}/assignment-timeline")
    def teacher_class_assignment_timeline(
        teacher_id: str, class_id: str, limit: int = 30
    ) -> dict:
        from ilearn.core.class_receipts import aggregate_class_assignment_timeline

        return aggregate_class_assignment_timeline(
            sessions=sessions,
            relationships=relationships,
            teacher_id=teacher_id,
            class_id=class_id,
            limit=limit,
        )

    class BatchAssignBody(BaseModel):
        session_ids: list[str] | None = None
        topic: str | None = None

    @router.post("/teacher/{teacher_id}/class/{class_id}/tiers/assign-batch")
    def teacher_class_assign_batch(
        teacher_id: str, class_id: str, body: BatchAssignBody | None = None
    ) -> dict:
        from ilearn.core.class_receipts import batch_assign_class_tiers

        payload = body or BatchAssignBody()
        return batch_assign_class_tiers(
            sessions=sessions,
            relationships=relationships,
            teacher_id=teacher_id,
            class_id=class_id,
            session_ids=payload.session_ids,
            topic=payload.topic,
        )

    @router.get("/teacher/{teacher_id}/student/{session_id}")
    def teacher_student_any_class(
        teacher_id: str, session_id: str, enhanced: bool = False
    ) -> Any:
        for class_id in relationships.classes_for_teacher(teacher_id):
            if session_id in relationships.students_for_class(teacher_id, class_id):
                return _session_payload(
                    _load_or_404(session_id), enhanced=enhanced
                )
        raise HTTPException(status_code=404, detail="student not found")

    return router
