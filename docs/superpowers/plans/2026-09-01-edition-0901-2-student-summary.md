# Edition 0901_2 StudentSummary Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship structured `StudentSummary` (seed-preferred + formula fallback), `GET /sessions/{id}/summary/student`, and a plan-step panel for demo student deep links — without a dedicated Student Dashboard page.

**Architecture:** Extend `audience_summary.py` like teacher/parent builders; demo seed writes `metadata.student_summary`; FastAPI GET returns `model_dump()`; StudentApp step 3 mounts `StudentSummaryPanel` above plan markdown.

**Tech Stack:** Python 3.11+, FastAPI, Pydantic, pytest; React 19 + Vitest; existing SessionStore / demo seed patterns.

## Global Constraints

- Scope **A only** per `docs/superpowers/specs/2026-09-01-edition-0901-2-student-summary-design.md`.
- Approach **方案 1**: extend existing modules; no dedicated student dashboard; no react-router.
- Seed preference **C**: `metadata.student_summary` keys overlay fallbacks; missing keys filled by formula.
- Demo seeded values (lock): `current_task="巩固：小数乘小数"`, `completed_tasks=2`, `total_tasks=5`, `stars_earned=5`, `next_challenge="挑战：运算律推广到小数"`, plus Chinese `narrative`.
- Sync APIs only; do **not** commit `doc/` or `docs/`; update `VERSION.md` only.
- TDD per task; keep offline pytest + vitest green.
- Out of scope: parent 留言/预约, class PDF, StudentDashboard page.

## File Structure

| Path | Responsibility |
| --- | --- |
| `ilearn/core/audience_summary.py` | `StudentSummary` + `build_student_summary` |
| `ilearn/demo/seed.py` | Write `metadata.student_summary` |
| `ilearn/api/app.py` | GET summary/student |
| `tests/test_student_summary.py` | Builder + seed preference tests |
| `tests/test_summary_api.py` | Extend with student endpoint |
| `frontend/src/api/client.ts` | Types + `getStudentSummary` |
| `frontend/src/components/StudentSummaryPanel.tsx` | Plan-step UI |
| `frontend/src/App.tsx` | Mount panel on step 3 |
| `VERSION.md` | Edition 0901_2 |

---

### Task 1: StudentSummary model + builder (TDD)

**Files:**
- Modify: `ilearn/core/audience_summary.py`
- Create: `tests/test_student_summary.py`

**Interfaces:**
- Consumes: `SessionState`
- Produces:

```python
class StudentSummary(BaseModel):
    current_task: str
    completed_tasks: int
    total_tasks: int
    stars_earned: int
    next_challenge: str
    narrative: str

def build_student_summary(session: SessionState) -> StudentSummary: ...
```

**Fallback rules (lock):**
- `total_tasks = max(len(plan.days), 1)` if plan and days else `max(len(paper.items) if paper else 0, 1)`
- `completed_tasks = min(len(answers), total_tasks)`
- `current_task = plan.goal` if truthy else first day `title`/`focus`/`theme` (whichever exists on `PlanDay`) else `"完成今日练习"`
- `stars_earned = int(metadata.demo_weaknesses_resolved or 0) * 2 + (1 if paper and len(answers) >= len(paper.items) else 0)`
- `next_challenge`: first diagnosis mastery row with `level == "weak"` → `knowledge_name or knowledge_id`; else `"挑战下一关练习"`
- `narrative = f"已完成 {completed}/{total} 个任务，继续加油！"`
- Overlay: `raw = session.metadata.get("student_summary")`; if dict, for each model field if key present and not None, override computed value; then `StudentSummary(**merged)`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_student_summary.py
from ilearn.core.audience_summary import build_student_summary, StudentSummary
from ilearn.core.schemas import (
    SessionState, StudentProfile, SessionPhase, LearningPlanReport, PlanDay,
)
from ilearn.demo.seed import seed_demo_session
from ilearn.demo.units import load_demo_unit


def test_build_student_summary_uses_metadata_when_present():
    session = seed_demo_session(load_demo_unit("math_5_1"))
    # After Task 2 seed will set this; for Task 1 inject manually:
    session.metadata["student_summary"] = {
        "current_task": "巩固：小数乘小数",
        "completed_tasks": 2,
        "total_tasks": 5,
        "stars_earned": 5,
        "next_challenge": "挑战：运算律推广到小数",
        "narrative": "今天又进步啦，继续加油！",
    }
    s = build_student_summary(session)
    assert isinstance(s, StudentSummary)
    assert s.current_task == "巩固：小数乘小数"
    assert s.completed_tasks == 2
    assert s.total_tasks == 5
    assert s.stars_earned == 5
    assert s.next_challenge.startswith("挑战")
    assert s.narrative


