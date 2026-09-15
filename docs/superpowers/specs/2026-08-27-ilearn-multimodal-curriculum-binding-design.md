# ILearn Multimodal Curriculum Binding Design (Edition 0827)

**Date:** 2026-08-27  
**Status:** Draft — approved for implementation planning  
**Source:** `doc/edition_0826.txt` (MV-MATH P1) + product requirement: multimodal items must bind deeply to knowledge points, exam objectives, learning progress, and textbook edition  
**Depends on:** Edition 0825 (adaptive cold-start), Edition 0826 (`build_pilot`, RCAE graph, `chapter_overrides.json`, legacy 13 kp)

## Goal

Introduce **curriculum-bound multimodal assessment items** for the Beijing · Renjiao · grades 4–6 math pilot: each item carries images **and** a complete `CurriculumRef` (知识点 / 考点 / 章节进度 / 教材版本). Items are selected only when they pass version, progress, prerequisite, and objective gates—never as a loose image dump from MV-MATH.

Pilot deliverable: a small, validated **multimodal bank** (target 40–80 items across legacy 13 `knowledge_id`s), 2–4 multimodal slots in the anchor paper and optional slots in the full 20-item paper, with frontend stem-image rendering and unchanged submit/grade flow.

## Non-Goals (Edition 0827)

- Replacing text-only `example_bank.json` or RCAE graph (0826 artifacts stay)
- Full MV-MATH corpus import (~2,009 items) without binding review
- MLLM / vision-model grading of student work (images remain question-side only in 0827)
- New textbook editions (e.g. 北师大) beyond stub hooks
- Changing full diagnostic paper quota (**exactly 20** items)
- Committing `doc/` / `docs/` to git (local design only)

## Constraints

| Rule | Value |
| --- | --- |
| Pilot region / edition | `北京` / `人教版` |
| Pilot grades | 4–6 |
| Knowledge ids | Must exist in `data/pilot/knowledge.json` or legacy 13 set |
| Objective ids | Must exist in `data/pilot/syllabus.json` (`citation_id`) |
| Chapter / weeks | Must match an entry in `data/curriculum/chapter_overrides.json` for that grade + semester |
| Unbound items | **Rejected** at import (fail-closed for pilot) |
| Raw MV-MATH dumps | `data/raw/mv_math/` (gitignored) |
| Committed assets | `data/pilot/assets/mv_math/<item_id>/` (images only; size-budget per PR) |
| Anchor multimodal cap | 2–4 items per anchor paper |
| Full paper multimodal cap | ≤4 items (remaining slots text templates) |

## Problem statement

Edition 0826 expanded **text** examples via RCAE / MM-K12 / TAL-SCQ5K / templates. MV-MATH was deferred because:

1. It is **multi-image** (2–8 images per question)—requires asset storage and UI, not JSON text fields alone.
2. It is **English-first** and benchmark-oriented—no 人教 chapter tags.
3. ILearn’s existing `has_image` flag refers to **student answer uploads** (`submit-images`), not **question stem images**.

Product requirement: multimodal must not be “import and pray.” Every multimodal item must be addressable in the same coordinate system as adaptive cold-start:

```text
(region, edition, grade, semester, chapter, weeks) × knowledge_ids × objective_ids
```

## Architecture

```text
External sources (MV-MATH primary; MM-K12 images optional later)
        │
        ▼
  mv_math_bindings.json  ── crosswalk: subject/keywords → kp + chapter + objective
        │
        ▼
  mv_math importer  ── images → assets/ ; stem/answer/analysis ; CurriculumRef required
        │
        ▼
  multimodal_bank.json  ── validated items only
        │
        ▼
  CurriculumGate  ── filter by Profile + ProgressMapper + KnowledgeGraph + syllabus
        │
        ├─ AssessmentAgent.generate_adaptive_assessment (anchor: 2–4 multimodal)
        └─ fill_blueprint (full paper: ≤4 multimodal slots)
        │
        ▼
  AssessmentItem (+ image_paths, source_refs with objective_ids)
        │
        ▼
  Assessment.tsx  ── render stem images + chapter context banner
```

### Relationship to Edition 0826 components

| 0826 artifact | 0827 use |
| --- | --- |
| `knowledge.json` + `knowledge_graph.json` | Validate `knowledge_ids`; prerequisite gate |
| `progress_mapping.json` + `chapter_overrides.json` | Validate `chapter` / `weeks`; progress gate |
| `syllabus.json` | Validate `objective_ids` (考点) |
| `kp_alias.json` | Crosswalk helper for binding rules |
| `build_pilot.py` | Extended with `--multimodal` step; does not merge into `example_bank` |
| `example_bank.json` | Optional stem donor for channel B (Chinese stem + MV images) |

