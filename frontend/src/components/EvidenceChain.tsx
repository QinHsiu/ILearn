import type { SessionState } from '../api/client'

type EvidenceEvent = {
  evidence_id?: string
  knowledge_id?: string
  correct?: boolean
  error_tag?: string | null
  hint_level?: string
  lane?: string
  item_id?: string
}

type EvidenceChainProps = {
  detail: SessionState
}

const HINT_LABELS: Record<string, string> = {
  none: '无提示',
  low: '轻度提示',
  medium: '思路提示',
  high: '详细提示',
}

function eventDetail(ev: EvidenceEvent): string {
  const parts: string[] = []
  if (ev.lane) parts.push(ev.lane)
  if (ev.hint_level && ev.hint_level !== 'none') {
    parts.push(HINT_LABELS[ev.hint_level] || ev.hint_level)
  }
  if (ev.error_tag) parts.push(ev.error_tag)
  parts.push(ev.correct ? '答对' : '答错')
  return parts.join(' · ')
}

export default function EvidenceChain({ detail }: EvidenceChainProps) {
  const log = (detail.evidence_log || []) as EvidenceEvent[]
  const enrichment = detail.metadata?.diagnosis_enrichment as
    | { diagnosis_confidence?: { score?: number; label?: string } | number }
    | undefined
  const confRaw = enrichment?.diagnosis_confidence
  const confidence =
    typeof confRaw === 'object' && confRaw !== null && 'score' in confRaw
      ? confRaw.score
      : typeof confRaw === 'number'
        ? confRaw
        : null

  if (!log.length) {
    return null
  }

  return (
    <section className="evidence-chain" aria-labelledby="evidence-chain-title">
      <h3 id="evidence-chain-title">诊断依据</h3>
      <p className="lede">以下证据链展示系统如何得出学情诊断结论。</p>
      <ul className="evidence-chain-list">
        {log.slice(0, 12).map((ev, index) => (
          <li key={ev.evidence_id || `${ev.item_id}-${index}`} className="evidence-item">
            <span className="evidence-skill">{ev.knowledge_id || '知识点'}</span>
            <span className={`evidence-status ${ev.correct ? 'ok' : 'weak'}`}>
              {ev.correct ? '掌握' : '薄弱'}
            </span>
            <span className="evidence-detail">{eventDetail(ev)}</span>
          </li>
        ))}
      </ul>
      {log.length > 12 ? (
        <p className="evidence-more">另有 {log.length - 12} 条证据未展示</p>
      ) : null}
      {confidence != null ? (
        <p className="evidence-confidence">
          诊断置信度：{Math.round(confidence * 100)}%
        </p>
      ) : null}
    </section>
  )
}
