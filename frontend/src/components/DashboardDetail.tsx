import type { DashboardStudentDetail, DemoClassData } from '../api/client'
import MarkdownView from '../MarkdownView'
import EffectivenessDashboard from './EffectivenessDashboard'

type DashboardDetailProps = {
  detail: DashboardStudentDetail
  surface?: 'parent' | 'teacher'
}

const DEMO_UNIT_NAMES: Record<string, string> = {
  math_5_1: '小数乘法',
}

function demoUnitId(detail: DashboardStudentDetail): string | null {
  const unit = detail.metadata?.demo_unit
  return typeof unit === 'string' && unit ? unit : null
}

function demoClassData(detail: DashboardStudentDetail): DemoClassData | null {
  const raw = detail.metadata?.demo_class_data
  if (!raw || typeof raw !== 'object') return null
  return raw
}

export default function DashboardDetail({ detail, surface = 'teacher' }: DashboardDetailProps) {
  const mastery = detail.diagnosis?.knowledge_mastery || []
  const unitId = demoUnitId(detail)
  const classData = unitId ? demoClassData(detail) : null
  const enrichment = detail.metadata?.diagnosis_enrichment
  const unitName = unitId ? DEMO_UNIT_NAMES[unitId] || unitId : null

  return (
    <section className="dashboard-detail panel">
      <h2>{detail.profile.nickname || '学生'}的学习详情</h2>
      <p className="lede">
        {detail.profile.grade} 年级 · 阶段：{detail.phase} · 巩固轮次：{detail.loop_count}
      </p>
      {unitId && surface === 'teacher' ? (
        <div className="demo-class-panel">
          <h3>备课概览</h3>
          <p className="demo-unit-name">{unitName}</p>
          {classData ? (
            <div className="summary-grid demo-class-stats">
              {classData.class_size != null ? (
                <article className="summary-block">
                  <span>班级人数</span>
                  <strong>{classData.class_size}</strong>
                </article>
              ) : null}
              {classData.avg_mastery != null ? (
                <article className="summary-block">
                  <span>平均掌握度</span>
                  <strong>{Math.round(classData.avg_mastery * 100)}%</strong>
                </article>
              ) : null}
              {classData.common_weaknesses?.length ? (
                <article className="summary-block">
                  <span>共性薄弱点</span>
                  <strong>{classData.common_weaknesses.join('、')}</strong>
                </article>
              ) : null}
            </div>
          ) : null}
          {classData?.mastery_distribution?.length ? (
            <p className="demo-distribution" aria-label="班级掌握度分布">
              班级分布：{classData.mastery_distribution.join(' / ')}
            </p>
          ) : null}
          <h3>教师工作量</h3>
          <EffectivenessDashboard sessionId={detail.session_id} />
        </div>
      ) : null}
      {unitId && surface === 'parent' ? (
        <div className="parent-demo-panel">
          <h3>家庭辅导建议</h3>
          {enrichment?.parent_summary ? <p>{enrichment.parent_summary}</p> : null}
          {enrichment?.learning_advice ? (
            <p className="parent-demo-tip">{enrichment.learning_advice}</p>
          ) : null}
        </div>
      ) : null}
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
