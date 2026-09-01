import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { api, dashboardApi } from './client'

function jsonResponse(body: unknown, status = 200): Response {
  return {
    ok: status >= 200 && status < 300,
    status,
    json: () => Promise.resolve(body),
  } as Response
}

describe('dashboardApi', () => {
  beforeEach(() => {
    vi.stubGlobal('fetch', vi.fn())
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('parentChildren requests the parent children endpoint', async () => {
    const mockFetch = vi.mocked(fetch)
    mockFetch.mockResolvedValue(jsonResponse([]))

    await dashboardApi.parentChildren('p1')

    expect(mockFetch).toHaveBeenCalledWith(
      '/dashboard/parent/p1/children',
      expect.objectContaining({
        headers: expect.objectContaining({ 'Content-Type': 'application/json' }),
      }),
    )
  })

  it('bindTeacher sends the exact JSON body', async () => {
    const mockFetch = vi.mocked(fetch)
    mockFetch.mockResolvedValue({ ok: true, status: 204 } as Response)

    await dashboardApi.bindTeacher('t1', 'c1', 'sess-1')

    expect(mockFetch).toHaveBeenCalledWith(
      '/dashboard/teacher/bind',
      expect.objectContaining({
        method: 'POST',
        body: JSON.stringify({ teacher_id: 't1', class_id: 'c1', session_id: 'sess-1' }),
      }),
    )
  })

  it('bindParent posts parent_id and session_id', async () => {
    const mockFetch = vi.mocked(fetch)
    mockFetch.mockResolvedValue({ ok: true, status: 204 } as Response)

    await dashboardApi.bindParent('p1', 'sess-1')

    expect(mockFetch).toHaveBeenCalledWith(
      '/dashboard/parent/bind',
      expect.objectContaining({
        method: 'POST',
        body: JSON.stringify({ parent_id: 'p1', session_id: 'sess-1' }),
      }),
    )
  })

  it('parentChild requests the child detail endpoint', async () => {
    const mockFetch = vi.mocked(fetch)
    mockFetch.mockResolvedValue(jsonResponse({ session_id: 'sess-1', phase: 'idle', loop_count: 0, profile: {} }))

    await dashboardApi.parentChild('p1', 'sess-1')

    expect(mockFetch).toHaveBeenCalledWith(
      '/dashboard/parent/p1/child/sess-1',
      expect.objectContaining({
        headers: expect.objectContaining({ 'Content-Type': 'application/json' }),
      }),
    )
  })

  it('teacherClasses requests the teacher classes endpoint', async () => {
    const mockFetch = vi.mocked(fetch)
    mockFetch.mockResolvedValue(jsonResponse([]))

    await dashboardApi.teacherClasses('t1')

    expect(mockFetch).toHaveBeenCalledWith(
      '/dashboard/teacher/t1/classes',
      expect.objectContaining({
        headers: expect.objectContaining({ 'Content-Type': 'application/json' }),
      }),
    )
  })

  it('teacherStudents requests the class students endpoint', async () => {
    const mockFetch = vi.mocked(fetch)
    mockFetch.mockResolvedValue(jsonResponse([]))

    await dashboardApi.teacherStudents('t1', 'c1')

    expect(mockFetch).toHaveBeenCalledWith(
      '/dashboard/teacher/t1/class/c1/students',
      expect.objectContaining({
        headers: expect.objectContaining({ 'Content-Type': 'application/json' }),
      }),
    )
  })

  it('teacherStudent requests the student detail endpoint', async () => {
    const mockFetch = vi.mocked(fetch)
    mockFetch.mockResolvedValue(jsonResponse({ session_id: 'sess-1', phase: 'idle', loop_count: 0, profile: {} }))

    await dashboardApi.teacherStudent('t1', 'c1', 'sess-1')

    expect(mockFetch).toHaveBeenCalledWith(
      '/dashboard/teacher/t1/class/c1/student/sess-1',
      expect.objectContaining({
        headers: expect.objectContaining({ 'Content-Type': 'application/json' }),
      }),
    )
  })
})

describe('api.createDemoSession', () => {
  beforeEach(() => {
    vi.stubGlobal('fetch', vi.fn())
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('POSTs /demo/units/{unitId}/session and returns links', async () => {
    const body = {
      session_id: 'sess-demo',
      unit_name: '小数乘法',
      links: {
        student: '?student=1&session_id=sess-demo',
        teacher:
          '?login=1&role=teacher&user=demo_teacher&class_id=demo_class_5a&student_id=sess-demo',
        parent: '?login=1&role=parent&user=demo_parent&student_id=sess-demo',
      },
    }
    const mockFetch = vi.mocked(fetch)
    mockFetch.mockResolvedValue(jsonResponse(body))

    const result = await api.createDemoSession('math_5_1')

    expect(result).toEqual(body)
    expect(mockFetch).toHaveBeenCalledWith(
      '/demo/units/math_5_1/session',
      expect.objectContaining({
        method: 'POST',
        headers: expect.objectContaining({ 'Content-Type': 'application/json' }),
      }),
    )
  })
})

const EFFECTIVENESS = {
  metrics: {
    mastery_gain: 18,
    time_saved_percent: 83.75,
    completion_rate: 100,
    diagnosis_confidence: 0.82,
    weakness_resolved_count: 1,
    traditional_grading_time_minutes: 40,
    estimated_grading_time_minutes: 6.5,
    total_questions: 20,
    evidence_count: 5,
    auto_graded_count: 14,
    manual_review_count: 6,
  },
  comparison: {
    traditional_vs_ilearn: {
      grading_time: { traditional: '40.0分钟', ilearn: '6.5分钟' },
      personalized: { traditional: '统一作业', ilearn: '自适应个性化' },
      feedback_delay: { traditional: '1-2天', ilearn: '即时' },
    },
  },
}

describe('api.getEffectiveness', () => {
  beforeEach(() => {
    vi.stubGlobal('fetch', vi.fn())
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('GETs /sessions/{id}/effectiveness', async () => {
    const mockFetch = vi.mocked(fetch)
    mockFetch.mockResolvedValue(jsonResponse(EFFECTIVENESS))

    const result = await api.getEffectiveness('sess-1')

    expect(result).toEqual(EFFECTIVENESS)
    expect(mockFetch).toHaveBeenCalledWith(
      '/sessions/sess-1/effectiveness',
      expect.objectContaining({
        headers: expect.objectContaining({ 'Content-Type': 'application/json' }),
      }),
    )
  })
})

describe('api.exportEffectivenessPdf', () => {
  beforeEach(() => {
    vi.stubGlobal('fetch', vi.fn())
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('downloads the effectiveness PDF blob', async () => {
    const blob = new Blob(['%PDF'], { type: 'application/pdf' })
    const mockFetch = vi.mocked(fetch)
    mockFetch.mockResolvedValue({
      ok: true,
      status: 200,
      blob: () => Promise.resolve(blob),
    } as Response)
    const createObjectURL = vi.fn(() => 'blob:effectiveness')
    const revokeObjectURL = vi.fn()
    Object.defineProperty(URL, 'createObjectURL', { configurable: true, writable: true, value: createObjectURL })
    Object.defineProperty(URL, 'revokeObjectURL', { configurable: true, writable: true, value: revokeObjectURL })
    const click = vi.fn()
    const link = document.createElement('a')
    link.click = click
    vi.spyOn(document, 'createElement').mockReturnValue(link)

    await api.exportEffectivenessPdf('sess-1')

    expect(mockFetch).toHaveBeenCalledWith('/sessions/sess-1/export/effectiveness.pdf')
    expect(link.download).toBe('ILearn-effectiveness.pdf')
    expect(click).toHaveBeenCalled()
    expect(createObjectURL).toHaveBeenCalled()
    expect(revokeObjectURL).toHaveBeenCalled()
  })
})
