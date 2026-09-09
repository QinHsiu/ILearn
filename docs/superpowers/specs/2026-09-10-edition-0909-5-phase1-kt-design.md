# Edition 0909_5 Phase 1 — Knowledge Tracing (BKT-first) Design

**Date:** 2026-09-10  
**Status:** Approved for implementation planning  
**Scope:** Phase 1 only (dynamic mastery). Phases 2–4 (path planning, roles, memory/reflection) are out of scope.

## Goal

Improve knowledge-state estimates used by the five-dim profile, with minimal invasion of the legacy pipeline. Frontend continues to read mastery via `?enhanced=` / existing profile blobs; only the update math changes when flags are on.

## Decisions (locked)

| Decision | Choice |
|----------|--------|
| Phase | A — KT / dynamic mastery first |
| Backend | A — Protocol + **BKT default**; pyKT optional later (checkpoint required) |
| Hard deps | No `torch` / `pykt-toolkit` in main requirements |
| Flags | New `ENABLE_ENHANCED_KT` default `false` |
| Profile API | Keep sync `get/set_enhanced_profile(session)`; no `session_id` async loaders |
| Orchestrator | Keep sync `diagnose` / `plan`; no dual async route |

## Architecture

### Flags

KT path runs only when **all** are true:

- `ENABLE_ENHANCED_PROFILE`
- `ENABLE_ENHANCED_AGENTS`
- `ENABLE_ENHANCED_KT`

`ENABLE_ENHANCED_BACKGROUND` unchanged: background task still calls `ProfileUpdaterAgent.update_session()`, which will apply KT when the three flags above are on.

When `ENABLE_ENHANCED_KT` is false, cognitive updates remain the existing ±0.12 heuristic (PR02 behavior).

### Components

| Unit | Responsibility | Dependencies |
|------|----------------|--------------|
| `KnowledgeTracingService` (protocol) | `add_interaction`, `predict_mastery`, `get_weak_concepts` | none |
| `BKTKnowledgeTracing` | Per-concept Bayesian KT | stdlib |
| `PyKTKnowledgeTracing` (optional) | Construct only if extra installed **and** checkpoint present | torch/pykt |
| `create_kt_service()` | Select backend; on failure → BKT | flags |
| `ProfileUpdaterAgent` | Flag-gated: load/save KT blob, fuse predictions | above |

### Non-goals (this PR)

- Training or shipping a DKT checkpoint
- `SyllabusKnowledgeGraph` / name→int concept maps (use string `knowledge_id`)
- New API routes or UI
- Path planning, multi-role director, long-term memory / reflection flags
- Changing public `StudentFiveDimProfile` field shapes

### Layout

```
ilearn/core/kt/
  __init__.py
  protocol.py          # Protocol / shared types
  bkt.py               # Default BKT
  factory.py           # create_kt_service()
  # pykt.py optional stub: import failure → ignored
```

## Data flow

### Trigger

Unchanged entry: `ProfileUpdaterAgent.update_session(session)` from:

- Orchestrator sync hooks (`_maybe_update_enhanced_profile`), or
- `update_profile_background` when `ENABLE_ENHANCED_BACKGROUND` is on

### Interaction signals

1. Prefer `knowledge_updates: {knowledge_id: bool}` from existing stub/LLM signal extraction (diagnosis score_rate ≥ 0.6 → correct).
2. If empty, optionally backfill from `session.grades` + item knowledge mapping when available; otherwise only update concepts already in mastery / updates.
3. Concept IDs are string `knowledge_id` values already used by curriculum/diagnosis. No global integer index for BKT.

### Persistence (`session.metadata["enhanced"]`)

```yaml
enhanced:
  schema_version: 1
  profile: { ... StudentFiveDimProfile ... }
  kt:
    backend: "bkt"   # or "pykt" if ever enabled
    interactions:    # cap 200
      - {concept: "kp_a", correct: true, ts: "<iso>"}
    states:
      kp_a: {p_known: 0.42}
  recommendations: ...  # must survive profile writes
```

**Required fix:** `set_enhanced_profile` must merge `profile` into the enhanced blob and **preserve** sibling keys (`kt`, `recommendations`, …). Today it replaces the entire `enhanced` dict.

### BKT parameters (global defaults)

| Param | Default | Meaning |
|-------|---------|---------|
| `p_l0` | 0.5 | Prior known (aligns with cold-start mastery 0.5) |
| `p_t` | 0.1 | Learn transition |
| `p_s` | 0.1 | Slip |
| `p_g` | 0.2 | Guess |

After each interaction, update that concept’s `p_known`. `predict_mastery` returns per-concept `p_known`. With fewer than one interaction for a concept, return existing mastery or 0.5 (cold start; do not invent noise).

### Fusion into profile (`ENABLE_ENHANCED_KT` on)

For each concept with a KT prediction:

```text
new = 0.4 * kt_score + 0.6 * old_mastery
```

- Missing `old` → 0.5.
- Only update keys that appear in this round’s interactions **or** already exist in `knowledge_mastery`.
- Rebuild `weak_concepts` / `strong_concepts` with thresholds &lt; 0.6 / ≥ 0.8 (same as current CognitiveSubAgent).
- When KT is on, **do not** also apply ±0.12 to the same `knowledge_updates` (no double counting).
- Emotional / behavioral / metacognitive sub-agents unchanged.

### Failure policy

Any KT exception → log, fall back to ±0.12 for that update, never fail diagnose/plan.

## Testing

1. **BKT unit:** correct raises `p_known`; incorrect lowers; stays in (0, 1).
2. **Flag off:** updater matches ±0.12; no requirement to write `kt` (or ignore if present).
3. **Flag on:** after update, `kt.interactions` / `states` present; mastery matches 0.4/0.6 fusion on fixed inputs.
4. **Key preserve:** write `recommendations`, then `set_enhanced_profile`; recommendations remain.
5. **Degrade:** mock KT raises → update completes via ±0.12.
6. **Regression:** `test_edition_0909_1_pr02`, `test_edition_0909_4_pr04`, `test_edition_0909_p2_background` green.

## Acceptance

- All enhanced flags default off → zero behavior change.
- PROFILE + AGENTS + KT on → interpretable mastery updates; disabling KT restores ±0.12.
- CI / local run without torch or pykt.

## PR file checklist (expected)

- `ilearn/core/kt/*` (protocol, BKT, factory)
- `ilearn/core/enhanced_session.py` (preserve sibling keys)
- `ilearn/agents/enhanced/profile_updater.py` (KT branch)
- `data/features.yaml`, `ilearn/core/enhanced_flags.py`, `.env.example`
- `tests/test_edition_0909_5_kt.py`
- Optional: `pyproject.toml` extras comment/stub for future `[kt]` — **no** main-dep torch

## Out of scope follow-ups

- Phase 2 path planner, Phase 3 roles, Phase 4 memory/reflection (`edition_0909_5.txt`)
- Real pyKT backend behind optional extra + checkpoint gate
