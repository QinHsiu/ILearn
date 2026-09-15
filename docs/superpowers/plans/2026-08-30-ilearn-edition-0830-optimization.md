# Edition 0830 Cognitive Graph + Style + Geometry Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Upgrade ILearn diagnosis to skill+Bloom cognitive layers, add implicit learning-style inference with planning adaptation, ship JSXGraph interactive geometry with trajectory analysis, and wire processed exports for open datasets—without breaking the existing 20-item paper / enrichment / scientific-plan contracts.

**Architecture:** Keep the flat `data/knowledge_graph.json` KP graph for cold-start prerequisites. Add a parallel cognitive skill layer (`data/cognitive_skills.json` + `ilearn/core/cognitive_profile.py`) that DiagnosisAgent consults for root-cause enrichment. Add `LearningStyleInferer` and fold style adaptation into PlanningAgent’s scientific plan payload. Add a React JSXGraph component plus `PracticeAgent.analyze_geo_interaction`. Prefer extending existing MM-K12 / TAL importers with a thin `scripts/export_processed_bank.py` rather than rewriting import pipelines.

**Tech Stack:** Python 3.11+, Pydantic, pytest; React 19 + Vite + Vitest; JSXGraph (npm); existing FastAPI / MultiAgentOrchestrator.

## Global Constraints

- Full diagnostic paper stays **exactly 20** items; adaptive anchor length may vary.
- Pilot: **北京** / **人教版** / grades **4–6** (fail closed outside).
- Do **not** commit `doc/` or secrets; plan/spec under `docs/superpowers/` is fine for this edition.
- Do **not** break `diagnosis_enrichment` keys already used by PlanningAgent (`weak_skills`, `prerequisite_gaps`, `learning_advice`) — **extend** with new keys.
- Cognitive skills for MVP: **3 units** (分数意义 / 分数比较 / 分数加减), **≥10 skills each** (30+ total), grades 4–5.
- Learning style labels: `visual` | `auditory` | `kinesthetic` | `reading` only.
- JSXGraph: no global `window.__checkGeoAnswer` in production API — expose check via React callback / imperative ref instead (spec sketch used window for illustration only).
- External search (DuckDuckGo / SerpAPI) and Agora low-code classroom are **out of scope** for this code plan (optional Day 6–7 product work).
- Dataset “500+” target: export cleaned items from existing importers / pilot banks; do not download HF datasets in CI tests (fixtures only).
- Follow existing agent sync style (`def run`, not async) unless a module already uses async.

## File Structure

| Path | Responsibility |
| --- | --- |
| `ilearn/core/cognitive_profile.py` | `CognitiveDimension`, `SkillNode`, `CognitiveSkillGraph` load/query |
| `data/cognitive_skills.json` | Seed cognitive skill graph (分数 3 units) |
| `scripts/build_cognitive_graph.py` | Validate / optionally merge LLM draft → JSON (offline, no live LLM required in tests) |
| `ilearn/agents/diagnosis.py` | `diagnose_with_cognitive_profile` + enrich payload |
| `ilearn/core/learning_style.py` | `LearningStyleInferer` Bayesian-lite |
| `ilearn/agents/planning.py` | `generate_personalized_plan` / style_adaptation on scientific plan |
| `ilearn/agents/practice.py` | `analyze_geo_interaction` |
| `frontend/src/components/DynamicGeometryQuestion.tsx` | JSXGraph board + interaction log callback |
| `frontend/src/pages/Assessment.tsx` | Render geo items when type/config present |
| `scripts/export_processed_bank.py` | Map importer output → `data/processed/*.json` |
| `data/processed/.gitkeep` | Ensure processed dir exists |
| Tests under `tests/` + `frontend/src/components/*.test.tsx` | TDD coverage per task |

---

### Task 1: Cognitive skill model + seed graph

**Files:**
- Create: `ilearn/core/cognitive_profile.py`
- Create: `data/cognitive_skills.json`
- Create: `tests/fixtures/cognitive_skills_tiny.json`
- Test: `tests/test_cognitive_profile.py`

