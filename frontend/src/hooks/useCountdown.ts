import { useCallback, useEffect, useRef, useState } from 'react'

export function useCountdown(
  initialSeconds = 3600,
  options?: {
    enabled?: boolean
    onUiDeadline?: () => void
  },
) {
  const enabled = options?.enabled ?? initialSeconds !== 0
  const [seconds, setSeconds] = useState(initialSeconds)
  const [isPaused, setIsPaused] = useState(false)
  const [isUiDeadlinePassed, setIsUiDeadlinePassed] = useState(false)

  const onUiDeadlineRef = useRef(options?.onUiDeadline)
  onUiDeadlineRef.current = options?.onUiDeadline
  const firedRef = useRef(false)
  const enabledRef = useRef(enabled)
  enabledRef.current = enabled
  const trackedInitialRef = useRef(initialSeconds)

  // Sync seconds when initialSeconds changes during render so effects never
  // see a stale <=0 value after activation (0 → N).
  if (trackedInitialRef.current !== initialSeconds) {
    trackedInitialRef.current = initialSeconds
    setSeconds(initialSeconds)
    firedRef.current = false
    setIsUiDeadlinePassed(false)
  }

  // Tick while enabled and not paused — including overtime (seconds < 0).
  useEffect(() => {
    if (!enabled || isPaused) return undefined
    const timer = window.setInterval(() => {
      setSeconds((prev) => prev - 1)
    }, 1000)
    return () => window.clearInterval(timer)
  }, [enabled, isPaused])

  // Fire onUiDeadline once: crossing into <=0, enable already <=0, or resume at <=0.
  useEffect(() => {
    if (!enabled || isPaused) return
    if (seconds > 0 || firedRef.current) return
    firedRef.current = true
    setIsUiDeadlinePassed(true)
    onUiDeadlineRef.current?.()
  }, [enabled, isPaused, seconds])

  const format = useCallback(() => {
    const abs = Math.abs(seconds)
    const m = Math.floor(abs / 60)
    const s = abs % 60
    const body = `${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`
    return seconds < 0 ? `+${body}` : body
  }, [seconds])

  const pause = useCallback(() => {
    setIsPaused(true)
  }, [])

  const resume = useCallback(() => {
    setIsPaused(false)
  }, [])

  const reset = useCallback(
    (nextSeconds?: number) => {
      if (!enabledRef.current) return
      const target = nextSeconds ?? initialSeconds
      firedRef.current = false
      setIsUiDeadlinePassed(false)
      setSeconds(target)
    },
    [initialSeconds],
  )

  return {
    seconds,
    isPaused,
    isUiDeadlinePassed,
    format,
    pause,
    resume,
    reset,
  }
}
