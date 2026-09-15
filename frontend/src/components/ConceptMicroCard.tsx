"""Concept micro-lesson card for soft-exit / report (no final answers)."""

import { useEffect, useState } from 'react'
import { api } from '../api/client'

type ConceptMicroCardProps = {
  sessionId: string
  itemId: string
}

export default function ConceptMicroCard({ sessionId, itemId }: ConceptMicroCardProps) {
  const [lesson, setLesson] = useState<{
    title: string
    duration_sec: number
    script_steps: string[]
    storyboard_url?: string | null
    poster_url?: string | null
    media_status?: string
  } | null>(null)

  useEffect(() => {
    let cancelled = false
    void api
      .getConceptLesson(sessionId, itemId)
      .then((data) => {
        if (!cancelled) setLesson(data.lesson)
      })
      .catch(() => {
        if (!cancelled) setLesson(null)
      })
    return () => {
      cancelled = true
    }
  }, [sessionId, itemId])

  if (!lesson) return null

  return (
    <aside className="concept-micro" aria-label="概念微课">
      <p className="concept-micro-title">
        <strong>{lesson.title}</strong>
        <span> · 约 {lesson.duration_sec} 秒</span>
        {lesson.storyboard_url ? (
          <>
            {' · '}
            <a href={lesson.storyboard_url} target="_blank" rel="noreferrer">
              打开分镜
            </a>
          </>
        ) : null}
      </p>
      {lesson.poster_url ? (
        <figure className="concept-poster">
          <img src={lesson.poster_url} alt={`${lesson.title} 分镜海报`} />
          <figcaption>不含终答 · 独立重试前先看一眼</figcaption>
        </figure>
      ) : null}
      <ol>
        {lesson.script_steps.map((step) => (
          <li key={step}>{step}</li>
        ))}
      </ol>
    </aside>
  )
}