**Interfaces:**
- Consumes: none
- Produces:
  - `CognitiveDimension` enum: `remember|understand|apply|analyze|evaluate|create`
  - `@dataclass SkillNode`: `skill_id: str`, `name: str`, `knowledge_point: str`, `dimension: CognitiveDimension`, `prerequisites: list[str]`, `grade: int`, `examples: list[str]`
  - `class CognitiveSkillGraph`:
    - `__init__(self, path: str | Path | None = None) -> None`
    - `get(self, skill_id: str) -> SkillNode | None`
    - `by_knowledge_point(self, kp: str) -> list[SkillNode]`
    - `get_prerequisites(self, skill_id: str) -> list[str]`
    - `all_skills(self) -> list[SkillNode]`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_cognitive_profile.py
from pathlib import Path
from ilearn.core.cognitive_profile import CognitiveDimension, CognitiveSkillGraph

FIXTURE = Path(__file__).parent / "fixtures" / "cognitive_skills_tiny.json"

def test_load_skill_and_prereqs():
    g = CognitiveSkillGraph(FIXTURE)
    node = g.get("fraction_001")
    assert node is not None
    assert node.dimension == CognitiveDimension.UNDERSTAND
    assert node.knowledge_point == "分数的意义"
    assert g.get_prerequisites("fraction_002") == ["fraction_001"]
    assert len(g.by_knowledge_point("分数的意义")) >= 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_cognitive_profile.py::test_load_skill_and_prereqs -v`  
Expected: FAIL with import/module not found

- [ ] **Step 3: Write minimal implementation**

```python
# ilearn/core/cognitive_profile.py
from __future__ import annotations
import json
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

class CognitiveDimension(Enum):
    REMEMBER = "remember"
    UNDERSTAND = "understand"
    APPLY = "apply"
    ANALYZE = "analyze"
    EVALUATE = "evaluate"
    CREATE = "create"

@dataclass
class SkillNode:
    skill_id: str
    name: str
    knowledge_point: str
    dimension: CognitiveDimension
    prerequisites: list[str] = field(default_factory=list)
    grade: int = 4
    examples: list[str] = field(default_factory=list)

class CognitiveSkillGraph:
    def __init__(self, path: str | Path | None = None) -> None:
        if path is None:
            root = Path(__file__).resolve().parents[2]
            path = root / "data" / "cognitive_skills.json"
        self.path = Path(path)
        self._nodes: dict[str, SkillNode] = {}
        self._load()

    def _load(self) -> None:
        raw = json.loads(self.path.read_text(encoding="utf-8"))
        skills = raw["skills"] if isinstance(raw, dict) and "skills" in raw else raw
        for item in skills:
            dim = CognitiveDimension(item["dimension"])
            node = SkillNode(
                skill_id=item["skill_id"],
                name=item["name"],
                knowledge_point=item["knowledge_point"],
                dimension=dim,
                prerequisites=list(item.get("prerequisites") or []),
                grade=int(item.get("grade", 4)),
                examples=list(item.get("examples") or []),
            )
            self._nodes[node.skill_id] = node

    def get(self, skill_id: str) -> SkillNode | None:
        return self._nodes.get(skill_id)

    def by_knowledge_point(self, kp: str) -> list[SkillNode]:
        return [n for n in self._nodes.values() if n.knowledge_point == kp]

    def get_prerequisites(self, skill_id: str) -> list[str]:
        node = self._nodes.get(skill_id)
        return list(node.prerequisites) if node else []

    def all_skills(self) -> list[SkillNode]:
        return list(self._nodes.values())
