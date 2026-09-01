import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import ReportColumnsView from './ReportColumnsView'

const PLAN = `# 学习计划

## 目标

突破小数乘法。

## 每日安排

### 第 1 天
- 复习错题

## 科学学习方法

### 任务
- **费曼讲解** · 小数乘法：讲解概念。
`

describe('ReportColumnsView', () => {
  it('splits plan markdown into two labeled columns', () => {
    render(<ReportColumnsView source={PLAN} />)

    expect(screen.getByLabelText('每日安排与目标')).toBeInTheDocument()
    expect(screen.getByLabelText('科学学习方法')).toBeInTheDocument()
    expect(screen.getByText('突破小数乘法。')).toBeInTheDocument()
    expect(screen.getByText(/费曼讲解/)).toBeInTheDocument()
    expect(screen.queryByText(/\[feynman\]/)).not.toBeInTheDocument()
  })
})
