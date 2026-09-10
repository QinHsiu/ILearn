# Edition 0910_1 — Student Timer Fairness (V1) Design

**Date:** 2026-09-10  
**Status:** Product-confirmed (Scenario B); revised for overtime, attribution, flush-all, refresh incompleteness  
**Scope:** Frontend countdown fairness (pause/resume) + thinking-time telemetry. Server 150 min is hard anti-bypass ceiling only.

## Goal

Stop system UI time (`systemWait` / feedback / background) from consuming the student’s assessment countdown, and emit trustworthy per-item **thinking** duration for later analytics (tutor / heatmap), without weakening server timeout trust.

## Decisions (locked)

| Decision | Choice |
|----------|--------|
| Slice | A — student timer fairness (0910_1 §2.1 P0) |
| Duration model | **Scenario B (confirmed)** — UI **60 min**; server **150 min** hard ceiling |
| At UI 60→0 | **Continue timing** (overtime). **No** auto-submit, **no** UI lock. Overtime **increases evaluation weight** downstream |
| Server 150 | Anti-bypass / hung-session hard stop only — **not** “extra free quiz time” as a product feature |
| Client countdown | Ticks only while **answering**; mount/refresh **re-seeds** from `assessment_started_at` (may already be overtime) |
| `elapsed_ms` | Wall-style (includes pauses) — backward compatible |
| `thinking_ms` | Authoritative answering-only ms for 学情 |
| Pause attribution | **Busy-priority exclusive** — no double-count overlap |
| Concurrent pause gate | **OR** to pause; resume when `!shouldPause` |
| `timer_events` | Flush to `session.metadata.timer_events` via **`flushAllItemEvents()`** on all exit paths (cap 200 FIFO) |
| Refresh | Budget resets; mark incomplete thinking; exclude from ≥95% metric |
| `systemWait` | Generic system wait (submit/fetch, feedback, future §2.2 LLM) — not tab-hide |
| SessionStore locks | Untouched |

Core slogan: **frontend fair & tighter, overtime weighted, backend hard ceiling, telemetry traceable.**

## Duration model (Scenario B — confirmed)

```ts
// frontend/src/constants/timing.ts
/** Student-facing fair window (UI deadline). */
export const ASSESSMENT_SECONDS = 60 * 60

/** Server hard ceiling; match ilearn.core.assessment_timeout.ASSESSMENT_TIMEOUT_SECONDS. */
export const SERVER_TIMEOUT_SECONDS = 150 * 60

export const MAX_VISIBILITY_PAUSE_MS = 10 * 60 * 1000
export const TIMER_EVENTS_CAP = 200
```

```python
# ilearn/core/assessment_timeout.py
ASSESSMENT_TIMEOUT_SECONDS = 150 * 60  # hard ceiling only
```

| Clock | Length | Role |
|-------|--------|------|
| UI `ASSESSMENT_SECONDS` | 60 min | Fair window; after this → **overtime mode** |
| Server `ASSESSMENT_TIMEOUT_SECONDS` | 150 min | Hard submit rejection / forced timeout — anti-bypass |

### Behavior when UI clock reaches 0

| Action | V1 |
|--------|-----|
| Auto-submit paper | **No** (today’s `submitFull` on `onTimeout` is **removed**) |
| Lock answering UI | **No** |
| Continue clock | **Yes** — keep ticking in `answering`; display overtime (e.g. `+MM:SS` or signed remaining) |
| Callback | Rename semantics to **`onUiDeadline`**: fire **once** when crossing 0 → set session flags / start overtime accumulation |
| Evaluation | Overtime interval **increases weight** on assessment / 评测 consideration (see below) |
| Server 150 | Still the only hard stop; client cannot submit past server timeout |

**Overtime weighting (V1 telemetry + hook):**

- Session/item meta emits e.g. `ui_deadline_crossed: true`, `overtime_ms` (answering time after UI deadline; pause rules still apply).  
- Downstream 学情 / scoring **must** treat overtime as **higher weight** than in-window thinking (exact formula can live in diagnosis later; V1 guarantees fields exist).  
- Server 150 does **not** redefine the pedagogical window — it only prevents indefinite / forged clients.

### Re-seed on mount / refresh

```ts
const startedAt = session.metadata?.assessment_started_at
const elapsedServerSec = startedAt
  ? (Date.now() - Date.parse(String(startedAt))) / 1000
  : 0
// May be negative → already in overtime; do NOT clamp to 0 for auto-submit.
const remainingSec = ASSESSMENT_SECONDS - elapsedServerSec
useCountdown(remainingSec, onUiDeadline)
```

