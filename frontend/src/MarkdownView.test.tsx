import { render, screen, within } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import MarkdownView from './MarkdownView'

const MASTERY_TABLE = [
  '### 知识掌握',
  '',
  '| 知识点 | 得分率 | 掌握等级 | 关联题目 |',
  '| --- | ---: | --- | --- |',
  '| dec_mult | 40% | 薄弱 | g5_easy_choice_02__00 |',
  '| frac_add | 100% | 已掌握 | g5_medium_fill_01__03 |',
  '',
  '### 能力估算',
].join('\n')

describe('MarkdownView tables', () => {
  it('renders a markdown table as a real table with header and rows', () => {
    render(<MarkdownView source={MASTERY_TABLE} />)

    const table = screen.getByRole('table')
    expect(within(table).getByRole('columnheader', { name: '知识点' })).toBeInTheDocument()
    expect(within(table).getByRole('columnheader', { name: '掌握等级' })).toBeInTheDocument()
    expect(within(table).getByRole('cell', { name: 'dec_mult' })).toBeInTheDocument()
    expect(within(table).getByRole('cell', { name: '已掌握' })).toBeInTheDocument()
    expect(within(table).getAllByRole('row')).toHaveLength(3)
  })

  it('does not leak the alignment separator row into the output', () => {
    const { container } = render(<MarkdownView source={MASTERY_TABLE} />)

    expect(container.textContent).not.toContain('---')
    expect(container.querySelector('.md-table-fallback')).toBeNull()
  })

  it('applies column alignment from the separator row', () => {
    render(<MarkdownView source={MASTERY_TABLE} />)

    const rateCell = screen.getByRole('cell', { name: '40%' })
    expect(rateCell).toHaveStyle({ textAlign: 'right' })
  })

  it('still renders headings and lists around the table', () => {
    render(<MarkdownView source={MASTERY_TABLE} />)

    expect(screen.getByRole('heading', { name: '知识掌握' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: '能力估算' })).toBeInTheDocument()
  })
})
