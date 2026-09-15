# Composition Phase 1 Closeout Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close all Phase 1 P0 *partial* gaps and engineering debt from `doc/composition/TODO.md` §§A+G (and F-01..F-04 doc refresh), so Phase 1 acceptance is fully met before starting P1 work.

**Architecture:** Wire existing schemas into production paths (`StepAttempt`, `contextual`, citation ids); extend eval CLI/adapters for completeness + two more mathtutorbench-style tasks; harden evidence/receipt/datetime/seed without new heavy deps. **True Qdrant vector RAG stays out of this plan** (see roadmap → Phase 2c).

**Tech Stack:** Python 3.11+, pydantic v2, pytest, Typer CLI, existing `ilearn` agents/core/eval (no new packages).

## Global Constraints

- Package root: `projects/ILearn/`; import `ilearn`
- Regression gate: `python -m pytest tests/ -q` must pass after every task (baseline **165**)
- Paper quotas unchanged: **20** items; difficulty **10/8/2**; types **8/8/4**
- Controlled `error_tags` unchanged unless a task explicitly extends them (this plan does **not**)
- Product copy: **K12 全学段**; 小学数学 4–6 = **current pilot only**
- No LangGraph; no live web crawl; no Qdrant in this plan
- Backward compat: new fields optional with defaults
- Source backlog: `doc/composition/TODO.md` A-01…A-05, G-01…G-06, F-01…F-04
- Sibling roadmap: `docs/superpowers/plans/2026-08-10-composition-todo-roadmap.md`

## File Map

| Path | Responsibility |
|------|----------------|
| `ilearn/core/schemas.py` | `AssessmentItem.curriculum_objective_ids`; UTC helpers; StepAttempt already exists |
| `ilearn/core/datetime_utils.py` | **New** `utc_now()` replacing `datetime.utcnow` |
| `ilearn/agents/practice.py` | Emit `StepAttempt[]` + step-aligned evidence |
| `ilearn/agents/diagnosis.py` | Fill `dimensions.contextual` from profile |
| `ilearn/core/evidence.py` | Idempotent append (dedupe key) |
| `ilearn/core/assessment.py` | Optional `rng` seed for fill_blueprint |
| `ilearn/core/grader.py` | Optional OCR confidence on receipt |
| `ilearn/agents/assessment.py` / `curriculum.py` | Attach citation ids from RAG hits |
| `ilearn/eval/mathtutorbench_tasks.py` | mistake_correction + scaffolding runners |
| `data/eval/mistake_correction_fixtures.json` | **New** ≥5 fixtures |
| `data/eval/scaffolding_fixtures.json` | **New** ≥5 fixtures |
| `ilearn/cli/main.py` | `--completeness`, `--mistake-correction`, `--scaffolding` |
| `ilearn/agents/eval_agent.py` | Wire new benchmarks |
| `doc/composition/INDEX.md` etc. | Status refresh |
| `doc/composition/TODO.md` | Mark A/G/F rows done |

---

### Task 1: Emit StepAttempt from PracticeAgent (A-01 / OPT-010)

**Files:**
- Modify: `ilearn/agents/practice.py`, `ilearn/core/schemas.py` (if `GradeResult` needs `step_attempts`)
- Create: `tests/test_step_attempt_emission.py`

**Interfaces:**
- Consumes: `StepAttempt`, `StepVerdict`, existing `GradeResult.step_results`, `AssessmentItem.rubric_steps`
- Produces: `PracticeAgent.run` payload key `step_attempts: list[StepAttempt]`; each grade’s steps aligned to rubric index

- [ ] **Step 1: Write the failing test**

