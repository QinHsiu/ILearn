import { describe, expect, it } from 'vitest'
import type { SessionState } from '../api/client'
import { nextStepOnSync, stepFromSession } from './sessionStep'

const emptySession = {
  session_id: 's1',
  phase: 'practice',
  loop_count: 0,
  profile: { region: '北京', grade: 5, age: 11 },
} as SessionState

describe('stepFromSession', () => {
  it('returns 0 when server has no paper, grades, or plan', () => {
    expect(stepFromSession(emptySession)).toBe(0)
  })

  it('maps paper → assessment, grades → diagnosis, plan → plan', () => {
    expect(
      stepFromSession({
        ...emptySession,
        paper: { items: [], grade: 5, curriculum_label: 'x' },
      } as SessionState),
    ).toBe(2)
    expect(
      stepFromSession({
        ...emptySession,
        grades: [{ item_id: 'i1', final_correct: true }],
      } as SessionState),
    ).toBe(3)
    expect(
      stepFromSession({
        ...emptySession,
        plan: { status: 'draft' },
      } as SessionState),
    ).toBe(4)
  })
})

describe('nextStepOnSync', () => {
  it('does not drop companion step to 0 when server has no paper', () => {
    expect(nextStepOnSync(1, emptySession)).toBe(1)
  })

  it('advances when server has grades or plan', () => {
    const withGrades = {
      ...emptySession,
      grades: [{ item_id: 'i1', final_correct: true }],
    } as SessionState
    expect(nextStepOnSync(1, withGrades)).toBe(3)

    const withPlan = { ...emptySession, plan: { status: 'draft' } } as SessionState
    expect(nextStepOnSync(2, withPlan)).toBe(4)
  })
})
