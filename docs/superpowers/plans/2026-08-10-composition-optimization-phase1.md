# Composition Optimization Phase 1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close the 12 P0 gaps from `doc/composition/OPTIMIZATION_BACKLOG.md` on top of `feature/ilearn-multi-agent-p0`: step/evidence schemas, host-owned grading, curriculum RAG, practice/probe mastery, PaperBlueprint, SM-2 review, and public benchmark hooks.

**Architecture:** Extend `ilearn/core/schemas.py` with evidence and mastery models first; split grading into `OcrExtractor` + `StepGrader` + `GradingReceipt` under `ilearn/core/`; wire DiagnosisAgent/PlanningAgent/CurriculumAgent/EvalAgent to new contracts. Keep lightweight Python orchestration (no LangGraph). Curriculum RAG Phase 1 uses **local keyword index** over `data/pilot/syllabus.json` + future `curriculum_sources.json` (YAGNI — no Qdrant yet).

**Tech Stack:** Python 3.11+, pydantic v2, existing FastAPI/Streamlit/Typer stack, pytest; optional `rank_bm25` or stdlib-only keyword scorer (prefer stdlib `difflib`/token overlap to avoid new deps unless already present)

## Global Constraints

- Paper size unchanged: **20** items; difficulty **10/8/2**; types **8/8/4** (choice/fill/constructed)
- Subject: **elementary math**, grades **4–6**; pilot curriculum **北京·人教·小学数学**
- Controlled `error_tags`: `concept_gap`, `calc_error`, `misread`, `method_wrong`, `incomplete`
- LLM via `.env` (`ILEARN_LLM_*`); optional `ILEARN_VISION_MODEL`
- **Regression gate:** `python -m pytest tests/ -q` must pass after every task (baseline **125** tests)
- Package root: `projects/ILearn/`; import `ilearn`
- Design refs: `doc/composition/OPTIMIZATION_BACKLOG.md`, `doc/composition/ANALYSIS_BY_REPO_v2.md`, `doc/design_think.txt`
- No LangGraph; no live web crawl in Phase 1
- Backward compat: existing session JSON must deserialize with defaults for new optional fields

## File Map

| Path | Responsibility |
|------|----------------|
| `ilearn/core/schemas.py` | StepAttempt, KnowledgeEvidence, MasteryRecord, GradingReceipt, PaperBlueprint |
| `ilearn/core/grader.py` | **New** Host-owned `ItemGrader` facade (OPT-012) |
| `ilearn/core/ocr.py` | **New** `OcrExtractor` — image→structured steps only |
| `ilearn/core/grading.py` | StepGrader (text); delegates vision path to ocr+grader |
| `ilearn/core/evidence.py` | **New** append/list evidence events |
| `ilearn/core/review.py` | **New** SM-2 scheduler (OPT-030) |
| `ilearn/core/assessment.py` | PaperBlueprint builder + validator |
| `ilearn/agents/practice.py` | Wire grader + evidence emission |
| `ilearn/agents/diagnosis.py` | practice_score vs probe_mastery |
| `ilearn/agents/planning.py` | Insert spaced review days |
| `ilearn/agents/curriculum.py` | Keyword RAG retrieve |
| `ilearn/agents/assessment.py` | Blueprint→items pipeline |
| `ilearn/eval/mathtutorbench_tasks.py` | **New** YAML-style task runners |
| `ilearn/eval/tutor_gym_profile.py` | **New** completeness metrics |
| `data/pilot/curriculum_sources.json` | Indexed syllabus snippets with hashes |
| `data/eval/mistake_location_fixtures.json` | **New** 10 CN fixtures |
| `data/eval/step_completeness_profiles.json` | **New** 5 tutor_gym-style profiles |

---

### Task 1: StepAttempt + KnowledgeEvidence schemas (OPT-010, OPT-021 base)

**Files:**
- Modify: `ilearn/core/schemas.py`
- Create: `ilearn/core/evidence.py`, `tests/test_evidence_schemas.py`

