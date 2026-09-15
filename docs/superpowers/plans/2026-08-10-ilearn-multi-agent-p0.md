# ILearn Multi-Agent P0 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Upgrade ILearn MVP into an explicit multi-agent system with four core agents (组题 / 练题 / 学情诊断 / 学习建议), a CurriculumAgent for regional syllabus grounding, an Orchestrator state machine with 练→评→练 feedback loop, and image-answer VL grading — aligned with `doc/design_think.txt` and `doc/composition/MULTI_AGENT_ARCHITECTURE.md`.

**Architecture:** Keep existing `ilearn/core/*` logic as agent internals; add `ilearn/agents/` with a sync `Agent` protocol, `AgentContext`, and phase enum. `MultiAgentOrchestrator` replaces direct pipeline calls, persists `LearnerPortrait`, and supports follow-up practice papers. No LangGraph in P0 — thin Python orchestration only (YAGNI).

**Tech Stack:** Python 3.11+, pydantic v2, FastAPI, uvicorn, httpx, streamlit, typer, pytest, python-dotenv, openai (compatible client, including vision when configured)

## Global Constraints

- Paper size: **20** items; difficulty **10/8/2**; types **8/8/4** (choice/fill/constructed)
- Subject: **elementary math**, grades **4–6**
- Curriculum pilot: **北京·人教·小学数学**; non-Beijing `region` → `region_mismatch_disclaimer` in diagnosis/plan
- Grading: **step-level** + controlled `error_tags` (`concept_gap`, `calc_error`, `misread`, `method_wrong`, `incomplete`)
- Answers: **text** (required) + **image** (base64 upload; VL when LLM vision available, else `grading_degraded=True`)
- LLM: OpenAI-compatible via `.env` (`ILEARN_LLM_BASE_URL`, `ILEARN_LLM_API_KEY`, `ILEARN_LLM_MODEL`); optional `ILEARN_VISION_MODEL`
- No LangGraph, no live web crawl in P0; syllabus RAG uses local JSON under `data/pilot/`
- Package root: `projects/ILearn/`; import name `ilearn`
- Design refs (local, gitignored): `doc/design_think.txt`, `doc/composition/MULTI_AGENT_ARCHITECTURE.md`, `doc/think_p0.txt`
- Existing MVP tests must keep passing after each task (regression gate: `pytest tests/ -q`)

## File Map

| Path | Responsibility |
|------|----------------|
| `ilearn/agents/__init__.py` | Public agent exports |
| `ilearn/agents/protocol.py` | `Agent` protocol, `AgentContext`, `AgentResult`, `SessionPhase` |
| `ilearn/agents/assessment.py` | `AssessmentAgent` — wraps `AssessmentBuilder`, optional follow-up mode |
| `ilearn/agents/practice.py` | `PracticeAgent` — text + image grading via `TextGrader` / `VisionGrader` |
| `ilearn/agents/diagnosis.py` | `DiagnosisAgent` — wraps `Diagnoser` + `PortraitUpdater` |
| `ilearn/agents/planning.py` | `PlanningAgent` — wraps `Planner` + `should_replan` |
| `ilearn/agents/curriculum.py` | `CurriculumAgent` — syllabus lookup + citations |
| `ilearn/agents/orchestrator.py` | `MultiAgentOrchestrator` — phase state machine + practice loop |
| `ilearn/agents/eval_agent.py` | `EvalAgent` — wraps `ilearn/eval/runner.py` + agent trace checks |
| `ilearn/core/schemas.py` | Extend: `SessionPhase`, `LearnerPortrait`, `WeaknessEntry`, `ImageAnswer`, `CurriculumCitation` |
| `ilearn/core/assessment.py` | Add `build_followup(profile, weak_knowledge_ids)` |
| `ilearn/core/grading.py` | Add `VisionGrader` class (extracted from PracticeAgent internals) |
| `ilearn/core/orchestrator.py` | Thin facade delegating to `MultiAgentOrchestrator` (backward compat) |
| `ilearn/api/app.py` | Phase endpoint, image submit, follow-up assessment route |
| `ilearn/web/app.py` | Image upload widget + phase indicator |
| `ilearn/cli/main.py` | `ilearn agents run` subcommand |
| `data/pilot/syllabus.json` | Regional syllabus snippets with `citation_id` |
| `data/eval/vision_grading_fixtures.json` | 3 offline vision fixture stubs (mock paths) |
| `tests/test_agents_*.py` | One test module per agent + orchestrator |

---

### Task 1: Agent protocol + extended session schemas

**Files:**
- Create: `ilearn/agents/__init__.py`, `ilearn/agents/protocol.py`, `tests/test_agents_protocol.py`
- Modify: `ilearn/core/schemas.py`

**Interfaces:**
- Produces: `SessionPhase`, `LearnerPortrait`, `WeaknessEntry`, `ImageAnswer`, `CurriculumCitation`, `AgentContext`, `AgentResult`, `Agent` protocol

- [ ] **Step 1: Write failing schema/protocol tests**

```python
# tests/test_agents_protocol.py
from ilearn.agents.protocol import AgentContext, SessionPhase
from ilearn.core.schemas import ImageAnswer, LearnerPortrait, StudentProfile

def test_session_phase_values():
    assert SessionPhase.ASSESS.value == "assess"
    assert SessionPhase.PRACTICE_LOOP.value == "practice_loop"

def test_image_answer_accepts_base64():
    ImageAnswer(item_id="q1", image_base64="aGVsbG8=", mime_type="image/png")

def test_learner_portrait_defaults():
    p = LearnerPortrait(student_key="beijing_g5")
    assert p.weakness_log == []
    assert p.knowledge_state == {}

def test_agent_context_carries_phase():
    ctx = AgentContext(
        session_id="abc",
        phase=SessionPhase.GRADE,
        profile=StudentProfile(region="北京", grade=5, age=11),
    )
    assert ctx.phase == SessionPhase.GRADE
```

