import type { DashboardStudentSummary } from '../api/client'

type StudentListProps = {
  students: DashboardStudentSummary[]
  selectedId?: string
  onSelect: (student: DashboardStudentSummary) => void
}

export default function StudentList({ students, selectedId, onSelect }: StudentListProps) {
  if (!students.length) return <p className="dashboard-empty">暂无学生数据</p>
  return (
    <div className="student-list" aria-label="学生列表">
      {students.map((student) => (
        <button
          className={`student-card${student.session_id === selectedId ? ' selected' : ''}`}
          key={student.session_id}
          type="button"
          onClick={() => onSelect(student)}
        >
          <strong>{student.nickname || '未命名学生'}</strong>
          <span>{student.grade} 年级 · {student.phase}</span>
          <span>掌握率 {Math.round(student.overall_mastery * 100)}%</span>
          <span>薄弱知识点：{student.weak_skills.length ? student.weak_skills.join('、') : '暂无'}</span>
        </button>
      ))}
    </div>
  )
}
