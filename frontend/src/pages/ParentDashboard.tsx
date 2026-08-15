import { useEffect, useState } from 'react'
import type { FormEvent } from 'react'
import { dashboardApi } from '../api/client'
import type { DashboardStudentDetail, DashboardStudentSummary } from '../api/client'
import DashboardDetail from '../components/DashboardDetail'
import StudentList from '../components/StudentList'
import DashboardHome, { updateDashboardQuery } from './DashboardHome'

type ParentDashboardProps = { userId: string; studentId?: string }

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

  function selectStudent(student: DashboardStudentSummary) {
    setSessionId(student.session_id)
    setSelectedSessionId(student.session_id)
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
    <DashboardHome title="家长端">
      <main className="dashboard-content">
        <section className="panel">
          <h2>孩子学习概览</h2>
          {students === null ? <p>加载中…</p> : (
            <StudentList
              students={students}
              selectedId={selectedSessionId}
              onSelect={selectStudent}
            />
          )}
          {error ? <p className="error">{error}</p> : null}
          <form className="dashboard-bind" onSubmit={(e) => void bind(e)}>
            <label htmlFor="parent-session">绑定学习会话</label>
            <input id="parent-session" value={sessionId} onChange={(e) => setSessionId(e.target.value)} />
            <button className="btn" type="submit">绑定并刷新</button>
          </form>
        </section>
        {selected ? <DashboardDetail detail={selected} /> : null}
      </main>
    </DashboardHome>
  )
}
