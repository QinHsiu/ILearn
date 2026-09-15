import { useEffect, useState } from 'react'
import { api } from '../api/client'

type ContinuityPayload = {
  nickname: string
  session_count: number
  streak_days: number
  next_challenge: string
  companion_line: string
  seven_day_chain: Array<{ day_index: number; focus: string; session_id?: string | null }>
  progress_delta?: {
    has_baseline: boolean
    evidence_delta?: number | null
    probe_gap_delta?: number | null
    mastery_delta?: number | null
    narrative?: string
  } | null
}

type CompanionContinuityPanelProps = {
  nickname: string
  title?: string
  showParentDelta?: boolean
}

function fmtSigned(n: number | null | undefined, invertGood = false): string {
  if (n == null) return '—'
  if (n === 0) return '持平'
  const good = invertGood ? n < 0 : n > 0
  const sign = n > 0 ? '+' : ''
  return `${sign}${n}${good ? ' ↑' : ' ↓'}`
}

/** Readable companion continuity — next challenge, streak, 7-day focus, vs-last delta. */
export default function CompanionContinuityPanel({
  nickname,
  title = '陪伴连续性',
  showParentDelta = false,
}: CompanionContinuityPanelProps) {
  const [data, setData] = useState<ContinuityPayload | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const name = (nickname || '').trim()
    if (!name) {
      setData(null)
      return
    }
    let cancelled = false
    void api
      .getLearnerContinuity(name)
      .then((row) => {
        if (!cancelled) {
          setData(row as ContinuityPayload)
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
  }, [nickname])

  if (!nickname.trim()) return null
  if (error) {
    return (
      <p className="error" role="alert">
        {error}
      </p>
    )
  }
  if (!data) return <p className="lede">加载陪伴连续性…</p>

  const delta = data.progress_delta

  return (
    <section className="companion-continuity-panel" aria-labelledby="companion-continuity-title">
      <h3 id="companion-continuity-title" className="student-section-title">
        {title}
      </h3>
      <p className="lede companion-line" role="status">
        {data.companion_line}
      </p>
      <div className="summary-grid">
        <article className="summary-block">
          <span>下一挑战</span>
          <strong>{data.next_challenge}</strong>
        </article>
        <article className="summary-block">
          <span>连学天数</span>
          <strong>{data.streak_days} 天</strong>
        </article>
        <article className="summary-block">
          <span>已陪伴会话</span>
          <strong>{data.session_count} 次</strong>
        </article>
      </div>
      {showParentDelta && delta ? (
        <div className="parent-vs-last" aria-label="比上次">
          <h4>比上次（证据优先）</h4>
          <p className="lede">{delta.narrative || '—'}</p>
          {delta.has_baseline ? (
            <div className="summary-grid">
              <article className="summary-block">
                <span>证据条数</span>
                <strong>{fmtSigned(delta.evidence_delta)}</strong>
              </article>
              <article className="summary-block">
                <span>探针缺口</span>
                <strong>{fmtSigned(delta.probe_gap_delta, true)}</strong>
              </article>
              <article className="summary-block">
                <span>掌握度</span>
                <strong>{fmtSigned(delta.mastery_delta)}%</strong>
              </article>
            </div>
          ) : null}
        </div>
      ) : null}
      <ol className="seven-day-chain" aria-label="七日学习焦点">
        {data.seven_day_chain.map((day) => (
          <li key={day.day_index} className={day.session_id ? 'has-session' : 'empty-day'}>
            <span className="day-index">D{day.day_index}</span>
            <span className="day-focus">{day.focus}</span>
          </li>
        ))}
      </ol>
    </section>
  )
}
