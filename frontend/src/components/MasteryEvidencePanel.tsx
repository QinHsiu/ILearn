import { useEffect, useState } from 'react'
import { api } from '../api/client'

type MasteryEvidencePanelProps = {
  sessionId: string
  title?: string
}

/** P2 / Why-Use: mastery as evidence quadruple, not a single score. */
export default function MasteryEvidencePanel({
  sessionId,
  title = '掌握证据（四元组）',
}: MasteryEvidencePanelProps) {
  const [data, setData] = useState<{
    mastery_percent: number | null
    evidence_count: number
    probe_gap_count: number
    discounted_hint_correct: number
  } | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    void api
      .getMasteryPublic(sessionId)
      .then((row) => {
        if (!cancelled) {
          setData({
            mastery_percent: row.mastery_percent,
            evidence_count: row.evidence_count,
            probe_gap_count: row.probe_gap_count,
            discounted_hint_correct: row.discounted_hint_correct,
          })
          setError(null)
        }
      })
      .catch((err) => {
        if (!cancelled) {
          setData(null)
          setError(err instanceof Error ? err.message : String(err))
        }
      })
    return () => {
      cancelled = true
    }
  }, [sessionId])

  if (error) {
    return (
      <p className="error" role="alert">
        {error}
      </p>
    )
  }
  if (!data) return <p className="lede">加载掌握证据…</p>

  return (
    <section className="mastery-evidence-panel" aria-labelledby="mastery-evidence-title">
      <h3 id="mastery-evidence-title" className="student-section-title">
        {title}
      </h3>
      <p className="lede">
        提示后做对不会算作已掌握；探针缺口提醒还需要无提示复核。
      </p>
      <div className="summary-grid">
        <article className="summary-block">
          <span>掌握度</span>
          <strong>{data.mastery_percent != null ? `${data.mastery_percent}%` : '—'}</strong>
        </article>
        <article className="summary-block">
          <span>证据条数</span>
          <strong>{data.evidence_count}</strong>
        </article>
        <article className="summary-block">
          <span>探针缺口</span>
          <strong>{data.probe_gap_count}</strong>
        </article>
        <article className="summary-block">
          <span>提示后做对（未计掌握）</span>
          <strong>{data.discounted_hint_correct}</strong>
        </article>
      </div>
    </section>
  )
}