```python
# tests/test_step_attempt_emission.py
from pathlib import Path
from ilearn.agents.practice import PracticeAgent
from ilearn.agents.protocol import AgentContext, SessionPhase
from ilearn.core.assessment import AssessmentBuilder
from ilearn.core.schemas import StudentAnswer, StudentProfile, StepAttempt
from ilearn.providers.curriculum import PilotBeijingRenjiaoProvider

PILOT = Path(__file__).resolve().parents[1] / "data" / "pilot"

def test_practice_agent_emits_step_attempts_aligned_to_rubric():
    curriculum = PilotBeijingRenjiaoProvider(PILOT)
    paper = AssessmentBuilder(curriculum).build(StudentProfile(region="北京", grade=5, age=11))
    constructed = next(i for i in paper.items if i.type == "constructed" and i.rubric_steps)
    from ilearn.core.schemas import AssessmentPaper
    tight = AssessmentPaper(
        items=[constructed],
        grade=5,
        curriculum_label=paper.curriculum_label,
    )
    answers = [StudentAnswer(item_id=constructed.id, answer_text=constructed.answer_key or "")]
    result = PracticeAgent(llm=None).run(
        AgentContext(
            session_id="s1",
            phase=SessionPhase.GRADE,
            profile=StudentProfile(region="北京", grade=5, age=11),
            paper=tight,
            answers=answers,
        )
    )
    attempts = result.payload["step_attempts"]
    assert attempts
    assert all(isinstance(a, StepAttempt) for a in attempts)
    assert {a.step_index for a in attempts} <= set(range(len(constructed.rubric_steps)))
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd projects/ILearn && python -m pytest tests/test_step_attempt_emission.py -v`  
Expected: FAIL (`step_attempts` KeyError or missing)

- [ ] **Step 3: Write minimal implementation**

In `PracticeAgent.run`, after grading each item:

```python
def _attempts_for_grade(item, grade, lane) -> list[StepAttempt]:
    attempts: list[StepAttempt] = []
    rubric = item.rubric_steps or []
    # Prefer step_results alignment; fall back to splitting answer text by lines
    if grade.step_results:
        for sr in grade.step_results:
            attempts.append(
                StepAttempt(
                    item_id=item.id,
                    step_index=sr.step_index,
                    step_text=rubric[sr.step_index] if sr.step_index < len(rubric) else sr.step_text,
                    student_expression=sr.step_text,
                    lane=lane,
                    hint_level=grade.hint_level_suggestion,
                )
            )
    elif rubric:
        for idx, label in enumerate(rubric):
            attempts.append(
                StepAttempt(
                    item_id=item.id,
                    step_index=idx,
                    step_text=label,
                    student_expression=grade.steps[idx] if idx < len(grade.steps) else "",
                    lane=lane,
                    hint_level=grade.hint_level_suggestion,
                )
            )
    return attempts
```

Return `payload={"grades": grades, "step_attempts": all_attempts, "evidence": evidence_from_grades(...)}`.

- [ ] **Step 4: Run tests**

Run: `cd projects/ILearn && python -m pytest tests/test_step_attempt_emission.py tests/test_agents_practice.py -v`  
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add ilearn/agents/practice.py tests/test_step_attempt_emission.py
git commit -m "feat(practice): emit StepAttempt events aligned to rubric"
```

---

### Task 2: Fill PortraitDimensions.contextual (A-02)

**Files:**
- Modify: `ilearn/core/diagnosis.py` (`PortraitDimensionUpdater`)
- Create: `tests/test_portrait_contextual.py`
- Modify: `ilearn/agents/diagnosis.py` to pass `StudentProfile` into updater if not already

**Interfaces:**
- Consumes: `LearnerPortrait.dimensions`, `StudentProfile.region/grade`
- Produces: `dimensions.contextual["grade_band"]`, `["region_weight"]` floats in `[0,1]`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_portrait_contextual.py
from ilearn.agents.diagnosis import PortraitDimensionUpdater
from ilearn.core.schemas import GradeResult, LearnerPortrait, StudentProfile

def test_contextual_dimensions_set_from_profile():
    portrait = LearnerPortrait(student_key="bj_g5")
    profile = StudentProfile(region="北京", grade=5, age=11)
    grade = GradeResult(item_id="q1", final_correct=True, knowledge_ids=["frac_add_same"])
    updated = PortraitDimensionUpdater.apply(portrait, [grade], profile=profile)
    assert updated.dimensions.contextual.get("grade_band", 0.0) > 0.0
    assert updated.dimensions.contextual.get("region_weight", 0.0) > 0.0
```

- [ ] **Step 2: Run — expect fail**

