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

export type AssessmentItem = {
  id: string
  stem: string
  type: string
  difficulty: string
  knowledge_ids: string[]
  choices?: string[] | null
  source_refs?: Array<{
    example_id?: string | null
    curriculum_objective_ids?: string[]
    textbook_chapter?: string | null
    source_label?: string | null
  }>
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

export type SessionState = {
  session_id: string
  phase: string
  loop_count: number
  profile: StudentProfile
  paper?: AssessmentPaper | null
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
}

export type ReportResponse = {
  markdown: string
  session: SessionState
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
  return response.json() as Promise<T>
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
  submit(sessionId: string, answers: Record<string, string>, itemMeta: Record<string, object> = {}) {
    return request<SessionState>(`/sessions/${sessionId}/submit`, {
      method: 'POST',
      body: JSON.stringify({ answers, item_meta: itemMeta }),
    })
  },
  run(sessionId: string) {
    return request<SessionState>(`/sessions/${sessionId}/run`, { method: 'POST' })
  },
  getReport(sessionId: string) {
    return request<ReportResponse>(`/sessions/${sessionId}/report`)
  },
  getPhase(sessionId: string) {
    return request<{ phase: string; loop_count: number }>(`/sessions/${sessionId}/phase`)
  },
}
