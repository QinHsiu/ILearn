import { TIMER_OPEN_ITEM_KEY_PREFIX } from '../constants/timing'

export type OpenItemMarker = { item_id: string; started_at: number; flushed: boolean }

export function openItemStorageKey(sessionId: string): string {
  return `${TIMER_OPEN_ITEM_KEY_PREFIX}${sessionId}`
}

function getStorage(): Storage | null {
  if (typeof sessionStorage === 'undefined') return null
  return sessionStorage
}

export function writeOpenItem(sessionId: string, itemId: string, now?: number): void {
  const storage = getStorage()
  if (!storage) return
  const marker: OpenItemMarker = {
    item_id: itemId,
    started_at: now ?? Date.now(),
    flushed: false,
  }
  storage.setItem(openItemStorageKey(sessionId), JSON.stringify(marker))
}

export function clearOpenItem(sessionId: string): void {
  const storage = getStorage()
  if (!storage) return
  storage.removeItem(openItemStorageKey(sessionId))
}

export function readOpenItem(sessionId: string): OpenItemMarker | null {
  const storage = getStorage()
  if (!storage) return null
  const raw = storage.getItem(openItemStorageKey(sessionId))
  if (!raw) return null
  try {
    return JSON.parse(raw) as OpenItemMarker
  } catch {
    return null
  }
}

export function consumeIncompleteOpenItem(sessionId: string): string | null {
  const marker = readOpenItem(sessionId)
  if (!marker || marker.flushed) return null
  clearOpenItem(sessionId)
  return marker.item_id
}
