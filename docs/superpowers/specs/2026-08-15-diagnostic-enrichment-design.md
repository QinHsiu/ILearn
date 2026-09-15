# Slice 3: Diagnostic rules / SOLO enrich Diagnoser

**Date:** 2026-08-15  
**Status:** Approved for planning  
**Parent program:** Adapt `doc/deepseek_edition/0815_e2` into main ILearn  
**Reference:** `doc/deepseek_edition/0815_e2/diagnostic_orchestrator/`  
**Prior slices:** session metadata; model routing infra

## Context

Main ILearn already runs sync `DiagnosisAgent` → `Diagnoser.diagnose` → `DiagnosisReport` (KC mastery, error_tag_counts, Top-5 interventions, `flags` from gap detection). The `0815_e2` diagnostic pack is an incomplete sketch (broken DINA, hardcoded Q-matrix, async per-question agent). Slice 3 adapts only the **usable rule/SOLO essence** into `Diagnoser` without replacing the pipeline.

## Goals

- Add a small runnable `ilearn/core/diagnostic_rules.py` adapted from the reference (ErrorType↔ErrorTag mapping, session-level SOLO, enrich helper).
- Hook into `Diagnoser.diagnose` to append explainable `flags` and lightly enrich intervention `why` text.
- Keep `DiagnosisReport` schema, mastery algorithm, agent/API contracts unchanged.
- Do **not** port DINA, LLM fusion, hardcoded fraction Q-matrix, or `diagnose_question` async path.

## Non-goals

- Changing `knowledge_mastery` / ability_scores computation.
- New HTTP endpoints or DiagnosisAgent signature changes.
- SmartLLM / TaskType.DIAGNOSIS wiring (later optional).
- Full RuleSpaceModel regex engine or prerequisite Q-matrix from sample data.

## Approach

Thin diagnostic_rules module + post-process hook at end of `Diagnoser.diagnose`.

## Components

### 1. `ilearn/core/diagnostic_rules.py`

**ErrorType** (enum, reference names): `conceptual`, `procedural`, `careless`, `transfer`, `reading`.

**Mapping** (ErrorTag → ErrorType):

| ErrorTag | ErrorType |
| --- | --- |
| `concept_gap` | conceptual |
| `calc_error` | procedural |
| `misread` | reading |
| `method_wrong` | transfer |
| `incomplete` | procedural |

Optional reverse labels for Chinese short phrases in `why` suffixes.

**SOLOTaxonomy** (session-level, adapted inputs):

- Input: list of `GradeResult` (+ optional student answer strings keyed by `item_id` if available from session answers; if absent, classify from correctness + error_tags only).
- Heuristics (aligned with reference spirit):
  - Mostly incorrect + little content signal → `prestructural`
  - Incorrect with tags/content → `unistructural`
  - Mostly correct, shallow → `multistructural`
  - Correct with explanation cues in answers (`因为`/`所以`/`步骤`) or strong multi-correct → `relational`
- Output: level key string used in flag: `solo:prestructural` | `solo:unistructural` | `solo:multistructural` | `solo:relational` (extended_abstract deferred / unused this slice).

**`enrich_diagnosis(*, knowledge_mastery, grades, answers_by_item: dict[str, str] | None = None) -> Enrichment`**

- `Enrichment.flags: list[str]` — one `solo:*` plus up to 5 unique `rule:<error_tag>` from grades’ tags (stable order).
- `Enrichment.why_suffix_by_knowledge_id: dict[str, str]` — for each non-mastered KC that appears in interventions candidates, a short Chinese suffix e.g. `SOLO多点结构；规则偏向概念缺口` derived from session SOLO + dominant tag on that KC.

Pure functions; no I/O; no numpy.

### 2. Hook in `ilearn/core/diagnosis.py` (`Diagnoser.diagnose`)

After building `interventions` and existing `flags = gap_flag(...)`:

1. Call `enrich_diagnosis(...)` with mastery + grades (pass answers if Diagnoser already has access via optional param — **prefer not** to change `diagnose` signature; use grades-only SOLO if answers not on Diagnoser today).
2. Merge flags: `list(dict.fromkeys([*flags, *enrichment.flags]))`.
3. For each `Intervention`, if `why_suffix_by_knowledge_id.get(knowledge_id)`, append `；{suffix}` to `why`.

Do not change `_build_interventions` scoring/selection order.

**Signature note:** Keep `diagnose(profile, paper, grades, portrait=..., evidence=...)` unchanged. SOLO without free-text answers is acceptable for this slice (grades + error_tags only); if `answers` later available on session, a follow-on can pass them without schema break.

### 3. Unchanged

- `ilearn/agents/diagnosis.py`
- API `/sessions/{id}/diagnose`
- `DiagnosisReport` Pydantic fields
- Portrait / SM-2 / evidence pipelines

## Data flow

```
grades + knowledge_mastery (existing Diagnoser)
        │
        ▼
 enrich_diagnosis  →  flags + why suffixes
        │
        ▼
 DiagnosisReport (same shape; richer flags/why)
```

## Error handling

- Empty grades → no solo/rule flags (or omit enrichment); existing diagnosis behavior stands.
- Unknown error tags ignored in mapping.
- Enrichment must never raise into API path; wrap is unnecessary if pure and defensive.

## Testing

- `tests/test_diagnostic_rules.py`: mapping table; SOLO levels for synthetic grades; enrich produces expected flags/suffixes.
- Extend or add one Diagnoser-level test asserting `solo:` appears in `DiagnosisReport.flags` when grades present.
- Existing `tests/test_agents_diagnosis.py` and related diagnosis tests remain green.

## Success criteria

- New module + Diagnoser hook + tests land.
- No schema/API/agent signature changes.
- Diff does not include DINA/orchestrator/LLM ports.
- Full suite green.

## Follow-on

Scaffold slice may consume `rule:*` / error history; optional later LLM fusion via SmartLLMClient.
