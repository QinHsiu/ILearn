import { useEffect, useMemo, useState } from 'react'
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
import { applyTheme } from './theme'
import './styles.css'

const STEPS = ['建档', '测评作答', '批改与学情', '学习计划'] as const

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

function formatSourceLines(ref: {
  example_id?: string | null
  curriculum_objective_ids?: string[]
  textbook_chapter?: string | null
  source_label?: string | null
}): string[] {
  const lines: string[] = []
  if (ref.example_id) lines.push(`例题 ID：${ref.example_id}`)
  if (ref.textbook_chapter) lines.push(`教材章节：${ref.textbook_chapter}`)
  if (ref.curriculum_objective_ids?.length) {
    lines.push(`课标条目：${ref.curriculum_objective_ids.join('、')}`)
  }
  if (ref.source_label) lines.push(`来源：${ref.source_label}`)
  return lines
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
      const sourceLines = (item.source_refs || []).flatMap(formatSourceLines)
      if (!sourceLines.length) return null
      return { itemId: item.id, stem: item.stem, sourceLines }
    })
    .filter(Boolean) as Array<{ itemId: string; stem: string; sourceLines: string[] }>
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

  useEffect(() => {
    applyTheme(profile.grade, profile.gender || 'unspecified')
  }, [profile.grade, profile.gender])

  async function onResume(id: string) {
    const nextReport = await api.getReport(id)
    setSessionId(id)
    setPaper(nextReport.session.paper || null)
    setReport(nextReport)
    if (nextReport.session.plan) setStep(3)
    else if (nextReport.session.grades?.length) setStep(2)
    else if (nextReport.session.paper) setStep(1)
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
      setStep(2)
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
                    <option key={g} value={g}>
                      {g} 年级
                    </option>
                  ))}
                </select>
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

      {step === 1 && paper && (
        <section className="panel">
          <h2>测评作答</h2>
          <p className="lede">
            {paper.curriculum_label} · 共 {paper.items.length} 题 · 可文本作答，也可上传手写照片
          </p>
          {paper.items.map((item, index) => (
            <article className="question-card" key={item.id}>
              <div className="item-meta">
                <span className="pill">第 {index + 1} 题</span>
                <span className="pill">{item.difficulty}</span>
                <span className="pill">{item.type}</span>
                {item.situation_tag ? (
                  <span className="pill">{item.situation_tag}</span>
                ) : null}
              </div>
              <div>{item.stem}</div>
              {item.choices?.length ? (
                <div className="choices">
                  {item.choices.map((choice) => (
                    <label className="choice" key={choice}>
                      <input
                        type="radio"
                        name={item.id}
                        checked={answers[item.id] === choice}
                        onChange={() =>
                          setAnswers({ ...answers, [item.id]: choice })
                        }
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
                    onChange={(e) =>
                      setAnswers({ ...answers, [item.id]: e.target.value })
                    }
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
                  <span className="upload-hint">支持 PNG / JPG / WebP，将随提交送去 OCR 批改</span>
                )}
              </div>
            </article>
          ))}
          <div className="actions">
            <button
              className="btn secondary"
              type="button"
              onClick={() => setStep(0)}
              disabled={busy}
            >
              返回建档
            </button>
            <button
              className="btn"
              type="button"
              onClick={onSubmitAnswers}
              disabled={busy}
            >
              {busy ? '批改中…' : '提交并诊断'}
            </button>
          </div>
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
              <h3>错题参考来源</h3>
              {wrongItems.map((entry) => (
                <details className="expander" key={entry.itemId}>
                  <summary>{entry.stem.slice(0, 48)}{entry.stem.length > 48 ? '…' : ''}</summary>
                  <div className="body">
                    {entry.sourceLines.map((line) => (
                      <div key={line}>{line}</div>
                    ))}
                  </div>
                </details>
              ))}
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
              source={session.plan?.markdown || report?.markdown || '暂无计划内容'}
            />
          </div>
          <div className="actions">
            <button className="btn secondary" type="button" onClick={() => setStep(2)}>
              返回学情
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