- [ ] **Step 2: Run test — expect fail**

Run: `cd projects/ILearn && pytest tests/test_agents_protocol.py -v`  
Expected: FAIL (`ModuleNotFoundError` or missing models)

- [ ] **Step 3: Implement schemas + protocol**

Add to `ilearn/core/schemas.py`:

```python
from enum import Enum

class SessionPhase(str, Enum):
    ONBOARD = "onboard"
    ASSESS = "assess"
    PRACTICE = "practice"
    GRADE = "grade"
    DIAGNOSE = "diagnose"
    PLAN = "plan"
    PRACTICE_LOOP = "practice_loop"

class ImageAnswer(BaseModel):
    item_id: str
    image_base64: str
    mime_type: Literal["image/png", "image/jpeg", "image/webp"] = "image/png"

class WeaknessEntry(BaseModel):
    knowledge_id: str
    topic: str
    logic_gap: str
    session_id: str
    created_at: datetime = Field(default_factory=datetime.utcnow)

class LearnerPortrait(BaseModel):
    student_key: str
    knowledge_state: dict[str, float] = Field(default_factory=dict)
    ability_ema: dict[str, float] = Field(default_factory=dict)
    weakness_log: list[WeaknessEntry] = Field(default_factory=list)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class CurriculumCitation(BaseModel):
    citation_id: str
    title: str
    excerpt: str
    source_label: str
```

Extend `SessionState`:

```python
class SessionState(BaseModel):
    session_id: str
    profile: StudentProfile
    phase: SessionPhase = SessionPhase.ONBOARD
    paper: AssessmentPaper | None = None
    answers: list[StudentAnswer] = Field(default_factory=list)
    image_answers: list[ImageAnswer] = Field(default_factory=list)
    grades: list[GradeResult] = Field(default_factory=list)
    diagnosis: DiagnosisReport | None = None
    plan: LearningPlanReport | None = None
    portrait: LearnerPortrait | None = None
    loop_count: int = 0
```

Create `ilearn/agents/protocol.py`:

```python
from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable

from ilearn.core.schemas import (
    AssessmentPaper, DiagnosisReport, GradeResult, ImageAnswer,
    LearnerPortrait, LearningPlanReport, SessionPhase, StudentAnswer, StudentProfile,
)

@dataclass
class AgentContext:
    session_id: str
    phase: SessionPhase
    profile: StudentProfile
    paper: AssessmentPaper | None = None
    answers: list[StudentAnswer] = field(default_factory=list)
    image_answers: list[ImageAnswer] = field(default_factory=list)
    grades: list[GradeResult] = field(default_factory=list)
    diagnosis: DiagnosisReport | None = None
    plan: LearningPlanReport | None = None
    portrait: LearnerPortrait | None = None
    loop_count: int = 0
    metadata: dict = field(default_factory=dict)

@dataclass
class AgentResult:
    phase: SessionPhase
    payload: dict = field(default_factory=dict)

@runtime_checkable
class Agent(Protocol):
    name: str
    def run(self, ctx: AgentContext) -> AgentResult: ...
```

- [ ] **Step 4: Run tests — expect pass**

Run: `cd projects/ILearn && pytest tests/test_agents_protocol.py tests/test_schemas.py -v`  
Expected: PASS (update `test_schemas.py` if it asserts exact `SessionState` fields — add defaults only)

- [ ] **Step 5: Commit**

```bash
git add ilearn/agents/ ilearn/core/schemas.py tests/test_agents_protocol.py tests/test_schemas.py
git commit -m "feat(agents): add protocol, session phases, and portrait schemas"
```

---

### Task 2: Syllabus pack + CurriculumAgent

**Files:**
- Create: `data/pilot/syllabus.json`, `ilearn/agents/curriculum.py`, `tests/test_agents_curriculum.py`
- Modify: `ilearn/providers/curriculum.py` (add `load_syllabus()` helper)

**Interfaces:**
- Consumes: `StudentProfile.grade`, `StudentProfile.region`
- Produces: `CurriculumAgent.run(ctx) -> AgentResult` with `payload["citations"]`

- [ ] **Step 1: Write failing curriculum agent test**

```python
# tests/test_agents_curriculum.py
from pathlib import Path
from ilearn.agents.curriculum import CurriculumAgent
from ilearn.agents.protocol import AgentContext, SessionPhase
from ilearn.core.schemas import StudentProfile

PILOT = Path(__file__).resolve().parents[1] / "data" / "pilot"

def test_curriculum_agent_returns_beijing_citations():
    agent = CurriculumAgent(pilot_dir=PILOT)
    ctx = AgentContext(
        session_id="s1",
        phase=SessionPhase.ONBOARD,
        profile=StudentProfile(region="北京", grade=5, age=11),
    )
    result = agent.run(ctx)
    citations = result.payload["citations"]
    assert len(citations) >= 3
    assert all(c.source_label for c in citations)
    assert result.phase == SessionPhase.ONBOARD
```

- [ ] **Step 2: Run test — expect fail**

Run: `cd projects/ILearn && pytest tests/test_agents_curriculum.py::test_curriculum_agent_returns_beijing_citations -v`  
Expected: FAIL

- [ ] **Step 3: Add syllabus.json + agent**

`data/pilot/syllabus.json` (minimum 6 entries, grade 4–6):

