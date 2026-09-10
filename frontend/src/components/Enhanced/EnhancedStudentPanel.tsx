import { useEffect, useState } from 'react'
import { api } from '../../api/client'
import type { EnhancedProfile } from '../../api/client'
import { ENHANCED_UI_ENABLED } from '../../config/enhanced'
import { EmotionCard } from './EmotionCard'
import { KnowledgeRadar } from './KnowledgeRadar'
import { WeakConceptsCard } from './WeakConceptsCard'
import styles from './enhanced.module.css'

type ViewMode = 'student' | 'teacher'
type SummaryKind = 'student' | 'teacher' | 'parent'

interface EnhancedStudentPanelProps {
  sessionId: string
  viewMode: ViewMode
  summaryKind?: SummaryKind
}

type EnhancedSummaryPayload = {
  enhanced_profile?: EnhancedProfile | null
}

function resolveSummaryKind(viewMode: ViewMode, summaryKind?: SummaryKind): SummaryKind {
  return summaryKind ?? (viewMode === 'student' ? 'student' : 'teacher')
}

function fetchEnhancedSummary(sessionId: string, kind: SummaryKind) {
  const options = { enhanced: true }
  if (kind === 'parent') return api.getParentSummary(sessionId, options)
  if (kind === 'teacher') return api.getTeacherSummary(sessionId, options)
  return api.getStudentSummary(sessionId, options)
}

function overallMastery(mastery: Record<string, number>): number | undefined {
  const values = Object.values(mastery)
  if (values.length === 0) return undefined
  return values.reduce((sum, value) => sum + value, 0) / values.length
}

export function EnhancedStudentPanel({
  sessionId,
  viewMode,
  summaryKind,
}: EnhancedStudentPanelProps) {
  const kind = resolveSummaryKind(viewMode, summaryKind)
  const [profile, setProfile] = useState<EnhancedProfile | null>(null)
  const [loading, setLoading] = useState(() => ENHANCED_UI_ENABLED && Boolean(sessionId))

  useEffect(() => {
    if (!ENHANCED_UI_ENABLED || !sessionId) return

    let cancelled = false
    setLoading(true)
    setProfile(null)

    fetchEnhancedSummary(sessionId, kind)
      .then((data) => {
        if (cancelled) return
        const enhanced = (data as EnhancedSummaryPayload).enhanced_profile
        setProfile(enhanced ?? null)
      })
      .catch(() => {
        if (!cancelled) setProfile(null)
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })

    return () => {
      cancelled = true
    }
  }, [sessionId, kind])

  if (!ENHANCED_UI_ENABLED) return null

  if (loading) {
    return <div className={styles.loading}>加载画像…</div>
  }

  if (!profile) return null

  const mastery = profile.cognitive?.knowledge_mastery || {}
  const weakConcepts = profile.cognitive?.weak_concepts || []

  return (
    <div className={styles.stack}>
      <div className={styles.card}>
        <div className={styles.cardTitle}>知识点掌握度</div>
        <KnowledgeRadar knowledgeMastery={mastery} />
      </div>

      <WeakConceptsCard weakConcepts={weakConcepts} viewMode={viewMode} />

      <EmotionCard
        currentEmotion={profile.emotional?.current_emotion || 'neutral'}
        learningStyle={profile.metacognitive?.learning_style || 'guided'}
        overallMastery={overallMastery(mastery)}
      />
    </div>
  )
}
