import { useCallback, useEffect, useRef, useState } from 'react'
import { api } from '../api/client'
import type { SessionState } from '../api/client'

const HEARTBEAT_MS = 30_000

export type UseSessionSyncOptions = {
  sessionId: string | null
  onSync: (state: SessionState) => void
  hasUnsavedChanges: () => boolean
}

export type UseSessionSyncResult = {
  isSynced: boolean
  lastSync: number
  forceSync: () => Promise<boolean>
}

export function useSessionSync({
  sessionId,
  onSync,
  hasUnsavedChanges,
}: UseSessionSyncOptions): UseSessionSyncResult {
  const [isSynced, setIsSynced] = useState(true)
  const [lastSync, setLastSync] = useState(0)
  const onSyncRef = useRef(onSync)
  onSyncRef.current = onSync
  const hasUnsavedRef = useRef(hasUnsavedChanges)
  hasUnsavedRef.current = hasUnsavedChanges

  const forceSync = useCallback(async () => {
    if (!sessionId) return false
    try {
      const state = await api.getSession(sessionId)
      onSyncRef.current(state)
      setIsSynced(true)
      setLastSync(Date.now())
      return true
    } catch {
      setIsSynced(false)
      return false
    }
  }, [sessionId])

  useEffect(() => {
    if (!sessionId) return undefined

    const onVisibility = () => {
      if (document.visibilityState !== 'visible') return
      void api
        .getSession(sessionId)
        .then((state) => {
          onSyncRef.current(state)
          setIsSynced(true)
          setLastSync(Date.now())
        })
        .catch(() => {
          setIsSynced(false)
        })
    }

    const onBeforeUnload = (event: BeforeUnloadEvent) => {
      if (!hasUnsavedRef.current()) return
      event.preventDefault()
      event.returnValue = ''
    }

    document.addEventListener('visibilitychange', onVisibility)
    window.addEventListener('beforeunload', onBeforeUnload)
    const intervalId = window.setInterval(() => {
      void api
        .heartbeat(sessionId)
        .then(() => {
          setIsSynced(true)
          setLastSync(Date.now())
        })
        .catch(() => {
          setIsSynced(false)
        })
    }, HEARTBEAT_MS)

    return () => {
      document.removeEventListener('visibilitychange', onVisibility)
      window.removeEventListener('beforeunload', onBeforeUnload)
      window.clearInterval(intervalId)
    }
  }, [sessionId])

  return { isSynced, lastSync, forceSync }
}
