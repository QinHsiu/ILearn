import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { KnowledgeRadar } from './KnowledgeRadar'

describe('KnowledgeRadar', () => {
  it('shows downgrade message when fewer than 3 concepts', () => {
    render(
      <KnowledgeRadar
        knowledgeMastery={{ 分数: 0.2, 小数: 0.5 }}
      />,
    )

    expect(
      screen.getByText('数据不足，暂无法绘制（需至少 3 个知识点）'),
    ).toBeInTheDocument()
    expect(screen.queryByRole('img')).not.toBeInTheDocument()
  })

  it('renders SVG radar with at least 3 concepts', () => {
    render(
      <KnowledgeRadar
        knowledgeMastery={{
          分数: 0.2,
          小数: 0.5,
          几何: 0.8,
        }}
      />,
    )

    expect(screen.getByRole('img', { name: '知识点掌握度雷达图' })).toBeInTheDocument()
    expect(
      screen.queryByText('数据不足，暂无法绘制（需至少 3 个知识点）'),
    ).not.toBeInTheDocument()
  })

  it('sorts concepts ascending by mastery (weakest first)', () => {
    const { container } = render(
      <KnowledgeRadar
        knowledgeMastery={{
          高掌握: 0.9,
          中掌握: 0.5,
          低掌握: 0.1,
        }}
      />,
    )

    const labels = Array.from(container.querySelectorAll('text'))
      .map((el) => el.childNodes[0]?.textContent)
      .filter(Boolean)

    expect(labels[0]).toBe('低掌握')
    expect(labels[1]).toBe('中掌握')
    expect(labels[2]).toBe('高掌握')
  })

  it('truncates labels to 6 chars plus ellipsis', () => {
    const { container } = render(
      <KnowledgeRadar
        knowledgeMastery={{
          abcdefghijklmnop: 0.2,
          分数加减法运算: 0.3,
          小数: 0.5,
        }}
      />,
    )

    const labelTitles = Array.from(container.querySelectorAll('text title')).map(
      (el) => el.textContent,
    )
    expect(labelTitles).toContain('abcdefghijklmnop')
    expect(labelTitles).toContain('分数加减法运算')

    const labelTexts = Array.from(container.querySelectorAll('text'))
      .map((el) => el.childNodes[0]?.textContent)
      .filter(Boolean)

    expect(labelTexts).toContain('abcdef…')
    expect(labelTexts).toContain('分数加减法运…')
  })

  it('limits to max 8 concepts', () => {
    const mastery: Record<string, number> = {}
    for (let i = 1; i <= 10; i += 1) {
      mastery[`概念${i}`] = i * 0.05
    }

    const { container } = render(<KnowledgeRadar knowledgeMastery={mastery} />)

    const labels = container.querySelectorAll('text')
    expect(labels.length).toBe(8)
  })
})
