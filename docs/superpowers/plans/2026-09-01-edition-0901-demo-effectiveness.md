# Edition 0901 Demo Unit + Effectiveness Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship a one-click 人教·五年级「小数乘法」pre-seeded closed-loop demo session plus teaching-effectiveness metrics API, PDF export, Landing CTA, dual-dashboard demo panels, and EffectivenessDashboard UI.

**Architecture:** JSON unit fixture + sync seed factory builds a complete `SessionState` (20-item paper, grades, diagnosis, plan, demo metadata) and binds demo teacher/parent. Pure `compute_metrics(session)` derives KPIs; FastAPI exposes demo create + effectiveness GET/PDF; frontend deep-links via existing query params (no react-router rewrite).

**Tech Stack:** Python 3.11+, FastAPI, Pydantic, pytest; React 19 + Vitest; existing `markdown_to_pdf` / RelationshipStore / SessionStore.

## Global Constraints

- Demo paper length **exactly 20** items; pilot grade **5** / region **北京**.
- Mode **C1**: pre-seed full loop (`phase=plan`), not runtime orchestrator auto-run.
- Sync APIs only; no asyncio SessionService rewrite.
- Knowledge IDs prefer real pilot ids: `dec_mult`, `kp_5fbf83ae12`（小数乘整数）, `kp_4433814116`（小数乘小数）.
- Demo binds: parent `demo_parent`; teacher `demo_teacher` + class `demo_class_5a`.
- Do **not** commit `doc/` or `docs/`; update `VERSION.md` only.
- Reuse `markdown_to_pdf` (dual engine OK); no engine unification this edition.
- Deep links use existing query style (`?login=1&role=teacher&user=demo_teacher&class_id=demo_class_5a&student_id=<sid>`).
- TDD per task; offline suite must stay green.

## File Structure

| Path | Responsibility |
| --- | --- |
| `data/demo/units/math_5_1.json` | Unit fixture |
| `data/demo/effectiveness_summary.json` | Generated/committed summary fixture |
| `ilearn/demo/__init__.py` | Package |
| `ilearn/demo/units.py` | Load unit JSON by id |
| `ilearn/demo/seed.py` | `seed_demo_session(...)` → SessionState |
| `ilearn/api/demo.py` | Demo router |
| `ilearn/core/effectiveness.py` | Metrics model + compute + markdown |
| `ilearn/api/app.py` | Mount demo router; effectiveness routes |
| `scripts/generate_demo_effectiveness.py` | Write summary JSON |
| `frontend/src/api/client.ts` | demo + effectiveness client |
| `frontend/src/pages/LandingPage.tsx` | Demo CTA |
| `frontend/src/components/EffectivenessDashboard.tsx` | KPI UI |
| `frontend/src/pages/TeacherDashboard.tsx` | Demo panels |
| `frontend/src/pages/ParentDashboard.tsx` | Demo panels |
| `tests/test_demo_unit_math_5_1.py` | Seed + demo API |
| `tests/test_effectiveness.py` | Metrics + API + PDF |
| `VERSION.md` | Edition 0901 |

---

### Task 1: Demo unit fixture + seed factory + POST /demo/units/{id}/session

**Files:**
- Create: `data/demo/units/math_5_1.json`
- Create: `ilearn/demo/__init__.py`, `ilearn/demo/units.py`, `ilearn/demo/seed.py`
- Create: `ilearn/api/demo.py`
- Modify: `ilearn/api/app.py` (include router; pass store + relationships)
- Test: `tests/test_demo_unit_math_5_1.py`

**Interfaces:**
- Consumes: `SessionStore`, `RelationshipStore`, schemas
- Produces:
  - `load_demo_unit(unit_id: str) -> dict`
  - `seed_demo_session(unit: dict, *, session_id: str | None = None) -> SessionState`
  - `create_demo_session(unit_id, store, relationships) -> dict` with keys `session_id`, `unit_name`, `links` (`student`,`teacher`,`parent`)
  - Router prefix `/demo`, `POST /demo/units/{unit_id}/session`