**Interfaces:**
- Produces: `StepAttempt`, `StepVerdict`, `KnowledgeEvidence`, `EvidenceLane` literal

- [ ] **Step 1: Write failing schema tests**

```python
# tests/test_evidence_schemas.py
from ilearn.core.schemas import EvidenceLane, KnowledgeEvidence, StepAttempt, StepVerdict

def test_step_attempt_aligns_rubric_index():
    StepAttempt(
        item_id="q1",
        step_index=0,
        step_text="列式",
        student_expression="12+8",
        lane="practice",
    )

def test_knowledge_evidence_requires_session():
    ev = KnowledgeEvidence(
        session_id="s1",
        item_id="q1",
        knowledge_id="frac_add_same",
        lane="practice",
        correct=False,
        error_tag="calc_error",
        hint_level="none",
        confidence=0.9,
    )
    assert ev.lane == "practice"
```

Add to `schemas.py`:

```python
EvidenceLane = Literal["practice", "probe"]

class StepAttempt(BaseModel):
    item_id: str
    step_index: int = Field(ge=0)
    step_text: str
    student_expression: str
    lane: EvidenceLane = "practice"
    hint_level: HintLevel = "none"

class StepVerdict(BaseModel):
    step_index: int = Field(ge=0)
    status: StepStatus
    comment: str = ""

class KnowledgeEvidence(BaseModel):
    session_id: str
    item_id: str
    knowledge_id: str
    lane: EvidenceLane
    correct: bool
    error_tag: ErrorTag | None = None
    hint_level: HintLevel = "none"
    confidence: float = Field(ge=0.0, le=1.0, default=1.0)
    step_index: int | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
```

Extend `SessionState`:

```python
evidence_log: list[KnowledgeEvidence] = Field(default_factory=list)
```

Create `evidence.py`:

```python
from ilearn.core.schemas import KnowledgeEvidence, SessionState

def append_evidence(session: SessionState, event: KnowledgeEvidence) -> None:
    session.evidence_log.append(event)

def events_for_knowledge(session: SessionState, knowledge_id: str) -> list[KnowledgeEvidence]:
    return [e for e in session.evidence_log if e.knowledge_id == knowledge_id]
```

- [ ] **Step 2: Run test — expect fail**

Run: `cd projects/ILearn && python -m pytest tests/test_evidence_schemas.py -v`  
Expected: FAIL

- [ ] **Step 3: Implement schemas + evidence helpers**

- [ ] **Step 4: Run tests — expect pass**

Run: `cd projects/ILearn && python -m pytest tests/test_evidence_schemas.py tests/test_schemas.py -v`  
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add ilearn/core/schemas.py ilearn/core/evidence.py tests/test_evidence_schemas.py
git commit -m "feat(evidence): add StepAttempt and KnowledgeEvidence schemas"
```

---

### Task 2: Host-owned ItemGrader module (OPT-012)

**Files:**
- Create: `ilearn/core/grader.py`, `tests/test_grader_module.py`
- Modify: `ilearn/core/grading.py`, `ilearn/agents/practice.py`

**Interfaces:**
- Produces: `ItemGrader.grade_item(item, answer_text, *, llm) -> GradeResult`
- Consumes: existing `StepGrader` logic moved/called from `ItemGrader`

- [ ] **Step 1: Write failing test — grader independent of AssessmentAgent**

```python
# tests/test_grader_module.py
from ilearn.core.grader import ItemGrader, GRADER_VERSION
from ilearn.core.schemas import AssessmentItem
from ilearn.providers.llm import LLMClient

def test_item_grader_offline_choice():
    grader = ItemGrader(llm=None)
    item = AssessmentItem(
        id="c1", stem="1+1=?", type="choice", difficulty="easy",
        knowledge_ids=["dec_mult"], answer_key="2",
        choices=["2", "3", "4", "5"],
    )
    result = grader.grade_item(item, "2")
    assert result.final_correct is True
    assert GRADER_VERSION
