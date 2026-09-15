import { render, screen, waitFor } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import CompanionContinuityPanel from './CompanionContinuityPanel'
import { api } from '../api/client'

vi.mock('../api/client', async () => {
  const actual = await vi.importActual<typeof import('../api/client')>('../api/client')
  return {
    ...actual,
    api: {
      ...actual.api,
      getLearnerContinuity: vi.fn().mockResolvedValue({
        nickname: '小明',
        session_count: 3,
        streak_days: 2,
        next_challenge: '小数乘法',
        companion_line: '已连学 2 天。下一挑战：小数乘法。',
        seven_day_chain: [
          { day_index: 1, focus: '小数乘法', session_id: 's0' },
          { day_index: 2, focus: '待开启', session_id: null },
        ],
        progress_delta: {
          has_baseline: true,
          evidence_delta: 2,
          probe_gap_delta: -1,
          mastery_delta: 5,
          narrative: '比上次：证据更好；探针缺口更好。',
        },
      }),
    },
  }
})

describe('CompanionContinuityPanel', () => {
  it('renders companion line and next challenge', async () => {
    render(<CompanionContinuityPanel nickname="小明" showParentDelta />)
    await waitFor(() => {
      expect(api.getLearnerContinuity).toHaveBeenCalledWith('小明')
    })
    expect(await screen.findByText(/已连学 2 天/)).toBeInTheDocument()
    expect(screen.getAllByText('小数乘法').length).toBeGreaterThanOrEqual(1)
    expect(screen.getAllByText(/比上次/).length).toBeGreaterThanOrEqual(1)
    expect(screen.getByLabelText('比上次')).toBeInTheDocument()
  })
})