**Fixture minimum JSON keys:** `id`, `name`, `grade`, `region`, `estimated_duration`, `knowledge_ids` (list of 4 ids/names mapping), `blueprint` (`total_questions`: 20), `profile_overrides`, `demo_class_data`, `demo_mastery_gain`, `demo_weaknesses_resolved`, `initial_mastery` map.

**Seed rules:**
- 20 items: ids `demo_m51_{i:02d}`; stems mention 小数/乘法 life context; types cycle choice/fill/constructed; knowledge_ids rotate across `kp_5fbf83ae12`, `kp_4433814116`, `dec_mult`
- grades: ~12 correct / 8 incorrect biased toward weak KPs
- diagnosis mastery: high on 乘整数, weak on 乘小数 / dec_mult
- enrichment parent/teacher summaries (Chinese strings)
- plan markdown with weak KP focus
- evidence_log ≥ 5
- metadata as in spec
- phase `SessionPhase.PLAN`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_demo_unit_math_5_1.py
from pathlib import Path
from fastapi.testclient import TestClient
from ilearn.api.app import create_app
from ilearn.demo.seed import seed_demo_session
from ilearn.demo.units import load_demo_unit
from ilearn.core.schemas import SessionPhase

PILOT = Path(__file__).resolve().parents[1] / "data" / "pilot"


def test_load_and_seed_math_5_1():
    unit = load_demo_unit("math_5_1")
    assert unit["id"] == "math_5_1"
    session = seed_demo_session(unit)
    assert session.phase == SessionPhase.PLAN
    assert session.paper is not None and len(session.paper.items) == 20
    assert session.grades and len(session.grades) == 20
    assert session.diagnosis is not None
    assert session.plan is not None
    assert session.metadata.get("demo_unit") == "math_5_1"
    assert "demo_class_data" in session.metadata
    assert len(session.evidence_log) >= 5


def test_demo_session_api(tmp_path: Path):
    client = TestClient(create_app(sessions_dir=tmp_path, pilot_data_dir=PILOT, llm=None))
    r = client.post("/demo/units/math_5_1/session")
    assert r.status_code == 200
    body = r.json()
    sid = body["session_id"]
    assert body["unit_name"]
    assert "teacher" in body["links"] and "parent" in body["links"]
    g = client.get(f"/sessions/{sid}")
    assert g.status_code == 200
    assert g.json()["metadata"]["demo_unit"] == "math_5_1"
    bad = client.post("/demo/units/nope/session")
    assert bad.status_code == 404
```

- [ ] **Step 2: Run tests — expect FAIL**

Run: `python -m pytest tests/test_demo_unit_math_5_1.py -v`

- [ ] **Step 3: Implement fixture, seed, router, mount**

`create_demo_router(store, relationships)` → POST handler: load unit or 404; seed; `store.save`; `relationships.bind_parent("demo_parent", sid)`; `bind_teacher("demo_teacher", "demo_class_5a", sid)`; return payload with links using query strings.

Ensure `create_app` passes the same `RelationshipStore` instance already constructed.

- [ ] **Step 4: Run tests — expect PASS**

Run: `python -m pytest tests/test_demo_unit_math_5_1.py -v`

- [ ] **Step 5: Commit**

```bash
git add data/demo/units/math_5_1.json ilearn/demo ilearn/api/demo.py ilearn/api/app.py tests/test_demo_unit_math_5_1.py
git commit -m "feat: seed math_5_1 demo unit session and POST /demo API"
```

---

### Task 2: Effectiveness model + compute + GET API

**Files:**
- Create: `ilearn/core/effectiveness.py`
- Modify: `ilearn/api/app.py` (GET effectiveness)
- Test: `tests/test_effectiveness.py`

**Interfaces:**
- Produces:
  - `class TeachingEffectivenessMetrics(BaseModel):` fields per design spec
  - `def compute_metrics(session: SessionState) -> TeachingEffectivenessMetrics`
  - `def effectiveness_payload(session: SessionState) -> dict` with `metrics` + `comparison.traditional_vs_ilearn`
  - `GET /sessions/{session_id}/effectiveness`

**Formula lock-in:**
- pre_score from grades `final_correct`
- manual if `grading_degraded` or corresponding paper item `type == "constructed"`
- traditional = n*2; ilearn = manual*1 + 0.5; time_saved_percent accordingly (0 if n==0)
- weakness_remaining = count level=="weak"; weakness_resolved = int(metadata.get("demo_weaknesses_resolved") or 0)
- mastery_gain = float(metadata.get("demo_mastery_gain") or 0) when post is None
- diagnosis_confidence from enrichment or 0.75
- hint_used_count = sum of hint_interactions lengths

- [ ] **Step 1: Failing tests**

```python
# tests/test_effectiveness.py
from ilearn.core.effectiveness import compute_metrics, TeachingEffectivenessMetrics
from ilearn.demo.units import load_demo_unit
from ilearn.demo.seed import seed_demo_session
from fastapi.testclient import TestClient
from ilearn.api.app import create_app
from pathlib import Path

