# Edition 0910_1 — Student Timer Fairness (V1) Design

**Date:** 2026-09-10  
**Status:** Revised after round-2 review (awaiting product confirm on countdown length)  
**Scope:** Frontend countdown fairness (pause/resume) + thinking-time telemetry. Server assessment timeout remains wall-clock (looser than client UI).

## Goal

Stop system UI time (`systemWait` / feedback / background) from consuming the student’s assessment countdown, and emit trustworthy per-item **thinking** duration for later analytics (tutor / heatmap), without weakening server timeout trust.

## Decisions (locked)

| Decision | Choice |
|----------|--------|
| Slice | A — student timer fairness (0910_1 §2.1 P0) |
| Duration model | **Scenario B** — frontend **60 min** countdown; server **150 min** wall-clock兜底 |
| Client countdown | Ticks only while **answering**; on mount/refresh, **re-seed from** `assessment_started_at` |
| `elapsed_ms` | **Backward compatible** wall-style (includes pauses) |
| `thinking_ms` | **New authoritative** answering-only ms for 学情 |
| `item_meta_version` | Emit `"v1"` on meta payloads so downstream can migrate to `thinking_ms` |
| Concurrent pause | **OR** to pause; clear when `!shouldPause` |
| `timer_events` | **A** — flush into `session.metadata.timer_events` **per item submit** (cap 200 FIFO) |
| Persist pause budget across refresh | **Out of V1** (accepted); countdown residual **is** re-synced from server start time |
| `systemWait` | Generic system-wait flag (submit/fetch, feedback, future §2.2 LLM) — **not** student tab-hide |
| SessionStore locks | Untouched |

Core slogan: **frontend fair & tighter, backend wall-clock & looser, telemetry traceable.**

## Duration model (Scenario B)

Today’s code exports `ASSESSMENT_SECONDS = 150 * 60` on both client and server (aligned). Product / edition intent is a **60-minute** student-facing countdown. V1 **splits** the constants:

```ts
// frontend/src/constants/timing.ts
/** Student-facing countdown length (tighter UX clock). */
export const ASSESSMENT_SECONDS = 60 * 60

/** Server wall-clock兜底; must match ilearn.core.assessment_timeout.ASSESSMENT_TIMEOUT_SECONDS. */
export const SERVER_TIMEOUT_SECONDS = 150 * 60

export const MAX_VISIBILITY_PAUSE_MS = 10 * 60 * 1000
export const TIMER_EVENTS_CAP = 200
```

```python
# ilearn/core/assessment_timeout.py — unchanged numerically
ASSESSMENT_TIMEOUT_SECONDS = 150 * 60  # server兜底 only; do not force-match frontend UI minutes
```

| Clock | Length | Purpose |
|-------|--------|---------|
| Frontend `ASSESSMENT_SECONDS` | 60 min | What the student sees; fair pause applies here |
| Server `ASSESSMENT_TIMEOUT_SECONDS` | 150 min | Hard submit/timeout trust boundary |

**Trust model:** client cannot extend the server deadline; server is intentionally **more generous** so pause/fairness + minor clock skew do not cause “sudden forced submit” before the student-facing window ends under normal use.

> **Product confirm:** Scenario B is the recommended lock. If product instead wants Scenario A (frontend = server = 150), set `ASSESSMENT_SECONDS = SERVER_TIMEOUT_SECONDS` and keep re-seed logic.

## Duration definitions

| Name | Definition | Use |
|------|------------|-----|
| Wall / `elapsed_ms` | On-item time **including** pauses (today’s flush semantics) | Backward-compatible UI/reports |
| Thinking / `thinking_ms` | Only while state = `answering` | **Authoritative for 学情** |
| `pause_ms` | Sum of pause on item | Totals |
| `pause_ms_busy` | Pause attributed to `systemWait` / feedback | Tests + “系统中断” |
| `pause_ms_visibility` | Pause attributed to tab hidden | Tests + budget accounting |
| Visibility pause budget | Cumulative **visibility** pause ≤ **10 minutes** / assessment session (in-memory) | Anti-abuse; `systemWait` does **not** consume budget |

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