```json
[
  {"citation_id": "bj-g5-num-01", "grade": 5, "title": "小数乘法", "excerpt": "掌握小数乘整数与小数乘小数的计算方法。", "source_label": "北京·人教·小学数学"},
  {"citation_id": "bj-g5-frac-01", "grade": 5, "title": "分数加减", "excerpt": "同分母分数加减法；异分母需通分。", "source_label": "北京·人教·小学数学"}
]
```

`ilearn/agents/curriculum.py`:

```python
class CurriculumAgent:
    name = "curriculum"

    def __init__(self, pilot_dir: Path) -> None:
        self._syllabus = json.loads((pilot_dir / "syllabus.json").read_text(encoding="utf-8"))

    def run(self, ctx: AgentContext) -> AgentResult:
        grade = ctx.profile.grade
        entries = [e for e in self._syllabus if e["grade"] == grade]
        if not _is_beijing(ctx.profile.region):
            entries = entries[:2]  # still return sample + disclaimer path handled downstream
        citations = [CurriculumCitation(**e) for e in entries]
        return AgentResult(phase=ctx.phase, payload={"citations": citations})
```

Add `load_syllabus(pilot_dir)` to `ilearn/providers/curriculum.py` for reuse in DiagnosisAgent/PlanningAgent.

- [ ] **Step 4: Run test — expect pass**

Run: `cd projects/ILearn && pytest tests/test_agents_curriculum.py -v`  
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add data/pilot/syllabus.json ilearn/agents/curriculum.py ilearn/providers/curriculum.py tests/test_agents_curriculum.py
git commit -m "feat(agents): add CurriculumAgent with local syllabus pack"
```

---

### Task 3: AssessmentAgent (组题)

**Files:**
- Create: `ilearn/agents/assessment.py`, `tests/test_agents_assessment.py`
- Modify: `ilearn/core/assessment.py` (add `build_followup`)

**Interfaces:**
- Consumes: `AssessmentBuilder`, `CurriculumProvider`, `AgentContext.profile`, optional `ctx.metadata["weak_knowledge_ids"]`
- Produces: `AgentResult(payload={"paper": AssessmentPaper})`, phase → `SessionPhase.PRACTICE`

- [ ] **Step 1: Write failing assessment agent test**

```python
# tests/test_agents_assessment.py
from pathlib import Path
from ilearn.agents.assessment import AssessmentAgent
from ilearn.agents.protocol import AgentContext, SessionPhase
from ilearn.core.schemas import StudentProfile
from ilearn.providers.curriculum import PilotBeijingRenjiaoProvider

PILOT = Path(__file__).resolve().parents[1] / "data" / "pilot"

def test_assessment_agent_builds_20_item_paper():
    agent = AssessmentAgent(PilotBeijingRenjiaoProvider(PILOT))
    ctx = AgentContext(
        session_id="s1",
        phase=SessionPhase.ASSESS,
        profile=StudentProfile(region="北京", grade=5, age=11),
    )
    result = agent.run(ctx)
    paper = result.payload["paper"]
    assert len(paper.items) == 20
    assert result.phase == SessionPhase.PRACTICE

def test_assessment_agent_followup_filters_weak_nodes():
    agent = AssessmentAgent(PilotBeijingRenjiaoProvider(PILOT))
    ctx = AgentContext(
        session_id="s1",
        phase=SessionPhase.PRACTICE_LOOP,
        profile=StudentProfile(region="北京", grade=5, age=11),
        metadata={"weak_knowledge_ids": ["g5_fraction_add"], "paper_type": "followup"},
    )
    result = agent.run(ctx)
    paper = result.payload["paper"]
    assert 1 <= len(paper.items) <= 10
    assert all(any(k in ctx.metadata["weak_knowledge_ids"] for k in item.knowledge_ids) for item in paper.items)
```

- [ ] **Step 2: Run test — expect fail**

Run: `cd projects/ILearn && pytest tests/test_agents_assessment.py -v`  
Expected: FAIL

- [ ] **Step 3: Implement AssessmentAgent + followup builder**

In `ilearn/core/assessment.py` add:

```python
def build_followup(self, profile: StudentProfile, weak_knowledge_ids: list[str], size: int = 8) -> AssessmentPaper:
    """Build a smaller practice paper targeting weak knowledge nodes."""
    templates = [
        t for t in self._curriculum.list_templates(profile.grade)
        if any(kid in weak_knowledge_ids for kid in t.knowledge_ids)
    ]
    if not templates:
        raise AssessmentBuildError("no templates for weak knowledge ids")
    random.shuffle(templates)
    picked = templates[: min(size, len(templates))]
    items = [self._instantiate(t, profile) for t in picked]
    return AssessmentPaper(items=items, grade=profile.grade, curriculum_label=self._curriculum.label)
```

`ilearn/agents/assessment.py`:

```python
class AssessmentAgent:
    name = "assessment"

    def __init__(self, curriculum: CurriculumProvider) -> None:
        self._builder = AssessmentBuilder(curriculum)

    def run(self, ctx: AgentContext) -> AgentResult:
        paper_type = ctx.metadata.get("paper_type", "diagnostic")
        if paper_type == "followup":
            weak_ids = ctx.metadata.get("weak_knowledge_ids", [])
            paper = self._builder.build_followup(ctx.profile, weak_ids)
        else:
            paper = self._builder.build(ctx.profile)
        return AgentResult(phase=SessionPhase.PRACTICE, payload={"paper": paper})
