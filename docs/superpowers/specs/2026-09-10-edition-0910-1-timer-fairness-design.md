# Edition 0910_1 — Student Timer Fairness (V1) Design

**Date:** 2026-09-10  
**Status:** Approved for implementation planning  
**Scope:** Frontend-only countdown fairness (pause/resume) + thinking-time telemetry. Server assessment timeout remains wall-clock.

## Goal

Stop system UI time (`busy`, feedback, background) from consuming the student’s assessment countdown, and emit trustworthy per-item **thinking** duration for later analytics (tutor / heatmap), without changing server timeout trust model.

## Decisions (locked)

| Decision | Choice |
|----------|--------|
| Slice | A — student timer fairness (0910_1 P0) |
| Server timeout | Wall-clock 150 min via `assessment_started_at` (unchanged) |
| Client countdown | Ticks only while **answering**; pauses for busy / feedback / visibility |
| `elapsed_ms` | **Backward compatible** — keep existing wall-style accumulation semantics |
| `thinking_ms` | **New authoritative** field for learning analytics (answering only) |
| Persist remaining seconds across refresh | **Out of V1** |
| SessionStore locks | Untouched |

Core slogan: **frontend fair, backend wall-clock, telemetry traceable.**

## Duration definitions

| Name | Definition | Use |
|------|------------|-----|
| Wall / `elapsed_ms` | Time on item including pauses (compatible with today’s flush) | Backward-compatible clients / reports |
| Thinking / `thinking_ms` | Only while state = `answering` | Countdown fairness signal for analytics; **authoritative for 学情** |
| Visibility pause budget | Cumulative visibility-driven pause ≤ **10 minutes** per assessment session | Anti-abuse; busy/feedback pauses do **not** consume this budget |

Whole-paper countdown (`ASSESSMENT_SECONDS`): decrements only in `answering`.

## State machine

```text
idle → answering ⇄ paused → submitted
```

| State | Countdown | thinking_ms | Notes |
|-------|-----------|-------------|-------|
| `idle` | stopped | no | Pre-start / brief gap |
| `answering` | running | accumulates | Student can answer |
| `paused` | frozen | no | `busy`, feedback window, or `visibilityState=hidden` (if budget left) |
| `submitted` | stopped | no | Item/paper submitted |

### Pause triggers (V1)

1. `busy === true` (submit / fetch) — **must** pause; does not use visibility budget  
2. Explicit feedback display window if present — same as busy  
3. `document.visibilityState === 'hidden'` — pause if visibility pause budget remaining; on `visible`, resume if not submitted  

When visibility budget exhausted: further `hidden` events are recorded (`timer_pause_cap`) but countdown **keeps running**.

## Data / API

Extend `AssessmentItemMeta` (backend may ignore unknown keys):

```ts
{
  elapsed_ms: number      // existing: wall-style on-item time (compatible)
  thinking_ms: number     // new authoritative answering-only ms
  pause_count?: number
  pause_ms?: number       // paused time on this item (all pause reasons)
  hint_used: boolean
}
```

Optional session-level `metadata.timer_events` (cap 200) for traceability — or client-only test hooks in V1 if metadata write is awkward; prefer attach events on submit path when cheap.

## Frontend file touchpoints

| File | Change |
|------|--------|
| `frontend/src/hooks/useCountdown.ts` | Add `pause` / `resume` / `isPaused`; no tick while paused |
| `frontend/src/pages/Assessment.tsx` | Wire busy + visibility; dual accumulate wall vs thinking; pause cap |
| `frontend/src/api/client.ts` (types) | Extend `AssessmentItemMeta` |
| Tests | `useCountdown.test.ts`, Assessment timer behavior tests |

## Recovery (V1)

- Tab background: pause/resume via Page Visibility API + budget  
- Full page refresh: countdown **restarts** from `ASSESSMENT_SECONDS` (no server residual); acceptable for V1  
- No conflict with `SessionStore` locks  

## Anti-cheat

- Server still enforces wall-clock timeout (`ilearn/core/assessment_timeout.py`)  
- Client cannot extend server deadline via pause  
- Visibility pause capped at 10 minutes cumulative  

## Testing & acceptance

1. While paused, displayed seconds unchanged; after resume, ticks again  
2. During `busy`, countdown frozen; after busy clears, resumes  
3. `hidden` → pause; `visible` → resume; after 10 min visibility pause budget, further hidden does not freeze  
4. Submit meta includes `thinking_ms` ≤ wall `elapsed_ms` for same item when pauses occurred  
5. Server timeout regression: `apply_submit_timeout` still wall-clock based  
6. Existing “onTimeout fires once” countdown tests still pass  

| Metric | V1 target |
|--------|-----------|
| Busy/feedback freeze countdown | Covered by automated tests |
| `thinking_ms` present on answered items’ meta | ≥ 95% in manual/smoke when flag path used |
| Visibility pause recoverable | Tested |
| Server wall timeout | Unchanged |

## Non-goals (V1)

- Server timeout based on thinking time  
- Persist remaining countdown across reload  
- OpenTelemetry, weekly parent digest, Socratic LLM, heatmap  
- Changing SessionStore locking  

## Relation to edition_0910_1

Implements **§2.1 计时与反馈的公平性 (P0)** only, with the agreed V1 trust boundary (frontend fair / backend wall-clock).
