/**
 * Round 3 · Photomath: step-by-step review with alignment highlight (P4).
 * Shows rubric steps only — never the final answer_key unless unlocked by guardian.
 */

import { useMemo, useState } from 'react'
import { api } from '../api/client'

type StepReviewItem = {
  itemId: string
  stem: string
  rubricSteps: string[]
  studentAnswer?: string
}

type AlignRow = {
  student: string | null
  rubric: string | null
  status: 'matched' | 'extra' | 'missing'
}

type StepReviewListProps = {
  items: StepReviewItem[]
  sessionId?: string
  /** Student may request guardian unlock; never shows answer_key here */
  allowUnlockRequest?: boolean
}

/** Mirror of ilearn.core.step_align.align_steps (naive char overlap). */
function alignSteps(studentLines: string[], rubricSteps: string[]): AlignRow[] {
  const remaining: Array<[number, string]> = rubricSteps.map((s, i) => [i, s])
  const out: AlignRow[] = []
  for (const raw of studentLines) {
    const line = (raw || '').trim()
    if (!line) continue
    let bestI: number | null = null
    let bestScore = 0
    for (const [idx, step] of remaining) {
      const tokens = new Set(step.split(''))
      let score = 0
      for (const ch of line) {
        if (tokens.has(ch)) score += 1
      }
      if (score > bestScore) {
        bestScore = score
        bestI = idx
      }
    }
    if (bestI !== null && bestScore > 0) {
      const step = rubricSteps[bestI]
      const filtered = remaining.filter(([i]) => i !== bestI)
      remaining.length = 0
      remaining.push(...filtered)
      out.push({ student: line, rubric: step, status: 'matched' })
    } else {
      out.push({ student: line, rubric: null, status: 'extra' })
    }
  }
  for (const [, step] of remaining) {
    out.push({ student: null, rubric: step, status: 'missing' })
  }
  return out
}

export default function StepReviewList({
  items,
  sessionId,
  allowUnlockRequest = false,
}: StepReviewListProps) {
  const [requestedIds, setRequestedIds] = useState<Record<string, boolean>>({})
  const [busyId, setBusyId] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  const enriched = useMemo(
    () =>
      items.map((item) => {
        const lines = (item.studentAnswer || '')
          .split(/\n|；|;|。/)
          .map((s) => s.trim())
          .filter(Boolean)
        const align = alignSteps(lines, item.rubricSteps || [])
        return { ...item, align }
      }),
    [items],
  )

  async function requestUnlock(itemId: string) {
    if (!sessionId) {
      setError('缺少会话，无法申请解锁')
      return
    }
    setBusyId(itemId)
    setError(null)
    try {
      await api.requestUnlock(sessionId, itemId)
      setRequestedIds((prev) => ({ ...prev, [itemId]: true }))
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err))
    } finally {
      setBusyId(null)
    }
  }

  if (!items.length) return null

  const anyRequested = Object.keys(requestedIds).length > 0

  return (
    <section className="step-review-list" aria-labelledby="step-review-title">
      <h3 id="step-review-title" className="student-section-title">
        分步复盘（不含最终答案）
      </h3>
      <p className="lede">
        对照步骤检查你的思路；对齐高亮标出匹配 / 多余 / 缺失；最终数值答案默认隐藏。
      </p>
      <ul className="step-review-cards">
        {enriched.map((item, index) => (
          <li key={item.itemId} className="step-review-card">
            <p className="step-review-stem">
              <span className="step-review-index">错题 {index + 1}</span>
              {item.stem}
            </p>
            {item.align.length ? (
              <ol className="step-review-steps step-align-list">
                {item.align.map((row, i) => (
                  <li
                    key={`${item.itemId}-${i}-${row.status}`}
                    className={`step-align step-align--${row.status}`}
                    data-status={row.status}
                  >
                    {row.status === 'matched' && (
                      <span>
                        <strong>对齐</strong> {row.rubric}
                        {row.student ? ` ← 「${row.student}」` : null}
                      </span>
                    )}
                    {row.status === 'missing' && (
                      <span>
                        <strong>缺失</strong> {row.rubric}
                      </span>
                    )}
                    {row.status === 'extra' && (
                      <span>
                        <strong>多余</strong> {row.student}
                      </span>
                    )}
                  </li>
                ))}
              </ol>
            ) : item.rubricSteps.length ? (
              <ol className="step-review-steps">
                {item.rubricSteps.map((step) => (
                  <li key={step}>{step}</li>
                ))}
              </ol>
            ) : (
              <p className="step-review-fallback">
                先读清条件 → 选择合适方法 → 逐步计算 → 回代检验（终答已隐藏）
              </p>
            )}
            <p className="step-review-guard" role="note">
              {requestedIds[item.itemId]
                ? '已向教师/家长发起终答解锁申请（会话内记录）'
                : '终答已遮罩 · 请用步骤自检'}
            </p>
            {allowUnlockRequest && sessionId ? (
              <button
                type="button"
                className="btn secondary"
                disabled={Boolean(requestedIds[item.itemId]) || busyId === item.itemId}
                onClick={() => void requestUnlock(item.itemId)}
              >
                {requestedIds[item.itemId]
                  ? '已申请解锁'
                  : busyId === item.itemId
                    ? '提交中…'
                    : '申请教师/家长解锁终答'}
              </button>
            ) : null}
          </li>
        ))}
      </ul>
      {allowUnlockRequest && !sessionId ? (
        <p className="lede">登录会话后可向教师/家长申请解锁终答。</p>
      ) : null}
      {anyRequested ? (
        <p className="lede" role="status">
          解锁申请已记录；终答不会显示在学生端，需监护人在家长/教师端批准后查看。
        </p>
      ) : null}
      {error ? (
        <p className="error" role="alert">
          {error}
        </p>
      ) : null}
    </section>
  )
}
