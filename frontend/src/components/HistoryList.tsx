import { useEffect, useState } from 'react'
import { api } from '../api/client'
import type { SessionSummary } from '../api/client'

type HistoryListProps = {
  nickname: string
  onResume: (sessionId: string) => void
}

export default function HistoryList({ nickname, onResume }: HistoryListProps) {
  const [sessions, setSessions] = useState<SessionSummary[]>([])
  const [busyId, setBusyId] = useState<string | null>(null)

  async function refresh() {
    const trimmed = nickname.trim()
    if (!trimmed) {
      setSessions([])
      return
    }
    try {
      setSessions(await api.listSessions(trimmed))
    } catch {
      setSessions([])
    }
  }

  useEffect(() => {
    void refresh()
  }, [nickname])

  if (!nickname.trim()) return null
  if (!sessions.length) return null

  async function onDelete(sessionId: string) {
    setBusyId(sessionId)
    try {
      await api.deleteSession(sessionId)
      await refresh()
    } finally {
      setBusyId(null)
    }
  }

  return (
    <section className="panel">
      <h2>历史会话</h2>
      <div className="history-list">
        {sessions.map((item) => (
          <article className="history-item" key={item.session_id}>
            <div>
              <strong>{item.session_id.slice(0, 8)}</strong>
              <span className="pill">{item.grade} 年级</span>
              <span className="pill">{item.phase}</span>
            </div>
            <div className="actions">
              <button
                className="btn secondary"
                type="button"
                onClick={() => onResume(item.session_id)}
                disabled={busyId !== null}
              >
                继续
              </button>
              <button
                className="btn secondary"
                type="button"
                onClick={() => void onDelete(item.session_id)}
                disabled={busyId !== null}
              >
                {busyId === item.session_id ? '删除中…' : '删除'}
              </button>
            </div>
          </article>
        ))}
      </div>
    </section>
  )
}