// Resume when !shouldPause (and not submitted).
```

- **OR** to enter/stay paused.  
- Example: `systemWait` ends while tab still `hidden` → **remain paused** until visible (if budget left) or until budget exhausted (then countdown may run while hidden).  
- When visibility budget exhausted: further `hidden` → emit `timer_pause_cap`; countdown **does not** freeze for visibility; `systemWait` can still freeze.

### `systemWait` semantics

```ts
/**
 * Generic system-wait flag.
 * Triggers: submit/fetch, feedback window, future LLM Socratic wait (§2.2).
 * Does NOT include student tab backgrounding (that is visibility’s job).
 */
type SystemWait = boolean
```

### Pause reason sources

1. **`systemWait`** — submit/fetch, feedback, future LLM wait. Does not consume visibility budget.  
2. **Feedback window** — folded into `systemWait`:  
   - Fixed-duration feedback (e.g. 1.5–2s): keep `systemWait` true for that window.  
   - Manual dismiss (“继续”): hold until dismiss, then clear.  
   Attribution: `pause_ms_busy`.  
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

Backend already stores `item_meta` as free-form dict; unknown fields OK.

### `timer_events` (locked: option A, **per-item submit flush**)

- Path: `session.metadata["timer_events"]`  
- Cap: **`TIMER_EVENTS_CAP = 200`**, FIFO drop oldest  
- Write timing: **on each item submit** (not whole-paper end; not every pause/resume)  
- Buffer per `item_id` in memory; flush that item’s events with the submit payload / metadata append; then clear the item buffer  

```ts
const flushItemEvents = (itemId: string) => {
  const events = itemEventBuffers[itemId] || []
  appendToSessionMetadata('timer_events', events) // FIFO cap 200
  itemEventBuffers[itemId] = []
}
```

Discriminated event shapes (`item_id` **required**):

```ts
type TimerEvent =
  | { type: 'timer_pause'; ts: number; item_id: string; reason: 'busy' | 'visibility' | 'feedback' }
  | { type: 'timer_resume'; ts: number; item_id: string; pause_duration_ms: number }
  | { type: 'timer_pause_cap'; ts: number; item_id: string; cap_ms: number }
  | { type: 'item_time_flush'; ts: number; item_id: string; thinking_ms: number; pause_ms: number }
```

Backend: accept & persist; no parse requirement in V1.

## Frontend file touchpoints

| File | Change |
|------|--------|
| `frontend/src/hooks/useCountdown.ts` | `pause` / `resume` / `isPaused`; no tick while paused; on resume if `seconds === 0`, fire `onTimeout` |
| `frontend/src/pages/Assessment.tsx` | systemWait + visibility; dual accumulators; budget; per-item event flush; **re-seed remaining** from session |
| `frontend/src/constants/timing.ts` | `ASSESSMENT_SECONDS`, `SERVER_TIMEOUT_SECONDS`, `MAX_VISIBILITY_PAUSE_MS`, `TIMER_EVENTS_CAP` |
| `frontend/src/api/client.ts` / types | Extend meta + read `metadata.assessment_started_at` |
| Tests | Countdown + Assessment timer edge cases below |

## Recovery (V1)

### Countdown residual (required — avoid “sudden timeout”)

On Assessment mount / full refresh, **do not** blindly start at full `ASSESSMENT_SECONDS`. Pull session (existing `getSession`) and re-seed:

```ts
const startedAt = session.metadata?.assessment_started_at // ISO from server
const elapsedServerSec = startedAt
  ? (Date.now() - Date.parse(startedAt)) / 1000
  : 0
