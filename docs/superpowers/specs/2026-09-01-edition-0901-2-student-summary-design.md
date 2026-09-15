# Edition 0901_2 Design — StudentSummary + Plan-Step Panel (P2-A)

**Date:** 2026-09-01  
**Status:** Ready for user review (self-reviewed)  
**Source:** `doc/edition_0901_2.txt` (scope **A** only)  
**Baseline:** Edition 0901_1 (structured teacher/parent summaries, demo CTA role picker, student `session_id` resume, ComparisonCards)  
**Approach:** 方案 1 — extend `audience_summary` + GET API + panel on StudentApp plan step (no dedicated student dashboard page)

## Goal

Close the remaining **student-facing** gap from 0901_2 score-point 1: a structured `StudentSummary` (task progress + light gamification) that demo students see after deep-link resume into the plan step — without building a separate Student Dashboard or react-router rewrite.

## Scope

**In:**

1. Pydantic `StudentSummary` + `build_student_summary(session)` in `ilearn/core/audience_summary.py`
2. Seed preference **C**: `metadata.student_summary` when present; else deterministic formula fallback
3. Demo seed writes fixed `metadata.student_summary` for `math_5_1`
4. `GET /sessions/{id}/summary/student`
5. Frontend client + `StudentSummaryPanel` rendered on StudentApp **step 3（学习计划）** above plan markdown when `sessionId` is set

**Out:**

- Dedicated Student Dashboard page / new route
- Parent 留言 / 预约 stubs
- Class-report PDF
- react-router migration
- Rework of teacher/parent summaries beyond reuse of existing patterns

## Architecture (approved §1)

| Layer | Path | Responsibility |
| --- | --- | --- |
| Model + builder | `ilearn/core/audience_summary.py` | `StudentSummary`, `build_student_summary` |
| Seed | `ilearn/demo/seed.py` (+ optional unit JSON key) | Write `metadata.student_summary` |
| API | `ilearn/api/app.py` | `GET /sessions/{session_id}/summary/student` |
| Client | `frontend/src/api/client.ts` | Types + `getStudentSummary` |
| UI | `frontend/src/components/StudentSummaryPanel.tsx` + `App.tsx` step 3 | Fetch + display |

## Fields / formulas (approved §2)

### StudentSummary

| Field | Type | Seeded demo values | Fallback when metadata absent / partial |
| --- | --- | --- | --- |
| `current_task` | str | `"巩固：小数乘小数"` | `plan.goal` or first `PlanDay` title/focus; else `"完成今日练习"` |
| `completed_tasks` | int | `2` | `min(len(answers), total_tasks)` |
| `total_tasks` | int | `5` | `max(len(plan.days), 1)` if plan days else `max(len(paper.items), 1)` |
| `stars_earned` | int | `5` | `int(demo_weaknesses_resolved or 0) * 2 + (1 if all paper items answered else 0)` |
| `next_challenge` | str | `"挑战：运算律推广到小数"` | First weak knowledge name/id from diagnosis; else `"挑战下一关练习"` |
| `narrative` | str | Short encouragement (Chinese) | Template: `"已完成 {completed}/{total} 个任务，继续加油！"` |

**Merge rule:** If `metadata.student_summary` is a dict, use provided keys; fill any missing keys via fallback (partial overlay), then validate into `StudentSummary`.

### Data flow

Landing role=student → `POST /demo/units/math_5_1/session` → `?student=1&session_id=` → resume → step 3 → `GET .../summary/student` → panel above plan body.

### Errors

| Case | Behavior |
| --- | --- |
| Unknown session | 404 via existing `FileNotFoundError` handler |
| Non-demo session | 200 with formula fallback |
| Missing plan/paper | Fallbacks still return valid summary; no 500 |

### Tests

| Area | Coverage |
| --- | --- |
| Core | Seeded fields win; missing metadata uses formula |
| API | 200 shape + 404 missing |
| Frontend | Panel renders on step 3 with mocked summary; optional: non-step-3 does not fetch |

## Implementation task order

1. Model + builder + pytest (TDD)
2. Seed `metadata.student_summary`
3. GET endpoint + API test
4. Client types/methods + vitest
5. `StudentSummaryPanel` + wire App step 3 + vitest
6. VERSION.md Edition 0901_2 note

## Success criteria

- [ ] Demo student deep link shows structured task/stars summary on 学习计划
- [ ] Non-demo sessions still get a valid formula-based summary
- [ ] Pytest + vitest green; VERSION notes Edition 0901_2
