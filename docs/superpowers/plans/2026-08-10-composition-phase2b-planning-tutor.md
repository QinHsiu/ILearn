# Composition Phase 2b — Planning & Tutoring Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deliver Phase 2b from `TODO.md` §H — dynamic Hint Ladder, frustration-aware replan, versioned plans, three-part intervention copy, KC-typed tasks, and a minimal TutorAgent Socratic state machine.

**Architecture:** Keep Python orchestrator (no LangGraph). Add `ilearn/core/hints.py` for ladder logic; extend `Planner`/`PlanningAgent` for replan + versions + templates; new `ilearn/agents/tutor.py` with offline rule-based Socratic steps (LLM optional later). OPT-013 full taxonomy expansion is **out of scope** — Hint Ladder maps existing five `error_tags`.

**Tech Stack:** Python 3.11+, pydantic v2, pytest, existing agents stack.

## Global Constraints

- Branch from: `feature/ilearn-phase2a-diagnosis` tip (includes Phase 2a)
- Baseline tests: **198**
- Quotas unchanged: 20 / 10/8/2 / 8/8/4
- `error_tags` set unchanged (no OPT-013 expansion)
- K12 product copy; pilot 北京·人教 小学数学 4–6
- Hints must **never** include `answer_key` verbatim
- No LangGraph / Qdrant
- Regression: `python -m pytest tests/ -q` after each task

## File Map

| Path | Responsibility |
|------|----------------|
| `ilearn/core/hints.py` | Hint ladder levels from error_tag + fail streak |
| `ilearn/agents/practice.py` | Optional hint payload when incorrect |
| `ilearn/core/schemas.py` | PlanVersion, PlanStatus, TutorState, LearningPlanReport.version fields |
| `ilearn/core/planning.py` | replan(), three-part markdown, KC task text |
| `ilearn/agents/planning.py` | Frustration trigger + plan history |
| `ilearn/agents/tutor.py` | **New** TutorAgent state machine |
| `ilearn/agents/orchestrator.py` | Wire replan + tutor entry points (minimal) |
| `data/pilot/knowledge.json` | Optional `kc_type` field if missing → default in code |
| `doc/composition/TODO.md` | Tick Phase 2b rows |

---

### Task 1: Hint Ladder core (OPT-014)

**Files:**
- Create: `ilearn/core/hints.py`, `tests/test_hint_ladder.py`
- Modify: `ilearn/agents/practice.py` (attach `hint_text` on incorrect grades via payload metadata or GradeResult extension)

**Interfaces:**
- Produces:

```python
def hint_for_error(error_tag: str | None, fail_streak: int = 0) -> tuple[HintLevel, str]:
    """Return (level, hint_text). Level escalates with fail_streak; never includes final answer."""
```

Mapping (existing tags):
- `calc_error` → low: "检查运算过程中的进位/通分"
- `misread` → low: "再读一遍题目条件"
- `concept_gap` → medium: "回顾相关定义与例题结构"
- `method_wrong` → high: "换一种列式思路，先写已知再求未知"
- `incomplete` → medium: "补全中间步骤后再写结论"
- fail_streak ≥ 3 → force level `high` and append "先对照例题步骤，不要直接看答案"

- [ ] **Step 1: Write failing test**

```python
# tests/test_hint_ladder.py
from ilearn.core.hints import hint_for_error

def test_hint_never_contains_numeric_answer_key_pattern():
    level, text = hint_for_error("calc_error", fail_streak=0)
    assert level == "low"
    assert "答案" not in text or "不要直接看答案" in hint_for_error("calc_error", 3)[1]

def test_fail_streak_escalates_to_high():
    level, _ = hint_for_error("misread", fail_streak=3)
    assert level == "high"

def test_hint_does_not_embed_answer_key():
    _, text = hint_for_error("concept_gap", 0)
    assert "answer_key" not in text.casefold()
```

- [ ] **Step 2: Run — expect fail**

- [ ] **Step 3: Implement hints.py; PracticeAgent on incorrect grade sets `grade.hint_level_suggestion` from ladder and stores hint in `result.payload["hints"]` dict item_id→text**

