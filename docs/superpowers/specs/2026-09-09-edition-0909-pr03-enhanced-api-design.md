# Edition 0909 PR03 Enhanced API Design

**Date:** 2026-09-09  
**Status:** Approved (A+C plan)  
**Depends on:** PR #01 storage + PR #02 agents (branch-stacked)

## Goal

Opt-in API branches for five-dim overlay and enhanced PDF; default responses unchanged.

## Behavior

- Query `enhanced=true` **and** `ENABLE_ENHANCED_API` → attach `enhanced_profile` + `suggestions`.
- Otherwise ignore query (legacy payload identical).
- `GET /sessions/{id}/enhanced/report.pdf` → 404 unless API flag on.

## Surfaces

- `/sessions/{id}/summary/{teacher|parent|student}?enhanced=`
- `/dashboard/.../student/...?enhanced=` and `/dashboard/teacher/.../classes?enhanced=`
- `/sessions/{id}/enhanced/report.pdf`
