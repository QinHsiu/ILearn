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

  it('does not fire onUiDeadline when activated from inactive (0 -> N)', () => {
    const onUiDeadline = vi.fn()
    const { rerender } = renderHook(
      ({ seconds }: { seconds: number }) => useCountdown(seconds, { onUiDeadline }),
      { initialProps: { seconds: 0 } },
    )

    act(() => {
      rerender({ seconds: 3600 })
    })

    expect(onUiDeadline).not.toHaveBeenCalled()
  })

  it('fires onUiDeadline exactly once when the countdown reaches zero', () => {
    const onUiDeadline = vi.fn()
    renderHook(() => useCountdown(2, { onUiDeadline }))

    act(() => {
      vi.advanceTimersByTime(2000)
    })

    expect(onUiDeadline).toHaveBeenCalledTimes(1)
  })

  it('never fires while inactive (initialSeconds = 0)', () => {
    const onUiDeadline = vi.fn()
    renderHook(() => useCountdown(0, { onUiDeadline }))

    act(() => {
      vi.advanceTimersByTime(5000)
    })

    expect(onUiDeadline).not.toHaveBeenCalled()
  })

  it('pauses freezing seconds', () => {
    const { result } = renderHook(() => useCountdown(5))

    act(() => {
      result.current.pause()
    })
    act(() => {
      vi.advanceTimersByTime(3000)
    })
    expect(result.current.seconds).toBe(5)
    expect(result.current.isPaused).toBe(true)

    act(() => {
      result.current.resume()
    })
    act(() => {
      vi.advanceTimersByTime(1000)
    })
    expect(result.current.seconds).toBe(4)
    expect(result.current.isPaused).toBe(false)
  })

  it('continues into overtime and formats +MM:SS', () => {
    const { result } = renderHook(() => useCountdown(1))

    act(() => {
      vi.advanceTimersByTime(2000)
    })

    expect(result.current.seconds).toBe(-1)
    expect(result.current.format().startsWith('+')).toBe(true)
    expect(result.current.isUiDeadlinePassed).toBe(true)
  })

  it('onUiDeadline fires once at crossing, not again', () => {
    const onUiDeadline = vi.fn()
    renderHook(() => useCountdown(1, { onUiDeadline }))

    act(() => {
      vi.advanceTimersByTime(1000)
    })
    expect(onUiDeadline).toHaveBeenCalledTimes(1)

    act(() => {
      vi.advanceTimersByTime(5000)
    })
    expect(onUiDeadline).toHaveBeenCalledTimes(1)
  })

  it('does not fire onUiDeadline while paused; fires after resume if already <=0', () => {
    const onUiDeadline = vi.fn()
    const { result } = renderHook(() => useCountdown(1, { onUiDeadline }))
    act(() => result.current.pause())
    act(() => {
      vi.advanceTimersByTime(5000)
    })
    expect(onUiDeadline).not.toHaveBeenCalled()
    act(() => result.current.resume())
    // either immediate if seconds already 0, or after remaining tick
    act(() => {
      vi.advanceTimersByTime(1100)
    })
    expect(onUiDeadline).toHaveBeenCalledTimes(1)
  })

  it('fires once when enabled with initialSeconds already <= 0', () => {
    const onUiDeadline = vi.fn()
    renderHook(() => useCountdown(-30, { enabled: true, onUiDeadline }))
    expect(onUiDeadline).toHaveBeenCalledTimes(1)
  })

  it('inactive when enabled false even if initialSeconds > 0', () => {
    const onUiDeadline = vi.fn()
    const { result } = renderHook(() =>
      useCountdown(60, { enabled: false, onUiDeadline }),
    )

    act(() => {
      vi.advanceTimersByTime(5000)
    })

    expect(result.current.seconds).toBe(60)
    expect(onUiDeadline).not.toHaveBeenCalled()
  })
})
