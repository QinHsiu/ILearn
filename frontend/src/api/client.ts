export type Gender = 'male' | 'female' | 'unspecified'

export type StudentProfile = {
  region: string
  grade: number
  age: number
  nickname?: string | null
  gender?: Gender
  learning_difficulty?: boolean | null
  subject?: string
}

export type SourceRef = {
  example_id?: string | null
  curriculum_objective_ids?: string[]
  textbook_chapter?: string | null
  example_stem?: string | null
  example_answer?: string | null
  example_difficulty?: string | null
  source_label?: string | null
}

export type AssessmentItem = {
  id: string
  stem: string
  type: string
  difficulty: string
  knowledge_ids: string[]
  answer_key?: string | null
  choices?: string[] | null
  source_refs?: SourceRef[]
  situation_tag?: string | null
}

export type AssessmentPaper = {
  items: AssessmentItem[]
  grade: number
  curriculum_label: string
}

export type GradeResult = {
  item_id: string
  final_correct: boolean
  grading_degraded?: boolean
}

export type StudentAnswer = {
  item_id: string
  answer_text: string
}

export type SessionState = {
  session_id: string
  phase: string
  loop_count: number
  profile: StudentProfile
  paper?: AssessmentPaper | null
  answers?: StudentAnswer[]
  grades?: GradeResult[] | null
  diagnosis?: {
    knowledge_mastery?: Array<{
      knowledge_id: string
      knowledge_name?: string
      score_rate: number
      level: string
      error_tag_counts?: Record<string, number>
    }>
    ability_scores?: Record<string, number>
    interventions?: Array<{ knowledge_id: string; reason?: string; action?: string }>
  } | null
  plan?: {
    status?: string
    markdown?: string
    items?: Array<{ title?: string; detail?: string; curriculum_basis?: string }>
  } | null
  metadata?: {
    diagnosis_enrichment?: {
      weak_skills?: string[]
      prerequisite_gaps?: string[]
      learning_advice?: string
    }
    scientific_plan?: {
      tasks?: Array<{ type?: string; skill?: string; instruction?: string }>
      review_schedule?: Array<{ skill?: string; scheduled_date?: string; session?: number }>
      estimated_total_hours?: number
    }
    [key: string]: unknown
  }
}

export type ImageMime = 'image/png' | 'image/jpeg' | 'image/webp'

export type ImageAnswer = {
  item_id: string
  image_base64: string
  mime_type: ImageMime
}

export type ReportResponse = {
  markdown: string
  session: SessionState
}

export type TutorTurn = {
  phase: string
  message: string
  error_tag?: string | null
}

export type SessionSummary = {
  session_id: string
  nickname?: string | null
  grade: number
  phase: string
}

export type DashboardStudentSummary = {
  session_id: string
  nickname: string
  grade: number
  region: string
  overall_mastery: number
  weak_skills: string[]
  skill_mastery: Record<string, number>
  updated_at?: string | null
  phase: string
}

export type DashboardClassSummary = {
  class_id: string
  students: DashboardStudentSummary[]
}

export type DashboardStudentDetail = SessionState

export type AuthRole = 'parent' | 'teacher'

export type LoginResponse = {
  role: AuthRole
  user_id: string
}

const MIME_BY_EXT: Record<string, ImageMime> = {
  png: 'image/png',
  jpg: 'image/jpeg',
  jpeg: 'image/jpeg',
  webp: 'image/webp',
}

export function mimeTypeForUpload(filename: string, fallback?: string): ImageMime | null {
  const ext = filename.split('.').pop()?.toLowerCase() || ''
  if (ext && MIME_BY_EXT[ext]) return MIME_BY_EXT[ext]
  if (fallback === 'image/png' || fallback === 'image/jpeg' || fallback === 'image/webp') {
    return fallback
  }
  return null
}

export function fileToImageAnswer(itemId: string, file: File): Promise<ImageAnswer> {
  const mime = mimeTypeForUpload(file.name, file.type)
  if (!mime) {
    return Promise.reject(new Error('仅支持 PNG、JPG 或 WebP'))
  }
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = () => {
      const dataUrl = String(reader.result || '')
      const comma = dataUrl.indexOf(',')
      const image_base64 = comma >= 0 ? dataUrl.slice(comma + 1) : dataUrl
      resolve({ item_id: itemId, image_base64, mime_type: mime })
    }
    reader.onerror = () => reject(new Error('图片读取失败'))
    reader.readAsDataURL(file)
  })
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, {
    headers: { 'Content-Type': 'application/json', ...(init?.headers || {}) },
    ...init,
  })
  if (!response.ok) {
    let detail = `HTTP ${response.status}`
    try {
      const body = await response.json()
      detail = body.detail || detail
    } catch {
      /* ignore */
    }
    throw new Error(typeof detail === 'string' ? detail : JSON.stringify(detail))
  }
  if (response.status === 204) return undefined as T
  return response.json() as Promise<T>
}

export type AdaptiveAssessmentResponse = {
  is_anchor: boolean
  paper: AssessmentPaper
  inferred_chapter?: string | null
  inferred_kps?: string[]
  anchor_kps?: string[]
  target_kps?: string[]
  semester?: string | null
  diagnosis?: Record<string, unknown> | null
  requested?: number
  delivered?: number
  shortfall?: number
  layer2_used?: boolean
  layer2_source?: string
}