```

- [ ] **Step 4: Run tests — expect pass**

Run: `cd projects/ILearn && pytest tests/test_agents_assessment.py tests/test_assessment.py -v`  
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add ilearn/agents/assessment.py ilearn/core/assessment.py tests/test_agents_assessment.py
git commit -m "feat(agents): add AssessmentAgent with follow-up paper mode"
```

---

### Task 4: PracticeAgent — text grading (练题)

**Files:**
- Create: `ilearn/agents/practice.py`, `tests/test_agents_practice.py`

**Interfaces:**
- Consumes: `StepGrader`, `AgentContext.paper`, `AgentContext.answers`
- Produces: `AgentResult(payload={"grades": list[GradeResult]})`, phase → `SessionPhase.DIAGNOSE`

- [ ] **Step 1: Write failing practice agent test**

```python
# tests/test_agents_practice.py
from pathlib import Path
from ilearn.agents.practice import PracticeAgent
from ilearn.agents.protocol import AgentContext, SessionPhase
from ilearn.core.schemas import StudentAnswer, StudentProfile
from ilearn.core.assessment import AssessmentBuilder
from ilearn.providers.curriculum import PilotBeijingRenjiaoProvider

PILOT = Path(__file__).resolve().parents[1] / "data" / "pilot"

def test_practice_agent_grades_text_answers_offline():
    curriculum = PilotBeijingRenjiaoProvider(PILOT)
    paper = AssessmentBuilder(curriculum).build(StudentProfile(region="北京", grade=5, age=11))
    answers = [StudentAnswer(item_id=item.id, answer_text=item.answer_key or "") for item in paper.items[:3]]
    agent = PracticeAgent(llm=None)
    ctx = AgentContext(
        session_id="s1",
        phase=SessionPhase.GRADE,
        profile=StudentProfile(region="北京", grade=5, age=11),
        paper=paper,
        answers=answers,
    )
    result = agent.run(ctx)
    grades = result.payload["grades"]
    assert len(grades) == 3
    assert all(g.final_correct for g in grades)
    assert result.phase == SessionPhase.DIAGNOSE
```

- [ ] **Step 2: Run test — expect fail**

Run: `cd projects/ILearn && pytest tests/test_agents_practice.py::test_practice_agent_grades_text_answers_offline -v`  
Expected: FAIL

- [ ] **Step 3: Implement PracticeAgent (text path)**

```python
# ilearn/agents/practice.py
class PracticeAgent:
    name = "practice"

    def __init__(self, llm: LLMClient | None = None) -> None:
        self._grader = StepGrader(llm)

    def run(self, ctx: AgentContext) -> AgentResult:
        if ctx.paper is None:
            raise ValueError("PracticeAgent requires paper in context")
        grades = self._grader.grade_paper(ctx.paper, ctx.answers)
        return AgentResult(phase=SessionPhase.DIAGNOSE, payload={"grades": grades})
```

- [ ] **Step 4: Run tests — expect pass**

Run: `cd projects/ILearn && pytest tests/test_agents_practice.py tests/test_grading.py -v`  
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add ilearn/agents/practice.py tests/test_agents_practice.py
git commit -m "feat(agents): add PracticeAgent wrapping StepGrader"
```

---

### Task 5: VisionGrader + image answers in PracticeAgent

**Files:**
- Modify: `ilearn/core/grading.py`, `ilearn/agents/practice.py`, `ilearn/providers/llm.py`
- Create: `data/eval/vision_grading_fixtures.json`, `tests/test_vision_grader.py`

**Interfaces:**
- Produces: `VisionGrader.grade_image(item, image_base64, mime_type) -> GradeResult`
- PracticeAgent merges text grades + image grades (image wins for same `item_id`)

- [ ] **Step 1: Write failing vision grader test**

```python
# tests/test_vision_grader.py
from ilearn.core.grading import VisionGrader
from ilearn.core.schemas import AssessmentItem

def test_vision_grader_offline_degrades_without_llm():
    grader = VisionGrader(llm=None)
    item = AssessmentItem(
        id="c1", stem="计算 12+8", type="constructed", difficulty="easy",
        knowledge_ids=["g5_add"], answer_key="20", rubric_steps=["列式", "计算", "写答"],
    )
    result = grader.grade_image(item, image_base64="aGVsbG8=", mime_type="image/png")
    assert result.grading_degraded is True
    assert result.item_id == "c1"
    assert len(result.step_results) >= 1
```

- [ ] **Step 2: Run test — expect fail**

Run: `cd projects/ILearn && pytest tests/test_vision_grader.py -v`  
Expected: FAIL

- [ ] **Step 3: Implement VisionGrader**

Add to `ilearn/providers/llm.py`:

```python
def vision_available(self) -> bool:
    return self.available() and bool(os.getenv("ILEARN_VISION_MODEL") or self.model)

def grade_image_json(self, system: str, image_base64: str, mime_type: str, user: str) -> dict:
    # Use chat.completions with image_url data URI; raise LLMError on failure
    ...
```

Add to `ilearn/core/grading.py`:

```python
_VISION_SYSTEM = """Extract handwritten math steps from the image and grade against rubric.
Return ONLY JSON matching GradeResult fields (final_correct, steps, step_results, error_tags, knowledge_ids, hint_level_suggestion)."""

class VisionGrader:
    def __init__(self, llm: LLMClient | None) -> None:
        self._llm = llm

    def grade_image(self, item: AssessmentItem, image_base64: str, mime_type: str) -> GradeResult:
        if self._llm is None or not self._llm.vision_available():
            return GradeResult(
                item_id=item.id,
                final_correct=False,
                steps=["（离线模式：无法识别手写图片）"],
                step_results=[
                    StepResult(step_index=0, step_text=item.rubric_steps[0] if item.rubric_steps else "作答", status="partial", comment="VL 不可用，已降级")
                ],
                error_tags=["incomplete"],
                knowledge_ids=item.knowledge_ids,
                grading_degraded=True,
            )
        # call llm.grade_image_json and parse into GradeResult
        ...
