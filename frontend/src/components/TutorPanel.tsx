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
      <div className="actions">
        <button className="btn secondary" type="button" onClick={() => void start()} disabled={busy}>
          {busy ? '辅导中…' : '开始辅导'}
        </button>
      </div>
      {turns.map((turn, index) => (
        <div className="tutor-turn" key={`${turn.phase}-${index}`}>
          <div>{turn.message}</div>
          <small>阶段：{turn.phase}</small>
        </div>
      ))}
      {turns.length > 0 && (
        <div className="field">
          <label htmlFor={`tutor-${itemId}`}>告诉老师你的想法</label>
          <textarea
            id={`tutor-${itemId}`}
            value={userMessage}
            onChange={(event) => setUserMessage(event.target.value)}
            placeholder="输入你的思路或困惑"
            disabled={busy}
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
      {error ? <p className="error">{error}</p> : null}
    </div>
  )
}
