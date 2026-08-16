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

  it('keeps the existing student app for an empty query', () => {
    render(<App />)

    expect(screen.getByRole('heading', { name: '建档' })).toBeInTheDocument()
  })

  it('renders parent and teacher role cards on the login entry', () => {
    setSearch('/?login=1')
    render(<App />)

    expect(screen.getByRole('heading', { name: '欢迎来到 ILearn' })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /家长登录/ })).toHaveAttribute(
      'href',
      '?login=1&role=parent',
    )
    expect(screen.getByRole('link', { name: /老师登录/ })).toHaveAttribute(
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

  it('redirects to the existing dashboard query after login', async () => {
    setSearch('/?login=1&role=teacher')
    vi.mocked(authApi.login).mockResolvedValue({ role: 'teacher', user_id: 'teacher-42' })
    render(<App />)

    fireEvent.change(screen.getByLabelText('用户名'), { target: { value: 'someone' } })
    fireEvent.change(screen.getByLabelText('密码'), { target: { value: 'secret' } })
    fireEvent.submit(screen.getByRole('button', { name: '登录' }).closest('form')!)

    await waitFor(() =>
      expect(window.location.search).toBe('?role=teacher&user=teacher-42'),
    )
    await waitFor(() => expect(screen.getByRole('button', { name: '登录' })).toBeEnabled())
  })
})
