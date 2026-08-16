import { useEffect, useState } from 'react'
import type { FormEvent } from 'react'
import { dashboardApi } from '../api/client'
import type { DashboardStudentDetail, DashboardStudentSummary } from '../api/client'
import DashboardDetail from '../components/DashboardDetail'
import StudentList from '../components/StudentList'
import DashboardHome, { updateDashboardQuery } from './DashboardHome'

type ParentDashboardProps = { userId: string; studentId?: string }

const phaseLabels: Record<string, string> = {
  profile: '资料待完成',
  assessing: '诊断进行中',
  diagnosed: '已完成诊断',
  planning: '学习计划生成中',
  planned: '学习计划已生成',
}

export default function ParentDashboard({ userId, studentId }: ParentDashboardProps) {
  const [students, setStudents] = useState<DashboardStudentSummary[] | null>(null)
  const [selected, setSelected] = useState<DashboardStudentDetail | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [sessionId, setSessionId] = useState('')
  const [selectedSessionId, setSelectedSessionId] = useState(studentId || '')

  const load = () => {
    setError(null)
    void dashboardApi.parentChildren(userId).then(setStudents).catch((err) => {
      setError(err instanceof Error ? err.message : String(err))
      setStudents([])
    })
  }

  useEffect(load, [userId])

  useEffect(() => {
    const target = studentId && students?.find((student) => student.session_id === studentId)
    if (target) selectStudent(target)
  }, [studentId, students])

  const summaryStudent = students?.find((student) => student.session_id === selectedSessionId)
    || students?.[0]

  function selectStudent(student: DashboardStudentSummary) {
    setSessionId(student.session_id)
    setSelectedSessionId(student.session_id)
    setSelected(null)
    updateDashboardQuery({ student_id: student.session_id })
    void dashboardApi.parentChild(userId, student.session_id).then(setSelected).catch((err) => {
      setError(err instanceof Error ? err.message : String(err))
    })
  }

  async function bind(e: FormEvent) {
    e.preventDefault()
    if (!sessionId.trim()) return
    try {
      await dashboardApi.bindParent(userId, sessionId.trim())
      setSessionId('')
      load()
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err))
    }
  }

  return (
    <DashboardHome title="家长端 / CHILD GROWTH">
      <main className="dashboard-content parent-content">
        <section className="dashboard-role-intro parent-surface">
          <p className="dashboard-section-label">01 / CHILD GROWTH</p>
          <h1>孩子最近学得怎么样，下一步怎么支持？</h1>
          <p>从当前掌握度、薄弱知识点和学习阶段开始，给出具体支持。</p>
        </section>
        {summaryStudent ? (
          <section className="parent-summary" aria-labelledby="parent-summary-title">
            <h2 id="parent-summary-title">事实摘要</h2>
            <div className="summary-grid">
              <article className="summary-block">
                <span>当前掌握度</span>
                <strong>{Math.round(summaryStudent.overall_mastery * 100)}%</strong>
              </article>
              <article className="summary-block">
                <span>薄弱知识点</span>
                <strong>{summaryStudent.weak_skills.length ? summaryStudent.weak_skills.join('、') : '暂无'}</strong>
              </article>
              <article className="summary-block">
                <span>学习阶段</span>
                <strong>{phaseLabels[summaryStudent.phase] || summaryStudent.phase}</strong>
              </article>
            </div>
          </section>
        ) : null}
        <section className="panel dashboard-panel parent-operations">
          <h2>孩子学习概览</h2>
          {students === null ? <p>加载中…</p> : (
            <>
              <StudentList
                students={students}
                selectedId={selectedSessionId}
                onSelect={selectStudent}
              />
              {!students.length ? (
                <p className="dashboard-empty-state">
                  还没有绑定学生，绑定学习会话后即可查看学习进度。
                </p>
              ) : null}
            </>
          )}
          {error ? <p className="error dashboard-error" role="alert" aria-live="polite">{error}</p> : null}
          <form className="dashboard-bind" onSubmit={(e) => void bind(e)}>
            <label htmlFor="parent-session">绑定学习会话</label>
            <input id="parent-session" value={sessionId} onChange={(e) => setSessionId(e.target.value)} />
            <button className="btn" type="submit">绑定学生并刷新</button>
          </form>
        </section>
        {selected ? <DashboardDetail detail={selected} surface="parent" /> : null}
      </main>
    </DashboardHome>
  )
}
