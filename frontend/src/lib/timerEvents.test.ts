import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { TIMER_EVENTS_CAP } from '../constants/timing'
import type { TimerEvent } from '../types/assessmentMeta'
import { appendFifo, preferKeepaliveSend, TimerEventBuffer } from './timerEvents'

function pauseEvent(itemId: string, ts: number): TimerEvent {
  return { type: 'timer_pause', ts, item_id: itemId, reason: 'busy' }
}

describe('appendFifo', () => {
  it('merges arrays within cap', () => {
    expect(appendFifo([1, 2], [3, 4], 10)).toEqual([1, 2, 3, 4])
  })

  it('drops oldest from front when over cap', () => {
    expect(appendFifo([1, 2, 3], [4, 5], 4)).toEqual([2, 3, 4, 5])
  })
})

describe('TimerEventBuffer', () => {
  it('FIFO drops oldest past TIMER_EVENTS_CAP', () => {
    const buf = new TimerEventBuffer()
    for (let i = 0; i < TIMER_EVENTS_CAP + 1; i++) {
      buf.push('q1', pauseEvent('q1', i))
    }
    const all = buf.drainAll()
    expect(all.length).toBeLessThanOrEqual(TIMER_EVENTS_CAP)
    expect(all[0].ts).toBe(1)
    expect(all[all.length - 1].ts).toBe(TIMER_EVENTS_CAP)
  })

  it('drainAll empties all item buffers', () => {
    const buf = new TimerEventBuffer()
    buf.push('q1', pauseEvent('q1', 1))
    buf.push('q2', pauseEvent('q2', 2))
    const drained = buf.drainAll()
    expect(drained).toHaveLength(2)
    expect(buf.drainAll()).toEqual([])
    expect(buf.drain('q1')).toEqual([])
  })

  it('drainAllEntries returns item ids and pushEntries restores', () => {
    const buf = new TimerEventBuffer()
    buf.push('q1', pauseEvent('q1', 1))
    buf.push('q2', pauseEvent('q2', 2))
    const entries = buf.drainAllEntries()
    expect(entries).toEqual([
      { itemId: 'q1', event: pauseEvent('q1', 1) },
      { itemId: 'q2', event: pauseEvent('q2', 2) },
    ])
    expect(buf.drainAll()).toEqual([])
    buf.pushEntries(entries)
    expect(buf.drainAll()).toEqual([pauseEvent('q1', 1), pauseEvent('q2', 2)])
  })
})

describe('preferKeepaliveSend', () => {
  beforeEach(() => {
    vi.stubGlobal('fetch', vi.fn())
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('returns beacon when sendBeacon succeeds', () => {
    const sendBeacon = vi.fn(() => true)
    vi.stubGlobal('navigator', { sendBeacon })

    expect(preferKeepaliveSend('/telemetry', { events: [] })).toBe('beacon')
    expect(sendBeacon).toHaveBeenCalledOnce()
  })

  it('falls back to keepalive fetch when sendBeacon unavailable', () => {
    vi.stubGlobal('navigator', {})
    const mockFetch = vi.mocked(fetch)
    mockFetch.mockResolvedValue({ ok: true } as Response)

    expect(preferKeepaliveSend('/telemetry', { events: [] })).toBe('keepalive')
    expect(mockFetch).toHaveBeenCalledWith(
      '/telemetry',
      expect.objectContaining({ method: 'POST', keepalive: true }),
    )
  })

  it('returns failed when neither transport is available', () => {
    vi.stubGlobal('navigator', {})
    vi.stubGlobal('fetch', undefined)

    expect(preferKeepaliveSend('/telemetry', { events: [] })).toBe('failed')
  })

  it('returns failed when sendBeacon returns false and fetch throws', () => {
    const sendBeacon = vi.fn(() => false)
    vi.stubGlobal('navigator', { sendBeacon })
    vi.stubGlobal('fetch', () => {
      throw new Error('no fetch')
    })

    expect(preferKeepaliveSend('/telemetry', { events: [] })).toBe('failed')
  })
})
