# Composition Phase 2d — Orchestration Quality Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close Phase 2d — lightweight context budget, AgentDecision trail, phase quality gate (retry→degrade), PendingQuestion answer binding, and agent capability whitelist.

**Architecture:** Small modules (`context_budget`, `quality_gate`, `capabilities`) + schema fields on `SessionState`; `MultiAgentOrchestrator` wires trim → capability check → gated run → decision append → pending bind. No new pip deps.

**Tech Stack:** Python 3.11+, pydantic v2, pytest, stdlib only.

## Global Constraints

- Branch from: `master` (Phase 2c merged; 258 tests) → `feature/ilearn-phase2d-orchestration`
- No new third-party packages
- OPT-050 = char/field budget only (no tokenizer)
- Do not break existing e2e phase1/2a/2b/2c
- Update `VERSION.md` + `doc/composition/TODO.md` in final task
- Regression: `python -m pytest tests/ -q` after each task
- PowerShell: use `;` not `&&`

## File Map

| Path | Responsibility |
|------|----------------|
| `ilearn/core/context_budget.py` | **New** `trim_context` |
| `ilearn/core/quality_gate.py` | **New** retry + degrade helpers |
| `ilearn/agents/capabilities.py` | **New** whitelist + assert |
| `ilearn/core/schemas.py` | `AgentDecision`, `PendingQuestion`, session fields |
| `ilearn/agents/orchestrator.py` | Wire all five OPT |
| `ilearn/agents/protocol.py` | optional metadata keys docs only if needed |
| `VERSION.md`, `doc/composition/TODO.md`, `README.md` | docs / counts |

---

### Task 1: AgentDecision + PendingQuestion schemas (OPT-051 / OPT-015 base)

**Files:**
- Modify: `ilearn/core/schemas.py`
- Test: `tests/test_phase2d_schemas.py`

**Interfaces:**
- Produces:

```python
class AgentDecision(BaseModel):
    agent: str
    phase: SessionPhase
    reason: str = ""
    evidence_ids: list[str] = Field(default_factory=list)
    ok: bool = True
    degraded: bool = False

class PendingQuestion(BaseModel):
    question_id: str
    expected_answer: str
    paper_id: str | None = None

# SessionState additions:
# decision_log: list[AgentDecision] = []
# pending_questions: list[PendingQuestion] = []
```

- [ ] **Step 1: Write failing tests**

```python
from ilearn.core.schemas import AgentDecision, PendingQuestion, SessionPhase, SessionState, StudentProfile

def test_agent_decision_defaults():
    d = AgentDecision(agent="diagnosis", phase=SessionPhase.DIAGNOSE, reason="ok")
    assert d.ok is True and d.degraded is False and d.evidence_ids == []

def test_session_has_decision_and_pending_lists():
    s = SessionState(
        session_id="s1",
        profile=StudentProfile(region="beijing", grade=5, age=11),
    )
    assert s.decision_log == []
    assert s.pending_questions == []
    s.pending_questions.append(
        PendingQuestion(question_id="q1", expected_answer="42", paper_id="p1")
    )
    assert s.pending_questions[0].expected_answer == "42"
```

- [ ] **Step 2: Run tests — expect FAIL (classes missing)**

Run: `python -m pytest tests/test_phase2d_schemas.py -q`

- [ ] **Step 3: Implement schemas on `SessionState`**

- [ ] **Step 4: Run tests — PASS**

- [ ] **Step 5: Commit**

```bash
git add ilearn/core/schemas.py tests/test_phase2d_schemas.py
git commit -m "feat(schemas): add AgentDecision and PendingQuestion for Phase2d"
```

---

### Task 2: Context budget trim (OPT-050)

**Files:**
- Create: `ilearn/core/context_budget.py`
- Test: `tests/test_context_budget.py`
- Modify: `ilearn/agents/orchestrator.py` — call `trim_context` inside `_ctx` before return (or wrap callers)

**Interfaces:**
- Produces:

```python
def trim_context(
    ctx: AgentContext,
    *,
    max_chars: int = 12000,
    max_evidence: int = 40,
) -> AgentContext:
    """Return a new AgentContext with truncated evidence/lists and optional summary."""
```

Rough size = `len(repr(profile)) + sum(len(e.model_dump_json()) for e in evidence_log)` (or equivalent). Keep last `max_evidence` evidence entries. If still over budget, truncate `grades`/`answers` from the front (oldest) and set `metadata["context_summary"]` like `"trimmed evidence=40 grades=N"`.

- [ ] **Step 1: Failing test** — 80 evidence events → trim to 40; profile unchanged; optional summary when forced

```python
def test_trim_keeps_recent_evidence_and_profile():
    # build AgentContext with profile + 80 KnowledgeEvidence
    out = trim_context(ctx, max_evidence=40)
    assert len(out.evidence_log) == 40
    assert out.profile.grade == ctx.profile.grade
    assert out.evidence_log[-1].evidence_id == ctx.evidence_log[-1].evidence_id
```

- [ ] **Step 2: FAIL then implement then PASS**

- [ ] **Step 3: Wire `MultiAgentOrchestrator._ctx` to return `trim_context(...)`**

