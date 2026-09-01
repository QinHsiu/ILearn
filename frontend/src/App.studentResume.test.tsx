import { render, screen } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import App from './App'
import { api } from './api/client'
import type { ReportResponse } from './api/client'

vi.mock('./api/client', async () => {
  const actual = await vi.importActual<typeof import('./api/client')>('./api/client')
  return {
    ...actual,
    api: {
      ...actual.api,
      getReport: vi.fn(),
      createSession: vi.fn(),
    },
  }
})

const PLAN_REPORT: ReportResponse = {
  markdown: '学习计划正文',
  session: {
    session_id: 's1',
    phase: 'plan',
    loop_count: 0,
    profile: { region: 'beijing', grade: 5, age: 11, nickname: '小明' },
    plan: { status: 'ready', markdown: '学习计划正文' },
    grades: [],
  },
}

function setSearch(search: string) {
  window.history.pushState({}, '', search)
}

describe('StudentApp deep-link resume', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    setSearch('/')
  })

  it('does not paint 建档 while session_id resume is in flight, then shows plan', async () => {
    setSearch('/?student=1&session_id=s1')
    let resolveReport: (value: ReportResponse) => void = () => undefined
    vi.mocked(api.getReport).mockImplementation(
      () =>
        new Promise((resolve) => {
          resolveReport = resolve
        }),
    )

    render(<App />)

    expect(screen.queryByRole('heading', { name: '建档' })).not.toBeInTheDocument()
    expect(screen.getByText('正在恢复会话…')).toBeInTheDocument()
    expect(api.createSession).not.toHaveBeenCalled()

    resolveReport(PLAN_REPORT)

    expect(await screen.findByRole('heading', { name: '学习计划' })).toBeInTheDocument()
    expect(screen.queryByRole('heading', { name: '建档' })).not.toBeInTheDocument()
    expect(screen.queryByText('正在恢复会话…')).not.toBeInTheDocument()
    expect(api.getReport).toHaveBeenCalledWith('s1')
    expect(api.createSession).not.toHaveBeenCalled()
  })

  it('shows the existing error pattern when deep-link resume fails', async () => {
    setSearch('/?student=1&session_id=s1')
    vi.mocked(api.getReport).mockRejectedValue(new Error('session missing'))

    render(<App />)

    expect(await screen.findByText('session missing')).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: '建档' })).toBeInTheDocument()
    expect(api.createSession).not.toHaveBeenCalled()
  })

  it('renders Swiss student-shell chrome and stepper', () => {
    setSearch('/?student=1')
    render(<App />)

    expect(screen.getByRole('heading', { name: '学生学习 / NEXT STEP' })).toBeInTheDocument()
    expect(document.querySelector('.student-shell')).toBeTruthy()
    expect(screen.getByRole('navigation', { name: '向导步骤' })).toHaveClass('student-steps')
  })
})
