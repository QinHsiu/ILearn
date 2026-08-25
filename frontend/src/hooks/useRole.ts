import type { AuthRole } from '../api/client'

export type AppRole = AuthRole | 'student' | null

export type RoleState = {
  role: AppRole
  userId: string
  isStudent: boolean
  isTeacher: boolean
  isParent: boolean
  getDashboardRoute: () => string
}

function readSearchParams(): URLSearchParams {
  if (typeof window === 'undefined') return new URLSearchParams()
  return new URLSearchParams(window.location.search)
}

/** Role routing from URL query (aligned with existing landing/login flow). */
export function useRole(): RoleState {
  const params = readSearchParams()
  const rawRole = params.get('role')
  const userId = params.get('user') || ''
  const isStudentEntry = params.get('student') === '1'

  let role: AppRole = null
  if (rawRole === 'parent' || rawRole === 'teacher') {
    role = rawRole
  } else if (isStudentEntry) {
    role = 'student'
  }

  return {
    role,
    userId,
    isStudent: role === 'student',
    isTeacher: role === 'teacher',
    isParent: role === 'parent',
    getDashboardRoute: () => {
      if (role === 'student') return '?student=1'
      if (role === 'teacher' && userId) {
        return `?role=teacher&user=${encodeURIComponent(userId)}`
      }
      if (role === 'parent' && userId) {
        return `?role=parent&user=${encodeURIComponent(userId)}`
      }
      if (role === 'teacher') return '?login=1&role=teacher'
      if (role === 'parent') return '?login=1&role=parent'
      return '/'
    },
  }
}
