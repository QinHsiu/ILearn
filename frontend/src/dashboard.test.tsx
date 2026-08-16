import { fireEvent, render, screen, waitFor } from '@testing-library/react'
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

  it('shows role entry labels on the default landing page', () => {
    render(<App />)
    expect(screen.getByRole('heading', { name: '把学习看清楚，再决定下一步' })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /家长端.*孩子成长/ })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /老师端.*班级运营/ })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /学生端.*下一步学习/ })).toHaveAttribute(
      'href',
      '?student=1',
    )
  })

  it('renders parent loading, empty, list, and detail states', async () => {
    setSearch('/?role=parent&user=p1')
    vi.mocked(dashboardApi.parentChildren).mockResolvedValue([parentSummary])
    vi.mocked(dashboardApi.parentChild).mockResolvedValue(detail)

    render(<App />)
    expect(screen.getByRole('heading', { name: '孩子最近学得怎么样，下一步怎么支持？' })).toBeInTheDocument()
    expect(screen.getByText('家长端 / CHILD GROWTH')).toHaveClass('dashboard-role-badge')
    expect(screen.getByRole('main')).toHaveClass('dashboard-content', 'parent-content')
    expect(screen.getByRole('link', { name: '返回角色选择' })).toHaveAttribute('href', '/')
    expect(screen.getByText('加载中…')).toBeInTheDocument()
    expect(await screen.findByText('小明')).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: '事实摘要' })).toBeInTheDocument()
    expect(screen.getByText('当前掌握度')).toBeInTheDocument()
    expect(screen.getByText('80%')).toBeInTheDocument()
    expect(screen.getByText('薄弱知识点')).toBeInTheDocument()
    expect(screen.getByText('分数')).toBeInTheDocument()
    expect(screen.getByText('学习阶段')).toBeInTheDocument()
    expect(screen.getByText('已完成诊断')).toBeInTheDocument()

    await waitFor(() => expect(dashboardApi.parentChildren).toHaveBeenCalledWith('p1'))
    screen.getByRole('button', { name: /小明/ }).click()
    expect(window.location.search).toContain('student_id=s1')
    expect(await screen.findByText('支持建议')).toBeInTheDocument()
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
    expect(screen.getByRole('heading', { name: '班级整体哪里需要干预，应该先看谁？' })).toBeInTheDocument()
    expect(screen.getByRole('main')).toHaveClass('dashboard-content', 'teacher-content')
    expect(await screen.findByText('班级 c1')).toBeInTheDocument()
    expect(screen.getByText('1 名学生')).toBeInTheDocument()
    expect(screen.getByText('状态：已绑定')).toBeInTheDocument()
    screen.getByText('班级 c1').closest('button')!.click()
    expect(window.location.search).toContain('class_id=c1')
    expect(await screen.findByRole('button', { name: /小明/ })).toBeInTheDocument()
    screen.getByRole('button', { name: /小明/ }).click()
    expect(window.location.search).toContain('student_id=s1')
    expect(await screen.findByText('知识点掌握')).toBeInTheDocument()
  })

  it('keeps an empty class status factual', async () => {
    setSearch('/?role=teacher&user=t1')
    vi.mocked(dashboardApi.teacherClasses).mockResolvedValue([{ class_id: 'c1', students: [] }])

    render(<App />)

    expect(await screen.findByText('班级 c1')).toBeInTheDocument()
    expect(screen.getByText('0 名学生')).toBeInTheDocument()
    expect(screen.getByText('状态：暂无学生')).toBeInTheDocument()
  })

  it('shows parent bind failures instead of leaving rejected promises unhandled', async () => {
    setSearch('/?role=parent&user=p1')
    vi.mocked(dashboardApi.parentChildren).mockResolvedValue([])
    vi.mocked(dashboardApi.bindParent).mockRejectedValue(new Error('绑定失败'))

    render(<App />)
    await screen.findByText('暂无学生数据')
    fireEvent.change(screen.getByLabelText('绑定学习会话'), { target: { value: 's1' } })
    expect(screen.getByText(/还没有绑定学生/)).toHaveClass('dashboard-empty-state')
    fireEvent.submit(screen.getByRole('button', { name: '绑定学生并刷新' }).closest('form')!)
    expect(await screen.findByText('绑定失败')).toBeInTheDocument()
  })

  it('shows teacher bind failures instead of leaving rejected promises unhandled', async () => {
    setSearch('/?role=teacher&user=t1&class_id=c1')
    vi.mocked(dashboardApi.teacherClasses).mockResolvedValue([{ class_id: 'c1', students: [] }])
    vi.mocked(dashboardApi.bindTeacher).mockRejectedValue(new Error('教师绑定失败'))

    render(<App />)
    await screen.findByText('班级 c1')
    fireEvent.change(screen.getByLabelText('绑定学生会话'), { target: { value: 's1' } })
    expect(screen.getByRole('heading', { name: '班级扫描' }).closest('section')).toHaveClass('dashboard-panel')
    expect(screen.getByText('班级 c1').closest('button')).toHaveClass('dashboard-entry-card')
    fireEvent.submit(screen.getByRole('button', { name: '绑定学生并刷新' }).closest('form')!)
    expect(await screen.findByText('教师绑定失败')).toBeInTheDocument()
  })
})