```

- [ ] **Step 2: Run test — expect fail**

Run: `cd projects/ILearn && python -m pytest tests/test_grader_module.py -v`  
Expected: FAIL

- [ ] **Step 3: Implement ItemGrader**

```python
# ilearn/core/grader.py
GRADER_VERSION = "1.0.0"

class ItemGrader:
    """Host-owned deterministic + LLM grader. AssessmentAgent must not embed grading."""
    def __init__(self, llm: LLMClient | None = None) -> None:
        self._step_grader = StepGrader(llm)

    def grade_item(self, item: AssessmentItem, answer_text: str) -> GradeResult:
        return self._step_grader.grade_item(item, answer_text)
```

Update `PracticeAgent` to use `ItemGrader` instead of `StepGrader` directly.

- [ ] **Step 4: Full regression**

Run: `cd projects/ILearn && python -m pytest tests/ -q`  
Expected: PASS (≥125)

- [ ] **Step 5: Commit**

```bash
git add ilearn/core/grader.py ilearn/core/grading.py ilearn/agents/practice.py tests/test_grader_module.py
git commit -m "feat(grader): add host-owned ItemGrader facade"
```

---

### Task 3: GradingReceipt source binding (OPT-080)

**Files:**
- Modify: `ilearn/core/schemas.py`, `ilearn/core/grader.py`, `ilearn/storage/sessions.py`
- Create: `tests/test_grading_receipt.py`

**Interfaces:**
- Produces: `GradingReceipt`, `GradeResult.receipt: GradingReceipt | None`

```python
class GradingReceipt(BaseModel):
    paper_created_at: datetime
    grader_version: str
    model_id: str | None = None
    graded_at: datetime = Field(default_factory=datetime.utcnow)
```

- [ ] **Step 1: Write failing test**

```python
# tests/test_grading_receipt.py
from datetime import datetime, timezone

from ilearn.core.grader import GRADER_VERSION, ItemGrader
from ilearn.core.schemas import AssessmentItem, GradingReceipt

def test_grade_result_includes_receipt():
    grader = ItemGrader(llm=None)
    item = AssessmentItem(
        id="c1",
        stem="1+1=?",
        type="choice",
        difficulty="easy",
        knowledge_ids=["dec_mult"],
        answer_key="2",
        choices=["2", "3", "4", "5"],
    )
    paper_created_at = datetime(2026, 8, 10, tzinfo=timezone.utc)
    result = grader.grade_item(item, "2", paper_created_at=paper_created_at)
    assert result.receipt is not None
    assert result.receipt.grader_version == GRADER_VERSION
    assert result.receipt.paper_created_at == paper_created_at
    assert result.receipt.model_id is None
```

Extend `ItemGrader.grade_item` signature:

```python
def grade_item(
    self,
    item: AssessmentItem,
    answer_text: str,
    *,
    paper_created_at: datetime | None = None,
) -> GradeResult:
    result = self._step_grader.grade_item(item, answer_text)
    receipt = GradingReceipt(
        paper_created_at=paper_created_at or datetime.utcnow(),
        grader_version=GRADER_VERSION,
        model_id=getattr(self._step_grader._llm, "model_id", None),
    )
    result.receipt = receipt
    return result