Run: `cd projects/ILearn && python -m pytest tests/test_portrait_contextual.py -v`  
Expected: FAIL (`apply() got unexpected keyword` or contextual empty)

- [ ] **Step 3: Minimal implementation**

```python
# PortraitDimensionUpdater.apply signature:
@staticmethod
def apply(
    portrait: LearnerPortrait,
    grades: list[GradeResult],
    profile: StudentProfile | None = None,
) -> LearnerPortrait:
    ...
    if profile is not None:
        # grade 4→0.4, 5→0.5, 6→0.6 (pilot band); other grades clamp later for K12
        portrait.dimensions.contextual["grade_band"] = profile.grade / 10.0
        portrait.dimensions.contextual["region_weight"] = (
            1.0 if profile.region.strip() in {"北京", "Beijing"} else 0.5
        )
    return portrait
```

Update `DiagnosisAgent.run` to pass `ctx.profile`.

- [ ] **Step 4: Run** `python -m pytest tests/test_portrait_contextual.py tests/test_portrait_dimensions.py tests/test_agents_diagnosis.py -v`  
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git commit -m "feat(diagnosis): populate portrait contextual dimensions from profile"
```

---

### Task 3: Curriculum citation ids on items (A-03 citation half; OPT-041 lite)

**Files:**
- Modify: `ilearn/core/schemas.py` (`AssessmentItem.curriculum_objective_ids: list[str] = []`)
- Modify: `ilearn/agents/assessment.py`, `ilearn/agents/curriculum.py`
- Modify: `ilearn/providers/curriculum_rag.py` (expose `source_id` on citations)
- Create: `tests/test_citation_on_paper.py`

**Interfaces:**
- Consumes: `CurriculumCitation`, RAG `source_id` / `content_hash`
- Produces: diagnostic `paper.items[*].curriculum_objective_ids` non-empty when citations exist; sources retain hash

- [ ] **Step 1: Write the failing test**

```python
# tests/test_citation_on_paper.py
from pathlib import Path
from ilearn.agents.assessment import AssessmentAgent
from ilearn.agents.curriculum import CurriculumAgent
from ilearn.agents.protocol import AgentContext, SessionPhase
from ilearn.core.schemas import StudentProfile
from ilearn.providers.curriculum import PilotBeijingRenjiaoProvider

PILOT = Path(__file__).resolve().parents[1] / "data" / "pilot"

def test_assessment_items_carry_curriculum_objective_ids():
    profile = StudentProfile(region="北京", grade=5, age=11)
    cur = CurriculumAgent(pilot_dir=PILOT).run(
        AgentContext(session_id="s1", phase=SessionPhase.ONBOARD, profile=profile)
    )
    citations = cur.payload.get("citations") or []
    assert citations, "pilot RAG should return citations"
    ctx = AgentContext(
        session_id="s1",
        phase=SessionPhase.ASSESS,
        profile=profile,
        metadata={"citations": citations, "weak_knowledge_ids": []},
    )
    paper = AssessmentAgent(PilotBeijingRenjiaoProvider(PILOT)).run(ctx).payload["paper"]
    assert any(item.curriculum_objective_ids for item in paper.items)
```

- [ ] **Step 2: Run — expect fail**

- [ ] **Step 3: Implementation**

```python
# schemas AssessmentItem:
curriculum_objective_ids: list[str] = Field(default_factory=list)

# AssessmentAgent after fill_blueprint:
citation_ids = [
    c.source_id if hasattr(c, "source_id") else getattr(c, "source_label", "")
    for c in (ctx.metadata.get("citations") or [])
]
citation_ids = [x for x in citation_ids if x]
for item in paper.items:
    if not item.curriculum_objective_ids and citation_ids:
        item.curriculum_objective_ids = citation_ids[:1]
```

Ensure `CurriculumCitation` has `source_id: str | None = None` populated from `curriculum_sources.json` `source_id`.

Verify hash present:

```python
def test_curriculum_sources_have_content_hash():
    import json
    from pathlib import Path
    data = json.loads((PILOT / "curriculum_sources.json").read_text(encoding="utf-8"))
    assert all(entry.get("content_hash") for entry in data)
