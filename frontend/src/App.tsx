import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import type { FormEvent } from 'react'
import { api } from './api/client'
import type {
  AssessmentPaper,
  Gender,
  ImageAnswer,
  ReportResponse,
  SessionState,
  StudentProfile,
} from './api/client'
import MarkdownView from './MarkdownView'
import HistoryList from './components/HistoryList'
import CitationPanel from './components/CitationPanel'
import TutorPanel from './components/TutorPanel'
import StudentSummaryPanel from './components/StudentSummaryPanel'
import ParentDashboard from './pages/ParentDashboard'
import TeacherDashboard from './pages/TeacherDashboard'
import LandingPage from './pages/LandingPage'
import LoginPage from './pages/LoginPage'
import Assessment from './pages/Assessment'
import type { AuthRole } from './api/client'
import { useRole } from './hooks/useRole'
import { useSessionSync } from './hooks/useSessionSync'
import { readDemoSessionId } from './lib/demoSessionQuery'
import { nextStepOnSync, stepFromSession } from './lib/sessionStep'
import { applyTheme } from './theme'
import './styles.css'
import './dashboard.css'

const STEPS = ['建档', '测评作答', '批改与学情', '学习计划'] as const

// Pilot pack ships only grade 4–6 math items; other grades have no blueprint.
const PILOT_GRADES = [4, 5, 6]

const LEVEL_LABELS: Record<string, string> = {
  mastered: '已掌握',
  unstable: '需巩固',
  weak: '待提升',
}

const ERROR_LABELS: Record<string, string> = {
  concept_gap: '概念缺口',
  calc_error: '计算错误',
  misread: '审题偏差',
  method_wrong: '方法不当',
  incomplete: '过程不完整',
}

function answersFromSession(nextSession: SessionState): Record<string, string> {
  return Object.fromEntries(
    (nextSession.answers || []).map((answer) => [answer.item_id, answer.answer_text]),
  )
}

function wrongItemEntries(session: SessionState) {
  const grades = session.grades || []
  const items = session.paper?.items || []
  const byId = Object.fromEntries(items.map((item) => [item.id, item]))
  return grades
    .filter((g) => !g.final_correct)
    .map((g) => {
      const item = byId[g.item_id]
      if (!item) return null
      return { itemId: item.id, stem: item.stem, sourceRefs: item.source_refs || [] }
    })
    .filter(Boolean) as Array<{
    itemId: string
    stem: string
    sourceRefs: NonNullable<SessionState['paper']>['items'][number]['source_refs']
  }>
}

export default function App() {
  const [, refreshRoute] = useState(0)
  const { role, userId, isParent, isTeacher } = useRole()
  const params = new URLSearchParams(window.location.search)

  useEffect(() => {
    const onPopState = () => refreshRoute((version) => version + 1)
    window.addEventListener('popstate', onPopState)
    return () => window.removeEventListener('popstate', onPopState)
  }, [])

  if (isParent && userId) {
    return <ParentDashboard userId={userId} studentId={params.get('student_id') || undefined} />
  }
  if (isTeacher && userId) {
    return (
      <TeacherDashboard
        userId={userId}
        classId={params.get('class_id') || undefined}
        studentId={params.get('student_id') || undefined}
      />
    )
  }
  if (params.get('login') === '1' || !params.get('student')) {
    if (role === 'parent' || role === 'teacher') {
      return <LoginPage role={role as AuthRole} />
    }
    return <LandingPage />
  }
  return <StudentApp />
}

