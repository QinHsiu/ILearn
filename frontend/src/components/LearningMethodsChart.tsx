import { useMemo } from 'react'
import {
  parseLearningPlan,
  type LearningTask,
  type LearningTaskType,
} from '../lib/parseLearningPlan'
import './LearningMethodsChart.css'

type LearningMethodsChartProps = {
  markdown: string
  estimatedHours?: number
}

type TaskBucket = Partial<Record<LearningTaskType, LearningTask>>

const BADGE_COLORS: Record<LearningTaskType, string> = {
  feynman: '#E8F5E9',
  review: '#E3F2FD',
  correct: '#FFF3E0',
  socratic: '#F3E5F5',
}

const BADGE_EMOJI: Record<LearningTaskType, string> = {
  feynman: '🧠',
  review: '📚',
  correct: '✏️',
  socratic: '💬',
}

function MethodBadge({ type }: { type: LearningTaskType }) {
  return (
    <span className="method-badge" style={{ background: BADGE_COLORS[type] }}>
      {BADGE_EMOJI[type]}
    </span>
  )
}

export default function LearningMethodsChart({
  markdown,
  estimatedHours,
}: LearningMethodsChartProps) {
  const parsed = useMemo(() => parseLearningPlan(markdown), [markdown])
  const { skills, tasks, spacedRepetitions } = parsed

  const taskMap = useMemo(() => {
    const map = new Map<string, TaskBucket>()
    skills.forEach((skill) => map.set(skill, {}))

    tasks.forEach((task) => {
      const key = task.skill === '通用' ? '通用' : task.skill
      if (!map.has(key)) map.set(key, {})
      const entry = map.get(key)!
      entry[task.type] = task
    })
    return map
  }, [skills, tasks])

  const spacedMap = useMemo(() => {
    const map = new Map<string, typeof spacedRepetitions>()
    spacedRepetitions.forEach((item) => {
      if (!map.has(item.skill)) map.set(item.skill, [])
      map.get(item.skill)!.push(item)
    })
    return map
  }, [spacedRepetitions])

  const matrixSkills = useMemo(() => {
    const ordered = [...skills]
    if (taskMap.has('通用')) ordered.push('通用')
    return ordered
  }, [skills, taskMap])

  if (matrixSkills.length === 0 && spacedRepetitions.length === 0) {
    return <div className="learning-methods-empty">暂无学习方法数据</div>
  }

  return (
    <div className="learning-methods-chart">
      <div className="chart-header">
        <h3>科学学习方法全景</h3>
        <div className="stats-badge">
          <span>{tasks.length} 项任务</span>
          <span>{spacedRepetitions.length} 次间隔复习</span>
          <span>{skills.length} 个知识点</span>
        </div>
      </div>

      {typeof estimatedHours === 'number' && estimatedHours > 0 ? (
        <p className="learning-methods-hours">预估总用时：约 {estimatedHours.toFixed(1)} 小时</p>
      ) : null}

      <div className="matrix-container">
        <table className="method-matrix">
          <thead>
            <tr>
              <th className="skill-col">知识点</th>
              <th>费曼讲解</th>
              <th>前置复习</th>
              <th>苏格拉底</th>
              <th>错题纠正</th>
              <th className="spaced-col">间隔复习</th>
            </tr>
          </thead>
          <tbody>
            {matrixSkills.map((skill) => {
              const rowTasks = taskMap.get(skill) || {}
              const spaced = spacedMap.get(skill) || []
              const hasAny =
                rowTasks.feynman ||
                rowTasks.review ||
                rowTasks.socratic ||
                rowTasks.correct ||
                spaced.length > 0
              if (!hasAny) return null

              return (
                <tr key={skill}>
                  <td className="skill-cell">
                    <span className="skill-name">{skill}</span>
                  </td>
                  <td>
                    {rowTasks.feynman ? (
                      <MethodBadge type="feynman" />
                    ) : (
                      <span className="empty-dot">·</span>
                    )}
                  </td>
                  <td>
                    {rowTasks.review ? (
                      <MethodBadge type="review" />
                    ) : (
                      <span className="empty-dot">·</span>
                    )}
                  </td>
                  <td>
                    {rowTasks.socratic ? (
                      <MethodBadge type="socratic" />
                    ) : (
                      <span className="empty-dot">·</span>
                    )}
                  </td>
                  <td>
                    {rowTasks.correct ? (
                      <MethodBadge type="correct" />
                    ) : (
                      <span className="empty-dot">·</span>
                    )}
                  </td>
                  <td className="spaced-cell">
                    {spaced.length > 0 ? (
                      <div className="spaced-dots">
                        {spaced.map((item, index) => (
                          <span
                            key={`${item.date}-${item.repetition}-${index}`}
                            className="spaced-dot"
                            title={`第${item.repetition}次复习: ${item.date}`}
                          >
                            {item.repetition}
                          </span>
                        ))}
                      </div>
                    ) : (
                      <span className="empty-dot">·</span>
                    )}
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>

      <div className="legend">
        <span className="legend-item">已规划</span>
        <span className="legend-item">· 待安排</span>
        <span className="legend-item">
          <span className="spaced-dot-example">1</span>
          间隔复习次数
        </span>
      </div>

      {spacedRepetitions.length > 0 ? (
        <div className="spaced-timeline">
          <h4>间隔复习时间轴</h4>
          <div className="timeline-grid">
            {spacedRepetitions.map((item, index) => (
              <div key={`${item.date}-${item.skill}-${index}`} className="timeline-item">
                <span className="timeline-date">{item.date}</span>
                <span className="timeline-skill">{item.skill}</span>
                <span className="timeline-rep">第{item.repetition}次</span>
              </div>
            ))}
          </div>
        </div>
      ) : null}
    </div>
  )
}
