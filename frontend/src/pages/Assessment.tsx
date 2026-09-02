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

/** Default overall assessment window: 150 minutes. */
export const ASSESSMENT_SECONDS = 150 * 60

export type AssessmentItemMeta = {
  elapsed_ms: number
  hint_used?: boolean
}

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

  const onErrorRef = useRef(onError)
  onErrorRef.current = onError
  const submitFullRef = useRef<() => void>(() => {})
  const itemStartedAtRef = useRef<number>(Date.now())
  const currentItemIdRef = useRef<string | null>(null)
  const elapsedMsRef = useRef<Record<string, number>>({})
  const hintUsedRef = useRef<Record<string, boolean>>({})

  const countdownActive = phase === 'anchor' || phase === 'full'
  const { format: formatCountdown, reset: resetCountdown } = useCountdown(
    countdownActive ? ASSESSMENT_SECONDS : 0,
    () => {
      if ((phase === 'anchor' || phase === 'full') && paper && !busy) {
        submitFullRef.current()
      }
    },
  )

  const flushCurrentItemTime = useCallback(() => {
    const itemId = currentItemIdRef.current
    if (!itemId) return
    const delta = Date.now() - itemStartedAtRef.current
    if (delta <= 0) return
    const next = {
      ...elapsedMsRef.current,
      [itemId]: (elapsedMsRef.current[itemId] || 0) + delta,
    }
    elapsedMsRef.current = next
    setElapsedMs(next)
    itemStartedAtRef.current = Date.now()
  }, [])

  const selectItem = useCallback(
    (index: number) => {
      flushCurrentItemTime()
      setCurrentIndex(index)
      const nextId = paper?.items[index]?.id ?? null
      currentItemIdRef.current = nextId
      itemStartedAtRef.current = Date.now()
    },
    [flushCurrentItemTime, paper],
  )

  useEffect(() => {
    let cancelled = false
    async function start() {
      setBusy(true)
      try {
        const res = await api.adaptiveStart(sessionId)
        if (cancelled) return
        setPaper(res.paper)
        setAnswers({})
        setImageUploads({})
        setFocusItemId(null)
        setHintUsed({})
        setElapsedMs({})
        elapsedMsRef.current = {}
        hintUsedRef.current = {}
        setCurrentIndex(0)
        currentItemIdRef.current = res.paper.items[0]?.id ?? null
        itemStartedAtRef.current = Date.now()
        setPhase('anchor')
        setInferredChapter(res.inferred_chapter ?? null)
        setSourceLabel(firstMultimodalSourceLabel(res.paper.items))
        setMeta(buildMetaLine(res))
      } catch (err) {
        onErrorRef.current?.(err instanceof Error ? err.message : String(err))
      } finally {
        if (!cancelled) setBusy(false)
      }
    }
    void start()
    return () => {
      cancelled = true
    }
  }, [sessionId])

  useEffect(() => {
    if (phase === 'anchor' || phase === 'full') {
      resetCountdown()
    }
  }, [phase, sessionId, paper?.items.length, resetCountdown])

  useEffect(() => {
    return () => {
      Object.values(imageUploads).forEach((row) => {
        if (row.preview) URL.revokeObjectURL(row.preview)
      })
    }
  }, [imageUploads])

  async function onPickImage(itemId: string, file: File | undefined) {
    if (!file) return
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

  function buildItemMeta(items: AssessmentItem[]): Record<string, AssessmentItemMeta> {
    flushCurrentItemTime()
    const metaMap: Record<string, AssessmentItemMeta> = {}
    for (const item of items) {
      metaMap[item.id] = {
        elapsed_ms: elapsedMsRef.current[item.id] || 0,
        hint_used: Boolean(hintUsedRef.current[item.id]),
      }
    }
    return metaMap
  }

  async function submitAnchor() {
    if (!paper) return
    setBusy(true)
    flushCurrentItemTime()
    try {
      const anchorResults = paper.items.map((item) => ({
        item_id: item.id,
        knowledge_ids: item.knowledge_ids || [],
        is_correct: gradeLocal(item, answers[item.id] || ''),
      }))
      const res = await api.adaptiveContinue(sessionId, anchorResults)
      setPaper(res.paper)
      setAnswers({})
      setImageUploads({})
      setFocusItemId(null)
      setHintUsed({})
      setElapsedMs({})
      elapsedMsRef.current = {}
      hintUsedRef.current = {}
      setCurrentIndex(0)
      currentItemIdRef.current = res.paper.items[0]?.id ?? null
      itemStartedAtRef.current = Date.now()
      setPhase('full')
      setInferredChapter(res.inferred_chapter ?? null)
      setSourceLabel(firstMultimodalSourceLabel(res.paper.items))
      setMeta(buildMetaLine(res))
    } catch (err) {
      onErrorRef.current?.(err instanceof Error ? err.message : String(err))
    } finally {
      setBusy(false)
    }
  }

  async function submitFull() {
    if (!paper) return
    setBusy(true)
    try {
      const itemMeta = buildItemMeta(paper.items)
      const images = Object.values(imageUploads).map(
        ({ item_id, image_base64, mime_type }) => ({
          item_id,
          image_base64,
          mime_type,
        }),
      )
      await onComplete({ paper, answers, images, itemMeta })
    } catch (err) {
      onErrorRef.current?.(err instanceof Error ? err.message : String(err))
    } finally {
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
