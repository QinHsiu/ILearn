# Composition Phase 2a — Diagnosis & Evidence Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close TODO Phase 2a — deterministic Evidence→Mastery, lightweight evidence claims, WeaknessEvent aggregation, leech detection, practice–probe gap flags, and thicker portrait heuristics from `evidence_log` (G-05).

**Architecture:** Keep diagnosis LLM-free for mastery math. Add `ilearn/core/mastery.py` for Evidence→Mastery; extend `KnowledgeEvidence` with stable `evidence_id`; upgrade weakness storage; wire DiagnosisAgent to consume `ctx` session evidence when present. Eval gap metric lives in `ilearn/eval/gap.py` + diagnosis flag.

**Tech Stack:** Python 3.11+, pydantic v2, pytest, existing agents/core (no new deps).

## Global Constraints

- Package root: `projects/ILearn/`; import `ilearn`
- Regression: `python -m pytest tests/ -q` after every task (baseline **177**)
- Paper quotas unchanged: 20 / 10/8/2 / 8/8/4
- Controlled `error_tags` unchanged
- K12 positioning; pilot still 北京·人教 小学数学 4–6
- No LangGraph; no Qdrant; no TutorAgent (Phase 2b)
- Backward compat: new fields optional with defaults
- Source: `doc/composition/TODO.md` §H Phase 2a; OPT-023, 024, 025, 026, 074; G-05
- Branch from: `master`

## File Map

| Path | Responsibility |
|------|----------------|
| `ilearn/core/schemas.py` | `evidence_id`, `WeaknessEvent`, `DiagnosisReport.flags`, Intervention.leech |
| `ilearn/core/mastery.py` | **New** deterministic mastery update from evidence |
| `ilearn/core/evidence.py` | claim helpers / id generation |
| `ilearn/core/diagnosis.py` | WeaknessEvent agg, leech, gap flag, PortraitDimensionUpdater from evidence |
| `ilearn/agents/diagnosis.py` | Pass `evidence_log` into updaters |
| `ilearn/agents/orchestrator.py` | Ensure diagnosis sees session.evidence_log |
| `ilearn/eval/gap.py` | **New** practice–probe gap metric |
| `ilearn/agents/eval_agent.py` / CLI | optional `--gap` later; unit tests sufficient for OPT-074 |
| `doc/composition/TODO.md` | Tick Phase 2a rows |

---

### Task 1: Evidence IDs + claim helpers (OPT-024 base)

**Files:**
- Modify: `ilearn/core/schemas.py`, `ilearn/core/evidence.py`, `ilearn/agents/practice.py` (`evidence_from_grades`)
- Create: `tests/test_evidence_ids.py`

**Interfaces:**
- Produces: `KnowledgeEvidence.evidence_id: str` (default factory uuid4 hex); `make_evidence_id() -> str`; `claim_refs(evidence_ids: list[str]) -> list[str]`

- [ ] **Step 1: Write failing test**

```python
# tests/test_evidence_ids.py
from ilearn.core.evidence import make_evidence_id
from ilearn.core.schemas import KnowledgeEvidence

def test_knowledge_evidence_has_unique_evidence_id():
    a = KnowledgeEvidence(
        session_id="s1", item_id="q1", knowledge_id="k1",
        lane="probe", correct=False,
    )
    b = KnowledgeEvidence(
        session_id="s1", item_id="q1", knowledge_id="k1",
        lane="probe", correct=False,
    )
    assert a.evidence_id
    assert a.evidence_id != b.evidence_id
    assert len(make_evidence_id()) >= 8
```

- [ ] **Step 2: Run — expect fail** (`evidence_id` missing)

- [ ] **Step 3: Implement**

```python
# schemas.py
from uuid import uuid4
def _new_evidence_id() -> str:
    return uuid4().hex

class KnowledgeEvidence(BaseModel):
    evidence_id: str = Field(default_factory=_new_evidence_id)
    ...
```

```python
# evidence.py
from uuid import uuid4
def make_evidence_id() -> str:
    return uuid4().hex
```

- [ ] **Step 4: Run** `python -m pytest tests/test_evidence_ids.py tests/test_evidence_schemas.py tests/test_evidence_emission.py -v`

- [ ] **Step 5: Commit** `feat(evidence): add stable evidence_id on KnowledgeEvidence`

---

### Task 2: Deterministic Evidence→Mastery (OPT-023)

**Files:**
- Create: `ilearn/core/mastery.py`, `tests/test_mastery_from_evidence.py`
- Modify: `ilearn/core/diagnosis.py` `PortraitUpdater` to call mastery updater from evidence when provided

**Interfaces:**
- Produces:

```python
def apply_evidence_to_mastery(
    portrait: LearnerPortrait,
    events: list[KnowledgeEvidence],
    *,
    alpha: float = 0.3,
) -> LearnerPortrait: ...
# stars: probe_mastery mapped 0-5 via round(score*5); confidence = min(1.0, 0.2 + 0.1*evidence_count)
```