function StudentApp() {
  const [step, setStep] = useState(0)
  const [resumePending, setResumePending] = useState(() =>
    Boolean(readDemoSessionId(window.location.search)),
  )
  const [busy, setBusy] = useState(() =>
    Boolean(readDemoSessionId(window.location.search)),
  )
  const [error, setError] = useState<string | null>(null)
  const [sessionId, setSessionId] = useState<string | null>(null)
  const [paper, setPaper] = useState<AssessmentPaper | null>(null)
  const [answers, setAnswers] = useState<Record<string, string>>({})
  const [imageUploads, setImageUploads] = useState<
    Record<string, ImageAnswer & { preview: string; name: string }>
  >({})
  const [report, setReport] = useState<ReportResponse | null>(null)
  const [session, setSession] = useState<SessionState | null>(null)
  const [historyNickname, setHistoryNickname] = useState('')
  const [focusItemId, setFocusItemId] = useState<string | null>(null)
  const [exporting, setExporting] = useState<'assessment' | 'report' | null>(null)

  const [profile, setProfile] = useState<StudentProfile>({
    region: 'beijing',
    grade: 5,
    age: 11,
    nickname: '',
    gender: 'unspecified',
    learning_difficulty: false,
  })

  const lastSyncedAnswersRef = useRef<Record<string, string>>({})
  const answersRef = useRef(answers)
  answersRef.current = answers

  const wrongItems = useMemo(
    () => (session ? wrongItemEntries(session) : []),
    [session],
  )

  useEffect(() => {
    applyTheme(profile.grade, profile.gender || 'unspecified')
  }, [profile.grade, profile.gender])

  const onSessionSync = useCallback((nextSession: SessionState) => {
    setSession(nextSession)
    setPaper(nextSession.paper || null)
    const nextAnswers = answersFromSession(nextSession)
    setAnswers(nextAnswers)
    lastSyncedAnswersRef.current = nextAnswers
    if (nextSession.profile) {
      setProfile(nextSession.profile)
      setHistoryNickname(nextSession.profile.nickname || '')
      applyTheme(nextSession.profile.grade, nextSession.profile.gender || 'unspecified')
    }
    setStep((prev) => nextStepOnSync(prev, nextSession))
  }, [])

  const hasUnsavedChanges = useCallback(() => {
    const current = answersRef.current
    const synced = lastSyncedAnswersRef.current
    const keys = new Set([...Object.keys(current), ...Object.keys(synced)])
    for (const key of keys) {
      if ((current[key] || '') !== (synced[key] || '')) return true
    }
    return false
  }, [])

  const onAssessmentError = useCallback((message: string) => {
    setError(message)
  }, [])

  useSessionSync({ sessionId, onSync: onSessionSync, hasUnsavedChanges })

  const onResume = useCallback(async (id: string) => {
    const nextReport = await api.getReport(id)
    const nextSession = nextReport.session
    setSessionId(id)
    setSession(nextSession)
    setPaper(nextSession.paper || null)
    const nextAnswers = answersFromSession(nextSession)
    setAnswers(nextAnswers)
    lastSyncedAnswersRef.current = nextAnswers
    setImageUploads({})
    setReport(nextReport)
    if (nextSession.profile) {
      setProfile(nextSession.profile)
      setHistoryNickname(nextSession.profile.nickname || '')
      applyTheme(nextSession.profile.grade, nextSession.profile.gender || 'unspecified')
    }
    setStep(stepFromSession(nextSession))
  }, [])

  const resumedFromQueryRef = useRef(false)
  useEffect(() => {
    if (resumedFromQueryRef.current) return
    const id = readDemoSessionId(window.location.search)
    if (!id) {
      setResumePending(false)
      return
    }
    resumedFromQueryRef.current = true
    setBusy(true)
    setResumePending(true)
    void onResume(id)
      .catch((err) => setError(err instanceof Error ? err.message : String(err)))
      .finally(() => {
        setBusy(false)
        setResumePending(false)
      })
  }, [onResume])

  async function onStart(e: FormEvent) {
    e.preventDefault()
    setBusy(true)
    setError(null)
    try {
      applyTheme(profile.grade, profile.gender || 'unspecified')
      const payload: StudentProfile = {
        region: profile.region,
        grade: Number(profile.grade),
        age: Number(profile.age),
        gender: (profile.gender || 'unspecified') as Gender,
        learning_difficulty: Boolean(profile.learning_difficulty) || null,
      }
      const nick = (profile.nickname || '').trim()
      if (nick) payload.nickname = nick
      const created = await api.createSession(payload)
      setSessionId(created.session_id)
      setSession(null)
      setPaper(null)
      setAnswers({})
      lastSyncedAnswersRef.current = {}
      setImageUploads({})
      setReport(null)
      setStep(1)
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err))
    } finally {
      setBusy(false)
    }
  }

  async function onAdaptiveComplete(payload: {
    paper: AssessmentPaper
    answers: Record<string, string>
  }) {
    if (!sessionId) return
    setBusy(true)
    setError(null)
    try {
      setPaper(payload.paper)
      setAnswers(payload.answers)
      lastSyncedAnswersRef.current = { ...payload.answers }
      const submitPayload: Record<string, string> = {}
      for (const item of payload.paper.items) {
        submitPayload[item.id] = (payload.answers[item.id] || '').trim()
      }
      await api.submit(sessionId, submitPayload)
      await api.run(sessionId)
      const nextReport = await api.getReport(sessionId)
      setReport(nextReport)
      setSession(nextReport.session)
      lastSyncedAnswersRef.current = answersFromSession(nextReport.session)
      setFocusItemId(null)
      setStep(2)
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err))
      throw err
    } finally {
      setBusy(false)
    }
  }

  async function onReplan() {
    if (!sessionId) return
    setBusy(true)
    setError(null)
    try {
      await api.replan(sessionId)
      const nextReport = await api.getReport(sessionId)
      setReport(nextReport)
      setSession(nextReport.session)
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err))
    } finally {
      setBusy(false)
    }
  }

  async function onExportPdf(kind: 'assessment' | 'report') {
    if (!sessionId) return
    setExporting(kind)
    setError(null)
    try {
      const nick = (profile.nickname || '').trim() || '未命名'
      const day = new Date().toISOString().slice(0, 10)
      const filename =
        kind === 'assessment'
          ? `ILearn-做题复盘-${nick}-${day}.pdf`
          : `ILearn-学习报告-${nick}-${day}.pdf`
      await api.downloadExport(sessionId, kind, filename)
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err))
    } finally {
      setExporting(null)
    }
  }

  const grades = session?.grades || []
  const correct = grades.filter((g) => g.final_correct).length

  return (
    <div className="app-shell student-shell">
      <header className="student-chrome">
        <p className="student-chrome-eyebrow">ILearn / STUDENT</p>
        <h1 className="brand">ILearn</h1>
        <h2 className="student-mode">学生学习 / NEXT STEP</h2>
        {(profile.nickname || '').trim() ? (
          <p className="student-chrome-nick">你好，{(profile.nickname || '').trim()}</p>
        ) : null}
      </header>

      <nav className="stepper student-steps" aria-label="向导步骤">
        {STEPS.map((label, index) => (
          <div
            key={label}
            className={`student-step ${index === step ? 'is-active' : ''} ${index < step ? 'is-done' : ''}`}
          >
            {label}
          </div>
        ))}
      </nav>

      {resumePending ? (
        <section className="panel">
          <p className="lede">正在恢复会话…</p>
        </section>
      ) : null}

      {step === 0 && !resumePending && (
        <section className="panel">
          <h2>建档</h2>
          <p className="lede">填写学习者信息后生成诊断卷。请先启动 FastAPI（:8000）。</p>
          <form onSubmit={onStart}>
            <div className="form-grid">
              <div className="field">
                <label htmlFor="nickname">昵称</label>
                <input
                  id="nickname"
                  value={profile.nickname || ''}
                  onChange={(e) => setProfile({ ...profile, nickname: e.target.value })}
                  onBlur={(e) => setHistoryNickname(e.currentTarget.value)}
                  placeholder="可选"
                />
              </div>
              <div className="field">
                <label htmlFor="gender">性别模板</label>
                <select
                  id="gender"
                  value={profile.gender || 'unspecified'}
                  onChange={(e) =>
                    setProfile({ ...profile, gender: e.target.value as Gender })
                  }
                >
                  <option value="unspecified">中性</option>
                  <option value="male">男生向</option>
                  <option value="female">女生向</option>
                </select>
              </div>
              <div className="field">
                <label htmlFor="region">地区</label>
                <input
                  id="region"
                  value={profile.region}
                  onChange={(e) => setProfile({ ...profile, region: e.target.value })}
                  required
                />
              </div>
              <div className="field">
                <label htmlFor="grade">年级</label>
                <select
                  id="grade"
                  value={profile.grade}
                  onChange={(e) =>
                    setProfile({ ...profile, grade: Number(e.target.value) })
                  }
                >
                  {Array.from({ length: 12 }, (_, i) => i + 1).map((g) => (
                    <option key={g} value={g} disabled={!PILOT_GRADES.includes(g)}>
                      {g} 年级{PILOT_GRADES.includes(g) ? '' : '（暂未开放）'}
                    </option>
                  ))}
                </select>
                <p className="field-hint">试点内容目前覆盖 4–6 年级数学。</p>
              </div>
              <div className="field">
                <label htmlFor="age">年龄</label>
                <input
                  id="age"
                  type="number"
                  min={6}
                  max={18}
                  value={profile.age}
                  onChange={(e) =>
                    setProfile({ ...profile, age: Number(e.target.value) })
                  }
                  required
                />
              </div>
              <div className="field">
                <label htmlFor="ld">学习困难简化路径</label>
                <select
                  id="ld"
                  value={profile.learning_difficulty ? 'yes' : 'no'}
                  onChange={(e) =>
                    setProfile({
                      ...profile,
                      learning_difficulty: e.target.value === 'yes',
                    })
                  }
                >
                  <option value="no">否</option>
                  <option value="yes">是</option>
                </select>
              </div>
            </div>
            <div className="actions">
              <button className="btn" type="submit" disabled={busy}>
                {busy ? '生成中…' : '开始测评'}
              </button>
            </div>
          </form>
          <HistoryList
            nickname={historyNickname}
            onResume={(id) => {
              void onResume(id).catch((err) => {
                setError(err instanceof Error ? err.message : String(err))
              })
            }}
          />
        </section>
      )}

      {step === 1 && sessionId ? (
        <Assessment
          sessionId={sessionId}
          profile={profile}
          onComplete={onAdaptiveComplete}
          onError={onAssessmentError}
          onBack={() => {
            setStep(0)
            setSessionId(null)
            setSession(null)
            setPaper(null)
            setReport(null)
            setAnswers({})
            lastSyncedAnswersRef.current = {}
            setImageUploads({})
            setFocusItemId(null)
          }}
        />
      ) : null}

      {step === 2 && session && (
        <section className="panel">
          <h2>批改与学情</h2>
          <p className="lede">
            正确 {correct}/{grades.length}
            {session.loop_count ? ` · 巩固轮次 ${session.loop_count}` : ''}
          </p>

          <h3 style={{ marginTop: '0.2rem' }}>知识点掌握</h3>
          <table className="table">
            <thead>
              <tr>
                <th>知识点</th>
                <th>掌握率</th>
                <th>水平</th>
                <th>主要错因</th>
              </tr>
            </thead>
            <tbody>
              {(session.diagnosis?.knowledge_mastery || []).map((row) => {
                const errors = row.error_tag_counts || {}
                const errorText =
                  Object.entries(errors)
                    .filter(([, n]) => n)
                    .map(([tag, n]) => `${ERROR_LABELS[tag] || tag} × ${n}`)
                    .join('、') || '—'
                return (
                  <tr key={row.knowledge_id}>
                    <td>{row.knowledge_name || row.knowledge_id}</td>
                    <td>{Math.round((row.score_rate || 0) * 100)}%</td>
                    <td>{LEVEL_LABELS[row.level] || row.level}</td>
                    <td>{errorText}</td>
                  </tr>
                )
              })}
            </tbody>
          </table>

          {wrongItems.length > 0 && (
            <>
              <CitationPanel items={wrongItems} />
              {wrongItems.map((entry) =>
                sessionId ? (
                  <TutorPanel key={entry.itemId} sessionId={sessionId} itemId={entry.itemId} />
                ) : null,
              )}
            </>
          )}

          <div className="actions">
            <button className="btn" type="button" onClick={() => setStep(3)}>
              查看学习计划
            </button>
          </div>
        </section>
      )}

      {step === 3 && session && (
        <section className="panel">
          <h2>学习计划</h2>
          <p className="lede">
            状态：{session.plan?.status || 'draft'}
            {profile.nickname ? ` · ${profile.nickname}` : ''}
          </p>
          {sessionId ? <StudentSummaryPanel sessionId={sessionId} /> : null}
          {session.metadata?.scientific_plan ? (
            <details className="scientific-plan-summary">
              <summary>科学学习方法摘要</summary>
              <p className="lede">
                任务 {(session.metadata.scientific_plan.tasks || []).length} 项
                {typeof session.metadata.scientific_plan.estimated_total_hours === 'number'
                  ? ` · 约 ${session.metadata.scientific_plan.estimated_total_hours.toFixed(1)} 小时`
                  : ''}
                {(session.metadata.scientific_plan.review_schedule || []).length
                  ? ` · 间隔复习 ${(session.metadata.scientific_plan.review_schedule || []).length} 个节点`
                  : ''}
              </p>
            </details>
          ) : null}
          <div className="plan-body">
            <MarkdownView
              source={report?.markdown || session.plan?.markdown || '暂无计划内容'}
            />
          </div>
          <div className="actions">
            <button className="btn secondary" type="button" onClick={() => setStep(2)}>
              返回学情
            </button>
            <button
              className="btn secondary"
              type="button"
              onClick={() => void onExportPdf('assessment')}
              disabled={busy || exporting !== null}
            >
              {exporting === 'assessment' ? '生成中…' : '导出做题复盘 PDF'}
            </button>
            <button
              className="btn secondary"
              type="button"
              onClick={() => void onExportPdf('report')}
              disabled={busy || exporting !== null}
            >
              {exporting === 'report' ? '生成中…' : '导出学习报告 PDF'}
            </button>
            <button className="btn" type="button" onClick={() => void onReplan()} disabled={busy}>
              {busy ? '规划中…' : '重新规划'}
            </button>
            <button
              className="btn"
              type="button"
              onClick={() => {
                setStep(0)
                setSessionId(null)
                setSession(null)
                setPaper(null)
                setReport(null)
                setAnswers({})
                lastSyncedAnswersRef.current = {}
                setImageUploads({})
              }}
            >
              新会话
            </button>
          </div>
        </section>
      )}

      {error ? <p className="error">{error}</p> : null}
    </div>
  )
}