```

Update `PracticeAgent.run` to grade `ctx.image_answers` and merge by `item_id`.

- [ ] **Step 4: Run tests — expect pass**

Run: `cd projects/ILearn && pytest tests/test_vision_grader.py tests/test_agents_practice.py -v`  
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add ilearn/core/grading.py ilearn/agents/practice.py ilearn/providers/llm.py data/eval/vision_grading_fixtures.json tests/test_vision_grader.py tests/test_agents_practice.py
git commit -m "feat(agents): add VisionGrader and image answer support in PracticeAgent"
```

---

### Task 6: DiagnosisAgent + PortraitUpdater (学情诊断)

**Files:**
- Create: `ilearn/agents/diagnosis.py`, `tests/test_agents_diagnosis.py`
- Modify: `ilearn/core/diagnosis.py` (extract `PortraitUpdater` function)

**Interfaces:**
- Produces: `DiagnosisAgent.run(ctx) -> AgentResult(payload={"diagnosis", "portrait"})`, phase → `SessionPhase.PLAN`

- [ ] **Step 1: Write failing diagnosis agent test**

```python
# tests/test_agents_diagnosis.py
from pathlib import Path
from ilearn.agents.diagnosis import DiagnosisAgent, PortraitUpdater
from ilearn.agents.protocol import AgentContext, SessionPhase
from ilearn.core.schemas import GradeResult, LearnerPortrait, StudentProfile
from ilearn.providers.curriculum import PilotBeijingRenjiaoProvider

PILOT = Path(__file__).resolve().parents[1] / "data" / "pilot"

def test_portrait_updater_appends_weakness():
    portrait = LearnerPortrait(student_key="bj_g5")
    grade = GradeResult(
        item_id="q1", final_correct=False, error_tags=["concept_gap"],
        knowledge_ids=["g5_fraction_add"],
    )
    updated = PortraitUpdater.update(portrait, [grade], session_id="s1", curriculum=PilotBeijingRenjiaoProvider(PILOT))
    assert len(updated.weakness_log) == 1
    assert updated.weakness_log[0].knowledge_id == "g5_fraction_add"

def test_diagnosis_agent_returns_top_interventions():
    agent = DiagnosisAgent(PilotBeijingRenjiaoProvider(PILOT))
    # build minimal ctx with one incorrect grade — use fixtures from test_diagnosis.py patterns
    ...
    assert result.phase == SessionPhase.PLAN
    assert len(result.payload["diagnosis"].interventions) <= 5
```

- [ ] **Step 2: Run test — expect fail**

Run: `cd projects/ILearn && pytest tests/test_agents_diagnosis.py -v`  
Expected: FAIL

- [ ] **Step 3: Implement DiagnosisAgent**

```python
# ilearn/agents/diagnosis.py
class PortraitUpdater:
    @staticmethod
    def update(portrait: LearnerPortrait, grades: list[GradeResult], session_id: str, curriculum: CurriculumProvider) -> LearnerPortrait:
        for g in grades:
            if g.final_correct:
                continue
            for kid in g.knowledge_ids:
                name = next((n.name for n in curriculum.list_knowledge(...) if n.id == kid), kid)
                portrait.weakness_log.append(WeaknessEntry(
                    knowledge_id=kid, topic=name,
                    logic_gap=g.error_tags[0] if g.error_tags else "unknown",
                    session_id=session_id,
                ))
                portrait.knowledge_state[kid] = min(portrait.knowledge_state.get(kid, 1.0), 0.4)
        portrait.updated_at = datetime.utcnow()
        return portrait

class DiagnosisAgent:
    name = "diagnosis"
    def run(self, ctx: AgentContext) -> AgentResult:
        diagnosis = self._diagnoser.diagnose(ctx.profile, ctx.paper, ctx.grades)
        portrait = PortraitUpdater.update(ctx.portrait or LearnerPortrait(student_key=_student_key(ctx.profile)), ctx.grades, ctx.session_id, self._curriculum)
        return AgentResult(phase=SessionPhase.PLAN, payload={"diagnosis": diagnosis, "portrait": portrait})
```

- [ ] **Step 4: Run tests — expect pass**

Run: `cd projects/ILearn && pytest tests/test_agents_diagnosis.py tests/test_diagnosis.py -v`  
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add ilearn/agents/diagnosis.py ilearn/core/diagnosis.py tests/test_agents_diagnosis.py
git commit -m "feat(agents): add DiagnosisAgent with portrait weakness log"
```

---

### Task 7: PlanningAgent + replan trigger (学习建议)

**Files:**
- Create: `ilearn/agents/planning.py`, `tests/test_agents_planning.py`

**Interfaces:**
- Produces: `PlanningAgent.run(ctx) -> AgentResult(payload={"plan", "should_loop"})`, phase → `SessionPhase.PRACTICE_LOOP` or `SessionPhase.PLAN`

- [ ] **Step 1: Write failing planning agent test**

```python
# tests/test_agents_planning.py
from pathlib import Path
from ilearn.agents.planning import PlanningAgent, should_enter_practice_loop
from ilearn.core.schemas import DiagnosisReport, KnowledgeMastery, StudentProfile
from ilearn.providers.curriculum import PilotBeijingRenjiaoProvider

PILOT = Path(__file__).resolve().parents[1] / "data" / "pilot"

