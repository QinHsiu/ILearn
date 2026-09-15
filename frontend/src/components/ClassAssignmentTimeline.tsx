export type CompletionState = 'not_started' | 'in_repractice' | 'submitted'

export type ClassTimelineRow = {
  session_id: string
  student_name: string
  assigned_at?: string | null
  topic?: string | null
  item_counts?: Record<string, number>
  completion?: { state: CompletionState; label: string; at?: string | null } | null
}

export type CompletionSummary = Record<CompletionState, number>

type ClassAssignmentTimelineProps = {
  rows: ClassTimelineRow[]
  summary: CompletionSummary | null
  limit?: number
}

const ORDER: CompletionState[] = ['submitted', 'in_repractice', 'not_started']
const FALLBACK_LABEL: Record<CompletionState, string> = {
  submitted: '已提交',
  in_repractice: '重练中',
  not_started: '未开始',
}

function fmtStamp(value?: string | null): string {
  if (!value) return '—'
  const d = new Date(value)
  if (Number.isNaN(d.getTime())) return value
  return d.toLocaleString('zh-CN', { month: 'numeric', day: 'numeric', hour: '2-digit', minute: '2-digit' })
}

/** W2 · class receipts with follow-up: did each student start / submit the assigned paper? */
export default function ClassAssignmentTimeline({ rows, summary, limit = 12 }: ClassAssignmentTimelineProps) {
  if (!rows.length) {
    return <p className="dashboard-empty">暂无班级级布置回执，点「布置巩固」后会出现在这里。</p>
  }
  return (
    <>
      {summary ? (
        <div className="completion-summary" role="group" aria-label="布置回访">
          {ORDER.map((state) => (
            <span key={state} className="pill completion-pill" data-state={state}>
              {FALLBACK_LABEL[state]} {summary[state] ?? 0}
            </span>
          ))}
        </div>
      ) : null}
      <ol className="class-timeline-list">
        {rows.slice(0, limit).map((row, index) => {
          const state = row.completion?.state || 'not_started'
          const label = row.completion?.label || FALLBACK_LABEL[state]
          return (
            <li key={`${row.session_id}-${row.assigned_at || index}`}>
              <strong>{row.student_name}</strong>
              {' · '}
              {fmtStamp(row.assigned_at)}
              {' · '}
              {String(row.topic || '巩固')}
              {' · '}
              {row.item_counts
                ? Object.entries(row.item_counts)
                    .map(([k, n]) => `${k}:${n}`)
                    .join(' ')
                : '—'}
              {' '}
              <span className="pill completion-pill" data-state={state}>
                {label}
              </span>
              {row.completion?.at && state !== 'not_started' ? (
                <span className="completion-at"> {fmtStamp(row.completion.at)}</span>
              ) : null}
            </li>
          )
        })}
      </ol>
    </>
  )
}
