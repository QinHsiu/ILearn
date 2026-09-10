# Edition 0910_1 Timer Fairness Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship fair student countdown (pause on systemWait/visibility), authoritative `thinking_ms` / exclusive pause splits, UI 60→overtime (no auto-submit), and flushable `timer_events` — without changing the server 150 min hard ceiling.

**Architecture:** Extend `useCountdown` for pause + overtime + one-shot `onUiDeadline`. Drive pause from Assessment via **`systemWaitCount`** (not a bare boolean) and visibility budget. Track open-item completeness in **`sessionStorage`**. Flush events on all exits; unload uses **`sendBeacon` / `fetch keepalive`** to a thin telemetry route (else accept loss + incomplete marker). Server still wall-clock 150 via `assessment_timeout.py`.

**Tech Stack:** React 19, Vite, Vitest, Testing Library, FastAPI/`Orchestrator`, existing `frontend/src/api/client.ts`. Spec: `docs/superpowers/specs/2026-09-10-edition-0910-1-timer-fairness-design.md`.

## Global Constraints

- **Scenario B:** `ASSESSMENT_SECONDS = 60 * 60`; `SERVER_TIMEOUT_SECONDS` / `ASSESSMENT_TIMEOUT_SECONDS = 150 * 60`
- UI 60→0: **continue** overtime; **no** auto-`submitFull`; **no** UI lock; emit overtime fields for downstream **weight** (not free time)
- `systemWait` = **`systemWaitCount > 0`** (refcount); never a lone boolean that one caller can clear while another wait is live
- Pause attribution: **busy-priority exclusive** → `pause_ms = pause_ms_busy + pause_ms_visibility` (±10ms)
- `overtime_ms` ⊆ `thinking_ms` — downstream must **not** double-count (`weight(base) + weight(overtime)` where `base = thinking_ms - overtime_ms`)
- `onUiDeadline` ≠ server timeout; fires **once** when UI crosses 0 **or** mount remaining already ≤ 0
- Incomplete detect: sessionStorage open-item marker; remount → `thinking_ms_incomplete: true`; ≥95% metric **excludes** incomplete
- Unload flush: prefer `navigator.sendBeacon` or `fetch(..., { keepalive: true })`; if transport fails, **do not** pretend flush succeeded — rely on incomplete marker
- Do **not** change SessionStore locks; do **not** make server timeout thinking-based
- PowerShell: no `&&`, no bash heredocs for commits; `docs/` may need `git add -f`

### Implementation locks (acceptance blockers)

| Lock | Rule |
|------|------|
| L1 `systemWaitCount` | `acquireSystemWait()` / `releaseSystemWait()`; `systemWait = count > 0` |
| L2 incomplete detect | On item start write `sessionStorage["ilearn:timer:open:"+sessionId] = { item_id, started_at, flushed:false }`; clear on successful `item_time_flush`; remount if present → mark that `item_id` incomplete |
| L3 unload transport | Try beacon/keepalive to `POST /sessions/{id}/timer-telemetry`; on failure/absence of guarantee, only L2 applies |

### Semantics (also locked)

1. **`overtime_ms` subset of `thinking_ms`:** answering ms after UI deadline is counted in both; weighted eval uses in-window `(thinking_ms - overtime_ms)` plus a **higher coefficient on `overtime_ms` only** — never `thinking_ms + overtime_ms`.
2. **`onUiDeadline` vs server 150:** rename Assessment callback away from auto-submit `onTimeout`; server path stays `apply_submit_timeout` / `assessment_timed_out` only at 150 wall minutes.

### File map

| Path | Role |
|------|------|
| `frontend/src/constants/timing.ts` | Shared timing constants |
| `frontend/src/hooks/useCountdown.ts` | pause/resume, overtime tick, `onUiDeadline` |
| `frontend/src/hooks/useCountdown.test.ts` | Hook tests |
| `frontend/src/lib/timerOpenItem.ts` | sessionStorage open-item helpers |
| `frontend/src/lib/timerOpenItem.test.ts` | Incomplete detect unit tests |
| `frontend/src/lib/timerEvents.ts` | buffers, FIFO cap, flush helpers, unload transport |
| `frontend/src/lib/timerEvents.test.ts` | Cap + flush unit tests |
| `frontend/src/pages/Assessment.tsx` | Wire wait count, visibility, meta, re-seed, remove auto-submit |
| `frontend/src/pages/Assessment.test.tsx` | Integration / boundary |
| `frontend/src/api/client.ts` | Types + `appendTimerTelemetry` |
| `ilearn/api/app.py` | `timer_events` on submit; `POST .../timer-telemetry` |
| `ilearn/agents/orchestrator.py` | Merge `timer_events` FIFO 200; telemetry merge |
| `ilearn/core/assessment_timeout.py` | Comment: 150 = hard ceiling ≠ UI 60 |
| `tests/test_timer_telemetry.py` (or extend existing) | Backend merge / cap |

