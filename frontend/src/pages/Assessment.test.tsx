import { act, fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { useState } from 'react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import Assessment from './Assessment'
import { api, fileToImageAnswer } from '../api/client'
import { useSessionSync } from '../hooks/useSessionSync'
import { ASSESSMENT_SECONDS } from '../constants/timing'
import { writeOpenItem, openItemStorageKey } from '../lib/timerOpenItem'

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
      appendTimerTelemetry: vi.fn(),
      appendTimerTelemetryKeepalive: vi.fn(),
    },
    fileToImageAnswer: vi.fn(),
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

const FULL_PAPER = {
  is_anchor: false,
  paper: {
    items: [
      {
        id: 'f0',
        stem: 'Q0',
        type: 'fill',
        difficulty: 'easy',
        knowledge_ids: ['frac_add_same'],
        answer_key: '1',
      },
    ],
    grade: 5,
    curriculum_label: 'pilot',
  },
  requested: 1,
  delivered: 1,
  shortfall: 0,
} as const

function mockDefaultSession(startedAt?: string) {
  vi.mocked(api.getSession).mockResolvedValue({
    session_id: 's1',
    phase: 'assessment',
    loop_count: 0,
    profile: { region: '北京', grade: 5, age: 11 },
    metadata: startedAt ? { assessment_started_at: startedAt } : {},
  } as never)
}

async function goToFullPhase() {
  vi.mocked(api.adaptiveStart).mockResolvedValue(ANCHOR_START)
  vi.mocked(api.adaptiveContinue).mockResolvedValue(FULL_PAPER)
  mockDefaultSession()
  vi.mocked(api.appendTimerTelemetry).mockResolvedValue(undefined as never)
  vi.mocked(api.appendTimerTelemetryKeepalive).mockReturnValue('keepalive')

  const onComplete = vi.fn().mockResolvedValue(undefined)
  render(
    <Assessment
      sessionId="s1"
      profile={{ region: '北京', grade: 5, age: 11 }}
      onComplete={onComplete}
    />,
  )
  await waitFor(() => expect(screen.getByText('锚点测评')).toBeInTheDocument())
  fireEvent.change(screen.getByPlaceholderText('输入你的答案'), { target: { value: '2' } })
  fireEvent.click(screen.getByRole('button', { name: '提交锚点，继续完整测评' }))
  await waitFor(() => expect(screen.getByText('完整测评')).toBeInTheDocument())
  return onComplete
}

