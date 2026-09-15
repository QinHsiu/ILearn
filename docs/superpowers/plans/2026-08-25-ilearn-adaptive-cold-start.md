# Adaptive Cold-Start Implementation Plan

> Do **not** commit `doc/` or `docs/` files. Do **not** git-commit unless the user asks.

**Goal:** Offline-debuggable two-phase adaptive assessment (anchor → full 20-item paper).

**Constraint:** Full diagnostic paper stays **exactly 20** items (existing blueprint/validate quotas unchanged).

**Status:** Implemented 2026-08-25. Adaptive + assessment + API regression: 32 passed.

## Delivered files

- `data/curriculum/progress_mapping.json`
- `data/knowledge_graph.json`
- `ilearn/core/progress_mapper.py`
- `ilearn/core/knowledge_graph.py`
- `ilearn/core/assessment.py` (`build_by_knowledge_ids`)
- `ilearn/agents/assessment.py` (`generate_adaptive_assessment`)
- `ilearn/agents/orchestrator.py` + `ilearn/core/orchestrator.py` hooks
- `ilearn/api/app.py` routes
- `tests/test_progress_mapper.py`, `test_knowledge_graph.py`, `test_adaptive_assessment.py`, `test_adaptive_api.py`

## Local debug

```bash
uvicorn ilearn.api.app:app --reload --host 127.0.0.1 --port 8000
# /docs: POST /sessions → /assessment/adaptive/start → /assessment/adaptive/continue
```
