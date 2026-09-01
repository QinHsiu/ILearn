import { describe, expect, it } from 'vitest'
import { readDemoSessionId } from './demoSessionQuery'

describe('readDemoSessionId', () => {
  it('reads session_id', () => {
    expect(readDemoSessionId('?student=1&session_id=sess-demo')).toBe('sess-demo')
  })
  it('returns null when missing', () => {
    expect(readDemoSessionId('?student=1')).toBeNull()
  })
  it('ignores empty session_id', () => {
    expect(readDemoSessionId('?session_id=')).toBeNull()
  })
})
