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
import ClassAssignmentTimeline from '../components/ClassAssignmentTimeline'
import type { ClassTimelineRow, CompletionSummary } from '../components/ClassAssignmentTimeline'
import DashboardDetail from '../components/DashboardDetail'
import EffectivenessDashboard from '../components/EffectivenessDashboard'
import SoftPdfButton from '../components/SoftPdfButton'
import UnlockRequestsPanel from '../components/UnlockRequestsPanel'
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
  const [assignReceipt, setAssignReceipt] = useState<string | null>(null)
  const [batchBusy, setBatchBusy] = useState(false)
  const [timeline, setTimeline] = useState<Array<Record<string, unknown>>>([])
  const [classTimeline, setClassTimeline] = useState<ClassTimelineRow[]>([])
  const [completionSummary, setCompletionSummary] = useState<CompletionSummary | null>(null)

  function loadTimeline(sessionId: string) {
    void api
      .getTierTimeline(sessionId)
      .then((data) => setTimeline(data.timeline || []))
      .catch(() => setTimeline([]))
  }

  function runTierAssign(sessionId: string) {
    void api
      .assignTierPapers(sessionId)
      .then((res) => {
        setError(null)
        const summary = Object.entries(res.item_counts)
          .map(([k, n]) => `${k}:${n}题`)
          .join(' · ')
        setAssignReceipt(`已布置 ${summary} · ${String((res.receipt as { assigned_at?: string }).assigned_at || '')}`)
        loadTimeline(sessionId)
        if (classId) loadClassTimeline(classId)
      })
      .catch((err) => setError(err instanceof Error ? err.message : String(err)))
  }

  function runBatchAssign(sessionIds?: string[]) {
    if (!classId) return
    setBatchBusy(true)
    setError(null)
    void dashboardApi
      .assignClassBatch(userId, classId, sessionIds?.length ? { session_ids: sessionIds } : {})
      .then((res) => {
        setAssignReceipt(res.summary)
        loadClassTimeline(classId)
      })
      .catch((err) => setError(err instanceof Error ? err.message : String(err)))
      .finally(() => setBatchBusy(false))
  }

  function loadClassMetrics(sessionId: string) {
    void api
      .getTeacherSummary(sessionId)
      .then((data) => {
        setClassMetrics(data)
        setError(null)
      })
      .catch(() => setClassMetrics(null))
    loadTimeline(sessionId)
  }

  useEffect(() => {
    if (selected?.session_id) {
      loadClassMetrics(selected.session_id)
      return
    }
    const first = students?.[0]?.session_id
    if (first) {
      loadClassMetrics(first)
      return
    }
    if (!classId) {
      setClassMetrics(null)
      setTimeline([])
    }
  }, [selected?.session_id, students, classId])

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

  function loadClassTimeline(id: string) {
    void dashboardApi
      .classAssignmentTimeline(userId, id)
      .then((data) => {
        setClassTimeline(data.timeline || [])
        setCompletionSummary(data.completion_summary || null)
      })
      .catch(() => {
        setClassTimeline([])
        setCompletionSummary(null)
      })
  }

  function selectClass(id: string) {
    setClassId(id)
    setSelected(null)
    setActiveTab('scan')
    updateDashboardQuery({ class_id: id, student_id: null })
    loadClassTimeline(id)
    void dashboardApi.teacherStudents(userId, id).then((next) => {
      setStudents(next)
      const target = studentId ? next.find((student) => student.session_id === studentId) : undefined
      if (target) selectStudent(id, target)
      else if (next.length) setActiveTab('overview')
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
    const code = bindSessionId.trim()
    if (!classId || !code) return
    try {
      if (code.length <= 8 && !code.includes('-')) {
        await dashboardApi.bindTeacherByCode(userId, classId, code)
      } else {
        await dashboardApi.bindTeacher(userId, classId, code)
      }
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

        {classMetrics?.tier_suggestion?.next_step ? (
          <section className="teacher-next-step panel" aria-labelledby="teacher-next-step-title">
            <h2 id="teacher-next-step-title">下一步行动</h2>
            <p className="lede">{classMetrics.tier_suggestion.next_step}</p>
            <ul className="tier-inline">
              <li>基础组 {classMetrics.tier_suggestion.basic.length} 人</li>
              <li>提高组 {classMetrics.tier_suggestion.advanced.length} 人</li>
              <li>挑战组 {classMetrics.tier_suggestion.challenge.length} 人</li>
            </ul>
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
              <label htmlFor="teacher-session">教师绑定码（6 位）</label>
              <input
                id="teacher-session"
                value={bindSessionId}
                onChange={(e) => setBindSessionId(e.target.value)}
                placeholder="例如 A3K9Q2"
                autoComplete="off"
              />
              <button className="btn" type="submit">用绑定码加入班级</button>
            </form>
            {classId && students?.length ? (
              <p>
                <SoftPdfButton
                  sessionId={students[0].session_id}
                  kind="grading-receipts"
                  label="导出班级批改回执 PDF"
                />
              </p>
            ) : null}
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
              {classMetrics.tier_suggestion ? (
                <div className="tier-suggestion">
                  <h3>下一步分层建议</h3>
                  <p>{classMetrics.tier_suggestion.next_step}</p>
                  <ul>
                    <li>基础组：{classMetrics.tier_suggestion.basic.join('、') || '—'}</li>
                    <li>提高组：{classMetrics.tier_suggestion.advanced.join('、') || '—'}</li>
                    <li>挑战组：{classMetrics.tier_suggestion.challenge.join('、') || '—'}</li>
                  </ul>
                  {classMetrics.tier_suggestion.assignment ? (
                    <div className="tier-assignment" aria-label="分层布置">
                      <h4>一键分层布置</h4>
                      <ul>
                        {(['basic', 'advanced', 'challenge'] as const).map((key) => {
                          const draft = classMetrics.tier_suggestion?.assignment?.[key]
                          if (!draft) return null
                          return (
                            <li key={key}>
                              {draft.title} · {draft.item_count} 题 · {draft.difficulty} · {draft.focus}
                            </li>
                          )
                        })}
                      </ul>
                      {selected?.session_id ? (
                        <button
                          type="button"
                          className="btn"
                          onClick={() => runTierAssign(selected.session_id)}
                        >
                          确认布置并生成回执
                        </button>
                      ) : null}
                      {assignReceipt ? (
                        <p className="lede" role="status">
                          回执：{assignReceipt}
                        </p>
                      ) : null}
                      {timeline.length > 0 ? (
                        <div className="tier-timeline" aria-label="布置回执时间线">
                          <h4>布置回执时间线</h4>
                          <ol>
                            {timeline.slice(0, 5).map((row, index) => (
                              <li key={`${String(row.assigned_at || index)}-${index}`}>
                                {String(row.assigned_at || '—')} · {String(row.topic || '巩固')} ·{' '}
                                {row.item_counts
                                  ? Object.entries(row.item_counts as Record<string, number>)
                                      .map(([k, n]) => `${k}:${n}`)
                                      .join(' ')
                                  : '—'}
                              </li>
                            ))}
                          </ol>
                        </div>
                      ) : null}
                    </div>
                  ) : null}
                </div>
              ) : null}
            </article>
          </section>
        ) : null}

        {activeTab === 'overview' && classId ? (
          <section className="panel class-assignment-timeline" aria-labelledby="class-timeline-title">
            <h2 id="class-timeline-title">班级布置回执（跨学生）</h2>
            <p className="lede">
              汇总本班所有学生会话的分层布置记录，并回访每份卷子是否已开始重练、是否已提交。
            </p>
            <ClassAssignmentTimeline rows={classTimeline} summary={completionSummary} />
          </section>
        ) : null}

        {activeTab === 'students' && classMetrics ? (
          <section className="panel teacher-intervention-panel">
            <h2>需要干预的学生</h2>
            {classMetrics.need_intervention_students.length ? (
              <>
                <div className="actions" style={{ marginBottom: '0.75rem' }}>
                  <button
                    className="btn"
                    type="button"
                    disabled={batchBusy || !classId}
                    onClick={() =>
                      runBatchAssign(
                        classMetrics.need_intervention_students
                          .map((s) => s.session_id)
                          .filter((id) => students?.some((row) => row.session_id === id)),
                      )
                    }
                  >
                    {batchBusy ? '批量布置中…' : '一键给干预名单布置巩固'}
                  </button>
                  <button
                    className="btn secondary"
                    type="button"
                    disabled={batchBusy || !classId || !students?.length}
                    onClick={() => runBatchAssign(students?.map((s) => s.session_id))}
                  >
                    全班布置巩固
                  </button>
                </div>
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
                          runTierAssign(student.session_id)
                        }}
                      >
                        布置巩固
                      </button>
                    </li>
                  ))}
                </ul>
              </>
            ) : (
              <p className="dashboard-empty">当前无需特殊干预</p>
            )}
            {assignReceipt ? (
              <p className="lede intervention-receipt" role="status">
                当面回执：{assignReceipt}
              </p>
            ) : null}
          </section>
        ) : null}

        {activeTab === 'detail' && selected ? (
          <>
            <DashboardDetail detail={selected} surface="teacher" />
            <UnlockRequestsPanel sessionId={selected.session_id} />
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
