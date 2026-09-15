# Edition 0826 Curriculum Data Expansion Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Expand ILearn pilot curriculum data—accurate chapter-aligned knowledge points and ≥8 examples per knowledge_id for grades 4–6—by importing open datasets listed in `doc/edition_0826.txt`.

**Architecture:** Keep runtime code unchanged; add a **build pipeline** under `ilearn/data/` that reads gitignored raw dumps in `data/raw/`, normalizes external IDs to ILearn `knowledge_id` slugs, and **regenerates** committed pilot artifacts (`knowledge.json`, `example_bank.json`, `knowledge_graph.json`, `progress_mapping.json`). Legacy 13 pilot ids remain via `kp_alias.json` so Edition 0825 adaptive/diagnostic flows keep working.

**Tech Stack:** Python 3.11+, stdlib + optional `datasets` (Hugging Face) for MM-K12/TAL-SCQ5K; pytest for importer/build tests; existing `KnowledgeGraph`, `load_example_bank`, `PilotBeijingRenjiaoProvider`.

## Global Constraints

- Full diagnostic paper stays **exactly 20** items (`validate_paper` quotas unchanged).
- Do **not** commit `doc/` or `docs/` (local only; `.gitignore` already excludes `docs/`).
- Do **not** git-commit unless the user explicitly asks.
- Raw external datasets live in `data/raw/` (**gitignored**); only normalized pilot JSON is committed.
- Windows-safe JSON: use English structural keys (`chapters`) in `progress_mapping.json`; avoid raw Chinese keys in committed JSON.
- RCAE dataset is **CC BY-NC 4.0**—attribute in `data/pilot/ATTRIBUTION.md`; do not use for commercial deployment without license review.
- Preserve backward compatibility: existing 13 `knowledge_id` values (`mult_3digit`, `frac_add_same`, …) must remain valid aliases.
- Pilot scope for this edition: **北京·人教·小学数学·4–6 年级** first; grades 1–3 deferred.

## Requirements Source

`doc/edition_0826.txt` — priority resources:

| Priority | Resource | URL / Source |
|----------|----------|--------------|
| P0 | RCAE 小学数学知识图谱 | `digitalboy/RCAE_graph_data` → `china_primary_school_math_knowledge_graph.json` |
| P0 | MM-K12 | Hugging Face `Cierra0506/MM-K12` |
| P0 | 好未来小学数学知识点标签体系 | https://ai.100tal.com/openData/knowledgeGraph (manual download) |
| P1 | TAL-SCQ5K 中文 | Hugging Face `math-eval/TAL-SCQ5K` |
| P2 | MV-MATH, OATutor, DeepMind dataset | out of scope for Edition 0826 |

**Success metrics (Edition 0826 done when):**

- `knowledge.json`: ≥80 nodes for grades 4–6 (vs current 13).
- `example_bank.json`: every `knowledge_id` in pilot has ≥8 examples (vs current ~2–3).
- `knowledge_graph.json`: ≥80 nodes; every node has `grade`; prerequisite edges sourced from RCAE `Prerequisite` type.
- `progress_mapping.json`: chapter titles match 人教版 unit names (not slug ids).
- All existing tests pass + new importer/build tests green.

---

## File Structure (created / modified)

| Path | Responsibility |
|------|----------------|
| `data/raw/.gitkeep` | Placeholder; raw dumps gitignored |
| `data/raw/README.md` | Download instructions (committed) |
| `data/curriculum/kp_alias.json` | External label → ILearn `knowledge_id` + legacy 13 aliases |
| `ilearn/data/__init__.py` | Package marker |
| `ilearn/data/kp_ids.py` | Slugify + alias resolution |
| `ilearn/data/importers/rcae_graph.py` | RCAE → knowledge + graph |
| `ilearn/data/importers/mm_k12.py` | MM-K12 → example_bank entries |
| `ilearn/data/importers/tal_scq5k.py` | TAL-SCQ5K → hard examples + route metadata |
| `ilearn/data/build_pilot.py` | Orchestrates full rebuild + validation |
| `scripts/download_raw_data.py` | Optional HF/git download helper |
| `tests/test_kp_ids.py` | Slug + alias tests |
| `tests/test_rcae_importer.py` | RCAE fixture tests |
| `tests/test_mm_k12_importer.py` | MM-K12 fixture tests |
| `tests/test_build_pilot.py` | End-to-end build on tiny fixtures |
| `data/pilot/knowledge.json` | **Regenerated** (expanded) |
| `data/pilot/example_bank.json` | **Regenerated** (expanded) |
| `data/knowledge_graph.json` | **Regenerated** (expanded) |
| `data/curriculum/progress_mapping.json` | **Regenerated** (chapter-aligned) |
| `data/pilot/ATTRIBUTION.md` | License attribution |
| `VERSION.md` | Edition 0826 changelog row |

