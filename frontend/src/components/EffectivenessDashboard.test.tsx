import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import EffectivenessDashboard from './EffectivenessDashboard'
import { api } from '../api/client'
import { EFFECTIVENESS } from '../test/effectivenessFixture'

vi.mock('../api/client', async () => {
  const actual = await vi.importActual<typeof import('../api/client')>('../api/client')
  return {
    ...actual,
    api: {
      ...actual.api,
      getEffectiveness: vi.fn(),
      exportEffectivenessPdf: vi.fn(),
    },
  }
})

describe('EffectivenessDashboard', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(api.getEffectiveness).mockResolvedValue(EFFECTIVENESS)
    vi.mocked(api.exportEffectivenessPdf).mockResolvedValue(undefined)
  })

  it('renders before/after comparison cards', async () => {
    render(<EffectivenessDashboard sessionId="s1" />)

    expect(await screen.findByRole('heading', { name: '前后对比' })).toBeInTheDocument()
    expect(screen.getByLabelText('掌握度前后对比')).toHaveTextContent(/60.*78/)
    expect(screen.getByLabelText('薄弱点对比')).toHaveTextContent(/已解决 1/)
    expect(screen.getByLabelText('批改耗时对比')).toHaveTextContent(/40.*6\.5/)
    expect(screen.getByLabelText('诊断依据')).toHaveTextContent(/82%.*5/)
  })

  it('renders four metric cards from fetched metrics', async () => {
    render(<EffectivenessDashboard sessionId="s1" />)

    expect(await screen.findByText('掌握度提升')).toBeInTheDocument()
    expect(screen.getByText('+18%')).toBeInTheDocument()
    expect(screen.getByText('批改时间节省')).toBeInTheDocument()
    expect(screen.getByText('84%')).toBeInTheDocument()
    expect(screen.getByText('完成率')).toBeInTheDocument()
    expect(screen.getByText('100%')).toBeInTheDocument()
    expect(screen.getByText('诊断置信度')).toBeInTheDocument()
    expect(screen.getByText('82%')).toBeInTheDocument()
    expect(api.getEffectiveness).toHaveBeenCalledWith('s1')
  })

  it('renders the traditional vs ILearn comparison table', async () => {
    render(<EffectivenessDashboard sessionId="s1" />)

    expect(await screen.findByRole('heading', { name: '与传统教学对比' })).toBeInTheDocument()
    expect(screen.getByText('40.0分钟')).toBeInTheDocument()
    expect(screen.getByText('6.5分钟')).toBeInTheDocument()
    expect(screen.getByText('统一作业')).toBeInTheDocument()
    expect(screen.getByText('自适应个性化')).toBeInTheDocument()
    expect(screen.getByText('1-2天')).toBeInTheDocument()
    expect(screen.getByText('即时')).toBeInTheDocument()
  })

  it('export button downloads the effectiveness PDF', async () => {
    render(<EffectivenessDashboard sessionId="s1" />)

    const button = await screen.findByRole('button', { name: '导出效果验证报告' })
    fireEvent.click(button)

    await waitFor(() => {
      expect(api.exportEffectivenessPdf).toHaveBeenCalledWith('s1')
    })
  })
})