def test_build_student_summary_formula_without_metadata():
    session = SessionState(
        session_id="plain-s",
        profile=StudentProfile(region="beijing", grade=5, age=11, nickname="小华"),
        phase=SessionPhase.PLAN,
        plan=LearningPlanReport(
            status="ready",
            goal="巩固小数乘法",
            days=[PlanDay(day=1, title="练习小数乘整数", focus="kp_a")],
            markdown="x",
        ),
        answers={},
        metadata={"demo_weaknesses_resolved": 1},
    )
    s = build_student_summary(session)
    assert s.current_task == "巩固小数乘法"
    assert s.total_tasks == 1
    assert s.completed_tasks == 0
    assert s.stars_earned == 2  # 1*2 + 0
    assert "任务" in s.narrative
```

Inspect `PlanDay` fields in `ilearn/core/schemas.py` and adjust the fixture constructor to match real required fields (do not invent fields).

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_student_summary.py -v`

Expected: FAIL — import / symbol missing

- [ ] **Step 3: Implement model + builder**

Add to `audience_summary.py` following teacher/parent style. Keep existing helpers intact.

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_student_summary.py -v`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add ilearn/core/audience_summary.py tests/test_student_summary.py
git commit -m "feat: add StudentSummary builder with seed overlay"
```

---

### Task 2: Seed `metadata.student_summary` for math_5_1

**Files:**
- Modify: `ilearn/demo/seed.py` (metadata dict)
- Modify: `tests/test_student_summary.py` (assert seed without manual inject)

**Interfaces:**
- Produces: seeded session always has `metadata["student_summary"]` dict with locked demo values

- [ ] **Step 1: Write failing assertion**

```python
def test_demo_seed_includes_student_summary():
    session = seed_demo_session(load_demo_unit("math_5_1"))
    raw = session.metadata.get("student_summary")
    assert isinstance(raw, dict)
    s = build_student_summary(session)
    assert s.completed_tasks == 2 and s.total_tasks == 5 and s.stars_earned == 5
```

- [ ] **Step 2: Run to verify fail**

Run: `pytest tests/test_student_summary.py::test_demo_seed_includes_student_summary -v`

Expected: FAIL — key missing

- [ ] **Step 3: Add to seed metadata**

```python
"student_summary": {
    "current_task": "巩固：小数乘小数",
    "completed_tasks": 2,
    "total_tasks": 5,
    "stars_earned": 5,
    "next_challenge": "挑战：运算律推广到小数",
    "narrative": "今天又进步啦，继续加油！",
},
```

- [ ] **Step 4: Run tests**

Run: `pytest tests/test_student_summary.py -v`

Expected: PASS (can simplify Task 1 inject test to rely on seed, or keep both)

- [ ] **Step 5: Commit**

```bash
git add ilearn/demo/seed.py tests/test_student_summary.py
git commit -m "feat(demo): seed student_summary metadata for math_5_1"
```

---

### Task 3: GET `/sessions/{id}/summary/student`

**Files:**
- Modify: `ilearn/api/app.py` (import + route next to parent/teacher)
- Modify: `tests/test_summary_api.py`

**Interfaces:**
- Produces: `GET /sessions/{session_id}/summary/student` → `build_student_summary(session).model_dump()`

- [ ] **Step 1: Write failing API tests**

```python
def test_summary_student(tmp_path: Path):
    client = _client(tmp_path)
    sid = client.post("/demo/units/math_5_1/session").json()["session_id"]
    r = client.get(f"/sessions/{sid}/summary/student")
    assert r.status_code == 200
    body = r.json()
    assert body["total_tasks"] == 5
    assert body["stars_earned"] == 5
    assert "current_task" in body


def test_summary_student_missing_404(tmp_path: Path):
    assert _client(tmp_path).get("/sessions/missing/summary/student").status_code == 404
```

(Reuse existing `_client` helper in the file.)

- [ ] **Step 2: Run to verify fail**

Run: `pytest tests/test_summary_api.py::test_summary_student -v`

Expected: FAIL — 404 route missing

- [ ] **Step 3: Wire route**

```python
from ilearn.core.audience_summary import (
    build_parent_summary,
    build_student_summary,
    build_teacher_summary,
)

@app.get("/sessions/{session_id}/summary/student")
def get_student_summary(session_id: str) -> dict:
    session = store.load(session_id)
    return build_student_summary(session).model_dump()
```