```

Fixture `tests/fixtures/cognitive_skills_tiny.json`:

```json
{
  "skills": [
    {
      "skill_id": "fraction_001",
      "name": "理解分数单位",
      "knowledge_point": "分数的意义",
      "dimension": "understand",
      "prerequisites": [],
      "grade": 4,
      "examples": []
    },
    {
      "skill_id": "fraction_002",
      "name": "用分数表示部分",
      "knowledge_point": "分数的意义",
      "dimension": "apply",
      "prerequisites": ["fraction_001"],
      "grade": 4,
      "examples": []
    }
  ]
}
```

Seed `data/cognitive_skills.json`: same schema; **≥30** skills across units `分数的意义`, `分数比较`, `分数加减法` (mix remember/understand/apply/analyze). Map `knowledge_point` aliases to legacy KPs where useful (`frac_add_same`, etc.) via optional field `legacy_knowledge_ids: list[str]` on each skill (supported by loader if present; ignored by tiny fixture).

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_cognitive_profile.py -v`  
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add ilearn/core/cognitive_profile.py data/cognitive_skills.json tests/fixtures/cognitive_skills_tiny.json tests/test_cognitive_profile.py
git commit -m "feat(0830): add cognitive skill graph model and seed data"
```

---

### Task 2: Build/validate script for cognitive graph

**Files:**
- Create: `scripts/build_cognitive_graph.py`
- Test: `tests/test_build_cognitive_graph.py`

**Interfaces:**
- Consumes: `CognitiveSkillGraph` / JSON schema from Task 1
- Produces:
  - `validate_cognitive_skills(path: Path) -> list[str]` — returns list of error strings (empty = ok)
  - CLI: `python scripts/build_cognitive_graph.py --check data/cognitive_skills.json` exit 0/1
  - Acceptance: ≥3 distinct `knowledge_point`, ≥10 skills per unit in production seed

- [ ] **Step 1: Write the failing test**

```python
from pathlib import Path
from scripts.build_cognitive_graph import validate_cognitive_skills
# Prefer import via package-less path: importlib or move validate into ilearn.core.cognitive_profile

def test_validate_accepts_tiny_fixture():
    from ilearn.core.cognitive_profile import validate_cognitive_skills
    errs = validate_cognitive_skills(Path("tests/fixtures/cognitive_skills_tiny.json"))
    assert errs == []

def test_validate_rejects_bad_prereq():
    from ilearn.core.cognitive_profile import validate_cognitive_skills
    import tempfile, json
    bad = {"skills": [{"skill_id": "a", "name": "x", "knowledge_point": "u",
                       "dimension": "remember", "prerequisites": ["missing"], "grade": 4}]}
    p = Path(tempfile.mkdtemp()) / "bad.json"
    p.write_text(json.dumps(bad), encoding="utf-8")
    errs = validate_cognitive_skills(p)
    assert any("missing" in e for e in errs)
```

Put `validate_cognitive_skills` in `ilearn/core/cognitive_profile.py`; script is a thin CLI wrapper.

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_build_cognitive_graph.py -v`  
Expected: FAIL (validate missing)

- [ ] **Step 3: Implement validate + CLI**

```python
def validate_cognitive_skills(path: Path) -> list[str]:
    g = CognitiveSkillGraph(path)
    errors: list[str] = []
    ids = {n.skill_id for n in g.all_skills()}
    for n in g.all_skills():
        for p in n.prerequisites:
            if p not in ids:
                errors.append(f"{n.skill_id}: unknown prerequisite {p}")
    return errors
```

```python
# scripts/build_cognitive_graph.py
from pathlib import Path
import sys
from ilearn.core.cognitive_profile import validate_cognitive_skills, CognitiveSkillGraph

def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    path = Path(argv[argv.index("--check") + 1] if "--check" in argv else "data/cognitive_skills.json")
    errs = validate_cognitive_skills(path)
    if errs:
        print("\n".join(errs))
        return 1
    g = CognitiveSkillGraph(path)
    units = {}
    for s in g.all_skills():
        units.setdefault(s.knowledge_point, 0)
        units[s.knowledge_point] += 1
    print(f"ok: {len(g.all_skills())} skills, units={units}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
```

Also assert in `tests/test_build_cognitive_graph.py` that production seed has ≥3 units and each ≥10 skills:

