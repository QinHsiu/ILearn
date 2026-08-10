# ILearn MVP Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship an end-to-end ILearn MVP for elementary math (grades 4–6): 20-item template assessment → step grading → diagnosis → learning plan, via FastAPI + Streamlit + CLI, with a minimal eval harness.

**Architecture:** Pipeline modules behind a thin orchestrator; template-first item bank under `CurriculumProvider`; OpenAI-compatible `LLMClient` for constructed grading and narrative polish; JSON session storage; Streamlit talks HTTP-only to FastAPI.

**Tech Stack:** Python 3.11+, pydantic v2, FastAPI, uvicorn, httpx, streamlit, typer, pytest, python-dotenv, openai (compatible client)

## Global Constraints

- Default paper size: **20** items; difficulty **10/8/2**; types **8/8/4** (choice/fill/constructed)
- Subject focus: **elementary math** (理科重点，模板出题); grades **4–6** only
- Curriculum: Beijing·Renjiao **pilot pack only**; non-Beijing `region` → disclaimer in report
- Answer input: **text only** (no VL)
- UI: **简洁优美、教学特色** — calm academic palette, clear hierarchy, lesson-like flow (not admin dashboard; avoid generic AI-purple chrome)
- No LangGraph in MVP; no live web crawl; secrets only via `.env`
- Package root: `projects/ILearn/`; import package name `ilearn`
- Spec: `docs/superpowers/specs/2026-08-10-ilearn-mvp-design.md`

## File Map

| Path | Responsibility |
|------|----------------|
| `pyproject.toml` / `requirements.txt` | Dependencies and package metadata |
| `.env.example` | `ILEARN_LLM_BASE_URL`, `ILEARN_LLM_API_KEY`, `ILEARN_LLM_MODEL`, `ILEARN_API_BASE` |
| `ilearn/__init__.py` | Package version |
| `ilearn/core/schemas.py` | Pydantic models for profile, items, grades, diagnosis, plan, session |
| `ilearn/core/assessment.py` | `AssessmentBuilder` mix quotas + template instantiate |
| `ilearn/core/grading.py` | `StepGrader` rule + LLM JSON grade |
| `ilearn/core/diagnosis.py` | `Diagnoser` aggregate mastery + abilities + Top-5 |
| `ilearn/core/planning.py` | `Planner` week plan Markdown+JSON |
| `ilearn/core/orchestrator.py` | Session pipeline glue |
| `ilearn/core/report.py` | Aggregate Markdown report renderer |
| `ilearn/providers/curriculum.py` | `CurriculumProvider` ABC + `PilotBeijingRenjiaoProvider` |
| `ilearn/providers/llm.py` | `LLMClient` OpenAI-compatible |
| `ilearn/storage/sessions.py` | JSON file load/save under `data/sessions/` |
| `ilearn/api/app.py` | FastAPI routes |
| `ilearn/cli/main.py` | Typer: `run`, `eval` |
| `ilearn/web/app.py` | Streamlit wizard + custom CSS |
| `ilearn/eval/runner.py` | Eval metrics |
| `data/pilot/knowledge.json` | Knowledge nodes |
| `data/pilot/templates.json` | Item templates |
| `data/eval/step_grading_fixtures.json` | 10–30 fixtures |
| `tests/...` | Pytest suite mirroring modules |

---

### Task 1: Scaffold + core schemas

**Files:**
- Create: `pyproject.toml`, `requirements.txt`, `.env.example`, `ilearn/__init__.py`, `ilearn/core/schemas.py`, `tests/test_schemas.py`
- Create: `data/sessions/.gitkeep`

**Interfaces:**
- Produces: pydantic models `StudentProfile`, `KnowledgeNode`, `ItemTemplate`, `AssessmentItem`, `AssessmentPaper`, `StudentAnswer`, `StepResult`, `GradeResult`, `KnowledgeMastery`, `DiagnosisReport`, `LearningPlanReport`, `SessionState`

- [ ] **Step 1: Write failing schema tests**

