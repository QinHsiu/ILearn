import { act, renderHook } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { useCountdown } from './useCountdown'

describe('useCountdown', () => {
  beforeEach(() => {
    vi.useFakeTimers()
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it('does not fire onTimeout when activated from inactive (0 -> N)', () => {
    const onTimeout = vi.fn()
    const { rerender } = renderHook(
      ({ seconds }: { seconds: number }) => useCountdown(seconds, onTimeout),
      { initialProps: { seconds: 0 } },
    )

    // Simulate entering the assessment step: initialSeconds goes 0 -> 3600.
    act(() => {
      rerender({ seconds: 3600 })
    })

    expect(onTimeout).not.toHaveBeenCalled()
  })

  it('fires onTimeout exactly once when the countdown reaches zero', () => {
    const onTimeout = vi.fn()
    renderHook(() => useCountdown(2, onTimeout))

    act(() => {
      vi.advanceTimersByTime(2000)
    })

    expect(onTimeout).toHaveBeenCalledTimes(1)
  })

  it('never fires while inactive (initialSeconds = 0)', () => {
    const onTimeout = vi.fn()
    renderHook(() => useCountdown(0, onTimeout))

    act(() => {
      vi.advanceTimersByTime(5000)
    })

    expect(onTimeout).not.toHaveBeenCalled()
  })
})