**Runtime files unchanged:** `ilearn/core/knowledge_graph.py`, `ilearn/providers/curriculum.py`, `ilearn/agents/assessment.py` (no API changes).

---

### Task 1: Raw data layout + gitignore

**Files:**
- Create: `data/raw/.gitkeep`
- Create: `data/raw/README.md`
- Modify: `.gitignore` (add `data/raw/*` except `.gitkeep` and `README.md`)

**Interfaces:**
- Produces: documented paths for importers:
  - `data/raw/rcae/china_primary_school_math_knowledge_graph.json`
  - `data/raw/mm_k12/` (HF cache or exported JSONL)
  - `data/raw/tal_kg/` (manual ZIP from 好未来)
  - `data/raw/tal_scq5k/` (HF export)

- [ ] **Step 1: Add gitignore rules**

```gitignore
# External curriculum dumps (Edition 0826)
data/raw/*
!data/raw/.gitkeep
!data/raw/README.md
```

- [ ] **Step 2: Create `data/raw/README.md`** with download commands:

```markdown
# Raw curriculum data (not committed)

## RCAE (required)
curl -L -o data/raw/rcae/china_primary_school_math_knowledge_graph.json \
  https://raw.githubusercontent.com/digitalboy/RCAE_graph_data/main/china_primary_school_math_knowledge_graph.json

## MM-K12 (required)
python scripts/download_raw_data.py --dataset mm_k12

## TAL KG (optional, manual)
Download from https://ai.100tal.com/openData/knowledgeGraph → extract to data/raw/tal_kg/

## TAL-SCQ5K (optional)
python scripts/download_raw_data.py --dataset tal_scq5k
```

- [ ] **Step 3: Verify** `data/raw/` exists and is ignored by git (except README).

---

### Task 2: Knowledge-point ID normalization

**Files:**
- Create: `ilearn/data/__init__.py`
- Create: `ilearn/data/kp_ids.py`
- Create: `data/curriculum/kp_alias.json`
- Test: `tests/test_kp_ids.py`

**Interfaces:**
- Produces:
  - `slugify_kp(name: str) -> str` — ASCII slug, max 48 chars
  - `resolve_kp_id(label: str, alias_map: dict) -> str | None`
  - `load_alias_map(path: Path) -> dict[str, str]`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_kp_ids.py
from pathlib import Path
import json
from ilearn.data.kp_ids import slugify_kp, resolve_kp_id, load_alias_map

def test_slugify_kp_ascii():
    assert slugify_kp("三位数乘两位数") == "mult_3digit"  # via alias
    assert slugify_kp("Hello World!") == "hello_world"

def test_resolve_legacy_alias():
    alias = {"三位数乘两位数": "mult_3digit", "mult_3digit": "mult_3digit"}
    assert resolve_kp_id("三位数乘两位数", alias) == "mult_3digit"
    assert resolve_kp_id("mult_3digit", alias) == "mult_3digit"
    assert resolve_kp_id("未知知识点", alias) is None

def test_load_alias_map_from_repo():
    root = Path(__file__).resolve().parents[1]
    m = load_alias_map(root / "data" / "curriculum" / "kp_alias.json")
    assert m["三位数乘两位数"] == "mult_3digit"
    assert m["同分母分数加法"] == "frac_add_same"
```

- [ ] **Step 2: Run test — expect FAIL**

Run: `pytest tests/test_kp_ids.py -v`

- [ ] **Step 3: Implement `kp_ids.py` + seed `kp_alias.json`**

```python
# ilearn/data/kp_ids.py
import re
from pathlib import Path
import json

