# Task 3 Report: Tutor, hint, and replan HTTP routes

## Status

Implemented and verified.

## Changes

- Added persisted `SessionState.tutor_by_item: dict[str, TutorTurn]`.
- Updated `MultiAgentOrchestrator.tutor_start` to persist each initial tutor turn.
- Added `MultiAgentOrchestrator.tutor_step` with item validation, missing-start validation, FSM progression, decision logging, and persistence.
- Added `Orchestrator.tutor_start`, `Orchestrator.tutor_hint`, and `Orchestrator.request_replan` facade methods.
- Added `POST /sessions/{session_id}/tutor`.
- Added `POST /sessions/{session_id}/tutor/hint`.
- Added `POST /sessions/{session_id}/replan`.
- Added the requested API integration test.
- Did not add GuardAgent.

## TDD evidence

The new endpoint test was run before implementation and failed as expected because
`POST /sessions/{session_id}/tutor` returned HTTP 405.

After implementation, the focused endpoint, phase 2b, and tutor-agent tests passed.

## Verification

Commands:

- `python -m pytest tests/test_api.py::test_tutor_and_replan_endpoints tests/test_e2e_phase2b.py tests/test_tutor_agent.py -q`
- `python -m pytest -q`
- `git diff --check`
- IDE linter diagnostics for all modified Python files

Results:

- Focused tests: **13 passed**
- Full suite: **329 passed**, with one pre-existing Starlette/httpx deprecation warning
- `git diff --check`: passed
- Linter diagnostics: none

## Files changed

- `ilearn/agents/orchestrator.py`
- `ilearn/api/app.py`
- `ilearn/core/orchestrator.py`
- `ilearn/core/schemas.py`
- `tests/test_api.py`
- `.superpowers/sdd/2026-08-14-edition0814-p0/task-3-report.md`

## Fix report

### What changed

- Removed `TutorAgent`'s mutable per-session `_error_tag` state.
- Made `TutorAgent.step` consume an explicit `error_tag`, while retaining
  compatibility for existing callers that omit it.
- Updated `MultiAgentOrchestrator.tutor_step` to pass the persisted
  `TutorTurn.error_tag`, preserving item isolation across interleaved tutoring
  and process restarts.
- Added tests covering explicit cross-item error-tag isolation and restoration
  from a persisted turn after a new agent instance.

### Covering tests

- `tests/test_tutor_agent.py`
- `tests/test_e2e_phase2b.py`
- `tests/test_api.py`

### Command and output

Command:

`python -m pytest tests/test_api.py tests/test_e2e_phase2b.py tests/test_tutor_agent.py -q`

Output:

`29 passed, 1 warning in 3.05s`

The warning is the existing Starlette/httpx deprecation warning.