---

### Task 1: Timing constants + meta / event types

**Files:**
- Create: `frontend/src/constants/timing.ts`
- Modify: `frontend/src/api/client.ts` (export / align `AssessmentItemMeta` if defined there; else keep page-local and re-export from a small `frontend/src/types/assessmentMeta.ts`)
- Modify: `frontend/src/pages/Assessment.tsx` — import `ASSESSMENT_SECONDS` from constants; delete local `150 * 60` export or re-export from constants for back-compat
- Modify: `ilearn/core/assessment_timeout.py` — comment only (still `150 * 60`)
- Test: `frontend/src/constants/timing.test.ts` (optional assert values)

**Interfaces:**
- Produces:
```ts
export const ASSESSMENT_SECONDS = 60 * 60
export const SERVER_TIMEOUT_SECONDS = 150 * 60
export const MAX_VISIBILITY_PAUSE_MS = 10 * 60 * 1000
export const TIMER_EVENTS_CAP = 200
export const TIMER_OPEN_ITEM_KEY_PREFIX = 'ilearn:timer:open:'
```
- Produces meta shape (TypeScript):
```ts
export type AssessmentItemMeta = {
  item_meta_version: 'v1'
  elapsed_ms: number
  thinking_ms: number
  overtime_ms?: number
  ui_deadline_crossed?: boolean
  thinking_ms_incomplete?: boolean
  pause_count?: number
  pause_ms?: number
  pause_ms_busy?: number
  pause_ms_visibility?: number
  hint_used: boolean
}
```
- Produces:
```ts
export type TimerEvent =
  | { type: 'timer_pause'; ts: number; item_id: string; reason: 'busy' | 'visibility' | 'feedback' }
  | { type: 'timer_resume'; ts: number; item_id: string; pause_duration_ms: number }
  | { type: 'timer_pause_cap'; ts: number; item_id: string; cap_ms: number }
  | { type: 'item_time_flush'; ts: number; item_id: string; thinking_ms: number; pause_ms: number; incomplete?: boolean }
  | { type: 'timer_refresh'; ts: number; item_id?: string }
  | { type: 'ui_deadline'; ts: number }
```

- [ ] **Step 1: Write failing constant test**

```ts
import { ASSESSMENT_SECONDS, SERVER_TIMEOUT_SECONDS, TIMER_EVENTS_CAP } from './timing'
it('locks Scenario B durations', () => {
  expect(ASSESSMENT_SECONDS).toBe(3600)
  expect(SERVER_TIMEOUT_SECONDS).toBe(150 * 60)
  expect(TIMER_EVENTS_CAP).toBe(200)
})
```

- [ ] **Step 2: Run FAIL** — `cd frontend; npm test -- src/constants/timing.test.ts`

- [ ] **Step 3: Add `timing.ts`, wire Assessment import, comment `assessment_timeout.py`**

- [ ] **Step 4: Tests PASS**

- [ ] **Step 5: Commit**

```bash
git add frontend/src/constants/timing.ts frontend/src/constants/timing.test.ts frontend/src/pages/Assessment.tsx ilearn/core/assessment_timeout.py
git commit -m "feat(timing): Scenario B ASSESSMENT_SECONDS 60m vs server 150m"
```

---

### Task 2: `useCountdown` — pause, overtime, `onUiDeadline`

**Files:**
- Modify: `frontend/src/hooks/useCountdown.ts`
- Modify: `frontend/src/hooks/useCountdown.test.ts`

**Interfaces:**
- Consumes: none
- Produces:
```ts
export function useCountdown(
  initialSeconds: number,
  options?: {
    enabled?: boolean          // default true when initialSeconds !== 0 OR explicitly passed from Assessment
    onUiDeadline?: () => void  // NOT server timeout; NOT auto-submit
  },
): {
  seconds: number              // may be < 0 in overtime
  isPaused: boolean
  isUiDeadlinePassed: boolean
  format: () => string         // MM:SS while >=0; +MM:SS when <0
  pause: () => void
  resume: () => void
  reset: (nextSeconds?: number) => void
}
```
- **Enabled semantics:** Assessment passes `enabled: countdownActive`. Do **not** use `initialSeconds > 0` as sole active gate (overtime / already-past-deadline must keep ticking).
- **`onUiDeadline`:** fire once when (a) ticking crosses from `>0` to `<=0`, or (b) `enabled` becomes true with `initialSeconds <= 0`. Never fire while `isPaused`. If paused across the zero boundary, fire on resume when `seconds <= 0` (once).
- **While paused:** interval cleared; `seconds` frozen (including negative).
- **Remove** Assessment’s use of countdown callback to call `submitFullRef`.

