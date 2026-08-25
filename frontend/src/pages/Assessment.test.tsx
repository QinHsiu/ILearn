import { render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import Assessment from './Assessment'
import { api } from '../api/client'

vi.mock('../api/client', async () => {
  const actual = await vi.importActual<typeof import('../api/client')>('../api/client')
  return {
    ...actual,
    api: {
      ...actual.api,
      adaptiveStart: vi.fn(),
      adaptiveContinue: vi.fn(),
    },
  }
})

describe('Assessment page', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('loads anchor phase then continues to full paper', async () => {
    vi.mocked(api.adaptiveStart).mockResolvedValue({
      is_anchor: true,
      paper: {
        items: [
          {
            id: 'a1',
            stem: '1+1=?',
            type: 'fill',
            difficulty: 'easy',
            knowledge_ids: ['frac_add_same'],
            answer_key: '2',
          },
        ],
        grade: 5,
        curriculum_label: 'pilot',
      },
      requested: 1,
      delivered: 1,
      shortfall: 0,
      layer2_used: false,
      layer2_source: 'none',
    })
    vi.mocked(api.adaptiveContinue).mockResolvedValue({
      is_anchor: false,
      paper: {
        items: Array.from({ length: 20 }, (_, i) => ({
          id: `f${i}`,
          stem: `Q${i}`,
          type: 'fill',
          difficulty: 'easy',
          knowledge_ids: ['frac_add_same'],
          answer_key: '1',
        })),
        grade: 5,
        curriculum_label: 'pilot',
      },
      requested: 20,
      delivered: 20,
      shortfall: 0,
    })

    const onComplete = vi.fn()
    render(
      <Assessment
        sessionId="s1"
        profile={{ region: '北京', grade: 5, age: 11 }}
        onComplete={onComplete}
      />,
    )

    await waitFor(() => expect(screen.getByText('锚点测评')).toBeInTheDocument())
    expect(api.adaptiveStart).toHaveBeenCalledWith('s1')

    screen.getByRole('button', { name: '提交锚点，继续完整测评' }).click()
    await waitFor(() => expect(screen.getByText('完整测评')).toBeInTheDocument())
    expect(api.adaptiveContinue).toHaveBeenCalled()
  })
})
