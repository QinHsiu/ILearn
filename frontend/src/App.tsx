import { useEffect, useMemo, useRef, useState } from 'react'
import type { FormEvent } from 'react'
import { api, fileToImageAnswer } from './api/client'
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
import ProgressDots from './components/ProgressDots'
import MathVisualizer from './components/MathVisualizer'
import FocusedHintLayout from './components/FocusedHintLayout'
import SocraticPanel from './components/SocraticPanel'
import { useCountdown } from './hooks/useCountdown'
import { inferVisualization } from './lib/inferVisualization'
import { applyTheme } from './theme'
import './styles.css'

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
  const [step, setStep] = useState(0)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [sessionId, setSessionId] = useState<string | null>(null)
  const [paper, setPaper] = useState<AssessmentPaper | null>(null)
  const [answers, setAnswers] = useState<Record<string, string>>({})
  const [imageUploads, setImageUploads] = useState<
    Record<string, ImageAnswer & { preview: string; name: string }>
  >({})
  const [report, setReport] = useState<ReportResponse | null>(null)
  const [historyNickname, setHistoryNickname] = useState('')
  const [focusItemId, setFocusItemId] = useState<string | null>(null)
  const [currentItemIndex, setCurrentItemIndex] = useState(0)

  const [profile, setProfile] = useState<StudentProfile>({
    region: 'beijing',
    grade: 5,
    age: 11,
    nickname: '',
    gender: 'unspecified',
    learning_difficulty: false,
  })

  const session = report?.session
  const wrongItems = useMemo(
    () => (session ? wrongItemEntries(session) : []),
    [session],
  )

  const submitAnswersRef = useRef<() => void>(() => {})
  const { format: formatCountdown, reset: resetCountdown } = useCountdown(
    step === 1 && paper ? 3600 : 0,
    () => {
      if (step === 1 && paper && sessionId && !busy) {
        submitAnswersRef.current()
      }
    },
  )

  useEffect(() => {
    applyTheme(profile.grade, profile.gender || 'unspecified')
  }, [profile.grade, profile.gender])

  useEffect(() => {
    if (step === 1 && paper) {
      resetCountdown()
      setCurrentItemIndex(0)
      setFocusItemId(null)
    }
  }, [step, sessionId, paper, resetCountdown])

  async function onResume(id: string) {
    const nextReport = await api.getReport(id)
    const nextSession = nextReport.session
    setSessionId(id)
    setPaper(nextSession.paper || null)
    setAnswers(
      Object.fromEntries(
        (nextSession.answers || []).map((answer) => [answer.item_id, answer.answer_text]),
      ),
    )
    setImageUploads({})
    setReport(nextReport)
    if (nextSession.profile) {
      setProfile(nextSession.profile)
      setHistoryNickname(nextSession.profile.nickname || '')
      applyTheme(nextSession.profile.grade, nextSession.profile.gender || 'unspecified')
    }
    if (nextSession.plan) setStep(3)
    else if (nextSession.grades?.length) setStep(2)
    else if (nextSession.paper) setStep(1)
    else setStep(0)
  }

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
      const nextPaper = await api.generateAssessment(created.session_id)
      setSessionId(created.session_id)
      setPaper(nextPaper)
      setAnswers({})
      setImageUploads({})
      setReport(null)
      setStep(1)
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err))
    } finally {
      setBusy(false)
    }
  }

  async function onPickImage(itemId: string, file: File | undefined) {
    if (!file) return
    setError(null)
    try {
      const payload = await fileToImageAnswer(itemId, file)
      const preview = URL.createObjectURL(file)
      setImageUploads((prev) => {
        const old = prev[itemId]
        if (old?.preview) URL.revokeObjectURL(old.preview)
        return { ...prev, [itemId]: { ...payload, preview, name: file.name } }
      })
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err))
    }
  }

  function onClearImage(itemId: string) {
    setImageUploads((prev) => {
      const next = { ...prev }
      if (next[itemId]?.preview) URL.revokeObjectURL(next[itemId].preview)
      delete next[itemId]
      return next
    })
  }

  async function onSubmitAnswers() {
    if (!sessionId || !paper) return
    setBusy(true)
    setError(null)
    try {
      const payload: Record<string, string> = {}
      for (const item of paper.items) {
        payload[item.id] = (answers[item.id] || '').trim()
      }
      await api.submit(sessionId, payload)
      const images = Object.values(imageUploads).map(
        ({ item_id, image_base64, mime_type }) => ({
          item_id,
          image_base64,
          mime_type,
        }),
      )
      if (images.length) {
        await api.submitImages(sessionId, images)
      }
      await api.run(sessionId)
      const nextReport = await api.getReport(sessionId)
      setReport(nextReport)
      setFocusItemId(null)
      setStep(2)
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err))
    } finally {
      setBusy(false)
    }
  }

  submitAnswersRef.current = () => {
    void onSubmitAnswers()
  }

  async function onReplan() {
    if (!sessionId) return
    setBusy(true)
    setError(null)
    try {
      await api.replan(sessionId)
      const nextReport = await api.getReport(sessionId)
      setReport(nextReport)
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err))
    } finally {
      setBusy(false)
    }
  }

  const grades = session?.grades || []
  const correct = grades.filter((g) => g.final_correct).length

  return (
    <div className="app-shell">
      <header className="brand-row">
        <h1 className="brand">ILearn</h1>
        <div className="brand-copy">
          {(profile.nickname || '').trim() ? (
            <p className="brand-sub">你好，{(profile.nickname || '').trim()}</p>
          ) : null}
          <p className="brand-sub">课标在环的个性化学习向导</p>
        </div>
      </header>

      <nav className="stepper" aria-label="向导步骤">
        {STEPS.map((label, index) => (
          <div
            key={label}
            className={`step ${index === step ? 'active' : ''} ${index < step ? 'done' : ''}`}
          >
            {label}
          </div>
        ))}
      </nav>

      {step === 0 && (
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

      {step === 1 && paper && sessionId && (
        <section className="panel">
          <div className="assess-head">
            <div>
              <h2>测评作答</h2>
              <p className="lede">
                {paper.curriculum_label} · 共 {paper.items.length} 题 · 可文本作答，也可上传手写照片
              </p>
            </div>
            <div className="countdown" aria-live="polite">
              剩余 {formatCountdown()}
            </div>
          </div>

          <ProgressDots
            total={paper.items.length}
            current={currentItemIndex}
            answered={answers}
            questionIds={paper.items.map((item) => item.id)}
            onSelect={setCurrentItemIndex}
          />

          {focusItemId ? (
            (() => {
              const focusItem =
                paper.items.find((item) => item.id === focusItemId) || paper.items[0]
              const visual = inferVisualization(focusItem.stem)
              return (
                <FocusedHintLayout
                  onExit={() => setFocusItemId(null)}
                  questionSlot={
                    <>
                      <div className="item-meta">
                        <span className="pill">{focusItem.difficulty}</span>
                        <span className="pill">{focusItem.type}</span>
                      </div>
                      <div>{focusItem.stem}</div>
                      <MathVisualizer spec={visual} />
                      {focusItem.choices?.length ? (
                        <div className="choices">
                          {focusItem.choices.map((choice) => (
                            <label className="choice" key={choice}>
                              <input
                                type="radio"
                                name={`focus-${focusItem.id}`}
                                checked={answers[focusItem.id] === choice}
                                onChange={() =>
                                  setAnswers({ ...answers, [focusItem.id]: choice })
                                }
                              />
                              <span>{choice}</span>
                            </label>
                          ))}
                        </div>
                      ) : (
                        <div className="field" style={{ marginTop: '0.65rem' }}>
                          <label htmlFor={`focus-ans-${focusItem.id}`}>作答</label>
                          <textarea
                            id={`focus-ans-${focusItem.id}`}
                            value={answers[focusItem.id] || ''}
                            onChange={(e) =>
                              setAnswers({
                                ...answers,
                                [focusItem.id]: e.target.value,
                              })
                            }
                            placeholder="输入答案或解题过程"
                          />
                        </div>
                      )}
                    </>
                  }
                  panelSlot={
                    <SocraticPanel sessionId={sessionId} itemId={focusItem.id} />
                  }
                />
              )
            })()
          ) : (
            paper.items.map((item, index) => {
              const visual = inferVisualization(item.stem)
              return (
                <article
                  className={`question-card${index === currentItemIndex ? ' current-question' : ''}`}
                  key={item.id}
                  id={`item-${item.id}`}
                >
                  <div className="item-meta">
                    <span className="pill">第 {index + 1} 题</span>
                    <span className="pill">{item.difficulty}</span>
                    <span className="pill">{item.type}</span>
                    {item.situation_tag ? (
                      <span className="pill">{item.situation_tag}</span>
                    ) : null}
                  </div>
                  <div>{item.stem}</div>
                  <MathVisualizer spec={visual} />
                  {item.choices?.length ? (
                    <div className="choices">
                      {item.choices.map((choice) => (
                        <label className="choice" key={choice}>
                          <input
                            type="radio"
                            name={item.id}
                            checked={answers[item.id] === choice}
                            onChange={() => {
                              setAnswers({ ...answers, [item.id]: choice })
                              setCurrentItemIndex(index)
                            }}
                          />
                          <span>{choice}</span>
                        </label>
                      ))}
                    </div>
                  ) : (
                    <div className="field" style={{ marginTop: '0.65rem' }}>
                      <label htmlFor={`ans-${item.id}`}>作答</label>
                      <textarea
                        id={`ans-${item.id}`}
                        value={answers[item.id] || ''}
                        onChange={(e) => {
                          setAnswers({ ...answers, [item.id]: e.target.value })
                          setCurrentItemIndex(index)
                        }}
                        placeholder="输入答案或解题过程"
                      />
                    </div>
                  )}
                  <div className="field upload-field">
                    <label htmlFor={`img-${item.id}`}>手写作答照片（可选）</label>
                    <input
                      id={`img-${item.id}`}
                      type="file"
                      accept="image/png,image/jpeg,image/webp,.png,.jpg,.jpeg,.webp"
                      disabled={busy}
                      onChange={(e) => {
                        const file = e.target.files?.[0]
                        void onPickImage(item.id, file)
                        e.target.value = ''
                      }}
                    />
                    {imageUploads[item.id] ? (
                      <div className="upload-preview">
                        <div className="upload-frame">
                          <img
                            src={imageUploads[item.id].preview}
                            alt={`${item.id} 手写作答预览`}
                          />
                        </div>
                        <div className="upload-meta">
                          <span className="upload-name">{imageUploads[item.id].name}</span>
                          <button
                            className="btn secondary"
                            type="button"
                            onClick={() => onClearImage(item.id)}
                          >
                            移除图片
                          </button>
                        </div>
                      </div>
                    ) : (
                      <span className="upload-hint">
                        支持 PNG / JPG / WebP，将随提交送去 OCR 批改
                      </span>
                    )}
                  </div>
                  <div className="actions">
                    <button
                      className="btn secondary"
                      type="button"
                      onClick={() => {
                        setCurrentItemIndex(index)
                        setFocusItemId(item.id)
                      }}
                    >
                      求助苏格拉底
                    </button>
                  </div>
                </article>
              )
            })
          )}

          {!focusItemId ? (
            <div className="actions">
              <button
                className="btn secondary"
                type="button"
                onClick={() => {
                  setStep(0)
                  setSessionId(null)
                  setPaper(null)
                  setReport(null)
                  setAnswers({})
                  setImageUploads({})
                  setFocusItemId(null)
                }}
                disabled={busy}
              >
                返回建档
              </button>
              <button
                className="btn"
                type="button"
                onClick={() => void onSubmitAnswers()}
                disabled={busy}
              >
                {busy ? '批改中…' : '提交并诊断'}
              </button>
            </div>
          ) : null}
        </section>
      )}

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
          <div className="plan-body">
            <MarkdownView
              source={report?.markdown || session.plan?.markdown || '暂无计划内容'}
            />
          </div>
          <div className="actions">
            <button className="btn secondary" type="button" onClick={() => setStep(2)}>
              返回学情
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
                setPaper(null)
                setReport(null)
                setAnswers({})
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