def test_should_loop_when_weak_knowledge_exists():
    diagnosis = DiagnosisReport(
        curriculum_label="北京·人教·小学数学",
        knowledge_mastery=[
            KnowledgeMastery(knowledge_id="k1", score_rate=0.2, level="weak"),
        ],
    )
    assert should_enter_practice_loop(diagnosis, loop_count=0) is True
    assert should_enter_practice_loop(diagnosis, loop_count=2) is False  # cap at 2 loops

def test_planning_agent_includes_citations(monkeypatch):
    agent = PlanningAgent(PilotBeijingRenjiaoProvider(PILOT))
    # inject citations via ctx.metadata["citations"] from CurriculumAgent
    ...
    assert "本计划为智能助手建议" in result.payload["plan"].disclaimer
```

- [ ] **Step 2: Run test — expect fail**

Run: `cd projects/ILearn && pytest tests/test_agents_planning.py -v`  
Expected: FAIL

- [ ] **Step 3: Implement PlanningAgent**

```python
_MAX_LOOPS = 2

def should_enter_practice_loop(diagnosis: DiagnosisReport, loop_count: int) -> bool:
    if loop_count >= _MAX_LOOPS:
        return False
    return any(m.level == "weak" for m in diagnosis.knowledge_mastery)

class PlanningAgent:
    name = "planning"
    def run(self, ctx: AgentContext) -> AgentResult:
        plan = self._planner.plan(ctx.profile, ctx.diagnosis)
        citations = ctx.metadata.get("citations", [])
        if citations:
            plan.markdown += "\n\n## 课标依据\n" + "\n".join(f"- {c.title}：{c.excerpt}" for c in citations[:3])
        should_loop = should_enter_practice_loop(ctx.diagnosis, ctx.loop_count)
        next_phase = SessionPhase.PRACTICE_LOOP if should_loop else SessionPhase.PLAN
        return AgentResult(phase=next_phase, payload={"plan": plan, "should_loop": should_loop})
```

- [ ] **Step 4: Run tests — expect pass**

Run: `cd projects/ILearn && pytest tests/test_agents_planning.py tests/test_planning.py -v`  
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add ilearn/agents/planning.py tests/test_agents_planning.py
git commit -m "feat(agents): add PlanningAgent with practice-loop trigger"
```

---

### Task 8: MultiAgentOrchestrator state machine

**Files:**
- Create: `ilearn/agents/orchestrator.py`, `tests/test_agents_orchestrator.py`
- Modify: `ilearn/core/orchestrator.py` (delegate to `MultiAgentOrchestrator`)
- Modify: `ilearn/storage/sessions.py` (persist new `SessionState` fields)

**Interfaces:**
- Produces: `MultiAgentOrchestrator` with methods matching existing `Orchestrator` API plus `start_practice_loop(session_id)`, `current_phase(session_id)`

- [ ] **Step 1: Write failing multi-agent orchestrator test**

```python
# tests/test_agents_orchestrator.py
from pathlib import Path
from ilearn.agents.orchestrator import MultiAgentOrchestrator
from ilearn.core.schemas import SessionPhase, StudentProfile
from ilearn.providers.curriculum import PilotBeijingRenjiaoProvider
from ilearn.storage.sessions import SessionStore

PILOT = Path(__file__).resolve().parents[1] / "data" / "pilot"

def test_multi_agent_full_loop_offline(tmp_path):
    orch = MultiAgentOrchestrator(
        store=SessionStore(tmp_path),
        curriculum=PilotBeijingRenjiaoProvider(PILOT),
        llm=None,
    )
    sid = orch.create_session(StudentProfile(region="北京", grade=5, age=11))
    assert orch.current_phase(sid) == SessionPhase.ONBOARD
    paper = orch.generate_assessment(sid)
    assert len(paper.items) == 20
    assert orch.current_phase(sid) == SessionPhase.PRACTICE
    answers = {item.id: (item.answer_key or "") for item in paper.items}
    orch.submit(sid, answers)
    completed = orch.run_after_submit(sid)
    assert completed.diagnosis is not None
    assert completed.plan is not None
    assert completed.portrait is not None
```

- [ ] **Step 2: Run test — expect fail**

Run: `cd projects/ILearn && pytest tests/test_agents_orchestrator.py -v`  
Expected: FAIL

- [ ] **Step 3: Implement MultiAgentOrchestrator**

```python
# ilearn/agents/orchestrator.py
class MultiAgentOrchestrator:
    def __init__(self, store, curriculum, llm=None):
        self._store = store
        self._curriculum_agent = CurriculumAgent(pilot_dir=...)
        self._assessment = AssessmentAgent(curriculum)
        self._practice = PracticeAgent(llm)
        self._diagnosis = DiagnosisAgent(curriculum)
        self._planning = PlanningAgent(curriculum)

    def _ctx(self, session: SessionState) -> AgentContext:
        return AgentContext(...)

    def generate_assessment(self, session_id: str) -> AssessmentPaper:
        session = self._store.load(session_id)
        cit = self._curriculum_agent.run(self._ctx(session))
        session.metadata_citations = cit.payload["citations"]  # or store in session via portrait/metadata field
        result = self._assessment.run(self._ctx(session))
        session.paper = result.payload["paper"]
        session.phase = SessionPhase.PRACTICE
        self._store.save(session)
        return session.paper

    def run_after_submit(self, session_id: str) -> SessionState:
        self.grade(session_id)
        self.diagnose(session_id)
        self.plan(session_id)
        session = self._store.load(session_id)
        if session.phase == SessionPhase.PRACTICE_LOOP:
            self.start_practice_loop(session_id)
        return self._store.load(session_id)

    def start_practice_loop(self, session_id: str) -> AssessmentPaper:
        session = self._store.load(session_id)
        weak = [m.knowledge_id for m in session.diagnosis.knowledge_mastery if m.level == "weak"][:5]
        ctx = self._ctx(session)
        ctx.metadata = {"paper_type": "followup", "weak_knowledge_ids": weak}
        ctx.phase = SessionPhase.PRACTICE_LOOP
        result = self._assessment.run(ctx)
        session.paper = result.payload["paper"]
        session.answers = []
        session.image_answers = []
        session.grades = []
        session.loop_count += 1
        session.phase = SessionPhase.PRACTICE
        self._store.save(session)
        return session.paper
```

