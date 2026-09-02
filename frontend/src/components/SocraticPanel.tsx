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
  }, [itemId])

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
        <span>剩余提示 {remaining}/{MAX_HINTS}</span>
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
