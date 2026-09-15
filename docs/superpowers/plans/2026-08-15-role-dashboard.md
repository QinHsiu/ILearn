# Role Dashboard UI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add explicit parent/teacher relationships, dashboard APIs, and React role dashboards while preserving the existing student wizard.

**Architecture:** Store relationships in a small JSON-backed `RelationshipStore`; dashboard routes authorize access through that store and reuse `SessionMetadata`/`SessionState`. Add typed dashboard API methods and focused React pages/components without replacing `App.tsx`'s student flow.

**Tech Stack:** FastAPI, Pydantic v2, existing JSON stores, React 19, TypeScript, Vitest, Testing Library.

## Global Constraints

- Keep the student wizard and existing session endpoints unchanged.
- No authentication, invitations, tokens, or production identity management.
- Relationship data uses `data/relationships.json`.
- Empty valid relationships return `200 []`; mismatched detail access returns `404`.
- Do not modify `SessionState` or `DiagnosisReport`.
- Do not fabricate seven-day history; show current values when history is absent.
- Reuse `SessionStore.list_all_metadata()` and existing report/session data.

---

## File map

| File | Responsibility |
| --- | --- |
| `ilearn/storage/relationships.py` | Relationship persistence and idempotent bindings |
| `ilearn/api/dashboard.py` | Dashboard request/response models and routes |
| `ilearn/api/app.py` | Include dashboard router with app-local stores |
| `tests/test_relationships.py` | Store validation, isolation, idempotency |
| `tests/test_dashboard_api.py` | FastAPI binding/list/detail behavior |
| `frontend/src/api/client.ts` | Dashboard types and HTTP methods |
| `frontend/src/pages/DashboardHome.tsx` | Role selection and dashboard entry |
| `frontend/src/pages/ParentDashboard.tsx` | Parent child list/detail |
| `frontend/src/pages/TeacherDashboard.tsx` | Teacher class/student list/detail |
| `frontend/src/components/StudentList.tsx` | Shared student summary list |
| `frontend/src/components/DashboardDetail.tsx` | Shared detail panel |
| `frontend/src/dashboard.css` | Dashboard-only styles |
| `frontend/src/App.tsx` | Add dashboard mode while retaining student mode |
| `frontend/src/pages/*.test.tsx` | Dashboard rendering/API tests |

---

### Task 1: RelationshipStore

**Files:**
- Create: `ilearn/storage/relationships.py`
- Create: `tests/test_relationships.py`

**Interfaces:**
- `RelationshipStore(root: Path, sessions: SessionStore)`
- `bind_parent(parent_id: str, session_id: str) -> None`
- `bind_teacher(teacher_id: str, class_id: str, session_id: str) -> None`
- `children_for_parent(parent_id: str) -> list[str]`
- `classes_for_teacher(teacher_id: str) -> list[str]`
- `students_for_class(teacher_id: str, class_id: str) -> list[str]`

- [ ] **Step 1: Write failing tests**

```python
def test_parent_binding_is_idempotent_and_explicit(tmp_path):
    sessions = SessionStore(tmp_path / "sessions")
    session = sessions.create(StudentProfile(region="北京", grade=5, age=11))
    store = RelationshipStore(tmp_path / "relationships.json", sessions)
    store.bind_parent("p1", session.session_id)
    store.bind_parent("p1", session.session_id)
    assert store.children_for_parent("p1") == [session.session_id]
    assert store.children_for_parent("p2") == []

def test_teacher_binding_isolated_by_teacher_and_class(tmp_path):
    sessions = SessionStore(tmp_path / "sessions")
    a = sessions.create(StudentProfile(region="北京", grade=5, age=11))
    b = sessions.create(StudentProfile(region="北京", grade=5, age=11))
    store = RelationshipStore(tmp_path / "relationships.json", sessions)
    store.bind_teacher("t1", "c1", a.session_id)
    store.bind_teacher("t1", "c2", b.session_id)
    assert store.classes_for_teacher("t1") == ["c1", "c2"]
    assert store.students_for_class("t1", "c1") == [a.session_id]
    assert store.students_for_class("t2", "c1") == []

def test_binding_unknown_session_fails(tmp_path):
    store = RelationshipStore(
        tmp_path / "relationships.json",
        SessionStore(tmp_path / "sessions"),
    )
    with pytest.raises(FileNotFoundError):
        store.bind_parent("p1", "missing")
```

- [ ] **Step 2: Run the focused tests and confirm the missing module failure**

```bash
python -m pytest tests/test_relationships.py -v
```

- [ ] **Step 3: Implement JSON storage**

Use a JSON shape with explicit lists:

```json
{
  "parents": {"p1": ["session-id"]},
  "teachers": {"t1": {"class-a": ["session-id"]}}
}
```

Trim and reject empty IDs with `ValueError`; validate session existence before mutation; preserve insertion order and avoid duplicates; write UTF-8 JSON atomically through a temporary file in the same directory.

- [ ] **Step 4: Run tests**

```bash
python -m pytest tests/test_relationships.py -v
```

- [ ] **Step 5: Commit**

```bash
git add ilearn/storage/relationships.py tests/test_relationships.py
git commit -m "feat: add explicit parent and teacher relationships"
```

---

### Task 2: Dashboard FastAPI routes

**Files:**
- Create: `ilearn/api/dashboard.py`
- Modify: `ilearn/api/app.py`
- Create: `tests/test_dashboard_api.py`

**Interfaces:**
- `ParentBinding(parent_id: str, session_id: str)`
- `TeacherBinding(teacher_id: str, class_id: str, session_id: str)`
- Route responses use `SessionMetadata` for summaries and `SessionState` for detail.