```

Add `GradeResult.receipt: GradingReceipt | None = None` in schemas.

- [ ] **Step 2: Run — expect fail**

Run: `cd projects/ILearn && python -m pytest tests/test_grading_receipt.py -v`  
Expected: FAIL (`receipt` attribute missing)

- [ ] **Step 3: Attach receipt in ItemGrader.grade_item**

- [ ] **Step 4: Run `python -m pytest tests/test_grading_receipt.py tests/test_grader_module.py -v`**

- [ ] **Step 5: Commit**

```bash
git commit -m "feat(grader): bind GradeResult to GradingReceipt"
```

---

### Task 4: Vision OCR / Grading separation (OPT-011)

**Files:**
- Create: `ilearn/core/ocr.py`, `tests/test_ocr_extractor.py`
- Modify: `ilearn/core/grading.py` (remove combined vision grade), `ilearn/agents/practice.py`

**Interfaces:**
- Produces: `OcrExtractor.extract(item, image_base64, mime_type) -> OcrResult`
- `OcrResult`: `pages: list[OcrPage]`, `steps: list[str]`, `confidence: float`, `degraded: bool`

- [ ] **Step 1: Write failing OCR test**

```python
# tests/test_ocr_extractor.py
from ilearn.core.ocr import OcrExtractor
from ilearn.core.schemas import AssessmentItem

def _constructed_item() -> AssessmentItem:
    return AssessmentItem(
        id="c1",
        stem="计算 12+8",
        type="constructed",
        difficulty="easy",
        knowledge_ids=["g5_add"],
        answer_key="20",
        rubric_steps=["列式", "计算", "写答"],
    )

def test_ocr_extractor_offline_degrades():
    result = OcrExtractor(llm=None).extract(
        item=_constructed_item(),
        image_base64="aGVsbG8=",
        mime_type="image/png",
    )
    assert result.degraded is True
    assert len(result.steps) >= 1
    assert result.confidence == 0.0
```

- [ ] **Step 2: Run — expect fail**

- [ ] **Step 3: Implement OcrExtractor; PracticeAgent pipeline: OCR → join steps → ItemGrader**

Remove direct `_VISION_SYSTEM_PROMPT` grading from `VisionGrader`; keep `VisionGrader` as thin wrapper calling `OcrExtractor` + `ItemGrader` or delete class in favor of pipeline.

- [ ] **Step 4: Run `python -m pytest tests/test_ocr_extractor.py tests/test_vision_grader.py -v`**

- [ ] **Step 5: Commit**

```bash
git commit -m "feat(practice): separate OCR extraction from step grading"
```

---

### Task 5: practice_score vs probe_mastery (OPT-020)

**Files:**
- Modify: `ilearn/core/schemas.py`, `ilearn/core/diagnosis.py`, `ilearn/agents/diagnosis.py`
- Create: `tests/test_mastery_lanes.py`

**Interfaces:**
- Produces: `MasteryRecord` on `LearnerPortrait`:

```python
class MasteryRecord(BaseModel):
    practice_score: float = Field(ge=0.0, le=1.0, default=0.0)
    probe_mastery: float = Field(ge=0.0, le=1.0, default=0.0)
    evidence_count: int = 0
    last_probe_at: datetime | None = None

# LearnerPortrait.knowledge_state: dict[str, MasteryRecord]  # breaking: migrate float compat
```

Use `dict[str, MasteryRecord]` new field `mastery_records` alongside legacy `knowledge_state: dict[str, float]` for backward compat.

- [ ] **Step 1: Write failing test — probe lane updates probe_mastery only**

```python
# tests/test_mastery_lanes.py
from ilearn.agents.diagnosis import PortraitUpdater
from ilearn.core.schemas import GradeResult, LearnerPortrait, MasteryRecord
from ilearn.providers.curriculum import PilotBeijingRenjiaoProvider
from pathlib import Path

PILOT = Path(__file__).resolve().parents[1] / "data" / "pilot"

def test_probe_lane_does_not_update_practice_score():
    portrait = LearnerPortrait(student_key="bj_g5")
    portrait.mastery_records["frac_add_same"] = MasteryRecord(
        practice_score=0.6,
        probe_mastery=0.4,
    )
    grade = GradeResult(
        item_id="q1",
        final_correct=True,
        knowledge_ids=["frac_add_same"],
        lane="probe",
    )
    updated = PortraitUpdater.update(
        portrait,
        [grade],
        session_id="s1",
        curriculum=PilotBeijingRenjiaoProvider(PILOT),
        grade=5,
    )
    rec = updated.mastery_records["frac_add_same"]
    assert rec.practice_score == 0.6
    assert rec.probe_mastery > 0.4
