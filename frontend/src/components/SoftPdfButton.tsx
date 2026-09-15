import { useState } from 'react'
import { api } from '../api/client'

type SoftPdfButtonProps = {
  sessionId: string
  kind: 'grading-receipts' | 'parent-card' | 'error-notebook'
  label: string
  className?: string
}

/** In-app PDF download for soft-launch exports (no raw navigation). */
export default function SoftPdfButton({
  sessionId,
  kind,
  label,
  className = 'btn secondary',
}: SoftPdfButtonProps) {
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function onClick() {
    setBusy(true)
    setError(null)
    try {
      const day = new Date().toISOString().slice(0, 10)
      await api.downloadSoftPdf(sessionId, kind, `ILearn-${kind}-${day}.pdf`)
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err))
    } finally {
      setBusy(false)
    }
  }

  return (
    <span className="soft-pdf-wrap">
      <button className={className} type="button" disabled={busy} onClick={() => void onClick()}>
        {busy ? '生成中…' : label}
      </button>
      {error ? (
        <span className="error" role="alert">
          {error}
        </span>
      ) : null}
    </span>
  )
}