## §1 Data model

### 1.1 `CurriculumRef` (required on every multimodal item)

Pydantic model location: `ilearn/core/schemas.py` (new) or nested dict validated in importer.

```python
class CurriculumRef(BaseModel):
    region: str              # "北京"
    edition: str             # "人教版"
    grade: Literal[4, 5, 6]
    semester: Literal["上学期", "下学期"]
    chapter: str             # human-readable, e.g. "长方形面积"
    weeks: list[int]         # must match chapter_overrides entry
    objective_ids: list[str] # citation_id from syllabus.json, ≥1
    source_label: str = "北京·人教·小学数学"
```

Validation rules (enforced in `ilearn/data/curriculum_gate.py`):

- `(region, edition, grade, semester, chapter)` must resolve to a chapter block in `chapter_overrides.json` whose `knowledge_ids` intersect the item’s `knowledge_ids`.
- Every `objective_id` must exist in `syllabus.json` for the same `grade` (or grade-adjacent if explicitly allowed in binding table).
- `weeks` on the item must be a subset of the chapter’s `weeks` in overrides (or equal).

### 1.2 `MultimodalItem` record (`data/pilot/multimodal_bank.json`)

Top-level shape: **list** of items (not keyed by `knowledge_id`, to allow multi-kp items later).

```json
{
  "id": "mmv-rect-001",
  "stem": "观察图中长方形，求面积是多少平方厘米？",
  "answer": "40",
  "answer_type": "free-form",
  "difficulty": "medium",
  "knowledge_ids": ["rect_area"],
  "image_paths": [
    "assets/mv_math/mmv-rect-001/0.png",
    "assets/mv_math/mmv-rect-001/1.png"
  ],
  "image_relevance": "independent",
  "curriculum_ref": {
    "region": "北京",
    "edition": "人教版",
    "grade": 4,
    "semester": "上学期",
    "chapter": "长方形面积",
    "weeks": [17, 18, 19, 20],
    "objective_ids": ["bj-g5-geo-01"],
    "source_label": "北京·人教·小学数学"
  },
  "analysis": "面积 = 长 × 宽 …",
  "source": "mv_math",
  "source_problem_id": "batch1_8g_0006_…"
}
```

Field notes:

| Field | Purpose |
| --- | --- |
| `image_paths` | Relative to `data/pilot/`; served as static files or API `/pilot-assets/...` |
| `image_relevance` | `independent` \| `mutually_dependent` (from MV-MATH `image_relavance`) — diagnostic metadata only in 0827 |
| `analysis` | Tutor / report enrichment (like TAL `answer_analysis`) |
| `source_problem_id` | Provenance for ATTRIBUTION |

### 1.3 `AssessmentItem` extension

```python
class AssessmentItem(BaseModel):
    # … existing fields …
    image_paths: list[str] = Field(default_factory=list)
    is_multimodal: bool = False  # derived: len(image_paths) > 0
```

`ItemSourceRef` unchanged; multimodal items still populate `curriculum_objective_ids`, `textbook_chapter`, `source_label` via existing `bind_source_refs_to_item` path (extend to read `curriculum_ref` when no `example_bank` hit).

### 1.4 Crosswalk: `data/curriculum/mv_math_bindings.json`

Maps external taxonomy → ILearn curriculum coordinates. **Authoritative for bulk import**; hand-maintained, small.

```json
{
  "rules": [
    {
      "match": { "mv_subject": "Metric Geometry", "stem_regex": "rectangle|area" },
      "bind": {
        "knowledge_ids": ["rect_area"],
        "grade": 4,
        "semester": "上学期",
        "chapter": "长方形面积",
        "objective_ids": ["bj-g5-geo-01"]
      }
    },
    {
      "match": { "mv_subject": "Arithmetic", "stem_regex": "decimal|multiply" },
      "bind": {
        "knowledge_ids": ["dec_mult"],
        "grade": 5,
        "semester": "上学期",
        "chapter": "小数乘法",
        "objective_ids": ["bj-g5-num-01"]
      }
    }
  ],
  "grade_map": {
    "Elementary": [4, 5, 6],
    "Junior": []
  }
}
```

Rules are evaluated **first match wins**; unmatched MV-MATH rows are **skipped** (logged), not imported.

Initial rule set (pilot): cover legacy 13 `knowledge_id`s where MV-MATH `subject` + stem keywords align; `Junior` / `Senior` grades map to empty (skip).

## §2 Import pipeline

### 2.1 Download

```bash
python scripts/download_raw_data.py --dataset mv_math --download
```

