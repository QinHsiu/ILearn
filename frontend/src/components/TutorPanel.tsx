import { useState } from 'react'
import { api } from '../api/client'
import type { TutorTurn } from '../api/client'

type TutorPanelProps = {
  sessionId: string
  itemId: string
}

export default function TutorPanel({ sessionId, itemId }: TutorPanelProps) {
  const [turns, setTurns] = useState<TutorTurn[]>([])
  const [userMessage, setUserMessage] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function start() {
    setBusy(true)
    setError(null)
    try {
      const turn = await api.tutorStart(sessionId, itemId)
      setTurns([turn])
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err))
    } finally {
      setBusy(false)
    }
  }

  async function hint() {
    const message = userMessage.trim()
    if (!message) return
    setBusy(true)
    setError(null)
    try {
      const turn = await api.tutorHint(sessionId, itemId, message)
      setTurns((previous) => [...previous, turn])
      setUserMessage('')
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err))
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="tutor-panel">
      <header className="tutor-panel-head">
        <p className="tutor-panel-eyebrow">TUTOR / SOCRATIC</p>
        <h3>苏格拉底助教</h3>
        <p className="lede">不直接给答案，用提问帮你找到卡住的地方。每题可引导多次。</p>
      </header>
      <div className="actions">
        <button className="btn" type="button" onClick={() => void start()} disabled={busy}>
          {busy && turns.length === 0 ? '辅导中…' : turns.length ? '重新开始辅导' : '开始辅导'}
        </button>
      </div>
      <div className="tutor-turns">
        {turns.map((turn, index) => (
          <div className="tutor-turn" key={`${turn.phase}-${index}`}>
            <p className="tutor-turn-message">{turn.message}</p>
            <p className="tutor-turn-phase">阶段 · {turn.phase}</p>
          </div>
        ))}
      </div>
      {turns.length > 0 && (
        <div className="field tutor-reply">
          <label htmlFor={`tutor-${itemId}`}>告诉助教你的想法</label>
          <textarea
            id={`tutor-${itemId}`}
            value={userMessage}
            onChange={(event) => setUserMessage(event.target.value)}
            placeholder="输入你的思路或困惑"
            disabled={busy}
            rows={3}
          />
          <button
            className="btn"
            type="button"
            onClick={() => void hint()}
            disabled={busy || !userMessage.trim()}
          >
            下一提示
          </button>
        </div>
      )}
      {error ? (
        <p className="error" role="alert">
          {error}
        </p>
      ) : null}
    </div>
  )
}