- [ ] **Step 1: Rewrite / extend failing tests**

```ts
it('pauses freezing seconds', () => { /* pause at 5; advance 3s; still 5; resume; advance 1s → 4 */ })
it('continues into overtime and formats +MM:SS', () => { /* start 1; advance 2s → seconds === -1; format starts with + */ })
it('onUiDeadline fires once at crossing, not again', () => { /* start 1; advance past 0; called 1x; advance more; still 1x */ })
it('does not fire onUiDeadline while paused; fires after resume if already <=0', () => {
  const onUiDeadline = vi.fn()
  const { result } = renderHook(() => useCountdown(1, { onUiDeadline }))
  act(() => result.current.pause())
  act(() => { vi.advanceTimersByTime(5000) })
  expect(onUiDeadline).not.toHaveBeenCalled()
  act(() => result.current.resume())
  // either immediate if seconds already 0, or after remaining tick
  act(() => { vi.advanceTimersByTime(1100) })
  expect(onUiDeadline).toHaveBeenCalledTimes(1)
})
it('fires once when enabled with initialSeconds already <= 0', () => {
  const onUiDeadline = vi.fn()
  renderHook(() => useCountdown(-30, { enabled: true, onUiDeadline }))
  expect(onUiDeadline).toHaveBeenCalledTimes(1)
})
it('inactive when enabled false even if initialSeconds > 0', () => { /* no tick */ })
```

Keep/adapt existing tests: rename `onTimeout` → `onUiDeadline`; inactive `enabled: false` replaces “initialSeconds = 0 never fires” where needed.

- [ ] **Step 2: Run FAIL** — `cd frontend; npm test -- src/hooks/useCountdown.test.ts`

- [ ] **Step 3: Implement hook**

- [ ] **Step 4: Tests PASS**

- [ ] **Step 5: Commit**

```bash
git commit -m "feat(frontend): useCountdown pause, overtime, onUiDeadline"
```

---

### Task 3: Open-item sessionStorage (incomplete detect)

**Files:**
- Create: `frontend/src/lib/timerOpenItem.ts`
- Create: `frontend/src/lib/timerOpenItem.test.ts`

**Interfaces:**
```ts
export type OpenItemMarker = { item_id: string; started_at: number; flushed: boolean }

export function openItemStorageKey(sessionId: string): string
  // `${TIMER_OPEN_ITEM_KEY_PREFIX}${sessionId}`

export function writeOpenItem(sessionId: string, itemId: string, now?: number): void
  // flushed: false

export function clearOpenItem(sessionId: string): void

export function readOpenItem(sessionId: string): OpenItemMarker | null

export function consumeIncompleteOpenItem(sessionId: string): string | null
  // if marker exists && !flushed → return item_id and clear marker (or leave until explicit clear after meta stamped)
  // Plan lock: return item_id for Assessment to set thinking_ms_incomplete; then clearOpenItem
```

- [ ] **Step 1: Failing tests**

```ts
it('write then consumeIncomplete returns item_id', () => {
  writeOpenItem('s1', 'q1', 1000)
  expect(consumeIncompleteOpenItem('s1')).toBe('q1')
  expect(readOpenItem('s1')).toBeNull()
})
it('clearOpenItem after successful flush prevents incomplete', () => {
  writeOpenItem('s1', 'q1')
  clearOpenItem('s1')
  expect(consumeIncompleteOpenItem('s1')).toBeNull()
})
```

- [ ] **Step 2: Run FAIL**

- [ ] **Step 3: Implement with `sessionStorage` (guard `typeof sessionStorage` for SSR/tests; use mock in vitest)**

- [ ] **Step 4: PASS + Commit**

```bash
git commit -m "feat(frontend): sessionStorage open-item incomplete detect"
```

---

### Task 4: Timer event buffers + FIFO + unload transport helper

**Files:**
- Create: `frontend/src/lib/timerEvents.ts`
- Create: `frontend/src/lib/timerEvents.test.ts`
- Modify: `frontend/src/api/client.ts` — `appendTimerTelemetry(sessionId, body)`

