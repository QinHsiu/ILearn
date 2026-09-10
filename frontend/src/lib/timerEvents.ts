import { TIMER_EVENTS_CAP } from '../constants/timing'
import type { TimerEvent } from '../types/assessmentMeta'

export function appendFifo<T>(existing: T[], next: T[], cap: number): T[] {
  const merged = [...existing, ...next]
  while (merged.length > cap) {
    merged.shift()
  }
  return merged
}

type BufferedEntry = { itemId: string; event: TimerEvent }

export class TimerEventBuffer {
  private ordered: BufferedEntry[] = []

  push(itemId: string, event: TimerEvent): void {
    this.ordered.push({ itemId, event })
    while (this.ordered.length > TIMER_EVENTS_CAP) {
      this.ordered.shift()
    }
  }

  drain(itemId: string): TimerEvent[] {
    const drained: TimerEvent[] = []
    this.ordered = this.ordered.filter((entry) => {
      if (entry.itemId === itemId) {
        drained.push(entry.event)
        return false
      }
      return true
    })
    return drained
  }

  drainAll(): TimerEvent[] {
    const all = this.ordered.map((entry) => entry.event)
    this.ordered = []
    return all
  }
}

export function preferKeepaliveSend(
  url: string,
  body: object,
  headers?: Record<string, string>,
): 'beacon' | 'keepalive' | 'failed' {
  const json = JSON.stringify(body)
  const contentType = headers?.['Content-Type'] ?? 'application/json'

  if (typeof navigator !== 'undefined' && typeof navigator.sendBeacon === 'function') {
    const blob = new Blob([json], { type: contentType })
    if (navigator.sendBeacon(url, blob)) {
      return 'beacon'
    }
  }

  if (typeof fetch === 'function') {
    try {
      void fetch(url, {
        method: 'POST',
        body: json,
        headers: { 'Content-Type': contentType, ...headers },
        keepalive: true,
      })
      return 'keepalive'
    } catch {
      return 'failed'
    }
  }

  return 'failed'
}
