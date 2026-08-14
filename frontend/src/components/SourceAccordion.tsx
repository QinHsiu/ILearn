import type { SourceRef } from '../api/client'

type SourceAccordionProps = {
  stem: string
  sourceRefs?: SourceRef[] | null
}

function valueOrDash(value: string | null | undefined) {
  return value?.trim() || '—'
}

export default function SourceAccordion({
  stem,
  sourceRefs,
}: SourceAccordionProps) {
  return (
    <details className="expander">
      <summary>
        {stem.slice(0, 48)}
        {stem.length > 48 ? '…' : ''}
      </summary>
      <div className="body">
        {sourceRefs?.length ? (
          sourceRefs.map((ref, index) => {
            const rows = [
              ['课标条目', ref.curriculum_objective_ids?.join('、')],
              ['教材章节', ref.textbook_chapter],
              ['例题原文', ref.example_stem],
              ['例题答案', ref.example_answer],
              ['例题难度', ref.example_difficulty],
              ['来源', ref.source_label],
            ]
            return (
              <div key={ref.example_id || index}>
                {rows.map(([label, value]) => (
                  <div key={label}>
                    <strong>{label}：</strong>
                    {valueOrDash(value)}
                  </div>
                ))}
              </div>
            )
          })
        ) : (
          <div>暂无课标例题快照</div>
        )}
      </div>
    </details>
  )
}
