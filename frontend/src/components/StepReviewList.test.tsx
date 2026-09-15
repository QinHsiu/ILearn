import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import StepReviewList from './StepReviewList'
import { api } from '../api/client'

vi.mock('../api/client', async () => {
  const actual = await vi.importActual<typeof import('../api/client')>('../api/client')
  return {
    ...actual,
    api: {
      ...actual.api,
      requestUnlock: vi.fn().mockResolvedValue({
        session_id: 's1',
        request: { item_id: 'q1', status: 'pending' },
      }),
    },
  }
})

describe('StepReviewList (Round 3 · Photomath steps)', () => {
  it('renders rubric steps without exposing a numeric final answer label', async () => {
    render(
      <StepReviewList
        sessionId="s1"
        items={[
          {
            itemId: 'q1',
            stem: '计算 1.2×3',
            rubricSteps: ['对齐小数位', '相乘', '点小数点'],
            studentAnswer: '对齐小数位\n乱写一步',
          },
        ]}
        allowUnlockRequest
      />,
    )
    expect(screen.getByRole('heading', { name: /分步复盘/ })).toBeInTheDocument()
    expect(document.querySelector('.step-align--matched')).toBeTruthy()
    expect(screen.getByText(/终答已遮罩/)).toBeInTheDocument()
    const unlock = screen.getByRole('button', { name: /申请教师\/家长解锁终答/ })
    expect(unlock).toBeInTheDocument()
    expect(screen.queryByText(/最终答案\s*[:=]/)).not.toBeInTheDocument()
    fireEvent.click(unlock)
    await waitFor(() => {
      expect(api.requestUnlock).toHaveBeenCalledWith('s1', 'q1')
    })
    expect(await screen.findByText(/已向教师\/家长发起终答解锁申请/)).toBeInTheDocument()
  })
})
