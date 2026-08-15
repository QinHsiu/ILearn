import type { SourceRef } from '../api/client'

type CitationPanelProps = {
  items: Array<{
    itemId: string
    stem: string
    sourceRefs?: SourceRef[] | null
  }>
}

function valueOrDash(value: string | null | undefined) {
  return value?.trim() || '—'
}

function referenceRows(ref: SourceRef) {
  return [
    ['课标条目', ref.curriculum_objective_ids?.join('、')],
    ['教材章节', ref.textbook_chapter],
    ['例题原文', ref.example_stem],
    ['例题答案', ref.example_answer],
    ['例题难度', ref.example_difficulty],
    ['来源', ref.source_label],
    ['例题编号', ref.example_id],
  ] as const
}

export default function CitationPanel({ items }: CitationPanelProps) {
  if (items.length === 0) {
    return <p className="citation-panel-empty">暂无错题可追溯来源。</p>
  }

  return (
    <div className="citation-panel">
      <div className="citation-panel-heading">
        <h3>错题来源追溯</h3>
        <span>共 {items.length} 道错题</span>
      </div>
      {items.map((item) => (
        <details className="citation-item" key={item.itemId}>
          <summary>
            <span className="citation-marker" aria-hidden="true">
              ▸
            </span>
            <span>{item.stem.slice(0, 80)}{item.stem.length > 80 ? '…' : ''}</span>
          </summary>
          <div className="citation-body">
            {item.sourceRefs?.length ? (
              item.sourceRefs.map((ref, index) => (
                <div className="citation-reference" key={ref.example_id || `${item.itemId}-${index}`}>
                  {referenceRows(ref).map(([label, value]) => (
                    <div className="citation-row" key={label}>
                      <strong>{label}：</strong>
                      <span>{valueOrDash(value)}</span>
                    </div>
                  ))}
                </div>
              ))
            ) : (
              <div className="citation-no-source">暂无课标例题快照</div>
            )}
          </div>
        </details>
      ))}
    </div>
  )
}
