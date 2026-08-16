import { useEffect, useState } from 'react'
import type { FormEvent } from 'react'
import { dashboardApi } from '../api/client'
import type {
  DashboardClassSummary,
  DashboardStudentDetail,
  DashboardStudentSummary,
} from '../api/client'
import DashboardDetail from '../components/DashboardDetail'
import StudentList from '../components/StudentList'
import DashboardHome, { updateDashboardQuery } from './DashboardHome'

type TeacherDashboardProps = { userId: string; classId?: string; studentId?: string }

export default function TeacherDashboard({ userId, classId: initialClassId, studentId }: TeacherDashboardProps) {
  const [classes, setClasses] = useState<DashboardClassSummary[] | null>(null)
  const [classId, setClassId] = useState(initialClassId || '')
  const [students, setStudents] = useState<DashboardStudentSummary[] | null>(null)
  const [selected, setSelected] = useState<DashboardStudentDetail | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [bindSessionId, setBindSessionId] = useState('')
  const [selectedStudentId, setSelectedStudentId] = useState(studentId || '')

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
    updateDashboardQuery({ class_id: id, student_id: null })
    void dashboardApi.teacherStudents(userId, id).then((next) => {
      setStudents(next)
      const target = studentId ? next.find((student) => student.session_id === studentId) : undefined
      if (target) selectStudent(id, target)
    }).catch((err) => setError(err instanceof Error ? err.message : String(err)))
  }

  function selectStudent(id: string, student: DashboardStudentSummary) {
    setSelectedStudentId(student.session_id)
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
        <section className="panel dashboard-panel teacher-operations">
          <h2>班级扫描</h2>
          {classes === null ? <p>加载中…</p> : classes.length ? (
            <div className="class-list">
              {classes.map((item) => (
                <button className="btn secondary dashboard-entry-card" key={item.class_id} type="button" onClick={() => selectClass(item.class_id)}>
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
        {selected ? <DashboardDetail detail={selected} /> : null}
      </main>
    </DashboardHome>
  )
}
