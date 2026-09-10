# Edition 0910_1 — Student Timer Fairness (V1) Design

**Date:** 2026-09-10  
**Status:** Approved for implementation planning (revised after review clarifications)  
**Scope:** Frontend-only countdown fairness (pause/resume) + thinking-time telemetry. Server assessment timeout remains wall-clock.

## Goal

Stop system UI time (`busy` / system wait, feedback, background) from consuming the student’s assessment countdown, and emit trustworthy per-item **thinking** duration for later analytics (tutor / heatmap), without changing server timeout trust model.

## Decisions (locked)

| Decision | Choice |
|----------|--------|
| Slice | A — student timer fairness (0910_1 §2.1 P0) |
| Server timeout | Wall-clock 150 min via `assessment_started_at` (unchanged) |
| Client countdown | Ticks only while **answering** |
| `elapsed_ms` | **Backward compatible** wall-style (includes pauses) |
| `thinking_ms` | **New authoritative** answering-only ms for 学情 |
| `item_meta_version` | Emit `"v1"` on meta payloads so downstream can migrate to `thinking_ms` |
| Concurrent pause | **OR** to pause; **AND** to resume (see below) |
| `timer_events` | **A** — flush into `session.metadata.timer_events` on submit (cap 200 FIFO) |
| Persist remaining seconds / pause budget across refresh | **Out of V1** (risk accepted; V1.5 optional `sessionStorage`) |
| `busy` | Generic **system-wait** flag (not only submit/fetch) — ready for §2.2 LLM wait |
| SessionStore locks | Untouched |

Core slogan: **frontend fair, backend wall-clock, telemetry traceable.**

## Duration definitions

| Name | Definition | Use |
|------|------------|-----|
| Wall / `elapsed_ms` | On-item time **including** pauses (today’s flush semantics) | Backward-compatible UI/reports |
| Thinking / `thinking_ms` | Only while state = `answering` | **Authoritative for 学情** |
| `pause_ms` | Sum of pause on item | Totals |
| `pause_ms_busy` | Pause attributed to system-wait / feedback | Tests + “系统中断” |
| `pause_ms_visibility` | Pause attributed to tab hidden | Tests + budget accounting |
| Visibility pause budget | Cumulative **visibility** pause ≤ **10 minutes** / assessment session | Anti-abuse; busy/feedback do **not** consume budget |

Whole-paper countdown: decrements only in `answering`.

### Compatibility risk (`elapsed_ms`)

Legacy pipelines that treat `elapsed_ms` as “thinking time” will **overstate** effort after V1 (pauses included).  

**Migration:** when `item_meta_version === "v1"`, downstream **must** use `thinking_ms` for 学情; keep `elapsed_ms` only for wall-clock / display compatibility.

## State machine

```text
idle → answering ⇄ paused → submitted
```

| State | Countdown | thinking_ms | Notes |
|-------|-----------|-------------|-------|
| `idle` | stopped | no | Pre-start / brief gap |
| `answering` | running | accumulates | Student can answer |
| `paused` | frozen | no | See pause formula |
| `submitted` | stopped | no | Item/paper submitted |

### Pause / resume formula (P0)

```ts
const shouldPause =
  systemWait /* busy */ ||
  (visibilityHidden && visibilityBudgetLeft);

// Resume only when BOTH conditions clear:
// !systemWait && !(visibilityHidden && visibilityBudgetLeft)
// Equivalently: resume when !shouldPause (and not submitted).
```

- **OR** to enter/stay paused: any active pause reason freezes the clock.  
- **AND**-clear to resume: e.g. `busy` ends while tab still `hidden` → **remain paused** until visible (if budget left) or until budget exhausted (then countdown may run while hidden).  
- When visibility budget exhausted: further `hidden` → emit `timer_pause_cap`; countdown **does not** freeze for visibility; `systemWait` can still freeze.

### Pause reason sources

1. **`systemWait` (`busy`)** — any system wait: submit/fetch **and** future LLM Socratic wait (§2.2). Does not consume visibility budget.  
2. **Feedback window** — folded into `systemWait`:  
   - Fixed-duration feedback (e.g. 1.5s): keep `busy`/systemWait true for that window.  
   - Manual dismiss (“继续”): hold systemWait until dismiss, then clear.  
   No separate pause reason beyond busy attribution (`pause_ms_busy`).  
3. **Visibility** — `document.visibilityState === 'hidden'`, subject to budget.

## Data / API

### `AssessmentItemMeta` (V1)