- [ ] **Step 4: Run** `python -m pytest tests/test_hint_ladder.py tests/test_agents_practice.py -v`

- [ ] **Step 5: Commit** `feat(practice): add dynamic three-level hint ladder`

---

### Task 2: Plan versioning draft/approved/superseded (OPT-032)

**Files:**
- Modify: `ilearn/core/schemas.py`, `ilearn/agents/planning.py`, `ilearn/agents/orchestrator.py`, `ilearn/storage` if needed
- Create: `tests/test_plan_versions.py`

**Interfaces:**

```python
PlanStatus = Literal["draft", "approved", "superseded"]

class PlanVersion(BaseModel):
    version: int = 1
    status: PlanStatus = "draft"
    plan: LearningPlanReport
    created_at: datetime = Field(default_factory=utc_now)

# SessionState.plan_history: list[PlanVersion] = []
# LearningPlanReport.version: int = 1
# LearningPlanReport.status: PlanStatus = "draft"
```

When PlanningAgent produces a new plan and session already has `plan`, mark previous as `superseded`, append to `plan_history`, set new as `draft` version+1.

- [ ] **Step 1: Write failing test**

```python
def test_replan_supersedes_previous_plan(tmp_path):
    # create session, plan once, plan again via agent → history len>=1, old status superseded
    ...
```

- [ ] **Step 2–5: Implement; commit** `feat(planning): version plans with draft/approved/superseded`

---

### Task 3: Frustration-aware replan (OPT-031)

**Files:**
- Create: `ilearn/core/replan.py`, `tests/test_frustration_replan.py`
- Modify: `ilearn/agents/planning.py`, `ilearn/core/planning.py`

**Interfaces:**

```python
def should_replan(portrait: LearnerPortrait, diagnosis: DiagnosisReport) -> bool:
    # True if emotional.frustration >= 0.3 OR behavioral.hint_dependency >= 0.4
    # OR flags contain practice_probe_gap

def replan_adjustments(diagnosis: DiagnosisReport) -> dict:
    # returns {"easier_focus": True, "confidence_task": "先做一道已掌握巩固题"}
```

Planner: if `should_replan`, prepend day-1 task "信心重建：回顾已掌握例题" and prefer easier weak nodes (higher score_rate among weak).

- [ ] **Step 1: Write failing test**

```python
def test_should_replan_on_high_frustration():
    portrait = LearnerPortrait(student_key="x")
    portrait.dimensions.emotional["frustration"] = 0.5
    assert should_replan(portrait, DiagnosisReport()) is True

def test_replan_plan_includes_confidence_rebuild():
    # Planner.plan with frustrated portrait → day1 tasks contain 信心重建
    ...
```

- [ ] **Step 2–5: Implement; commit** `feat(planning): frustration-aware replan adjustments`

---

### Task 4: Three-part intervention template (OPT-033)

**Files:**
- Modify: `ilearn/core/planning.py` markdown renderer / diagnosis report section
- Create: `tests/test_three_part_intervention.py`

**Interfaces:**
- Plan markdown (or diagnosis section appended by PlanningAgent) must contain headings:
  - `### 当前认知`
  - `### 预测难点`
  - `### 教学方案`

Fill from top intervention + dominant error_tag labels.

- [ ] **Step 1: Write failing test** asserting all three headings in `plan.markdown`

- [ ] **Step 2–5: Implement; commit** `feat(planning): add three-part intervention recommendation block`

---

### Task 5: KC-type task wording (OPT-034)

**Files:**
- Modify: `ilearn/core/planning.py`, optionally `data/pilot/knowledge.json`
- Create: `tests/test_kc_task_wording.py`

**Interfaces:**

```python
def task_for_kc(kc_type: str, knowledge_name: str) -> str:
    # fact → f"检索练习：默写或辨认「{name}」关键结论"
    # skill → f"变式练习：完成「{name}」同类题 2 道"
    # principle → f"解释为什么：用自己的话说明「{name}」的道理"
    # default → skill
```

