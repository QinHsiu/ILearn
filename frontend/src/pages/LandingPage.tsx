import type { AuthRole } from '../api/client'

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
  return (
    <main className="landing-page">
      <header className="landing-header">
        <div>
          <p className="eyebrow">ILearn / ROLE SURFACES</p>
          <p className="landing-kicker">课标在环的个性化学习向导</p>
        </div>
        <p className="landing-meta">PRECISION LEARNING<br />EDITION 01</p>
      </header>
      <div className="landing-grid">
        <section className="landing-hero" aria-labelledby="landing-title">
          <p className="landing-index">/ 00 · START HERE</p>
          <h1 id="landing-title">把学习看清楚，<br />再决定下一步</h1>
          <p className="landing-lede">
            ILearn 将诊断、计划与反馈连成一条可追踪的学习路径。
            请选择最适合你的入口。
          </p>
        </section>
        <nav className="role-cards" aria-label="选择学习角色">
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
        <h2 id="workflow-title">学习如何向前</h2>
        <ol>
          <li><span>诊断 — 识别知识点掌握情况</span></li>
          <li><span>计划 — 生成下一步学习路径</span></li>
          <li><span>反馈 — 根据练习结果持续调整</span></li>
        </ol>
      </section>
    </main>
  )
}
