import { useCallback, useEffect, useRef, useState } from 'react'
import {
  api,
  fileToImageAnswer,
  type AdaptiveAssessmentResponse,
  type AssessmentItem,
  type AssessmentPaper,
  type ImageAnswer,
  type StudentProfile,
} from '../api/client'
import { useResponsive } from '../hooks/useResponsive'
import { useCountdown } from '../hooks/useCountdown'
import ProgressDots from '../components/ProgressDots'
import DynamicGeometryQuestion from '../components/DynamicGeometryQuestion'
import FocusedHintLayout from '../components/FocusedHintLayout'
import SocraticPanel from '../components/SocraticPanel'
import MathVisualizer from '../components/MathVisualizer'
import CountingManipulative from '../components/CountingManipulative'
import { inferVisualization } from '../lib/inferVisualization'
import { inferCountingManipulative } from '../lib/inferManipulative'
import { ASSESSMENT_SECONDS, MAX_VISIBILITY_PAUSE_MS } from '../constants/timing'
import type { AssessmentItemMeta } from '../types/assessmentMeta'
import { TimerEventBuffer, type TimerBufferedEntry } from '../lib/timerEvents'
import {
  clearOpenItem,
  consumeIncompleteOpenItem,
  writeOpenItem,
} from '../lib/timerOpenItem'

export { ASSESSMENT_SECONDS }
export type { AssessmentItemMeta }

export type AssessmentCompletePayload = {
  paper: AssessmentPaper
  answers: Record<string, string>
  images: ImageAnswer[]
  itemMeta: Record<string, AssessmentItemMeta>
}

type AssessmentProps = {
  sessionId: string
  profile: StudentProfile
  onComplete: (payload: AssessmentCompletePayload) => void | Promise<void>
  onError?: (message: string) => void
  onBack?: () => void
}

type ImageUpload = ImageAnswer & { preview: string; name: string }

type ItemAccumulator = {
  elapsed_ms: number
  thinking_ms: number
  overtime_ms: number
  pause_ms_busy: number
  pause_ms_visibility: number
  pause_count: number
}

function emptyAccumulator(): ItemAccumulator {
  return {
    elapsed_ms: 0,
    thinking_ms: 0,
    overtime_ms: 0,
    pause_ms_busy: 0,
    pause_ms_visibility: 0,
    pause_count: 0,
  }
}

function gradeLocal(item: AssessmentItem, answer: string): boolean {
  const key = (item.answer_key || '').trim()
  if (!key) return false
  return answer.trim() === key
}

function firstMultimodalSourceLabel(items: AssessmentItem[]): string | null {
  for (const item of items) {
    if (item.is_multimodal || (item.image_paths?.length ?? 0) > 0) {
      const label = item.source_refs?.[0]?.source_label
      if (label) return label
    }
  }
  return null
}

function buildMetaLine(res: AdaptiveAssessmentResponse): string {
  const bits = [
    res.multimodal_count && res.multimodal_count > 0
      ? `多模态 ${res.multimodal_count} 题`
      : '',
    res.layer2_used ? `二层补题：${res.layer2_source}` : '',
    res.is_anchor ? `锚点 ${res.delivered}/${res.requested}` : '',
    !res.is_anchor && res.paper ? `完整测评 ${res.paper.items.length} 题` : '',
    !res.is_anchor && res.diagnosis ? '已根据锚点调整知识点' : '',
  ].filter(Boolean)
  return bits.join(' · ')
}

function formatElapsed(ms: number): string {
  const total = Math.max(0, Math.round(ms / 1000))
  const m = Math.floor(total / 60)
  const s = total % 60
  return `${m}:${String(s).padStart(2, '0')}`
}

function renderCountingManipulative(stem: string) {
  const spec = inferCountingManipulative(stem)
  if (!spec) return null
  return <CountingManipulative spec={spec} />
}