```python
# tests/test_schemas.py
from ilearn.core.schemas import StudentProfile, AssessmentPaper, ERROR_TAGS

def test_profile_grade_must_be_4_to_6():
    StudentProfile(region="北京", grade=5, age=11)
    try:
        StudentProfile(region="北京", grade=3, age=9)
        assert False, "expected validation error"
    except Exception:
        pass

def test_error_tags_controlled_vocab():
    assert "calc_error" in ERROR_TAGS
    assert len(ERROR_TAGS) == 5
```

- [ ] **Step 2: Run test — expect fail (module missing)**

Run: `cd projects/ILearn && pytest tests/test_schemas.py -v`  
Expected: FAIL import error

- [ ] **Step 3: Add dependencies + implement schemas**

`requirements.txt`:
```
pydantic>=2.6
fastapi>=0.110
uvicorn>=0.27
httpx>=0.27
streamlit>=1.32
typer>=0.12
python-dotenv>=1.0
openai>=1.30
pytest>=8.0
```

`ilearn/core/schemas.py` must define:
- `ERROR_TAGS = ("concept_gap", "calc_error", "misread", "method_wrong", "incomplete")`
- `StudentProfile` with `grade: Literal[4,5,6]`
- `AssessmentItem` with `type: Literal["choice","fill","constructed"]`, `difficulty: Literal["easy","medium","hard"]`, `answer_key: str | None`, `rubric_steps: list[str]`, `knowledge_ids: list[str]`, `choices: list[str] | None`
- `GradeResult` fields per spec §5.1
- `DiagnosisReport` with `interventions: list[...]` (max used as Top-5 later), `ability_scores: dict[str, float]`, `curriculum_label: str`, `region_mismatch_disclaimer: str | None`
- `LearningPlanReport` with `days: list[{day, focus_knowledge_ids, tasks, minutes}]`, `markdown: str`
- `SessionState` holding profile, paper, answers, grades, diagnosis, plan

- [ ] **Step 4: Run tests — expect pass**

Run: `pytest tests/test_schemas.py -v`  
Expected: PASS

- [ ] **Step 5: Commit** (if git available)

```bash
git add pyproject.toml requirements.txt .env.example ilearn tests data/sessions
git commit -m "feat: scaffold ILearn package and core schemas"
```

---

### Task 2: Pilot curriculum data + CurriculumProvider

**Files:**
- Create: `data/pilot/knowledge.json`, `data/pilot/templates.json`
- Create: `ilearn/providers/curriculum.py`
- Create: `tests/test_curriculum.py`

**Interfaces:**
- Consumes: `KnowledgeNode`, `ItemTemplate` schemas
- Produces: `CurriculumProvider.list_knowledge(grade) -> list[KnowledgeNode]`; `list_templates(grade, difficulty=None, item_type=None) -> list[ItemTemplate]`; `PilotBeijingRenjiaoProvider(data_dir)`; `label -> "北京·人教·小学数学"`

- [ ] **Step 1: Write failing provider tests**

```python
from pathlib import Path
from ilearn.providers.curriculum import PilotBeijingRenjiaoProvider

ROOT = Path(__file__).resolve().parents[1] / "data" / "pilot"

def test_grade5_has_enough_templates_for_mix():
    p = PilotBeijingRenjiaoProvider(ROOT)
    # Need enough distinct templates to build 10 easy / 8 medium / 2 hard and 8/8/4 types
    for g in (4, 5, 6):
        t = p.list_templates(g)
        assert len(t) >= 20
        assert {x.difficulty for x in t} >= {"easy", "medium", "hard"}
        assert {x.item_type for x in t} >= {"choice", "fill", "constructed"}
```

- [ ] **Step 2: Run — expect fail**

Run: `pytest tests/test_curriculum.py -v`

- [ ] **Step 3: Author pilot JSON + provider**

`knowledge.json`: ≥12 nodes across grades 4–6 (fractions, decimals, perimeter/area, angles, simple equations, factors). Each: `id`, `grade`, `name`, `ability_tags` (`logic`|`spatial`|`mental_math`).

