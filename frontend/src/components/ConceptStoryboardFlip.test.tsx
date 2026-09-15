import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import ConceptStoryboardFlip from './ConceptStoryboardFlip'

const STEPS = ['数位对齐', '分步相乘', '相加核对']

describe('ConceptStoryboardFlip', () => {
  it('pages through three script frames without opening a new tab or leaking a final answer', () => {
    render(
      <ConceptStoryboardFlip
        title="三位数乘法竖式"
        scriptSteps={STEPS}
        posterUrl="/pilot-assets/concept/mult_3digit.svg"
      />,
    )
    expect(screen.getByRole('region', { name: /概念分镜/ })).toBeInTheDocument()
    expect(screen.getByText(/第 1 \/ 3 镜/)).toBeInTheDocument()
    expect(screen.getByText('数位对齐')).toBeInTheDocument()
    expect(screen.queryByText('分步相乘')).not.toBeInTheDocument()
    expect(screen.getByRole('button', { name: '上一镜' })).toBeDisabled()
    expect(screen.getByText(/不含终答/)).toBeInTheDocument()
    expect(screen.queryByText(/最终答案/)).not.toBeInTheDocument()
    expect(screen.queryByText(/\d+\.\d+/)).not.toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: '下一镜' }))
    expect(screen.getByText(/第 2 \/ 3 镜/)).toBeInTheDocument()
    expect(screen.getByText('分步相乘')).toBeInTheDocument()
    expect(screen.queryByText('数位对齐')).not.toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: '下一镜' }))
    expect(screen.getByText(/第 3 \/ 3 镜/)).toBeInTheDocument()
    expect(screen.getByText('相加核对')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: '下一镜' })).toBeDisabled()
  })
})