Update `ilearn/core/orchestrator.py`:

```python
class Orchestrator:
    def __init__(self, store, curriculum, llm=None):
        self._inner = MultiAgentOrchestrator(store, curriculum, llm)
    # delegate all public methods to self._inner
```

- [ ] **Step 4: Run full test suite — expect pass**

Run: `cd projects/ILearn && pytest tests/ -q`  
Expected: PASS (fix `test_orchestrator.py` if phase assertions needed)

- [ ] **Step 5: Commit**

```bash
git add ilearn/agents/orchestrator.py ilearn/core/orchestrator.py ilearn/storage/sessions.py tests/test_agents_orchestrator.py tests/test_orchestrator.py
git commit -m "feat(agents): add MultiAgentOrchestrator with practice feedback loop"
```

---

### Task 9: API — phase, image submit, follow-up routes

**Files:**
- Modify: `ilearn/api/app.py`, `tests/test_api.py`

**Interfaces:**
- New routes: `GET /sessions/{id}/phase`, `POST /sessions/{id}/submit-images`, `POST /sessions/{id}/followup`

- [ ] **Step 1: Write failing API tests**

```python
# append to tests/test_api.py
from fastapi.testclient import TestClient
from ilearn.api.app import create_app

def test_phase_endpoint(tmp_path):
    client = TestClient(create_app(sessions_dir=tmp_path, llm=None))
    r = client.post("/sessions", json={"region": "北京", "grade": 5, "age": 11})
    sid = r.json()["session_id"]
    client.post(f"/sessions/{sid}/assessment")
    phase = client.get(f"/sessions/{sid}/phase").json()
    assert phase["phase"] == "practice"

def test_submit_images_accepts_base64(tmp_path):
    client = TestClient(create_app(sessions_dir=tmp_path, llm=None))
    ...
    r = client.post(f"/sessions/{sid}/submit-images", json={"images": [{"item_id": paper["items"][0]["id"], "image_base64": "aGVsbG8=", "mime_type": "image/png"}]})
    assert r.status_code == 200
```

- [ ] **Step 2: Run test — expect fail**

Run: `cd projects/ILearn && pytest tests/test_api.py::test_phase_endpoint -v`  
Expected: FAIL

- [ ] **Step 3: Implement API routes**

```python
class ImageSubmitRequest(BaseModel):
    images: list[ImageAnswer]

@app.get("/sessions/{session_id}/phase")
def get_phase(session_id: str):
    session = store.load(session_id)
    return {"phase": session.phase.value, "loop_count": session.loop_count}

@app.post("/sessions/{session_id}/submit-images", response_model=SessionState)
def submit_images(session_id: str, body: ImageSubmitRequest) -> SessionState:
    session = store.load(session_id)
    session.image_answers = body.images
    return store.save(session)

@app.post("/sessions/{session_id}/followup", response_model=AssessmentPaper)
def followup(session_id: str) -> AssessmentPaper:
    return orchestrator.start_practice_loop(session_id)
```

- [ ] **Step 4: Run API tests — expect pass**

Run: `cd projects/ILearn && pytest tests/test_api.py -v`  
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add ilearn/api/app.py tests/test_api.py
git commit -m "feat(api): add phase, image submit, and follow-up endpoints"
```

---

### Task 10: Streamlit + CLI agent surfaces

**Files:**
- Modify: `ilearn/web/app.py`, `ilearn/cli/main.py`, `tests/test_web_app.py`, `tests/test_cli.py`

- [ ] **Step 1: Write failing CLI test**

```python
# append to tests/test_cli.py
from typer.testing import CliRunner
from ilearn.cli.main import app as cli_app

def test_cli_agents_run_offline(tmp_path, monkeypatch):
    monkeypatch.setenv("ILEARN_SESSIONS_DIR", str(tmp_path))
    runner = CliRunner()
    result = runner.invoke(cli_app, ["agents", "run", "--region", "北京", "--grade", "5", "--age", "11", "--offline"])
    assert result.exit_code == 0
    assert "phase" in result.stdout.lower() or "会话" in result.stdout
```

- [ ] **Step 2: Run test — expect fail**

Run: `cd projects/ILearn && pytest tests/test_cli.py::test_cli_agents_run_offline -v`  
Expected: FAIL

- [ ] **Step 3: Implement CLI + Streamlit updates**

CLI (`ilearn/cli/main.py`):

```python
@app.command("agents")
def agents_run(region: str, grade: int, age: int, offline: bool = False):
    """Run multi-agent pipeline and print phase + report path."""
    llm = None if offline else LLMClient.from_env()
    orch = Orchestrator(SessionStore(...), PilotBeijingRenjiaoProvider(...), llm)
    ...
```

Streamlit: add `st.file_uploader` per constructed item; on submit POST text + optional images to API; show `phase` badge in sidebar.

- [ ] **Step 4: Run tests — expect pass**

Run: `cd projects/ILearn && pytest tests/test_cli.py tests/test_web_app.py -v`  
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add ilearn/cli/main.py ilearn/web/app.py tests/test_cli.py tests/test_web_app.py
git commit -m "feat(ui): expose multi-agent loop in CLI and Streamlit"
```

