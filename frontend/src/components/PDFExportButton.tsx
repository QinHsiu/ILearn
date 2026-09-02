import { useEffect, useState } from 'react'
import { api } from '../api/client'

type PDFExportButtonProps = {
  sessionId: string
  kind: 'assessment' | 'report' | 'effectiveness'
  label?: string
  className?: string
  disabled?: boolean
  nickname?: string | null
}

export default function PDFExportButton({
  sessionId,
  kind,
  label,
  className = 'btn secondary',
  disabled = false,
  nickname,
}: PDFExportButtonProps) {
  const [backend, setBackend] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    void api.getPdfBackend().then((info) => setBackend(info.backend)).catch(() => setBackend(null))
  }, [])

  const defaultLabel =
    kind === 'assessment'
      ? '导出做题复盘 PDF'
      : kind === 'report'
        ? '导出学习报告 PDF'
        : '导出效果验证报告'

  async function onExport() {
    setBusy(true)
    try {
      if (kind === 'effectiveness') {
        await api.exportEffectivenessPdf(sessionId)
      } else {
        const nick = (nickname || '').trim() || '未命名'
        const day = new Date().toISOString().slice(0, 10)
        const filename =
          kind === 'assessment'
            ? `ILearn-做题复盘-${nick}-${day}.pdf`
            : `ILearn-学习报告-${nick}-${day}.pdf`
        await api.downloadExport(sessionId, kind, filename)
      }
      if (backend === 'fpdf2') {
        // User already sees pdf-backend-indicator in plan step; brief alert on fallback export.
        window.alert('当前使用备选 PDF 引擎，排版可能与高清预览略有差异。')
      }
    } finally {
      setBusy(false)
    }
  }

  const engineLabel =
    backend === 'weasyprint' ? '高清引擎' : backend === 'fpdf2' ? '备选引擎' : null

  return (
    <button
      className={className}
      type="button"
      disabled={disabled || busy}
      onClick={() => void onExport()}
    >
      {busy ? '生成中…' : label || defaultLabel}
      {engineLabel ? (
        <span className="pdf-export-engine-badge" aria-label={`PDF 引擎：${engineLabel}`}>
          {engineLabel}
        </span>
      ) : null}
    </button>
  )
}
