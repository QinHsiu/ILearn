# Composition Phase 2d — Orchestration Quality Design

> **Status:** Approved (approach A, 2026-08-10)  
> **Goal:** Close TODO Phase 2d — context budget, agent decision contract, phase quality gates, PendingQuestion answer binding, agent capability whitelist.  
> **Baseline:** `master` @ Phase 2c（258 tests）  
> **IDs:** OPT-050, OPT-051, OPT-052, OPT-015, OPT-016

---

## 1. Scope

| ID | Deliverable | Depth |
|----|-------------|-------|
| OPT-050 | `trim_context` char/field budget | Lightweight（无 tokenizer） |
| OPT-051 | `AgentDecision` + `session.decision_log` | Observable trail |
| OPT-052 | ASSESS / DIAGNOSE / PLAN schema gate | retry 1 → degrade |
| OPT-015 | `PendingQuestion` bind expected_answer | anti cross-turn mix-up |
| OPT-016 | per-Agent `allowed_writes` | unauthorized write raises |

**Out of this phase:** OPT-053 intent layer; full Tutor API/UI; real tokenizers; LangGraph.

---

## 2. Architecture

```text
Orchestrator method
  → trim_context(ctx)                    # OPT-050
  → assert_capability(agent, writes)     # OPT-016
  → run agent (optional quality_gate)    # OPT-052
  → append AgentDecision                 # OPT-051
  → bind/clear PendingQuestion           # OPT-015 (assess / submit)
  → persist SessionState
```

No new pip dependencies. Prefer small modules under `ilearn/core/` + thin orchestrator wiring.

---

## 3. Components

### 3.1 OPT-050 — Context budget

- Module: `ilearn/core/context_budget.py`
- `trim_context(ctx: AgentContext, *, max_chars: int = 12000, max_evidence: int = 40) -> AgentContext`
- Keep `profile` intact; keep `paper` / `diagnosis` / `plan` references as-is when present
- Truncate `evidence_log` to last `max_evidence`
- If serialized rough size still exceeds `max_chars`, drop oldest grades/answers tails and set `metadata["context_summary"]` string (counts + last phase)

### 3.2 OPT-051 — Decision contract

- Schema: `AgentDecision` in `schemas.py` — `agent`, `phase`, `reason`, `evidence_ids`, `ok`, `degraded`
- `SessionState.decision_log: list[AgentDecision]`
- Orchestrator appends one decision per major transition (assess, grade, diagnose, plan, replan, tutor_start)

### 3.3 OPT-052 — Quality gate

- Module: `ilearn/core/quality_gate.py`
- `run_with_quality_gate(fn, validate, *, max_retries=1) -> (result, degraded: bool)`
- Validators: paper has items; diagnosis has mastery or interventions; plan has markdown/tasks
- On failure after retry: return minimal degrade payload + `ok=False`, `degraded=True` on decision

### 3.4 OPT-015 — PendingQuestion

- Schema: `PendingQuestion(question_id, expected_answer, paper_id, created_at?)`
- `SessionState.pending_questions: list[PendingQuestion]`
- On `generate_assessment`: populate from paper items (`expected_answer` / answer key field)
- On `submit`: reject answers whose ids are not in pending set; optional clear after grade

### 3.5 OPT-016 — Capability whitelist

- Module: `ilearn/agents/capabilities.py`
- Map agent name → frozenset of write keys (`paper`, `grades`, `diagnosis`, `portrait`, `plan`, …)
- `assert_writes_allowed(agent_name, keys)` raises `PermissionError` on violation
- Orchestrator checks intended writes before applying agent payload

---

## 4. Testing & docs

- Unit tests per OPT + `tests/test_e2e_phase2d.py`
- Update `VERSION.md`, `doc/composition/TODO.md` §H, README test count if changed
- Branch: `feature/ilearn-phase2d-orchestration`

---

## 5. Acceptance

- Long evidence_log trim keeps profile + recent evidence; sets summary when needed
- `decision_log` non-empty after diagnose/plan
- Forced invalid agent output triggers one retry then degrade
- Submit with foreign question_id fails
- Assessment agent cannot “write” portrait under capability check
