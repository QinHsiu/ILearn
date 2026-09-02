import { useEffect, useState } from 'react'
import type { FormEvent } from 'react'
import { dashboardApi } from '../api/client'
import type {
  DashboardClassSummary,
  DashboardStudentDetail,
  DashboardStudentSummary,
  TeacherSummary,
} from '../api/client'
import { api } from '../api/client'
import DashboardDetail from '../components/DashboardDetail'
import EffectivenessDashboard from '../components/EffectivenessDashboard'
import StudentList from '../components/StudentList'
import DashboardHome, { updateDashboardQuery } from './DashboardHome'

type TeacherDashboardProps = { userId: string; classId?: string; studentId?: string }

type TeacherTab = 'scan' | 'overview' | 'students' | 'detail'

export default function TeacherDashboard({ userId, classId: initialClassId, studentId }: TeacherDashboardProps) {
  const [classes, setClasses] = useState<DashboardClassSummary[] | null>(null)
  const [classId, setClassId] = useState(initialClassId || '')
  const [students, setStudents] = useState<DashboardStudentSummary[] | null>(null)
  const [selected, setSelected] = useState<DashboardStudentDetail | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [bindSessionId, setBindSessionId] = useState('')
  const [selectedStudentId, setSelectedStudentId] = useState(studentId || '')
  const [classMetrics, setClassMetrics] = useState<TeacherSummary | null>(null)
  const [activeTab, setActiveTab] = useState<TeacherTab>('scan')

  useEffect(() => {
    if (!selected?.session_id) {
      setClassMetrics(null)
      return
    }
    let cancelled = false
    void api.getTeacherSummary(selected.session_id).then((data) => {
      if (!cancelled) setClassMetrics(data)
    }).catch(() => {
      if (!cancelled) setClassMetrics(null)
    })
    return () => {
      cancelled = true
    }
  }, [selected?.session_id])

  useEffect(() => {
    void dashboardApi.teacherClasses(userId).then(setClasses).catch((err) => {
      setError(err instanceof Error ? err.message : String(err))
      setClasses([])
    })
  }, [userId])

  useEffect(() => {
    if (initialClassId && classes?.some((item) => item.class_id === initialClassId)) {
      selectClass(initialClassId)
    }
  }, [classes, initialClassId])

  function selectClass(id: string) {
    setClassId(id)
    setSelected(null)
    setActiveTab('scan')
    updateDashboardQuery({ class_id: id, student_id: null })
    void dashboardApi.teacherStudents(userId, id).then((next) => {
      setStudents(next)
      const target = studentId ? next.find((student) => student.session_id === studentId) : undefined
      if (target) selectStudent(id, target)
    }).catch((err) => setError(err instanceof Error ? err.message : String(err)))
  }

  function selectStudent(id: string, student: DashboardStudentSummary) {
    setSelectedStudentId(student.session_id)
    setActiveTab('detail')
    updateDashboardQuery({ student_id: student.session_id })
    void dashboardApi.teacherStudent(userId, id, student.session_id).then(setSelected).catch((err) => {
      setError(err instanceof Error ? err.message : String(err))
    })
  }

  async function bind(e: FormEvent) {
    e.preventDefault()
    if (!classId || !bindSessionId.trim()) return
    try {
      await dashboardApi.bindTeacher(userId, classId, bindSessionId.trim())
      setBindSessionId('')
      selectClass(classId)
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err))
    }
  }

  return (
    <DashboardHome title="老师端 / CLASS STUDIO">
      <main className="dashboard-content teacher-content">
        <section className="dashboard-role-intro teacher-surface">
          <p className="dashboard-section-label">02 / CLASS STUDIO</p>
          <h1>班级整体哪里需要干预，应该先看谁？</h1>
          <p>先扫描班级，再定位学生；用掌握度、薄弱知识点和阶段信息安排行动。</p>
        </section>

        {classMetrics ? (
          <section className="teacher-metric-cards" aria-label="班级核心指标">
            <article className="metric-card">
              <span>班级平均掌握度</span>
              <strong>{Math.round(classMetrics.avg_mastery * 100)}%</strong>
            </article>
            <article className="metric-card metric-card-alert">
              <span>需干预学生</span>
              <strong>{classMetrics.need_intervention_students.length}人</strong>
            </article>
            <article className="metric-card">
              <span>节省批改时间</span>
              <strong>{Math.round(classMetrics.estimated_time_saved_minutes)}分钟</strong>
            </article>
            <article className="metric-card">
              <span>自动批改率</span>
              <strong>{Math.round(classMetrics.auto_graded_rate * 100)}%</strong>
            </article>
          </section>
        ) : null}

        {classId && classMetrics ? (
          <nav className="teacher-tabs" aria-label="教师工作台视图">
            {[
              { key: 'scan' as TeacherTab, label: '班级扫描' },
              { key: 'overview' as TeacherTab, label: '班级总览' },
              { key: 'students' as TeacherTab, label: '学生干预' },
              { key: 'detail' as TeacherTab, label: '学情详情' },
            ].map((tab) => (
              <button
                key={tab.key}
                type="button"
                className={`teacher-tab${activeTab === tab.key ? ' is-active' : ''}`}
                onClick={() => setActiveTab(tab.key)}
              >
                {tab.label}
              </button>
            ))}
          </nav>
        ) : null}

        {activeTab === 'scan' || !classMetrics ? (
          <section className="panel dashboard-panel teacher-operations">
            <h2>班级扫描</h2>
            {classes === null ? <p>加载中…</p> : classes.length ? (
              <div className="class-list">
                {classes.map((item) => (
                  <button
                    className="btn secondary dashboard-entry-card"
                    key={item.class_id}
                    type="button"
                    onClick={() => selectClass(item.class_id)}
                  >
                    <span>班级 {item.class_id}</span>
                    <small>
                      <span>{item.students.length} 名学生</span>
                      <span aria-hidden="true"> · </span>
                      <span>状态：{item.students.length ? '已绑定' : '暂无学生'}</span>
                    </small>
                  </button>
                ))}
              </div>
            ) : <p className="dashboard-empty">暂无班级数据</p>}
            {classId && students ? (
              <StudentList
                students={students}
                selectedId={selectedStudentId}
                onSelect={(student) => selectStudent(classId, student)}
              />
            ) : null}
            {error ? <p className="error dashboard-error" role="alert" aria-live="polite">{error}</p> : null}
            <form className="dashboard-bind" onSubmit={(e) => void bind(e)}>
              <label htmlFor="teacher-session">绑定学生会话</label>
              <input id="teacher-session" value={bindSessionId} onChange={(e) => setBindSessionId(e.target.value)} />
              <button className="btn" type="submit">绑定学生并刷新</button>
            </form>
          </section>
        ) : null}

        {activeTab === 'overview' && classMetrics ? (
          <section className="teacher-overview-grid panel">
            <article className="teacher-overview-card">
              <h2>班级薄弱点排行</h2>
              {classMetrics.top_weaknesses.length ? (
                <ol className="weakness-rank-list">
                  {classMetrics.top_weaknesses.map((row, index) => (
                    <li key={`${row.skill}-${index}`}>
                      <span className="weakness-rank">{index + 1}</span>
                      <span className="weakness-skill">{row.skill}</span>
                      <span className="weakness-count">{row.affected_students} 人薄弱</span>
                    </li>
                  ))}
                </ol>
              ) : (
                <p className="dashboard-empty">暂无薄弱点数据</p>
              )}
            </article>
            <article className="teacher-overview-card">
              <h2>班级掌握度概览</h2>
              <p className="lede">
                平均掌握度 {Math.round(classMetrics.avg_mastery * 100)}%，自动批改率{' '}
                {Math.round(classMetrics.auto_graded_rate * 100)}%。
              </p>
              {classMetrics.narrative ? <p>{classMetrics.narrative}</p> : null}
            </article>
          </section>
        ) : null}

        {activeTab === 'students' && classMetrics ? (
          <section className="panel teacher-intervention-panel">
            <h2>需要干预的学生</h2>
            {classMetrics.need_intervention_students.length ? (
              <ul className="intervention-list">
                {classMetrics.need_intervention_students.map((student) => (
                  <li key={`${student.session_id}-${student.name}`} className="intervention-row">
                    <div>
                      <strong>{student.name}</strong>
                      <span>薄弱：{student.weakness}</span>
                    </div>
                    <button
                      className="btn secondary"
                      type="button"
                      onClick={() => {
                        const match = students?.find((s) => s.session_id === student.session_id)
                        if (match && classId) selectStudent(classId, match)
                      }}
                    >
                      查看学情
                    </button>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="dashboard-empty">当前无需特殊干预</p>
            )}
          </section>
        ) : null}

        {activeTab === 'detail' && selected ? (
          <>
            <DashboardDetail detail={selected} surface="teacher" />
            {selected.metadata?.demo_unit ? (
              <section className="panel teacher-effectiveness-panel">
                <h2>教学效果验证</h2>
                <EffectivenessDashboard sessionId={selected.session_id} />
              </section>
            ) : null}
          </>
        ) : null}
      </main>
    </DashboardHome>
  )
}