const remainingSec = Math.max(0, ASSESSMENT_SECONDS - elapsedServerSec)
useCountdown(remainingSec, onTimeout)
```

- Uses **client UI length** (`ASSESSMENT_SECONDS` = 60m), not server 150m.  
- If wall elapsed already ≥ 60m, remaining is 0 → timeout path immediately.  
- Server may still allow submits until 150m (兜底).  
- **Tradeoff:** refresh still **drops** in-session pause credit for the countdown (pause fairness is session-local until V1.5). Residual is wall-aligned to start time so UI never shows *more* time than the client window allows.

### Visibility budget

Still **resets on refresh** (accepted cheat surface; refresh also burns server wall-clock and loses local `thinking_ms`). V1.5 may persist budget in `sessionStorage`.

### Other

- No SessionStore lock changes  

## Anti-cheat

- Server wall-clock timeout unchanged at 150 min  
- Client pause cannot extend server deadline  
- Visibility pause capped at `MAX_VISIBILITY_PAUSE_MS`  
- Refresh: countdown residual re-synced; budget reset accepted for V1  

## Testing & acceptance

### Core

1. Paused → seconds frozen; resume → ticks  
2. `systemWait` true → frozen; clear + visible → resume  
3. `hidden` → pause; `visible` → resume; after budget exhausted, further `hidden` does not freeze  
4. On item submit: precise invariants below  
5. Server `apply_submit_timeout` still wall-clock 150 min  
6. Existing single `onTimeout` behavior preserved (including resume-when-zero)  

### Precise meta invariants (±10ms)

```ts
expect(Math.abs(meta.pause_ms - (meta.pause_ms_busy + meta.pause_ms_visibility))).toBeLessThan(10)
expect(meta.pause_ms_busy).toBeGreaterThanOrEqual(0)
expect(meta.pause_ms_visibility).toBeGreaterThanOrEqual(0)
expect(meta.thinking_ms + meta.pause_ms).toBeLessThanOrEqual(meta.elapsed_ms + 10)
// equivalent: thinking_ms ≤ elapsed_ms
expect(meta.thinking_ms).toBeLessThanOrEqual(meta.elapsed_ms + 10)
```

### Boundary (required)

| Scenario | Expected |
|----------|----------|
| `busy` + `hidden` together | Paused; after busy ends still paused until visible (budget allowing) |
| Refresh mid-assessment | No crash; remaining = `max(0, ASSESSMENT_SECONDS - serverElapsed)`; budget resets |
| Visibility budget exactly exhausted | Last budgeted pause OK; subsequent hidden does not freeze |
| Feedback inside systemWait | No double-pause bookkeeping |
| Per-item `timer_events` flush | After 5 item submits, metadata contains flush events for all 5 items (subject to cap) |
| `onTimeout` does not fire during pause | Paused with 1s left; advance 5s → no timeout; resume then advance ~1s → fires once |
| Resume when seconds already 0 | `resume()` triggers `onTimeout` immediately (hook responsibility) |

### `onTimeout` while paused (canonical test)

```ts
it('resume 后若仍有剩余秒则继续倒数到 0 再 onTimeout；paused 期间不触发', async () => {
  const onTimeout = vi.fn()
  const { result } = renderHook(() => useCountdown(1, onTimeout))
  act(() => result.current.pause())
  await advanceTimersByTime(5000)
  expect(onTimeout).not.toHaveBeenCalled()
  act(() => result.current.resume())
  await advanceTimersByTime(1100)
  expect(onTimeout).toHaveBeenCalledTimes(1)
})
```

Also cover: start at `0` or resume into `0` → fire once without waiting another tick.

| Metric | V1 target |
|--------|-----------|
| systemWait/feedback freeze | Automated |
| `thinking_ms` on answered items | ≥ 95% smoke |
| Split pause fields usable in tests | Yes |
| Server wall timeout | Unchanged (150 min) |
| Client UI length | 60 min + start-time re-seed |

## Non-goals (V1)

- Server timeout on thinking time  
- Persist pause budget or pause-credit across reload (V1.5 optional)  
- OpenTelemetry dashboards, parent weekly digest, Socratic LLM UI, heatmap  
- Changing SessionStore locking  

## Relation to edition_0910_1

Implements **§2.1** only. `systemWait` is defined generically so **§2.2** LLM wait can set the same flag without refactoring the timer.
