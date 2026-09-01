import { render, screen } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import StudentSummaryPanel from './StudentSummaryPanel'
import { api } from '../api/client'
import type { StudentSummary } from '../api/client'

vi.mock('../api/client', async () => {
  const actual = await vi.importActual<typeof import('../api/client')>('../api/client')
  return {
    ...actual,
    api: {
      ...actual.api,
      getStudentSummary: vi.fn(),
    },
  }
})

const SUMMARY: StudentSummary = {
  current_task: '巩固：小数乘小数',
  completed_tasks: 2,
  total_tasks: 5,
  stars_earned: 5,
  next_challenge: '挑战：运算律推广到小数',
  narrative: '今天又进步啦，继续加油！',
}

describe('StudentSummaryPanel', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(api.getStudentSummary).mockResolvedValue(SUMMARY)
  })

  it('renders task progress and stars', async () => {
    render(<StudentSummaryPanel sessionId="s1" />)

    expect(await screen.findByText(/巩固：小数乘小数/)).toBeInTheDocument()
    expect(screen.getByText(/2\s*\/\s*5|2\/5/)).toBeInTheDocument()
    expect(screen.getByLabelText('获得星星')).toHaveTextContent('5')
    expect(screen.getByLabelText('学生任务摘要')).toBeInTheDocument()
    expect(api.getStudentSummary).toHaveBeenCalledWith('s1')
  })

  it('renders next challenge and narrative', async () => {
    render(<StudentSummaryPanel sessionId="s1" />)

    expect(await screen.findByText('挑战：运算律推广到小数')).toBeInTheDocument()
    expect(screen.getByText('今天又进步啦，继续加油！')).toBeInTheDocument()
  })

  it('shows loading until the summary arrives', async () => {
    let resolveSummary: (value: StudentSummary) => void = () => undefined
    vi.mocked(api.getStudentSummary).mockImplementation(
      () =>
        new Promise((resolve) => {
          resolveSummary = resolve
        }),
    )

    render(<StudentSummaryPanel sessionId="s1" />)

    expect(screen.getByText('加载中…')).toBeInTheDocument()
    resolveSummary(SUMMARY)
    expect(await screen.findByText(/巩固：小数乘小数/)).toBeInTheDocument()
    expect(screen.queryByText('加载中…')).not.toBeInTheDocument()
  })

  it('shows error when fetch fails', async () => {
    vi.mocked(api.getStudentSummary).mockRejectedValue(new Error('网络错误'))

    render(<StudentSummaryPanel sessionId="s1" />)

    expect(await screen.findByRole('alert')).toHaveTextContent('网络错误')
  })
})
