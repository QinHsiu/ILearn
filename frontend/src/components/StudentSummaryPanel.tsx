import { useEffect, useState } from 'react'
import { api } from '../api/client'
import type { StudentSummary } from '../api/client'

type StudentSummaryPanelProps = {
  sessionId: string
}

export default function StudentSummaryPanel({ sessionId }: StudentSummaryPanelProps) {
  const [data, setData] = useState<StudentSummary | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    setError(null)
    setData(null)
    void api
      .getStudentSummary(sessionId)
      .then((summary) => {
        if (!cancelled) setData(summary)
      })
      .catch((err) => {
        if (!cancelled) setError(err instanceof Error ? err.message : String(err))
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
  if (!data) {
    return <p>加载中…</p>
  }

  return (
    <section aria-label="学生任务摘要">
      <div className="summary-grid">
        <article className="summary-block">
          <span>当前任务</span>
          <strong>{data.current_task}</strong>
        </article>
        <article className="summary-block">
          <span>任务进度</span>
          <strong>
            {data.completed_tasks} / {data.total_tasks}
          </strong>
        </article>
        <article className="summary-block" aria-label="获得星星">
          <span>获得星星</span>
          <strong>{data.stars_earned}</strong>
        </article>
        <article className="summary-block">
          <span>下一挑战</span>
          <strong>{data.next_challenge}</strong>
        </article>
      </div>
      {data.narrative ? <p>{data.narrative}</p> : null}
    </section>
  )
}
