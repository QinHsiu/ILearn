import { useEffect, useState } from 'react'
import { api } from '../api/client'
import type { SessionClosePayload } from '../api/client'

type SessionCloseRitualProps = {
  sessionId: string
  /** Parent surface: show receipt line, never stamp. */
  readOnly?: boolean
  title?: string
}

/** W6 · evidence-first close: stamp today, next challenge, no final answer. */
export default function SessionCloseRitual({
  sessionId,
  readOnly = false,
  title = '今天收工',
}: SessionCloseRitualProps) {
  const [data, setData] = useState<SessionClosePayload | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    if (!sessionId) return
    let cancelled = false
    void api
      .getSessionClose(sessionId)
      .then((row) => {
        if (!cancelled) {
          setData(row)
          setError(null)
        }
      })
      .catch((err) => {
        if (!cancelled) {
          setData(null)
          setError(err instanceof Error ? err.message : String(err))
        }
      })
    return () => {
      cancelled = true
    }
  }, [sessionId])

  if (!sessionId) return null
  if (error) {
    return (
      <p className="error" role="alert">
        {error}
      </p>
    )
  }
  if (!data) return <p className="lede">加载收工卡…</p>

  const stamp = () => {
    if (readOnly || data.closed || busy) return
    setBusy(true)
    void api
      .stampSessionClose(sessionId)
      .then((row) => {
        setData(row)
        setError(null)
      })
      .catch((err) => {
        setError(err instanceof Error ? err.message : String(err))
      })
      .finally(() => setBusy(false))
  }

  return (
    <section className="session-close-ritual" role="region" aria-labelledby="session-close-title">
      <header className="session-close-head">
        <div>
          <h3 id="session-close-title" className="student-section-title">
            {title}
          </h3>
          <p className="lede">{data.headline}</p>
        </div>
        <span className="pill session-close-mask">不泄终答</span>
      </header>
      <p className="session-close-next">
        下一挑战：<strong>{data.next_challenge}</strong>
      </p>
      {readOnly ? <p className="session-close-parent">{data.parent_line}</p> : null}
      <p className="session-close-honesty">{data.honesty_note}</p>
      {!readOnly && !data.closed ? (
        <button type="button" className="btn" onClick={stamp} disabled={busy}>
          今天收工
        </button>
      ) : null}
    </section>
  )
}