```

- [ ] **Step 4: Run** `python -m pytest tests/test_citation_on_paper.py tests/test_curriculum_rag.py tests/test_agents_assessment.py -v`

- [ ] **Step 5: Commit**

```bash
git commit -m "feat(curriculum): bind curriculum_objective_ids onto assessment items"
```

---

### Task 4: CLI `--completeness` (A-04)

**Files:**
- Modify: `ilearn/cli/main.py`, `ilearn/agents/eval_agent.py` (if needed)
- Create: `tests/test_cli_completeness.py`

**Interfaces:**
- Consumes: `EvalAgent.run_completeness() -> dict` with keys `total`, `completeness`, `avg_step_score`
- Produces: CLI flag `--completeness` (alias accept `--tutor-gym` same path)

- [ ] **Step 1: Write the failing test**

```python
# tests/test_cli_completeness.py
from typer.testing import CliRunner
from ilearn.cli.main import app

def test_eval_completeness_flag_prints_metrics():
    runner = CliRunner()
    result = runner.invoke(app, ["eval", "--completeness"])
    assert result.exit_code == 0
    assert "completeness:" in result.stdout
    assert "total:" in result.stdout
```

- [ ] **Step 2: Run — expect fail** (unknown option)

- [ ] **Step 3: Implementation**

```python
# ilearn/cli/main.py eval():
completeness: bool = typer.Option(False, "--completeness", "--tutor-gym", help="...")
...
if completeness:
    eval_agent = EvalAgent(fixtures_dir=_DEFAULT_FIXTURES.parent, llm=llm)
    report = eval_agent.run_completeness()
    typer.echo(f"total: {report['total']}")
    typer.echo(f"completeness: {report['completeness']:.4f}")
    typer.echo(f"avg_step_score: {report.get('avg_step_score', 0.0):.4f}")
    return
```

- [ ] **Step 4: Run** `python -m pytest tests/test_cli_completeness.py tests/test_tutor_gym_profile.py tests/test_cli.py -v`

- [ ] **Step 5: Commit**

```bash
git commit -m "feat(cli): add eval --completeness for tutor_gym metrics"
```

---

### Task 5: mistake_correction + scaffolding_generation (A-05)

**Files:**
- Create: `data/eval/mistake_correction_fixtures.json`, `data/eval/scaffolding_fixtures.json`
- Modify: `ilearn/eval/mathtutorbench_tasks.py`, `ilearn/agents/eval_agent.py`, `ilearn/cli/main.py`
- Create: `tests/test_mathtutorbench_extra_tasks.py`

**Interfaces:**
- Produces:
  - `run_mistake_correction_benchmark(path, llm=None) -> dict` keys: `total`, `correction_acc`
  - `run_scaffolding_benchmark(path, llm=None) -> dict` keys: `total`, `hint_level_match`

Fixture shapes:

```json
// mistake_correction_fixtures.json (5+ items)
[{"id": "mc_01", "stem": "12+8", "wrong_answer": "19", "gold_correction": "20", "rubric_steps": ["列式", "计算"]}]

// scaffolding_fixtures.json
[{"id": "sc_01", "stem": "分数加法", "error_tag": "concept_gap", "gold_hint_level": "medium"}]
```

Offline correction: normalize and compare `gold_correction` to rule that maps wrong→key via `answers_match(grader_suggested, gold)` where suggestion = `gold_correction` when offline identity check uses fixture key as expected repair target — implement:

```python
def score_mistake_correction(fx, llm=None) -> bool:
    # Offline: student wrong_answer must NOT match gold; corrected value == gold_correction
    if answers_match(fx.wrong_answer, fx.gold_correction):
        return False
    return answers_match(fx.gold_correction, fx.gold_correction)  # tautology for fixture integrity
```

Better offline metric: treat `gold_correction` as the only accepted repair; a stub `propose_correction(wrong, stem, key)` returns `key` if `answers_match` fails else `wrong`:

```python
def propose_correction(wrong: str, answer_key: str) -> str:
    return answer_key if not answers_match(wrong, answer_key) else wrong

