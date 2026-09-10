import { beforeEach, describe, expect, it } from 'vitest'
import {
  clearOpenItem,
  consumeIncompleteOpenItem,
  readOpenItem,
  writeOpenItem,
} from './timerOpenItem'

describe('timerOpenItem', () => {
  beforeEach(() => {
    sessionStorage.clear()
  })

  it('write then consumeIncomplete returns item_id', () => {
    writeOpenItem('s1', 'q1', 1000)
    expect(consumeIncompleteOpenItem('s1')).toBe('q1')
    expect(readOpenItem('s1')).toBeNull()
  })

  it('clearOpenItem after successful flush prevents incomplete', () => {
    writeOpenItem('s1', 'q1')
    clearOpenItem('s1')
    expect(consumeIncompleteOpenItem('s1')).toBeNull()
  })
})
