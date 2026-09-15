import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import TutorPanel from './TutorPanel'
import { api } from '../api/client'

vi.mock('../api/client', async () => {
  const actual = await vi.importActual<typeof import('../api/client')>('../api/client')
  return {
    ...actual,
    api: {
      ...actual.api,
      tutorStart: vi.fn(),
      tutorHint: vi.fn(),
    },
  }
})

describe('TutorPanel (Round 1 · Khanmigo ethics)', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('shows Socratic tutor heading, ethics note, and start action', () => {
    render(<TutorPanel sessionId="s1" itemId="q1" />)

    expect(screen.getByRole('heading', { name: '苏格拉底助教' })).toBeInTheDocument()
    expect(screen.getByRole('note')).toHaveTextContent(/不直接给出最终答案/)
    expect(screen.getByRole('button', { name: '开始辅导' })).toBeInTheDocument()
  })

  it('shows soft-exit status and hides next-hint when suggest_review', async () => {
    vi.mocked(api.tutorStart).mockResolvedValue({
      phase: 'locate_gap',
      message: '我们先定位卡点',
    })
    vi.mocked(api.tutorHint).mockResolvedValue({
      phase: 'done',
      message: '请先回顾概念',
      action: 'suggest_review',
    })

    render(<TutorPanel sessionId="s1" itemId="q1" />)
    fireEvent.click(screen.getByRole('button', { name: '开始辅导' }))
    await screen.findByText('我们先定位卡点')

    fireEvent.change(screen.getByLabelText(/告诉助教你的想法/), {
      target: { value: '还是不会' },
    })
    fireEvent.click(screen.getByRole('button', { name: '下一提示' }))

    await waitFor(() => {
      expect(screen.getByRole('status')).toHaveTextContent(/不会直接给出最终数值答案/)
    })
    expect(screen.queryByRole('button', { name: '下一提示' })).not.toBeInTheDocument()
  })
})