```python
def test_seed_coverage():
    from ilearn.core.cognitive_profile import CognitiveSkillGraph
    from pathlib import Path
    root = Path(__file__).resolve().parents[1]
    g = CognitiveSkillGraph(root / "data" / "cognitive_skills.json")
    units = {}
    for s in g.all_skills():
        units.setdefault(s.knowledge_point, []).append(s)
    assert len(units) >= 3
    for name, skills in units.items():
        assert len(skills) >= 10, name
```

- [ ] **Step 4: Run tests**

Run: `python -m pytest tests/test_build_cognitive_graph.py tests/test_cognitive_profile.py -v`  
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add ilearn/core/cognitive_profile.py scripts/build_cognitive_graph.py tests/test_build_cognitive_graph.py data/cognitive_skills.json
git commit -m "feat(0830): validate cognitive skill graph coverage"
```

---

### Task 3: DiagnosisAgent cognitive root-cause enrichment

**Files:**
- Modify: `ilearn/agents/diagnosis.py`
- Test: `tests/test_cognitive_diagnosis_0830.py`

**Interfaces:**
- Consumes: `CognitiveSkillGraph.get`, `get_prerequisites`; evidence dicts/objects with `skill_id` / `knowledge_id` / `correct|is_correct`
- Produces:
  - `DiagnosisAgent.diagnose_with_cognitive_profile(self, evidence_log: list[Any], *, skill_id: str | None = None) -> dict[str, Any]`
  - Return shape: `{ "root_cause": str, "gap_skill": str, "recommendation": str, "dimension": str | None }`
  - `enrich_with_prerequisites` extended keys: `cognitive_findings: list[dict]`, optionally set flag `cognitive_gap`
  - `_get_dimension_advice(dimension: CognitiveDimension) -> str` static map in Chinese

Evidence resolution order for a wrong answer:
1. If event has `skill_id`, use it.
2. Else map `knowledge_id` → first weak-ish skill via `by_knowledge_point` / `legacy_knowledge_ids`.
3. Walk prerequisites; if any unmastered → `root_cause="前置技能缺失"`.
4. Else → `root_cause=f"{dimension.value}层次不足"`.

Mastery helper: reuse `_is_skill_mastered` for KP ids; for skill_ids treat evidence with matching `skill_id` the same way (score ≥0.7).

- [ ] **Step 1: Write the failing test**

```python
from ilearn.agents.diagnosis import DiagnosisAgent
from ilearn.core.cognitive_profile import CognitiveSkillGraph
from pathlib import Path

def test_cognitive_diagnosis_prereq_gap():
    agent = DiagnosisAgent(
        PilotBeijingRenjiaoProvider(PILOT),
        cognitive_graph=CognitiveSkillGraph(FIXTURE),
    )
    evidence = [{"skill_id": "fraction_002", "is_correct": False}]
    out = agent.diagnose_with_cognitive_profile(evidence, skill_id="fraction_002")
    assert out["root_cause"] == "前置技能缺失"
    assert out["gap_skill"] == "fraction_001"

