import { useEffect, useState } from 'react'
import { api } from '../api/client'
import type { TutorTurn } from '../api/client'

const MAX_HINTS = 3

const HINT_LEVELS = [
  { icon: '🔍', label: '提示', key: 'hint' },
  { icon: '💡', label: '思路', key: 'clue' },
  { icon: '✅', label: '验证', key: 'verify' },
] as const

type SocraticPanelProps = {
  sessionId: string
  itemId: string
}

type ChatMessage = {
  role: 'user' | 'assistant'
  content: string
}

type ConceptLesson = {
  knowledge_id: string
  title: string
  duration_sec: number
  script_steps: string[]
  asset_url?: string | null
  storyboard_url?: string | null
  poster_url?: string | null
  video_slot_url?: string | null
  media_status?: 'video' | 'poster' | 'storyboard' | 'slot'
  no_final_answer?: boolean
}

export default function SocraticPanel({ sessionId, itemId }: SocraticPanelProps) {
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      role: 'assistant',
      content: '我是苏格拉底助教，不会直接给答案，但会引导你思考。每道题可问 3 次。',
    },
  ])
  const [input, setInput] = useState('')
  const [usedCount, setUsedCount] = useState(0)
  const [started, setStarted] = useState(false)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [lesson, setLesson] = useState<ConceptLesson | null>(null)

  const remaining = Math.max(0, MAX_HINTS - usedCount)

  useEffect(() => {
    setMessages([
      {
        role: 'assistant',
        content: '我是苏格拉底助教，不会直接给答案，但会引导你思考。每道题可问 3 次。',
      },
    ])
    setInput('')
    setUsedCount(0)
    setStarted(false)
    setError(null)
    setLesson(null)
  }, [itemId])

  useEffect(() => {
    if (remaining > 0) return
    let cancelled = false
    void api
      .getConceptLesson(sessionId, itemId)
      .then((data) => {
        if (!cancelled) setLesson(data.lesson)
      })
      .catch(() => {
        if (!cancelled) setLesson(null)
      })
    return () => {
      cancelled = true
    }
  }, [remaining, sessionId, itemId])

  async function ensureStarted(): Promise<TutorTurn | null> {
    if (started) return null
    const turn = await api.tutorStart(sessionId, itemId)
    setStarted(true)
    setMessages((prev) => [...prev, { role: 'assistant', content: turn.message }])
    return turn
  }

  async function onSend() {
    const text = input.trim()
    if (!text || busy || remaining <= 0) return
    setBusy(true)
    setError(null)
    try {
      await ensureStarted()
      setMessages((prev) => [...prev, { role: 'user', content: text }])
      setInput('')
      const turn = await api.tutorHint(sessionId, itemId, text)
      setUsedCount((n) => n + 1)
      setMessages((prev) => [...prev, { role: 'assistant', content: turn.message }])
      if (usedCount + 1 >= MAX_HINTS) {
        setMessages((prev) => [
          ...prev,
          { role: 'assistant', content: '⭐ 坚持思考很棒，继续试试独立完成！' },
        ])
      }
    } catch (err) {
      const message = err instanceof Error ? err.message : String(err)
      setError(message)
      if (/exhausted/i.test(message)) {
        setUsedCount(MAX_HINTS)
      }
    } finally {
      setBusy(false)
    }
  }

  async function onStartOnly() {
    if (busy || started) return
    setBusy(true)
    setError(null)
    try {
      await ensureStarted()
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err))
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="socratic-panel">
      <div className="socratic-head">
        <strong>苏格拉底助教</strong>
        <span>
          剩余提示 {remaining}/{MAX_HINTS}
        </span>
      </div>
      <div className="socratic-hint-progress" aria-label="提示进度">
        {HINT_LEVELS.map((level, index) => (
          <span
            key={level.key}
            className={`socratic-hint-step ${index < usedCount ? 'is-used' : ''} ${index === usedCount && remaining > 0 ? 'is-next' : ''}`}
          >
            {level.icon} {level.label}
          </span>
        ))}
      </div>
      <div className="socratic-hint-bar" aria-hidden="true">
        <div
          className="socratic-hint-bar-fill"
          style={{ width: `${(usedCount / MAX_HINTS) * 100}%` }}
        />
      </div>
      <div className="socratic-messages">
        {messages.map((msg, index) => (
          <div
            key={`${msg.role}-${index}`}
            className={`socratic-msg ${msg.role === 'user' ? 'user' : 'assistant'}`}
          >
            {msg.content}
          </div>
        ))}
      </div>
      {error ? <p className="error">{error}</p> : null}
      {remaining <= 0 ? (
        <div className="concept-micro" role="complementary" aria-label="概念微课入口">
          <p>
            提示次数已用完。先看 {lesson?.duration_sec || 60}{' '}
            秒概念卡，再独立重试——我们仍不会直接给最终答案。
          </p>
          {lesson ? (
            <>
              <p className="concept-micro-title">
                <strong>{lesson.title}</strong>
                {lesson.storyboard_url ? (
                  <>
                    {' · '}
                    <a href={lesson.storyboard_url} target="_blank" rel="noreferrer">
                      打开概念分镜
                    </a>
                  </>
                ) : null}
                {lesson.media_status === 'poster' ? (
                  <span className="concept-asset-slot"> · 分镜海报已就绪</span>
                ) : lesson.media_status === 'video' ? (
                  <span className="concept-asset-slot"> · 微课视频已就绪</span>
                ) : lesson.media_status === 'storyboard' ? (
                  <span className="concept-asset-slot"> · 文案分镜已就绪</span>
                ) : (
                  <span className="concept-asset-slot"> · 视频位已预留</span>
                )}
              </p>
              {lesson.poster_url ? (
                <figure className="concept-poster">
                  <img src={lesson.poster_url} alt={`${lesson.title} 分镜海报`} />
                  <figcaption>视觉分镜海报（不含终答；mp4 仍为预留位）</figcaption>
                </figure>
              ) : null}
              <ol>
                {lesson.script_steps.map((step) => (
                  <li key={step}>{step}</li>
                ))}
              </ol>
            </>
          ) : (
            <ol>
              <li>用自己的话复述本题相关概念</li>
              <li>对照 rubric 步骤口述思路</li>
              <li>请教家长/老师检查卡点（不要要终答）</li>
            </ol>
          )}
        </div>
      ) : null}
      <div className="socratic-actions">
        {!started ? (
          <button className="btn secondary" type="button" disabled={busy} onClick={() => void onStartOnly()}>
            开始对话
          </button>
        ) : null}
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder={remaining <= 0 ? '提示次数已用完' : '说说你卡在哪一步…'}
          disabled={busy || remaining <= 0}
          onKeyDown={(e) => {
            if (e.key === 'Enter') void onSend()
          }}
        />
        <button
          className="btn"
          type="button"
          disabled={busy || remaining <= 0 || !input.trim()}
          onClick={() => void onSend()}
        >
          发送
        </button>
      </div>
    </div>
  )
}
