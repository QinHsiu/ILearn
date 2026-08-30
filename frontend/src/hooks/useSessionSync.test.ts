import { describe, expect, it, vi, beforeEach, afterEach } from 'vitest'
import { renderHook, act, waitFor } from '@testing-library/react'
import { useSessionSync } from './useSessionSync'

vi.mock('../api/client', () => ({
  api: {
    getSession: vi.fn(),
    heartbeat: vi.fn(),
  },
}))

import { api } from '../api/client'

describe('useSessionSync', () => {
  beforeEach(() => {
    vi.mocked(api.getSession).mockReset()
    vi.mocked(api.heartbeat).mockReset()
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it('does not call APIs without sessionId', () => {
    renderHook(() =>
      useSessionSync({
        sessionId: null,
        onSync: vi.fn(),
        hasUnsavedChanges: () => false,
      }),
    )
    expect(api.getSession).not.toHaveBeenCalled()
    expect(api.heartbeat).not.toHaveBeenCalled()
  })

  it('refetches session when document becomes visible', async () => {
    const onSync = vi.fn()
    const state = {
      session_id: 's1',
      phase: 'practice',
      loop_count: 0,
      profile: { region: '北京', grade: 5, age: 11 },
    }
    vi.mocked(api.getSession).mockResolvedValue(state as never)
    vi.mocked(api.heartbeat).mockResolvedValue({
      ok: true,
      phase: 'practice',
      server_time: '2026-01-01T00:00:00Z',
    })

    renderHook(() =>
      useSessionSync({
        sessionId: 's1',
        onSync,
        hasUnsavedChanges: () => false,
      }),
    )

    await act(async () => {
      Object.defineProperty(document, 'visibilityState', {
        configurable: true,
        get: () => 'visible',
      })
      document.dispatchEvent(new Event('visibilitychange'))
    })

    await waitFor(() => expect(api.getSession).toHaveBeenCalledWith('s1'))
    await waitFor(() => expect(onSync).toHaveBeenCalled())
  })

  it('marks isSynced false when the 30s heartbeat fails', async () => {
    vi.useFakeTimers()
    vi.mocked(api.heartbeat).mockRejectedValue(new Error('network'))
    vi.mocked(api.getSession).mockResolvedValue({} as never)

    const { result } = renderHook(() =>
      useSessionSync({
        sessionId: 's1',
        onSync: vi.fn(),
        hasUnsavedChanges: () => false,
      }),
    )

    expect(result.current.isSynced).toBe(true)

    await act(async () => {
      await vi.advanceTimersByTimeAsync(30000)
    })

    expect(api.heartbeat).toHaveBeenCalledWith('s1')
    expect(result.current.isSynced).toBe(false)
  })

  it('prevents unload when hasUnsavedChanges is true', () => {
    renderHook(() =>
      useSessionSync({
        sessionId: 's1',
        onSync: vi.fn(),
        hasUnsavedChanges: () => true,
      }),
    )

    const event = new Event('beforeunload', { cancelable: true })
    window.dispatchEvent(event)
    expect(event.defaultPrevented).toBe(true)
  })
})