_LEGACY = {
    "三位数乘两位数": "mult_3digit",
    "长方形面积": "rect_area",
    "角的度量": "angle_measure",
    "平行与垂直": "parallel_perp",
    "小数乘法": "dec_mult",
    "同分母分数加法": "frac_add_same",
    "分数乘法": "frac_mult",
    "简易方程": "simple_eq",
    "分数除法": "frac_div",
    "比和比例": "ratio",
    "圆的面积": "circle_area",
    "百分数应用": "percent",
    "因数与倍数": "factors",
}

def slugify_kp(name: str, alias_map: dict[str, str] | None = None) -> str:
    alias_map = alias_map or {}
    if name in alias_map:
        return alias_map[name]
    slug = re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")
    return slug[:48] or "kp_unknown"

def resolve_kp_id(label: str, alias_map: dict[str, str]) -> str | None:
    if label in alias_map:
        return alias_map[label]
    slug = slugify_kp(label, alias_map)
    return slug if slug != "kp_unknown" else None

def load_alias_map(path: Path) -> dict[str, str]:
    data = json.loads(path.read_text(encoding="utf-8"))
    merged = dict(_LEGACY)
    merged.update(data.get("aliases", {}))
    for v in _LEGACY.values():
        merged[v] = v
    return merged
```

```json
// data/curriculum/kp_alias.json
{
  "aliases": {}
}
```

- [ ] **Step 4: Run test — expect PASS**

Run: `pytest tests/test_kp_ids.py -v`

---

### Task 3: RCAE graph importer

**Files:**
- Create: `ilearn/data/importers/__init__.py`
- Create: `ilearn/data/importers/rcae_graph.py`
- Create: `tests/fixtures/rcae_tiny.json`
- Test: `tests/test_rcae_importer.py`

**Interfaces:**
- Consumes: RCAE JSON (inspect on first load; expect `nodes` + `edges` or list of node records—adapter handles both)
- Produces:
  - `parse_rcae(path: Path) -> tuple[list[dict], list[dict]]`  # nodes, edges
  - `to_ilearn_knowledge(nodes, alias_map, grades=(4,5,6)) -> list[dict]`
  - `to_ilearn_graph(nodes, edges, alias_map, grades=(4,5,6)) -> dict[str, dict]`

ILearn knowledge node shape (match existing `data/pilot/knowledge.json`):

```python
{"id": "mult_3digit", "grade": 4, "name": "三位数乘两位数", "ability_tags": ["mental_math"]}
```

ILearn graph node shape (match `data/knowledge_graph.json`):

```python
{"prerequisites": ["..."], "related": ["..."], "grade": 4}
```

Edge mapping: `Prerequisite` → `prerequisites`; `RelatedTo` | `ComplementaryTo` | `Includes` (reverse) → `related`.

- [ ] **Step 1: Create tiny fixture** (`tests/fixtures/rcae_tiny.json`) with 5 nodes, 4 edges including one `Prerequisite` chain and grade metadata if present in source.

- [ ] **Step 2: Write failing tests**

```python
# tests/test_rcae_importer.py
from pathlib import Path
from ilearn.data.importers.rcae_graph import parse_rcae, to_ilearn_knowledge, to_ilearn_graph
from ilearn.data.kp_ids import load_alias_map

FIX = Path(__file__).parent / "fixtures" / "rcae_tiny.json"
ALIAS = Path(__file__).resolve().parents[1] / "data" / "curriculum" / "kp_alias.json"

def test_parse_rcae_returns_nodes_and_edges():
    nodes, edges = parse_rcae(FIX)
    assert len(nodes) >= 3
    assert len(edges) >= 1

def test_to_ilearn_graph_prerequisite_chain():
    nodes, edges = parse_rcae(FIX)
    alias = load_alias_map(ALIAS)
    graph = to_ilearn_graph(nodes, edges, alias, grades=(4, 5, 6))
    assert "frac_mult" in graph or any("prerequisites" in v for v in graph.values())
    for node in graph.values():
        assert "grade" in node
        assert isinstance(node["prerequisites"], list)
        assert isinstance(node["related"], list)