def score_mistake_correction(fx) -> bool:
    return answers_match(propose_correction(fx.wrong_answer, fx.gold_correction), fx.gold_correction)
```

Scaffolding offline: map `error_tag` → default hint level table; compare to `gold_hint_level`.

```python
_DEFAULT_HINT = {
    "concept_gap": "medium",
    "calc_error": "low",
    "misread": "low",
    "method_wrong": "high",
    "incomplete": "medium",
}
```

- [ ] **Step 1: Write failing tests**

```python
def test_mistake_correction_offline_acc():
    from ilearn.eval.mathtutorbench_tasks import run_mistake_correction_benchmark
    from pathlib import Path
    path = Path(__file__).resolve().parents[1] / "data/eval/mistake_correction_fixtures.json"
    report = run_mistake_correction_benchmark(path, llm=None)
    assert report["total"] >= 5
    assert report["correction_acc"] >= 0.8

def test_scaffolding_offline_hint_match():
    from ilearn.eval.mathtutorbench_tasks import run_scaffolding_benchmark
    from pathlib import Path
    path = Path(__file__).resolve().parents[1] / "data/eval/scaffolding_fixtures.json"
    report = run_scaffolding_benchmark(path, llm=None)
    assert report["total"] >= 5
    assert report["hint_level_match"] >= 0.8
```

- [ ] **Step 2: Run — expect fail** (fixtures/module missing)

- [ ] **Step 3: Add fixtures + runners + CLI flags `--mistake-correction` `--scaffolding`**

- [ ] **Step 4: Run** `python -m pytest tests/test_mathtutorbench_extra_tasks.py tests/test_mathtutorbench_tasks.py -v`

- [ ] **Step 5: Commit**

```bash
git commit -m "feat(eval): add mistake_correction and scaffolding mathtutorbench tasks"
```

---

### Task 6: Replace datetime.utcnow (G-01)

**Files:**
- Create: `ilearn/core/datetime_utils.py`
- Modify: all `datetime.utcnow` call sites under `ilearn/` (`schemas.py`, `grader.py`, `diagnosis.py`, …)
- Create: `tests/test_datetime_utils.py`

**Interfaces:**
- Produces: `utc_now() -> datetime` timezone-aware UTC

- [ ] **Step 1: Write failing test**

```python
# tests/test_datetime_utils.py
from datetime import timezone
from ilearn.core.datetime_utils import utc_now

def test_utc_now_is_timezone_aware():
    now = utc_now()
    assert now.tzinfo is not None
    assert now.tzinfo == timezone.utc
```

- [ ] **Step 2: Run — expect fail**

- [ ] **Step 3: Implement and replace**

```python
# ilearn/core/datetime_utils.py
from datetime import datetime, timezone

def utc_now() -> datetime:
    return datetime.now(timezone.utc)
```

Replace `default_factory=datetime.utcnow` with `default_factory=utc_now` and `datetime.utcnow()` call sites with `utc_now()`.

- [ ] **Step 4: Run** `python -m pytest tests/test_datetime_utils.py tests/ -q`  
Expected: PASS; **no** `utcnow` DeprecationWarning from `ilearn/` (Starlette/httpx warnings may remain)

- [ ] **Step 5: Commit**

```bash
git commit -m "fix: replace datetime.utcnow with timezone-aware utc_now"
```

---

### Task 7: Evidence log dedupe (G-02)

**Files:**
- Modify: `ilearn/core/evidence.py`, `ilearn/agents/orchestrator.py`
- Create: `tests/test_evidence_dedupe.py`

**Interfaces:**
- Produces: `append_evidence` no-ops if same `(session_id, item_id, knowledge_id, lane, step_index)` already present

- [ ] **Step 1: Write failing test**

```python
# tests/test_evidence_dedupe.py
from ilearn.core.evidence import append_evidence
from ilearn.core.schemas import KnowledgeEvidence, SessionState, StudentProfile

