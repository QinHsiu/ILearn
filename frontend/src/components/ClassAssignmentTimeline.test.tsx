import { render, screen, within } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import ClassAssignmentTimeline from './ClassAssignmentTimeline'

const ROWS = [
  {
    session_id: 's-a',
    student_name: '甲',
    assigned_at: '2026-09-16T01:00:00+00:00',
    topic: '小数乘法',
    item_counts: { basic: 2, advanced: 1 },
    completion: { state: 'submitted' as const, label: '已提交', at: '2026-09-16T02:00:00+00:00' },
  },
  {
    session_id: 's-b',
    student_name: '乙',
    assigned_at: '2026-09-16T01:00:00+00:00',
    topic: '小数乘法',
    item_counts: { basic: 2 },
    completion: { state: 'in_repractice' as const, label: '重练中', at: '2026-09-16T01:30:00+00:00' },
  },
  {
    session_id: 's-c',
    student_name: '丙',
    assigned_at: '2026-09-16T01:00:00+00:00',
    topic: '小数乘法',
    item_counts: { basic: 2 },
    completion: { state: 'not_started' as const, label: '未开始', at: null },
  },
]

describe('ClassAssignmentTimeline', () => {
  it('shows per-student completion state and a class follow-up summary', () => {
    render(
      <ClassAssignmentTimeline
        rows={ROWS}
        summary={{ not_started: 1, in_repractice: 1, submitted: 1 }}
      />,
    )
    const summary = screen.getByRole('group', { name: '布置回访' })
    expect(within(summary).getByText(/已提交 1/)).toBeInTheDocument()
    expect(within(summary).getByText(/重练中 1/)).toBeInTheDocument()
    expect(within(summary).getByText(/未开始 1/)).toBeInTheDocument()

    const items = screen.getAllByRole('listitem')
    expect(items).toHaveLength(3)
    expect(within(items[0]).getByText('甲')).toBeInTheDocument()
    expect(within(items[0]).getByText('已提交')).toHaveAttribute('data-state', 'submitted')
    expect(within(items[1]).getByText('重练中')).toHaveAttribute('data-state', 'in_repractice')
    expect(within(items[2]).getByText('未开始')).toHaveAttribute('data-state', 'not_started')
  })

  it('renders the empty hint when there are no receipts', () => {
    render(<ClassAssignmentTimeline rows={[]} summary={null} />)
    expect(screen.getByText(/暂无班级级布置回执/)).toBeInTheDocument()
    expect(screen.queryByRole('group', { name: '布置回访' })).not.toBeInTheDocument()
  })
})