- Source: Hugging Face `PeijieWang/MV-MATH`
- Output: `data/raw/mv_math/items.jsonl` (metadata only) + `data/raw/mv_math/images/<problem_id>/`
- Skip non-`Elementary` grade unless binding rule explicitly sets `grade` 4–6

### 2.2 Importer: `ilearn/data/importers/mv_math.py`

```text
load_mv_math_record(path) -> dict
resolve_binding(record, rules) -> CurriculumRef | None
extract_images(record, out_dir) -> list[str]   # relative paths
to_multimodal_item(record, binding, image_paths) -> dict | None
```

**Channel B (recommended default):** If MV-MATH `question` is English or choice-only (`answer_type: choice`), replace `stem` with a Chinese stem sampled from `example_bank.json` for the same `knowledge_id` (deterministic hash by `source_problem_id`). Keep MV-MATH images.

### 2.3 Build integration

`python -m ilearn.data.build_pilot` gains step:

1. Existing 0826 steps (RCAE, MM-K12, TAL, templates → `example_bank`)
2. **New:** `build_multimodal_bank(raw_dir, bindings_path, overrides_path, syllabus_path, out_path, assets_dir)`
3. Validate all items via `CurriculumGate.validate_item()`
4. Write `data/pilot/multimodal_bank.json`; copy images to `data/pilot/assets/mv_math/`

Do **not** append multimodal rows into `example_bank.json` (separate bank avoids text-only code paths breaking).

### 2.4 Attribution

Extend `data/pilot/ATTRIBUTION.md` with MV-MATH (CVPR 2025, PeijieWang/MV-MATH, cite paper).

## §3 Curriculum gates (runtime)

New module: `ilearn/core/curriculum_gate.py`

```python
class CurriculumGate:
    def __init__(self, overrides_path, syllabus_path, graph: KnowledgeGraph): ...

    def validate_item(self, item: dict) -> list[str]:
        """Return list of validation errors; empty = OK."""

    def eligible_for_profile(
        self,
        item: dict,
        profile: StudentProfile,
        *,
        semester: str,
        now: datetime,
        current_kps: list[str] | None = None,
    ) -> bool:
        """Version + progress + prerequisite gate."""

    def filter_bank(
        self,
        bank: list[dict],
        profile: StudentProfile,
        *,
        semester: str,
        now: datetime,
        knowledge_ids: list[str] | None = None,
    ) -> list[dict]:
        """Return items safe to show now."""
```

### Gate definitions

| Gate | Rule |
| --- | --- |
| **Version** | `profile.region == curriculum_ref.region` (default `北京`); edition fixed `人教版` until profile grows an `edition` field |
| **Grade** | `profile.grade == curriculum_ref.grade` |
| **Progress** | `ProgressMapper.infer_current_progress` → `current_kps`; item `knowledge_ids` ∩ `current_kps` ≠ ∅ (anchor); full paper may also include diagnosed weak kps |
| **Prerequisite** | For each item kp, all `KnowledgeGraph.get_prerequisites(kp)` either in `current_kps` or mastery above threshold (0827: simplify to “prereqs ⊆ current_kps ∪ anchor_kps”) |
| **Objective** | `len(curriculum_ref.objective_ids) >= 1` and all ids ∈ syllabus |
| **Semester** | `curriculum_ref.semester` matches inferred or API-provided semester |

Fail-closed: if no multimodal item passes gates, anchor/full paper falls back to **text templates only** (existing 0825 behavior).

## §4 Assessment integration

### 4.1 Anchor paper (`generate_adaptive_assessment`, `is_first_time=True`)

Existing flow (0825):

1. `ProgressMapper` → `current_chapter`, `current_kps`
2. `KnowledgeGraph` → expand prerequisites → `anchor_kps`
3. Select text templates by `anchor_kps`

**0827 addition** (after step 2):

4. `CurriculumGate.filter_bank(multimodal_bank, profile, semester, knowledge_ids=anchor_kps)`
5. Pick **2–4** multimodal items (distinct `knowledge_ids`, difficulty mix easy/medium/hard)
6. Fill remaining anchor slots with text templates (total anchor size still 5–8)
7. Set `AssessmentItem.image_paths`, `is_multimodal=True`; bind `source_refs` from `curriculum_ref`

Response metadata additions:

```json
{
  "multimodal_count": 3,
  "inferred_chapter": "长方形面积",
  "curriculum_ref_summary": { "region": "北京", "edition": "人教版", "grade": 4 }
}
```

### 4.2 Full paper (`anchor_results` present)

1. Existing weak-kp diagnosis unchanged
2. When filling blueprint slots, up to **4** slots may draw from gated multimodal bank (matching slot `knowledge_id` + difficulty)
3. Remaining slots: `fill_blueprint` templates
4. `validate_paper` still enforces **20** items and type/difficulty quotas