**Interfaces:**
```ts
export function appendFifo<T>(existing: T[], next: T[], cap: number): T[]
  // drop from front until length <= cap

export class TimerEventBuffer {
  push(itemId: string, event: TimerEvent): void
  drain(itemId: string): TimerEvent[]
  drainAll(): TimerEvent[]
}

export function preferKeepaliveSend(
  url: string,
  body: object,
  headers?: Record<string, string>,
): 'beacon' | 'keepalive' | 'failed' {
  // 1) try navigator.sendBeacon(url, blob JSON) if available
  // 2) else try fetch(url, { method:'POST', body, headers, keepalive: true })
  // 3) return 'failed' — caller must NOT clear incomplete marker as success
}
```

- Client:
```ts
appendTimerTelemetry(sessionId: string, payload: {
  timer_events?: TimerEvent[]
  item_meta_patch?: Record<string, Partial<AssessmentItemMeta>>
}): Promise<void>  // normal async path

appendTimerTelemetryKeepalive(sessionId: string, payload: ...): 'beacon' | 'keepalive' | 'failed'
```

- [ ] **Step 1: Unit tests for FIFO + drainAll**

```ts
it('FIFO drops oldest past TIMER_EVENTS_CAP', () => {
  const buf = new TimerEventBuffer()
  // push 201 events across items; drainAll length <= 200 OR appendFifo on merge
})
it('drainAll empties all item buffers', () => { ... })
```

- [ ] **Step 2–4: Implement + PASS + Commit**

```bash
git commit -m "feat(frontend): timer event buffer and keepalive helper"
```

---

### Task 5: Backend merge `timer_events` + telemetry route

**Files:**
- Modify: `ilearn/api/app.py` — extend `SubmitRequest`; add `TimerTelemetryRequest` + `POST /sessions/{session_id}/timer-telemetry`
- Modify: `ilearn/agents/orchestrator.py` — `submit(..., timer_events=)` merge; new `append_timer_telemetry(...)`
- Create: `tests/test_timer_telemetry.py`

**Interfaces:**
```python
def _merge_timer_events(session, events: list[dict], *, cap: int = 200) -> None:
    existing = list(session.metadata.get("timer_events") or [])
    merged = (existing + list(events))[-cap:]  # FIFO drop oldest
    session.metadata["timer_events"] = merged

# submit: after item_meta assign, if timer_events: _merge_timer_events
# append_timer_telemetry: merge events; shallow-merge item_meta_patch into metadata["item_meta"]
```

- Route auth/session load same as heartbeat/submit patterns.
- Telemetry must **not** require answers; must **not** advance phase.

- [ ] **Step 1: Failing pytest**

```python
def test_timer_telemetry_appends_fifo(tmp_path):
    # create session; post 3 events; assert metadata["timer_events"] len 3
    # post 200 more; len == 200; oldest dropped

def test_submit_merges_timer_events(tmp_path):
    # submit with timer_events list → stored

def test_timer_telemetry_patches_incomplete_meta(tmp_path):
    # patch item_meta thinking_ms_incomplete True
```

- [ ] **Step 2: Run FAIL** — `pytest tests/test_timer_telemetry.py -v`

- [ ] **Step 3: Implement merge + routes; wire `api.submit` body to pass `timer_events` when provided**

Update frontend `api.submit` signature:
```ts
submit(sessionId, answers, itemMeta = {}, opts?: { timer_events?: TimerEvent[] })
```

- [ ] **Step 4: PASS + Commit**

```bash
git commit -m "feat(api): merge timer_events on submit and timer-telemetry"
```

---

### Task 6: Wire `Assessment.tsx` (refcount, attribution, re-seed, flush-all)

**Files:**
- Modify: `frontend/src/pages/Assessment.tsx`
- Modify: `frontend/src/pages/Assessment.test.tsx`

**Interfaces / behavior to implement:**