PILOT = Path(__file__).resolve().parents[1] / "data" / "pilot"


def test_compute_metrics_on_demo_seed():
    session = seed_demo_session(load_demo_unit("math_5_1"))
    m = compute_metrics(session)
    assert isinstance(m, TeachingEffectivenessMetrics)
    assert m.total_questions == 20
    assert 0 <= m.pre_assessment_score <= 100
    assert m.completion_rate == 100.0
    assert m.evidence_count >= 5
    assert m.time_saved_percent > 0


def test_effectiveness_endpoint(tmp_path: Path):
    client = TestClient(create_app(sessions_dir=tmp_path, pilot_data_dir=PILOT, llm=None))
    sid = client.post("/demo/units/math_5_1/session").json()["session_id"]
    r = client.get(f"/sessions/{sid}/effectiveness")
    assert r.status_code == 200
    body = r.json()
    assert "metrics" in body and "comparison" in body
    assert "traditional_vs_ilearn" in body["comparison"]
```

- [ ] **Step 2: Run — expect FAIL**

- [ ] **Step 3: Implement `effectiveness.py` + route**

- [ ] **Step 4: Run — expect PASS**

- [ ] **Step 5: Commit**

```bash
git add ilearn/core/effectiveness.py ilearn/api/app.py tests/test_effectiveness.py
git commit -m "feat: teaching effectiveness metrics and GET API"
```

---

### Task 3: Effectiveness PDF + generate script fixture

**Files:**
- Modify: `ilearn/core/effectiveness.py` (`render_effectiveness_markdown`)
- Modify: `ilearn/api/app.py` (export route)
- Create: `scripts/generate_demo_effectiveness.py`
- Create: `data/demo/effectiveness_summary.json` (run script once, commit output)
- Extend: `tests/test_effectiveness.py`

**Interfaces:**
- `def render_effectiveness_markdown(metrics: TeachingEffectivenessMetrics, *, unit_name: str = "") -> str`
- `GET /sessions/{session_id}/export/effectiveness.pdf` → `markdown_to_pdf(...)`
- Script: create temp seeded session metrics OR call compute on seeded in-memory session; write summary JSON with avg fields

- [ ] **Step 1: Failing test**

```python
def test_effectiveness_pdf(tmp_path: Path):
    client = TestClient(create_app(sessions_dir=tmp_path, pilot_data_dir=PILOT, llm=None))
    sid = client.post("/demo/units/math_5_1/session").json()["session_id"]
    r = client.get(f"/sessions/{sid}/export/effectiveness.pdf")
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("application/pdf")
    assert len(r.content) > 100
