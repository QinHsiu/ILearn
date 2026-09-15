/**
 * Round 12 · OpenMAIC / DeepTutor: auditable orchestration trust surface.
 * Loads live quality-gate status from /quality-gates (P10).
 */
import { useEffect, useState } from 'react'
import { api } from '../api/client'

type QualityGate = {
  id: string
  name: string
  status: string
  suite: string
}

type QualityPayload = {
  gates: QualityGate[]
  summary: { total: number; enforced: number }
  how_to_verify: string[]
}

export default function TrustPage() {
  const [gates, setGates] = useState<QualityPayload | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    void api
      .getQualityGates()
      .then((data) => {
        if (!cancelled) setGates(data)
      })
      .catch((err) => {
        if (!cancelled) setError(err instanceof Error ? err.message : String(err))
      })
    return () => {
      cancelled = true
    }
  }, [])

  return (
    <main className="landing-page trust-page">
      <header className="landing-header">
        <div className="landing-brand-block">
          <p className="landing-kicker">AUDITABLE</p>
          <p className="landing-brand">ILearn</p>
        </div>
        <p className="landing-meta">
          <a href="?">返回首页</a>
        </p>
      </header>
      <section className="landing-hero" aria-labelledby="trust-title">
        <h1 id="trust-title">可审计编排 · 信任说明</h1>
        <p className="landing-lede">
          参考开源教学 Agent 的模块化与可观测传统：ILearn 用多 Agent 流水线替代「一个巨型
          prompt」，关键决策可追溯。
        </p>
        <ul>
          <li>课标在环：组卷与计划可绑定 curriculum citation</li>
          <li>批改可审计：OCR 与判分分离，GradingReceipt 可复现</li>
          <li>掌握度双轨：practice / probe + 证据日志</li>
          <li>编排可观测：阶段状态机、decision_log、能力注册表 GET /capabilities</li>
          <li>辅导护栏：苏格拉底状态机 + 不泄终答约定</li>
        </ul>
        <section className="quality-gates-panel" aria-labelledby="qg-title">
          <h2 id="qg-title">质量门（对用户可见）</h2>
          {error ? <p className="error">{error}</p> : null}
          {gates ? (
            <>
              <p className="lede">
                已强制执行 {gates.summary.enforced}/{gates.summary.total} 项门禁
              </p>
              <ul>
                {gates.gates.map((g) => (
                  <li key={g.id}>
                    <strong>{g.name}</strong> · {g.status}
                  </li>
                ))}
              </ul>
              <p className="lede">
                本地复核：{gates.how_to_verify.join(' · ')}
              </p>
            </>
          ) : (
            <p className="lede">加载质量门状态…</p>
          )}
        </section>
        <p className="lede">
          能力探测：<code>/capabilities</code> · <code>/healthz</code> ·
          <code>/quality-gates</code> · 会话{' '}
          <code>/sessions/&#123;id&#125;/decision-log/summary</code> ·
          <code>/grading-receipts</code>
        </p>
      </section>
    </main>
  )
}
