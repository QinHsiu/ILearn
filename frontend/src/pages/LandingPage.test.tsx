import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import LandingPage from './LandingPage'
import { api } from '../api/client'

vi.mock('../api/client', async () => {
  const actual = await vi.importActual<typeof import('../api/client')>('../api/client')
  return {
    ...actual,
    api: {
      ...actual.api,
      createDemoSession: vi.fn(),
      submitWaitlist: vi.fn(),
      getQualityGates: vi.fn().mockResolvedValue({
        summary: { total: 5, enforced: 5 },
        gates: [],
        how_to_verify: [],
        product: 'ILearn',
        eval_suite: 'tests/eval_winbars',
      }),
    },
  }
})

const DEMO = {
  session_id: 'sess-demo',
  unit_name: '小数乘法',
  links: {
    student: '?student=1&session_id=sess-demo',
    teacher:
      '?role=teacher&user=demo_teacher&class_id=demo_class_5a&student_id=sess-demo',
    parent: '?role=parent&user=demo_parent&student_id=sess-demo',
  },
}

describe('LandingPage demo CTA', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(api.createDemoSession).mockResolvedValue(DEMO)
    vi.stubGlobal('location', { href: 'http://localhost/' })
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('shows the 小数乘法 demo button', async () => {
    render(<LandingPage />)

    expect(screen.getByRole('heading', { name: /敢给孩子用|证据化/ })).toBeInTheDocument()
    expect(screen.getByLabelText('试点范围')).toHaveTextContent(/北京·人教/)
    expect(screen.getByRole('button', { name: '体验小数乘法' })).toBeInTheDocument()
    expect(screen.getByLabelText('产品承诺')).toHaveTextContent(/掌握度进步/)
    expect(await screen.findByLabelText('质量门摘要')).toHaveTextContent(/质量门已强制/)
    expect(screen.getAllByText(/今晚就能陪|敢问敢练|布置就能办完/).length).toBeGreaterThanOrEqual(3)
  })

  it('submits waitlist email', async () => {
    vi.mocked(api.submitWaitlist).mockResolvedValue({ ok: true })
    render(<LandingPage />)
    fireEvent.change(screen.getByLabelText(/邮箱/), {
      target: { value: 'parent@example.com' },
    })
    fireEvent.click(screen.getByRole('button', { name: '加入候补' }))
    await waitFor(() => {
      expect(api.submitWaitlist).toHaveBeenCalledWith({
        email: 'parent@example.com',
        role: 'parent',
      })
    })
    expect(await screen.findByRole('status')).toHaveTextContent(/早鸟候补/)
  })

  it('creates math_5_1 demo and assigns location to the teacher link', async () => {
    render(<LandingPage />)

    fireEvent.click(screen.getByRole('button', { name: '体验小数乘法' }))

    await waitFor(() => {
      expect(window.location.href).toBe(DEMO.links.teacher)
    })
    expect(api.createDemoSession).toHaveBeenCalledWith('math_5_1')
  })

  it('uses selected demo role link (parent)', async () => {
    render(<LandingPage />)
    fireEvent.click(screen.getByRole('radio', { name: /家长/ }))
    fireEvent.click(screen.getByRole('button', { name: '体验小数乘法' }))
    await waitFor(() => {
      expect(window.location.href).toBe(DEMO.links.parent)
    })
  })

  it('uses selected demo role link (student)', async () => {
    render(<LandingPage />)
    fireEvent.click(screen.getByRole('radio', { name: /学生/ }))
    fireEvent.click(screen.getByRole('button', { name: '体验小数乘法' }))
    await waitFor(() => {
      expect(window.location.href).toBe(DEMO.links.student)
    })
  })

  it('role card parent one-click starts parent demo', async () => {
    render(<LandingPage />)
    fireEvent.click(screen.getByRole('button', { name: /家长 · 今晚就能陪/ }))
    await waitFor(() => {
      expect(api.createDemoSession).toHaveBeenCalledWith('math_5_1')
      expect(window.location.href).toBe(DEMO.links.parent)
    })
  })
})
