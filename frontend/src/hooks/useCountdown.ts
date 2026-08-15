import { useCallback, useEffect, useRef, useState } from 'react'

export function useCountdown(initialSeconds = 3600, onTimeout?: () => void) {
  const active = initialSeconds > 0
  const [seconds, setSeconds] = useState(active ? initialSeconds : 0)
  const [isFinished, setIsFinished] = useState(false)
  const onTimeoutRef = useRef(onTimeout)
  onTimeoutRef.current = onTimeout
  const firedRef = useRef(false)

  useEffect(() => {
    if (!active) {
      setSeconds(0)
      setIsFinished(false)
      firedRef.current = false
      return
    }
    setSeconds(initialSeconds)
    setIsFinished(false)
    firedRef.current = false
  }, [active, initialSeconds])

  useEffect(() => {
    if (!active) return undefined
    if (seconds > 0) {
      const timer = window.setInterval(() => {
        setSeconds((prev) => prev - 1)
      }, 1000)
      return () => window.clearInterval(timer)
    }
    setIsFinished(true)
    if (!firedRef.current) {
      firedRef.current = true
      onTimeoutRef.current?.()
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
    setSeconds(initialSeconds)
    setIsFinished(false)
  }, [active, initialSeconds])

  return { seconds, format, isFinished, reset }
}