```

- [ ] **Step 2: Run — expect FAIL**

- [ ] **Step 3: Implement markdown + PDF route + script; generate fixture**

- [ ] **Step 4: PASS + commit fixture**

```bash
git add ilearn/core/effectiveness.py ilearn/api/app.py scripts/generate_demo_effectiveness.py data/demo/effectiveness_summary.json tests/test_effectiveness.py
git commit -m "feat: effectiveness PDF export and demo summary fixture"
```

---

### Task 4: Frontend client + Landing demo CTA

**Files:**
- Modify: `frontend/src/api/client.ts`
- Modify: `frontend/src/pages/LandingPage.tsx`
- Create: `frontend/src/pages/LandingPage.test.tsx` (or hook test for startDemo)
- Optional CSS in `frontend/src/styles.css` for demo card (minimal, match landing)

**Interfaces:**
- `api.createDemoSession(unitId: string)` → `{ session_id, unit_name, links }`
- Landing button 「体验小数乘法」→ createDemoSession(`math_5_1`) → `window.location.href = links.teacher` (or show three links after create)

- [ ] **Step 1: Vitest** — button present; clicking mocks API and assigns location (jsdom)

- [ ] **Step 2: FAIL**

- [ ] **Step 3: Implement**

- [ ] **Step 4: `cd frontend && npm test -- --run` focused PASS**

- [ ] **Step 5: Commit**

```bash
git add frontend/src/api/client.ts frontend/src/pages/LandingPage.tsx frontend/src/pages/LandingPage.test.tsx frontend/src/styles.css
git commit -m "feat: Landing one-click math_5_1 demo entry"
```

---

### Task 5: EffectivenessDashboard + Teacher/Parent demo panels

**Files:**
- Create: `frontend/src/components/EffectivenessDashboard.tsx` (+ `.test.tsx`)
- Modify: `frontend/src/pages/TeacherDashboard.tsx`, `ParentDashboard.tsx`
- Modify: `frontend/src/components/DashboardDetail.tsx` optionally embed effectiveness when `metadata.demo_unit`
- Modify: `frontend/src/api/client.ts` (`getEffectiveness`, `exportEffectivenessPdf` blob download helper)
- CSS: `frontend/src/dashboard.css` minimal metrics grid

**Behavior:**
- When `detail.metadata?.demo_unit` set, show: unit name, class_size/avg_mastery/common_weaknesses from `demo_class_data`; teacher surface: workload via effectiveness fetch; parent surface: parent_summary from enrichment + tips
- EffectivenessDashboard: 4 cards (mastery_gain, time_saved, completion, confidence) + comparison table + export button

- [ ] **Step 1: Vitest** render dashboard with mock metrics; Teacher panel shows demo_class_data when present

- [ ] **Step 2–4: TDD implement**

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/EffectivenessDashboard.tsx frontend/src/components/EffectivenessDashboard.test.tsx frontend/src/pages/TeacherDashboard.tsx frontend/src/pages/ParentDashboard.tsx frontend/src/components/DashboardDetail.tsx frontend/src/api/client.ts frontend/src/dashboard.css
git commit -m "feat: effectiveness dashboard and role demo panels"
```

---

### Task 6: VERSION + full verification

**Files:**
- Modify: `VERSION.md`

- [ ] **Step 1: Run full suites**

```bash
python -m pytest -q
cd frontend && npm test -- --run
```

- [ ] **Step 2: Update VERSION** — tag `Edition 0901 小数乘法演示单元 + 教学效果量化`; changelog row with pytest/vitest counts

- [ ] **Step 3: Commit**

```bash
git add VERSION.md
git commit -m "docs: VERSION Edition 0901 demo unit and effectiveness"
```

---

## Self-Review (plan vs spec)

| Spec | Task |
| --- | --- |
| math_5_1 fixture + seed C1 | Task 1 |
| POST demo + binds | Task 1 |
| effectiveness compute + GET | Task 2 |
| PDF + summary script | Task 3 |
| Landing CTA | Task 4 |
| EffectivenessDashboard + dashboards | Task 5 |
| VERSION | Task 6 |
| Out of scope engines/router rewrite | Not planned |

No TBD placeholders. Types/formulas aligned with design.

---

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-09-01-edition-0901-demo-effectiveness.md`（`docs/` gitignored）。

**Two execution options:**

1. **Subagent-Driven (recommended)** — fresh subagent per task + review  
2. **Inline Execution** — this session via executing-plans  

Which approach?