```

Add `lane: EvidenceLane = "practice"` to `GradeResult`.

- [ ] **Step 2–5: Implement lane-aware PortraitUpdater; emit evidence with lane from GradeResult metadata**

Run: `python -m pytest tests/test_mastery_lanes.py tests/test_agents_diagnosis.py -v`  
Commit: `feat(diagnosis): separate practice_score and probe_mastery`

---

### Task 6: KnowledgeEvidence emission from PracticeAgent (OPT-021)

**Files:**
- Modify: `ilearn/agents/practice.py`, `ilearn/agents/orchestrator.py`, `tests/test_evidence_emission.py`

**Interfaces:**
- After grade: for each `GradeResult`, append `KnowledgeEvidence` per `knowledge_id` to session via `append_evidence`

- [ ] **Step 1: Write failing orchestrator test**

```python
# tests/test_evidence_emission.py
from pathlib import Path
from ilearn.agents.orchestrator import MultiAgentOrchestrator
from ilearn.core.schemas import StudentProfile
from ilearn.providers.curriculum import PilotBeijingRenjiaoProvider
from ilearn.storage.sessions import SessionStore

PILOT = Path(__file__).resolve().parents[1] / "data" / "pilot"

def test_full_loop_populates_evidence_log(tmp_path):
    orch = MultiAgentOrchestrator(
        store=SessionStore(tmp_path),
        curriculum=PilotBeijingRenjiaoProvider(PILOT),
        llm=None,
    )
    sid = orch.create_session(StudentProfile(region="北京", grade=5, age=11))
    paper = orch.generate_assessment(sid)
    answers = {item.id: (item.answer_key or "") for item in paper.items}
    orch.submit(sid, answers)
    completed = orch.run_after_submit(sid)
    assert len(completed.evidence_log) >= 1
    assert completed.evidence_log[0].session_id == sid
```

- [ ] **Step 2–5: Implement; regression `python -m pytest tests/ -q`**

Commit: `feat(evidence): emit KnowledgeEvidence from PracticeAgent`

---

### Task 7: Five-dimension portrait extension (OPT-022)

**Files:**
- Modify: `ilearn/core/schemas.py`, `ilearn/agents/diagnosis.py`
- Create: `tests/test_portrait_dimensions.py`

**Interfaces:**

```python
class PortraitDimensions(BaseModel):
    cognitive: dict[str, float] = Field(default_factory=dict)      # bloom / knowledge
    behavioral: dict[str, float] = Field(default_factory=dict)     # hint dependency
    emotional: dict[str, float] = Field(default_factory=dict)      # frustration proxy
    metacognitive: dict[str, float] = Field(default_factory=dict)  # retry patterns
    contextual: dict[str, float] = Field(default_factory=dict)     # grade/region weights

# LearnerPortrait.dimensions: PortraitDimensions = Field(default_factory=PortraitDimensions)
```

Heuristics (no LLM): high hint_level → behavioral↑; consecutive wrong → emotional↑; probe gap → metacognitive flag.

- [ ] **Step 1: Write failing dimension update test**

```python
# tests/test_portrait_dimensions.py
from ilearn.agents.diagnosis import PortraitDimensionUpdater
from ilearn.core.schemas import GradeResult, LearnerPortrait

def test_high_hint_increases_behavioral_score():
    portrait = LearnerPortrait(student_key="bj_g5")
    grade = GradeResult(
        item_id="q1",
        final_correct=False,
        hint_level_suggestion="high",
        knowledge_ids=["frac_add_same"],
    )
    updated = PortraitDimensionUpdater.apply(portrait, [grade])
    assert updated.dimensions.behavioral.get("hint_dependency", 0.0) > 0.0