1. **`systemWaitCountRef`** + `acquireSystemWait` / `releaseSystemWait` around every async wait (adaptiveStart, adaptiveContinue, submitFull, image upload if blocking, feedback window). Feedback: acquire at show, release after timeout/dismiss.
2. **Visibility:** `document.visibilitychange`; budget `visibilityPauseUsedRef`; `shouldPause = systemWait || (hidden && budgetLeft)`.
3. **Exclusive attribution** while paused: if `systemWait` → busy only; else visibility (+ budget).
4. **Per-item accumulators:** `thinking_ms`, `pause_ms_*`, `overtime_ms` (only answering time with `isUiDeadlinePassed`); wall `elapsed_ms` includes pauses.
5. **Re-seed:** on mount when phase active, `getSession` → `remainingSec = ASSESSMENT_SECONDS - elapsedServerSec` (may be negative); pass into `useCountdown`.
6. **`onUiDeadline`:** set session-local `uiDeadlineCrossed`; push `{ type:'ui_deadline', ts }`; **do not** submit.
7. **Open item:** `writeOpenItem` on select/start; `clearOpenItem` after successful flush for that item; on mount `consumeIncompleteOpenItem` → remember id for `thinking_ms_incomplete` on next meta build / telemetry patch.
8. **`flushAllItemEvents`:** call before item-level flows that leave buffers, `submitAnchor`, `submitFull`, unmount, and visibility `pagehide`. Pass events via submit opts or `appendTimerTelemetry`.
9. **Unload:** `pagehide`/`beforeunload` → `flushAllItemEvents` into payload → `appendTimerTelemetryKeepalive`; **only if** return ≠ `'failed'` may you treat network flush as attempted-success; **always** leave/write open-item marker until clear on confirmed flush. Prefer: on unload **do not** `clearOpenItem` (so remount detects incomplete); normal submit path clears after success.
10. **Display:** countdown `format()`; optional small overtime hint in UI (minimal copy ok).

**Invariant asserts in tests (±10ms):**
```ts
expect(Math.abs(meta.pause_ms - (meta.pause_ms_busy + meta.pause_ms_visibility))).toBeLessThan(10)
expect(meta.overtime_ms! <= meta.thinking_ms + 10).toBe(true)
```

- [ ] **Step 1: Failing Assessment tests** (mock `api`, fake timers, visibility)

```ts
it('does not auto-submit when UI deadline fires', async () => { ... })
it('busy+hidden overlap attributes only to pause_ms_busy', async () => { ... })
it('re-seeds remaining from assessment_started_at', async () => { ... })
it('marks thinking_ms_incomplete after remount with open marker', async () => { ... })
it('submit includes timer_events drained from buffer', async () => { ... })
```

- [ ] **Step 2: Run FAIL**

- [ ] **Step 3: Implement wiring**

- [ ] **Step 4: PASS** — `cd frontend; npm test -- src/pages/Assessment.test.tsx src/hooks/useCountdown.test.ts`

- [ ] **Step 5: Commit**

```bash
git commit -m "feat(frontend): Assessment timer fairness, overtime, flush-all"
```

---

### Task 7: Verification sweep + docs note

**Files:**
- Modify if needed: design spec status already points at this plan
- Run full frontend timer-related tests + backend telemetry tests

- [ ] **Step 1: Run**

```bash
cd frontend
npm test -- src/hooks/useCountdown.test.ts src/lib/timerOpenItem.test.ts src/lib/timerEvents.test.ts src/pages/Assessment.test.tsx src/constants/timing.test.ts
cd ..
pytest tests/test_timer_telemetry.py tests/test_edition_0902_improvements.py -v
```

Expected: all PASS; server timeout tests still 150 min wall-clock.

- [ ] **Step 2: Manual checklist (engineer)**

- Start assessment → countdown ~60:00 (or re-seeded)  
- Toggle tab hidden → freeze; return → resume  
- Submit path busy → freeze; no double-count with hidden  
- Hit 0 → overtime `+…`; still can answer; no forced submit  
- Refresh mid-item → incomplete marker path  
- Hard refresh after 70 wall minutes → overtime UI, still no auto-submit  

- [ ] **Step 3: Commit any test fixes only**

```bash
git commit -m "test: timer fairness acceptance coverage"
```

---

## Spec coverage (self-review)

| Spec requirement | Task |
|------------------|------|
| Scenario B 60 / 150 | T1 |
| Overtime continue, no auto-submit, weight fields | T2, T6 |
| `systemWaitCount` | T6 (L1) |
| Busy-priority exclusive pause | T6 |
| `thinking_ms` / pause splits / `item_meta_version` | T1, T6 |
| sessionStorage incomplete (L2) | T3, T6 |
| `flushAllItemEvents` all exits | T4, T6 |
| Beacon/keepalive unload (L3) | T4, T5, T6 |
| `timer_events` metadata FIFO 200 | T4, T5 |
| Re-seed from `assessment_started_at` | T6 |
| `overtime_ms ⊆ thinking_ms` | T6 tests + Global Constraints |
| `onUiDeadline` ≠ server 150 | T2, T5 unchanged timeout module |
| Server timeout unchanged | T1 comment, T5/T7 regression |

**Placeholder scan:** none intentional.  
**Type consistency:** `onUiDeadline`, `AssessmentItemMeta`, `TimerEvent`, `TIMER_EVENTS_CAP`, `appendTimerTelemetryKeepalive` used uniformly above.
