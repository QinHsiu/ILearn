import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import ConceptMicroCard from './ConceptMicroCard'
import { api } from '../api/client'

vi.mock('../api/client', async () => {
  const actual = await vi.importActual<typeof import('../api/client')>('../api/client')
  return {
    ...actual,
    api: {
      ...actual.api,
      getConceptLesson: vi.fn(),
    },
  }
})

describe('ConceptMicroCard', () => {
  it('pages the storyboard in-card without opening a new tab', async () => {
    vi.mocked(api.getConceptLesson).mockResolvedValue({
      session_id: 's1',
      item_id: 'q1',
      lesson: {
        knowledge_id: 'mult_3digit',
        title: '三位数乘法竖式',
        duration_sec: 60,
        script_steps: ['数位对齐', '分步相乘', '相加核对'],
        poster_url: '/pilot-assets/concept/mult_3digit.svg',
        storyboard_url: '/pilot-assets/concept/mult_3digit.md',
        media_status: 'poster',
        no_final_answer: true,
      },
    })

    render(<ConceptMicroCard sessionId="s1" itemId="q1" />)

    await waitFor(() => {
      expect(screen.getByRole('region', { name: /概念分镜/ })).toBeInTheDocument()
    })
    expect(screen.queryByRole('link', { name: /打开分镜/ })).not.toBeInTheDocument()
    expect(screen.queryByRole('link', { name: /打开概念分镜/ })).not.toBeInTheDocument()
    expect(screen.getByText('数位对齐')).toBeInTheDocument()
    expect(screen.queryByText('分步相乘')).not.toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: '下一镜' }))
    expect(screen.getByText('分步相乘')).toBeInTheDocument()
  })
})
