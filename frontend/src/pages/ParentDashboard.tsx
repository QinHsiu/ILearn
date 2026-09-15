import { useEffect, useState } from 'react'
import type { FormEvent } from 'react'
import { api, dashboardApi } from '../api/client'
import type {
  DashboardStudentDetail,
  DashboardStudentSummary,
  ParentSummary,
} from '../api/client'
import DashboardDetail from '../components/DashboardDetail'
import SoftPdfButton from '../components/SoftPdfButton'
import UnlockRequestsPanel from '../components/UnlockRequestsPanel'
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
  const [actionPack, setActionPack] = useState<ParentSummary | null>(null)
  const [masteryEvidence, setMasteryEvidence] = useState<{
    evidence_count: number
    probe_gap_count: number
    discounted_hint_correct: number
    mastery_percent: number | null
  } | null>(null)

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

  useEffect(() => {
    const sid = selectedSessionId || summaryStudent?.session_id
    if (!sid) {
      setActionPack(null)
      setMasteryEvidence(null)
      return
    }
    let cancelled = false
    void api.getParentSummary(sid).then((data) => {
      if (!cancelled) setActionPack(data)
    }).catch(() => {
      if (!cancelled) setActionPack(null)
    })
    void api.getMasteryPublic(sid).then((data) => {
      if (!cancelled) {
        setMasteryEvidence({
          evidence_count: data.evidence_count,
          probe_gap_count: data.probe_gap_count,
          discounted_hint_correct: data.discounted_hint_correct,
          mastery_percent: data.mastery_percent,
        })
      }
    }).catch(() => {
      if (!cancelled) setMasteryEvidence(null)
    })
    return () => {
      cancelled = true
    }
  }, [selectedSessionId, summaryStudent?.session_id])

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
    const code = sessionId.trim()
    if (!code) return
    try {
      if (code.length <= 8 && !code.includes('-')) {
        await dashboardApi.bindParentByCode(userId, code)
      } else {
        await dashboardApi.bindParent(userId, code)
      }
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
        {actionPack?.action_summary ? (
          <section className="parent-action-pack" aria-labelledby="parent-action-title">
            <h2 id="parent-action-title">一分钟行动摘要</h2>
            <p className="lede">{actionPack.action_summary.headline}</p>
            <div className="summary-grid">
              <article className="summary-block">
                <span>值得肯定</span>
                <strong>{actionPack.action_summary.wins.join('；') || '—'}</strong>
              </article>
              <article className="summary-block">
                <span>需要加强</span>
                <strong>{actionPack.action_summary.focus.join('；') || '—'}</strong>
              </article>
              <article className="summary-block">
                <span>今晚可做</span>
                <ol>
                  {actionPack.action_summary.actions.map((item) => (
                    <li key={item}>{item}</li>
                  ))}
                </ol>
              </article>
            </div>
            {(selectedSessionId || selected?.session_id) ? (
              <p>
                <SoftPdfButton
                  sessionId={selectedSessionId || selected!.session_id}
                  kind="parent-card"
                  label="今晚陪练：导出亲子题卡 PDF"
                  className="btn"
                />
              </p>
            ) : null}
          </section>
        ) : (selectedSessionId || selected?.session_id) ? (
          <section className="parent-action-pack" aria-labelledby="parent-card-cta-title">
            <h2 id="parent-card-cta-title">今晚可带走</h2>
            <p className="lede">先导出亲子题卡，用口述三问陪练，不需要当家教。</p>
            <SoftPdfButton
              sessionId={selectedSessionId || selected!.session_id}
              kind="parent-card"
              label="导出亲子题卡 PDF"
              className="btn"
            />
          </section>
        ) : null}
        {masteryEvidence ? (
          <section className="parent-evidence-pack" aria-labelledby="parent-evidence-title">
            <h2 id="parent-evidence-title">本周证据（不只正确率）</h2>
            <div className="summary-grid">
              <article className="summary-block">
                <span>掌握度</span>
                <strong>
                  {masteryEvidence.mastery_percent != null
                    ? `${masteryEvidence.mastery_percent}%`
                    : '—'}
                </strong>
              </article>
              <article className="summary-block">
                <span>证据条数</span>
                <strong>{masteryEvidence.evidence_count}</strong>
              </article>
              <article className="summary-block">
                <span>探针缺口</span>
                <strong>{masteryEvidence.probe_gap_count}</strong>
              </article>
              <article className="summary-block">
                <span>提示后做对（未计掌握）</span>
                <strong>{masteryEvidence.discounted_hint_correct}</strong>
              </article>
            </div>
          </section>
        ) : null}
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
                <div className="dashboard-empty-state parent-zero-state" aria-label="尚未绑定孩子">
                  <p>
                    <strong>还没有绑定孩子。</strong>
                    让孩子在学习报告页复制「家长绑定码」，或先体验演示孩子。
                  </p>
                  <ol>
                    <li>孩子完成测评后，在学情页查看绑定码</li>
                    <li>把 6 位绑定码发给你</li>
                    <li>在下方输入绑定码即可看到行动摘要</li>
                  </ol>
                  <button
                    className="btn"
                    type="button"
                    onClick={() => {
                      void api.createDemoSession('math_5_1').then((demo) => {
                        window.location.href = demo.links.parent
                      }).catch((err) => {
                        setError(err instanceof Error ? err.message : String(err))
                      })
                    }}
                  >
                    先看演示孩子（一键）
                  </button>
                </div>
              ) : null}
            </>
          )}
          {error ? <p className="error dashboard-error" role="alert" aria-live="polite">{error}</p> : null}
          <form className="dashboard-bind" onSubmit={(e) => void bind(e)}>
            <label htmlFor="parent-session">家长绑定码（6 位）</label>
            <input
              id="parent-session"
              value={sessionId}
              onChange={(e) => setSessionId(e.target.value)}
              placeholder="例如 A3K9Q2"
              autoComplete="off"
            />
            <button className="btn" type="submit">用绑定码绑定孩子</button>
          </form>
        </section>
        {selected ? <DashboardDetail detail={selected} surface="parent" /> : null}
        {(selectedSessionId || selected?.session_id) ? (
          <UnlockRequestsPanel sessionId={selectedSessionId || selected!.session_id} />
        ) : null}
      </main>
    </DashboardHome>
  )
}
