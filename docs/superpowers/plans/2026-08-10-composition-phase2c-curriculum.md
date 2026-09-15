# Composition Phase 2c — Curriculum & Multi-Subject Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close TODO Phase 2c — swappable curriculum retrievers (keyword + stdlib “vector”), stronger citation↔item binding, multi-subject quota templates, a second region pack stub, and K12-wide grade typing with pilot still serving 4–6 math.

**Architecture:** Introduce `CurriculumRetriever` Protocol; keep existing keyword RAG as default; add `HashVectorRetriever` (fixed-dim hashed n-gram vectors, **no Qdrant dependency**). Qdrant remains an optional backend stub raising clear error if selected without install. Widen `GradeLevel` to 1–12; pilot providers reject unsupported grades with clear errors. Multi-subject via `SubjectQuotaTemplate` (math live, chinese stub quotas).

**Tech Stack:** Python 3.11+, pydantic v2, pytest, stdlib only (no new pip deps).

## Global Constraints

- Branch from: `feature/ilearn-phase2b-planning-tutor` (234 tests)
- No new third-party packages (YAGNI; HashVector ≈ vector RAG acceptance without Qdrant server)
- Pilot math still **北京·人教 4–6**; K12 grades typed but unsupported grades fail closed at provider
- Paper quotas for math unchanged when subject=math
- Product copy: K12; cite `TODO.md` A-03, OPT-041, OPT-042, OPT-003, D-04, E-05
- Regression: `python -m pytest tests/ -q` after each task

## File Map

| Path | Responsibility |
|------|----------------|
| `ilearn/providers/retriever.py` | **New** Protocol + Keyword + HashVector + QdrantStub |
| `ilearn/providers/curriculum_rag.py` | Delegate to retriever backends |
| `ilearn/agents/assessment.py` | Per-knowledge citation binding |
| `ilearn/core/assessment.py` | SubjectQuotaTemplate / multi-subject mix |
| `ilearn/core/schemas.py` | `GradeLevel=1..12`, `Subject`, profile.subject |
| `data/pilot/regions/shanghai_sources.json` | **New** second-region stub |
| `data/pilot/subjects/chinese_quota.json` | **New** layered quota stub |
| `ilearn/providers/curriculum.py` | Multi-region load path; grade gate |
| `doc/composition/TODO.md` | Tick Phase 2c |

---

### Task 1: CurriculumRetriever Protocol + Keyword backend (OPT-042 base)

**Files:**
- Create: `ilearn/providers/retriever.py`, `tests/test_retriever_protocol.py`
- Modify: `ilearn/providers/curriculum_rag.py` to wrap KeywordRetriever

**Interfaces:**

```python
class CurriculumRetriever(Protocol):
    def retrieve(self, profile: StudentProfile, query: str, *, top_k: int = 5) -> list[CurriculumCitation]: ...

class KeywordCurriculumRetriever:
    def __init__(self, sources: list[dict]) -> None: ...
    def retrieve(...) -> list[CurriculumCitation]: ...  # move logic from CurriculumRagRetriever

def get_retriever(backend: str, pilot_dir: Path) -> CurriculumRetriever:
    if backend == "keyword": return KeywordCurriculumRetriever(load_curriculum_sources(pilot_dir))
    if backend == "hash_vector": return HashVectorCurriculumRetriever(...)  # Task 2
    if backend == "qdrant": return QdrantCurriculumRetriever(...)  # Task 2 stub
    raise ValueError(f"unknown retriever backend: {backend}")
```

`CurriculumRagRetriever` becomes thin facade defaulting to keyword.

- [ ] **Step 1: Write failing test**

```python
def test_get_retriever_keyword_returns_beijing_hits():
    from pathlib import Path
    from ilearn.providers.retriever import get_retriever
    from ilearn.core.schemas import StudentProfile
    PILOT = Path(__file__).resolve().parents[1] / "data" / "pilot"
    r = get_retriever("keyword", PILOT)
    cites = r.retrieve(StudentProfile(region="北京", grade=5, age=11), "分数加减", top_k=3)
    assert len(cites) >= 1
```

- [ ] **Step 2–5: Implement; commit** `feat(curriculum): add CurriculumRetriever protocol with keyword backend`

---

### Task 2: HashVector retriever + Qdrant stub (A-03)

**Files:**
- Modify: `ilearn/providers/retriever.py`, `tests/test_hash_vector_retriever.py`

**Interfaces:**
- `HashVectorCurriculumRetriever`: embed text via hashed character bigrams into dim=256 dense vector (list[float] or array via pure Python); cosine similarity rank
- `QdrantCurriculumRetriever.retrieve` raises `NotImplementedError("Install qdrant-client and configure ILEARN_QDRANT_URL — Phase 2c stub")`

- [ ] **Step 1: Write failing tests**

```python
def test_hash_vector_retriever_ranks_fraction_query():
    ...
    cites = get_retriever("hash_vector", PILOT).retrieve(profile, "同分母分数", top_k=3)
    assert cites
    assert cites[0].source_id

def test_qdrant_backend_raises_clear_error():
    import pytest
    with pytest.raises(NotImplementedError, match="qdrant"):
        get_retriever("qdrant", PILOT).retrieve(profile, "分数", top_k=1)
```

- [ ] **Step 2–5: Implement hashing embed + cosine; commit** `feat(curriculum): add hash-vector RAG backend and Qdrant stub`

---

### Task 3: Per-knowledge citation binding (OPT-041)

**Files:**
- Modify: `ilearn/agents/assessment.py`, `ilearn/core/diagnosis.py` or planning report
- Create: `tests/test_citation_binding_per_knowledge.py`

