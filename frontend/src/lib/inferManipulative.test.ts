import { describe, expect, it } from 'vitest'
import { inferCountingManipulative } from './inferManipulative'

describe('inferCountingManipulative', () => {
  it('matches primary-grade apple takeaway stems', () => {
    expect(
      inferCountingManipulative('有6个苹果，吃掉3个，剩下几个？'),
    ).toEqual({
      type: 'counting_takeaway',
      total: 6,
      takeAway: 3,
      objectLabel: '苹果',
    })
  })

  it('matches stems without 有', () => {
    expect(
      inferCountingManipulative('6个苹果吃了2个还剩几个'),
    ).toEqual({
      type: 'counting_takeaway',
      total: 6,
      takeAway: 2,
      objectLabel: '苹果',
    })
  })

  it('rejects invalid totals or take-away counts', () => {
    expect(inferCountingManipulative('3个苹果吃掉3个还剩几个')).toBeNull()
    expect(inferCountingManipulative('25个苹果吃掉1个还剩几个')).toBeNull()
    expect(inferCountingManipulative('小明买了2千克苹果')).toBeNull()
  })
})