`templates.json`: ≥24 templates per grade **or** shared pool tagged by grade list — enough to sample without replacement for 20 items. Each template:
```json
{
  "id": "g5_frac_add_01",
  "grades": [5],
  "item_type": "choice",
  "difficulty": "easy",
  "knowledge_ids": ["frac_add_same_den"],
  "stem_template": "计算：{a}/{d} + {b}/{d} = ?",
  "slots": {"a": "int:1-8", "b": "int:1-8", "d": "choice:2,4,5,8"},
  "answer_key_template": "{(a+b)/d simplified or numeric}",
  "choices_template": ["..."],
  "rubric_steps": ["通分或同分母相加", "约分得结果"]
}
```
Implement a small slot renderer in `curriculum.py` or `assessment.py` (`int:lo-hi`, `choice:a,b,c`). For MVP, prefer **pre-resolved numeric answer_key in template after slot fill** via deterministic Python eval of simple expressions declared in template field `answer_expr` (e.g. `"(a+b)/d"`), not free LLM.

- [ ] **Step 4: Tests pass**

Run: `pytest tests/test_curriculum.py -v`

- [ ] **Step 5: Commit**

```bash
git add data/pilot ilearn/providers/curriculum.py tests/test_curriculum.py
git commit -m "feat: add pilot Beijing Renjiao curriculum pack and provider"
```

---

### Task 3: AssessmentBuilder (20-item mix)

**Files:**
- Create: `ilearn/core/assessment.py`
- Create: `tests/test_assessment.py`

**Interfaces:**
- Consumes: `CurriculumProvider`, `StudentProfile`
- Produces: `AssessmentBuilder.build(profile, n=20) -> AssessmentPaper`; raises `AssessmentBuildError` if quotas unmet

- [ ] **Step 1: Failing tests for quotas**

```python
def test_build_20_mix_exact():
    paper = builder.build(StudentProfile(region="北京", grade=5, age=11), n=20)
    assert len(paper.items) == 20
    assert sum(1 for i in paper.items if i.difficulty == "easy") == 10
    assert sum(1 for i in paper.items if i.difficulty == "medium") == 8
    assert sum(1 for i in paper.items if i.difficulty == "hard") == 2
    assert sum(1 for i in paper.items if i.type == "choice") == 8
    assert sum(1 for i in paper.items if i.type == "fill") == 8
    assert sum(1 for i in paper.items if i.type == "constructed") == 4
```

Algorithm note (implement exactly): build a **joint quota** by iterating a fixed blueprint list of 20 `(difficulty, type)` pairs that realize both margins (construct one valid 20-row contingency; hardcode the blueprint in code), then for each slot pick a matching unused template and instantiate.

- [ ] **Step 2: Run — fail**

- [ ] **Step 3: Implement `AssessmentBuilder`**

- [ ] **Step 4: Tests pass** (also test fail-closed when provider emptied)

- [ ] **Step 5: Commit**

```bash
git commit -m "feat: template assessment builder with locked 20-item mix"
```

---

### Task 4: LLMClient

**Files:**
- Create: `ilearn/providers/llm.py`
- Create: `tests/test_llm.py`

**Interfaces:**
- Produces: `LLMClient.chat_json(system: str, user: str) -> dict`; reads env `ILEARN_LLM_*`; `LLMClient.available() -> bool`

- [ ] **Step 1: Test unavailable without key**

```python
def test_available_false_without_key(monkeypatch):
    monkeypatch.delenv("ILEARN_LLM_API_KEY", raising=False)
    assert LLMClient.from_env().available() is False
```

- [ ] **Step 2–4: Implement client wrapping `openai.OpenAI(base_url=..., api_key=...)`; parse JSON from content (strip fences); one retry on JSON parse failure**

- [ ] **Step 5: Commit**

```bash
git commit -m "feat: OpenAI-compatible LLM client"
```

---

### Task 5: StepGrader

**Files:**
- Create: `ilearn/core/grading.py`
- Create: `tests/test_grading.py`

**Interfaces:**
- Consumes: `AssessmentItem`, answer `str`, `LLMClient`
- Produces: `StepGrader.grade_item(...) -> GradeResult`; `grade_paper(paper, answers) -> list[GradeResult]`

- [ ] **Step 1: Failing tests**

```python
def test_choice_correct_no_llm():
    item = make_choice(answer_key="B")
    g = StepGrader(llm=None).grade_item(item, "B")
    assert g.final_correct is True
    assert g.grading_degraded is False

def test_choice_wrong_tags_without_llm_still_structured():
    g = StepGrader(llm=None).grade_item(make_choice(answer_key="B"), "A")
    assert g.final_correct is False
    assert "concept_gap" in g.error_tags or "misread" in g.error_tags
```

