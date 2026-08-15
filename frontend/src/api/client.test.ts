import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { dashboardApi } from './client'

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