```

- [ ] **Step 3: Implement `rcae_graph.py`** — on first real file load, log node/edge schema; map `grade` from node properties (`grade`, `年级`, or infer from `Includes` chapter parent).

- [ ] **Step 4: Run tests — expect PASS**

Run: `pytest tests/test_rcae_importer.py -v`

---

### Task 4: MM-K12 example importer

**Files:**
- Create: `ilearn/data/importers/mm_k12.py`
- Create: `tests/fixtures/mm_k12_tiny.jsonl`
- Test: `tests/test_mm_k12_importer.py`

**Interfaces:**
- Produces:
  - `iter_mm_k12_records(path: Path) -> Iterator[dict]`
  - `to_example_entry(record: dict, alias_map: dict) -> tuple[str, dict] | None`  # (knowledge_id, example dict)

Example bank entry shape (match existing):

```python
{
  "id": "ex-mm-0001",
  "stem": "计算 125 × 36 = ?",
  "chapter": "四年级上册 第4章 三位数乘两位数",
  "label": "北京·人教·小学数学",
  "answer": "4500",
  "difficulty": "easy",
  "source": "mm_k12"
}
```

Mapping rules:
- Filter `grade` in {4, 5, 6} when field present; else include with `knowledge_id` from keyword match against alias map.
- Cap **12 examples per knowledge_id** (keep smallest difficulty spread: 4 easy / 4 medium / 4 hard).
- Skip records without parseable numeric answer.

- [ ] **Step 1: Create fixture** with 6 records covering 2 knowledge_ids.

- [ ] **Step 2: Write failing tests**

```python
# tests/test_mm_k12_importer.py
from pathlib import Path
from ilearn.data.importers.mm_k12 import iter_mm_k12_records, to_example_entry
from ilearn.data.kp_ids import load_alias_map

FIX = Path(__file__).parent / "fixtures" / "mm_k12_tiny.jsonl"
ALIAS = Path(__file__).resolve().parents[1] / "data" / "curriculum" / "kp_alias.json"

def test_iter_mm_k12_records():
    rows = list(iter_mm_k12_records(FIX))
    assert len(rows) == 6

def test_to_example_entry_maps_knowledge_id():
    alias = load_alias_map(ALIAS)
    rows = list(iter_mm_k12_records(FIX))
    mapped = [to_example_entry(r, alias) for r in rows]
    mapped = [m for m in mapped if m]
    assert mapped
    kid, ex = mapped[0]
    assert kid
    assert ex["stem"]
    assert ex["answer"]
    assert ex["source"] == "mm_k12"
```

- [ ] **Step 3: Implement `mm_k12.py`**

- [ ] **Step 4: Run tests — expect PASS**

Run: `pytest tests/test_mm_k12_importer.py -v`

---

### Task 5: TAL-SCQ5K supplemental importer (P1)

**Files:**
- Create: `ilearn/data/importers/tal_scq5k.py`
- Create: `tests/fixtures/tal_scq5k_tiny.jsonl`
- Test: `tests/test_tal_scq5k_importer.py`

**Interfaces:**
- Produces:
  - `to_example_from_scq5k(record: dict, alias_map: dict) -> tuple[str, dict] | None`
  - `extract_kp_routes(record: dict) -> list[str]` — raw Chinese kp chain labels

Use for **hard** difficulty examples only; merge into `example_bank` without duplicating stems (hash stem prefix).

- [ ] **Step 1–4:** Same TDD cycle as Task 4 with 3 fixture records containing `knowledge_point_routes` and `answer_analysis`.

---

### Task 6: Build orchestrator + validation

**Files:**
- Create: `ilearn/data/build_pilot.py`
- Create: `scripts/download_raw_data.py`
- Test: `tests/test_build_pilot.py`

**Interfaces:**
- Produces:
  - `build_pilot(raw_dir: Path, out_pilot: Path, out_graph: Path, out_progress: Path, alias_path: Path) -> BuildReport`
  - `BuildReport` dataclass: `knowledge_count`, `example_count`, `graph_nodes`, `warnings: list[str]`

Build order:
1. Load alias map
2. RCAE → merge into `knowledge.json` + `knowledge_graph.json` (grades 4–6)
3. MM-K12 → merge into `example_bank.json`
4. TAL-SCQ5K → append hard examples
5. Preserve legacy 13 knowledge entries (union, don't drop)
6. Rebuild `progress_mapping.json` from RCAE chapter `Includes` hierarchy + manual overrides in `data/curriculum/chapter_overrides.json`
7. Validate:
   - Every knowledge_id in `knowledge.json` has ≥1 example (warn if <8)
   - Every knowledge_id appears in `knowledge_graph.json`
   - No orphan prerequisites (warn only)

CLI:

```bash
python -m ilearn.data.build_pilot \
  --raw-dir data/raw \
  --pilot-dir data/pilot \
  --graph data/knowledge_graph.json \
  --progress data/curriculum/progress_mapping.json