- [ ] **Step 1: Write failing API tests**

Use `create_app(sessions_dir=tmp_path / "sessions", pilot_data_dir=...)`, create two sessions through the app's store/API, bind one to `p1` and `t1/c1`, then assert:

```python
assert client.get("/dashboard/parent/p1/children").status_code == 200
assert client.get("/dashboard/parent/p1/children").json()[0]["session_id"] == session_id
assert client.get(f"/dashboard/parent/p2/children").json() == []
assert client.get(f"/dashboard/parent/p1/child/{other_id}").status_code == 404
assert client.get("/dashboard/teacher/t1/classes").json()[0]["class_id"] == "c1"
assert client.get("/dashboard/teacher/t1/class/c1/students").status_code == 200
```

- [ ] **Step 2: Run tests to confirm missing route failures**

```bash
python -m pytest tests/test_dashboard_api.py -v
```

- [ ] **Step 3: Implement router and app wiring**

`dashboard.py` receives `SessionStore` and `RelationshipStore` through a router factory:

```python
def create_dashboard_router(
    sessions: SessionStore,
    relationships: RelationshipStore,
) -> APIRouter:
    ...
```

The parent list resolves relationship IDs then calls `list_all_metadata()` and indexes by session ID. Teacher class list aggregates only bound sessions. Detail routes check membership before `load`; otherwise raise `HTTPException(404, ...)`. `create_app` creates `RelationshipStore(_PROJECT_ROOT / "data" / "relationships.json", store)` and includes the router.

- [ ] **Step 4: Run API tests and existing backend tests**

```bash
python -m pytest tests/test_dashboard_api.py tests/test_api.py tests/test_session_store.py -v
```

- [ ] **Step 5: Commit**

```bash
git add ilearn/api/dashboard.py ilearn/api/app.py tests/test_dashboard_api.py
git commit -m "feat: add parent and teacher dashboard APIs"
```

---

### Task 3: Typed frontend dashboard client

**Files:**
- Modify: `frontend/src/api/client.ts`
- Create/update: `frontend/src/api/client.test.ts`

**Interfaces:**
- `DashboardStudentSummary`
- `DashboardClassSummary`
- `DashboardStudentDetail`
- `dashboardApi.bindParent`, `bindTeacher`, `parentChildren`, `parentChild`, `teacherClasses`, `teacherStudents`, `teacherStudent`

- [ ] **Step 1: Add client tests with mocked fetch**

Assert `parentChildren("p1")` requests `/dashboard/parent/p1/children`, and `bindTeacher` sends the exact JSON body `{teacher_id, class_id, session_id}`.

- [ ] **Step 2: Implement types and methods**

Use the existing `request<T>` helper. Keep dashboard methods separate from the existing `api` object to avoid changing student call sites.

- [ ] **Step 3: Run frontend tests and typecheck**

```bash
cd frontend
npm test -- --run
npm run build
```

- [ ] **Step 4: Commit**

```bash
git add frontend/src/api/client.ts frontend/src/api/client.test.ts
git commit -m "feat: add typed dashboard API client"
```

---

### Task 4: Parent and teacher dashboard views

**Files:**
- Create: `frontend/src/pages/DashboardHome.tsx`
- Create: `frontend/src/pages/ParentDashboard.tsx`
- Create: `frontend/src/pages/TeacherDashboard.tsx`
- Create: `frontend/src/components/StudentList.tsx`
- Create: `frontend/src/components/DashboardDetail.tsx`
- Create: `frontend/src/dashboard.css`
- Modify: `frontend/src/App.tsx`
- Create: dashboard component tests

**Interfaces:**
- Dashboard mode is selected by `?role=parent&user=p1` or `?role=teacher&user=t1`.
- Student mode remains the default when no role query exists.
- Teacher class selection uses `?class_id=...`; selected student uses `?student_id=...`.

- [ ] **Step 1: Write rendering tests**

Mock `dashboardApi` and assert:

```tsx
render(<App />)
expect(screen.getByText('家长端')).toBeInTheDocument()
expect(screen.getByText('老师端')).toBeInTheDocument()
```

For each role, assert loading, empty state, list, and detail rendering.

- [ ] **Step 2: Implement shared list/detail components**

Render nickname, grade, mastery percentage, weak skills, and phase. Detail renders skill mastery and existing report fields; omit a trend chart when no historical values exist.

- [ ] **Step 3: Implement role pages and entry**

Read `window.location.search`; default to existing student JSX. Parent page loads children, then child detail after selection. Teacher page loads classes, students after class selection, then detail after selection. Bind forms call the dashboard client and refresh the list.

- [ ] **Step 4: Run frontend tests/build**

```bash
cd frontend
npm test -- --run
npm run build
```

- [ ] **Step 5: Commit**

```bash
git add frontend/src/App.tsx frontend/src/pages frontend/src/components/StudentList.tsx frontend/src/components/DashboardDetail.tsx frontend/src/dashboard.css
git commit -m "feat: add parent and teacher dashboard views"
```

---

### Task 5: Full verification

- [ ] **Step 1: Run backend suite**

```bash
python -m pytest -q
```

- [ ] **Step 2: Run frontend suite**

```bash
cd frontend
npm test -- --run
npm run build
```

- [ ] **Step 3: Confirm scope**

Only relationship storage, dashboard API, dashboard client/components, and tests changed. Student session endpoints and schema definitions remain compatible.

## Self-review

- Spec coverage: relationship storage Task 1; API Task 2; frontend client Task 3; parent/teacher views Task 4; testing/error/scope Task 5.
- No placeholders or undefined cross-task signatures.
- The plan deliberately avoids the reference's nickname inference and synthetic trend generation.
