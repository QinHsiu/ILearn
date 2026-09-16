import { fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import ErrorNotebookBlock from './ErrorNotebookBlock'
import { api } from '../api/client'

vi.mock('../api/client', async () => {
  const actual = await vi.importActual<typeof import('../api/client')>('../api/client')
  return {
    ...actual,
    api: {
      ...actual.api,
      getErrorNotebook: vi.fn(),
    },
  }
})

const PAYLOAD = {
  session_id: 's1',
  count: 2,
  knowledge_focus: ['小数乘法', '小数点定位'],
  mask_note: '终答已遮罩：错题本只保留题干、步骤与你的作答。',
  repractice_ready: true,
  items: [
    {
      item_id: 'q1',
      stem: '1.2×3=?',
      rubric_steps: ['对齐', '相乘', '点小数点'],
      knowledge_ids: ['小数乘法'],
      citation_label: '人教五上 P.12',
      answer_key: null,
      student_answer: '3',
    },
    {
      item_id: 'q2',
      stem: '0.5×0.4=?',
      rubric_steps: ['相乘', '数小数位'],
      knowledge_ids: ['小数点定位'],
      citation_label: null,
      answer_key: null,
      student_answer: null,
    },
  ],
}

describe('ErrorNotebookBlock', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(api.getErrorNotebook).mockResolvedValue(PAYLOAD)
  })

  it('renders the notebook home: count, focus, masked answers, one-click repractice', async () => {
    const onRepractice = vi.fn()
    render(<ErrorNotebookBlock sessionId="s1" onRepractice={onRepractice} />)
    await waitFor(() => expect(api.getErrorNotebook).toHaveBeenCalledWith('s1'))

    const region = await screen.findByRole('region', { name: /错题本/ })
    expect(within(region).getByText(/共 2 道错题/)).toBeInTheDocument()
    expect(within(region).getByText(/小数乘法、小数点定位/)).toBeInTheDocument()
    expect(within(region).getByText(/终答已遮罩/)).toBeInTheDocument()

    const items = within(region).getAllByRole('listitem')
    expect(items).toHaveLength(2)
    expect(within(items[0]).getByText('1.2×3=?')).toBeInTheDocument()
    expect(within(items[0]).getByText(/我的作答：3/)).toBeInTheDocument()
    expect(within(items[0]).getByText(/人教五上 P.12/)).toBeInTheDocument()
    expect(within(items[1]).getByText(/我的作答：未作答/)).toBeInTheDocument()
    expect(within(region).getAllByText('终答 ●●●')).toHaveLength(2)
    expect(within(region).queryByText(/3\.6/)).not.toBeInTheDocument()

    fireEvent.click(within(region).getByRole('button', { name: '一键重练这 2 道' }))
    expect(onRepractice).toHaveBeenCalledTimes(1)
  })

  it('read-only mode (parent) hides the repractice CTA but keeps the mask', async () => {
    render(<ErrorNotebookBlock sessionId="s1" readOnly />)
    const region = await screen.findByRole('region', { name: /错题本/ })
    expect(within(region).queryByRole('button', { name: /一键重练/ })).not.toBeInTheDocument()
    expect(within(region).getByText(/终答已遮罩/)).toBeInTheDocument()
    expect(within(region).getByText(/家长不看终答/)).toBeInTheDocument()
  })

  it('shows an honest empty state when there are no wrong items', async () => {
    vi.mocked(api.getErrorNotebook).mockResolvedValue({
      ...PAYLOAD,
      count: 0,
      items: [],
      knowledge_focus: [],
      repractice_ready: false,
    })
    render(<ErrorNotebookBlock sessionId="s1" onRepractice={vi.fn()} />)
    const region = await screen.findByRole('region', { name: /错题本/ })
    expect(within(region).getByText(/本场没有错题/)).toBeInTheDocument()
    expect(within(region).queryByRole('button', { name: /一键重练/ })).not.toBeInTheDocument()
  })
})