```

- [ ] **Step 1: Write failing integration test** using only fixtures (no network):

```python
# tests/test_build_pilot.py
from pathlib import Path
from ilearn.data.build_pilot import build_pilot

def test_build_pilot_from_fixtures(tmp_path: Path):
    raw = tmp_path / "raw"
    # copy tests/fixtures/* into raw/rcae, raw/mm_k12 layout
    pilot = tmp_path / "pilot"
    graph = tmp_path / "knowledge_graph.json"
    progress = tmp_path / "progress_mapping.json"
    alias = Path(__file__).resolve().parents[1] / "data" / "curriculum" / "kp_alias.json"
    report = build_pilot(raw, pilot, graph, progress, alias)
    assert report.knowledge_count >= 13
    assert (pilot / "knowledge.json").exists()
    assert (pilot / "example_bank.json").exists()
```

- [ ] **Step 2: Implement `build_pilot.py`**

- [ ] **Step 3: Run test — expect PASS**

Run: `pytest tests/test_build_pilot.py -v`

- [ ] **Step 4: Run full build locally** (after user downloads raw data):

```bash
python -m ilearn.data.build_pilot
```

Expected stdout includes: `knowledge_count >= 80`, `examples_per_kp min >= 8` for grade 4–6 pilot slice.

---

### Task 7: Chapter overrides + progress mapping alignment

**Files:**
- Create: `data/curriculum/chapter_overrides.json`
- Modify: output `data/curriculum/progress_mapping.json` via build

**Interfaces:**
- Consumes: RCAE chapter nodes + manual overrides
- Produces: progress mapping with human-readable chapter titles:

```json
{
  "chapter": "三位数乘两位数",
  "weeks": [1, 2, 3, 4, 5, 6, 7, 8],
  "knowledge_ids": ["mult_3digit", "mult_3digit_vertical", "..."]
}
```

Seed `chapter_overrides.json` with current 0825 mapping for grades 4–6 (from existing `progress_mapping.json`) so build never regresses chapter order.

- [ ] **Step 1: Export current mapping to overrides file**
- [ ] **Step 2: Extend build to merge RCAE chapters + overrides**
- [ ] **Step 3: Test** `tests/test_progress_mapper.py` still passes with rebuilt file

Run: `pytest tests/test_progress_mapper.py tests/test_knowledge_graph.py -v`

---

### Task 8: Regression + pilot invariants

**Files:**
- Modify: `tests/test_source_refs.py` (optional: assert min example count)
- Create: `tests/test_pilot_data_quality.py`

- [ ] **Step 1: Add quality test**

```python
# tests/test_pilot_data_quality.py
import json
from pathlib import Path

PILOT = Path(__file__).resolve().parents[1] / "data" / "pilot"
GRAPH = Path(__file__).resolve().parents[1] / "data" / "knowledge_graph.json"

def test_pilot_knowledge_minimum_coverage():
    knowledge = json.loads((PILOT / "knowledge.json").read_text(encoding="utf-8"))
    g46 = [k for k in knowledge if k["grade"] in (4, 5, 6)]
    assert len(g46) >= 80

