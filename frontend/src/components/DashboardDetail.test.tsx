import { render, screen } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import DashboardDetail from './DashboardDetail'
import { api } from '../api/client'
import type { DashboardStudentDetail, ParentSummary, TeacherSummary } from '../api/client'
import { EFFECTIVENESS } from '../test/effectivenessFixture'

vi.mock('../api/client', async () => {
  const actual = await vi.importActual<typeof import('../api/client')>('../api/client')
  return {
    ...actual,
    api: {
      ...actual.api,
      getEffectiveness: vi.fn(),
      exportEffectivenessPdf: vi.fn(),
      getTeacherSummary: vi.fn(),
      getParentSummary: vi.fn(),
    },
  }
})

const TEACHER_SUMMARY: TeacherSummary = {
  class_name: 'demo_class_5a',
  student_count: 35,
  avg_mastery: 0.62,
  top_weaknesses: [{ skill: '小数乘小数', affected_students: 11 }],
  need_intervention_students: [{ name: '小红', weakness: '小数乘小数', session_id: 's1' }],
  auto_graded_rate: 0.85,
  estimated_time_saved_minutes: 12,
  narrative: '班级需重点补小数乘小数。',
}

const PARENT_SUMMARY: ParentSummary = {
  child_name: '小明',
  current_mastery: 0.72,
  mastery_change: 0.18,
  weak_skills: ['小数乘小数'],
  learning_phase: 'plan',
  daily_practice_tips: ['每天花约 5 分钟完成 2 道生活情境乘法题。'],
  next_milestone: '完成本单元薄弱点巩固',
  narrative: '孩子正在巩固小数乘法。',
}

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
    vi.mocked(api.getTeacherSummary).mockResolvedValue(TEACHER_SUMMARY)
    vi.mocked(api.getParentSummary).mockResolvedValue(PARENT_SUMMARY)
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
    vi.mocked(api.getParentSummary).mockRejectedValue(new Error('summary unavailable'))
    render(<DashboardDetail detail={demoDetail} surface="parent" />)

    expect(screen.getByRole('heading', { name: '家庭辅导建议' })).toBeInTheDocument()
    expect(screen.getByText(/给家长的行动建议/)).toBeInTheDocument()
    expect(screen.getByText(/先口述小数位数再动笔/)).toBeInTheDocument()
    expect(screen.queryByText('掌握度提升')).not.toBeInTheDocument()
  })

  it('shows structured teacher summary when session_id is present', async () => {
    render(<DashboardDetail detail={demoDetail} surface="teacher" />)

    expect(await screen.findByText(/结构化备课摘要/)).toBeInTheDocument()
    expect(screen.getByText(/demo_class_5a/)).toBeInTheDocument()
    expect(api.getTeacherSummary).toHaveBeenCalledWith('s1')
  })

  it('shows structured parent summary when session_id is present', async () => {
    render(<DashboardDetail detail={demoDetail} surface="parent" />)

    expect(await screen.findByText(/结构化家庭摘要/)).toBeInTheDocument()
    expect(screen.getByText(/下一步里程碑/)).toBeInTheDocument()
    expect(api.getParentSummary).toHaveBeenCalledWith('s1')
  })

  it('does not show demo panels when demo_unit is absent', async () => {
    render(<DashboardDetail detail={baseDetail} surface="teacher" />)

    expect(screen.queryByRole('heading', { name: '备课概览' })).not.toBeInTheDocument()
    expect(screen.queryByRole('heading', { name: '家庭辅导建议' })).not.toBeInTheDocument()
    expect(screen.getByText('知识点掌握')).toBeInTheDocument()
    expect(api.getEffectiveness).not.toHaveBeenCalled()
    expect(await screen.findByText(/结构化备课摘要/)).toBeInTheDocument()
  })
})
