import { useEffect, useState } from 'react'
import {
  api,
  type AssessmentItem,
  type AssessmentPaper,
  type StudentProfile,
} from '../api/client'
import { useResponsive } from '../hooks/useResponsive'
import ProgressDots from '../components/ProgressDots'

export type AssessmentCompletePayload = {
  paper: AssessmentPaper
  answers: Record<string, string>
}

type AssessmentProps = {
  sessionId: string
  profile: StudentProfile
  onComplete: (payload: AssessmentCompletePayload) => void | Promise<void>
  onError?: (message: string) => void
  onBack?: () => void
}

function gradeLocal(item: AssessmentItem, answer: string): boolean {
  const key = (item.answer_key || '').trim()
  if (!key) return false
  return answer.trim() === key
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

  useEffect(() => {
    let cancelled = false
    async function start() {
      setBusy(true)
      try {
        const res = await api.adaptiveStart(sessionId)
        if (cancelled) return
        setPaper(res.paper)
        setAnswers({})
        setCurrentIndex(0)
        setPhase('anchor')
        const bits = [
          res.inferred_chapter ? `推断章节：${res.inferred_chapter}` : '',
          res.layer2_used ? `二层补题：${res.layer2_source}` : '',
          `锚点 ${res.delivered}/${res.requested}`,
        ].filter(Boolean)
        setMeta(bits.join(' · '))
      } catch (err) {
        onError?.(err instanceof Error ? err.message : String(err))
      } finally {
        if (!cancelled) setBusy(false)
      }
    }
    void start()
    return () => {
      cancelled = true
    }
  }, [sessionId, onError])

  async function submitAnchor() {
    if (!paper) return
    setBusy(true)
    try {
      const anchorResults = paper.items.map((item) => ({
        item_id: item.id,
        knowledge_ids: item.knowledge_ids || [],
        is_correct: gradeLocal(item, answers[item.id] || ''),
      }))
      const res = await api.adaptiveContinue(sessionId, anchorResults)
      setPaper(res.paper)
      setAnswers({})
      setCurrentIndex(0)
      setPhase('full')
      setMeta(
        `完整测评 ${res.paper.items.length} 题` +
          (res.diagnosis ? ' · 已根据锚点调整知识点' : ''),
      )
    } catch (err) {
      onError?.(err instanceof Error ? err.message : String(err))
    } finally {
      setBusy(false)
    }
  }

  async function submitFull() {
    if (!paper) return
    setBusy(true)
    try {
      await onComplete({ paper, answers })
    } catch (err) {
      onError?.(err instanceof Error ? err.message : String(err))
    } finally {
      setBusy(false)
    }
  }

  if (phase === 'loading' || !paper) {
    return (
      <section className={`panel assessment-layout assessment-layout--${breakpoint}`}>
        <h2>自适应测评</h2>
        <p className="lede">{busy ? '正在生成锚点卷…' : '准备中…'}</p>
        {onBack ? (
          <div className="actions">
            <button className="btn secondary" type="button" onClick={onBack} disabled={busy}>
              返回建档
            </button>
          </div>
        ) : null}
      </section>
    )
  }

  const layoutClass = `panel assessment-layout assessment-layout--${breakpoint} assessment-container ${
    breakpoint === 'mobile' ? 'single-column' : 'two-column'
  }`

  return (
    <section className={layoutClass}>
      <div className="assess-head">
        <div>
          <h2>{phase === 'anchor' ? '锚点测评' : '完整测评'}</h2>
          <p className="lede">
            {profile.nickname ? `${profile.nickname} · ` : ''}
            {paper.curriculum_label} · 共 {paper.items.length} 题
            {meta ? ` · ${meta}` : ''}
          </p>
        </div>
      </div>

      <ProgressDots
        total={paper.items.length}
        current={currentIndex}
        answered={answers}
        questionIds={paper.items.map((item) => item.id)}
        onSelect={setCurrentIndex}
      />

      <div className="assessment-items">
        {paper.items.map((item, index) => (
          <article
            className={`item-card${index === currentIndex ? ' active' : ''}`}
            key={item.id}
            hidden={index !== currentIndex}
          >
            <p className="item-meta">
              第 {index + 1} 题 · {item.difficulty} · {(item.knowledge_ids || []).join(', ')}
            </p>
            <p className="item-stem">{item.stem}</p>
            {item.choices?.length ? (
              <div className="choices">
                {item.choices.map((choice) => (
                  <label key={choice}>
                    <input
                      type="radio"
                      name={item.id}
                      checked={(answers[item.id] || '') === choice}
                      onChange={() =>
                        setAnswers((prev) => ({ ...prev, [item.id]: choice }))
                      }
                    />
                    {choice}
                  </label>
                ))}
              </div>
            ) : (
              <textarea
                value={answers[item.id] || ''}
                onChange={(e) =>
                  setAnswers((prev) => ({ ...prev, [item.id]: e.target.value }))
                }
                rows={3}
                placeholder="输入你的答案"
              />
            )}
          </article>
        ))}
      </div>

      <div className="actions">
        {onBack ? (
          <button className="btn secondary" type="button" onClick={onBack} disabled={busy}>
            返回建档
          </button>
        ) : null}
        <button
          className="btn secondary"
          type="button"
          disabled={busy || currentIndex <= 0}
          onClick={() => setCurrentIndex((i) => Math.max(0, i - 1))}
        >
          上一题
        </button>
        <button
          className="btn secondary"
          type="button"
          disabled={busy || currentIndex >= paper.items.length - 1}
          onClick={() => setCurrentIndex((i) => Math.min(paper.items.length - 1, i + 1))}
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
