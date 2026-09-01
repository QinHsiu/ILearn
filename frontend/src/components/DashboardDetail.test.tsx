import { render, screen } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import DashboardDetail from './DashboardDetail'
import { api } from '../api/client'
import type { DashboardStudentDetail } from '../api/client'
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

const baseDetail: DashboardStudentDetail = {
  session_id: 's1',
  phase: 'plan',
  loop_count: 0,
  profile: { region: '北京', grade: 5, age: 11, nickname: '小明' },
  diagnosis: {
    knowledge_mastery: [
      { knowledge_id: 'k1', knowledge_name: '代数', score_rate: 0.8, level: 'mastered' },
    ],
  },
  plan: { status: 'ready', markdown: '学习计划' },
}

const demoDetail: DashboardStudentDetail = {
  ...baseDetail,
  metadata: {
    demo_unit: 'math_5_1',
    demo_class_data: {
      class_size: 35,
      avg_mastery: 0.62,
      mastery_distribution: [8, 12, 10, 5],
      common_weaknesses: ['小数乘小数', '运算律推广'],
    },
    diagnosis_enrichment: {
      parent_summary: '给家长的行动建议：每天花约 5 分钟完成 2 道生活情境乘法题。',
      learning_advice: '先口述小数位数再动笔。',
    },
  },
}

describe('DashboardDetail demo panels', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(api.getEffectiveness).mockResolvedValue(EFFECTIVENESS)
  })

  it('shows demo_class_data on the teacher surface when demo_unit is set', async () => {
    render(<DashboardDetail detail={demoDetail} surface="teacher" />)

    expect(screen.getByRole('heading', { name: '备课概览' })).toBeInTheDocument()
    expect(screen.getByText('小数乘法')).toBeInTheDocument()
    expect(screen.getByText('35')).toBeInTheDocument()
    expect(screen.getByText('62%')).toBeInTheDocument()
    expect(screen.getByText(/小数乘小数/)).toBeInTheDocument()
    expect(screen.getByText(/运算律推广/)).toBeInTheDocument()
    expect(await screen.findByText('掌握度提升')).toBeInTheDocument()
    expect(api.getEffectiveness).toHaveBeenCalledWith('s1')
  })

  it('shows parent_summary on the parent surface when demo_unit is set', () => {
    render(<DashboardDetail detail={demoDetail} surface="parent" />)

    expect(screen.getByRole('heading', { name: '家庭辅导建议' })).toBeInTheDocument()
    expect(screen.getByText(/给家长的行动建议/)).toBeInTheDocument()
    expect(screen.getByText(/先口述小数位数再动笔/)).toBeInTheDocument()
    expect(screen.queryByText('掌握度提升')).not.toBeInTheDocument()
  })

  it('does not show demo panels when demo_unit is absent', () => {
    render(<DashboardDetail detail={baseDetail} surface="teacher" />)

    expect(screen.queryByRole('heading', { name: '备课概览' })).not.toBeInTheDocument()
    expect(screen.queryByRole('heading', { name: '家庭辅导建议' })).not.toBeInTheDocument()
    expect(screen.getByText('知识点掌握')).toBeInTheDocument()
    expect(api.getEffectiveness).not.toHaveBeenCalled()
  })
})
