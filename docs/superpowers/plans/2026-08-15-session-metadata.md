# Session Metadata Listing Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add typed `SessionStore.list_all_metadata()` that projects dashboard-ready metadata from existing `SessionState` files without schema or API changes.

**Architecture:** Introduce a Pydantic `SessionMetadata` model next to `SessionSummary`. Add a private `_to_metadata(state, path)` projector and `list_all_metadata()` on the existing JSON `SessionStore`. Mastery fields are derived from `diagnosis.knowledge_mastery`; `updated_at` comes from the session file mtime.

**Tech Stack:** Python 3.11+, Pydantic v2, pytest, existing `ilearn` package layouts.

**Spec:** `docs/superpowers/specs/2026-08-15-session-metadata-design.md`

## Global Constraints

- Derive metadata only from existing `SessionState` fields (+ file mtime); do **not** modify `SessionState` or `DiagnosisReport` fields.
- Do **not** touch HTTP APIs or the React frontend in this slice.
- Weak-skill threshold is fixed at **0.6** (`score_rate < 0.6`).
- Keep `list_all` / `list_by_nickname` / CRUD behavior unchanged (including fail-on-corrupt for listing).
- Diff should only touch: `ilearn/core/schemas.py`, `ilearn/storage/sessions.py`, `tests/test_session_store.py`.
- Commit only if the user explicitly asks (user git preference); otherwise skip commit steps and stop after green tests.

---

## File map

| File | Responsibility |
| --- | --- |
| `ilearn/core/schemas.py` | Add `SessionMetadata` model (do not change `SessionSummary` / `SessionState`) |
| `ilearn/storage/sessions.py` | `_to_metadata`, `list_all_metadata` |
| `tests/test_session_store.py` | Empty / with-diagnosis / no-diagnosis / nickname-fallback coverage |

---

### Task 1: Failing tests for `list_all_metadata`

**Files:**
- Modify: `tests/test_session_store.py`
- Test: `tests/test_session_store.py`

**Interfaces:**
- Consumes: existing `SessionStore`, `StudentProfile`; will soon consume `SessionMetadata`, `DiagnosisReport`, `KnowledgeMastery`
- Produces: failing tests that lock the public contract for Tasks 2–3

- [ ] **Step 1: Append these tests to `tests/test_session_store.py`**

Keep existing tests. Add imports and helpers at the top of the file (merge with current imports):

```python
from datetime import timezone

from ilearn.core.schemas import (
    DiagnosisReport,
    KnowledgeMastery,
    SessionMetadata,
    StudentProfile,
)
from ilearn.storage.sessions import SessionStore


def test_list_all_metadata_empty(tmp_path):
    store = SessionStore(tmp_path)
    assert store.list_all_metadata() == []


def test_list_all_metadata_projects_diagnosis(tmp_path):
    store = SessionStore(tmp_path)
    state = store.create(
        StudentProfile(region="北京", grade=5, age=11, nickname="Alice")
    )
    state.diagnosis = DiagnosisReport(
        curriculum_label="pilot",
        knowledge_mastery=[
            KnowledgeMastery(
                knowledge_id="fraction",
                score_rate=0.4,
                level="weak",
            ),
            KnowledgeMastery(
                knowledge_id="decimal",
                score_rate=0.8,
                level="mastered",
            ),
        ],
    )
    store.save(state)

    rows = store.list_all_metadata()
    assert len(rows) == 1
    row = rows[0]
    assert isinstance(row, SessionMetadata)
    assert row.session_id == state.session_id
    assert row.nickname == "Alice"
    assert row.grade == 5
    assert row.region == "北京"
    assert row.overall_mastery == 0.6
    assert row.weak_skills == ["fraction"]
    assert row.skill_mastery == {"fraction": 0.4, "decimal": 0.8}
    assert row.phase == state.phase
    assert row.updated_at is not None
    assert row.updated_at.tzinfo is not None


def test_list_all_metadata_defaults_without_diagnosis(tmp_path):
    store = SessionStore(tmp_path)
    state = store.create(StudentProfile(region="上海", grade=4, age=10))
    rows = store.list_all_metadata()
    assert len(rows) == 1
    row = rows[0]
    assert row.session_id == state.session_id
    assert row.nickname == "未命名"
    assert row.overall_mastery == 0.0
    assert row.weak_skills == []
    assert row.skill_mastery == {}
```

- [ ] **Step 2: Run the new tests to verify they fail**

Run from repo root `projects/ILearn`:

```bash
python -m pytest tests/test_session_store.py::test_list_all_metadata_empty tests/test_session_store.py::test_list_all_metadata_projects_diagnosis tests/test_session_store.py::test_list_all_metadata_defaults_without_diagnosis -v
```

Expected: FAIL with `ImportError` / `AttributeError` (`SessionMetadata` missing and/or `list_all_metadata` missing).

- [ ] **Step 3: Commit (only if user requested commits)**

```bash
git add tests/test_session_store.py
git commit -m "test: add failing session metadata listing coverage"
```

If commits are not requested, skip this step.

---

### Task 2: Add `SessionMetadata` model

**Files:**
- Modify: `ilearn/core/schemas.py` (immediately after `SessionSummary`, ~lines 411–415)

**Interfaces:**
- Consumes: existing `BaseModel`, `datetime`, `SessionPhase`, `GradeLevel`
- Produces: `class SessionMetadata(BaseModel)` with fields listed below

