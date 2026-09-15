# Edition 0830_8 Gap Design — Subject Adapter + Evidence Migration + Multi-round Validators

**Date:** 2026-08-30  
**Status:** Ready for user review (self-reviewed: no TBD/contradictions; scope = gaps only)  
**Source:** `doc/edition_0830_8.txt` (gaps only)  
**Baseline:** Edition 0830_7 (PhaseGuard / FeatureRegistry / UserFriendlyError already shipped)

## Goal

Close the remaining **unimplemented** items from edition_0830_8 without re-doing P0/P1 work already landed in 0830_3–7:

1. Thin `SubjectAdapter` (math only, grades 4–6 fail closed)
2. `EvidenceMigrator` for legacy session evidence fields
3. Multi-round item revision (`revise_paper`, max 3) with safe fallback

Out of scope: PDF preview / multi-format export, frontend `useDevice`, re-implementing session locks / LLM fallback / PhaseGuard / FeatureRegistry / UserFriendlyError, Chinese stub adapter, soft-open grades 1–12.

## Architecture (approved §1)

Thin adapter layer over existing `CurriculumProvider`; migrate on load; extend validators without replacing the single-pass helper.

| Component | Path | Responsibility |
| --- | --- | --- |
| Subject adapter | `ilearn/core/subject_adapter.py` | ABC + `MathSubjectAdapter` + `get_adapter(subject)` wrapping current curriculum provider |
| Evidence migration | `ilearn/core/migration.py` | Normalize legacy `evidence_log` dicts → current `KnowledgeEvidence` shape |
| Multi-round revise | `ilearn/core/item_validators.py` | Add `revise_paper(..., max_attempts=3)`; keep `revise_paper_once` as thin wrapper / compat |
| Wiring | `ilearn/storage/sessions.py`, `ilearn/agents/orchestrator.py` | Migrate on load/list; orchestrator uses multi-round revise |

### SubjectAdapter (A1)

```text
SubjectAdapter (ABC)
  get_grade_range() -> tuple[int, int]
  supports(grade: int) -> bool
  curriculum() -> CurriculumProvider   # delegate

MathSubjectAdapter(SubjectAdapter)
  get_grade_range() -> (4, 6)
  supports(g) -> g in {4,5,6}
  wraps existing PilotBeijingRenjiaoProvider (or injected CurriculumProvider)

get_adapter(subject: str) -> SubjectAdapter
  "math" -> MathSubjectAdapter
  else -> raise (map to friendly error only if called from API; unit path may raise ValueError)
```

Constraints:

- Do **not** replace `CurriculumProvider` call sites in Assessment/Diagnosis/Planning this edition.
- Adapter is the extension seam + unit-testable facade; main pipeline keeps injecting `CurriculumProvider` as today.
- Grade fail-closed remains `require_pilot_grade` / `E-001`.

### EvidenceMigrator

Apply to raw `evidence_log` entries **before or around** `SessionState` validation so old JSON still loads.

Field mapping (legacy → current):

| Legacy / missing | Current default / map |
| --- | --- |
| missing `confidence` | `0.5` |
| missing `evidence_id` | generate hex id |
| missing `created_at` / present `timestamp` | use `timestamp` if parseable else `utc_now()` |
| `source_type` / `hint_count` | map to `lane` / `hint_level` when those fields absent (`hint_count > 0` → treat as hinted practice; default `lane="practice"`) |
| already-valid `KnowledgeEvidence` dict | pass through unchanged |

Per-entry failure: skip bad entry + log; do not fail the whole session load.

Wire into `SessionStore.load` and list paths that parse session JSON (same migrate helper).

### Multi-round validators

- Add `revise_paper(paper, issues, *, profile, curriculum, max_attempts=3, rng=None) -> RevisedPaperResult`  
  where result carries `paper`, `attempts`, `fallback_used: bool`.
- Loop: validate → if clear return; else replace failing items via alternate templates (reuse `_alternate_templates` / instantiate logic from `revise_paper_once`).
- If attempts exhausted and issues remain: replace remaining failing items with a **deterministic safe fallback item** (pilot-grade simple fraction/choice stem), set `fallback_used=True`, preserve paper length when possible (full diagnostic still 20 when input was 20).
- Keep `revise_paper_once` as `revise_paper(..., max_attempts=1)` wrapper or one-shot call so existing tests keep working.
- Orchestrator `_validate_and_revise_paper` switches to `revise_paper`; decision summary uses `revised N` / `fallback` instead of only `revised once`.

## Data flow / errors / tests (approved §2)

### Data flow

1. Session create → unchanged (profile subject math default).
2. Assessment generate → quality gate → `_validate_and_revise_paper` → multi-round revise → bind source_refs if items changed → save.
3. Session load → read JSON → migrate evidence_log → `SessionState.model_validate` → cache.

### Error handling

| Case | Behavior |
| --- | --- |
| Grade outside 4–6 via curriculum | Existing `CurriculumError` / `E-001` |
| Unknown subject in `get_adapter` | `ValueError` (optional map if exposed on API later) |
| Corrupt evidence entry | Drop entry, continue |
| Revision exhausted | Fallback items, no raise; keep paper usable |

### Tests (TDD)

| Test file | Cases |
| --- | --- |
| `tests/test_subject_adapter.py` | grade range, supports true/false, curriculum delegate list_knowledge |
| `tests/test_evidence_migration.py` | missing fields filled; legacy timestamp/source_type; SessionStore.load migrates |
| `tests/test_item_validators.py` (extend) | multi-round replacement; fallback after max attempts; `revise_paper_once` still passes |

Do not regress existing 522+ offline tests; new tests are additive.

## Non-goals (explicit)

- PDF preview / confirm / docx
- Frontend mobile `useDevice` (existing `useResponsive` stays)
- Async rewrite of SessionStore / LLM client
- Replacing PhaseGuard with the idealized enum sketch from the edition doc
- Opening grades 1–12 or non-math subjects

## Success criteria

- [ ] `MathSubjectAdapter` + `get_adapter("math")` unit tests green
- [ ] Legacy evidence fixtures load without validation errors after migrate
- [ ] Orchestrator paper path can revise up to 3 times and records fallback in summary when used
- [ ] Full offline pytest suite still green; VERSION.md notes Edition 0830_8 gap close