- [ ] **Step 1: Write failing test**

```python
# tests/test_mastery_from_evidence.py
from ilearn.core.mastery import apply_evidence_to_mastery, mastery_stars
from ilearn.core.schemas import KnowledgeEvidence, LearnerPortrait

def test_probe_correct_raises_probe_mastery_not_practice():
    portrait = LearnerPortrait(student_key="bj_g5")
    events = [
        KnowledgeEvidence(
            session_id="s1", item_id="q1", knowledge_id="frac_add_same",
            lane="probe", correct=True, confidence=1.0,
        )
    ]
    updated = apply_evidence_to_mastery(portrait, events)
    rec = updated.mastery_records["frac_add_same"]
    assert rec.probe_mastery > 0.0
    assert rec.practice_score == 0.0
    assert rec.evidence_count == 1
    assert mastery_stars(rec.probe_mastery) >= 1
```

- [ ] **Step 2: Run — expect fail**

- [ ] **Step 3: Implement mastery.py**

```python
def mastery_stars(score: float) -> int:
    return max(0, min(5, round(score * 5)))

def apply_evidence_to_mastery(portrait, events, *, alpha=0.3):
    for ev in events:
        rec = portrait.mastery_records.get(ev.knowledge_id) or MasteryRecord()
        observed = 1.0 if ev.correct else 0.0
        observed *= ev.confidence
        if ev.lane == "probe":
            rec.probe_mastery = _ema(rec.probe_mastery, observed, alpha)
            rec.last_probe_at = ev.created_at
        else:
            rec.practice_score = _ema(rec.practice_score, observed, alpha)
        rec.evidence_count += 1
        portrait.mastery_records[ev.knowledge_id] = rec
        # keep legacy float mirror for probe-or-practice max
        portrait.knowledge_state[ev.knowledge_id] = max(rec.practice_score, rec.probe_mastery)
    return portrait
```

Wire `PortraitUpdater.update(..., evidence: list[KnowledgeEvidence] | None = None)` — if evidence provided, call `apply_evidence_to_mastery` instead of/in addition to grade-only EMA (prefer evidence path when non-empty).

- [ ] **Step 4: Run** `python -m pytest tests/test_mastery_from_evidence.py tests/test_mastery_lanes.py tests/test_agents_diagnosis.py -v`

- [ ] **Step 5: Commit** `feat(diagnosis): deterministic Evidence→Mastery updates`

---

### Task 3: WeaknessEvent structured log (OPT-025)

**Files:**
- Modify: `ilearn/core/schemas.py`, `ilearn/core/diagnosis.py`
- Create: `tests/test_weakness_events.py`

**Interfaces:**
- Produces:

```python
class WeaknessEvent(BaseModel):
    knowledge_id: str
    step_index: int | None = None
    error_tag: ErrorTag | None = None
    confidence: float = 1.0
    evidence_id: str | None = None
    session_id: str = ""
    created_at: datetime = Field(default_factory=utc_now)

# LearnerPortrait.weakness_events: list[WeaknessEvent] = []
# keep weakness_log for backward compat; PortraitUpdater appends both, aggregates duplicates by knowledge_id within same session
```

- [ ] **Step 1: Write failing test**

```python
def test_repeated_errors_same_knowledge_collapse_to_one_weakness_event_per_session():
    # two incorrect grades same knowledge_id same session → one WeaknessEvent (latest error_tag wins) or count field
    ...
```

Implement aggregation: for same `(session_id, knowledge_id)`, keep single WeaknessEvent with max confidence and dominant error_tag; still allow multiple sessions.

- [ ] **Step 2–5: Implement + commit** `feat(diagnosis): add WeaknessEvent with per-session aggregation`

---

### Task 4: Leech detection (OPT-026)

**Files:**
- Modify: `ilearn/core/diagnosis.py`, `ilearn/core/schemas.py` (`Intervention.leech: bool = False`)
- Create: `tests/test_leech_detection.py`

**Interfaces:**
- Produces: `is_leech(portrait, knowledge_id, *, threshold=3) -> bool` — count incorrect evidence for kid ≥ threshold
- Diagnoser / PortraitUpdater marks interventions with `leech=True` and boosts priority (lower number = higher priority)

- [ ] **Step 1: Write failing test**

```python
def test_three_probe_failures_mark_leech_on_intervention():
    # build portrait with 3 incorrect probe evidence for frac_add_same
    # run diagnose or rank interventions → leech True and appears in top interventions
    ...
```

- [ ] **Step 2–5: Implement + commit** `feat(diagnosis): detect leech knowledge nodes and boost priority`

---

### Task 5: Evidence claims on DiagnosisReport (OPT-024 complete)

