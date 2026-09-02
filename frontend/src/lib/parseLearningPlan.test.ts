import { describe, expect, it } from 'vitest'
import { parseLearningPlan } from './parseLearningPlan'

const SAMPLE = `
### 任务
- **费曼讲解** · 分数乘法：请尝试用自己的话向别人解释「分数乘法」的概念。
- **前置复习** · 同分母分数加法：复习「同分母分数加法」，完成3道巩固题。
- **错题纠正** · 概念理解不清：针对概念混淆：先用自己的话解释定义，再做2道概念辨析题。
- **苏格拉底对话** · 分数乘法：与苏格拉底助教就「分数乘法」进行一次对话。

### 间隔复习
- 2026-09-03 · 分数乘法（第 1 次复习）
- 2026-09-05 · 分数乘法（第 2 次复习）

预估总用时：1.2 小时
`

describe('parseLearningPlan', () => {
  it('returns empty plan for invalid markdown input', () => {
    expect(parseLearningPlan(null)).toEqual({
      skills: [],
      tasks: [],
      spacedRepetitions: [],
    })
  })

  it('parses task lines and spaced repetition from scientific plan markdown', () => {
    const parsed = parseLearningPlan(SAMPLE)

    expect(parsed.tasks).toHaveLength(4)
    expect(parsed.tasks.map((t) => t.type)).toEqual([
      'feynman',
      'review',
      'correct',
      'socratic',
    ])
    expect(parsed.tasks[0].skill).toBe('分数乘法')
    expect(parsed.tasks[2].skill).toBe('通用')
    expect(parsed.spacedRepetitions).toHaveLength(2)
    expect(parsed.spacedRepetitions[0]).toMatchObject({
      date: '2026-09-03',
      skill: '分数乘法',
      repetition: 1,
    })
    expect(parsed.skills).toContain('分数乘法')
    expect(parsed.skills).toContain('同分母分数加法')
  })

  it('accepts dot separators in task lines', () => {
    const parsed = parseLearningPlan('- **费曼讲解**. 小数乘法：讲解概念。')
    expect(parsed.tasks).toHaveLength(1)
    expect(parsed.tasks[0].skill).toBe('小数乘法')
  })
})