def test_example_bank_minimum_per_kp():
    bank = json.loads((PILOT / "example_bank.json").read_text(encoding="utf-8"))
    knowledge_ids = {k["id"] for k in json.loads((PILOT / "knowledge.json").read_text(encoding="utf-8"))}
    for kid in knowledge_ids:
        assert len(bank.get(kid, [])) >= 8, f"{kid} has fewer than 8 examples"

def test_legacy_ids_still_present():
    legacy = {"mult_3digit", "frac_add_same", "frac_mult", "percent"}
    ids = {k["id"] for k in json.loads((PILOT / "knowledge.json").read_text(encoding="utf-8"))}
    assert legacy <= ids
```

- [ ] **Step 2: Run full suite**

Run: `pytest -q`

Expected: all prior 418+ tests pass; new quality tests pass after full build.

- [ ] **Step 3: Smoke adaptive assessment**

Run: `pytest tests/test_adaptive_assessment.py tests/test_source_refs.py -v`

---

### Task 9: Attribution + VERSION.md

**Files:**
- Create: `data/pilot/ATTRIBUTION.md`
- Modify: `VERSION.md`, `README.md` test badge if count changed

- [ ] **Step 1: Write ATTRIBUTION.md** citing RCAE (CC BY-NC 4.0), MM-K12, TAL-SCQ5K, 好未来 KG with URLs.

- [ ] **Step 2: Add Edition 0826 section to VERSION.md**

```markdown
## Edition 0826 — Curriculum data expansion (pilot)

- Import pipeline: RCAE graph + MM-K12 examples (+ optional TAL-SCQ5K)
- Pilot knowledge nodes 13 → 80+ (grades 4–6); examples per kp ≥ 8
- `data/curriculum/kp_alias.json` preserves legacy knowledge_id compatibility
- New tests: `test_kp_ids`, `test_rcae_importer`, `test_mm_k12_importer`, `test_build_pilot`, `test_pilot_data_quality`
```

- [ ] **Step 3: Update test count in README badge after pytest**

---

## Self-Review (spec coverage)

| edition_0826 requirement | Task |
|---------------------------|------|
| MM-K12 bulk import | Task 4, 6 |
| RCAE knowledge graph | Task 3, 6 |
| TAL-SCQ5K kp routes + analysis | Task 5 |
| 人教版 chapter alignment | Task 7 |
| 好未来 KG | Task 6 (optional merge via alias enrichment) |
| importer code pattern | Tasks 2–6 |
| MV-MATH / OATutor / DeepMind | Deferred (P2+) |
| Full paper 20 items | Global constraint — no task changes quotas |

## Execution order

```
Task 1 → 2 → 3 → 4 → 5 → 6 → 7 → 8 → 9
         ↘ fixtures can be built in parallel after Task 2
```

## Local debug (after Task 6)

```bash
# 1. Download raw data (see data/raw/README.md)
python scripts/download_raw_data.py --dataset mm_k12

# 2. Rebuild pilot pack
python -m ilearn.data.build_pilot

# 3. Verify
pytest tests/test_pilot_data_quality.py tests/test_adaptive_assessment.py -v

# 4. API smoke
uvicorn ilearn.api.app:app --reload --host 127.0.0.1 --port 8000
```

## Risks + mitigations

| Risk | Mitigation |
|------|------------|
| RCAE JSON schema differs from assumption | `parse_rcae` logs schema; fixture-first TDD |
| MM-K12 lacks 人教 chapter tags | Keyword + alias map; manual `kp_alias.json` entries |
| Network blocked for HF download | Commit tiny fixtures; user downloads manually |
| CC BY-NC license on RCAE | ATTRIBUTION.md + non-commercial note in VERSION |
| Expanded graph breaks diagnosis | Keep legacy ids; fail-soft `KnowledgeGraph` for unknown ids |
| `test_pilot_data_quality` too strict before build | Gate: skip if `ILearn_SKIP_DATA_QUALITY=1` during importer-only CI |

---

**Plan complete and saved to `docs/superpowers/plans/2026-08-26-ilearn-edition-0826-curriculum-data.md`. Two execution options:**

**1. Subagent-Driven (recommended)** — dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** — execute tasks in this session using executing-plans, batch execution with checkpoints

**Which approach?**
