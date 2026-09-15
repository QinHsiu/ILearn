import { useEffect, useState } from 'react'
import { api } from '../api/client'
import type { ErrorNotebookPayload } from '../api/client'
import SoftPdfButton from './SoftPdfButton'

type ErrorNotebookBlockProps = {
  sessionId: string
  /** Student surface: one-click repractice (activates the retry paper). */
  onRepractice?: () => void
  /** Parent surface: no repractice CTA, mask stays, PDF export allowed. */
  readOnly?: boolean
  title?: string
}

/** W4 · error-notebook home: count, focus, per-item stem/steps/source, final answer always masked. */
export default function ErrorNotebookBlock({
  sessionId,
  onRepractice,
  readOnly = false,
  title = '错题本',
}: ErrorNotebookBlockProps) {
  const [data, setData] = useState<ErrorNotebookPayload | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!sessionId) return
    let cancelled = false
    void api
      .getErrorNotebook(sessionId)
      .then((row) => {
        if (!cancelled) {
          setData(row)
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

  if (!sessionId) return null
  if (error) {
    return (
      <p className="error" role="alert">
        {error}
      </p>
    )
  }
  if (!data) return <p className="lede">加载错题本…</p>

  const showRepractice = !readOnly && data.repractice_ready && data.count > 0 && onRepractice

  return (
    <section className="error-notebook-block" role="region" aria-labelledby="error-notebook-title">
      <header className="error-notebook-head">
        <div>
          <h3 id="error-notebook-title" className="student-section-title">
            {title}
          </h3>
          <p className="lede">
            {data.count > 0 ? `共 ${data.count} 道错题` : '本场没有错题'}
            {data.knowledge_focus.length ? ` · 集中在：${data.knowledge_focus.join('、')}` : ''}
          </p>
        </div>
        <span className="pill error-notebook-mask" title={data.mask_note}>
          不泄终答
        </span>
      </header>
      <p className="error-notebook-note">
        {data.mask_note}
        {readOnly ? ' 家长不看终答，只看孩子卡在哪一步。' : ''}
      </p>
      {data.count > 0 ? (
        <ol className="error-notebook-list">
          {data.items.map((item, index) => (
            <li key={item.item_id} className="error-notebook-item">
              <p className="error-notebook-stem">
                <span className="error-notebook-index">{index + 1}</span>
                <strong>{item.stem}</strong>
              </p>
              <p className="error-notebook-meta">
                {item.knowledge_ids.length ? `知识点：${item.knowledge_ids.join('、')}` : '知识点：—'}
                {item.citation_label ? ` · 来源：${item.citation_label}` : ''}
              </p>
              <p className="error-notebook-meta">
                我的作答：{item.student_answer?.trim() ? item.student_answer : '未作答'}
                {' · '}
                <span className="error-notebook-answer-mask" aria-label="最终答案已遮罩">
                  终答 ●●●
                </span>
              </p>
              {item.rubric_steps.length ? (
                <p className="error-notebook-steps">思路步骤：{item.rubric_steps.join(' → ')}</p>
              ) : null}
            </li>
          ))}
        </ol>
      ) : null}
      <div className="actions error-notebook-actions">
        {showRepractice ? (
          <button className="btn" type="button" onClick={onRepractice}>
            一键重练这 {data.count} 道
          </button>
        ) : null}
        {data.count > 0 ? (
          <SoftPdfButton sessionId={sessionId} kind="error-notebook" label="导出错题本 PDF" />
        ) : null}
      </div>
    </section>
  )
}
