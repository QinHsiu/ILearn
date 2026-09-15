import { useEffect, useState } from 'react'
import { api } from '../api/client'

type ReplanExplainPanelProps = {
  sessionId: string
  refreshKey?: number
}

/** P11 / Why-Use: show why the plan was refreshed — never leaks final answers. */
export default function ReplanExplainPanel({ sessionId, refreshKey = 0 }: ReplanExplainPanelProps) {
  const [explain, setExplain] = useState<{
    triggered?: boolean
    reasons?: string[]
    previous_goal?: string | null
    new_goal?: string | null
  } | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    void api
      .getReplanExplain(sessionId)
      .then((data) => {
        if (!cancelled) {
          setExplain((data.explain || {}) as {
            triggered?: boolean
            reasons?: string[]
            previous_goal?: string | null
            new_goal?: string | null
          })
          setError(null)
        }
      })
      .catch((err) => {
        if (!cancelled) {
          setExplain(null)
          setError(err instanceof Error ? err.message : String(err))
        }
      })
    return () => {
      cancelled = true
    }
  }, [sessionId, refreshKey])

  if (error) {
    return (
      <p className="error" role="alert">
        {error}
      </p>
    )
  }
  if (!explain) return null

  const reasons = explain.reasons || []
  if (!reasons.length && !explain.previous_goal && !explain.new_goal) return null

  return (
    <section className="replan-explain-panel" aria-labelledby="replan-explain-title">
      <h3 id="replan-explain-title" className="student-section-title">
        为什么重新规划
      </h3>
      <p className="lede">
        {explain.triggered ? '系统根据学情证据建议调整计划。' : '本次为手动或温和刷新，依据现有证据更新计划。'}
      </p>
      {reasons.length ? (
        <ul>
          {reasons.map((reason) => (
            <li key={reason}>{reason}</li>
          ))}
        </ul>
      ) : null}
      {explain.previous_goal || explain.new_goal ? (
        <p className="lede">
          {explain.previous_goal ? `原目标：${explain.previous_goal}` : null}
          {explain.previous_goal && explain.new_goal ? ' → ' : null}
          {explain.new_goal ? `新目标：${explain.new_goal}` : null}
        </p>
      ) : null}
    </section>
  )
}
