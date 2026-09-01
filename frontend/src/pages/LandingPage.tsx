import { useState } from 'react'
import { api, type AuthRole } from '../api/client'

const roleCards: Array<{
  role: AuthRole | 'student'
  index: string
  title: string
  description: string
  href: string
}> = [
  {
    role: 'parent',
    index: '01',
    title: '家长端 · 孩子成长',
    description: '看懂孩子当前掌握情况，找到下一步支持方式',
    href: '?login=1&role=parent',
  },
  {
    role: 'teacher',
    index: '02',
    title: '老师端 · 班级运营',
    description: '扫描班级整体状态，优先查看需要干预的学生',
    href: '?login=1&role=teacher',
  },
  {
    role: 'student',
    index: '03',
    title: '学生端 · 下一步学习',
    description: '完成诊断，获得清晰可执行的学习路径',
    href: '?student=1',
  },
]

export default function LandingPage() {
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [demoRole, setDemoRole] = useState<'teacher' | 'parent' | 'student'>('teacher')

  async function startDemo() {
    setBusy(true)
    setError(null)
    try {
      const demo = await api.createDemoSession('math_5_1')
      window.location.href = demo.links[demoRole]
    } catch (err) {
      setError(err instanceof Error ? err.message : '演示创建失败')
      setBusy(false)
    }
  }

  return (
    <main className="landing-page">
      <header className="landing-header">
        <div className="landing-brand-block">
          <p className="landing-kicker">课标在环 · ROLE SURFACES</p>
          <p className="landing-brand">ILearn</p>
        </div>
        <p className="landing-meta">PRECISION LEARNING<br />EDITION 01</p>
      </header>
      <div className="landing-grid">
        <section className="landing-hero" aria-labelledby="landing-title">
          <p className="landing-index">/ 00 · START HERE</p>
          <h1 id="landing-title">把学习看清楚，<br />再决定下一步</h1>
          <p className="landing-lede">
            诊断、计划与反馈连成一条可追踪的学习路径。
            请选择最适合你的入口。
          </p>
        </section>
        <nav className="role-cards" aria-label="选择学习角色">
          <p className="landing-index">/ 01 · CHOOSE ROLE</p>
        {roleCards.map((card) => (
          <a
            className={`role-card role-card-${card.role}`}
            href={card.href}
            key={card.role}
          >
            <span className="role-card-marker">{card.index}</span>
            <span className="role-card-title">{card.title}</span>
            <span className="role-card-description">{card.description}</span>
            <span className="role-card-arrow" aria-hidden="true">↗</span>
          </a>
        ))}
        </nav>
      </div>
      <section className="workflow-strip" aria-labelledby="workflow-title">
        <p className="landing-index">/ 02 · HOW IT WORKS</p>
        <h2 id="workflow-title">学习如何向前</h2>
        <ol>
          <li>
            <strong className="workflow-step">诊断</strong>
            <span className="workflow-detail">识别知识点掌握情况</span>
          </li>
          <li>
            <strong className="workflow-step">计划</strong>
            <span className="workflow-detail">生成下一步学习路径</span>
          </li>
          <li>
            <strong className="workflow-step">反馈</strong>
            <span className="workflow-detail">根据练习结果持续调整</span>
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
              一键进入已预置诊断、计划与班级数据的闭环演示。
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
    </main>
  )
}
