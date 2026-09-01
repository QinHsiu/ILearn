import { render, screen } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import TutorPanel from './TutorPanel'
import { api } from '../api/client'

vi.mock('../api/client', async () => {
  const actual = await vi.importActual<typeof import('../api/client')>('../api/client')
  return {
    ...actual,
    api: {
      ...actual.api,
      tutorStart: vi.fn(),
      tutorHint: vi.fn(),
    },
  }
})

describe('TutorPanel', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('shows Socratic tutor heading and start action', () => {
    render(<TutorPanel sessionId="s1" itemId="q1" />)

    expect(screen.getByRole('heading', { name: '苏格拉底助教' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: '开始辅导' })).toBeInTheDocument()
  })
})
