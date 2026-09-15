import { render, screen, waitFor, within } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import WeeklyReportPanel from './WeeklyReportPanel'
import { api } from '../api/client'

vi.mock('../api/client', async () => {
  const actual = await vi.importActual<typeof import('../api/client')>('../api/client')
  const bucket = (label: string, over: Partial<Record<string, unknown>> = {}) => ({
    label,
    start: '2026-09-14',
    end: '2026-09-20',
    session_count: 2,
    active_days: 2,
    evidence_count: 4,
    probe_correct_count: 3,
    hinted_correct_count: 1,
    probe_gap_count: 1,
    mastery_percent: 72,
    accuracy_percent: 83,
    focus: ['小数乘法'],
    session_ids: ['a', 'b'],
    ...over,
  })
  return {
    ...actual,
    api: {
      ...actual.api,
      getLearnerWeeklyReport: vi.fn().mockResolvedValue({
        nickname: '小明',
        generated_at: '2026-09-16T12:00:00+08:00',
        week_start: '2026-09-14',
        week_end: '2026-09-20',
        this_week: bucket('本周'),
        last_week: bucket('上周', {
          start: '2026-09-07',
          end: '2026-09-13',
          session_count: 1,
          active_days: 1,
          evidence_count: 1,
          probe_correct_count: 1,
          hinted_correct_count: 0,
          probe_gap_count: 2,
          mastery_percent: 60,
          accuracy_percent: 33,
          focus: ['小数意义'],
        }),
        has_baseline: true,
        delta: {
          session_count: 1,
          active_days: 1,
          evidence_count: 3,
          probe_correct_count: 2,
          probe_gap_count: -1,
          mastery_percent: 12,
        },
        narrative: '比上周：证据+3条（更好）；探针缺口-1（更好）。',
        honesty_note: '提示后做对不计入掌握；正确率只作参考。',
      }),
    },
  }
})

describe('WeeklyReportPanel', () => {
  it('renders this week vs last week with evidence-first rows and the honesty footnote', async () => {
    render(<WeeklyReportPanel nickname="小明" />)
    await waitFor(() => expect(api.getLearnerWeeklyReport).toHaveBeenCalledWith('小明'))

    const region = await screen.findByRole('region', { name: /本周学习周报/ })
    expect(within(region).getByText(/2026-09-14/)).toBeInTheDocument()
    expect(within(region).getByText(/比上周：证据\+3条/)).toBeInTheDocument()

    const table = within(region).getByRole('table')
    expect(within(table).getByRole('columnheader', { name: '本周' })).toBeInTheDocument()
    expect(within(table).getByRole('columnheader', { name: '上周' })).toBeInTheDocument()
    const evidenceRow = within(table).getByRole('row', { name: /证据条数/ })
    expect(within(evidenceRow).getByText('4')).toBeInTheDocument()
    expect(within(evidenceRow).getByText('1')).toBeInTheDocument()
    expect(within(evidenceRow).getByText('+3')).toBeInTheDocument()
    expect(within(table).getByRole('row', { name: /独立探针通过/ })).toBeInTheDocument()
    expect(within(table).getByRole('row', { name: /提示后做对（未计掌握）/ })).toBeInTheDocument()
    expect(within(table).getByRole('row', { name: /正确率（仅参考）/ })).toBeInTheDocument()

    expect(within(region).getByText(/提示后做对不计入掌握/)).toBeInTheDocument()
    expect(within(region).getByText(/小数乘法/)).toBeInTheDocument()
  })
})
