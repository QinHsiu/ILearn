import MarkdownView from '../MarkdownView'

type ReportColumnsViewProps = {
  source: string
  splitHeading?: string
  leftLabel?: string
  rightLabel?: string
}

export default function ReportColumnsView({
  source,
  splitHeading = '科学学习方法',
  leftLabel = '每日安排与目标',
  rightLabel = '科学学习方法',
}: ReportColumnsViewProps) {
  const normalized = source.replace(/\r\n/g, '\n')
  const marker = `## ${splitHeading}`
  const needle = `\n${marker}`
  const idx = normalized.indexOf(needle)
  const hasSplit = idx >= 0 || normalized.startsWith(marker)

  if (!hasSplit) {
    return (
      <div className="report-columns report-columns--single">
        <MarkdownView source={source} />
      </div>
    )
  }

  const left = idx >= 0 ? normalized.slice(0, idx).trim() : ''
  const right = idx >= 0 ? normalized.slice(idx + 1).trim() : normalized.trim()

  return (
    <div className="report-columns">
      <section className="report-col report-col-left" aria-label={leftLabel}>
        <p className="report-col-label">{leftLabel}</p>
        <MarkdownView source={left || '暂无内容'} />
      </section>
      <section className="report-col report-col-right" aria-label={rightLabel}>
        <p className="report-col-label">{rightLabel}</p>
        <MarkdownView source={right || '暂无内容'} />
      </section>
    </div>
  )
}
