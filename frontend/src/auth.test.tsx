import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import App from './App'
import { authApi } from './api/client'

vi.mock('./api/client', async () => {
  const actual = await vi.importActual<typeof import('./api/client')>('./api/client')
  return {
    ...actual,
    authApi: {
      login: vi.fn(),
    },
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

function setSearch(search: string) {
  window.history.pushState({}, '', search)
}

describe('landing and login routes', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    setSearch('/')
  })

  it('shows role selection at the root path', () => {
    render(<App />)

    expect(screen.getByRole('heading', { name: '把学习看清楚，再决定下一步' })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /家长端.*孩子成长/ })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /老师端.*班级运营/ })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /学生端.*下一步学习/ })).toHaveAttribute(
      'href',
      '?student=1',
    )
  })

  it('opens the existing student app from the student entry', () => {
    setSearch('/?student=1')
    render(<App />)

    expect(screen.getByRole('heading', { name: '建档' })).toBeInTheDocument()
  })

  it('renders parent and teacher role cards on the login entry', () => {
    setSearch('/?login=1')
    render(<App />)

    expect(screen.getByRole('heading', { name: '把学习看清楚，再决定下一步' })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /家长端.*孩子成长/ })).toHaveAttribute(
      'href',
      '?login=1&role=parent',
    )
    expect(screen.getByRole('link', { name: /老师端.*班级运营/ })).toHaveAttribute(
      'href',
      '?login=1&role=teacher',
    )
  })

  it('shows the API error when login fails', async () => {
    setSearch('/?login=1&role=parent')
    vi.mocked(authApi.login).mockRejectedValue(new Error('invalid credentials'))
    render(<App />)

    fireEvent.change(screen.getByLabelText('用户名'), { target: { value: 'someone' } })
    fireEvent.change(screen.getByLabelText('密码'), { target: { value: 'secret' } })
    fireEvent.submit(screen.getByRole('button', { name: '登录' }).closest('form')!)

    expect(await screen.findByText('invalid credentials')).toBeInTheDocument()
  })

  it('renders the existing dashboard immediately after login', async () => {
    setSearch('/?login=1&role=teacher')
    vi.mocked(authApi.login).mockResolvedValue({ role: 'teacher', user_id: 'teacher-42' })
    const { dashboardApi } = await import('./api/client')
    vi.mocked(dashboardApi.teacherClasses).mockResolvedValue([])
    render(<App />)

    fireEvent.change(screen.getByLabelText('用户名'), { target: { value: 'someone' } })
    fireEvent.change(screen.getByLabelText('密码'), { target: { value: 'secret' } })
    fireEvent.submit(screen.getByRole('button', { name: '登录' }).closest('form')!)

    await waitFor(() =>
      expect(window.location.search).toBe('?role=teacher&user=teacher-42'),
    )
    expect(await screen.findByRole('heading', { name: '班级扫描' })).toBeInTheDocument()
    expect(dashboardApi.teacherClasses).toHaveBeenCalledWith('teacher-42')
  })
})
