import { ASSESSMENT_SECONDS, SERVER_TIMEOUT_SECONDS, TIMER_EVENTS_CAP } from './timing'

it('locks Scenario B durations', () => {
  expect(ASSESSMENT_SECONDS).toBe(3600)
  expect(SERVER_TIMEOUT_SECONDS).toBe(150 * 60)
  expect(TIMER_EVENTS_CAP).toBe(200)
})