**Interfaces:**
- Instead of `citation_ids[:1]` for all items, match item.knowledge_ids / stem tokens to citation keywords/title; assign best `source_id` per item
- Diagnosis interventions get `curriculum_objective_ids` field (add to Intervention if missing)

```python
def bind_citations_to_item(item: AssessmentItem, citations: list[CurriculumCitation]) -> list[str]:
    # score citations against knowledge_ids joined + stem; return top 1-2 source_ids
```

- [ ] **Step 1: Write failing test** that two items with different knowledge prefer different citations when sources differ by keywords

- [ ] **Step 2–5: Implement; commit** `feat(curriculum): bind citations per item knowledge`

---

### Task 4: Multi-subject quota templates (OPT-003)

**Files:**
- Create: `data/pilot/subjects/chinese_quota.json`, `ilearn/core/subject_quotas.py`, `tests/test_subject_quotas.py`
- Modify: `ilearn/core/schemas.py` (`Subject = Literal["math","chinese"]`, `StudentProfile.subject: Subject = "math"`)
- Modify: `ilearn/core/assessment.py` to select MIX from subject template when subject!=math use layered 基础/提高/拓展 counts from JSON (for chinese stub: e.g. 8/8/4 easy/med/hard still 20 but labeled layers)

Chinese stub JSON:

```json
{
  "subject": "chinese",
  "layers": {"basic": 10, "raising": 8, "extension": 2},
  "types": {"choice": 8, "fill": 8, "constructed": 4}
}
```

Math keeps existing MIX_BLUEPRINT. AssessmentBuilder.build reads `profile.subject`.

- [ ] **Step 1: Write failing tests for load_quota + math unchanged + chinese layer sums to 20**

- [ ] **Step 2–5: Implement; for chinese without templates, AssessmentBuildError with clear message OR generate blueprint slots only (fill may fail) — prefer: chinese builds blueprint quotas but fill uses math templates only if no chinese templates → skip fill test; instead test `build_blueprint_for_subject` returns 20 slots**

- [ ] **Commit** `feat(assessment): add multi-subject layered quota templates`

---

### Task 5: Second region pack stub (D-04)

**Files:**
- Create: `data/pilot/regions/shanghai_renjiao/curriculum_sources.json` (2–3 entries grade 5)
- Modify: `ilearn/providers/curriculum_rag.py` / retriever to also load `regions/*/curriculum_sources.json` merged
- Create: `tests/test_multi_region_sources.py`

**Interfaces:**
- Profile region containing `上海` / `shanghai` retrieves shanghai sources
- Beijing profile still hits beijing sources

- [ ] **Step 1: Write failing test**

```python
def test_shanghai_profile_retrieves_shanghai_sources():
    cites = get_retriever("keyword", PILOT).retrieve(
        StudentProfile(region="上海", grade=5, age=11), "分数", top_k=3
    )
    assert cites
    assert any("上海" in (c.source_label or "") or "sh-" in c.source_id for c in cites)
```

- [ ] **Step 2–5: Implement merge load; commit** `feat(curriculum): load multi-region curriculum source packs`

---

### Task 6: K12 grade typing (E-05)

**Files:**
- Modify: `ilearn/core/schemas.py` — `GradeLevel = Literal[1,2,3,4,5,6,7,8,9,10,11,12]` on StudentProfile, KnowledgeNode, ItemTemplate, papers as appropriate
- Modify: `ilearn/providers/curriculum.py` — `list_knowledge` / `list_templates` raise `CurriculumError` if grade not in {4,5,6} for pilot provider
- Modify: Streamlit grade selectbox to show 1–12 but caption “试点内容目前覆盖 4–6 年级数学”
- Create: `tests/test_k12_grade_gate.py`

**Interfaces:**
- `StudentProfile(region="北京", grade=8, age=14)` validates schema
- `PilotBeijingRenjiaoProvider.list_knowledge(8)` raises with message containing `试点`

- [ ] **Step 1: Write failing tests**

```python
def test_profile_accepts_grade_8():
    StudentProfile(region="北京", grade=8, age=14)

def test_pilot_provider_rejects_grade_8():
    import pytest
    with pytest.raises(Exception, match="试点"):
        PilotBeijingRenjiaoProvider(PILOT).list_knowledge(8)
```

- [ ] **Step 2–5: Implement; fix any Literal[4,5,6] breakages in tests that construct invalid combos; commit** `feat(schemas): widen grade to K12 with pilot provider gate`

---

### Task 7: CurriculumAgent backend switch + E2E + docs

**Files:**
- Modify: `ilearn/agents/curriculum.py` — read `ILEARN_RETRIEVER_BACKEND` env default `keyword`, allow `hash_vector`
- Create: `tests/test_e2e_phase2c.py` — beijing g5 keyword path still works; shanghai retrieve works
- Modify: `doc/composition/TODO.md`, README (retriever backends, multi-region, K12 grades), `.env.example`

- [ ] **Step 1: Write E2E / env backend test**

```python
def test_curriculum_agent_hash_vector_backend(monkeypatch):
    monkeypatch.setenv("ILEARN_RETRIEVER_BACKEND", "hash_vector")
    ...
```

- [ ] **Step 2–5: Wire; full suite; commit** `feat(curriculum): Phase2c backend switch and docs`

---

## Self-Review

| TODO ID | Task |
|---------|------|
| OPT-042 | 1, 2, 7 |
| A-03 vector | 2 (hash vector; Qdrant stub) |
| OPT-041 | 3 |
| OPT-003 | 4 |
| D-04 | 5 |
| E-05 | 6 |
| Docs/E2E | 7 |

---

**Plan complete and saved to `docs/superpowers/plans/2026-08-10-composition-phase2c-curriculum.md`.**