```

- [ ] **Step 2–5: Implement PortraitDimensionUpdater in diagnosis.py**

Commit: `feat(diagnosis): add five-dimension portrait extension`

---

### Task 8: Curriculum keyword RAG (OPT-040)

**Files:**
- Create: `data/pilot/curriculum_sources.json`, `ilearn/providers/curriculum_rag.py`
- Modify: `ilearn/agents/curriculum.py`, `tests/test_curriculum_rag.py`

**Interfaces:**
- Produces: `CurriculumRagRetriever.retrieve(profile, query, top_k=5) -> list[CurriculumCitation]`
- `curriculum_sources.json` entry:

```json
{
  "source_id": "bj-g5-math-2024",
  "region": "北京",
  "grade": 5,
  "subject": "math",
  "title": "人教版五年级数学",
  "excerpt": "五年级上册：同分母分数加减法，分母不变，分子相加减。",
  "keywords": ["小数", "分数"],
  "content_hash": "sha256:abc123def456"
}
```

- [ ] **Step 1: Write failing retrieve test**

```python
def test_retriever_returns_beijing_grade5_on_fraction_query():
    retriever = CurriculumRagRetriever(pilot_dir=PILOT)
    cites = retriever.retrieve(
        StudentProfile(region="北京", grade=5, age=11),
        query="分数加减",
        top_k=3,
    )
    assert len(cites) >= 1
    assert cites[0].source_label
```

Implement stdlib token overlap scorer (no new deps):

```python
def _score(query_tokens: set[str], doc_tokens: set[str]) -> float:
    if not query_tokens:
        return 0.0
    return len(query_tokens & doc_tokens) / len(query_tokens)
```

Wire `CurriculumAgent.run` to store retrieved citations in `ctx.metadata["citations"]` (already consumed by PlanningAgent).

- [ ] **Step 2–5: Implement; commit**

```bash
git commit -m "feat(curriculum): add keyword RAG over curriculum_sources"
```

---

### Task 9: PaperBlueprint two-phase assembly (OPT-001)

**Files:**
- Modify: `ilearn/core/schemas.py`, `ilearn/core/assessment.py`, `ilearn/agents/assessment.py`
- Create: `tests/test_paper_blueprint.py`

**Interfaces:**

```python
class BlueprintSlot(BaseModel):
    difficulty: Difficulty
    item_type: ItemType
    knowledge_id: str | None = None  # optional target

class PaperBlueprint(BaseModel):
    grade: Literal[4, 5, 6]
    slots: list[BlueprintSlot]  # len 20, matches MIX_BLUEPRINT

class AssessmentPaper(BaseModel):
    items: list[AssessmentItem]
    grade: Literal[4, 5, 6]
    curriculum_label: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    blueprint: PaperBlueprint | None = None
    paper_version: str = "1.0.0"
```

Add to `assessment.py`:

```python
def build_blueprint(profile: StudentProfile, weak_ids: list[str] | None = None) -> PaperBlueprint:
    slots: list[BlueprintSlot] = []
    for difficulty, item_type in MIX_BLUEPRINT:
        kid = weak_ids.pop(0) if weak_ids else None
        slots.append(BlueprintSlot(difficulty=difficulty, item_type=item_type, knowledge_id=kid))
    return PaperBlueprint(grade=profile.grade, slots=slots)

def fill_blueprint(
    profile: StudentProfile,
    blueprint: PaperBlueprint,
    curriculum: CurriculumProvider,
) -> AssessmentPaper:
    builder = AssessmentBuilder(curriculum)
    items = [builder._instantiate_slot(profile, slot) for slot in blueprint.slots]
    return AssessmentPaper(
        items=items,
        grade=profile.grade,
        curriculum_label=curriculum.label,
        blueprint=blueprint,
        paper_version="1.0.0",
    )

def validate_paper(paper: AssessmentPaper) -> None:
    if len(paper.items) != 20:
        raise AssessmentBuildError("paper must have 20 items")
    easy = sum(1 for i in paper.items if i.difficulty == "easy")
    medium = sum(1 for i in paper.items if i.difficulty == "medium")
    hard = sum(1 for i in paper.items if i.difficulty == "hard")
    if (easy, medium, hard) != (10, 8, 2):
        raise AssessmentBuildError(f"difficulty quota mismatch: {(easy, medium, hard)}")