def test_cognitive_diagnosis_dimension_gap_when_prereq_ok():
    agent = DiagnosisAgent(
        PilotBeijingRenjiaoProvider(PILOT),
        cognitive_graph=CognitiveSkillGraph(FIXTURE),
    )
    evidence = [
        {"skill_id": "fraction_001", "is_correct": True},
        {"skill_id": "fraction_001", "is_correct": True},
        {"skill_id": "fraction_002", "is_correct": False},
    ]
    out = agent.diagnose_with_cognitive_profile(evidence, skill_id="fraction_002")
    assert "层次不足" in out["root_cause"]
    assert out["gap_skill"] == "fraction_002"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_cognitive_diagnosis_0830.py -v`  
Expected: FAIL (`cognitive_graph` / method missing)

- [ ] **Step 3: Implement**

Extend `__init__` with `cognitive_graph: CognitiveSkillGraph | None = None` (default load production file if exists else None).

Implement `diagnose_with_cognitive_profile` and wire into `enrich_with_prerequisites` / `run` so `diagnosis_enrichment["cognitive_findings"]` is a list of findings for failed evidence items that resolve to a skill.

- [ ] **Step 4: Run tests**

Run: `python -m pytest tests/test_cognitive_diagnosis_0830.py tests/test_diagnosis_enrichment_0825.py -v`  
Expected: PASS (0825 enrichment unchanged)

- [ ] **Step 5: Commit**

```bash
git add ilearn/agents/diagnosis.py tests/test_cognitive_diagnosis_0830.py
git commit -m "feat(0830): cognitive-profile root-cause diagnosis enrichment"
```

---

### Task 4: Learning style inferer

**Files:**
- Create: `ilearn/core/learning_style.py`
- Test: `tests/test_learning_style.py`

**Interfaces:**
- Consumes: behavior dict with optional keys `diagram_expand_count`, `audio_play_count`, `total_questions`, `avg_response_time`, `visual_question_correct`, `visual_question_total`
- Produces:
  - `LearningStyleInferer.PRIOR: dict[str, float]`
  - `infer(self, behavior: dict) -> str` → one of four styles
  - `posterior(self, behavior: dict) -> dict[str, float]` for debugging/tests

Likelihood heuristics (deterministic, no sklearn):
- high `diagram_expand_rate` or `visual_question_correct_rate` → boost visual
- high `audio_play_rate` → boost auditory
- low `avg_response_time` with high interaction counts → boost kinesthetic
- otherwise reading stays competitive via prior

- [ ] **Step 1: Write the failing test**

```python
from ilearn.core.learning_style import LearningStyleInferer

def test_visual_bias_from_diagrams():
    style = LearningStyleInferer().infer({
        "diagram_expand_count": 8,
        "total_questions": 10,
        "audio_play_count": 0,
        "avg_response_time": 20,
        "visual_question_correct": 5,
        "visual_question_total": 5,
    })
    assert style == "visual"

def test_posterior_sums_to_one():
    post = LearningStyleInferer().posterior({"total_questions": 1})
    assert abs(sum(post.values()) - 1.0) < 1e-6
```

- [ ] **Step 2: Run to fail**

Run: `python -m pytest tests/test_learning_style.py -v`  
Expected: FAIL

- [ ] **Step 3: Implement** per edition_0830 §3.1 (simple Bayesian product of prior × likelihood, normalize).

- [ ] **Step 4: Run to pass**

Run: `python -m pytest tests/test_learning_style.py -v`  
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add ilearn/core/learning_style.py tests/test_learning_style.py
git commit -m "feat(0830): Bayesian-lite learning style inference"
```

---

### Task 5: PlanningAgent style adaptation

**Files:**
- Modify: `ilearn/agents/planning.py`
- Test: `tests/test_style_planning_0830.py`

**Interfaces:**
- Consumes: `LearningStyleInferer`; diagnosis + optional `ctx.metadata["behavior"]`
- Produces:
  - `generate_personalized_plan(self, diagnosis, learning_style: str, *, enrichment: dict | None = None, profile: StudentProfile | None = None) -> dict`
  - Returns scientific-plan-compatible dict **plus** `style_adaptation: { "material_type": list[str], "suggestion": str }` and `learning_style: str`
  - `run()`: if `metadata.behavior` present, infer style and merge into `scientific_plan`; also append a short markdown subsection `## 学习风格适配`

Style mapping (minimum):
```python
{
  "visual": {"material_type": ["diagram", "chart", "interactive_geometry"], "suggestion": "推荐使用图形化材料辅助理解"},
  "auditory": {"material_type": ["audio_explanation", "read_aloud"], "suggestion": "推荐听讲解或跟读例题"},
  "kinesthetic": {"material_type": ["simulation", "drag_drop", "manipulative"], "suggestion": "推荐动手操作类练习"},
  "reading": {"material_type": ["worked_example", "text_summary"], "suggestion": "推荐文字例题与总结笔记"},
}
```

- [ ] **Step 1: Write failing test**

