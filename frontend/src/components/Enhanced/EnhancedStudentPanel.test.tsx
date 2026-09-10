import { render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { api } from '../../api/client'
import type { EnhancedProfile, ParentSummary, StudentSummary, TeacherSummary } from '../../api/client'
import styles from './enhanced.module.css'
import { EnhancedStudentPanel } from './EnhancedStudentPanel'

const enhancedFlag = vi.hoisted(() => ({ enabled: true }))

vi.mock('../../config/enhanced', () => ({
  get ENHANCED_UI_ENABLED() {
    return enhancedFlag.enabled
  },
}))

vi.mock('../../api/client', async () => {
  const actual = await vi.importActual<typeof import('../../api/client')>('../../api/client')
  return {
    ...actual,
    api: {
      ...actual.api,
      getStudentSummary: vi.fn(),
      getTeacherSummary: vi.fn(),
      getParentSummary: vi.fn(),
    },
  }
})

const STUDENT_SUMMARY: StudentSummary = {
  current_task: '巩固：小数',
  completed_tasks: 1,
  total_tasks: 4,
  stars_earned: 2,
  next_challenge: '挑战：分数',
  narrative: '继续加油',
}

const TEACHER_SUMMARY: TeacherSummary = {
  class_name: '三年二班',
  student_count: 30,
  avg_mastery: 0.6,
  top_weaknesses: [],
  need_intervention_students: [],
  auto_graded_rate: 0.9,
  estimated_time_saved_minutes: 10,
  narrative: '课堂摘要',
}

const PARENT_SUMMARY: ParentSummary = {
  child_name: '小明',
  current_mastery: 0.5,
  mastery_change: 0.1,
  weak_skills: [],
  learning_phase: '巩固',
  daily_practice_tips: [],
  next_milestone: '分数加减',
  narrative: '家长摘要',
}

const PROFILE: EnhancedProfile = {
  cognitive: {
    knowledge_mastery: { 分数: 0.2, 小数: 0.5, 几何: 0.8 },
    weak_concepts: ['分数'],
  },
  emotional: { current_emotion: 'confused' },
  metacognitive: { learning_style: 'guided' },
}

function withProfile<T>(base: T, profile: EnhancedProfile | null | undefined) {
  return { ...base, enhanced_profile: profile }
}

describe('EnhancedStudentPanel', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    enhancedFlag.enabled = true
    vi.mocked(api.getStudentSummary).mockResolvedValue(withProfile(STUDENT_SUMMARY, PROFILE))
    vi.mocked(api.getTeacherSummary).mockResolvedValue(withProfile(TEACHER_SUMMARY, PROFILE))
    vi.mocked(api.getParentSummary).mockResolvedValue(withProfile(PARENT_SUMMARY, PROFILE))
  })

  it('renders nothing when UI flag off', () => {
    enhancedFlag.enabled = false

    const { container } = render(
      <EnhancedStudentPanel sessionId="s1" viewMode="student" />,
    )

    expect(container).toBeEmptyDOMElement()
    expect(api.getStudentSummary).not.toHaveBeenCalled()
    expect(api.getTeacherSummary).not.toHaveBeenCalled()
    expect(api.getParentSummary).not.toHaveBeenCalled()
  })

  it('shows 加载画像… while pending', () => {
    vi.mocked(api.getStudentSummary).mockImplementation(() => new Promise(() => {}))

    render(<EnhancedStudentPanel sessionId="s1" viewMode="student" />)

    const placeholder = screen.getByText('加载画像…')
    expect(placeholder).toBeInTheDocument()
    expect(placeholder).toHaveClass(styles.loading)
    expect(api.getStudentSummary).toHaveBeenCalledWith('s1', { enhanced: true })
  })

  it('renders radar and cards when enhanced_profile is present', async () => {
    render(<EnhancedStudentPanel sessionId="s1" viewMode="student" />)

    expect(await screen.findByText('知识点掌握度')).toBeInTheDocument()
    expect(screen.getByRole('img', { name: '知识点掌握度雷达图' })).toBeInTheDocument()
    expect(screen.getByText('待加强')).toBeInTheDocument()
    expect(screen.getByTitle('分数')).toBeInTheDocument()
    expect(screen.getByText('困惑')).toBeInTheDocument()
    expect(screen.getByText('引导型')).toBeInTheDocument()
    expect(screen.getByText('50%')).toBeInTheDocument()
  })

  it('returns null when enhanced_profile is missing', async () => {
    vi.mocked(api.getStudentSummary).mockResolvedValue(STUDENT_SUMMARY)

    const { container } = render(
      <EnhancedStudentPanel sessionId="s1" viewMode="student" />,
    )

    await waitFor(() => {
      expect(api.getStudentSummary).toHaveBeenCalledWith('s1', { enhanced: true })
    })
    await waitFor(() => {
      expect(screen.queryByText('加载画像…')).not.toBeInTheDocument()
    })
    expect(container).toBeEmptyDOMElement()
  })

  it('returns null when the summary request fails', async () => {
    vi.mocked(api.getStudentSummary).mockRejectedValue(new Error('network'))

    const { container } = render(
      <EnhancedStudentPanel sessionId="s1" viewMode="student" />,
    )

    await waitFor(() => {
      expect(api.getStudentSummary).toHaveBeenCalled()
    })
    await waitFor(() => {
      expect(screen.queryByText('加载画像…')).not.toBeInTheDocument()
    })
    expect(container).toBeEmptyDOMElement()
    expect(screen.queryByRole('alert')).not.toBeInTheDocument()
  })

  it('defaults summaryKind from viewMode teacher to getTeacherSummary', async () => {
    render(<EnhancedStudentPanel sessionId="s1" viewMode="teacher" />)

    await waitFor(() => {
      expect(api.getTeacherSummary).toHaveBeenCalledWith('s1', { enhanced: true })
    })
    expect(api.getStudentSummary).not.toHaveBeenCalled()
    expect(api.getParentSummary).not.toHaveBeenCalled()
    expect(await screen.findByText('薄弱知识点')).toBeInTheDocument()
  })

  it('uses getParentSummary when summaryKind is parent', async () => {
    render(
      <EnhancedStudentPanel
        sessionId="s1"
        viewMode="teacher"
        summaryKind="parent"
      />,
    )

    await waitFor(() => {
      expect(api.getParentSummary).toHaveBeenCalledWith('s1', { enhanced: true })
    })
    expect(api.getTeacherSummary).not.toHaveBeenCalled()
    expect(await screen.findByText('薄弱知识点')).toBeInTheDocument()
  })
})
