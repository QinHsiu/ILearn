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
    },
  }
})

const DEMO = {
  session_id: 'sess-demo',
  unit_name: '小数乘法',
  links: {
    student: '?student=1&session_id=sess-demo',
    teacher:
      '?login=1&role=teacher&user=demo_teacher&class_id=demo_class_5a&student_id=sess-demo',
    parent: '?login=1&role=parent&user=demo_parent&student_id=sess-demo',
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

  it('shows the 小数乘法 demo button', () => {
    render(<LandingPage />)

    expect(screen.getByRole('button', { name: '体验小数乘法' })).toBeInTheDocument()
  })

  it('creates math_5_1 demo and assigns location to the teacher link', async () => {
    render(<LandingPage />)

    fireEvent.click(screen.getByRole('button', { name: '体验小数乘法' }))

    await waitFor(() => {
      expect(window.location.href).toBe(DEMO.links.teacher)
    })
    expect(api.createDemoSession).toHaveBeenCalledWith('math_5_1')
  })
})
