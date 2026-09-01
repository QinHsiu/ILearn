import { useState } from 'react'
import type { CountingTakeawaySpec } from '../lib/inferManipulative'

type Props = {
  spec: CountingTakeawaySpec
  onRemainingChange?: (remaining: number) => void
}

export default function CountingManipulative({ spec, onRemainingChange }: Props) {
  const [removed, setRemoved] = useState<Set<number>>(() => new Set())

  function toggle(index: number) {
    setRemoved((prev) => {
      const next = new Set(prev)
      if (next.has(index)) {
        next.delete(index)
      } else if (next.size < spec.takeAway) {
        next.add(index)
      }
      const remaining = spec.total - next.size
      onRemainingChange?.(remaining)
      return next
    })
  }

  const removedCount = removed.size
  const remaining = spec.total - removedCount

  return (
    <div className="counting-manipulative" aria-label={`${spec.objectLabel}情境操作`}>
      <p className="counting-manipulative-hint">
        点击 {spec.takeAway} 个{spec.objectLabel}表示「吃掉」，看看还剩几个。
      </p>
      <div className="counting-object-grid">
        {Array.from({ length: spec.total }).map((_, index) => {
          const isRemoved = removed.has(index)
          return (
            <button
              key={index}
              type="button"
              className={`counting-object${isRemoved ? ' is-removed' : ''}`}
              onClick={() => toggle(index)}
              aria-pressed={isRemoved}
              aria-label={`${spec.objectLabel} ${index + 1}${isRemoved ? '，已吃掉' : ''}`}
            >
              <span className="counting-object-icon" aria-hidden="true">
                {spec.objectLabel === '苹果' ? '🍎' : '●'}
              </span>
            </button>
          )
        })}
      </div>
      <div className="counting-manipulative-meta">
        <span>已标记 {removedCount} / {spec.takeAway}</span>
        <span>
          还剩 <strong>{remaining}</strong> 个
        </span>
      </div>
    </div>
  )
}