When `llm` missing/unavailable: choice/fill use rules; constructed returns `grading_degraded=True` with best-effort single step.

When LLM present: prompt must require JSON matching `GradeResult` subset; validate tags ⊆ `ERROR_TAGS`.

- [ ] **Step 2–4: Implement + pass tests**

- [ ] **Step 5: Commit**

```bash
git commit -m "feat: hybrid rule/LLM step grader"
```

---

### Task 6: Diagnoser + Planner + report Markdown

**Files:**
- Create: `ilearn/core/diagnosis.py`, `ilearn/core/planning.py`, `ilearn/core/report.py`
- Create: `tests/test_diagnosis.py`, `tests/test_planning.py`

**Interfaces:**
- `Diagnoser.diagnose(profile, paper, grades) -> DiagnosisReport` (Top-5 interventions; ability scores 0–100; mismatch disclaimer if region not 北京/Beijing)
- `Planner.plan(profile, diagnosis, daily_minutes=40) -> LearningPlanReport` (14 days max, default 7)
- `render_full_report(session) -> str` Markdown

- [ ] **Step 1: Tests**

```python
def test_top5_and_traceable():
    d = Diagnoser().diagnose(profile, paper, grades)
    assert len(d.interventions) <= 5
    assert d.curriculum_label.startswith("北京")

def test_plan_links_weak_knowledge():
    plan = Planner().plan(profile, diagnosis)
    weak = {i.knowledge_id for i in diagnosis.interventions}
    linked = {kid for day in plan.days for kid in day.focus_knowledge_ids}
    assert weak & linked
```

- [ ] **Step 2–4: Implement heuristic mastery** (`mastered` if rate≥0.8, `unstable` if ≥0.5 else `weak`); abilities = mean of related item correctness * 100; plan days prioritize weakest first

- [ ] **Step 5: Commit**

```bash
git commit -m "feat: diagnosis, learning plan, and markdown report"
```

---

### Task 7: JSON session storage + Orchestrator

**Files:**
- Create: `ilearn/storage/sessions.py`, `ilearn/core/orchestrator.py`
- Create: `tests/test_orchestrator.py`

**Interfaces:**
- `SessionStore(root).create/save/load(session_id) -> SessionState`
- `Orchestrator.create_session(profile) -> id`
- `generate_assessment(id)`, `submit(id, answers: dict[str,str])`, `grade(id)`, `diagnose(id)`, `plan(id)`, `run_after_submit(id)`, `report(id) -> str`

- [ ] **Step 1: Integration-style test with llm=None and fixture answers**

```python
def test_full_pipeline_offline(tmp_path):
    orch = Orchestrator(store=SessionStore(tmp_path), curriculum=..., llm=None)
    sid = orch.create_session(StudentProfile(region="北京", grade=5, age=11))
    paper = orch.generate_assessment(sid)
    answers = {it.id: (it.answer_key or "") for it in paper.items}
    orch.submit(sid, answers)
    orch.run_after_submit(sid)
    md = orch.report(sid)
    assert "学习计划" in md or "Learning" in md or "计划" in md
```

- [ ] **Step 2–4: Implement + pass**

- [ ] **Step 5: Commit**

```bash
git commit -m "feat: session store and orchestrator pipeline"
```

---

### Task 8: FastAPI surface

**Files:**
- Create: `ilearn/api/app.py`, `tests/test_api.py`

**Interfaces:**
- Routes exactly as spec §7.1; app factory `create_app() -> FastAPI`

- [ ] **Step 1: Write API tests with `TestClient`**

```python
from fastapi.testclient import TestClient
from ilearn.api.app import create_app

def test_session_assessment_flow():
    c = TestClient(create_app())
    r = c.post("/sessions", json={"region": "北京", "grade": 5, "age": 11})
    sid = r.json()["session_id"]
    paper = c.post(f"/sessions/{sid}/assessment").json()
    assert len(paper["items"]) == 20
```

- [ ] **Step 2–4: Implement routes wiring Orchestrator; CORS for local Streamlit**

- [ ] **Step 5: Commit**

```bash
git commit -m "feat: FastAPI session endpoints"
```