export default function Assessment({
  sessionId,
  profile,
  onComplete,
  onError,
  onBack,
}: AssessmentProps) {
  const breakpoint = useResponsive()
  const [phase, setPhase] = useState<'loading' | 'anchor' | 'full'>('loading')
  const [busy, setBusy] = useState(false)
  const [paper, setPaper] = useState<AssessmentPaper | null>(null)
  const [answers, setAnswers] = useState<Record<string, string>>({})
  const [currentIndex, setCurrentIndex] = useState(0)
  const [meta, setMeta] = useState<string>('')
  const [inferredChapter, setInferredChapter] = useState<string | null>(null)
  const [sourceLabel, setSourceLabel] = useState<string | null>(null)
  const [imageUploads, setImageUploads] = useState<Record<string, ImageUpload>>({})
  const [focusItemId, setFocusItemId] = useState<string | null>(null)
  const [, setHintUsed] = useState<Record<string, boolean>>({})
  const [elapsedMs, setElapsedMs] = useState<Record<string, number>>({})
  const [seedSeconds, setSeedSeconds] = useState(ASSESSMENT_SECONDS)

  const onErrorRef = useRef(onError)
  onErrorRef.current = onError
  const submitFullRef = useRef<() => void>(() => {})
  const currentItemIdRef = useRef<string | null>(null)
  const hintUsedRef = useRef<Record<string, boolean>>({})
  const accumulatorsRef = useRef<Record<string, ItemAccumulator>>({})
  const timerBufferRef = useRef(new TimerEventBuffer())
  const systemWaitCountRef = useRef(0)
  const visibilityHiddenRef = useRef(false)
  const visibilityPauseUsedRef = useRef(0)
  const uiDeadlineCrossedRef = useRef(false)
  const uiDeadlineHandledRef = useRef(false)
  const incompleteItemIdsRef = useRef<Set<string>>(new Set())
  const lastTickAtRef = useRef(Date.now())
  const pauseSegmentRef = useRef<{
    reason: 'busy' | 'visibility'
    startedAt: number
  } | null>(null)
  const countdownPauseRef = useRef<(pause: boolean) => void>(() => {})
  const isUiDeadlinePassedRef = useRef(false)
  const phaseRef = useRef(phase)
  phaseRef.current = phase
  const sessionIdRef = useRef(sessionId)
  sessionIdRef.current = sessionId
  const flushedUnloadRef = useRef(false)
  /** Wall re-seed once per session entry; remount/refresh may re-seed. Not phase/paper. */
  const wallSeededSessionRef = useRef<string | null>(null)

  const countdownActive = phase === 'anchor' || phase === 'full'

  const handleUiDeadline = useCallback(() => {
    if (uiDeadlineHandledRef.current) return
    uiDeadlineHandledRef.current = true
    uiDeadlineCrossedRef.current = true
    timerBufferRef.current.push(currentItemIdRef.current || '_session', {
      type: 'ui_deadline',
      ts: Date.now(),
    })
  }, [])

  const {
    format: formatCountdown,
    pause: pauseCountdown,
    resume: resumeCountdown,
    reset: resetCountdown,
    isUiDeadlinePassed,
  } = useCountdown(countdownActive ? seedSeconds : 0, {
    enabled: countdownActive,
    onUiDeadline: handleUiDeadline,
  })

  const resetCountdownRef = useRef(resetCountdown)
  resetCountdownRef.current = resetCountdown

  isUiDeadlinePassedRef.current = isUiDeadlinePassed || uiDeadlineCrossedRef.current

  const ensureAccumulator = useCallback((itemId: string): ItemAccumulator => {
    if (!accumulatorsRef.current[itemId]) {
      accumulatorsRef.current[itemId] = emptyAccumulator()
    }
    return accumulatorsRef.current[itemId]
  }, [])

  const computeShouldPause = useCallback(() => {
    const systemWait = systemWaitCountRef.current > 0
    const budgetLeft = visibilityPauseUsedRef.current < MAX_VISIBILITY_PAUSE_MS
    return systemWait || (visibilityHiddenRef.current && budgetLeft)
  }, [])

  const syncCountdownPause = useCallback(() => {
    const should = computeShouldPause()
    countdownPauseRef.current(should)
  }, [computeShouldPause])

  useEffect(() => {
    countdownPauseRef.current = (shouldPause: boolean) => {
      if (shouldPause) pauseCountdown()
      else resumeCountdown()
    }
  }, [pauseCountdown, resumeCountdown])

  const closePauseSegment = useCallback(
    (now: number) => {
      const segment = pauseSegmentRef.current
      const itemId = currentItemIdRef.current
      if (!segment || !itemId) {
        pauseSegmentRef.current = null
        return
      }
      const duration = Math.max(0, now - segment.startedAt)
      timerBufferRef.current.push(itemId, {
        type: 'timer_resume',
        ts: now,
        item_id: itemId,
        pause_duration_ms: duration,
      })
      pauseSegmentRef.current = null
    },
    [],
  )

  const openPauseSegment = useCallback(
    (reason: 'busy' | 'visibility', now: number) => {
      const itemId = currentItemIdRef.current
      if (!itemId) return
      const existing = pauseSegmentRef.current
      if (existing?.reason === reason) return
      if (existing) closePauseSegment(now)
      const acc = ensureAccumulator(itemId)
      acc.pause_count += 1
      pauseSegmentRef.current = { reason, startedAt: now }
      timerBufferRef.current.push(itemId, {
        type: 'timer_pause',
        ts: now,
        item_id: itemId,
        reason,
      })
    },
    [closePauseSegment, ensureAccumulator],
  )

  const tickAccumulators = useCallback(
    (now = Date.now()) => {
      const itemId = currentItemIdRef.current
      const active = phaseRef.current === 'anchor' || phaseRef.current === 'full'
      if (!itemId || !active) {
        lastTickAtRef.current = now
        return
      }
      let dt = now - lastTickAtRef.current
      lastTickAtRef.current = now
      if (dt <= 0) return
      // Cap a single slice to avoid huge jumps after long sleeps / fake-timer quirks
      if (dt > 60_000) dt = 60_000

      const acc = ensureAccumulator(itemId)
      acc.elapsed_ms += dt

      const systemWait = systemWaitCountRef.current > 0
      const hidden = visibilityHiddenRef.current
      const budgetLeft = visibilityPauseUsedRef.current < MAX_VISIBILITY_PAUSE_MS
      const shouldPause = systemWait || (hidden && budgetLeft)

      if (shouldPause) {
        if (systemWait) {
          openPauseSegment('busy', now)
          acc.pause_ms_busy += dt
        } else {
          openPauseSegment('visibility', now)
          const room = MAX_VISIBILITY_PAUSE_MS - visibilityPauseUsedRef.current
          const credited = Math.min(dt, Math.max(0, room))
          acc.pause_ms_visibility += credited
          visibilityPauseUsedRef.current += credited
          if (
            credited > 0 &&
            visibilityPauseUsedRef.current >= MAX_VISIBILITY_PAUSE_MS
          ) {
            timerBufferRef.current.push(itemId, {
              type: 'timer_pause_cap',
              ts: now,
              item_id: itemId,
              cap_ms: MAX_VISIBILITY_PAUSE_MS,
            })
          }
          if (dt > credited) {
            const thinkingDt = dt - credited
            acc.thinking_ms += thinkingDt
            if (isUiDeadlinePassedRef.current) {
              acc.overtime_ms += thinkingDt
            }
            closePauseSegment(now)
            syncCountdownPause()
          }
        }
      } else {
        if (pauseSegmentRef.current) closePauseSegment(now)
        acc.thinking_ms += dt
        if (isUiDeadlinePassedRef.current) {
          acc.overtime_ms += dt
        }
      }

      setElapsedMs((prev) => {
        const nextVal = acc.elapsed_ms
        if (prev[itemId] === nextVal) return prev
        return { ...prev, [itemId]: nextVal }
      })
    },
    [closePauseSegment, ensureAccumulator, openPauseSegment, syncCountdownPause],
  )

  const acquireSystemWait = useCallback(() => {
    tickAccumulators()
    systemWaitCountRef.current += 1
    syncCountdownPause()
    tickAccumulators()
  }, [syncCountdownPause, tickAccumulators])

  const releaseSystemWait = useCallback(() => {
    tickAccumulators()
    systemWaitCountRef.current = Math.max(0, systemWaitCountRef.current - 1)
    syncCountdownPause()
    tickAccumulators()
  }, [syncCountdownPause, tickAccumulators])

  const pushItemTimeFlush = useCallback(
    (itemId: string, opts?: { incomplete?: boolean }) => {
      const acc = ensureAccumulator(itemId)
      const pauseMs = acc.pause_ms_busy + acc.pause_ms_visibility
      timerBufferRef.current.push(itemId, {
        type: 'item_time_flush',
        ts: Date.now(),
        item_id: itemId,
        thinking_ms: acc.thinking_ms,
        pause_ms: pauseMs,
        incomplete: opts?.incomplete,
      })
    },
    [ensureAccumulator],
  )

  const flushAllItemEvents = useCallback(
    (opts?: { incomplete?: boolean }): TimerBufferedEntry[] => {
      tickAccumulators()
      const itemId = currentItemIdRef.current
      if (itemId) {
        pushItemTimeFlush(itemId, opts)
      }
      return timerBufferRef.current.drainAllEntries()
    },
    [pushItemTimeFlush, tickAccumulators],
  )

  const restoreBufferedEntries = useCallback((entries: TimerBufferedEntry[]) => {
    timerBufferRef.current.pushEntries(entries)
  }, [])

  const buildItemMeta = useCallback(
    (items: AssessmentItem[]): Record<string, AssessmentItemMeta> => {
      tickAccumulators()
      const metaMap: Record<string, AssessmentItemMeta> = {}
      for (const item of items) {
        const acc = accumulatorsRef.current[item.id] || emptyAccumulator()
        const pauseMs = acc.pause_ms_busy + acc.pause_ms_visibility
        const incomplete = incompleteItemIdsRef.current.has(item.id)
        metaMap[item.id] = {
          item_meta_version: 'v1',
          elapsed_ms: acc.elapsed_ms,
          thinking_ms: acc.thinking_ms,
          overtime_ms: acc.overtime_ms || undefined,
          ui_deadline_crossed: uiDeadlineCrossedRef.current || undefined,
          thinking_ms_incomplete: incomplete || undefined,
          hint_used: Boolean(hintUsedRef.current[item.id]),
          ...(acc.pause_count > 0 || pauseMs > 0
            ? {
                pause_count: acc.pause_count,
                pause_ms: pauseMs,
                pause_ms_busy: acc.pause_ms_busy,
                pause_ms_visibility: acc.pause_ms_visibility,
              }
            : {}),
        }
      }
      return metaMap
    },
    [tickAccumulators],
  )

  const selectItem = useCallback(
    (index: number) => {
      tickAccumulators()
      if (pauseSegmentRef.current) closePauseSegment(Date.now())
      const leavingId = currentItemIdRef.current
      const nextId = paper?.items[index]?.id ?? null
      if (leavingId && leavingId !== nextId) {
        pushItemTimeFlush(leavingId)
      }
      setCurrentIndex(index)
      currentItemIdRef.current = nextId
      lastTickAtRef.current = Date.now()
      if (nextId) {
        writeOpenItem(sessionId, nextId)
        ensureAccumulator(nextId)
      }
    },
    [
      closePauseSegment,
      ensureAccumulator,
      paper,
      pushItemTimeFlush,
      sessionId,
      tickAccumulators,
    ],
  )

  // Mount: detect incomplete open item from prior session
  useEffect(() => {
    const incompleteId = consumeIncompleteOpenItem(sessionId)
    if (incompleteId) {
      incompleteItemIdsRef.current.add(incompleteId)
      timerBufferRef.current.push(incompleteId, {
        type: 'timer_refresh',
        ts: Date.now(),
        item_id: incompleteId,
      })
    }
  }, [sessionId])

  // Accumulator ticker
  useEffect(() => {
    if (!countdownActive) return undefined
    lastTickAtRef.current = Date.now()
    const id = window.setInterval(() => {
      tickAccumulators()
      syncCountdownPause()
    }, 250)
    return () => window.clearInterval(id)
  }, [countdownActive, syncCountdownPause, tickAccumulators])

  // Visibility pause + budget
  useEffect(() => {
    if (!countdownActive) return undefined

    const onVisibility = () => {
      tickAccumulators()
      visibilityHiddenRef.current = document.visibilityState === 'hidden'
      syncCountdownPause()
      tickAccumulators()
    }
    visibilityHiddenRef.current = document.visibilityState === 'hidden'
    syncCountdownPause()
    document.addEventListener('visibilitychange', onVisibility)
    return () => document.removeEventListener('visibilitychange', onVisibility)
  }, [countdownActive, syncCountdownPause, tickAccumulators])

  // Unload flush (do not clearOpenItem; latch only after keepalive ≠ failed)
  useEffect(() => {
    if (!countdownActive) return undefined

    const onUnload = () => {
      if (flushedUnloadRef.current) return
      const itemId = currentItemIdRef.current
      if (itemId) writeOpenItem(sessionIdRef.current, itemId)
      const entries = flushAllItemEvents({ incomplete: true })
      if (!entries.length) {
        flushedUnloadRef.current = true
        return
      }
      const result = api.appendTimerTelemetryKeepalive(sessionIdRef.current, {
        timer_events: entries.map((entry) => entry.event),
        item_meta_patch: itemId
          ? {
              [itemId]: {
                thinking_ms_incomplete: true,
                ...(accumulatorsRef.current[itemId]
                  ? {
                      elapsed_ms: accumulatorsRef.current[itemId].elapsed_ms,
                      thinking_ms: accumulatorsRef.current[itemId].thinking_ms,
                      overtime_ms: accumulatorsRef.current[itemId].overtime_ms,
                      pause_ms_busy: accumulatorsRef.current[itemId].pause_ms_busy,
                      pause_ms_visibility:
                        accumulatorsRef.current[itemId].pause_ms_visibility,
                    }
                  : {}),
              },
            }
          : undefined,
      })
      if (result === 'failed') {
        restoreBufferedEntries(entries)
        return
      }
      flushedUnloadRef.current = true
    }

    window.addEventListener('pagehide', onUnload)
    window.addEventListener('beforeunload', onUnload)
    return () => {
      window.removeEventListener('pagehide', onUnload)
      window.removeEventListener('beforeunload', onUnload)
      // Component unmount: best-effort flush; keep open marker
      if (!flushedUnloadRef.current) {
        onUnload()
      }
    }
  }, [countdownActive, flushAllItemEvents, restoreBufferedEntries])

  // Adaptive start
  useEffect(() => {
    let cancelled = false
    async function start() {
      setBusy(true)
      acquireSystemWait()
      try {
        const res = await api.adaptiveStart(sessionId)
        if (cancelled) return
        setPaper(res.paper)
        setAnswers({})
        setImageUploads({})
        setFocusItemId(null)
        setHintUsed({})
        setElapsedMs({})
        accumulatorsRef.current = {}
        hintUsedRef.current = {}
        setCurrentIndex(0)
        const firstId = res.paper.items[0]?.id ?? null
        currentItemIdRef.current = firstId
        lastTickAtRef.current = Date.now()
        if (firstId) {
          ensureAccumulator(firstId)
          writeOpenItem(sessionId, firstId)
        }
        setPhase('anchor')
        setInferredChapter(res.inferred_chapter ?? null)
        setSourceLabel(firstMultimodalSourceLabel(res.paper.items))
        setMeta(buildMetaLine(res))
      } catch (err) {
        onErrorRef.current?.(err instanceof Error ? err.message : String(err))
      } finally {
        releaseSystemWait()
        if (!cancelled) setBusy(false)
      }
    }
    void start()
    return () => {
      cancelled = true
    }
  }, [sessionId, acquireSystemWait, releaseSystemWait, ensureAccumulator])

  // Wall-seed countdown from assessment_started_at once per session entry.
  // Remount/refresh may re-seed. Do NOT re-run on phase / paper length (anchor→full
  // would claw back pause credit by subtracting full wall elapsed).
  useEffect(() => {
    if (!countdownActive) return undefined
    if (wallSeededSessionRef.current === sessionId) return undefined
    let cancelled = false
    async function reseed() {
      try {
        const session = await api.getSession(sessionId)
        if (cancelled) return
        const startedAt = session.metadata?.assessment_started_at
        const elapsedServerSec = startedAt
          ? (Date.now() - Date.parse(String(startedAt))) / 1000
          : 0
        const remainingSec = ASSESSMENT_SECONDS - elapsedServerSec
        if (remainingSec <= 0) {
          uiDeadlineCrossedRef.current = true
          // Emit once before gating; reset() clears useCountdown firedRef and would re-fire
          if (!uiDeadlineHandledRef.current) {
            uiDeadlineHandledRef.current = true
            timerBufferRef.current.push(currentItemIdRef.current || '_session', {
              type: 'ui_deadline',
              ts: Date.now(),
            })
          }
        }
        wallSeededSessionRef.current = sessionId
        setSeedSeconds(remainingSec)
        resetCountdownRef.current(remainingSec)
      } catch {
        // Keep local seed on failure — leave wallSeededSessionRef unset so a later
        // countdownActive/sessionId effect can retry.
      }
    }
    void reseed()
    return () => {
      cancelled = true
    }
  }, [countdownActive, sessionId])

  useEffect(() => {
    return () => {
      Object.values(imageUploads).forEach((row) => {
        if (row.preview) URL.revokeObjectURL(row.preview)
      })
    }
  }, [imageUploads])

  async function onPickImage(itemId: string, file: File | undefined) {
    if (!file) return
    acquireSystemWait()
    setBusy(true)
    try {
      const payload = await fileToImageAnswer(itemId, file)
      const preview = URL.createObjectURL(file)
      setImageUploads((prev) => {
        const old = prev[itemId]
        if (old?.preview) URL.revokeObjectURL(old.preview)
        return { ...prev, [itemId]: { ...payload, preview, name: file.name } }
      })
    } catch (err) {
      onErrorRef.current?.(err instanceof Error ? err.message : String(err))
    } finally {
      releaseSystemWait()
      setBusy(false)
    }
  }

  function onClearImage(itemId: string) {
    setImageUploads((prev) => {
      const next = { ...prev }
      if (next[itemId]?.preview) URL.revokeObjectURL(next[itemId].preview)
      delete next[itemId]
      return next
    })
  }

  async function submitAnchor() {
    if (!paper) return
    setBusy(true)
    acquireSystemWait()
    const entries = flushAllItemEvents()
    const events = entries.map((entry) => entry.event)
    let telemetryCommitted = false
    try {
      // appendTimerTelemetry is the authoritative V1 path for timer_events.
      // Do not also pass the same events through api.submit / onComplete (avoids
      // double FIFO merge on the server).
      if (events.length) {
        await api.appendTimerTelemetry(sessionId, { timer_events: events })
      }
      telemetryCommitted = true
      const anchorResults = paper.items.map((item) => ({
        item_id: item.id,
        knowledge_ids: item.knowledge_ids || [],
        is_correct: gradeLocal(item, answers[item.id] || ''),
      }))
      const res = await api.adaptiveContinue(sessionId, anchorResults)
      clearOpenItem(sessionId)
      setPaper(res.paper)
      setAnswers({})
      setImageUploads({})
      setFocusItemId(null)
      setHintUsed({})
      setElapsedMs({})
      accumulatorsRef.current = {}
      hintUsedRef.current = {}
      timerBufferRef.current = new TimerEventBuffer()
      setCurrentIndex(0)
      const firstId = res.paper.items[0]?.id ?? null
      currentItemIdRef.current = firstId
      lastTickAtRef.current = Date.now()
      pauseSegmentRef.current = null
      if (firstId) {
        ensureAccumulator(firstId)
        writeOpenItem(sessionId, firstId)
      }
      setPhase('full')
      setInferredChapter(res.inferred_chapter ?? null)
      setSourceLabel(firstMultimodalSourceLabel(res.paper.items))
      setMeta(buildMetaLine(res))
    } catch (err) {
      if (!telemetryCommitted) restoreBufferedEntries(entries)
      onErrorRef.current?.(err instanceof Error ? err.message : String(err))
    } finally {
      releaseSystemWait()
      setBusy(false)
    }
  }

  async function submitFull() {
    if (!paper) return
    setBusy(true)
    acquireSystemWait()
    const itemMeta = buildItemMeta(paper.items)
    const entries = flushAllItemEvents()
    const events = entries.map((entry) => entry.event)
    let telemetryCommitted = false
    try {
      // appendTimerTelemetry is the authoritative V1 path for timer_events.
      // Omit from onComplete so App does not re-submit the same FIFO batch.
      if (events.length) {
        await api.appendTimerTelemetry(sessionId, { timer_events: events })
      }
      telemetryCommitted = true
      const images = Object.values(imageUploads).map(
        ({ item_id, image_base64, mime_type }) => ({
          item_id,
          image_base64,
          mime_type,
        }),
      )
      await onComplete({ paper, answers, images, itemMeta })
      clearOpenItem(sessionId)
      flushedUnloadRef.current = true
    } catch (err) {
      if (!telemetryCommitted) restoreBufferedEntries(entries)
      onErrorRef.current?.(err instanceof Error ? err.message : String(err))
    } finally {
      releaseSystemWait()
      setBusy(false)
    }
  }

  submitFullRef.current = () => {
    if (phase === 'anchor') void submitAnchor()
    else if (phase === 'full') void submitFull()
  }

  function renderAnswerControls(item: AssessmentItem) {
    return (
      <>
        {item.geo_config?.correct_answer ? (
          <DynamicGeometryQuestion
            question={{
              id: item.id,
              type: item.geo_config.type || 'drag_point',
              config: item.geo_config.config,
              correct_answer: item.geo_config.correct_answer,
            }}
            onInteraction={(log) => {
              setAnswers((prev) => ({
                ...prev,
                [item.id]: `${log.position[0].toFixed(2)},${log.position[1].toFixed(2)}`,
              }))
            }}
          />
        ) : null}
        {item.geo_config?.correct_answer ? null : item.choices?.length ? (
          <div className="choices">
            {item.choices.map((choice) => (
              <label
                className={`choice-row${(answers[item.id] || '') === choice ? ' is-selected' : ''}`}
                key={choice}
              >
                <input
                  type="radio"
                  name={item.id}
                  checked={(answers[item.id] || '') === choice}
                  onChange={() =>
                    setAnswers((prev) => ({ ...prev, [item.id]: choice }))
                  }
                />
                <span>{choice}</span>
              </label>
            ))}
          </div>
        ) : (
          <textarea
            className="answer-input"
            value={answers[item.id] || ''}
            onChange={(e) =>
              setAnswers((prev) => ({ ...prev, [item.id]: e.target.value }))
            }
            rows={3}
            placeholder="输入你的答案"
          />
        )}
        <div className="field upload-field">
          <label htmlFor={`img-${item.id}`}>手写作答照片（可选）</label>
          <input
            id={`img-${item.id}`}
            type="file"
            accept="image/png,image/jpeg,image/webp,.png,.jpg,.jpeg,.webp"
            disabled={busy}
            onChange={(e) => {
              const file = e.target.files?.[0]
              void onPickImage(item.id, file)
              e.target.value = ''
            }}
          />
          {imageUploads[item.id] ? (
            <div className="upload-preview">
              <div className="upload-frame">
                <img
                  src={imageUploads[item.id].preview}
                  alt={`${item.id} 手写作答预览`}
                />
              </div>
              <div className="upload-meta">
                <span className="upload-name">{imageUploads[item.id].name}</span>
                <button
                  className="btn secondary"
                  type="button"
                  disabled={busy}
                  onClick={() => onClearImage(item.id)}
                >
                  移除
                </button>
              </div>
            </div>
          ) : (
            <span className="upload-hint">支持 PNG / JPG / WebP，将随提交送去 OCR 批改</span>
          )}
        </div>
        <div className="actions assess-item-actions">
          <button
            className="btn secondary"
            type="button"
            disabled={busy}
            onClick={() => {
              setHintUsed((prev) => {
                const next = { ...prev, [item.id]: true }
                hintUsedRef.current = next
                return next
              })
              setFocusItemId(item.id)
            }}
          >
            求助苏格拉底
          </button>
          {(elapsedMs[item.id] || 0) > 0 ? (
            <span className="item-elapsed">本题已用时 {formatElapsed(elapsedMs[item.id] || 0)}</span>
          ) : null}
        </div>
      </>
    )
  }

  if (phase === 'loading' || !paper) {
    return (
      <section
        className={`panel student-panel assessment-layout assessment-layout--${breakpoint}`}
      >
        <p className="assess-phase">测评</p>
        <h2>自适应测评</h2>
        <p className="lede">{busy ? '正在生成锚点卷…' : '准备中…'}</p>
        {onBack ? (
          <div className="actions assess-actions">
            <button className="btn secondary" type="button" onClick={onBack} disabled={busy}>
              返回建档
            </button>
          </div>
        ) : null}
      </section>
    )
  }

  const layoutClass = `panel student-panel assessment-layout assessment-layout--${breakpoint} assessment-container ${
    breakpoint === 'mobile' ? 'single-column' : 'two-column'
  }`
  const counterCurrent = String(currentIndex + 1).padStart(2, '0')
  const counterTotal = String(paper.items.length).padStart(2, '0')
  const focusItem =
    focusItemId != null
      ? paper.items.find((item) => item.id === focusItemId) || null
      : null
  const overtimeHint = isUiDeadlinePassed || uiDeadlineCrossedRef.current

  if (focusItem) {
    const visual = inferVisualization(focusItem.stem)
    return (
      <section className={layoutClass}>
        <div className="assess-head">
          <div className="assess-head-main">
            <p className="assess-phase">专注辅导</p>
            <h2>苏格拉底助教</h2>
          </div>
          <div className="countdown" aria-live="polite">
            剩余 {formatCountdown()}
            {overtimeHint ? <span className="countdown-overtime"> · 已超时</span> : null}
          </div>
        </div>
        <FocusedHintLayout
          onExit={() => setFocusItemId(null)}
          questionSlot={
            <>
              <p className="item-meta">
                <span>{focusItem.difficulty}</span>
                <span>{focusItem.type}</span>
              </p>
              {focusItem.image_paths?.length ? (
                <div className="item-images">
                  {focusItem.image_paths.map((path, imgIndex) => (
                    <img
                      key={`${focusItem.id}-focus-img-${imgIndex}`}
                      src={path}
                      alt={`题目配图 ${imgIndex + 1}`}
                      loading="lazy"
                    />
                  ))}
                </div>
              ) : null}
              <p className="item-stem">{focusItem.stem}</p>
              <MathVisualizer spec={visual} />
              {renderCountingManipulative(focusItem.stem)}
              {renderAnswerControls(focusItem)}
            </>
          }
          panelSlot={<SocraticPanel sessionId={sessionId} itemId={focusItem.id} />}
        />
      </section>
    )
  }

  return (
    <section className={layoutClass}>
      <div className="assess-head">
        <div className="assess-head-main">
          <div className="assess-head-meta">
            <p className="assess-phase">{phase === 'anchor' ? '锚点' : '完整'}</p>
            <p className="assess-counter" aria-live="polite">
              {counterCurrent} / {counterTotal}
            </p>
          </div>
          <h2>{phase === 'anchor' ? '锚点测评' : '完整测评'}</h2>
          {inferredChapter ? (
            <p className="chapter-banner">
              <span className="chapter-banner__chapter">{inferredChapter}</span>
              {sourceLabel ? (
                <span className="chapter-banner__source">{sourceLabel}</span>
              ) : null}
            </p>
          ) : null}
          <p className="lede assess-lede">
            {profile.nickname ? `${profile.nickname} · ` : ''}
            {paper.curriculum_label} · 共 {paper.items.length} 题
            {meta ? ` · ${meta}` : ''}
          </p>
        </div>
        <div className="countdown" aria-live="polite">
          剩余 {formatCountdown()}
          {overtimeHint ? <span className="countdown-overtime"> · 已超时</span> : null}
        </div>
      </div>

      <ProgressDots
        total={paper.items.length}
        current={currentIndex}
        answered={answers}
        questionIds={paper.items.map((item) => item.id)}
        onSelect={selectItem}
      />

      <div className="assessment-items">
        {paper.items.map((item, index) => (
          <article
            className={`item-card${index === currentIndex ? ' active' : ''}`}
            key={item.id}
            hidden={index !== currentIndex}
          >
            <p className="item-meta">
              <span>第 {index + 1} 题</span>
              <span>{item.difficulty}</span>
              {(item.knowledge_ids || []).length ? (
                <span>{(item.knowledge_ids || []).join(' · ')}</span>
              ) : null}
            </p>
            {item.image_paths?.length ? (
              <div className="item-images">
                {item.image_paths.map((path, imgIndex) => (
                  <img
                    key={`${item.id}-img-${imgIndex}`}
                    src={path}
                    alt={`题目配图 ${imgIndex + 1}`}
                    loading="lazy"
                  />
                ))}
              </div>
            ) : null}
            <p className="item-stem">{item.stem}</p>
            <MathVisualizer spec={inferVisualization(item.stem)} />
            {renderCountingManipulative(item.stem)}
            {renderAnswerControls(item)}
          </article>
        ))}
      </div>

      <div className="actions assess-actions">
        {onBack ? (
          <button className="btn secondary" type="button" onClick={onBack} disabled={busy}>
            返回建档
          </button>
        ) : null}
        <button
          className="btn secondary"
          type="button"
          disabled={busy || currentIndex <= 0}
          onClick={() => selectItem(Math.max(0, currentIndex - 1))}
        >
          上一题
        </button>
        <button
          className="btn secondary"
          type="button"
          disabled={busy || currentIndex >= paper.items.length - 1}
          onClick={() => selectItem(Math.min(paper.items.length - 1, currentIndex + 1))}
        >
          下一题
        </button>
        {phase === 'anchor' ? (
          <button className="btn" type="button" onClick={() => void submitAnchor()} disabled={busy}>
            {busy ? '生成完整卷…' : '提交锚点，继续完整测评'}
          </button>
        ) : (
          <button className="btn" type="button" onClick={() => void submitFull()} disabled={busy}>
            {busy ? '提交中…' : '提交并诊断'}
          </button>
        )}
      </div>
    </section>
  )
}
