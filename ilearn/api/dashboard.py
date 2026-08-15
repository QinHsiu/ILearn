"""Parent and teacher dashboard endpoints."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ilearn.core.schemas import SessionMetadata, SessionState
from ilearn.storage.relationships import RelationshipStore
from ilearn.storage.sessions import SessionStore


class ParentBinding(BaseModel):
    parent_id: str
    session_id: str


class TeacherBinding(BaseModel):
    teacher_id: str
    class_id: str
    session_id: str


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

    @router.post("/parent/bind", status_code=204)
    def bind_parent(binding: ParentBinding) -> None:
        relationships.bind_parent(binding.parent_id, binding.session_id)

    @router.post("/teacher/bind", status_code=204)
    def bind_teacher(binding: TeacherBinding) -> None:
        relationships.bind_teacher(
            binding.teacher_id, binding.class_id, binding.session_id
        )

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

    @router.get(
        "/parent/{parent_id}/child/{session_id}",
        response_model=SessionState,
    )
    def parent_child(parent_id: str, session_id: str) -> SessionState:
        if session_id not in relationships.children_for_parent(parent_id):
            raise HTTPException(status_code=404, detail="child not found")
        return sessions.load(session_id)

    @router.get(
        "/teacher/{teacher_id}/classes",
        response_model=list[TeacherClass],
    )
    def teacher_classes(teacher_id: str) -> list[TeacherClass]:
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
        return result

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

    @router.get(
        "/teacher/{teacher_id}/class/{class_id}/student/{session_id}",
        response_model=SessionState,
    )
    def teacher_student(
        teacher_id: str, class_id: str, session_id: str
    ) -> SessionState:
        if session_id not in relationships.students_for_class(teacher_id, class_id):
            raise HTTPException(status_code=404, detail="student not found")
        return sessions.load(session_id)

    @router.get(
        "/teacher/{teacher_id}/student/{session_id}",
        response_model=SessionState,
    )
    def teacher_student_any_class(
        teacher_id: str, session_id: str
    ) -> SessionState:
        for class_id in relationships.classes_for_teacher(teacher_id):
            if session_id in relationships.students_for_class(teacher_id, class_id):
                return sessions.load(session_id)
        raise HTTPException(status_code=404, detail="student not found")

    return router
