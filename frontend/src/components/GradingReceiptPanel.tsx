import { useEffect, useState } from 'react'
import { api } from '../api/client'
import SoftPdfButton from './SoftPdfButton'

type ReceiptRow = {
  item_id: string
  final_correct: boolean
  grading_degraded?: boolean
  lane?: string
  receipt: {
    grader_version?: string
    model_id?: string | null
    graded_at?: string
    ocr_degraded?: boolean | null
  } | null
}

type GradingReceiptPanelProps = {
  sessionId: string
}

/** P5 win-bar: expose auditable grading receipts in student review. */
export default function GradingReceiptPanel({ sessionId }: GradingReceiptPanelProps) {
  const [rows, setRows] = useState<ReceiptRow[] | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    void api
      .getGradingReceipts(sessionId)
      .then((data) => {
        if (!cancelled) setRows(data.receipts)
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
  if (!rows) return <p>加载批改收据…</p>
  if (!rows.length) return null

  return (
    <section className="grading-receipt-panel" aria-labelledby="grading-receipt-title">
      <h3 id="grading-receipt-title" className="student-section-title">
        批改收据（可审计）
      </h3>
      <p className="lede">每题绑定 grader 版本与批改时间，超越黑盒自动批改。</p>
      <p className="lede" role="note">
        如何复核：打开「Grader」列看规则/模型版本；若「降级」为是，表示本场用了兜底判分，可让老师对照步骤再看一眼——仍不会在此展示终答。
      </p>
      <p>
        <SoftPdfButton
          sessionId={sessionId}
          kind="grading-receipts"
          label="导出批改收据 PDF"
        />
      </p>
      <table className="table">
        <thead>
          <tr>
            <th>题目</th>
            <th>结果</th>
            <th>Grader</th>
            <th>轨道</th>
            <th>降级</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row.item_id}>
              <td>{row.item_id}</td>
              <td>{row.final_correct ? '正确' : '错误'}</td>
              <td>{row.receipt?.grader_version || '—'}</td>
              <td>{row.lane || '—'}</td>
              <td>{row.grading_degraded ? '是' : '否'}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  )
}