- [ ] **Step 4: Run tests**

Run: `pytest tests/test_summary_api.py tests/test_student_summary.py -v`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add ilearn/api/app.py tests/test_summary_api.py
git commit -m "feat(api): expose student structured summary"
```

---

### Task 4: Frontend client types + method

**Files:**
- Modify: `frontend/src/api/client.ts`
- Modify: `frontend/src/api/client.test.ts`

**Interfaces:**

```typescript
export type StudentSummary = {
  current_task: string
  completed_tasks: number
  total_tasks: number
  stars_earned: number
  next_challenge: string
  narrative: string
}
// api.getStudentSummary(sessionId): Promise<StudentSummary>
```

- [ ] **Step 1: Write failing client test** mirroring `getParentSummary` pattern — assert URL contains `/sessions/s1/summary/student`

- [ ] **Step 2: Run** `cd frontend; npx vitest run src/api/client.test.ts` — expect fail

- [ ] **Step 3: Add type + `getStudentSummary` next to other summary methods**

- [ ] **Step 4: Run vitest — expect pass**

- [ ] **Step 5: Commit**

```bash
git add frontend/src/api/client.ts frontend/src/api/client.test.ts
git commit -m "feat(frontend): client getStudentSummary"
```

---

### Task 5: StudentSummaryPanel + wire App step 3

**Files:**
- Create: `frontend/src/components/StudentSummaryPanel.tsx`
- Create: `frontend/src/components/StudentSummaryPanel.test.tsx`
- Modify: `frontend/src/App.tsx` (step === 3 block)

**Interfaces:**
- Props: `{ sessionId: string }`
- Fetches `api.getStudentSummary(sessionId)` on mount / id change; shows loading / error / cards for task progress, stars, next challenge, narrative
- App: inside `{step === 3 && session && (` panel, **above** plan markdown / scientific_plan, render `<StudentSummaryPanel sessionId={sessionId!} />` only when `sessionId` truthy

- [ ] **Step 1: Write failing panel test**

```tsx
vi.mock('../api/client', ...)
it('renders task progress and stars', async () => {
  vi.mocked(api.getStudentSummary).mockResolvedValue({
    current_task: '巩固：小数乘小数',
    completed_tasks: 2,
    total_tasks: 5,
    stars_earned: 5,
    next_challenge: '挑战：运算律推广到小数',
    narrative: '今天又进步啦，继续加油！',
  })
  render(<StudentSummaryPanel sessionId="s1" />)
  expect(await screen.findByText(/巩固：小数乘小数/)).toBeInTheDocument()
  expect(screen.getByText(/2\s*\/\s*5|2\/5/)).toBeInTheDocument()
  expect(screen.getByText(/5/)).toBeTruthy() // stars — prefer aria-label="获得星星"
})
```

Prefer stable `aria-label`s: `学生任务摘要`, `获得星星`.

- [ ] **Step 2: Run panel test — expect fail**

- [ ] **Step 3: Implement panel + mount in App.tsx step 3**

Reuse existing `summary-grid` / `summary-block` / `panel` classes where possible. No new design system.

- [ ] **Step 4: Run** `npx vitest run src/components/StudentSummaryPanel.test.tsx` (+ smoke existing `App.studentResume.test.tsx` if present)

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/StudentSummaryPanel.tsx frontend/src/components/StudentSummaryPanel.test.tsx frontend/src/App.tsx
git commit -m "feat(student): show StudentSummaryPanel on plan step"
```

---

### Task 6: VERSION.md + suite gate

**Files:**
- Modify: `VERSION.md`

- [ ] **Step 1: Update header to Edition 0901_2; add 本版范围 / 更新日志 bullet for StudentSummary + plan-step panel**

- [ ] **Step 2: Run full suites**

```bash
pytest -q
cd frontend; npx vitest run
```

Record exact counts in VERSION table.

- [ ] **Step 3: Commit**

```bash
git add VERSION.md
git commit -m "docs: note Edition 0901_2 student summary"
```

---

## Spec coverage (self-review)

| Spec requirement | Task |
| --- | --- |
| StudentSummary + builder + overlay C | 1 |
| Demo seed metadata | 2 |
| GET summary/student | 3 |
| Client | 4 |
| Plan-step panel | 5 |
| VERSION | 6 |
| Out-of-scope items | Not tasked |

Seeded numbers locked: 2/5 tasks, 5 stars, locked Chinese strings for current_task / next_challenge.
