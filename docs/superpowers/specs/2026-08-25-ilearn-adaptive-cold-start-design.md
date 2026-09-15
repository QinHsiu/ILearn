# ILearn Adaptive Cold-Start Design

**Date:** 2026-08-25  
**Status:** Approved for implementation planning  
**Source:** `doc/edition_0825_coding.txt` (scope A) + existing ILearn codebase  
**Approach:** Thin adapter layer + reuse pilot data (Approach 3)

## Goal

Enable offline-debuggable cold-start assessment: infer learning progress from grade/semester/date, expand prerequisites via a knowledge graph, generate an anchor paper (5–8 items), then a full diagnostic paper (~20 items) from the local pilot template bank only. Independent session APIs + Orchestrator hooks; default wizard path unchanged.

## Non-Goals (this iteration)

- External / LLM question generation
- Frontend wizard changes (`useRole` / `useResponsive` / Assessment page rewrite)
- Feynman / spaced-repetition planning enhancements
- Changing default `POST /sessions/{id}/assessment` behavior
- Extending `StudentProfile` schema with `semester`

## Constraints

- Pilot grades 4–6, Beijing · Renjiao, math only
- Knowledge ids match `data/pilot/knowledge.json` (e.g. `frac_add_same`), not free-text Chinese names
- Zero LLM required for local debug
- Sync agent style (`AssessmentAgent.run` / new sync methods), not async rewrites from the coding doc
- Anchor papers are variable length; must not call fixed-20 `validate_paper`

## Architecture

```text
StudentProfile (+ optional semester)
        │
        ▼
 ProgressMapper ──► chapter + current knowledge_ids
        │
        ▼
 KnowledgeGraph ──► prerequisites → anchor_kps
        │
        ▼
 AssessmentAgent.generate_adaptive_assessment
        │  templates via AssessmentBuilder / list_templates
        ├─ start  → anchor paper (5–8, fail-soft shortfall)
        └─ continue → diagnose anchor → blueprint 20 → full paper
        │
        ▼
 Orchestrator hooks + FastAPI session routes
```

## §1 Data model and progress mapping

### Files

| Path | Role |
| --- | --- |
| `data/curriculum/progress_mapping.json` | Region → textbook → grade → semester → chapter weeks + `knowledge_ids` |
| `data/knowledge_graph.json` | Nodes keyed by knowledge id: `prerequisites`, `related`, `grade` |
| `ilearn/core/progress_mapper.py` | `ProgressMapper` |
| `ilearn/core/knowledge_graph.py` | `KnowledgeGraph` |

### Progress mapping rules

- Fall semester (`上学期`): weeks from Sep 1 of the current year
- Spring semester (`下学期`): weeks from Mar 1 of the current year
- `week = (today - start).days // 7 + 1`
- Match chapter whose `weeks` contains `week`; else fall back to first chapter of that semester
- `semester`: optional on API body; if omitted, infer from month (Mar–Aug → `下学期`, else `上学期`)
- Missing JSON file → embedded minimal fallback covering grades 4–6 (at least one chapter each)

### Knowledge graph rules

- English keys: `prerequisites`, `related`, `grade`
- Edges only among existing pilot ids (reasonable prerequisites, e.g. `frac_mult` ← `frac_add_same`)
- Unknown id → empty lists (fail-soft)

## §2 Adaptive assessment engine

### API on `AssessmentAgent`

```text
generate_adaptive_assessment(
    profile,
    *,
    is_first_time: bool = True,
    anchor_results: list[dict] | None = None,
    semester: str | None = None,
    now: datetime | None = None,
) -> dict
```

Default `run()` unchanged.

### Phase 1 — Anchor (`is_anchor=True`)

1. Infer `current_chapter`, `current_kps` via `ProgressMapper`
2. Expand prerequisites → `anchor_kps = unique(current + prereqs)[:6]`
3. Select items from pilot **templates** by `knowledge_ids` (same spirit as `AssessmentBuilder.build_followup`)
4. Target size: `min(len(anchor_kps) * 2, 8)`, prefer ≥5; if bank short, deliver what exists and report `requested` / `delivered` / `shortfall`
5. Skip fixed-20 `validate_paper`
6. Prefer difficulty mix ≈ easy/medium/hard 0.5/0.3/0.2; relax if insufficient templates
7. Response fields: `is_anchor`, `paper`, `inferred_chapter`, `inferred_kps`, `anchor_kps`, size metadata

### Phase 2 — Full paper (`anchor_results` present)

1. `_diagnose_from_anchor(anchor_results)`: aggregate by knowledge id; mark weak if correct rate &lt; 0.7. Debug-friendly input shape: `{ item_id, knowledge_ids?, is_correct }`
2. Target knowledge = unique(`weak` + `current_kps`)
3. Existing `build_blueprint(profile, weak_list)` + `fill_blueprint` + `validate_paper` → 20-item paper (quota 10/8/2)
4. Response: `is_anchor=False`, `paper`, `diagnosis` (weak ids + rate summary)

## §3 API, storage, hooks, tests, local debug

### HTTP

| Method | Path | Body | Result |
| --- | --- | --- | --- |
| POST | `/sessions/{session_id}/assessment/adaptive/start` | optional `{ "semester" }` | Anchor payload |
| POST | `/sessions/{session_id}/assessment/adaptive/continue` | `{ "anchor_results": [...] }` | Full paper + diagnosis |

Requires prior `POST /sessions`. Default assessment route and React wizard unchanged.

### Session storage

- Persist under `session.metadata["adaptive"]`: `anchor_paper`, `anchor_results`, `full_paper`, inferred fields, size metadata
- Do **not** set anchor paper as `session.paper` (avoids breaking grade/diagnose)
- On successful `continue`: set `session.paper` to the full paper so existing submit/grade flow works for local end-to-end debug

### Orchestrator hooks

- `start_adaptive_assessment(session_id, semester=None)`
- `continue_adaptive_assessment(session_id, anchor_results)`
- Default pipeline / `run()` does **not** call these automatically

### Tests (offline)

- `tests/test_progress_mapper.py` — week hit, fallback, missing-file fallback
- `tests/test_knowledge_graph.py` — prerequisites, unknown id
- `tests/test_adaptive_assessment.py` — anchor size/kps, continue→20, shortfall
- `tests/test_adaptive_api.py` — start/continue HTTP contract

### Local debug

```bash
uvicorn ilearn.api.app:app --reload --host 127.0.0.1 --port 8000
# Use /docs: create session → adaptive/start → adaptive/continue
# Or: pytest tests/test_progress_mapper.py tests/test_knowledge_graph.py tests/test_adaptive_assessment.py tests/test_adaptive_api.py -q
```

## Success criteria

1. Offline pytest for mapper, graph, adaptive agent, and API all pass
2. `/docs` can create a session and obtain anchor then full paper without API keys
3. Full paper after `continue` is usable with existing submit/grade endpoints
4. Existing non-adaptive assessment tests remain green

## Implementation notes

- Prefer extending `AssessmentAgent` / `Orchestrator` / `ilearn/api/app.py` over inventing parallel `assessment_agent.py` package names from the coding doc
- Keep Chinese user-facing semester labels (`上学期` / `下学期`) as used in the product doc; graph JSON uses English keys