**Files:**
- Modify: `ilearn/core/schemas.py` (`DiagnosisReport.evidence_refs: list[str] = []`, `Intervention.evidence_ids: list[str] = []`)
- Modify: `ilearn/core/diagnosis.py` Diagnoser to attach evidence ids from session evidence matching knowledge_id
- Modify: `ilearn/agents/diagnosis.py` / orchestrator to pass evidence_log
- Create: `tests/test_diagnosis_evidence_refs.py`

**Interfaces:**
- Consumes: `list[KnowledgeEvidence]`
- Produces: report.interventions[*].evidence_ids non-empty when evidence exists for that knowledge_id

- [ ] **Step 1: Write failing test**

```python
def test_intervention_includes_evidence_ids():
    ...
```

- [ ] **Step 2–5: Implement Diagnoser.diagnose(..., evidence=None); commit** `feat(diagnosis): attach evidence_ids to interventions`

---

### Task 6: practice–probe gap flag (OPT-074)

**Files:**
- Create: `ilearn/eval/gap.py`, `tests/test_practice_probe_gap.py`
- Modify: `ilearn/core/schemas.py` (`DiagnosisReport.flags: list[str] = []`)
- Modify: `ilearn/core/diagnosis.py` to set flag `practice_probe_gap` when practice_score - probe_mastery > 0.25 for any knowledge

**Interfaces:**
- Produces: `compute_gap(practice: float, probe: float) -> float`; `gap_flag(portrait, threshold=0.25) -> list[str]`

- [ ] **Step 1: Write failing test**

```python
def test_gap_flag_when_practice_exceeds_probe():
    from ilearn.eval.gap import gap_exceeds
    assert gap_exceeds(practice=0.9, probe=0.4, threshold=0.25) is True
    assert gap_exceeds(practice=0.5, probe=0.4, threshold=0.25) is False
```

- [ ] **Step 2–5: Wire into diagnosis; commit** `feat(diagnosis): flag practice–probe mastery gaps`

---

### Task 7: Portrait dimensions from evidence_log (G-05)

**Files:**
- Modify: `ilearn/core/diagnosis.py` `PortraitDimensionUpdater`
- Create: `tests/test_portrait_from_evidence.py`

**Interfaces:**
- Consumes: `list[KnowledgeEvidence]`
- Produces: higher `behavioral.hint_dependency` when many high-hint evidence events; metacognitive gap from practice vs probe evidence rates

- [ ] **Step 1: Write failing test**

```python
def test_high_hint_evidence_raises_behavioral_from_evidence_log():
    portrait = LearnerPortrait(student_key="x")
    events = [
        KnowledgeEvidence(
            session_id="s", item_id="q1", knowledge_id="k",
            lane="practice", correct=True, hint_level="high",
        )
        for _ in range(3)
    ]
    updated = PortraitDimensionUpdater.apply_from_evidence(portrait, events)
    assert updated.dimensions.behavioral.get("hint_dependency", 0) > 0.2
```

- [ ] **Step 2–5: Implement `apply_from_evidence`; DiagnosisAgent calls it when evidence_log present; commit** `feat(diagnosis): enrich portrait dimensions from evidence_log`

---

### Task 8: Orchestrator wiring + E2E + TODO ticks

**Files:**
- Modify: `ilearn/agents/orchestrator.py` (pass `session.evidence_log` into diagnosis context — via `ctx.metadata["evidence_log"]` or extend AgentContext)
- Prefer extend `AgentContext` with `evidence_log: list[KnowledgeEvidence] = []` if clean
- Create: `tests/test_e2e_phase2a_diagnosis.py`
- Modify: `doc/composition/TODO.md` mark OPT-023/024/025/026/074, G-05 done
- Modify: README one line under diagnosis capabilities if needed

**Interfaces:**
- After `run_after_submit`, portrait.mastery_records populated from evidence; interventions may have evidence_ids; flags may include gap

- [ ] **Step 1: Write E2E failing test**

```python
def test_e2e_diagnosis_uses_evidence_log(tmp_path):
    # full offline loop; assert evidence_log and mastery_records and (evidence_ids or flags schema present)
    ...
```

- [ ] **Step 2–5: Wire AgentContext.evidence_log; full suite; commit** `feat(orchestrator): feed evidence_log into diagnosis Phase2a`

---

## Self-Review

| TODO / OPT | Task |
|------------|------|
| OPT-024 ids + claims | 1, 5 |
| OPT-023 | 2 |
| OPT-025 | 3 |
| OPT-026 | 4 |
| OPT-074 | 6 |
| G-05 | 7 |
| Wiring / E2E / TODO.md | 8 |

Out of scope: Phase 2b Tutor/Hint, 2c Qdrant, 2d orchestrator budget, Eval HF benchmarks.

---

**Plan complete and saved to `docs/superpowers/plans/2026-08-10-composition-phase2a-diagnosis.md`.**
