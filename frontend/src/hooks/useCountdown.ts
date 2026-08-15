import { useCallback, useEffect, useRef, useState } from 'react'

export function useCountdown(initialSeconds = 3600, onTimeout?: () => void) {
  const active = initialSeconds > 0
  const [seconds, setSeconds] = useState(active ? initialSeconds : 0)
  const [isFinished, setIsFinished] = useState(false)
  const onTimeoutRef = useRef(onTimeout)
  onTimeoutRef.current = onTimeout
  const firedRef = useRef(false)
  // Tracks the previous tick value so we only fire onTimeout on a genuine
  // countdown-to-zero, not on the render where the timer first activates
  // (when `seconds` state still lags at its stale value).
  const prevSecondsRef = useRef(active ? initialSeconds : 0)

  useEffect(() => {
    if (!active) {
      setSeconds(0)
      setIsFinished(false)
      firedRef.current = false
      prevSecondsRef.current = 0
      return
    }
    setSeconds(initialSeconds)
    setIsFinished(false)
    firedRef.current = false
  }, [active, initialSeconds])

  useEffect(() => {
    if (!active) return undefined
    if (seconds > 0) {
      prevSecondsRef.current = seconds
      const timer = window.setInterval(() => {
        setSeconds((prev) => prev - 1)
      }, 1000)
      return () => window.clearInterval(timer)
    }
    // seconds === 0: only a timeout if we actually counted down from a
    // positive value. On activation prevSecondsRef is still 0, so we skip.
    if (prevSecondsRef.current > 0) {
      setIsFinished(true)
      if (!firedRef.current) {
        firedRef.current = true
        onTimeoutRef.current?.()
      }
    }
    return undefined
  }, [active, seconds])

  const format = useCallback(() => {
    const m = Math.floor(Math.max(0, seconds) / 60)
    const s = Math.max(0, seconds) % 60
    return `${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`
  }, [seconds])

  const reset = useCallback(() => {
    if (!active) return
    firedRef.current = false
    prevSecondsRef.current = initialSeconds
    setSeconds(initialSeconds)
    setIsFinished(false)
  }, [active, initialSeconds])

  return { seconds, format, isFinished, reset }
}