```python
def test_personalized_plan_adds_style_adaptation():
    agent = PlanningAgent(PilotBeijingRenjiaoProvider(PILOT))
    diagnosis = DiagnosisReport(
        curriculum_label="beijing-renjiao",
        knowledge_mastery=[KnowledgeMastery(knowledge_id="frac_mult", score_rate=0.2, level="weak")],
        interventions=[],
    )
    out = agent.generate_personalized_plan(diagnosis, "visual")
    assert out["learning_style"] == "visual"
    assert "diagram" in out["style_adaptation"]["material_type"]

def test_run_infers_style_from_behavior_metadata():
    # AgentContext with metadata.behavior heavy on diagrams → scientific_plan.learning_style == "visual"
    ...
```

- [ ] **Step 2: Run to fail**

Run: `python -m pytest tests/test_style_planning_0830.py -v`

- [ ] **Step 3: Implement** without changing `PlanDay` schema (markdown + payload only), keep `generate_scientific_plan` and call it from `generate_personalized_plan`.

- [ ] **Step 4: Regression**

Run: `python -m pytest tests/test_style_planning_0830.py tests/test_scientific_planning_0825.py -v`  
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add ilearn/agents/planning.py tests/test_style_planning_0830.py
git commit -m "feat(0830): planning adapts materials to learning style"
```

---

### Task 6: PracticeAgent geometry trajectory analysis

**Files:**
- Modify: `ilearn/agents/practice.py`
- Test: `tests/test_geo_interaction_0830.py`

**Interfaces:**
- Consumes: `interaction_log: list[dict]` with `type`, `position: [x,y]`, optional `timestamp`; `correct_answer: dict` with `x`, `y`
- Produces: `analyze_geo_interaction(self, interaction_log, correct_answer) -> dict` with keys `status` (`confident|explored|struggling|misguided|empty`) and `diagnosis: str`

Helpers (module-private):
- `_is_position_correct(pos, answer, tol=0.1) -> bool`
- `_calculate_path_length(log) -> float` sum of Euclidean segments between consecutive positions

Logic from edition_0830 §4.3.

- [ ] **Step 1: Write failing tests** for confident / explored / struggling / empty log.

- [ ] **Step 2: Run to fail**

Run: `python -m pytest tests/test_geo_interaction_0830.py -v`

- [ ] **Step 3: Implement** on `PracticeAgent` (no change to `run()` contract required for MVP; method callable from API later).

- [ ] **Step 4: Pass**

Run: `python -m pytest tests/test_geo_interaction_0830.py -v`

- [ ] **Step 5: Commit**

```bash
git add ilearn/agents/practice.py tests/test_geo_interaction_0830.py
git commit -m "feat(0830): analyze JSXGraph interaction trajectories"
```

---

### Task 7: Frontend DynamicGeometryQuestion + Assessment hook

**Files:**
- Modify: `frontend/package.json` — add dependency `jsxgraph`
- Create: `frontend/src/components/DynamicGeometryQuestion.tsx`
- Create: `frontend/src/components/DynamicGeometryQuestion.test.tsx`
- Modify: `frontend/src/pages/Assessment.tsx` — if item has `geo_config` (or `type === "construct"` when that ItemType exists; prefer optional `geo_config` on item metadata from API to avoid schema churn) render the component
- Optional: extend `AssessmentItem` with `geo_config: dict | None = None` in `ilearn/core/schemas.py` only if Assessment needs it for typing; otherwise keep frontend-only optional field on API JSON

**Interfaces:**
- Props: `{ question: { id: string; type: 'drag_point' | 'drag_slider' | 'construct_shape'; config: { boundingbox?: number[]; start?: [number, number]; snapToGrid?: boolean }; correct_answer: { x: number; y: number } }; onInteraction: (log: GeoInteractionEvent) => void; onReady?: (api: { checkAnswer: () => boolean }) => void }`
- Emits drag events: `{ type: 'drag_point'; questionId: string; position: [number, number]; timestamp: number }`
- Cleanup: `board.destroy()` / `JXG.JSXGraph.freeBoard(board)` on unmount

- [ ] **Step 1: Install**

```bash
cd frontend && npm install jsxgraph && npm install -D @types/jsxgraph || true
```

- [ ] **Step 2: Write component test** mocking `jsxgraph` module initBoard/create/on/delete.

- [ ] **Step 3: Implement component** using `useRef` + `useEffect`; **do not** assign `window.__checkGeoAnswer`; use `onReady` instead.

- [ ] **Step 4: Wire Assessment.tsx** behind a narrow condition so existing multimodal/choice flows unchanged.

- [ ] **Step 5: Run**

Run: `cd frontend && npm test -- DynamicGeometryQuestion`  
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add frontend/package.json frontend/package-lock.json frontend/src/components/DynamicGeometryQuestion.tsx frontend/src/components/DynamicGeometryQuestion.test.tsx frontend/src/pages/Assessment.tsx
git commit -m "feat(0830): JSXGraph dynamic geometry question component"
```

