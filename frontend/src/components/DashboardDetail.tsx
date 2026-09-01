import { useEffect, useState } from 'react'
import type {
  DashboardStudentDetail,
  DemoClassData,
  ParentSummary,
  TeacherSummary,
} from '../api/client'
import { api } from '../api/client'
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
  const [teacherSummary, setTeacherSummary] = useState<TeacherSummary | null>(null)
  const [parentSummary, setParentSummary] = useState<ParentSummary | null>(null)
  const [summaryLoad, setSummaryLoad] = useState<'idle' | 'loading' | 'ready' | 'error'>('idle')

  useEffect(() => {
    setTeacherSummary(null)
    setParentSummary(null)
    if (!detail.session_id) {
      setSummaryLoad('idle')
      return
    }
    setSummaryLoad('loading')
    let cancelled = false
    const request =
      surface === 'teacher'
        ? api.getTeacherSummary(detail.session_id).then((data) => {
            if (cancelled) return
            setTeacherSummary(data)
            setSummaryLoad('ready')
          })
        : api.getParentSummary(detail.session_id).then((data) => {
            if (cancelled) return
            setParentSummary(data)
            setSummaryLoad('ready')
          })
    void request.catch(() => {
      if (cancelled) return
      setTeacherSummary(null)
      setParentSummary(null)
      setSummaryLoad('error')
    })
    return () => {
      cancelled = true
    }
  }, [detail.session_id, surface])

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
      {surface === 'teacher' && teacherSummary ? (
        <div className="structured-summary-panel">
          <h3>结构化备课摘要</h3>
          <p>
            {teacherSummary.class_name} · {teacherSummary.student_count} 名学生
          </p>
          {teacherSummary.top_weaknesses.length ? (
            <ul>
              {teacherSummary.top_weaknesses.map((row) => (
                <li key={row.skill}>
                  {row.skill}（{row.affected_students}人薄弱）
                </li>
              ))}
            </ul>
          ) : null}
          {teacherSummary.need_intervention_students.length ? (
            <ul>
              {teacherSummary.need_intervention_students.map((student) => (
                <li key={`${student.session_id}-${student.name}`}>
                  {student.name}：{student.weakness}
                </li>
              ))}
            </ul>
          ) : null}
          {teacherSummary.narrative ? <p>{teacherSummary.narrative}</p> : null}
        </div>
      ) : null}
      {unitId && surface === 'parent' && summaryLoad === 'error' ? (
        <div className="parent-demo-panel">
          <h3>家庭辅导建议</h3>
          {enrichment?.parent_summary ? <p>{enrichment.parent_summary}</p> : null}
          {enrichment?.learning_advice ? (
            <p className="parent-demo-tip">{enrichment.learning_advice}</p>
          ) : null}
        </div>
      ) : null}
      {surface === 'parent' && parentSummary ? (
        <div className="structured-summary-panel">
          <h3>结构化家庭摘要</h3>
          <div className="summary-grid">
            <article className="summary-block">
              <span>当前掌握度</span>
              <strong>{Math.round(parentSummary.current_mastery * 100)}%</strong>
            </article>
            <article className="summary-block">
              <span>掌握度变化</span>
              <strong>
                {parentSummary.mastery_change >= 0 ? '+' : ''}
                {Math.round(parentSummary.mastery_change * 100)}%
              </strong>
            </article>
          </div>
          {parentSummary.daily_practice_tips.length ? (
            <ul>
              {parentSummary.daily_practice_tips.map((tip) => (
                <li key={tip}>{tip}</li>
              ))}
            </ul>
          ) : null}
          <p>下一步里程碑：{parentSummary.next_milestone}</p>
          {parentSummary.narrative ? <p>{parentSummary.narrative}</p> : null}
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