- If `remainingSec < 0` on load: enter overtime display immediately; set `ui_deadline_crossed` if not already; **do not** auto-submit.  
- Pause credit still lost on refresh (session-local until V1.5).

## Duration definitions

| Name | Definition | Use |
|------|------------|-----|
| Wall / `elapsed_ms` | On-item time including pauses | Compatibility |
| Thinking / `thinking_ms` | Only while `answering` (includes overtime answering) | 学情 (if complete) |
| `overtime_ms` | Answering time after UI deadline on item/session | Evaluation weight |
| `pause_ms` | Total pause on item | Totals |
| `pause_ms_busy` | Exclusive busy/feedback pause | System interrupt |
| `pause_ms_visibility` | Exclusive visibility pause (non-busy only) | Budget + “主动切走” |
| Visibility budget | Cumulative **visibility-attributed** pause ≤ 10 min / session (in-memory) | Anti-abuse |

Invariant (exclusive attribution):

```text
pause_ms = pause_ms_busy + pause_ms_visibility   (±10ms)
```

### Compatibility risk (`elapsed_ms`)

Legacy pipelines treating `elapsed_ms` as thinking will overstate effort. When `item_meta_version === "v1"`, use `thinking_ms` (+ `overtime_ms` / flags for weight).

## State machine

```text
idle → answering ⇄ paused → submitted
         │
         └─ (seconds ≤ 0) answering continues in overtime; answering still allowed
```

| State | Countdown | thinking_ms | Notes |
|-------|-----------|-------------|-------|
| `idle` | stopped | no | Pre-start |
| `answering` | running (may be ≤0 / overtime) | yes | Student can answer |
| `paused` | frozen | no | See pause formula |
| `submitted` | stopped | no | Item done |

### Pause / resume formula

```ts
const shouldPause =
  systemWait ||
  (visibilityHidden && visibilityBudgetLeft)
```

### Pause attribution (busy-priority, exclusive)

Overlapping `systemWait` + `hidden` must **not** double-count.

```ts
// While paused, attribute elapsed pause slice exclusively:
if (systemWait) {
  pause_ms_busy += dt        // feedback folded into busy
  // visibility does NOT accumulate; budget does NOT consume for this slice
} else if (visibilityHidden && visibilityBudgetLeft) {
  pause_ms_visibility += dt
  visibilityBudgetUsed += dt
}
pause_ms = pause_ms_busy + pause_ms_visibility
```

Transition while paused: if visibility-only pause then `systemWait` becomes true → switch attribution to busy for subsequent slices (close visibility segment first).

### `systemWait` semantics

```ts
/**
 * Generic system-wait flag.
 * Triggers: submit/fetch, feedback window, future LLM Socratic wait (§2.2).
 * Does NOT include student tab backgrounding (visibility’s job).
 */
type SystemWait = boolean
```

Feedback: fixed duration or until dismiss — always via `systemWait` → `pause_ms_busy`.

## Data / API

### `AssessmentItemMeta` (V1)

```ts
{
  item_meta_version: "v1"
  elapsed_ms: number
  thinking_ms: number
  overtime_ms?: number
  ui_deadline_crossed?: boolean
  thinking_ms_incomplete?: boolean  // refresh / ungraceful loss
  pause_count?: number
  pause_ms?: number
  pause_ms_busy?: number
  pause_ms_visibility?: number
  hint_used: boolean
}
```

### `timer_events`

- Path: `session.metadata["timer_events"]`  
- Cap: `TIMER_EVENTS_CAP = 200`, FIFO  
- **Not** only per-item submit — use unified flush:

```ts
function flushItemEvents(itemId: string) { /* append buffer; clear; FIFO cap */ }

function flushAllItemEvents() {
  for (const itemId of Object.keys(itemEventBuffers)) {
    flushItemEvents(itemId)
  }
}
```

**Call `flushAllItemEvents()` (or current-item + all buffers) before:**

| Trigger | Why |
|---------|-----|
| Each item submit | Normal path |
| Full paper submit | Catch open buffers |
| UI/server timeout handling | Unanswered items still have buffers |
| Assessment unmount / `pagehide` / `beforeunload` (best effort) | Avoid silent loss |
| Phase leave | Same |

Also emit `item_time_flush` for the **current** open item even if unanswered when flushing on timeout/unmount.