Resolve `kc_type` from knowledge node: add optional field `kc_type` on KnowledgeNode default `"skill"`; if JSON lacks field, infer from ability_tags (`记忆`→fact, `理解`→principle, else skill).

- [ ] **Step 1: Write failing unit tests for three wordings**

- [ ] **Step 2–5: Use in `_build_days` task strings; commit** `feat(planning): KC-type driven practice task wording`

---

### Task 6: TutorAgent Socratic state machine (OPT-060)

**Files:**
- Create: `ilearn/agents/tutor.py`, `tests/test_tutor_agent.py`
- Modify: `ilearn/core/schemas.py` (`TutorPhase` literal / `TutorTurn`)
- Modify: `ilearn/agents/__init__.py` export

**Interfaces:**

```python
TutorPhase = Literal["locate_gap", "hint_1", "hint_2", "retry", "explain", "done"]

class TutorAgent:
    name = "tutor"
    def start(self, item: AssessmentItem, error_tag: str | None) -> TutorTurn: ...
    def step(self, state: TutorPhase, user_message: str, item: AssessmentItem) -> TutorTurn: ...
```

Transitions:
- start → `locate_gap` (ask which step is unclear; no answer)
- locate_gap → `hint_1` (use hint_for_error level low/medium)
- hint_1 → `hint_2` (escalate)
- hint_2 → `retry` (ask student to retry step)
- retry → `explain` if still wrong keywords / empty; else `done`
- explain → pedagogical explanation **without** `answer_key`

Pedagogy regression: every TutorTurn.message must not contain `item.answer_key` when answer_key set.

- [ ] **Step 1: Write failing tests**

```python
def test_tutor_start_does_not_leak_answer():
    item = AssessmentItem(..., answer_key="20", ...)
    turn = TutorAgent().start(item, "calc_error")
    assert "20" not in turn.message

def test_tutor_escalates_locate_to_hint1():
    ...
```

- [ ] **Step 2–5: Implement; commit** `feat(tutor): add Socratic TutorAgent state machine`

---

### Task 7: Wire tutor + replan into orchestrator surfaces

**Files:**
- Modify: `ilearn/agents/orchestrator.py` — methods `replan(session_id)` and `tutor_start(session_id, item_id)`
- Modify: `ilearn/api/app.py` — optional routes OR skip API if time — prefer CLI:
- Modify: `ilearn/cli/main.py` — `ilearn tutor turn` minimal OR document agent-only
- Create: `tests/test_e2e_phase2b.py`

**Minimal wiring (YAGNI):**
- `MultiAgentOrchestrator.request_replan(sid)` → PlanningAgent with portrait → plan versioning
- Do **not** require full Tutor in main E2E loop; E2E asserts: replan creates superseded history; TutorAgent unit already covered

- [ ] **Step 1: Write failing orchestrator replan test**

```python
def test_request_replan_appends_plan_history(tmp_path):
    ...
```

- [ ] **Step 2–5: Implement; commit** `feat(orchestrator): expose request_replan with plan versioning`

---

### Task 8: Docs + TODO + README + full regression

**Files:**
- `doc/composition/TODO.md` — mark OPT-014, 031–034, 060 done
- `README.md` — mention Hint Ladder + TutorAgent + plan versions
- Update roadmap file status for Phase 2b

- [ ] **Step 1–5: Update docs; `python -m pytest tests/ -q` expect ≥198; commit** `docs: mark Phase 2b planning/tutor items done`

---

## Self-Review

| ID | Task |
|----|------|
| OPT-014 | 1 |
| OPT-032 | 2 |
| OPT-031 | 3 |
| OPT-033 | 4 |
| OPT-034 | 5 |
| OPT-060 | 6 |
| Wiring | 7 |
| Docs | 8 |

**Deferred:** OPT-013 tag taxonomy expansion; full API tutor routes; LangGraph.

---

**Plan complete and saved to `docs/superpowers/plans/2026-08-10-composition-phase2b-planning-tutor.md`.**
