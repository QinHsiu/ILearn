import { useState } from 'react'

type ConceptStoryboardFlipProps = {
  title: string
  scriptSteps: string[]
  posterUrl?: string | null
}

/** In-app 3-frame concept storyboard — one step at a time, no new tab, no final answer. */
export default function ConceptStoryboardFlip({
  title,
  scriptSteps,
  posterUrl,
}: ConceptStoryboardFlipProps) {
  const total = scriptSteps.length
  const lastIndex = Math.max(0, total - 1)
  const [index, setIndex] = useState(0)
  const frame = total === 0 ? 0 : index + 1
  const current = scriptSteps[index] ?? ''

  return (
    <section className="concept-storyboard" role="region" aria-label="概念分镜">
      <header className="concept-storyboard-head">
        <p className="concept-storyboard-kicker">第 {frame} / {total} 镜</p>
        <p className="concept-storyboard-mask">不含终答</p>
      </header>
      {posterUrl ? (
        <figure className="concept-poster">
          <img src={posterUrl} alt={`${title} 分镜海报`} />
          <figcaption>分步翻看，独立重试前先看一眼</figcaption>
        </figure>
      ) : null}
      {current ? (
        <p className="concept-storyboard-step" aria-live="polite">
          {current}
        </p>
      ) : null}
      <div className="concept-storyboard-nav">
        <button
          type="button"
          className="btn secondary"
          disabled={index <= 0}
          onClick={() => setIndex((value) => Math.max(0, value - 1))}
        >
          上一镜
        </button>
        <button
          type="button"
          className="btn"
          disabled={index >= lastIndex}
          onClick={() => setIndex((value) => Math.min(lastIndex, value + 1))}
        >
          下一镜
        </button>
      </div>
    </section>
  )
}
