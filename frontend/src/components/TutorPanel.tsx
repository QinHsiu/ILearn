import { useMemo, useState } from 'react'
import { api } from '../api/client'
import type { TutorTurn } from '../api/client'

type TutorPanelProps = {
  sessionId: string
  itemId: string
}

/** Round 1 · Khanmigo: make “guide, don’t give final answers” visible and enforceable in UI. */
export default function TutorPanel({ sessionId, itemId }: TutorPanelProps) {
  const [turns, setTurns] = useState<TutorTurn[]>([])
  const [userMessage, setUserMessage] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const softExit = useMemo(
    () => turns.some((turn) => turn.action === 'suggest_review' || turn.phase === 'done'),
    [turns],
  )
  const reviewSuggested = useMemo(
    () => turns.some((turn) => turn.action === 'suggest_review'),
    [turns],
  )

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
    if (!message || softExit) return
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
        <p className="lede">用提问帮你找到卡住的地方——引导思考，而不是代做题目。</p>
        <p className="tutor-ethics" role="note">
          学习约定：本助教<strong>不直接给出最终答案</strong>；提示用尽后会建议你回顾概念或请教老师。
        </p>
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
            <p className="tutor-turn-phase">
              阶段 · {turn.phase}
              {turn.action === 'suggest_review' ? ' · 建议复习（不泄终答）' : ''}
            </p>
          </div>
        ))}
      </div>
      {reviewSuggested ? (
        <p className="tutor-soft-exit" role="status">
          提示轮次已收束：请先回顾本题相关概念，或请教老师口述思路。我们仍然不会直接给出最终数值答案。
        </p>
      ) : null}
      {turns.length > 0 && !softExit ? (
        <div className="field tutor-reply">
          <label htmlFor={`tutor-${itemId}`}>告诉助教你的想法</label>
          <textarea
            id={`tutor-${itemId}`}
            value={userMessage}
            onChange={(event) => setUserMessage(event.target.value)}
            placeholder="输入你的思路或困惑（不要只问「直接告诉我答案」）"
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
      ) : null}
      {turns.length > 0 && softExit && !reviewSuggested ? (
        <p className="tutor-soft-exit" role="status">
          本轮辅导已结束。需要时点「重新开始辅导」，我们依旧不会直接给最终答案。
        </p>
      ) : null}
      {error ? (
        <p className="error" role="alert">
          {error}
        </p>
      ) : null}
    </div>
  )
}
