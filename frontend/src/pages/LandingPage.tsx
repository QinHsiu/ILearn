import type { AuthRole } from '../api/client'

const roleCards: Array<{ role: AuthRole; title: string; description: string }> = [
  { role: 'parent', title: '家长登录', description: '查看孩子的学习诊断与计划' },
  { role: 'teacher', title: '老师登录', description: '查看班级与学生学习情况' },
]

export default function LandingPage() {
  return (
    <main className="landing-page">
      <p className="eyebrow">ILearn</p>
      <h1>欢迎来到 ILearn</h1>
      <p className="landing-lede">课标在环的个性化学习向导</p>
      <div className="role-cards">
        {roleCards.map((card) => (
          <a
            className="role-card"
            href={`?login=1&role=${card.role}`}
            key={card.role}
          >
            <span className="role-card-title">{card.title}</span>
            <span className="role-card-description">{card.description}</span>
          </a>
        ))}
      </div>
    </main>
  )
}
