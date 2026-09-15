import { useEffect, useState } from 'react'
import { api } from '../api/client'

const roleCards: Array<{
  role: 'parent' | 'teacher' | 'student'
  index: string
  title: string
  description: string
}> = [
  {
    role: 'parent',
    index: '01',
    title: '家长 · 今晚就能陪',
    description: '一分钟看懂进步与缺口，拿到亲子口述三件事——不当监工也能帮上忙',
  },
  {
    role: 'teacher',
    index: '02',
    title: '教师 · 布置就能办完',
    description: '分层建议一键成真卷，干预名单可点布置并留回执——不只是数据墙',
  },
  {
    role: 'student',
    index: '03',
    title: '学生 · 敢问敢练',
    description: '卡住有引导但不剧透终答；做完能看见「真会了」的证据，不是抄到的分数',
  },
]

type QualitySummary = { total: number; enforced: number }

export default function LandingPage() {
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [demoRole, setDemoRole] = useState<'teacher' | 'parent' | 'student'>('teacher')
  const [waitEmail, setWaitEmail] = useState('')
  const [waitRole, setWaitRole] = useState<'parent' | 'teacher' | 'other'>('parent')
  const [waitBusy, setWaitBusy] = useState(false)
  const [waitMsg, setWaitMsg] = useState<string | null>(null)
  const [waitErr, setWaitErr] = useState<string | null>(null)
  const [quality, setQuality] = useState<QualitySummary | null>(null)

  useEffect(() => {
    let cancelled = false
    void api
      .getQualityGates()
      .then((data) => {
        if (!cancelled) setQuality(data.summary)
      })
      .catch(() => {
        if (!cancelled) setQuality(null)
      })
    return () => {
      cancelled = true
    }
  }, [])

  async function startDemo(role: 'teacher' | 'parent' | 'student' = demoRole) {
    setBusy(true)
    setError(null)
    try {
      const demo = await api.createDemoSession('math_5_1')
      window.location.href = demo.links[role]
    } catch (err) {
      const detail = err instanceof Error ? err.message : '演示创建失败'
      setError(`演示创建失败：${detail}。请确认 API 已启动（默认 :8000），或稍后重试。`)
      setBusy(false)
    }
  }

  async function submitWaitlist() {
    setWaitBusy(true)
    setWaitErr(null)
    setWaitMsg(null)
    try {
      await api.submitWaitlist({ email: waitEmail, role: waitRole })
      setWaitMsg('已加入早鸟候补，我们会在开放试点时联系你。')
      setWaitEmail('')
    } catch (err) {
      setWaitErr(err instanceof Error ? err.message : '提交失败')
    } finally {
      setWaitBusy(false)
    }
  }

  return (
    <main className="landing-page">
      <header className="landing-header">
        <div className="landing-brand-block">
          <p className="landing-kicker">课标在环 · 多 Agent 协同</p>
          <p className="landing-brand">ILearn</p>
        </div>
        <p className="landing-meta">
          LOVE LEARN · I LEARN
          <br />
          SOFT LAUNCH
        </p>
      </header>
      <div className="landing-grid">
        <section className="landing-hero" aria-labelledby="landing-title">
          <p className="landing-index">/ 00 · START HERE</p>
          <p className="pilot-badge" aria-label="试点范围">
            试点 · 北京·人教 · 小学数学 4–6 年级
          </p>
          <h1 id="landing-title">敢给孩子用的证据化学习闭环</h1>
          <p className="landing-lede">
            学生敢问敢练（不泄终答）、家长今晚能陪、教师布置能办完。课标可追溯，掌握度有证据——不是搜题器。
            试点：小学数学四至六年级 · 北京·人教。
          </p>
          <ul className="landing-promise" aria-label="产品承诺">
            <li>掌握度进步优先于刷题量</li>
            <li>课标可追溯 · 证据化诊断</li>
            <li>苏格拉底护栏（不直接给终答）</li>
          </ul>
          <p className="quality-gate-strip" aria-label="质量门摘要">
            {quality
              ? `质量门已强制 ${quality.enforced}/${quality.total} 项`
              : '质量门状态加载中…'}
            {' · '}
            <a href="?trust=1">查看可审计信任说明</a>
            {' · 三角色演示 ≤2 次点击见证据'}
          </p>
        </section>
        <nav className="role-cards" aria-label="选择学习角色">
          <p className="landing-index">/ 01 · CHOOSE ROLE</p>
          {roleCards.map((card) => (
            <button
              type="button"
              className={`role-card role-card-${card.role}`}
              key={card.role}
              disabled={busy}
              onClick={() => {
                if (card.role === 'student') {
                  window.location.href = '?student=1'
                  return
                }
                void startDemo(card.role)
              }}
            >
              <span className="role-card-marker">{card.index}</span>
              <span className="role-card-title">{card.title}</span>
              <span className="role-card-description">{card.description}</span>
              <span className="role-card-arrow" aria-hidden="true">
                {card.role === 'student' ? '↗' : '一键体验'}
              </span>
            </button>
          ))}
          <p className="lede">
            已有账号？
            <a href="?login=1&role=parent">家长登录</a>
            {' · '}
            <a href="?login=1&role=teacher">教师登录</a>
          </p>
        </nav>
      </div>
      <section className="workflow-strip" aria-labelledby="workflow-title">
        <p className="landing-index">/ 02 · HOW IT WORKS</p>
        <h2 id="workflow-title">学习如何向前</h2>
        <ol>
          <li>
            <strong className="workflow-step">诊断</strong>
            <span className="workflow-detail">课标约束组卷，识别掌握缺口</span>
          </li>
          <li>
            <strong className="workflow-step">计划</strong>
            <span className="workflow-detail">生成可追溯的下一步路径</span>
          </li>
          <li>
            <strong className="workflow-step">巩固</strong>
            <span className="workflow-detail">证据化掌握度，报告可带走</span>
          </li>
        </ol>
      </section>
      <section className="demo-unit" aria-labelledby="demo-unit-title">
        <p className="landing-index">/ 03 · DEMO UNIT</p>
        <h2 id="demo-unit-title">体验完整教学单元</h2>
        <article className="demo-card">
          <span className="demo-card-marker">01</span>
          <div>
            <p className="demo-card-kicker">人教 · 五年级</p>
            <h3 className="demo-card-title">小数乘法</h3>
            <p className="demo-card-description">
              选角色后一键进入：≤2 次点击见到掌握度 / 行动摘要 / 分层布置证据之一。
            </p>
          </div>
          <div role="radiogroup" aria-label="演示角色">
            {(['teacher', 'parent', 'student'] as const).map((role) => (
              <label key={role}>
                <input
                  type="radio"
                  name="demo-role"
                  value={role}
                  checked={demoRole === role}
                  onChange={() => setDemoRole(role)}
                />
                {role === 'teacher' ? '教师' : role === 'parent' ? '家长' : '学生'}
              </label>
            ))}
          </div>
          <button
            className="btn"
            type="button"
            onClick={() => void startDemo()}
            disabled={busy}
          >
            体验小数乘法
          </button>
          {error ? (
            <p className="error" role="alert">
              {error}
            </p>
          ) : null}
        </article>
      </section>
      <section className="waitlist-strip" aria-labelledby="waitlist-title">
        <p className="landing-index">/ 04 · EARLY ACCESS</p>
        <h2 id="waitlist-title">加入早鸟候补</h2>
        <p className="landing-lede">家庭试点与教师试用即将开放。留下邮箱，我们只用于开放通知。</p>
        <form
          className="waitlist-form"
          onSubmit={(e) => {
            e.preventDefault()
            void submitWaitlist()
          }}
        >
          <label>
            邮箱
            <input
              type="email"
              name="email"
              required
              value={waitEmail}
              onChange={(e) => setWaitEmail(e.target.value)}
              placeholder="you@example.com"
              autoComplete="email"
            />
          </label>
          <label>
            身份
            <select
              name="role"
              value={waitRole}
              onChange={(e) => setWaitRole(e.target.value as 'parent' | 'teacher' | 'other')}
            >
              <option value="parent">家长</option>
              <option value="teacher">教师</option>
              <option value="other">其他</option>
            </select>
          </label>
          <button className="btn" type="submit" disabled={waitBusy || !waitEmail.trim()}>
            {waitBusy ? '提交中…' : '加入候补'}
          </button>
        </form>
        {waitMsg ? (
          <p role="status" className="waitlist-ok">
            {waitMsg}
          </p>
        ) : null}
        {waitErr ? (
          <p className="error" role="alert">
            {waitErr}
          </p>
        ) : null}
      </section>
      <footer className="landing-footer">
        <a href="?privacy=1">隐私与能力边界</a>
        <span aria-hidden="true"> · </span>
        <a href="?trust=1">可审计信任说明</a>
        <span aria-hidden="true"> · </span>
        <span>不是搜题器 · 不拍照出答案 · 不直接给终答 · 试点学段诚实标注</span>
      </footer>
    </main>
  )
}
