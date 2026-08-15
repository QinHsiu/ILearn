import type { ReactNode } from 'react'

type FocusedHintLayoutProps = {
  title?: string
  onExit: () => void
  questionSlot: ReactNode
  panelSlot: ReactNode
}

export default function FocusedHintLayout({
  title = '专注模式 · 当前题目',
  onExit,
  questionSlot,
  panelSlot,
}: FocusedHintLayoutProps) {
  return (
    <div className="focused-hint">
      <div className="focused-hint-top">
        <button className="btn secondary" type="button" onClick={onExit}>
          ← 返回整体测评
        </button>
        <span className="focused-hint-label">{title}</span>
      </div>
      <div className="focused-hint-body">
        <div className="focused-hint-question">{questionSlot}</div>
        <div className="focused-hint-panel">{panelSlot}</div>
      </div>
    </div>
  )
}
