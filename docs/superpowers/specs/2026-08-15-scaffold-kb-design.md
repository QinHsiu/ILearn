# Slice 4: Scaffold pedagogical KB into hint ladder

**Date:** 2026-08-15  
**Status:** Approved for planning  
**Parent program:** Adapt `doc/deepseek_edition/0815_e2` into main ILearn  
**Reference:** `doc/deepseek_edition/0815_e2/scaffold_state/`  
**Prior slices:** session metadata; model routing; diagnostic enrichment

## Context

Main ILearn already has `TutorAgent` (`TutorPhase` FSM), `hint_for_error` / fail-streak escalation, `GuardAgent` answer-leak protection, and tutor HTTP APIs returning `TutorTurn`. The `0815_e2` scaffold pack adds a parallel 4-level ladder, KB, optional LLM, and affective tone — but depends on missing `affective` and duplicates the existing phase machine.

Slice 4 adapts only **PedagogicalKnowledgeBase + offline templates** into the existing hint ladder.

## Goals

- Add `ilearn/core/pedagogical_kb.py` (adapted from reference defaults).
- Ship `data/pedagogical_strategies.json` with builtin fallback if missing.
- Extend `hint_for_error` to prefer KB text, then `_TAG_HINTS`; keep streak≥3 suffix behavior.
- Leave `TutorAgent`, Guard, APIs, and `TutorTurn` unchanged.

## Non-goals

- Parallel `ScaffoldState` / replacing `TutorPhase`.
- LLM / `SmartLLMClient` tutoring calls.
- Affective computing module.
- Changing Guard or max-hints policy.
- New tutor endpoints or response shape.

## Approach

Thin KB module + JSON data file; wire only through `hint_for_error`.

## Components

### 1. `ilearn/core/pedagogical_kb.py`

`PedagogicalKnowledgeBase`:

- Load builtin strategies (conceptual / procedural / metacognitive phrase lists keyed by coarse skill or `default`).
- Optionally merge `data/pedagogical_strategies.json` (path: default under repo `data/`, overridable for tests via constructor `data_path`).
- Missing JSON → builtin only (no raise).

**ErrorTag → bucket**

| ErrorTag | Bucket |
| --- | --- |
| `concept_gap` | `conceptual` |
| `calc_error` | `procedural` |
| `incomplete` | `procedural` |
| `method_wrong` | `procedural` |
| `misread` | `metacognitive` |
| unknown / None | `metacognitive` |

**`retrieve(error_tag: str | None, fail_streak: int = 0) -> str | None`**

- Collect phrases for the bucket (`default` list + any skill lists if present).
- If empty → `None`.
- Pick index `min(max(fail_streak, 0), len(phrases) - 1)` (deterministic, no RNG).
- Do not interpolate unanswered placeholders that would invent numbers; prefer phrases without `{numerator}`-style slots, or strip unused format fields. Builtin set for this slice should use plain Chinese strings (no format placeholders) to avoid KeyError.

### 2. `data/pedagogical_strategies.json`

Same nested shape as builtin. Example keys under buckets: `"default": ["...", "..."]`. File checked into repo so deployments get richer copy without code edits.

### 3. `ilearn/core/hints.py`

```text
hint_for_error(error_tag, fail_streak=0):
  level from existing _TAG_HINTS / default
  text = KB.retrieve(error_tag, fail_streak) or existing tag text
  if fail_streak >= 3: escalate level to high; append streak suffix if missing
  return (level, text)
```

Use a module-level default KB instance (lazy) so call sites of `hint_for_error` stay unchanged. Allow injecting KB in tests via optional parameter `kb: PedagogicalKnowledgeBase | None = None` **only if** needed — prefer monkeypatching the module singleton to avoid signature change; **prefer keeping `hint_for_error(error_tag, fail_streak=0)` signature** and testing via JSON temp path by constructing KB used internally through a replaceable `_default_kb()` helper.

### 4. Unchanged

- `ilearn/agents/tutor.py`
- Guard / orchestrator tutor paths
- Frontend Socratic panels

## Data flow

```
error_tag + fail_streak
        │
        ▼
 PedagogicalKnowledgeBase.retrieve  ← JSON ⊕ builtin
        │
        ▼
 hint_for_error → (HintLevel, text) → TutorAgent.step messages
        │
        ▼
 GuardAgent (unchanged leak check)
```

## Testing

- `tests/test_pedagogical_kb.py`: builtin retrieve; missing file OK; JSON override preferred for a tag.
- `tests/test_practice_hints.py` (or extend existing hint tests): KB-backed text; unknown tag fallback; streak≥3 suffix still applied.
- Existing tutor / guard / hint interaction tests remain green.

## Success criteria

- Richer offline hints without API/schema changes.
- Diff limited to KB module, JSON data, `hints.py`, and tests.
- Full suite green.

## Follow-on

Optional later: SmartLLM tutoring; ScaffoldLevel metadata on TutorTurn; affective tone.
