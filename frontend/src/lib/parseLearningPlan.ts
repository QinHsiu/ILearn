export type LearningTaskType = 'feynman' | 'review' | 'correct' | 'socratic'

export type LearningTask = {
  type: LearningTaskType
  skill: string
  description: string
}

export type SpacedRepetition = {
  skill: string
  date: string
  repetition: number
}

export type ParsedPlan = {
  skills: string[]
  tasks: LearningTask[]
  spacedRepetitions: SpacedRepetition[]
}

const EMPTY_PLAN: ParsedPlan = { skills: [], tasks: [], spacedRepetitions: [] }

function normalizeLine(line: string): string {
  let trimmed = line.trim()
  if (trimmed.startsWith('- ')) trimmed = trimmed.slice(2)
  return trimmed.replace(/\*\*/g, '').trim()
}

function stripInstructionSuffix(value: string): string {
  const colon = value.search(/[：:]/)
  return colon >= 0 ? value.slice(0, colon).trim() : value.trim()
}

export function parseLearningPlan(markdownText: string | null | undefined): ParsedPlan {
  if (!markdownText || typeof markdownText !== 'string') {
    return EMPTY_PLAN
  }

  const tasks: LearningTask[] = []
  const spacedReps: SpacedRepetition[] = []

  const feynmanRegex = /费曼讲解\s*[·.]\s*(.+)/i
  const reviewRegex = /前置复习\s*[·.]\s*(.+?)[：:]/i
  const correctRegex = /错题纠正\s*[·.]\s*(.+)/i
  const socraticRegex = /苏格拉底对话\s*[·.]\s*(.+)/i
  const spacedRegex = /(\d{4}-\d{2}-\d{2})\s*[·.]\s*(.+?)\s*（第\s*(\d+)\s*次复习）/

  for (const line of markdownText.split('\n')) {
    const trimmed = normalizeLine(line)
    if (!trimmed) continue
    if (trimmed.startsWith('#')) continue
    if (trimmed.startsWith('任务') || trimmed.startsWith('间隔复习')) continue
    if (trimmed.startsWith('预估总用时')) continue
    if (trimmed.includes('个复习节点')) continue
    if (trimmed.startsWith('---')) continue

    const feynmanMatch = trimmed.match(feynmanRegex)
    if (feynmanMatch) {
      tasks.push({
        type: 'feynman',
        skill: stripInstructionSuffix(feynmanMatch[1]),
        description: trimmed,
      })
      continue
    }

    const reviewMatch = trimmed.match(reviewRegex)
    if (reviewMatch) {
      tasks.push({
        type: 'review',
        skill: reviewMatch[1].trim(),
        description: trimmed,
      })
      continue
    }

    const correctMatch = trimmed.match(correctRegex)
    if (correctMatch) {
      tasks.push({
        type: 'correct',
        skill: '通用',
        description: trimmed,
      })
      continue
    }

    const socraticMatch = trimmed.match(socraticRegex)
    if (socraticMatch) {
      tasks.push({
        type: 'socratic',
        skill: stripInstructionSuffix(socraticMatch[1]),
        description: trimmed,
      })
      continue
    }

    const spacedMatch = trimmed.match(spacedRegex)
    if (spacedMatch) {
      spacedReps.push({
        date: spacedMatch[1],
        skill: spacedMatch[2].trim(),
        repetition: parseInt(spacedMatch[3], 10),
      })
    }
  }

  const skillSet = new Set<string>()
  tasks.forEach((task) => {
    if (task.skill !== '通用') skillSet.add(task.skill)
  })
  spacedReps.forEach((item) => skillSet.add(item.skill))

  return {
    skills: Array.from(skillSet),
    tasks,
    spacedRepetitions: spacedReps,
  }
}

export function hasLearningMethodsData(markdown: string): boolean {
  const parsed = parseLearningPlan(markdown)
  return parsed.skills.length > 0 || parsed.spacedRepetitions.length > 0
}

export type SpacedDateStatus = {
  label: string
  color: string
}

export function spacedDateStatus(dateStr: string): SpacedDateStatus {
  const today = new Date().toISOString().slice(0, 10)
  if (dateStr === today) {
    return { label: '今日', color: '#4CAF50' }
  }
  if (dateStr < today) {
    return { label: '已完成', color: '#9E9E9E' }
  }
  return { label: '待执行', color: '#FF9800' }
}
