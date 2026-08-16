import type { DashboardStudentDetail } from '../api/client'
import MarkdownView from '../MarkdownView'

type DashboardDetailProps = {
  detail: DashboardStudentDetail
  surface?: 'parent' | 'teacher'
}

export default function DashboardDetail({ detail, surface = 'teacher' }: DashboardDetailProps) {
  const mastery = detail.diagnosis?.knowledge_mastery || []
  return (
    <section className="dashboard-detail panel">
      <h2>{detail.profile.nickname || '学生'}的学习详情</h2>
      <p className="lede">
        {detail.profile.grade} 年级 · 阶段：{detail.phase} · 巩固轮次：{detail.loop_count}
      </p>
      <h3>知识点掌握</h3>
      {mastery.length ? (
        <div className="dashboard-skills">
          {mastery.map((skill) => (
            <div className="dashboard-skill" key={skill.knowledge_id}>
              <span>{skill.knowledge_name || skill.knowledge_id}</span>
              <strong>{Math.round(skill.score_rate * 100)}%</strong>
              <span>{skill.level}</span>
            </div>
          ))}
        </div>
      ) : (
        <p className="dashboard-empty">暂无掌握度数据</p>
      )}
      <div className="dashboard-report">
        <h3>{surface === 'parent' ? '支持建议' : '学习报告'}</h3>
        <p>计划状态：{detail.plan?.status || '暂无'}</p>
        {detail.plan?.markdown ? <MarkdownView source={detail.plan.markdown} /> : <p>暂无报告内容</p>}
      </div>
    </section>
  )
}
