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
  image_paths?: string[]
  is_multimodal?: boolean
  geo_config?: {
    type?: 'drag_point' | 'drag_slider' | 'construct_shape'
    config?: {
      boundingbox?: number[]
      start?: [number, number]
      snapToGrid?: boolean
    }
    correct_answer?: { x: number; y: number }
  } | null
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

export type HintInteraction = {
  item_id: string
  turn: number
  user_input: string
  ai_hint: string
  has_image?: boolean
  solved_after_hint?: boolean | null
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
  hint_interactions?: Record<string, HintInteraction[]>
  evidence_log?: Array<{
    evidence_id?: string
    knowledge_id?: string
    correct?: boolean
    error_tag?: string | null
    hint_level?: string
    lane?: string
    item_id?: string
  }>
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
      parent_summary?: string
      teacher_summary?: string
    }
    demo_unit?: string
    demo_class_data?: DemoClassData
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

export type DemoSessionLinks = {
  student: string
  teacher: string
  parent: string
}

export type DemoSessionResponse = {
  session_id: string
  unit_name: string
  links: DemoSessionLinks
}

export type DemoClassData = {
  class_size?: number
  avg_mastery?: number
  mastery_distribution?: number[]
  common_weaknesses?: string[]
}

export type TeachingEffectivenessMetrics = {
  pre_assessment_score: number
  post_assessment_score: number | null
  mastery_gain: number
  weakness_resolved_count: number
  weakness_remaining_count: number
  total_questions: number
  auto_graded_count: number
  manual_review_count: number
  estimated_grading_time_minutes: number
  traditional_grading_time_minutes: number
  time_saved_percent: number
  session_duration_seconds: number
  hint_used_count: number
  avg_response_time_seconds: number
  completion_rate: number
  diagnosis_confidence: number
  evidence_count: number
  parent_view_count: number
  teacher_notes_count: number
  is_simulated: boolean
  data_source: string
}

export type EffectivenessComparisonPair = {
  traditional: string
  ilearn: string
}

export type EffectivenessResponse = {
  metrics: TeachingEffectivenessMetrics
  comparison: {
    traditional_vs_ilearn: {
      grading_time: EffectivenessComparisonPair
      personalized: EffectivenessComparisonPair
      feedback_delay: EffectivenessComparisonPair
    }
  }
}

export type PdfBackendInfo = {
  backend: 'weasyprint' | 'fpdf2'
  weasyprint_available: boolean
  forced: boolean
  last_used: 'weasyprint' | 'fpdf2' | null
  fallback_active: boolean
}

export type LoginResponse = {
  role: AuthRole
  user_id: string
}

export type WeaknessStat = { skill: string; affected_students: number }
export type InterventionStudent = { name: string; weakness: string; session_id: string }
export type TeacherSummary = {
  class_name: string
  student_count: number
  avg_mastery: number
  top_weaknesses: WeaknessStat[]
  need_intervention_students: InterventionStudent[]
  auto_graded_rate: number
  estimated_time_saved_minutes: number
  narrative: string
}
export type ParentSummary = {
  child_name: string
  current_mastery: number
  mastery_change: number
  weak_skills: string[]
  learning_phase: string
  daily_practice_tips: string[]
  next_milestone: string
  narrative: string
}
export type StudentSummary = {
  current_task: string
  completed_tasks: number
  total_tasks: number
  stars_earned: number
  next_challenge: string
  narrative: string
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

async function downloadBlob(path: string, filename: string): Promise<void> {
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
}

export type CurriculumRefSummary = {
  region?: string
  edition?: string
  grade?: number
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
  multimodal_count?: number
  curriculum_ref_summary?: CurriculumRefSummary | null
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
  createDemoSession(unitId: string) {
    return request<DemoSessionResponse>(`/demo/units/${unitId}/session`, {
      method: 'POST',
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
  getSession(sessionId: string) {
    return request<SessionState>(`/sessions/${sessionId}`)
  },
  getEffectiveness(sessionId: string) {
    return request<EffectivenessResponse>(`/sessions/${sessionId}/effectiveness`)
  },
  getPdfBackend() {
    return request<PdfBackendInfo>('/system/pdf-backend')
  },
  getTeacherSummary(sessionId: string) {
    return request<TeacherSummary>(`/sessions/${sessionId}/summary/teacher`)
  },
  getParentSummary(sessionId: string) {
    return request<ParentSummary>(`/sessions/${sessionId}/summary/parent`)
  },
  getStudentSummary(sessionId: string) {
    return request<StudentSummary>(`/sessions/${sessionId}/summary/student`)
  },
  heartbeat(sessionId: string) {
    return request<{ ok: boolean; phase: string; server_time: string }>(
      `/sessions/${sessionId}/heartbeat`,
      { method: 'POST' },
    )
  },
  exportEffectivenessPdf(sessionId: string, filename = 'ILearn-effectiveness.pdf') {
    return downloadBlob(`/sessions/${sessionId}/export/effectiveness.pdf`, filename)
  },
  downloadExport(sessionId: string, kind: 'assessment' | 'report', filename: string) {
    const path =
      kind === 'assessment'
        ? `/sessions/${sessionId}/export/assessment.pdf`
        : `/sessions/${sessionId}/export/report.pdf`
    return downloadBlob(path, filename)
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