```

`AssessmentAgent.run`: diagnostic → `build_blueprint` → `fill_blueprint` → `validate_paper`.

- [ ] **Step 1: Write failing blueprint quota test**

```python
def test_blueprint_has_20_slots_with_correct_quotas():
    bp = build_blueprint(StudentProfile(region="北京", grade=5, age=11))
    assert len(bp.slots) == 20
    assert sum(1 for s in bp.slots if s.difficulty == "easy") == 10
```

- [ ] **Step 2–5: Implement; `python -m pytest tests/test_paper_blueprint.py tests/test_assessment.py -v`**

Commit: `feat(assessment): add PaperBlueprint two-phase assembly`

---

### Task 10: SM-2 spaced review in PlanningAgent (OPT-030)

**Files:**
- Create: `ilearn/core/review.py`, `tests/test_review_sm2.py`
- Modify: `ilearn/agents/planning.py`, `ilearn/core/planning.py`

**Interfaces:**

```python
class ReviewState(BaseModel):
    ease_factor: float = 2.5
    interval_days: int = 1
    repetitions: int = 0
    due_date: date | None = None

def sm2_update(state: ReviewState, quality: int) -> ReviewState:
    """SuperMemo-2 update; quality 0-5 (3+ = success)."""
    if quality < 3:
        return ReviewState(ease_factor=max(1.3, state.ease_factor - 0.2))
    ef = state.ease_factor + (0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02))
    reps = state.repetitions + 1
    if reps == 1:
        interval = 1
    elif reps == 2:
        interval = 6
    else:
        interval = round(state.interval_days * ef)
    return ReviewState(
        ease_factor=max(1.3, ef),
        interval_days=interval,
        repetitions=reps,
        due_date=date.today() + timedelta(days=interval),
    )

def due_knowledge_ids(portrait: LearnerPortrait, today: date) -> list[str]:
    return [
        kid for kid, rs in portrait.review_states.items()
        if rs.due_date is not None and rs.due_date <= today
    ]
```

PlanningAgent: prepend "复习" tasks for due ids before weak-point focus.

- [ ] **Step 1: Write failing SM-2 test**

```python
def test_sm2_increases_interval_on_good_quality():
    s = ReviewState()
    updated = sm2_update(s, quality=4)
    assert updated.interval_days >= 1
    assert updated.repetitions == 1
```

- [ ] **Step 2–5: Implement; extend `LearnerPortrait.review_states: dict[str, ReviewState]`**

Commit: `feat(planning): add SM-2 spaced review scheduling`

---

### Task 11: mathtutorbench-style eval tasks (OPT-070)

**Files:**
- Create: `data/eval/mistake_location_fixtures.json`, `ilearn/eval/mathtutorbench_tasks.py`, `tests/test_mathtutorbench_tasks.py`
- Modify: `ilearn/agents/eval_agent.py`, `ilearn/cli/main.py`

**Interfaces:**
- Produces: `run_mistake_location_benchmark(fixtures_path, grader) -> dict` with keys `total`, `step_f1`, `first_error_acc`

Fixture format (10 items, Chinese elementary):

```json
{
  "id": "ml_01",
  "stem": "计算 12+8",
  "rubric_steps": ["列式", "计算", "写答"],
  "student_steps": ["12+8=19", "答：19"],
  "gold_first_error_step": 2
}
```

- [ ] **Step 1: Write failing benchmark test**

```python
def test_mistake_location_offline_perfect_on_gold():
    report = run_mistake_location_benchmark(FIXTURES, llm=None)
    assert report["total"] == 10
    assert report["first_error_acc"] >= 0.8
