import { render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import App from './App'
import { dashboardApi } from './api/client'

vi.mock('./api/client', async () => {
  const actual = await vi.importActual<typeof import('./api/client')>('./api/client')
  return {
    ...actual,
    dashboardApi: {
      parentChildren: vi.fn(),
      parentChild: vi.fn(),
      teacherClasses: vi.fn(),
      teacherStudents: vi.fn(),
      teacherStudent: vi.fn(),
      bindParent: vi.fn(),
      bindTeacher: vi.fn(),
    },
  }
})

const parentSummary = {
  session_id: 's1',
  nickname: '小明',
  grade: 5,
  region: '北京',
  overall_mastery: 0.8,
  weak_skills: ['分数'],
  skill_mastery: { 代数: 0.8 },
  phase: 'diagnosed',
}

const detail = {
  session_id: 's1',
  phase: 'diagnosed',
  loop_count: 0,
  profile: { region: '北京', grade: 5, age: 11, nickname: '小明' },
  diagnosis: {
    knowledge_mastery: [
      { knowledge_id: 'k1', knowledge_name: '代数', score_rate: 0.8, level: 'mastered' },
    ],
  },
  plan: { status: 'ready', markdown: '学习计划' },
}

function setSearch(search: string) {
  window.history.pushState({}, '', search)
}

describe('dashboard role views', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    setSearch('/')
  })

  it('shows both role entry labels while preserving student mode by default', () => {
    render(<App />)
    expect(screen.getByText('家长端')).toBeInTheDocument()
    expect(screen.getByText('老师端')).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: '建档' })).toBeInTheDocument()
  })

  it('renders parent loading, empty, list, and detail states', async () => {
    setSearch('/?role=parent&user=p1')
    vi.mocked(dashboardApi.parentChildren).mockResolvedValue([parentSummary])
    vi.mocked(dashboardApi.parentChild).mockResolvedValue(detail)

    render(<App />)
    expect(screen.getByText('加载中…')).toBeInTheDocument()
    expect(await screen.findByText('小明')).toBeInTheDocument()

    await waitFor(() => expect(dashboardApi.parentChildren).toHaveBeenCalledWith('p1'))
    screen.getByRole('button', { name: /小明/ }).click()
    expect(await screen.findByText('学习计划')).toBeInTheDocument()

    vi.mocked(dashboardApi.parentChildren).mockResolvedValueOnce([])
    setSearch('/?role=parent&user=p1')
  })

  it('renders teacher class, student, and detail states', async () => {
    setSearch('/?role=teacher&user=t1')
    vi.mocked(dashboardApi.teacherClasses).mockResolvedValue([
      { class_id: 'c1', students: [parentSummary] },
    ])
    vi.mocked(dashboardApi.teacherStudents).mockResolvedValue([parentSummary])
    vi.mocked(dashboardApi.teacherStudent).mockResolvedValue(detail)

    render(<App />)
    expect(screen.getByText('加载中…')).toBeInTheDocument()
    expect(await screen.findByText('班级 c1')).toBeInTheDocument()
    screen.getByRole('button', { name: '班级 c1' }).click()
    expect(await screen.findByRole('button', { name: /小明/ })).toBeInTheDocument()
    screen.getByRole('button', { name: /小明/ }).click()
    expect(await screen.findByText('知识点掌握')).toBeInTheDocument()
  })
})