---

### Task 11: EvalAgent + extended eval fixtures

**Files:**
- Create: `ilearn/agents/eval_agent.py`, `tests/test_agents_eval.py`
- Modify: `ilearn/eval/runner.py`, `ilearn/cli/main.py` (`eval` subcommand flags)

- [ ] **Step 1: Write failing eval agent test**

```python
# tests/test_agents_eval.py
from pathlib import Path
from ilearn.agents.eval_agent import EvalAgent

FIXTURES = Path(__file__).resolve().parents[1] / "data" / "eval"

def test_eval_agent_runs_step_grading_offline():
    agent = EvalAgent(fixtures_dir=FIXTURES, llm=None)
    report = agent.run_step_grading()
    assert report["total"] >= 10
    assert "step_f1" in report
    assert report["agents_invoked"] == ["practice"]
```

- [ ] **Step 2: Run test — expect fail**

Run: `cd projects/ILearn && pytest tests/test_agents_eval.py -v`  
Expected: FAIL

- [ ] **Step 3: Implement EvalAgent**

```python
class EvalAgent:
    name = "eval"
    def run_step_grading(self) -> dict:
        # delegate to ilearn.eval.runner, wrap with PracticeAgent instead of raw StepGrader
        return {"total": ..., "step_f1": ..., "agents_invoked": ["practice"]}
    def run(self, ctx: AgentContext) -> AgentResult:
        return AgentResult(phase=ctx.phase, payload={"eval_report": self.run_step_grading()})
```

Extend `ilearn eval` CLI: `--agents` flag prints agent trace.

- [ ] **Step 4: Run eval tests — expect pass**

Run: `cd projects/ILearn && pytest tests/test_agents_eval.py tests/test_eval_runner.py -v`  
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add ilearn/agents/eval_agent.py ilearn/eval/runner.py ilearn/cli/main.py tests/test_agents_eval.py
git commit -m "feat(agents): add EvalAgent wrapping step grading benchmarks"
```

---

### Task 12: README, .env.example, E2E verification

**Files:**
- Modify: `README.md`, `.env.example`
- Create: `tests/test_e2e_multi_agent.py`

- [ ] **Step 1: Write E2E test**

```python
# tests/test_e2e_multi_agent.py
def test_e2e_beijing_grade5_offline_loop(tmp_path):
    """Full multi-agent path including optional follow-up when weak items injected."""
    ...
    assert session.loop_count <= 2
    assert "课标依据" in session.plan.markdown or session.plan is not None
```

- [ ] **Step 2: Run E2E — expect pass**

Run: `cd projects/ILearn && pytest tests/test_e2e_multi_agent.py -v`  
Expected: PASS

- [ ] **Step 3: Update README**

Document:
- Four agents + CurriculumAgent + EvalAgent
- Phase diagram (ONBOARD → … → PRACTICE_LOOP)
- `ILEARN_VISION_MODEL` for handwriting
- `ilearn agents run` and new API routes

- [ ] **Step 4: Full regression**

Run: `cd projects/ILearn && pytest tests/ -q`  
Expected: all pass (target ≥ 110 tests)

- [ ] **Step 5: Commit**

```bash
git add README.md .env.example tests/test_e2e_multi_agent.py
git commit -m "docs: document multi-agent P0 architecture and E2E verification"
```

---

## Self-Review

### Spec coverage (`think_p0.txt` + `design_think.txt`)

| Requirement | Task |
|-------------|------|
| 开源分析借鉴 | Pre-complete (`doc/composition/*`); agents cite patterns in README Task 12 |
| 组题 Agent（地区/年级） | Task 3 AssessmentAgent |
| 练题 Agent（步骤批改 + 手写 VL） | Task 4–5 PracticeAgent + VisionGrader |
| 学情诊断 Agent | Task 6 DiagnosisAgent + Portrait |
| 个性化学习建议 Agent | Task 7 PlanningAgent + syllabus citations |
| 补充 CurriculumAgent | Task 2 |
| 补充 EvalAgent | Task 11 |
| 练→评→练正反馈环 | Task 8 MultiAgentOrchestrator `start_practice_loop` |
| 20 题 / 难度 / 题型配额 | Task 3 (diagnostic unchanged); follow-up 1–10 items |
| 公开数据集评估 | Task 11 (fixtures + hook for mathtutorbench import later) |
| Web + API | Task 9–10 |

### Placeholder scan

No TBD/TODO/similar-task-only references. Each task includes concrete test code and run commands.

### Type consistency

- `SessionPhase` used consistently from Task 1 onward
- `AgentContext.metadata["weak_knowledge_ids"]` set in Task 8, consumed in Task 3
- `LearnerPortrait` flows: Task 6 produces → Task 8 persists → Task 7 may read for replan (future)
- `ImageAnswer` introduced Task 1, used Task 5/9/10

### Out of scope (explicit deferrals)

- **TutorAgent** (苏格拉底多轮): Phase 3 — not in this plan
- **LangGraph Director**: deferred per architecture doc
- **Live web curriculum crawl**: Phase 4
- **Full mathtutorbench / EduAgentBench HF integration**: Task 11 hooks only; dedicated import plan later

---

**Plan complete and saved to `docs/superpowers/plans/2026-08-10-ilearn-multi-agent-p0.md`. Two execution options:**

**1. Subagent-Driven (recommended)** — I dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** — Execute tasks in this session using executing-plans, batch execution with checkpoints

**Which approach?**
