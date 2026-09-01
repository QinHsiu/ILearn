import { act, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { useState } from 'react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import Assessment from './Assessment'
import { api } from '../api/client'
import { useSessionSync } from '../hooks/useSessionSync'

vi.mock('../api/client', async () => {
  const actual = await vi.importActual<typeof import('../api/client')>('../api/client')
  return {
    ...actual,
    api: {
      ...actual.api,
      adaptiveStart: vi.fn(),
      adaptiveContinue: vi.fn(),
      getSession: vi.fn(),
      heartbeat: vi.fn(),
    },
  }
})

const ANCHOR_START = {
  is_anchor: true,
  paper: {
    items: [
      {
        id: 'a1',
        stem: '1+1=?',
        type: 'fill',
        difficulty: 'easy',
        knowledge_ids: ['frac_add_same'],
        answer_key: '2',
      },
    ],
    grade: 5,
    curriculum_label: 'pilot',
  },
  requested: 1,
  delivered: 1,
  shortfall: 0,
  layer2_used: false,
  layer2_source: 'none',
} as const

describe('Assessment page', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('loads anchor phase then continues to full paper', async () => {
    vi.mocked(api.adaptiveStart).mockResolvedValue(ANCHOR_START)
    vi.mocked(api.adaptiveContinue).mockResolvedValue({
      is_anchor: false,
      paper: {
        items: Array.from({ length: 20 }, (_, i) => ({
          id: `f${i}`,
          stem: `Q${i}`,
          type: 'fill',
          difficulty: 'easy',
          knowledge_ids: ['frac_add_same'],
          answer_key: '1',
        })),
        grade: 5,
        curriculum_label: 'pilot',
      },
      requested: 20,
      delivered: 20,
      shortfall: 0,
    })

    const onComplete = vi.fn()
    render(
      <Assessment
        sessionId="s1"
        profile={{ region: '北京', grade: 5, age: 11 }}
        onComplete={onComplete}
      />,
    )

    await waitFor(() => expect(screen.getByText('锚点测评')).toBeInTheDocument())
    expect(api.adaptiveStart).toHaveBeenCalledWith('s1')
    expect(screen.getByText('锚点')).toBeInTheDocument()
    expect(screen.getByText(/01\s*\/\s*01/)).toBeInTheDocument()
    expect(screen.getByText('1+1=?')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /第 1 题/ })).toBeInTheDocument()

    screen.getByRole('button', { name: '提交锚点，继续完整测评' }).click()
    await waitFor(() => expect(screen.getByText('完整测评')).toBeInTheDocument())
    expect(screen.getByText('完整')).toBeInTheDocument()
    expect(screen.getByText(/01\s*\/\s*20/)).toBeInTheDocument()
    expect(api.adaptiveContinue).toHaveBeenCalled()
  })

  it('does not restart adaptiveStart when onError identity changes after answering', async () => {
    vi.mocked(api.adaptiveStart).mockResolvedValue(ANCHOR_START)

    const profile = { region: '北京', grade: 5, age: 11 }
    const { rerender } = render(
      <Assessment
        sessionId="s1"
        profile={profile}
        onComplete={vi.fn()}
        onError={() => {}}
      />,
    )

    await waitFor(() => expect(screen.getByText('锚点测评')).toBeInTheDocument())
    expect(api.adaptiveStart).toHaveBeenCalledTimes(1)

    fireEvent.change(screen.getByPlaceholderText('输入你的答案'), { target: { value: '2' } })
    expect(screen.getByPlaceholderText('输入你的答案')).toHaveValue('2')

    rerender(
      <Assessment
        sessionId="s1"
        profile={profile}
        onComplete={vi.fn()}
        onError={() => {}}
      />,
    )

    await waitFor(() => {
      expect(screen.getByPlaceholderText('输入你的答案')).toHaveValue('2')
    })
    expect(api.adaptiveStart).toHaveBeenCalledTimes(1)
    expect(screen.getByText('锚点测评')).toBeInTheDocument()
  })

  it('does not restart adaptiveStart after visibility sync re-renders the parent', async () => {
    vi.mocked(api.adaptiveStart).mockResolvedValue(ANCHOR_START)
    vi.mocked(api.getSession).mockResolvedValue({
      session_id: 's1',
      phase: 'assessment',
      loop_count: 0,
      profile: { region: '北京', grade: 5, age: 11 },
    } as never)
    vi.mocked(api.heartbeat).mockResolvedValue({
      ok: true,
      phase: 'assessment',
      server_time: '2026-01-01T00:00:00Z',
    })

    function Harness() {
      const [, setError] = useState<string | null>(null)
      useSessionSync({
        sessionId: 's1',
        onSync: () => {},
        hasUnsavedChanges: () => false,
      })
      return (
        <Assessment
          sessionId="s1"
          profile={{ region: '北京', grade: 5, age: 11 }}
          onComplete={() => {}}
          onError={(message) => setError(message)}
        />
      )
    }

    render(<Harness />)
    await waitFor(() => expect(screen.getByText('锚点测评')).toBeInTheDocument())
    fireEvent.change(screen.getByPlaceholderText('输入你的答案'), { target: { value: '2' } })
    expect(api.adaptiveStart).toHaveBeenCalledTimes(1)

    const previousVisibility = document.visibilityState
    Object.defineProperty(document, 'visibilityState', {
      configurable: true,
      get: () => 'visible',
    })
    await act(async () => {
      document.dispatchEvent(new Event('visibilitychange'))
    })
    await waitFor(() => expect(api.getSession).toHaveBeenCalledWith('s1'))
    await waitFor(() => {
      expect(screen.getByPlaceholderText('输入你的答案')).toHaveValue('2')
    })
    expect(api.adaptiveStart).toHaveBeenCalledTimes(1)

    Object.defineProperty(document, 'visibilityState', {
      configurable: true,
      get: () => previousVisibility,
    })
  })

  it('shows countdown, handwriting upload, and Socratic entry on anchor paper', async () => {
    vi.mocked(api.adaptiveStart).mockResolvedValue(ANCHOR_START)
    render(
      <Assessment
        sessionId="s1"
        profile={{ region: '北京', grade: 5, age: 11 }}
        onComplete={vi.fn()}
      />,
    )

    await waitFor(() => expect(screen.getByText('锚点测评')).toBeInTheDocument())
    expect(screen.getByText(/剩余/)).toBeInTheDocument()
    expect(screen.getByLabelText(/手写作答照片/)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: '求助苏格拉底' })).toBeInTheDocument()
  })
})