- [ ] **Step 4: Full suite green**

- [ ] **Step 5: Commit** `feat(orchestrator): trim AgentContext by char/evidence budget`

---

### Task 3: Capability whitelist (OPT-016)

**Files:**
- Create: `ilearn/agents/capabilities.py`
- Test: `tests/test_capabilities.py`
- Modify: `ilearn/agents/orchestrator.py` — before applying payload keys, `assert_writes_allowed`

**Interfaces:**

```python
AGENT_CAPABILITIES: dict[str, frozenset[str]] = {
    "assessment": frozenset({"paper"}),
    "practice": frozenset({"grades", "evidence"}),
    "diagnosis": frozenset({"diagnosis", "portrait"}),
    "planning": frozenset({"plan", "plan_history_append"}),
    "curriculum": frozenset({"citations"}),
    "tutor": frozenset({"tutor_turn"}),
}

def assert_writes_allowed(agent_name: str, write_keys: set[str]) -> None:
    allowed = AGENT_CAPABILITIES.get(agent_name, frozenset())
    bad = write_keys - allowed
    if bad:
        raise PermissionError(f"{agent_name} cannot write {sorted(bad)}")
```

- [ ] **Step 1: Test assessment cannot write portrait; diagnosis can**

- [ ] **Step 2: Implement + call from orchestrator when applying known payload keys**

- [ ] **Step 3: Commit** `feat(agents): enforce per-agent write capability whitelist`

---

### Task 4: Quality gate retry → degrade (OPT-052)

**Files:**
- Create: `ilearn/core/quality_gate.py`
- Test: `tests/test_quality_gate.py`
- Modify: `orchestrator.generate_assessment` / `diagnose` / `plan` to wrap agent `run`

**Interfaces:**

```python
def run_with_quality_gate(run_once, validate, *, max_retries: int = 1):
    """Call run_once; if validate(result) fails, retry up to max_retries; then return (result, degraded)."""
```

Validators:
- assess: `payload["paper"]` is AssessmentPaper with `len(items) >= 1`
- diagnose: diagnosis report non-None with mastery or interventions
- plan: plan report has non-empty markdown or tasks

Degrade helpers return minimal valid empty-ish structures already used elsewhere, with decision `degraded=True`.

- [ ] **Step 1: Unit test** — fake `run_once` fails validate once then succeeds → `degraded=False`, call_count==2

- [ ] **Step 2: Unit test** — always fail → `degraded=True` after retries

- [ ] **Step 3: Wire assess/diagnose/plan**

- [ ] **Step 4: Commit** `feat(orchestrator): phase quality gate with one retry then degrade`

---

### Task 5: Decision log wiring (OPT-051)

**Files:**
- Modify: `ilearn/agents/orchestrator.py`
- Test: `tests/test_decision_log.py`

**Interfaces:**
- Helper `_record_decision(session, agent, phase, reason, *, ok=True, degraded=False, evidence_ids=None)`

After assess/grade/diagnose/plan/replan/tutor_start append `AgentDecision`.

- [ ] **Step 1: E2E-ish** — create session → assess → grade → diagnose → plan; `len(decision_log) >= 3` and last agent is planning

- [ ] **Step 2: Implement + PASS**

- [ ] **Step 3: Commit** `feat(orchestrator): append AgentDecision trail to session`

---

### Task 6: PendingQuestion bind on assess / submit (OPT-015)

**Files:**
- Modify: `ilearn/agents/orchestrator.py` (`generate_assessment`, `submit`)
- Test: `tests/test_pending_questions.py`

**Interfaces:**
- After paper created: `pending_questions = [PendingQuestion(question_id=i.id, expected_answer=i.answer_key or "", paper_id=session.session_id) for i in paper.items]`
- `submit`: if `pending_questions` non-empty, every answer key must be in `{pq.question_id}`; else `ValueError`
- After successful grade, optionally clear pending (or keep until next assess — prefer clear on next `generate_assessment` overwrite)

- [ ] **Step 1: Test** submit unknown id raises; valid ids pass

- [ ] **Step 2: Implement**

- [ ] **Step 3: Commit** `feat(session): bind PendingQuestion answers to block cross-item submit`

---

### Task 7: E2E + docs closeout

**Files:**
- Create: `tests/test_e2e_phase2d.py`
- Modify: `VERSION.md`, `doc/composition/TODO.md`, `README.md` (test count)

- [ ] **Step 1: E2E** covers trim + decision_log + pending + capability (indirect) + quality gate happy path

- [ ] **Step 2: Mark OPT-050/051/052/015/016 done in TODO; Phase 2d ✅ in §H; refresh VERSION 近期 Todo / 更新日志**

- [ ] **Step 3: `python -m pytest tests/ -q` — all green**

- [ ] **Step 4: Commit** `docs: mark Phase 2d orchestration items done`

---

## Self-review

- Spec coverage: all five OPT have tasks ✅
- No tokenizer / no OPT-053 ✅
- Types consistent: `AgentDecision`, `PendingQuestion`, `trim_context`, `assert_writes_allowed`, `run_with_quality_gate` ✅