export type AdaptiveAnchorResult = {
  item_id: string
  is_correct: boolean
  knowledge_ids?: string[]
}

export const api = {
  createSession(profile: StudentProfile) {
    return request<{ session_id: string }>('/sessions', {
      method: 'POST',
      body: JSON.stringify(profile),
    })
  },
  generateAssessment(sessionId: string) {
    return request<AssessmentPaper>(`/sessions/${sessionId}/assessment`, {
      method: 'POST',
    })
  },
  adaptiveStart(sessionId: string, semester?: string) {
    return request<AdaptiveAssessmentResponse>(
      `/sessions/${sessionId}/assessment/adaptive/start`,
      {
        method: 'POST',
        body: JSON.stringify(semester ? { semester } : {}),
      },
    )
  },
  adaptiveContinue(sessionId: string, anchorResults: AdaptiveAnchorResult[]) {
    return request<AdaptiveAssessmentResponse>(
      `/sessions/${sessionId}/assessment/adaptive/continue`,
      {
        method: 'POST',
        body: JSON.stringify({ anchor_results: anchorResults }),
      },
    )
  },
  submit(sessionId: string, answers: Record<string, string>, itemMeta: Record<string, object> = {}) {
    return request<SessionState>(`/sessions/${sessionId}/submit`, {
      method: 'POST',
      body: JSON.stringify({ answers, item_meta: itemMeta }),
    })
  },
  submitImages(sessionId: string, images: ImageAnswer[]) {
    return request<SessionState>(`/sessions/${sessionId}/submit-images`, {
      method: 'POST',
      body: JSON.stringify({ images }),
    })
  },
  run(sessionId: string) {
    return request<SessionState>(`/sessions/${sessionId}/run`, { method: 'POST' })
  },
  getReport(sessionId: string) {
    return request<ReportResponse>(`/sessions/${sessionId}/report`)
  },
  tutorStart(sessionId: string, itemId: string) {
    return request<TutorTurn>(`/sessions/${sessionId}/tutor`, {
      method: 'POST',
      body: JSON.stringify({ item_id: itemId }),
    })
  },
  tutorHint(sessionId: string, itemId: string, userMessage: string) {
    return request<TutorTurn>(`/sessions/${sessionId}/tutor/hint`, {
      method: 'POST',
      body: JSON.stringify({ item_id: itemId, user_message: userMessage }),
    })
  },
  replan(sessionId: string) {
    return request<{ markdown: string; status?: string }>(
      `/sessions/${sessionId}/replan`,
      { method: 'POST' },
    )
  },
  listSessions(nickname: string) {
    const q = new URLSearchParams({ nickname })
    return request<SessionSummary[]>(`/sessions?${q.toString()}`)
  },
  deleteSession(sessionId: string) {
    return request<void>(`/sessions/${sessionId}`, { method: 'DELETE' })
  },
  getPhase(sessionId: string) {
    return request<{ phase: string; loop_count: number }>(`/sessions/${sessionId}/phase`)
  },
  async downloadExport(sessionId: string, kind: 'assessment' | 'report', filename: string) {
    const path =
      kind === 'assessment'
        ? `/sessions/${sessionId}/export/assessment.pdf`
        : `/sessions/${sessionId}/export/report.pdf`
    const response = await fetch(path)
    if (!response.ok) {
      let detail = `HTTP ${response.status}`
      try {
        const body = await response.json()
        detail = body.detail || detail
      } catch {
        /* ignore */
      }
      throw new Error(typeof detail === 'string' ? detail : JSON.stringify(detail))
    }
    const blob = await response.blob()
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = filename
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    URL.revokeObjectURL(url)
  },
}

export const authApi = {
  login(role: AuthRole, username: string, password: string) {
    return request<LoginResponse>('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ role, username, password }),
    })
  },
}

export const dashboardApi = {
  bindParent(parentId: string, sessionId: string) {
    return request<void>('/dashboard/parent/bind', {
      method: 'POST',
      body: JSON.stringify({ parent_id: parentId, session_id: sessionId }),
    })
  },
  bindTeacher(teacherId: string, classId: string, sessionId: string) {
    return request<void>('/dashboard/teacher/bind', {
      method: 'POST',
      body: JSON.stringify({ teacher_id: teacherId, class_id: classId, session_id: sessionId }),
    })
  },
  parentChildren(parentId: string) {
    return request<DashboardStudentSummary[]>(`/dashboard/parent/${parentId}/children`)
  },
  parentChild(parentId: string, sessionId: string) {
    return request<DashboardStudentDetail>(`/dashboard/parent/${parentId}/child/${sessionId}`)
  },
  teacherClasses(teacherId: string) {
    return request<DashboardClassSummary[]>(`/dashboard/teacher/${teacherId}/classes`)
  },
  teacherStudents(teacherId: string, classId: string) {
    return request<DashboardStudentSummary[]>(
      `/dashboard/teacher/${teacherId}/class/${classId}/students`,
    )
  },
  teacherStudent(teacherId: string, classId: string, sessionId: string) {
    return request<DashboardStudentDetail>(
      `/dashboard/teacher/${teacherId}/class/${classId}/student/${sessionId}`,
    )
  },
}
