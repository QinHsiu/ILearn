import type { SessionState } from '../api/client'

export function stepFromSession(nextSession: SessionState) {
  if (nextSession.plan) return 3
  if (nextSession.grades?.length) return 2
  if (nextSession.paper) return 1
  return 0
}

/** Visibility/forceSync must not drop past onboard when the server has no paper yet. */
export function nextStepOnSync(currentStep: number, nextSession: SessionState) {
  return Math.max(currentStep, stepFromSession(nextSession))
}
