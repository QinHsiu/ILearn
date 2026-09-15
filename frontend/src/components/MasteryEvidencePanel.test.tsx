import { render, screen, waitFor } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import MasteryEvidencePanel from './MasteryEvidencePanel'
import { api } from '../api/client'

vi.mock('../api/client', async () => {
  const actual = await vi.importActual<typeof import('../api/client')>('../api/client')
  return {
    ...actual,
    api: {
      ...actual.api,
      getMasteryPublic: vi.fn().mockResolvedValue({
        session_id: 's1',
        mastery_percent: 72,
        evidence_count: 5,
        probe_gap_count: 2,
        discounted_hint_correct: 1,
      }),
    },
  }
})

describe('MasteryEvidencePanel', () => {
  it('renders the mastery evidence quadruple', async () => {
    render(<MasteryEvidencePanel sessionId="s1" />)
    expect(await screen.findByRole('heading', { name: /掌握证据/ })).toBeInTheDocument()
    await waitFor(() => {
      expect(api.getMasteryPublic).toHaveBeenCalledWith('s1')
    })
    expect(screen.getByText('72%')).toBeInTheDocument()
    expect(screen.getByText('提示后做对（未计掌握）')).toBeInTheDocument()
    expect(screen.getByText('探针缺口')).toBeInTheDocument()
  })
})