```ts
type TimerEvent =
  | { type: 'timer_pause'; ts: number; item_id: string; reason: 'busy' | 'visibility' | 'feedback' }
  | { type: 'timer_resume'; ts: number; item_id: string; pause_duration_ms: number }
  | { type: 'timer_pause_cap'; ts: number; item_id: string; cap_ms: number }
  | { type: 'item_time_flush'; ts: number; item_id: string; thinking_ms: number; pause_ms: number; incomplete?: boolean }
  | { type: 'timer_refresh'; ts: number; item_id?: string }  // best-effort on unload/remount detect
  | { type: 'ui_deadline'; ts: number }
```

## Frontend file touchpoints

| File | Change |
|------|--------|
| `useCountdown.ts` | pause/resume; allow `seconds ≤ 0` overtime tick; `onUiDeadline` once at crossing; display helper for overtime |
| `Assessment.tsx` | Remove auto-`submitFull` on deadline; systemWait + visibility; exclusive attribution; budget; `flushAllItemEvents`; re-seed; overtime flags |
| `constants/timing.ts` | Shared constants |
| API types | Meta fields + `assessment_started_at` |
| Tests | See below — **do not** expect auto-submit at 60 |

## Recovery (V1)

### Visibility budget

Resets on full refresh — accepted. V1.5: optional `sessionStorage`.

### Refresh vs `thinking_ms` (explicit)

Refresh loses in-memory thinking for the **current unsubmitted item** and resets visibility budget.

**V1 mitigations (required):**

1. Best-effort `flushAllItemEvents()` + `timer_refresh` on `pagehide`/`beforeunload`.  
2. On remount, if prior open item had no complete flush, subsequent analytics treat missing/partial as `thinking_ms_incomplete: true`.  
3. **Acceptance metric:** `thinking_ms` ≥95% applies only to items with **successful submit flush** and **`thinking_ms_incomplete !== true`**. Incomplete / refresh-abandoned items are **excluded** from that denominator so teachers/heatmap do not silently under-read effort as “fast.”

## Anti-cheat

- Server 150 min hard ceiling unchanged  
- Client pause cannot extend server deadline  
- Visibility pause capped; busy does not consume budget  
- Overtime allowed on client until server hard stop; overtime is **weighted**, not free  

## Testing & acceptance

### Core

1. Pause freezes; resume ticks (including overtime region)  
2. `systemWait` freezes; clear + visible → resume  
3. Visibility pause + budget exhaustion  
4. Exclusive attribution invariants  
5. Server `apply_submit_timeout` still 150 min wall-clock  
6. UI deadline: **no** auto-submit; overtime continues; `onUiDeadline` once  

### Precise meta invariants (±10ms)

```ts
expect(Math.abs(meta.pause_ms - (meta.pause_ms_busy + meta.pause_ms_visibility))).toBeLessThan(10)
expect(meta.pause_ms_busy).toBeGreaterThanOrEqual(0)
expect(meta.pause_ms_visibility).toBeGreaterThanOrEqual(0)
expect(meta.thinking_ms).toBeLessThanOrEqual(meta.elapsed_ms + 10)
```

Overlap case: while both busy and hidden, only `pause_ms_busy` increases.

### Boundary

| Scenario | Expected |
|----------|----------|
| busy + hidden | Paused; attribution → busy only for overlap |
| UI 60→0 | Keep answering; overtime display; no auto-submit |
| Refresh mid-item | Re-seed (possibly overtime); budget reset; incomplete excluded from ≥95% |
| `flushAllItemEvents` | Item submit, paper submit, timeout path, unmount all flush |
| 5 item submits | Events for all 5 (cap permitting) |
| Pause then resume across 0 | No deadline callback while paused; after resume, cross/fire once as designed |

| Metric | V1 target |
|--------|-----------|
| systemWait/feedback freeze | Automated |
| Complete `thinking_ms` on submitted, non-incomplete items | ≥ 95% smoke |
| Split pause fields + exclusive overlap | Yes |
| Server hard ceiling | 150 min unchanged |
| UI window | 60 min + overtime weight fields |

## Non-goals (V1)

- Exact numeric overtime→score formula in diagnosis (emit fields + document weight intent; formula can follow)  
- Persist pause budget / pause-credit across reload  
- OpenTelemetry dashboards, parent digest, Socratic LLM UI, heatmap UI  
- SessionStore locking changes  

## Relation to edition_0910_1

Implements **§2.1** only. `systemWait` stays generic for **§2.2** LLM wait.
