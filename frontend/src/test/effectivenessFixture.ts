import type { EffectivenessResponse } from '../api/client'

export const EFFECTIVENESS: EffectivenessResponse = {
  metrics: {
    pre_assessment_score: 60,
    post_assessment_score: null,
    mastery_gain: 18,
    weakness_resolved_count: 1,
    weakness_remaining_count: 2,
    total_questions: 20,
    auto_graded_count: 14,
    manual_review_count: 6,
    estimated_grading_time_minutes: 6.5,
    traditional_grading_time_minutes: 40,
    time_saved_percent: 83.75,
    session_duration_seconds: 1680,
    hint_used_count: 0,
    avg_response_time_seconds: 0,
    completion_rate: 100,
    diagnosis_confidence: 0.82,
    evidence_count: 5,
    parent_view_count: 3,
    teacher_notes_count: 2,
  },
  comparison: {
    traditional_vs_ilearn: {
      grading_time: { traditional: '40.0分钟', ilearn: '6.5分钟' },
      personalized: { traditional: '统一作业', ilearn: '自适应个性化' },
      feedback_delay: { traditional: '1-2天', ilearn: '即时' },
    },
  },
}
