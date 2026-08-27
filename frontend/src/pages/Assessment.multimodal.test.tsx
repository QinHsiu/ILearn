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

describe('Assessment multimodal rendering', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders stem images and chapter banner when image_paths are present', async () => {
    const imagePath = '/pilot-assets/mv_math/demo/0.png'
    vi.mocked(api.adaptiveStart).mockResolvedValue({
      is_anchor: true,
      paper: {
        items: [
          {
            id: 'mm1',
            stem: '观察图中长方形，求面积是多少平方厘米？',
            type: 'fill',
            difficulty: 'medium',
            knowledge_ids: ['rect_area'],
            answer_key: '40',
            image_paths: [imagePath],
            is_multimodal: true,
            source_refs: [
              {
                source_label: '北京·人教·小学数学',
                textbook_chapter: '长方形面积',
              },
            ],
          },
        ],
        grade: 4,
        curriculum_label: 'pilot',
      },
      inferred_chapter: '长方形面积',
      multimodal_count: 1,
      requested: 1,
      delivered: 1,
      shortfall: 0,
      layer2_used: false,
      layer2_source: 'none',
    })

    render(
      <Assessment
        sessionId="s1"
        profile={{ region: '北京', grade: 4, age: 10 }}
        onComplete={vi.fn()}
      />,
    )

    await waitFor(() => expect(screen.getByText('锚点测评')).toBeInTheDocument())

    const img = screen.getByRole('img', { name: '题目配图 1' })
    expect(img).toHaveAttribute('src', imagePath)
    expect(screen.getByText('长方形面积')).toBeInTheDocument()
    expect(screen.getByText('北京·人教·小学数学')).toBeInTheDocument()
    expect(screen.getByText(/多模态 1 题/)).toBeInTheDocument()
  })
})
