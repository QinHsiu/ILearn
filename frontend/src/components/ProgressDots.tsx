type ProgressDotsProps = {
  total: number
  current: number
  answered: Record<string, string>
  questionIds: string[]
  onSelect: (index: number) => void
}

export default function ProgressDots({
  total,
  current,
  answered,
  questionIds,
  onSelect,
}: ProgressDotsProps) {
  return (
    <div className="progress-dots" role="navigation" aria-label="题目进度">
      {Array.from({ length: total }).map((_, idx) => {
        const qid = questionIds[idx]
        const isAnswered = Boolean(qid && (answered[qid] || '').trim())
        const isCurrent = idx === current
        return (
          <button
            key={qid || idx}
            type="button"
            className={`progress-dot${isCurrent ? ' current' : ''}${isAnswered ? ' answered' : ''}`}
            onClick={() => onSelect(idx)}
            title={`第 ${idx + 1} 题${isAnswered ? '（已答）' : ''}`}
            aria-label={`第 ${idx + 1} 题${isAnswered ? '，已答' : ''}`}
            aria-current={isCurrent ? 'true' : undefined}
          >
            <span className="progress-dot-num" aria-hidden="true">
              {idx + 1}
            </span>
          </button>
        )
      })}
    </div>
  )
}
