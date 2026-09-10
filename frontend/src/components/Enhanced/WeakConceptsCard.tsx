import styles from './enhanced.module.css'

interface WeakConceptsCardProps {
  weakConcepts: string[]
  viewMode: 'student' | 'teacher'
}

export function WeakConceptsCard({ weakConcepts, viewMode }: WeakConceptsCardProps) {
  const title = viewMode === 'student' ? '待加强' : '薄弱知识点'
  const emptyText =
    viewMode === 'student'
      ? '暂无需加强的内容，继续保持！'
      : '暂无明显薄弱点'

  const list = (weakConcepts || []).slice(0, 8)

  return (
    <div className={styles.card}>
      <div className={styles.cardTitle}>{title}</div>
      {list.length === 0 ? (
        <div className={styles.mutedText}>{emptyText}</div>
      ) : (
        <div className={styles.chipList}>
          {list.map((c, i) => (
            <span key={`${c}-${i}`} className={styles.chip} title={c}>
              {c}
            </span>
          ))}
        </div>
      )}
    </div>
  )
}