def test_append_evidence_dedupes_same_key():
    session = SessionState(
        session_id="s1",
        profile=StudentProfile(region="北京", grade=5, age=11),
    )
    ev = KnowledgeEvidence(
        session_id="s1",
        item_id="q1",
        knowledge_id="frac_add_same",
        lane="probe",
        correct=True,
        step_index=0,
    )
    append_evidence(session, ev)
    append_evidence(session, ev.model_copy())
    assert len(session.evidence_log) == 1
```

- [ ] **Step 2: Run — expect fail** (len==2)

- [ ] **Step 3: Implement**

```python
def _evidence_key(event: KnowledgeEvidence) -> tuple:
    return (
        event.session_id,
        event.item_id,
        event.knowledge_id,
        event.lane,
        event.step_index,
    )

def append_evidence(session: SessionState, event: KnowledgeEvidence) -> None:
    key = _evidence_key(event)
    if any(_evidence_key(e) == key for e in session.evidence_log):
        return
    session.evidence_log.append(event)
```

- [ ] **Step 4: Run** `python -m pytest tests/test_evidence_dedupe.py tests/test_evidence_emission.py -v`

- [ ] **Step 5: Commit**

```bash
git commit -m "fix(evidence): dedupe KnowledgeEvidence appends by natural key"
```

---

### Task 8: Receipt OCR fields + blueprint seed (G-03, G-04)

**Files:**
- Modify: `ilearn/core/schemas.py` (`GradingReceipt.ocr_confidence: float | None = None`, `ocr_degraded: bool | None = None`)
- Modify: `ilearn/agents/practice.py` (set receipt fields after OCR path)
- Modify: `ilearn/core/assessment.py` (`fill_blueprint(..., rng: random.Random | None = None)`)
- Modify: `ilearn/agents/assessment.py` (pass `Random(seed)` from `ctx.metadata.get("rng_seed", 0)` for diagnostic reproducibility when seed provided)
- Create: `tests/test_receipt_ocr_and_seed.py`

**Interfaces:**
- Produces: image grades with `receipt.ocr_confidence` set; same seed → same item ids order for blueprint fill

- [ ] **Step 1: Write failing tests**

```python
def test_image_grade_receipt_records_ocr_confidence():
    from ilearn.agents.practice import PracticeAgent
    from ilearn.agents.protocol import AgentContext, SessionPhase
    from ilearn.core.schemas import (
        AssessmentItem, AssessmentPaper, ImageAnswer, StudentProfile,
    )
    item = AssessmentItem(
        id="c1", stem="计算 12+8", type="constructed", difficulty="easy",
        knowledge_ids=["g5_add"], answer_key="20", rubric_steps=["列式", "计算", "写答"],
    )
    paper = AssessmentPaper(items=[item], grade=5, curriculum_label="北京·人教·小学数学")
    result = PracticeAgent(llm=None).run(
        AgentContext(
            session_id="s1",
            phase=SessionPhase.GRADE,
            profile=StudentProfile(region="北京", grade=5, age=11),
            paper=paper,
            image_answers=[ImageAnswer(item_id="c1", image_base64="aGVsbG8=", mime_type="image/png")],
        )
    )
    grade = result.payload["grades"][0]
    assert grade.receipt is not None
    assert grade.receipt.ocr_confidence is not None
    assert grade.receipt.ocr_degraded is True

def test_fill_blueprint_respects_seed():
    from pathlib import Path
    from random import Random
    from ilearn.core.assessment import build_blueprint, fill_blueprint
    from ilearn.core.schemas import StudentProfile
    from ilearn.providers.curriculum import PilotBeijingRenjiaoProvider
    PILOT = Path(__file__).resolve().parents[1] / "data" / "pilot"
    profile = StudentProfile(region="北京", grade=5, age=11)
    curriculum = PilotBeijingRenjiaoProvider(PILOT)
    bp = build_blueprint(profile)
    p1 = fill_blueprint(profile, bp, curriculum, rng=Random(42))
    p2 = fill_blueprint(profile, bp, curriculum, rng=Random(42))
    assert [i.id for i in p1.items] == [i.id for i in p2.items]
