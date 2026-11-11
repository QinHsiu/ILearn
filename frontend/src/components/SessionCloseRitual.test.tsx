import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import SessionCloseRitual from './SessionCloseRitual'
import { api } from '../api/client'

vi.mock('../api/client', async () => {
  const actual = await vi.importActual<typeof import('../api/client')>('../api/client')
  return {
    ...actual,
    api: {
      ...actual.api,
      getSessionClose: vi.fn(),
      stampSessionClose: vi.fn(),
    },
  }
})

const OPEN = {
  closed: false,
  closed_at: null,
  headline: '今天先到这里 · 证据 1 条',
  next_challenge: '小数乘法',
  evidence_count: 1,
  probe_gap_count: 1,
  parent_line: '孩子今天还没收工。下一挑战：小数乘法。',
  honesty_note: '提示后做对不计入掌握；收工卡不含终答。',
}

describe('SessionCloseRitual', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(api.getSessionClose).mockResolvedValue(OPEN)
    vi.mocked(api.stampSessionClose).mockResolvedValue({
      ...OPEN,
      closed: true,
      closed_at: '2026-09-16T12:00:00+00:00',
      headline: '今天收工了 · 证据 1 条',
      parent_line: '孩子今天收工了。下一挑战：小数乘法。不含终答。',
    })
  })

  it('lets the student close today and never shows a final answer', async () => {
    render(<SessionCloseRitual sessionId="s1" />)
    await waitFor(() => expect(api.getSessionClose).toHaveBeenCalledWith('s1'))
    const region = await screen.findByRole('region', { name: /今天收工/ })
    expect(screen.getByText(/今天先到这里/)).toBeInTheDocument()
    expect(screen.getByText(/小数乘法/)).toBeInTheDocument()
    expect(screen.queryByText(/最终答案/)).not.toBeInTheDocument()
    expect(screen.queryByText(/3\.6/)).not.toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: '今天收工' }))
    await waitFor(() => expect(api.stampSessionClose).toHaveBeenCalledWith('s1'))
    expect(await screen.findByText(/今天收工了/)).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: '今天收工' })).not.toBeInTheDocument()
    expect(region).toBeInTheDocument()
  })

  it('parent read-only surface shows the receipt line and never stamps', async () => {
    vi.mocked(api.getSessionClose).mockResolvedValue({
      ...OPEN,
      closed: true,
      closed_at: '2026-09-16T12:00:00+00:00',
      headline: '今天收工了 · 证据 1 条',
      parent_line: '孩子今天收工了。下一挑战：小数乘法。不含终答。',
    })
    render(<SessionCloseRitual sessionId="s1" readOnly />)
    expect(await screen.findByText(/孩子今天收工了/)).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: '今天收工' })).not.toBeInTheDocument()
    expect(api.stampSessionClose).not.toHaveBeenCalled()
    expect(screen.queryByText(/最终答案/)).not.toBeInTheDocument()
  })
})
