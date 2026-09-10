export type AssessmentItemMeta = {
  item_meta_version: 'v1'
  elapsed_ms: number
  thinking_ms: number
  overtime_ms?: number
  ui_deadline_crossed?: boolean
  thinking_ms_incomplete?: boolean
  pause_count?: number
  pause_ms?: number
  pause_ms_busy?: number
  pause_ms_visibility?: number
  hint_used: boolean
}

export type TimerEvent =
  | { type: 'timer_pause'; ts: number; item_id: string; reason: 'busy' | 'visibility' | 'feedback' }
  | { type: 'timer_resume'; ts: number; item_id: string; pause_duration_ms: number }
  | { type: 'timer_pause_cap'; ts: number; item_id: string; cap_ms: number }
  | { type: 'item_time_flush'; ts: number; item_id: string; thinking_ms: number; pause_ms: number; incomplete?: boolean }
  | { type: 'timer_refresh'; ts: number; item_id?: string }
  | { type: 'ui_deadline'; ts: number }
