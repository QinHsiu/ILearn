# Edition 0827 Multimodal Curriculum Binding Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development. Steps use checkbox syntax.

**Goal:** Curriculum-bound multimodal items (MV-MATH) with CurriculumRef gates, anchor 2–4 + full paper ≤4 multimodal, frontend image render.

**Architecture:** Separate `multimodal_bank.json`; `CurriculumGate` validates/filters; `mv_math` importer with bindings crosswalk; extend `AssessmentAgent` + `/pilot-assets` + `Assessment.tsx`.

**Tech Stack:** Python 3.11+, Pydantic, FastAPI, React, pytest; HF `PeijieWang/MV-MATH`.

## Global Constraints

- Full diagnostic paper stays **exactly 20** items.
- Do **not** commit `doc/` or `docs/`.
- Pilot: **北京** / **人教版** / grades **4–6**.
- Unbound multimodal items **rejected** at import.
- Raw MV-MATH in `data/raw/mv_math/` (gitignored).
- Anchor multimodal: **2–4**; full paper multimodal: **≤4**.
- Do not merge multimodal into `example_bank.json`.

---

### Task 1: CurriculumRef + CurriculumGate (0827a)

**Files:**
- Modify: `ilearn/core/schemas.py` — add `CurriculumRef`; extend `AssessmentItem` with `image_paths`, `is_multimodal`
- Create: `ilearn/core/curriculum_gate.py`
- Create: `tests/fixtures/multimodal_tiny.json`
- Test: `tests/test_curriculum_gate.py`

**Interfaces:**
- `CurriculumRef` pydantic model per spec
- `CurriculumGate(overrides_path, syllabus_path, graph)` with `validate_item(item) -> list[str]`, `eligible_for_profile(...)`, `filter_bank(...)`

Run: `python -m pytest tests/test_curriculum_gate.py -v`

---

### Task 2: MV-MATH bindings + importer (0827b)

**Files:**
- Create: `data/curriculum/mv_math_bindings.json` (rules for legacy 13 kp)
- Create: `ilearn/data/importers/mv_math.py`
- Modify: `scripts/download_raw_data.py` — add `mv_math` dataset
- Create: `tests/fixtures/mv_math_tiny.json` + placeholder PNGs or skip image copy in fixture test
- Test: `tests/test_mv_math_importer.py`

---

### Task 3: build_pilot multimodal step (0827c)

**Files:**
- Modify: `ilearn/data/build_pilot.py` — `build_multimodal_bank()`
- Modify: `data/pilot/ATTRIBUTION.md`
- Test: `tests/test_multimodal_bank.py`

---

### Task 4: Assessment + pilot-assets API (0827d)

**Files:**
- Modify: `ilearn/agents/assessment.py` — multimodal in adaptive anchor/full
- Modify: `ilearn/api/app.py` — `GET /pilot-assets/{path}`
- Test: `tests/test_adaptive_multimodal.py`, `tests/test_pilot_assets_api.py`

---

### Task 5: Frontend Assessment.tsx (0827e)

**Files:**
- Modify: `frontend/src/pages/Assessment.tsx`
- Modify: `frontend/src/api/client.ts` if needed for asset URLs
- Test: `frontend/src/pages/Assessment.multimodal.test.tsx`

---

### Task 6: VERSION + regression (0827 wrap)

**Files:**
- Modify: `VERSION.md`, `README.md` test badge
- Run: `python -m pytest -q` + frontend tests
