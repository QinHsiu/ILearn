import { useEffect, useState } from 'react'
import { api } from '../api/client'
import type { WeekBucket, WeeklyReport } from '../api/client'

type WeeklyReportPanelProps = {
  nickname: string
  title?: string
}

type RowSpec = {
  key: keyof WeekBucket
  label: string
  deltaKey?: string
  unit?: string
  invertGood?: boolean
  reference?: boolean
}

const ROWS: RowSpec[] = [
  { key: 'session_count', label: '学习次数', deltaKey: 'session_count', unit: '次' },
  { key: 'active_days', label: '活跃天数', deltaKey: 'active_days', unit: '天' },
  { key: 'evidence_count', label: '证据条数', deltaKey: 'evidence_count' },
  { key: 'probe_correct_count', label: '独立探针通过', deltaKey: 'probe_correct_count' },
  { key: 'probe_gap_count', label: '探针缺口', deltaKey: 'probe_gap_count', invertGood: true },
  { key: 'mastery_percent', label: '掌握度', deltaKey: 'mastery_percent', unit: '%' },
  { key: 'hinted_correct_count', label: '提示后做对（未计掌握）', reference: true },
  { key: 'accuracy_percent', label: '正确率（仅参考）', unit: '%', reference: true },
]

function cell(value: unknown, unit = ''): string {
  if (value == null) return '—'
  return `${value}${unit}`
}

function signed(n: number | null | undefined, invertGood = false): { text: string; tone: string } {
  if (n == null) return { text: '—', tone: 'none' }
  if (n === 0) return { text: '持平', tone: 'flat' }
  const good = invertGood ? n < 0 : n > 0
  return { text: `${n > 0 ? '+' : ''}${n}`, tone: good ? 'good' : 'watch' }
}

/** W3 · calendar-week parent report: this week vs last week, evidence before accuracy. */
export default function WeeklyReportPanel({ nickname, title = '本周学习周报' }: WeeklyReportPanelProps) {
  const [data, setData] = useState<WeeklyReport | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const name = (nickname || '').trim()
    if (!name) {
      setData(null)
      return
    }
    let cancelled = false
    void api
      .getLearnerWeeklyReport(name)
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
  }, [nickname])

  if (!nickname.trim()) return null
  if (error) {
    return (
      <p className="error" role="alert">
        {error}
      </p>
    )
  }
  if (!data) return <p className="lede">加载本周周报…</p>

  const { this_week: tw, last_week: lw } = data

  return (
    <section className="weekly-report-panel" role="region" aria-labelledby="weekly-report-title">
      <h3 id="weekly-report-title" className="student-section-title">
        {title}
      </h3>
      <p className="lede weekly-report-range">
        自然周 {data.week_start} ~ {data.week_end}（周一至周日 · 北京时间）
      </p>
      <p className="lede weekly-report-narrative" role="status">
        {data.narrative}
      </p>
      <table className="weekly-report-table">
        <thead>
          <tr>
            <th scope="col">指标</th>
            <th scope="col">本周</th>
            <th scope="col">上周</th>
            <th scope="col">变化</th>
          </tr>
        </thead>
        <tbody>
          {ROWS.map((row) => {
            const d = row.deltaKey ? signed(data.delta[row.deltaKey], row.invertGood) : null
            return (
              <tr key={row.key} className={row.reference ? 'is-reference' : undefined}>
                <th scope="row">{row.label}</th>
                <td>{cell(tw[row.key], row.unit)}</td>
                <td>{cell(lw[row.key], row.unit)}</td>
                <td>
                  {d ? (
                    <span className="weekly-delta" data-tone={d.tone}>
                      {d.text}
                    </span>
                  ) : (
                    <span className="weekly-delta" data-tone="none">
                      不比较
                    </span>
                  )}
                </td>
              </tr>
            )
          })}
        </tbody>
      </table>
      <p className="weekly-report-focus">
        本周关注：{tw.focus.length ? tw.focus.join('、') : '暂无薄弱点记录'}
        {lw.focus.length ? ` · 上周关注：${lw.focus.join('、')}` : ''}
      </p>
      <p className="weekly-report-honesty">{data.honesty_note}</p>
    </section>
  )
}
