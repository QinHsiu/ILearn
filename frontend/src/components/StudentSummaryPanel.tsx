import { useEffect, useState } from 'react'
import { api } from '../api/client'
import type { StudentSummary } from '../api/client'
import { EnhancedStudentPanel } from './Enhanced'

type StudentSummaryPanelProps = {
  sessionId: string
  nickname?: string | null
}

export default function StudentSummaryPanel({ sessionId, nickname }: StudentSummaryPanelProps) {
  const [data, setData] = useState<StudentSummary | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [streak, setStreak] = useState<number | null>(null)
  const [chainFocus, setChainFocus] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    setError(null)
    setData(null)
    void api
      .getStudentSummary(sessionId)
      .then((summary) => {
        if (!cancelled) setData(summary)
      })
      .catch((err) => {
        if (!cancelled) setError(err instanceof Error ? err.message : String(err))
      })
    return () => {
      cancelled = true
    }
  }, [sessionId])

  useEffect(() => {
    const name = (nickname || '').trim()
    if (!name) {
      setStreak(null)
      setChainFocus(null)
      return
    }
    let cancelled = false
    void api
      .getLearnerContinuity(name)
      .then((view) => {
        if (cancelled) return
        setStreak(view.streak_days)
        setChainFocus(view.seven_day_chain[0]?.focus || view.next_challenge)
      })
      .catch(() => {
        if (!cancelled) {
          setStreak(null)
          setChainFocus(null)
        }
      })
    return () => {
      cancelled = true
    }
  }, [nickname])

  if (error) {
    return (
      <p className="error" role="alert">
        {error}
      </p>
    )
  }
  if (!data) {
    return <p>加载中…</p>
  }

  return (
    <>
      <section className="student-summary-panel" aria-label="学生任务摘要">
        <p className="student-summary-eyebrow">MASTERY / PROGRESS</p>
        {streak != null ? (
          <p className="companion-strip" aria-label="陪伴连续">
            陪伴连续 <strong>{streak}</strong> 天
            {chainFocus ? ` · 今日焦点：${chainFocus}` : ''}
          </p>
        ) : null}
        {data.mastery_percent != null ? (
          <p className="student-mastery-strip" aria-label="掌握度进展">
            <span className="student-mastery-kicker">掌握度北极星 · </span>
            当前约 <strong>{data.mastery_percent}%</strong>
            {data.mastery_change_pp != null && data.mastery_change_pp !== 0
              ? `（${data.mastery_change_pp > 0 ? '+' : ''}${data.mastery_change_pp}pp）`
              : ''}
            {data.focus_skill ? ` · 本周重点：${data.focus_skill}` : ''}
            {data.evidence_count != null ? ` · 证据 ${data.evidence_count}` : ''}
            {data.probe_gap_count != null ? ` · probe缺口 ${data.probe_gap_count}` : ''}
            {data.discounted_hint_correct != null && data.discounted_hint_correct > 0
              ? ` · 提示后做对不计掌握 ${data.discounted_hint_correct}`
              : ''}
          </p>
        ) : (
          <p className="student-mastery-strip" aria-label="掌握度进展">
            <span className="student-mastery-kicker">掌握度北极星 · </span>
            完成练习后将更新你的掌握度进展
          </p>
        )}
        <div className="summary-grid student-summary-grid">
          <article className="summary-block">
            <span>当前任务</span>
            <strong>{data.current_task}</strong>
          </article>
          <article className="summary-block">
            <span>任务进度</span>
            <strong>
              {data.completed_tasks} / {data.total_tasks}
            </strong>
          </article>
          <article className="summary-block" aria-label="获得星星">
            <span>获得星星</span>
            <strong>{data.stars_earned}</strong>
          </article>
          <article className="summary-block summary-block-challenge">
            <span>下一挑战</span>
            <strong>{data.next_challenge}</strong>
          </article>
        </div>
        {data.narrative ? <p className="student-summary-narrative">{data.narrative}</p> : null}
      </section>
      <EnhancedStudentPanel sessionId={sessionId} viewMode="student" summaryKind="student" />
    </>
  )
}