---

### Task 9: CLI (`ilearn run` / `ilearn eval`)

**Files:**
- Create: `ilearn/cli/main.py`
- Modify: `pyproject.toml` entry point `ilearn = ilearn.cli.main:app`

- [ ] **Step 1: Implement Typer app**

`ilearn run --region 北京 --grade 5 --age 11 --answers-file optional.json`  
If no answers file: generate paper and write to `data/sessions/<id>/paper.json`, print path (offline demo can auto-fill answer_key for smoke).

`ilearn eval --fixtures data/eval/step_grading_fixtures.json` prints macro-F1 / accuracy / json_valid_rate.

- [ ] **Step 2: Manual smoke**

Run: `python -m ilearn.cli.main run --region 北京 --grade 5 --age 11 --auto-answer`  
Expected: prints report path and excerpt

- [ ] **Step 3: Commit**

```bash
git commit -m "feat: CLI run and eval commands"
```

---

### Task 10: Eval fixtures + runner

**Files:**
- Create: `data/eval/step_grading_fixtures.json` (≥12 items)
- Create: `ilearn/eval/runner.py`, `tests/test_eval_runner.py`

**Interfaces:**
- Fixture: `{id, item: AssessmentItem-dict, student_answer, expected_final_correct, expected_error_tags}`
- Metrics: final-correct accuracy; error-tag macro-F1; always 1.0 json validity for offline path

- [ ] **Step 1–4: Implement + unit test metric helpers on toy preds**

- [ ] **Step 5: Commit**

```bash
git commit -m "feat: minimal step-grading eval harness"
```

---

### Task 11: Streamlit teaching UI

**Files:**
- Create: `ilearn/web/app.py`, `ilearn/web/styles.css` (or embedded CSS)
- Create: `README.md` run instructions

**UI requirements (in scope):**
- Soft academic palette (e.g. deep teal / ink + warm paper background — **not** purple-on-white)
- Header: brand **ILearn** dominant; subtitle “小学数学学情与规划”
- Stepper: 建档 → 测评作答 → 批改与学情 → 学习计划
- Large readable stems; clear choice buttons; progress `第 i/20 题`
- Report page: mastery table, simple ability bars, day plan cards, disclaimer
- Config: `ILEARN_API_BASE` default `http://127.0.0.1:8000`

- [ ] **Step 1: Implement Streamlit multipage-via-session_state wizard calling httpx**

- [ ] **Step 2: Manual check** — start API + `streamlit run ilearn/web/app.py`; complete flow with auto or typed answers

- [ ] **Step 3: Commit**

```bash
git commit -m "feat: Streamlit teaching-themed assessment wizard"
```

---

### Task 12: README + end-to-end verification

**Files:**
- Create/update: `README.md`
- Modify: `.env.example`

- [ ] **Step 1: Document** install, `uvicorn ilearn.api.app:app`, streamlit, CLI, eval, env vars, scope/non-goals

- [ ] **Step 2: Run full offline verification**

```bash
pytest -q
python -m ilearn.cli.main eval
python -m ilearn.cli.main run --region 北京 --grade 5 --age 11 --auto-answer
```

Expected: all green; report contains 学情 + 计划

- [ ] **Step 3: Final commit**

```bash
git commit -m "docs: README and MVP verification notes"
```

---

## Spec coverage checklist

| Spec section | Task(s) |
|--------------|---------|
| 20-item mix 10/8/2 & 8/8/4 | 3 |
| Template-first math bank | 2, 3 |
| Step grading + error tags | 5, 10 |
| Diagnosis Top-5 + abilities | 6 |
| Learning plan report | 6, 7 |
| FastAPI + CLI | 8, 9 |
| Streamlit polished UI | 11 |
| Pilot curriculum + mismatch disclaimer | 2, 6 |
| Minimal eval | 10, 9 |
| JSON sessions | 7 |
| OpenAI-compatible LLM | 4, 5 |
| Non-goals respected | all (no VL/RAG/LangGraph) |

## Self-review notes

- Blueprint joint quotas avoid impossible separate sampling.
- Offline path (`llm=None` / `--auto-answer`) keeps demo and CI usable without API keys.
- UI polish called out in Task 11 to match approved spec amendment.
