# Role dashboard UI and relationships

**Date:** 2026-08-15  
**Status:** Approved for planning  
**Reference:** `doc/deepseek_edition/0815_e2/UI/`

## Context

ILearn currently has a React student wizard and a FastAPI session API. The reference UI adds parent and teacher dashboards, but its association logic is only simulated. This slice adds explicit lightweight relationships and dashboard views while preserving the student flow.

## Goals

- Add explicit parent-to-session and teacher-to-class-to-session relationships.
- Add dashboard APIs for parent and teacher list/detail views.
- Add React dashboard views that reuse the existing client, theme, and session metadata.
- Keep the student wizard and existing session APIs unchanged.

## Non-goals

- Authentication, authorization tokens, invitations, or production identity management.
- Database migration; relationships use the existing JSON persistence style.
- Rewriting diagnosis, report, or session projection logic.
- Fabricating historical trend points. If no history exists, show current data without a synthetic seven-day chart.

## Architecture

### Relationship storage

Create `ilearn/storage/relationships.py` with `RelationshipStore`, backed by `data/relationships.json`.

The store exposes:

- `bind_parent(parent_id, session_id)`
- `bind_teacher(teacher_id, class_id, session_id)`
- `children_for_parent(parent_id)`
- `classes_for_teacher(teacher_id)`
- `students_for_class(teacher_id, class_id)`

Identifiers must be non-empty after trimming. Bind operations are idempotent. The store validates that referenced session IDs exist through the session store. It never deletes sessions when a relationship is removed or replaced.

### Dashboard API

Create `ilearn/api/dashboard.py` and include its router from `create_app`.

Endpoints:

- `POST /dashboard/relationships/parent`
- `POST /dashboard/relationships/teacher`
- `GET /dashboard/parent/{parent_id}/children`
- `GET /dashboard/parent/{parent_id}/child/{session_id}`
- `GET /dashboard/teacher/{teacher_id}/classes`
- `GET /dashboard/teacher/{teacher_id}/class/{class_id}/students`
- `GET /dashboard/teacher/{teacher_id}/student/{session_id}`

Dashboard endpoints must filter through `RelationshipStore` before loading session metadata/details. A session not related to the requested parent/teacher returns 404. Empty valid relationships return an empty list.

Dashboard detail responses reuse `SessionMetadata` and existing `SessionState`/report data. No duplicate mastery or diagnosis calculations are introduced.

### Frontend

Keep `frontend/src/App.tsx` as the student entry point and add role dashboard components/pages:

- `DashboardHome`
- `ParentDashboard`
- `TeacherDashboard`
- `StudentList`
- `DashboardDetail`

Extend `frontend/src/api/client.ts` with dashboard types and API methods. Add a small role entry selector or URL-based dashboard entry without introducing authentication. Parent views show children and a selected child detail. Teacher views show classes, students, and a selected student detail. Trend visualization uses real available values only.

## Data flow

```text
relationship bind request
        ↓
RelationshipStore → data/relationships.json
        ↓
dashboard query → relationship authorization check
        ↓
SessionStore.list_all_metadata / load
        ↓
React parent/teacher dashboard
```

## Error handling

- Empty identifiers: 400.
- Unknown session IDs during binding: 404.
- Valid user with no relationships: 200 with `[]`.
- Relationship mismatch on detail/list: 404.
- Malformed relationship JSON: follow existing JSON-store behavior and return a controlled server error; do not silently expose all sessions.

## Testing

- Relationship store tests for bind, idempotency, explicit separation, and unknown sessions.
- FastAPI tests for parent/teacher binding, list/detail authorization, empty results, and 404 mismatch.
- Frontend tests for dashboard API calls and basic parent/teacher rendering.
- Full existing Python and frontend suites remain green.

## Scope boundary

The slice may add the minimum Pydantic request/response models and route registration needed for these endpoints. It must not modify `SessionState`, `DiagnosisReport`, or student session endpoint semantics.
