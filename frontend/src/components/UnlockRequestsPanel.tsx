import { useEffect, useState } from 'react'
import { api } from '../api/client'

type UnlockRequestsPanelProps = {
  sessionId: string
}

/** Parent/teacher: approve student unlock requests and optionally reveal answer. */
export default function UnlockRequestsPanel({ sessionId }: UnlockRequestsPanelProps) {
  const [rows, setRows] = useState<Array<Record<string, unknown>>>([])
  const [message, setMessage] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  function reload() {
    void api
      .listUnlockRequests(sessionId)
      .then((data) => setRows(data.requests || []))
      .catch(() => setRows([]))
  }

  useEffect(() => {
    reload()
  }, [sessionId])

  if (!rows.length) return null

  return (
    <section className="panel unlock-requests-panel" aria-labelledby="unlock-req-title">
      <h2 id="unlock-req-title">终答解锁申请</h2>
      <ul>
        {rows.map((row) => (
          <li key={String(row.item_id)}>
            题目 {String(row.item_id)} · {String(row.status || 'pending')}
            {row.status !== 'approved' ? (
              <button
                type="button"
                className="btn secondary"
                onClick={() => {
                  void api
                    .approveUnlock(sessionId, String(row.item_id))
                    .then((res) => {
                      setMessage(
                        res.answer_key
                          ? `已批准。终答仅对监护人可见：${res.answer_key}`
                          : '已批准解锁申请',
                      )
                      reload()
                    })
                    .catch((err) =>
                      setError(err instanceof Error ? err.message : String(err)),
                    )
                }}
              >
                批准解锁
              </button>
            ) : null}
          </li>
        ))}
      </ul>
      {message ? <p className="lede" role="status">{message}</p> : null}
      {error ? (
        <p className="error" role="alert">
          {error}
        </p>
      ) : null}
    </section>
  )
}