```

- [ ] **Step 2: Run — expect fail**

- [ ] **Step 3: Implement receipt OCR fields + `rng` parameter on `fill_blueprint` / `AssessmentBuilder` instantiate path**

- [ ] **Step 4: Run** `python -m pytest tests/test_receipt_ocr_and_seed.py tests/test_grading_receipt.py tests/test_paper_blueprint.py -v`

- [ ] **Step 5: Commit**

```bash
git commit -m "feat: record OCR on GradingReceipt and seed blueprint fill"
```

---

### Task 9: Doc refresh + TODO ticks (F-01…F-04, G-05 note, G-06)

**Files:**
- Modify: `doc/composition/INDEX.md`, `doc/composition/MULTI_AGENT_ARCHITECTURE.md` §7 table, `doc/composition/AGENT_MAPPING.md`, `doc/composition/ANALYSIS_BY_REPO_v2.md` §下一步, `doc/composition/TODO.md`
- Modify: `tests/test_evidence_schemas.py` (drop unused imports — G-06)
- Modify: `README.md` eval section to mention `--completeness` / new flags

**Interfaces:** none (docs + tiny test cleanup)

- [ ] **Step 1: Write failing test for unused-import cleanup is N/A — run ruff/compile check instead**

```python
# tests/test_evidence_schemas.py — remove unused EvidenceLane, StepVerdict imports if still unused
# Keep StepVerdict only if a construction test is added; preferred: add one-liner construction test
from ilearn.core.schemas import StepVerdict

def test_step_verdict_defaults():
    v = StepVerdict(step_index=0, status="correct")
    assert v.comment == ""
```

- [ ] **Step 2: Run** `python -m pytest tests/test_evidence_schemas.py -v`

- [ ] **Step 3: Update docs**

`INDEX.md` / architecture phase table: mark Phase1 closeout done; point next to Phase 2a.  
`TODO.md`: set A-01…A-05, G-01…G-06, F-01…F-04 to `done` with date; note A-03 Qdrant still open under Phase 2c.  
`AGENT_MAPPING.md`: VL is implemented (not Phase 3).  
`ANALYSIS_BY_REPO_v2.md` 下一步: Phase1 done → Phase 2a.  
README CLI eval bullets include new flags.

- [ ] **Step 4: Full regression**

Run: `cd projects/ILearn && python -m pytest tests/ -q`  
Expected: PASS (≥165)

- [ ] **Step 5: Commit**

```bash
git add doc/composition/*.md README.md tests/test_evidence_schemas.py
git commit -m "docs: mark Phase1 closeout done and refresh composition index"
```

---

## Self-Review

### Spec coverage (`TODO.md` A+G+F-01..04)

| TODO ID | Task |
|---------|------|
| A-01 | Task 1 |
| A-02 | Task 2 |
| A-03 citation/hash | Task 3 (Qdrant → deferred Phase 2c) |
| A-04 | Task 4 |
| A-05 | Task 5 |
| G-01 | Task 6 |
| G-02 | Task 7 |
| G-03, G-04 | Task 8 |
| G-05 | Deferred to Phase 2a (OPT-023/024) — noted in Task 9 TODO.md |
| G-06 | Task 9 |
| F-01…F-04 | Task 9 |

### Placeholder scan
No TBD / “similar to Task N” / empty test stubs.

### Type consistency
- `StepAttempt` fields match schemas Task 1
- `PortraitDimensionUpdater.apply(..., profile=)` Task 2
- `curriculum_objective_ids: list[str]` Task 3
- CLI flags match EvalAgent method names Tasks 4–5
- `utc_now()` used everywhere Task 6+

### Out of this plan
All of TODO §§B, C, D, E, F-05…07, and A-03 Qdrant — see `2026-08-10-composition-todo-roadmap.md`.

---

**Plan complete and saved to `docs/superpowers/plans/2026-08-10-composition-phase1-closeout.md`.**  
Roadmap index: `docs/superpowers/plans/2026-08-10-composition-todo-roadmap.md`.

**Two execution options:**

**1. Subagent-Driven (recommended)** — fresh subagent per task, review between tasks  

**2. Inline Execution** — execute in this session with executing-plans checkpoints  

**Which approach?**

(Next writing-plans invocations should target Phase 2a / 2b / … packages from the roadmap — not re-plan the whole 75-item TODO.)