```ts
{
  item_meta_version: "v1"
  elapsed_ms: number           // wall (includes paused)
  thinking_ms: number          // answering only
  pause_count?: number
  pause_ms?: number            // total pause on item
  pause_ms_busy?: number       // systemWait / feedback
  pause_ms_visibility?: number // tab hidden
  hint_used: boolean
}
```

Backend already stores `item_meta` as free-form dict (`orchestrator` → `session.metadata["item_meta"]`); unknown fields OK.

### `timer_events` (locked: option A)

- Path: `session.metadata["timer_events"]`  
- Cap: **`TIMER_EVENTS_CAP = 200`**, FIFO drop oldest  
- Write timing: **once on submit flush** (not on every pause/resume)  
- Event shapes (illustrative): `{ type, ts, item_id?, reason?, ... }` where `type` ∈ `timer_pause` | `timer_resume` | `timer_pause_cap` | `item_time_flush`  
- Backend: accept & persist; no parse requirement in V1  

## Constants

Prefer a small shared module (names locked):

```ts
// frontend/src/constants/timing.ts  (or colocated exports)
export const ASSESSMENT_SECONDS = 150 * 60  // keep existing Assessment export value
export const MAX_VISIBILITY_PAUSE_MS = 10 * 60 * 1000
export const TIMER_EVENTS_CAP = 200
```

Keep `ASSESSMENT_SECONDS` numerically aligned with `ilearn.core.assessment_timeout.ASSESSMENT_TIMEOUT_SECONDS` (150 minutes).

## Frontend file touchpoints

| File | Change |
|------|--------|
| `frontend/src/hooks/useCountdown.ts` | `pause` / `resume` / `isPaused`; no tick while paused |
| `frontend/src/pages/Assessment.tsx` | systemWait + visibility OR/AND; dual accumulators; budget; submit flush events |
| `frontend/src/constants/timing.ts` | Shared constants (optional extract from Assessment) |
| `frontend/src/api/client.ts` / Assessment types | Extend meta fields + `item_meta_version` |
| Tests | Countdown + Assessment timer edge cases below |

## Recovery (V1)

- Tab background: visibility pause/resume + budget  
- Full page refresh: countdown **and visibility budget reset**; thinking buffers lost — **accepted risk** (refresh also burns server wall-clock; not a strong cheat). V1.5 may persist budget in `sessionStorage`.  
- No SessionStore lock changes  

## Anti-cheat

- Server wall-clock timeout unchanged  
- Client pause cannot extend server deadline  
- Visibility pause capped at `MAX_VISIBILITY_PAUSE_MS`  
- Refresh reset of budget explicitly accepted for V1  

## Testing & acceptance

### Core

1. Paused → seconds frozen; resume → ticks  
2. `systemWait` true → frozen; clear + visible → resume  
3. `hidden` → pause; `visible` → resume; after budget exhausted, further `hidden` does not freeze  
4. On submit: `thinking_ms ≤ elapsed_ms`; `pause_ms_busy` / `pause_ms_visibility` sum coherently with `pause_ms`  
5. Server `apply_submit_timeout` still wall-clock  
6. Existing single `onTimeout` behavior preserved  

### Boundary (required)

| Scenario | Expected |
|----------|----------|
| `busy` + `hidden` together | Paused; after busy ends still paused until visible (budget allowing) |
| Refresh during busy | No crash; countdown resets; budget resets |
| Visibility budget exactly exhausted | Last budgeted pause OK; subsequent hidden does not freeze |
| Submit invariants | `thinking_ms ≤ elapsed_ms` always |
| Feedback inside systemWait | No double-pause bookkeeping |
| `onTimeout` while paused | Fire only after resume when remaining hits 0 (or equivalent: do not fire mid-pause; after resume, immediate timeout if seconds already 0) |

| Metric | V1 target |
|--------|-----------|
| systemWait/feedback freeze | Automated |
| `thinking_ms` on answered items | ≥ 95% smoke |
| Split pause fields usable in tests | Yes |
| Server wall timeout | Unchanged |

## Non-goals (V1)

- Server timeout on thinking time  
- Persist countdown residual or pause budget across reload (V1.5 optional)  
- OpenTelemetry dashboards, parent weekly digest, Socratic LLM UI, heatmap  
- Changing SessionStore locking  

## Relation to edition_0910_1

Implements **§2.1** only. `systemWait` is defined generically so **§2.2** LLM wait can set the same flag without refactoring the timer.