```

- [ ] **Step 2–5: Implement first-error-step detector using step_results; CLI `ilearn eval --mathtutorbench`**

Commit: `feat(eval): add mistake_location benchmark adapter`

---

### Task 12: tutor_gym completeness metrics + E2E (OPT-071)

**Files:**
- Create: `data/eval/step_completeness_profiles.json`, `ilearn/eval/tutor_gym_profile.py`, `tests/test_tutor_gym_profile.py`, `tests/test_e2e_composition_phase1.py`
- Modify: `ilearn/agents/eval_agent.py`, `README.md`

**Interfaces:**
- Profile row: `{ "item_id", "legal_step_indices": [0,1,2], "student_step_indices": [0,1] }`
- Metrics: `correctness`, `completeness`, `avg_step_score`

- [ ] **Step 1: Write failing completeness test**

```python
def test_completeness_penalizes_missing_steps():
    report = run_completeness_benchmark(PROFILES, llm=None)
    assert "completeness" in report
    assert report["total"] >= 5
```

- [ ] **Step 2: Implement completeness scorer**

- [ ] **Step 3: E2E test covering evidence + receipt + blueprint + SM-2**

```python
# tests/test_e2e_composition_phase1.py
from pathlib import Path
from ilearn.agents.orchestrator import MultiAgentOrchestrator
from ilearn.core.schemas import StudentProfile
from ilearn.providers.curriculum import PilotBeijingRenjiaoProvider
from ilearn.storage.sessions import SessionStore

PILOT = Path(__file__).resolve().parents[1] / "data" / "pilot"

def test_e2e_phase1_offline_beijing_g5(tmp_path):
    orch = MultiAgentOrchestrator(
        store=SessionStore(tmp_path),
        curriculum=PilotBeijingRenjiaoProvider(PILOT),
        llm=None,
    )
    sid = orch.create_session(StudentProfile(region="北京", grade=5, age=11))
    paper = orch.generate_assessment(sid)
    assert paper.blueprint is not None
    assert len(paper.blueprint.slots) == 20
    answers = {item.id: (item.answer_key or "") for item in paper.items}
    orch.submit(sid, answers)
    completed = orch.run_after_submit(sid)
    assert completed.evidence_log
    assert completed.portrait.mastery_records or completed.portrait.knowledge_state
    assert "课标依据" in completed.plan.markdown
    assert completed.grades[0].receipt is not None
```

- [ ] **Step 4: Update README Phase 1 section; `python -m pytest tests/ -q`**

- [ ] **Step 5: Commit**

```bash
git commit -m "feat(eval): add tutor_gym completeness metrics and Phase1 E2E"
```

---

## Self-Review

### Spec coverage (12 P0 items)

| P0 ID | Task |
|-------|------|
| OPT-010 | Task 1 |
| OPT-012 | Task 2 |
| OPT-080 | Task 3 |
| OPT-011 | Task 4 |
| OPT-020 | Task 5 |
| OPT-021 | Task 6 |
| OPT-022 | Task 7 |
| OPT-040 | Task 8 |
| OPT-001 | Task 9 |
| OPT-030 | Task 10 |
| OPT-070 | Task 11 |
| OPT-071 | Task 12 |

### Placeholder scan
No TBD/TODO/similar-task-only references.

### Type consistency
- `KnowledgeEvidence.lane` uses `EvidenceLane` throughout Tasks 5–6
- `ItemGrader` / `GRADER_VERSION` referenced in Tasks 2–3
- `MasteryRecord` on portrait Tasks 5–7
- `PaperBlueprint.slots` length 20 validated Task 9

### Dependency order
Tasks 1→2→3→4 (grading stack); 5→6→7 (diagnosis); 8→9 (curriculum before blueprint citations); 10–12 independent eval/E2E.

---

**Plan complete and saved to `docs/superpowers/plans/2026-08-10-composition-optimization-phase1.md`. Two execution options:**

**1. Subagent-Driven (recommended)** — I dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** — Execute tasks in this session using executing-plans, batch execution with checkpoints

**Which approach?**
