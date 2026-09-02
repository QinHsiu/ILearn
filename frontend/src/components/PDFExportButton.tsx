import { useEffect, useState } from 'react'
import { api, DownloadHttpError } from '../api/client'

type PDFExportButtonProps = {
  sessionId: string
  kind: 'assessment' | 'report' | 'effectiveness'
  label?: string
  className?: string
  disabled?: boolean
  nickname?: string | null
  onError?: (message: string) => void
}

function pdfErrorMessage(error: unknown): string {
  if (error instanceof DownloadHttpError) {
    const detail = error.detail
    if (error.status === 503) {
      if (
        typeof detail === 'object' &&
        detail !== null &&
        'code' in detail &&
        (detail as { code?: string }).code === 'PDF_UNAVAILABLE'
      ) {
        return 'PDF 渲染引擎未就绪，请稍后重试或联系管理员检查依赖。'
      }
      if (typeof detail === 'object' && detail !== null && 'message' in detail) {
        return String((detail as { message?: string }).message)
      }
    }
    if (error.status === 500) {
      return '服务器内部错误，请稍后重试。'
    }
    return error.message || '导出失败，请稍后重试。'
  }
  if (error instanceof TypeError) {
    return '网络连接异常，请检查网络后重试。'
  }
  if (error instanceof Error && error.message) {
    return error.message
  }
  return '导出失败，请稍后重试。'
}

export default function PDFExportButton({
  sessionId,
  kind,
  label,
  className = 'btn secondary',
  disabled = false,
  nickname,
  onError,
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
      let usedBackend: string | null = backend
      if (kind === 'effectiveness') {
        const result = await api.exportEffectivenessPdf(sessionId)
        usedBackend = result.backend
      } else {
        const nick = (nickname || '').trim() || '未命名'
        const day = new Date().toISOString().slice(0, 10)
        const filename =
          kind === 'assessment'
            ? `ILearn-做题复盘-${nick}-${day}.pdf`
            : `ILearn-学习报告-${nick}-${day}.pdf`
        const result = await api.downloadExport(sessionId, kind, filename)
        usedBackend = result.backend
      }
      if (usedBackend === 'fpdf2') {
        window.alert('当前使用备选 PDF 引擎，排版可能与高清预览略有差异，但内容完整。')
      }
    } catch (error) {
      const message = pdfErrorMessage(error)
      if (onError) {
        onError(message)
      } else {
        window.alert(message)
      }
      console.error('PDF export failed:', error)
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