### 4.3 Layer2 / stub

Unchanged: multimodal items are **never** LLM-generated in 0827; Layer2 only applies to text template shortfall.

## §5 API and frontend

### 5.1 Static assets

Option A (preferred for local debug):

```text
GET /pilot-assets/{path}
```

Maps to `data/pilot/assets/` with path traversal guard. `image_paths` in API responses are URL paths `/pilot-assets/mv_math/...`.

### 5.2 Frontend (`Assessment.tsx`)

- Render `item.image_paths` as `<img>` list above stem (lazy load, max height)
- Show **chapter banner**: `{inferred_chapter}` + `source_label` from session metadata
- No change to answer input (text/choice); student image upload flow unchanged

### 5.3 Session metadata

```json
{
  "adaptive": {
    "multimodal_item_ids": ["mmv-rect-001", "..."],
    "inferred_chapter": "长方形面积",
    "curriculum_edition": "人教版"
  }
}
```

## §6 Phased delivery

| Phase | Scope | Exit criterion |
| --- | --- | --- |
| **0827a** | `CurriculumRef`, `CurriculumGate`, `multimodal_bank.json` schema, validation tests | Invalid fixtures rejected |
| **0827b** | `mv_math_bindings.json` + importer + download script + assets on disk | ≥20 bound items in bank |
| **0827c** | `build_pilot` step + ATTRIBUTION | One-command rebuild |
| **0827d** | `AssessmentAgent` anchor/full multimodal slots + `/pilot-assets` | Adaptive start returns items with `image_paths` |
| **0827e** | `Assessment.tsx` + chapter banner | Manual E2E in browser |
| **0827f** (stretch) | 好未来 KG enrichment of `objective_ids` per kp | Finer 考点 alignment |

## §7 Tests (offline)

| File | Covers |
| --- | --- |
| `tests/test_curriculum_gate.py` | validate_item, version/grade/progress/prereq gates |
| `tests/test_mv_math_importer.py` | binding resolve, image extract, channel B stem |
| `tests/test_multimodal_bank.py` | bank schema, all items pass gate |
| `tests/test_adaptive_multimodal.py` | anchor includes 2–4 gated multimodal; full paper ≤4 |
| `tests/test_pilot_assets_api.py` | `/pilot-assets` serves image, blocks `..` |
| `frontend/src/pages/Assessment.multimodal.test.tsx` | renders images when `image_paths` set |

Regression: full `pytest -q` + existing adaptive tests green; **20-item** quota test unchanged.

## §8 Success criteria

1. Every committed multimodal item has complete `CurriculumRef` passing `CurriculumGate.validate_item`
2. No multimodal item shown when `profile.region` ≠ `北京` (or progress gate fails)—falls back to text
3. Anchor paper contains 2–4 multimodal items when bank has eligible items for current chapter
4. Full paper after `continue` remains **20** items with ≤4 multimodal
5. `source_refs` on multimodal items include `curriculum_objective_ids` and `textbook_chapter`
6. Offline pytest + frontend test pass without API keys

## §9 Risks and mitigations

| Risk | Mitigation |
| --- | --- |
| MV-MATH English stems | Channel B: Chinese stem from `example_bank` |
| Large image repo size | Cap pilot import at 80 items; git LFS or size check in CI |
| RCAE junk kp ids | Multimodal only binds to **legacy 13** + explicitly ruled subjects in 0827 |
| `syllabus.json` sparse (7 citations) | Reuse closest grade objective; extend syllabus in 0827f |
| Choice answers (`A`/`B`) | Map to `answer_type: choice`; require `choices` field or convert to free-form for pilot |
| Week inference edge cases (holidays) | Same fallback as 0825 ProgressMapper (first chapter of semester) |

## §10 Open questions (defaults chosen)

| Question | Default for 0827 |
| --- | --- |
| Store multimodal in `example_bank` vs separate file? | **Separate** `multimodal_bank.json` |
| Grade from MV-MATH `Elementary` | Binding rule sets explicit `grade` 4/5/6, not auto-all |
| Multimodal in non-adaptive wizard? | **No**; adaptive path only in 0827 |
| Add `profile.edition` field? | **No**; hardcode `人教版` in gate until multi-edition pilot |

## Implementation handoff

Next step: `docs/superpowers/plans/2026-08-27-ilearn-multimodal-curriculum-binding.md` via writing-plans skill, tasks ordered **0827a → 0827f**.

Local debug after 0827d:

```bash
python scripts/download_raw_data.py --dataset mv_math --download
python -m ilearn.data.build_pilot
uvicorn ilearn.api.app:app --reload --port 8000
# /docs: session → adaptive/start → verify image_paths + chapter metadata
```
