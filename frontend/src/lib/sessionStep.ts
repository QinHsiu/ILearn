import type { SessionState } from '../api/client'

/** Wizard: 0 onboard · 1 companion · 2 assessment · 3 diagnosis · 4 plan */
export function stepFromSession(nextSession: SessionState) {
  if (nextSession.plan) return 4
  if (nextSession.grades?.length) return 3
  if (nextSession.paper) return 2
  return 0
}

/** Visibility/forceSync must not drop past companion when the server has no paper yet. */
export function nextStepOnSync(currentStep: number, nextSession: SessionState) {
  return Math.max(currentStep, stepFromSession(nextSession))
}
