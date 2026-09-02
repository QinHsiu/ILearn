import type { SessionState } from '../api/client'

type EvidenceEvent = {
  evidence_id?: string
  knowledge_id?: string
  correct?: boolean
  error_tag?: string | null
  hint_level?: string
  lane?: string
  item_id?: string
  created_at?: string
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

const ERROR_LABELS: Record<string, string> = {
  concept_gap: '概念偏差',
  calc_error: '计算失误',
  misread: '审题偏差',
  method_wrong: '方法不当',
  incomplete: '步骤不完整',
}

function eventStatus(ev: EvidenceEvent): 'correct' | 'wrong' | 'hint' {
  if (ev.hint_level && ev.hint_level !== 'none') return 'hint'
  return ev.correct ? 'correct' : 'wrong'
}

function eventDetail(ev: EvidenceEvent): string {
  const parts: string[] = []
  if (ev.lane) parts.push(ev.lane)
  if (ev.hint_level && ev.hint_level !== 'none') {
    parts.push(HINT_LABELS[ev.hint_level] || ev.hint_level)
  }
  if (ev.error_tag) parts.push(ERROR_LABELS[ev.error_tag] || ev.error_tag)
  return parts.join(' · ') || (ev.correct ? '作答正确' : '作答错误')
}

function knowledgeLabel(
  knowledgeId: string | undefined,
  mastery?: SessionState['diagnosis'],
): string {
  if (!knowledgeId) return '学习内容'
  const row = mastery?.knowledge_mastery?.find((item) => item.knowledge_id === knowledgeId)
  return row?.knowledge_name || knowledgeId
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

  const stats = {
    correct: log.filter((ev) => eventStatus(ev) === 'correct').length,
    wrong: log.filter((ev) => eventStatus(ev) === 'wrong').length,
    hint: log.filter((ev) => eventStatus(ev) === 'hint').length,
  }

  return (
    <section className="evidence-chain" aria-labelledby="evidence-chain-title">
      <div className="evidence-chain-head">
        <h3 id="evidence-chain-title">诊断依据 · 证据链</h3>
        <div className="evidence-chain-stats" aria-label="证据统计">
          <span className="evidence-stat ok">正确 {stats.correct}</span>
          <span className="evidence-stat weak">错误 {stats.wrong}</span>
          <span className="evidence-stat hint">提示 {stats.hint}</span>
        </div>
      </div>
      <p className="lede">以下记录展示系统如何从答题与提示行为得出学情结论。</p>
      <ul className="evidence-chain-list">
        {log.slice(0, 12).map((ev, index) => {
          const status = eventStatus(ev)
          const statusLabel =
            status === 'correct' ? '已掌握' : status === 'hint' ? '提示辅助' : '需加强'
          return (
            <li
              key={ev.evidence_id || `${ev.item_id}-${index}`}
              className={`evidence-item evidence-item-${status}`}
            >
              <span className="evidence-skill">
                {knowledgeLabel(ev.knowledge_id, detail.diagnosis)}
              </span>
              <span className={`evidence-status ${status === 'correct' ? 'ok' : 'weak'}`}>
                {statusLabel}
              </span>
              <span className="evidence-detail">{eventDetail(ev)}</span>
            </li>
          )
        })}
      </ul>
      {log.length > 12 ? (
        <p className="evidence-more">另有 {log.length - 12} 条证据未展示</p>
      ) : null}
      <footer className="evidence-chain-foot">
        基于 <strong>{log.length}</strong> 条学习记录生成诊断
        {confidence != null ? (
          <span>
            {' '}
            · 置信度{' '}
            <strong className={confidence >= 0.7 ? 'evidence-conf-high' : 'evidence-conf-mid'}>
              {Math.round(confidence * 100)}%
            </strong>
          </span>
        ) : null}
      </footer>
    </section>
  )
}