---

### Task 8: Processed bank export script (open datasets)

**Files:**
- Create: `scripts/export_processed_bank.py`
- Create: `data/processed/.gitkeep`
- Create: `tests/fixtures/mm_k12_export_tiny.jsonl` (2–3 lines) if needed
- Test: `tests/test_export_processed_bank.py`

**Interfaces:**
- Reuse `ilearn.data.importers.mm_k12` / `tal_scq5k` record mappers
- `export_mm_k12(raw_path: Path, output_path: Path) -> int` returns count written
- Output record shape:
```python
{
  "id": str,
  "stem": str,
  "type": str,
  "options": list,
  "correct_answer": str,
  "difficulty": str | int,
  "grade": int,
  "skill_id": str,  # mapped knowledge / skill
  "source": "mm_k12" | "tal_scq5k",
}
```
- CLI: `python scripts/export_processed_bank.py --source mm_k12 --input <path> --output data/processed/mm_k12_cleaned.json`
- Test uses tiny fixture; production 500+ is operational (run against local `data/raw/` when present), not a CI hard fail if raw missing.

- [ ] **Step 1–4:** TDD export count ≥ fixture size; commit.

```bash
git commit -m "feat(0830): export cleaned MM-K12/TAL items to data/processed"
```

---

### Task 9: VERSION + regression wrap

**Files:**
- Modify: `VERSION.md` — Edition 0830 section
- Modify: `README.md` test count badge if present
- Run full suite

- [ ] **Step 1: Run**

```bash
python -m pytest -q
cd frontend && npm test
python scripts/build_cognitive_graph.py --check data/cognitive_skills.json
```

Expected: all green; seed coverage print ok.

- [ ] **Step 2: Update VERSION.md** with Edition 0830 bullets (cognitive skills, style planning, geo analysis, processed export).

- [ ] **Step 3: Commit**

```bash
git add VERSION.md README.md
git commit -m "docs(0830): record Edition 0830 optimization in VERSION"
```

---

## Self-Review

1. **Spec coverage (edition_0830):**
   - §2 Cognitive graph → Tasks 1–3
   - §3 Learning style + planning → Tasks 4–5
   - §4 JSXGraph + PracticeAgent → Tasks 6–7
   - §5 Dataset import → Task 8 (extends existing importers; no DuckDuckGo)
   - §1 Agora low-code / AI-coding strategy → documented as out-of-scope product guidance
   - §6 Day 6–7 deploy → not automated in this plan (manual)

2. **Placeholders:** none intentional; geo ItemType kept optional via `geo_config` to avoid large schema migration.

3. **Type consistency:** enrichment keys additive; `style_adaptation` / `cognitive_findings` / `analyze_geo_interaction` status enum values stable across tasks.

---

## Execution Handoff

Plan saved to `docs/superpowers/plans/2026-08-30-ilearn-edition-0830-optimization.md`.

**Two execution options:**

1. **Subagent-Driven (recommended)** — fresh subagent per task + review between tasks  
2. **Inline Execution** — execute tasks in this session using executing-plans  

User requested implementation after the plan (`再实施`); defaulting to **Inline Execution** unless they interrupt.
