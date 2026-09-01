export type CountingTakeawaySpec = {
  type: 'counting_takeaway'
  total: number
  takeAway: number
  objectLabel: string
}

const TAKEAWAY_RE =
  /(?:有)?(\d+)\s*个?\s*(苹果|梨|桃|橘子|橙|本子|铅笔|球).*?(?:吃掉|吃了|拿走|去掉|减去|用去)(\d+)\s*个?.*?(?:剩下|还剩)/

const MAX_TOTAL = 20

/** Heuristic: primary-grade takeaway word problems with countable objects. */
export function inferCountingManipulative(stem: string): CountingTakeawaySpec | null {
  const text = stem.replace(/\s+/g, '')
  const match = text.match(TAKEAWAY_RE)
  if (!match) return null

  const total = Number(match[1])
  const objectLabel = match[2]
  const takeAway = Number(match[3])
  if (
    !Number.isFinite(total) ||
    !Number.isFinite(takeAway) ||
    total <= 0 ||
    takeAway <= 0 ||
    takeAway >= total ||
    total > MAX_TOTAL
  ) {
    return null
  }

  return { type: 'counting_takeaway', total, takeAway, objectLabel }
}
