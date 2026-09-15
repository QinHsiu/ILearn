import type { AssessmentItem } from '../api/client'

type TeacherCurriculumPreviewProps = {
  items: AssessmentItem[]
}

/** Teacher Why-Use: preview item-level curriculum citations before assign. */
export default function TeacherCurriculumPreview({ items }: TeacherCurriculumPreviewProps) {
  const withRefs = items.filter((item) => (item.source_refs || []).length > 0)
  if (!withRefs.length) return null

  return (
    <section className="teacher-curriculum-preview" aria-labelledby="teacher-curr-preview-title">
      <h3 id="teacher-curr-preview-title">题级课标预览</h3>
      <p className="lede">布置前可核对章节与置信度；不展示终答。</p>
      <ul className="curriculum-preview-list">
        {withRefs.slice(0, 8).map((item) => {
          const ref = (item.source_refs || [])[0]
          const chapters = ref?.textbook_chapter || '—'
          const confidence =
            typeof ref?.confidence === 'number' ? `${Math.round(ref.confidence * 100)}%` : '—'
          const objectives = ref?.curriculum_objective_ids?.join('、') || '—'
          return (
            <li key={item.id}>
              <strong>{item.id}</strong>
              <span>章节：{chapters}</span>
              <span>课标：{objectives}</span>
              <span>置信度：{confidence}</span>
            </li>
          )
        })}
      </ul>
    </section>
  )
}