- [ ] **Step 1: Insert `SessionMetadata` after `SessionSummary`**

Place this class **after** `SessionSummary` and **before** the `from ilearn.core.review import ReviewState` line:

```python
class SessionMetadata(BaseModel):
    """Lightweight session projection for dashboards and listing."""

    session_id: str
    nickname: str
    grade: GradeLevel
    region: str
    overall_mastery: float = 0.0
    weak_skills: list[str] = Field(default_factory=list)
    skill_mastery: dict[str, float] = Field(default_factory=dict)
    updated_at: datetime | None = None
    phase: SessionPhase
```

Do not rename or alter `SessionSummary`.

- [ ] **Step 2: Re-run metadata tests (still expect method missing)**

```bash
python -m pytest tests/test_session_store.py::test_list_all_metadata_empty -v
```

Expected: FAIL with `AttributeError: 'SessionStore' object has no attribute 'list_all_metadata'` (import of `SessionMetadata` succeeds).

- [ ] **Step 3: Commit (only if user requested commits)**

```bash
git add ilearn/core/schemas.py
git commit -m "feat: add SessionMetadata projection model"
```

---

### Task 3: Implement `_to_metadata` and `list_all_metadata`

**Files:**
- Modify: `ilearn/storage/sessions.py`
- Test: `tests/test_session_store.py`

**Interfaces:**
- Consumes: `SessionState`, `SessionMetadata`, `Path`
- Produces:
  - `_to_metadata(state: SessionState, path: Path) -> SessionMetadata`
  - `SessionStore.list_all_metadata(self) -> list[SessionMetadata]`

- [ ] **Step 1: Update imports in `ilearn/storage/sessions.py`**

```python
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from ilearn.core.schemas import SessionMetadata, SessionState, StudentProfile

_WEAK_SKILL_THRESHOLD = 0.6
```

- [ ] **Step 2: Add module-level `_to_metadata`**

```python
def _to_metadata(state: SessionState, path: Path) -> SessionMetadata:
    nickname = (state.profile.nickname or "").strip() or "未命名"
    skill_mastery: dict[str, float] = {}
    weak_skills: list[str] = []
    overall_mastery = 0.0

    if state.diagnosis and state.diagnosis.knowledge_mastery:
        rows = state.diagnosis.knowledge_mastery
        skill_mastery = {row.knowledge_id: row.score_rate for row in rows}
        weak_skills = [
            row.knowledge_id
            for row in rows
            if row.score_rate < _WEAK_SKILL_THRESHOLD
        ]
        overall_mastery = sum(row.score_rate for row in rows) / len(rows)

    updated_at = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)

    return SessionMetadata(
        session_id=state.session_id,
        nickname=nickname,
        grade=state.profile.grade,
        region=state.profile.region,
        overall_mastery=overall_mastery,
        weak_skills=weak_skills,
        skill_mastery=skill_mastery,
        updated_at=updated_at,
        phase=state.phase,
    )
```

- [ ] **Step 3: Add `list_all_metadata` on `SessionStore`**

Insert after `list_all` (keep `list_all` body unchanged):

```python
def list_all_metadata(self) -> list[SessionMetadata]:
    rows: list[SessionMetadata] = []
    for path in sorted(self.root.glob("*.json")):
        state = SessionState.model_validate_json(path.read_text(encoding="utf-8"))
        rows.append(_to_metadata(state, path))
    return rows
```

- [ ] **Step 4: Run metadata tests — expect PASS**

```bash
python -m pytest tests/test_session_store.py -v
```

Expected: all tests in the file PASS (including prior nickname/delete tests).

- [ ] **Step 5: Commit (only if user requested commits)**

```bash
git add ilearn/storage/sessions.py tests/test_session_store.py ilearn/core/schemas.py
git commit -m "feat: project SessionMetadata from session store listings"
```

---

### Task 4: Verification gate

**Files:**
- None (read-only verification)

**Interfaces:**
- Consumes: Tasks 1–3 deliverables
- Produces: confirmation that constraints hold

- [ ] **Step 1: Run focused + related session tests**

```bash
python -m pytest tests/test_session_store.py -v
```

Expected: PASS.

- [ ] **Step 2: Confirm diff scope**

```bash
git status
git diff --stat
```

Expected: only `schemas.py`, `sessions.py`, `test_session_store.py` (plus the already-written spec/plan docs if untracked). No `frontend/` or `ilearn/api/` changes.

- [ ] **Step 3: Mark slice 1 complete**

Do not start model-router slice unless the user asks.

---

## Self-review (plan vs spec)

| Spec requirement | Task |
| --- | --- |
| `SessionMetadata` fields + derivation rules | Task 2 + Task 3 `_to_metadata` |
| Weak threshold 0.6 | Task 3 `_WEAK_SKILL_THRESHOLD` |
| `list_all_metadata()` sorted scan / validate | Task 3 |
| No `SessionState` / API / UI changes | Global constraints + Task 4 |
| Tests: empty / with diagnosis / no diagnosis + nickname fallback | Task 1 |
| Existing tests stay green | Task 3 Step 4 / Task 4 |

No placeholders. Types consistent: `list_all_metadata() -> list[SessionMetadata]`, `_to_metadata(state, path) -> SessionMetadata`.