describe('Assessment page', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    sessionStorage.clear()
    mockDefaultSession()
    vi.mocked(api.appendTimerTelemetry).mockResolvedValue(undefined as never)
    vi.mocked(api.appendTimerTelemetryKeepalive).mockReturnValue('keepalive')
    Object.defineProperty(document, 'visibilityState', {
      configurable: true,
      get: () => 'visible',
    })
  })

  afterEach(() => {
    vi.useRealTimers()
    Object.defineProperty(document, 'visibilityState', {
      configurable: true,
      get: () => 'visible',
    })
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

  it('does not auto-submit when UI deadline fires', async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true })
    const startedAt = new Date(Date.now() - (ASSESSMENT_SECONDS - 2) * 1000).toISOString()
    mockDefaultSession(startedAt)
    vi.mocked(api.adaptiveStart).mockResolvedValue(ANCHOR_START)

    const onComplete = vi.fn()
    render(
      <Assessment
        sessionId="s1"
        profile={{ region: '北京', grade: 5, age: 11 }}
        onComplete={onComplete}
      />,
    )

    await waitFor(() => expect(screen.getByText('锚点测评')).toBeInTheDocument())

    await act(async () => {
      await vi.advanceTimersByTimeAsync(5000)
    })

    expect(onComplete).not.toHaveBeenCalled()
    expect(screen.getByText('锚点测评')).toBeInTheDocument()
    expect(screen.getByText(/剩余/)).toBeInTheDocument()
  })

  it('busy+hidden overlap attributes only to pause_ms_busy', async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true })
    const onComplete = await goToFullPhase()

    let resolveUpload!: (value: {
      item_id: string
      image_base64: string
      mime_type: string
    }) => void
    vi.mocked(fileToImageAnswer).mockImplementation(
      () =>
        new Promise((resolve) => {
          resolveUpload = resolve
        }),
    )

    const file = new File(['x'], 'hand.png', { type: 'image/png' })
    await act(async () => {
      fireEvent.change(screen.getByLabelText(/手写作答照片/), {
        target: { files: [file] },
      })
    })

    Object.defineProperty(document, 'visibilityState', {
      configurable: true,
      get: () => 'hidden',
    })
    await act(async () => {
      document.dispatchEvent(new Event('visibilitychange'))
    })

    await act(async () => {
      await vi.advanceTimersByTimeAsync(5000)
    })

    await act(async () => {
      resolveUpload({ item_id: 'f0', image_base64: 'abc', mime_type: 'image/png' })
      await Promise.resolve()
    })

    Object.defineProperty(document, 'visibilityState', {
      configurable: true,
      get: () => 'visible',
    })
    await act(async () => {
      document.dispatchEvent(new Event('visibilitychange'))
    })

    fireEvent.change(screen.getByPlaceholderText('输入你的答案'), { target: { value: '1' } })
    await act(async () => {
      fireEvent.click(screen.getByRole('button', { name: '提交并诊断' }))
    })

    await waitFor(() => expect(onComplete).toHaveBeenCalled())
    const meta = onComplete.mock.calls[0][0].itemMeta.f0
    expect(meta.pause_ms_busy).toBeGreaterThanOrEqual(4500)
    expect(meta.pause_ms_visibility ?? 0).toBeLessThan(100)
    expect(Math.abs(meta.pause_ms! - (meta.pause_ms_busy! + meta.pause_ms_visibility!))).toBeLessThan(
      10,
    )
    if (meta.overtime_ms != null) {
      expect(meta.overtime_ms <= meta.thinking_ms + 10).toBe(true)
    }
  })

  it('re-seeds remaining from assessment_started_at', async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true })
    const elapsedMin = 30
    const startedAt = new Date(Date.now() - elapsedMin * 60 * 1000).toISOString()
    mockDefaultSession(startedAt)
    vi.mocked(api.adaptiveStart).mockResolvedValue(ANCHOR_START)

    render(
      <Assessment
        sessionId="s1"
        profile={{ region: '北京', grade: 5, age: 11 }}
        onComplete={vi.fn()}
      />,
    )

    await waitFor(() => expect(screen.getByText('锚点测评')).toBeInTheDocument())
    await waitFor(() => expect(api.getSession).toHaveBeenCalledWith('s1'))

    await act(async () => {
      await vi.advanceTimersByTimeAsync(0)
    })

    await waitFor(() => {
      const countdown = screen.getByText(/剩余/)
      expect(countdown.textContent).toMatch(/剩余 30:\d{2}/)
    })
  })

  it('marks thinking_ms_incomplete after remount with open marker', async () => {
    writeOpenItem('s1', 'f0', Date.now() - 1000)
    expect(sessionStorage.getItem(openItemStorageKey('s1'))).toBeTruthy()

    const onComplete = await goToFullPhase()

    fireEvent.change(screen.getByPlaceholderText('输入你的答案'), { target: { value: '1' } })
    fireEvent.click(screen.getByRole('button', { name: '提交并诊断' }))

    await waitFor(() => expect(onComplete).toHaveBeenCalled())
    const meta = onComplete.mock.calls[0][0].itemMeta.f0
    expect(meta.thinking_ms_incomplete).toBe(true)
  })

  it('submit includes timer_events drained from buffer', async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true })
    const startedAt = new Date(Date.now() - (ASSESSMENT_SECONDS - 1) * 1000).toISOString()
    mockDefaultSession(startedAt)
    vi.mocked(api.adaptiveStart).mockResolvedValue(ANCHOR_START)
    vi.mocked(api.adaptiveContinue).mockResolvedValue(FULL_PAPER)

    const onComplete = vi.fn().mockResolvedValue(undefined)
    render(
      <Assessment
        sessionId="s1"
        profile={{ region: '北京', grade: 5, age: 11 }}
        onComplete={onComplete}
      />,
    )

    await waitFor(() => expect(screen.getByText('锚点测评')).toBeInTheDocument())

    await act(async () => {
      await vi.advanceTimersByTimeAsync(3000)
    })

    fireEvent.change(screen.getByPlaceholderText('输入你的答案'), { target: { value: '2' } })
    fireEvent.click(screen.getByRole('button', { name: '提交锚点，继续完整测评' }))
    await waitFor(() => expect(screen.getByText('完整测评')).toBeInTheDocument())

    fireEvent.change(screen.getByPlaceholderText('输入你的答案'), { target: { value: '1' } })
    await act(async () => {
      fireEvent.click(screen.getByRole('button', { name: '提交并诊断' }))
    })

    await waitFor(() => expect(onComplete).toHaveBeenCalled())
    const payload = onComplete.mock.calls[0][0]
    expect(payload.timerEvents?.length).toBeGreaterThan(0)
    expect(payload.timerEvents).toEqual(
      expect.arrayContaining([expect.objectContaining({ type: 'item_time_flush' })]),
    )

    const telemetryCalls = vi.mocked(api.appendTimerTelemetry).mock.calls
    const allEvents = telemetryCalls.flatMap(
      (call) => (call[1] as { timer_events?: { type: string }[] }).timer_events || [],
    )
    expect(allEvents).toEqual(
      expect.arrayContaining([expect.objectContaining({ type: 'ui_deadline' })]),
    )
    expect(allEvents.length).toBeGreaterThan(0)
  })

  it('pagehide keepalive failed keeps events, does not latch, keeps open marker', async () => {
    vi.mocked(api.adaptiveStart).mockResolvedValue(ANCHOR_START)
    mockDefaultSession()
    vi.mocked(api.appendTimerTelemetryKeepalive)
      .mockReturnValueOnce('failed')
      .mockReturnValueOnce('keepalive')

    const { unmount } = render(
      <Assessment
        sessionId="s1"
        profile={{ region: '北京', grade: 5, age: 11 }}
        onComplete={vi.fn()}
      />,
    )

    await waitFor(() => expect(screen.getByText('锚点测评')).toBeInTheDocument())
    expect(sessionStorage.getItem(openItemStorageKey('s1'))).toBeTruthy()

    await act(async () => {
      window.dispatchEvent(new Event('pagehide'))
    })

    expect(api.appendTimerTelemetryKeepalive).toHaveBeenCalledTimes(1)
    expect(sessionStorage.getItem(openItemStorageKey('s1'))).toBeTruthy()

    await act(async () => {
      window.dispatchEvent(new Event('pagehide'))
    })

    expect(api.appendTimerTelemetryKeepalive).toHaveBeenCalledTimes(2)
    const secondPayload = vi.mocked(api.appendTimerTelemetryKeepalive).mock.calls[1][1] as {
      timer_events?: { type: string }[]
    }
    expect(secondPayload.timer_events?.length).toBeGreaterThan(0)
    expect(sessionStorage.getItem(openItemStorageKey('s1'))).toBeTruthy()

    unmount()
  })

  it('re-buffers events when appendTimerTelemetry throws on submit', async () => {
    const onComplete = await goToFullPhase()
    const baseline = vi.mocked(api.appendTimerTelemetry).mock.calls.length
    vi.mocked(api.appendTimerTelemetry)
      .mockRejectedValueOnce(new Error('network down'))
      .mockResolvedValueOnce(undefined as never)

    fireEvent.change(screen.getByPlaceholderText('输入你的答案'), { target: { value: '1' } })
    await act(async () => {
      fireEvent.click(screen.getByRole('button', { name: '提交并诊断' }))
    })

    await waitFor(() =>
      expect(api.appendTimerTelemetry).toHaveBeenCalledTimes(baseline + 1),
    )
    expect(onComplete).not.toHaveBeenCalled()
    expect(sessionStorage.getItem(openItemStorageKey('s1'))).toBeTruthy()

    await act(async () => {
      fireEvent.click(screen.getByRole('button', { name: '提交并诊断' }))
    })

    await waitFor(() => expect(onComplete).toHaveBeenCalled())
    expect(api.appendTimerTelemetry).toHaveBeenCalledTimes(baseline + 2)
    const retryEvents = (
      vi.mocked(api.appendTimerTelemetry).mock.calls[baseline + 1][1] as {
        timer_events?: { type: string }[]
      }
    ).timer_events
    expect(retryEvents?.length).toBeGreaterThan(0)
  })

  it('selectItem flushes leaving item into buffer', async () => {
    const twoItemFull = {
      is_anchor: false,
      paper: {
        items: [
          {
            id: 'f0',
            stem: 'Q0',
            type: 'fill',
            difficulty: 'easy',
            knowledge_ids: ['frac_add_same'],
            answer_key: '1',
          },
          {
            id: 'f1',
            stem: 'Q1',
            type: 'fill',
            difficulty: 'easy',
            knowledge_ids: ['frac_add_same'],
            answer_key: '1',
          },
        ],
        grade: 5,
        curriculum_label: 'pilot',
      },
      requested: 2,
      delivered: 2,
      shortfall: 0,
    } as const

    vi.mocked(api.adaptiveStart).mockResolvedValue(ANCHOR_START)
    vi.mocked(api.adaptiveContinue).mockResolvedValue(twoItemFull)
    mockDefaultSession()

    const onComplete = vi.fn().mockResolvedValue(undefined)
    render(
      <Assessment
        sessionId="s1"
        profile={{ region: '北京', grade: 5, age: 11 }}
        onComplete={onComplete}
      />,
    )

    await waitFor(() => expect(screen.getByText('锚点测评')).toBeInTheDocument())
    fireEvent.change(screen.getByPlaceholderText('输入你的答案'), { target: { value: '2' } })
    fireEvent.click(screen.getByRole('button', { name: '提交锚点，继续完整测评' }))
    await waitFor(() => expect(screen.getByText('完整测评')).toBeInTheDocument())

    fireEvent.click(screen.getByRole('button', { name: /第 2 题/ }))
    const activeCard = document.querySelector('.item-card.active')
    expect(activeCard).toBeTruthy()
    fireEvent.change(within(activeCard as HTMLElement).getByPlaceholderText('输入你的答案'), {
      target: { value: '1' },
    })
    await act(async () => {
      fireEvent.click(screen.getByRole('button', { name: '提交并诊断' }))
    })

    await waitFor(() => expect(onComplete).toHaveBeenCalled())
    const events = onComplete.mock.calls[0][0].timerEvents as { type: string; item_id?: string }[]
    expect(events).toEqual(
      expect.arrayContaining([
        expect.objectContaining({ type: 'item_time_flush', item_id: 'f0' }),
      ]),
    )
  })
})
