import { useEffect, useState } from 'react'
import { api } from '../api/client'
import type { EffectivenessResponse } from '../api/client'

type EffectivenessDashboardProps = {
  sessionId: string
}

const COMPARISON_ROWS: Array<{
  key: 'grading_time' | 'personalized' | 'feedback_delay'
  label: string
}> = [
  { key: 'grading_time', label: '批改耗时' },
  { key: 'personalized', label: '个性化程度' },
  { key: 'feedback_delay', label: '反馈周期' },
]

export default function EffectivenessDashboard({ sessionId }: EffectivenessDashboardProps) {
  const [data, setData] = useState<EffectivenessResponse | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    setError(null)
    setData(null)
    void api.getEffectiveness(sessionId).then(setData).catch((err) => {
      setError(err instanceof Error ? err.message : String(err))
    })
  }, [sessionId])

  if (error) {
    return <p className="error dashboard-error" role="alert">{error}</p>
  }
  if (!data) {
    return <p>加载中…</p>
  }

  const { metrics, comparison } = data
  const vs = comparison.traditional_vs_ilearn
  const simulated = metrics.is_simulated

  return (
    <div
      className={`effectiveness-dashboard${simulated ? ' is-simulated' : ''}`}
      data-simulated={simulated ? 'true' : 'false'}
    >
      {simulated ? (
        <p className="simulated-data-notice" role="status">
          ⚠️ 当前部分效果数据为演示估算值（{metrics.data_source}），仅供参考。
        </p>
      ) : null}
      <section className="comparison-cards" aria-labelledby="comparison-cards-title">
        <h3 id="comparison-cards-title">前后对比</h3>
        <div className="comparison-cards-grid">
          <article aria-label="掌握度前后对比" className="comparison-card metric-card">
            <span>掌握度</span>
            <strong>
              {metrics.pre_assessment_score} → {metrics.post_assessment_score ?? '—'}
            </strong>
          </article>
          <article aria-label="薄弱点对比" className="comparison-card metric-card">
            <span>薄弱点</span>
            <strong>
              已解决 {metrics.weakness_resolved_count} / 仍存 {metrics.weakness_remaining_count}
            </strong>
          </article>
          <article aria-label="批改耗时对比" className="comparison-card metric-card">
            <span>批改耗时</span>
            <strong>
              {metrics.traditional_grading_time_minutes} → {metrics.estimated_grading_time_minutes}分钟
            </strong>
          </article>
          <article aria-label="诊断依据" className="comparison-card metric-card">
            <span>诊断依据</span>
            <strong>
              {Math.round(metrics.diagnosis_confidence * 100)}% · {metrics.evidence_count} 条证据
            </strong>
          </article>
        </div>
      </section>
      <div className="metrics-grid">
        <article className="metric-card">
          <span>掌握度提升</span>
          <strong>+{metrics.mastery_gain}%</strong>
          <small>解决了 {metrics.weakness_resolved_count} 个薄弱点</small>
        </article>
        <article className="metric-card">
          <span>批改时间节省</span>
          <strong>{Math.round(metrics.time_saved_percent)}%</strong>
          <small>
            从 {metrics.traditional_grading_time_minutes}分钟 → {metrics.estimated_grading_time_minutes}分钟
          </small>
        </article>
        <article className="metric-card">
          <span>完成率</span>
          <strong>{metrics.completion_rate}%</strong>
          <small>共 {metrics.total_questions} 题</small>
        </article>
        <article className="metric-card">
          <span>诊断置信度</span>
          <strong>{Math.round(metrics.diagnosis_confidence * 100)}%</strong>
          <small>基于 {metrics.evidence_count} 条证据</small>
        </article>
      </div>
      <section className="comparison-section">
        <h3>与传统教学对比</h3>
        <table className="comparison-table">
          <thead>
            <tr>
              <th>对比项</th>
              <th>传统教学</th>
              <th>ILearn</th>
            </tr>
          </thead>
          <tbody>
            {COMPARISON_ROWS.map((row) => (
              <tr key={row.key}>
                <th scope="row">{row.label}</th>
                <td>{vs[row.key].traditional}</td>
                <td>{vs[row.key].ilearn}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
      <button
        className="btn"
        type="button"
        onClick={() => {
          void api.exportEffectivenessPdf(sessionId)
        }}
      >
        导出效果验证报告
      </button>
    </div>
  )
}
