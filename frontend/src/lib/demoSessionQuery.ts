export function readDemoSessionId(search: string): string | null {
  const raw = new URLSearchParams(search.startsWith('?') ? search : `?${search}`).get('session_id')
  const id = (raw || '').trim()
  return id || null
}
